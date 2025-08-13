import os
import json
import uuid
import pathlib
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from square.client import Client

# ----- Config / Env -----
API_NAME = os.getenv("API_NAME", "Street Momentum API")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")

SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")
SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID")
SQUARE_ENV = os.getenv("SQUARE_ENV", "sandbox")  # "sandbox" or "production"

# Square client (ok even if not configured yet; we'll check later)
sq = Client(
    access_token=SQUARE_ACCESS_TOKEN,
    environment=SQUARE_ENV
)

# ----- FastAPI app & CORS -----
app = FastAPI(title=API_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if CORS_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Data (simple JSON catalog for now) -----
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
    success_url: str  # page to return to after successful payment
    cancel_url: str   # (not used by Square Payment Links; kept for parity)


# ----- Routes -----
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/products")
def products():
    return load_products()


@app.post("/create-payment-link")
def create_payment_link(payload: CheckoutRequest):
    """
    Create a Square-hosted checkout link for the given cart.
    Uses Checkout API -> CreatePaymentLink with an embedded Order.
    """
    # Basic config checks
    if not SQUARE_ACCESS_TOKEN or not SQUARE_LOCATION_ID:
        raise HTTPException(status_code=500, detail="Square is not configured")

    catalog = {p["id"]: p for p in load_products()}
    if not payload.items:
        raise HTTPException(status_code=400, detail="No items in cart")

    # Build Order line items
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
            "base_price_money": {
                "amount": int(prod["price"]),  # cents
                "currency": "USD"
            },
            # Optional:
            "note": prod.get("description", ""),
            # You can add "item_type": "ITEM" and "catalog_object_id" if you use Square Catalog later
        })

    # Build request body for CreatePaymentLink
    body = {
        "idempotency_key": str(uuid.uuid4()),
        "order": {
            "location_id": SQUARE_LOCATION_ID,
            "line_items": line_items,
        },
        "checkout_options": {
            # Square redirects back to this URL after payment
            "redirect_url": payload.success_url,
            # Ask for shipping details on the hosted page (optional)
            "ask_for_shipping_address": True
        }
    }

    # Call Square's API
    result = sq.checkout.create_payment_link(body)

    if result.is_error():
        # Surface first error for easier debugging
        try:
            detail = result.errors[0]["detail"]
        except Exception:
            detail = str(result.errors)
        raise HTTPException(status_code=502, detail=f"Square error: {detail}")

    link = result.body["payment_link"]["url"]
    return {"url": link}