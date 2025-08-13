import os, json, pathlib
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import stripe

API_NAME = os.getenv("API_NAME", "Street Momentum API")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")  # set on Render
STRIPE_PRICE_MODE = "dynamic"  # we’ll pass price in cents

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

app = FastAPI(title=API_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if CORS_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = pathlib.Path(__file__).parent / "data"
PRODUCTS_FILE = DATA_DIR / "products.json"

def load_products() -> List[Dict[str, Any]]:
    with open(PRODUCTS_FILE, "r") as f:
        return json.load(f)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/products")
def products():
    return load_products()

class CheckoutItem(BaseModel):
    id: str
    quantity: int

class CheckoutRequest(BaseModel):
    items: List[CheckoutItem]
    success_url: str  # frontend page to return to
    cancel_url: str

@app.post("/create-checkout-session")
def create_checkout_session(payload: CheckoutRequest):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    catalog = {p["id"]: p for p in load_products()}
    line_items = []
    for item in payload.items:
        if item.id not in catalog:
            raise HTTPException(status_code=400, detail=f"Unknown product id={item.id}")
        p = catalog[item.id]
        if not p.get("in_stock", True):
            raise HTTPException(status_code=400, detail=f"Out of stock: {p['name']}")
        line_items.append({
            "quantity": item.quantity,
            "price_data": {
                "currency": "usd",
                "unit_amount": p["price"],  # cents
                "product_data": {
                    "name": p["name"],
                    "images": [p["image_url"]],
                    "metadata": {"product_id": p["id"]},
                }
            }
        })
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        success_url=payload.success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=payload.cancel_url,
        shipping_address_collection={"allowed_countries": ["US", "CA"]},
    )
    return {"id": session.id, "url": session.url}