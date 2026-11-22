import uuid

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from supabase_auth.errors import AuthError

from app.core.supabase import create_supabase_client
from app.db.session import SessionLocal
from app.models.inventory import Usuario

bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


BEARER_CREDENTIALS_DEPENDENCY = Depends(bearer_scheme)
DB_DEPENDENCY = Depends(get_db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = BEARER_CREDENTIALS_DEPENDENCY,
    db: Session = DB_DEPENDENCY,
) -> Usuario:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        client = create_supabase_client()
        response = client.auth.get_user(credentials.credentials)
        auth_user = response.user if response is not None else None
    except (AuthError, httpx.HTTPError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if auth_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        auth_uuid = uuid.UUID(str(auth_user.id))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario autenticado sin autorización",
        )

    user = (
        db.query(Usuario)
        .filter(
            Usuario.auth_user_id == auth_uuid,
            Usuario.activo.is_(True),
        )
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario autenticado sin autorización",
        )

    return user


CURRENT_USER_DEPENDENCY = Depends(get_current_user)
