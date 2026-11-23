import pytest
import os

from fastapi.testclient import TestClient
from sqlalchemy import text
from test_inventory_exits_postgres import pg_api, state  # noqa: F401

from app.main import app

pytestmark = pytest.mark.skipif(
    not os.environ.get("DISTRIBONILLA_TEST_DATABASE_URL"),
    reason="Disposable PostgreSQL is not configured",
)


def post_entry(key="d8d3"):
    with TestClient(app) as client:
        return client.post(
            "/api/v1/inventory/entries",
            json={"producto_id": 1, "cantidad": 4, "motivo": "Compra"},
            headers={"Idempotency-Key": key},
        )


def test_single_stock_update_and_idempotency(request: pytest.FixtureRequest):
    engine, factory = request.getfixturevalue("pg_api")
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE productos SET actualizado_en = '2000-01-01' WHERE id = 1")
        )
        conn.execute(
            text("CREATE TABLE stock_audit (old_stock integer, new_stock integer)")
        )
        conn.execute(
            text(
                """
            CREATE FUNCTION audit_stock_update() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                INSERT INTO stock_audit VALUES (OLD.stock_actual, NEW.stock_actual);
                RETURN NEW;
            END; $$
        """
            )
        )
        conn.execute(
            text(
                """
            CREATE TRIGGER audit_stock_update BEFORE UPDATE ON productos
            FOR EACH ROW EXECUTE FUNCTION audit_stock_update()
        """
            )
        )
    first, replay = post_entry(), post_entry()
    with engine.connect() as conn:
        updates = conn.execute(
            text("SELECT old_stock, new_stock FROM stock_audit")
        ).all()
        updated_at = conn.execute(
            text("SELECT actualizado_en FROM productos WHERE id = 1")
        ).scalar_one()
    result = state(factory)
    print("ENTRY", first.status_code, replay.status_code, result, "UPDATES", updates)
    assert first.status_code == replay.status_code == 201
    assert result == (9, [("entrada", 4, 5, 9, 1)], 1)
    assert [pair for pair in updates if pair[0] != pair[1]] == [(5, 9)]
    assert updates[-1] == (9, 9)
    assert updated_at.year > 2000


def test_entry_fails_and_rolls_back_with_incompatible_trigger(
    request: pytest.FixtureRequest,
):
    engine, factory = request.getfixturevalue("pg_api")
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE movimientos_inventario DISABLE TRIGGER trg_movimiento_stock"
            )
        )
    response = post_entry("missing-trigger")
    result = state(factory)
    print("MISSING_TRIGGER", response.status_code, result)
    assert response.status_code == 500
    assert result == (5, [], 0)
