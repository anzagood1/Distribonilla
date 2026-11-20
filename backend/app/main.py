from fastapi import FastAPI
from app.api.endpoints import auth, inventory

app = FastAPI(title="API Distribuidora")

# Prefijo /api/v1 es una buena práctica de arquitectura
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
