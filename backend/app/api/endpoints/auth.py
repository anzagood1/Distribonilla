import logging

import httpx
from fastapi import APIRouter, HTTPException
from supabase_auth.errors import AuthApiError, AuthError

from app.core.supabase import create_supabase_client
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/login", response_model=LoginResponse)
def login(credentials: LoginRequest) -> LoginResponse:
    if not credentials.password:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    try:
        client = create_supabase_client()
        result = client.auth.sign_in_with_password(
            {"email": str(credentials.email), "password": credentials.password}
        )
    except AuthApiError as exc:
        if exc.code == "invalid_credentials":
            raise HTTPException(
                status_code=401, detail="Credenciales inválidas"
            ) from exc
        logger.warning(
            "Supabase Auth error: type=%s code=%s status=%s",
            type(exc).__name__,
            exc.code,
            exc.status,
        )
        raise HTTPException(
            status_code=503, detail="Servicio de autenticación no disponible"
        ) from exc
    except (AuthError, httpx.RequestError) as exc:
        logger.warning(
            "Supabase Auth error: type=%s code=%s status=%s",
            type(exc).__name__,
            getattr(exc, "code", None),
            getattr(exc, "status", None),
        )
        raise HTTPException(
            status_code=503, detail="Servicio de autenticación no disponible"
        ) from exc

    if result.session is None:
        logger.warning("Supabase Auth returned no session")
        raise HTTPException(
            status_code=503, detail="Servicio de autenticación no disponible"
        )
    session = result.session
    return LoginResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        token_type=session.token_type,
        expires_in=session.expires_in,
    )
