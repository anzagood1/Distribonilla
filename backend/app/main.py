from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import auth, inventory

app = FastAPI(title="API Distribuidora")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Prefijo /api/v1 es una buena práctica de arquitectura
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
