# api/main.py
import os
import uuid
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Square SDK (v42+)
from square import Square
from square.environment import SquareEnvironment
from square.core.api_error import ApiError

# DB (SQLAlchemy async)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session  # <- you created api/db.py earlier

# ----- Config / Env -----
API_NAME = os.getenv("API_NAME", "Street Momentum API")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")

SQUARE_ACCESS_TOKEN = os.getenv("SQUARE_ACCESS_TOKEN")
SQUARE_LOCATION_ID = os.getenv("SQUARE_LOCATION_ID")
SQUARE_ENV = os.getenv("SQUARE_ENV", "sandbox")  # "sandbox" or "production"

square_env = (
    SquareEnvironment.SANDBOX
    if SQUARE_ENV.lower() == "sandbox"
    else SquareEnvironment.PRODUCTION
)
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

# ----- Models -----
class CheckoutItem(BaseModel):
    id: str          # variant_id
    quantity: int

class CheckoutRequest(BaseModel):
    items: List[CheckoutItem]
    success_url: str
    cancel_url: str

# ----- Utility -----
def _require_square():
    if not (SQUARE_ACCESS_TOKEN and SQUARE_LOCATION_ID):
        raise HTTPException(status_code=500, detail="Square is not configured")

# ----- Routes -----
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"ok": True, "routes": ["/health", "/products", "/create-payment-link", "/config-check", "/docs"]}

@app.get("/config-check")
def config_check():
    return {
        "square_env": SQUARE_ENV,
        "has_token": bool(SQUARE_ACCESS_TOKEN),
        "has_location": bool(SQUARE_LOCATION_ID),
    }

@app.get("/products")
async def products(session: AsyncSession = Depends(get_session)):
    """
    Return sellable variants from Postgres (products + variants + inventory).
    Shape matches your existing frontend expectations.
    """
    q = text("""
      select
        p.id as product_id,
        p.name as product_name,
        p.description,
        v.id as variant_id,
        v.label,
        v.price_cents,
        v.image_url,
        coalesce(i.in_stock, 0) as in_stock
      from product_variants v
      join products p on p.id = v.product_id
      left join inventory i on i.variant_id = v.id
      where v.active = true
      order by p.name, v.label nulls last;
    """)
    rows = (await session.execute(q)).mappings().all()

    # Flatten to your simple product card shape; id is the VARIANT id.
    return [
        {
            "id": r["variant_id"],
            "name": r["product_name"] + (f" — {r['label']}" if r["label"] else ""),
            "price": r["price_cents"],       # cents
            "image_url": r["image_url"],
            "description": r["description"],
            "in_stock": (r["in_stock"] > 0),
        }
        for r in rows
    ]

@app.post("/create-payment-link")
async def create_payment_link(
    payload: CheckoutRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Builds a Square-hosted checkout link using server-side prices from Postgres.
    Expects payload.items[*].id to be a VARIANT id.
    """
    _require_square()
    if not payload.items:
        raise HTTPException(status_code=400, detail="No items in cart")

    variant_ids = [i.id for i in payload.items]
    q = text("""
      select
        v.id as variant_id,
        p.name as product_name,
        v.label,
        v.price_cents,
        v.image_url,
        coalesce(i.in_stock, 0) as in_stock
      from product_variants v
      join products p on p.id = v.product_id
      left join inventory i on i.variant_id = v.id
      where v.id = any(:ids)
    """)
    rows = (await session.execute(q, {"ids": variant_ids})).mappings().all()
    by_id: Dict[str, Any] = {r["variant_id"]: r for r in rows}

    # Build Square line items
    line_items = []
    for item in payload.items:
        r = by_id.get(item.id)
        if not r:
            raise HTTPException(status_code=400, detail=f"Unknown variant id={item.id}")
        if r["in_stock"] <= 0:
            raise HTTPException(status_code=400, detail=f"Out of stock: {r['product_name']}")
        name = r["product_name"] + (f" — {r['label']}" if r["label"] else "")
        line_items.append({
            "name": name,
            "quantity": str(item.quantity),
            "base_price_money": {"amount": int(r["price_cents"]), "currency": "USD"},
        })

    # Create the hosted checkout link via Square Checkout API
    try:
        resp = sq.checkout.create_payment_link(
            body={
                "idempotency_key": str(uuid.uuid4()),
                "order": {
                    "location_id": SQUARE_LOCATION_ID,
                    "line_items": line_items,
                },
                "checkout_options": {
                    "redirect_url": payload.success_url,
                    "ask_for_shipping_address": True,
                },
            }
        )
        return {"url": resp.payment_link.url}

    except ApiError as e:
        detail = e.errors[0].detail if getattr(e, "errors", None) else str(e)
        raise HTTPException(status_code=502, detail=f"Square error: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unhandled server error: {e.__class__.__name__}: {e}")