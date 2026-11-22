from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import auth, inventory, inventory_exits
from app.core.config import settings


def cors_origins(configured: str) -> list[str]:
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    for value in configured.split(","):
        origin = value.strip().rstrip("/")
        if not origin:
            continue
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or "*" in parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("CORS_ORIGINS must contain explicit HTTP(S) origins")
        if origin not in origins:
            origins.append(origin)
    return origins


app = FastAPI(title="API Distribuidora")


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(settings.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

# Prefijo /api/v1 es una buena práctica de arquitectura
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])
app.include_router(
    inventory_exits.router, prefix="/api/v1/inventory", tags=["Inventory"]
)
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
