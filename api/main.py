import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

API_NAME = os.getenv("API_NAME", "Street Momentum API")
CORS_ORIGIN = os.getenv("CORS_ORIGIN", "*")

app = FastAPI(title=API_NAME)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[CORS_ORIGIN] if CORS_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}