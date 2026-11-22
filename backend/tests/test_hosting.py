import os
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from app.main import app, cors_origins


def test_health_does_not_require_a_database_connection():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_local_cors_preflight_remains_supported():
    with TestClient(app) as client:
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://*.example.com",
        "https://example.com/path",
        "ftp://example.com",
        "https://user:pass@example.com",
    ],
)
def test_invalid_cors_origins_are_rejected(origin):
    with pytest.raises(ValueError):
        cors_origins(origin)


def test_configured_origin_is_allowed_and_unknown_origin_is_denied():
    env = os.environ.copy()
    env.update(
        CORS_ORIGINS="https://midterm.example.test",
        DATABASE_URL="postgresql://127.0.0.1:1/isolated",
        VITE_SUPABASE_URL="http://127.0.0.1:1",
        VITE_SUPABASE_PUBLISHABLE_KEY="isolated-test-placeholder",
    )
    script = """
from fastapi.testclient import TestClient
from app.main import app
with TestClient(app) as client:
    for origin, status in [("https://midterm.example.test", 200), ("https://other.example.test", 400)]:
        response = client.options("/api/auth/login", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
        assert response.status_code == status
        assert (response.headers.get("access-control-allow-origin") == origin) == (status == 200)
"""
    subprocess.run([sys.executable, "-c", script], env=env, check=True)


def test_backend_settings_accept_the_shared_frontend_env_file(tmp_path):
    from app.core.config import Settings

    shared = tmp_path / ".env"
    shared.write_text(
        "VITE_API_URL=https://api.example.test\n"
        "VITE_SUPABASE_URL=http://127.0.0.1:1\n"
        "VITE_SUPABASE_PUBLISHABLE_KEY=isolated-test-placeholder\n"
        "DATABASE_URL=postgresql://127.0.0.1:1/isolated\n",
        encoding="utf-8",
    )
    settings = Settings(_env_file=shared)
    assert settings.VITE_SUPABASE_URL
