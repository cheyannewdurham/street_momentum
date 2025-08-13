import os
import json
import uuid
import pathlib
from typing import List, Dict, Any
import httpx

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# NEW Square SDK imports (v42+)
from square import Square
from square.environment import SquareEnvironment
from square.core.api_error import ApiError

# ----- Config / Env -----
API_NAME = os.getenv("API_NAME", "Street Momentum API")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")

SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")
SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID")
SQUARE_ENV = os.getenv("SQUARE_ENV", "sandbox")  # "sandbox" or "production"

# Build Square client (SDK v42+)
square_env = SquareEnvironment.SANDBOX if SQUARE_ENV.lower() == "sandbox" else SquareEnvironment.PRODUCTION
sq = Square(token=SQUARE_ACCESS_TOKEN, environment=square_env)

# ----- FastAPI app & CORS -----
app = FastAPI(title=API_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if CORS_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Data (simple JSON catalog) -----
DATA_DIR = pathlib.Path(__file__).parent / "data"
PRODUCTS_FILE = DATA_DIR / "products.json"

def load_products() -> List[Dict[str, Any]]:
    if not PRODUCTS_FILE.exists():
        return []
    with open(PRODUCTS_FILE, "r") as f:
        return json.load(f)

# ----- Models -----
class CheckoutItem(BaseModel):
    id: str
    quantity: int

class CheckoutRequest(BaseModel):
    items: List[CheckoutItem]
    success_url: str
    cancel_url: str  # kept for parity; Square Payment Links only uses redirect_url

# ----- Routes -----
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"ok": True, "routes": ["/health", "/products", "/create-payment-link", "/docs"]}

@app.get("/config-check")
def config_check():
    return {
        "square_env": SQUARE_ENV,
        "has_token": bool(SQUARE_ACCESS_TOKEN),
        "has_location": bool(SQUARE_LOCATION_ID),
    }

@app.get("/products")
def products():
    return load_products()

@app.post("/create-payment-link")
def create_payment_link(payload: CheckoutRequest):
    if not (SQUARE_ACCESS_TOKEN and SQUARE_LOCATION_ID):
        raise HTTPException(status_code=500, detail="Square is not configured")

    catalog = {p["id"]: p for p in load_products()}
    if not payload.items:
        raise HTTPException(status_code=400, detail="No items in cart")

    # Build line items for the Square Order
    line_items: List[Dict[str, Any]] = []
    for item in payload.items:
        prod = catalog.get(item.id)
        if not prod:
            raise HTTPException(status_code=400, detail=f"Unknown product id={item.id}")
        if not prod.get("in_stock", True):
            raise HTTPException(status_code=400, detail=f"Out of stock: {prod['name']}")
        line_items.append({
            "name": prod["name"],
            "quantity": str(item.quantity),
            "base_price_money": {"amount": int(prod["price"]), "currency": "USD"},
            "note": prod.get("description", "")
        })

    try:
        # Build the HTTP request directly to Square's Payment Links API
        base = "https://connect.squareupsandbox.com" if SQUARE_ENV.lower() == "sandbox" else "https://connect.squareup.com"
        url = f"{base}/v2/online-checkout/payment-links"

        body = {
            "idempotency_key": str(uuid.uuid4()),
            "order": {
                "location_id": SQUARE_LOCATION_ID,
                "line_items": line_items,
            },
            "checkout_options": {
                "redirect_url": payload.success_url,
                "ask_for_shipping_address": True
            }
        }

        headers = {
            "Authorization": f"Bearer {SQUARE_ACCESS_TOKEN}",
            # Use a recent Square-Version; month updates are fine. Keep this in sync occasionally.
            "Square-Version": "2025-07-17",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=15) as client:
            r = client.post(url, headers=headers, json=body)
            data = r.json()

        if r.status_code >= 400:
            # Surface Square's first error if available
            err = data.get("errors", [{}])[0].get("detail", f"HTTP {r.status_code}")
            raise HTTPException(status_code=502, detail=f"Square error: {err}")

        link = data["payment_link"]["url"]
        return {"url": link}

    except ApiError as e:
        detail = e.errors[0].detail if getattr(e, "errors", None) else str(e)
        raise HTTPException(status_code=502, detail=f"Square error: {detail}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unhandled server error: {e.__class__.__name__}: {e}")