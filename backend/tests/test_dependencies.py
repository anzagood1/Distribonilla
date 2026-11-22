from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user
from app.models.inventory import Usuario


def make_db(user):
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = user

    db = Mock()
    db.query.return_value = query
    return db


def test_get_current_user_requires_credentials():
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=None, db=make_db(None))

    assert exc.value.status_code == 401


def test_get_current_user_rejects_invalid_supabase_response(monkeypatch):
    client = Mock()
    client.auth.get_user.return_value = SimpleNamespace(user=None)
    monkeypatch.setattr("app.api.dependencies.create_supabase_client", lambda: client)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=credentials, db=make_db(None))

    assert exc.value.status_code == 401


def test_get_current_user_rejects_http_error(monkeypatch):
    client = Mock()
    client.auth.get_user.side_effect = httpx.HTTPError("network failed")
    monkeypatch.setattr("app.api.dependencies.create_supabase_client", lambda: client)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=credentials, db=make_db(None))

    assert exc.value.status_code == 401


def test_get_current_user_rejects_invalid_uuid(monkeypatch):
    client = Mock()
    client.auth.get_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id="not-a-uuid")
    )
    monkeypatch.setattr("app.api.dependencies.create_supabase_client", lambda: client)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=credentials, db=make_db(None))

    assert exc.value.status_code == 403


def test_get_current_user_rejects_unknown_user(monkeypatch):
    client = Mock()
    client.auth.get_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
    )
    monkeypatch.setattr("app.api.dependencies.create_supabase_client", lambda: client)

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=credentials, db=make_db(None))

    assert exc.value.status_code == 403


def test_get_current_user_returns_active_user(monkeypatch):
    client = Mock()
    client.auth.get_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id="12345678-1234-5678-1234-567812345678")
    )
    monkeypatch.setattr("app.api.dependencies.create_supabase_client", lambda: client)

    user = Usuario(id=7, activo=True)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")

    assert get_current_user(credentials=credentials, db=make_db(user)) is user
