"""Integration tests for an explicitly named disposable loopback PostgreSQL DB."""

import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from app.api.dependencies import get_current_user, get_db
from app.db.base import Base
from app.main import app
from app.models.inventory import IdempotencyKey, MovimientoInventario, Usuario
from app.models.item import Item

TEST_URL = os.environ.get("DISTRIBONILLA_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_URL, reason="Disposable PostgreSQL is not configured"
)


@pytest.fixture
def pg_api():
    url = make_url(TEST_URL)
    if (
        url.get_backend_name() != "postgresql"
        or url.host != "127.0.0.1"
        or url.port is None
        or url.port < 1024
        or not (url.database or "").startswith("grupo511_test_")
        or url.query
    ):
        pytest.fail("Refusing to run against a non-disposable database")
    schema = "test_" + uuid.uuid4().hex
    admin_engine = create_engine(url)
    with admin_engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
            CREATE OR REPLACE FUNCTION aplicar_movimiento_stock()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.tipo = 'entrada' THEN
                    UPDATE productos SET stock_actual = stock_actual + NEW.cantidad
                    WHERE id = NEW.producto_id;
                ELSE
                    UPDATE productos SET stock_actual = stock_actual - NEW.cantidad
                    WHERE id = NEW.producto_id AND stock_actual >= NEW.cantidad;
                    IF NOT FOUND THEN
                        RAISE EXCEPTION 'Stock insuficiente o producto inexistente';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$
        """
            )
        )
        conn.execute(
            text(
                "DROP TRIGGER IF EXISTS trg_movimiento_stock ON movimientos_inventario"
            )
        )
        conn.execute(
            text(
                """
            CREATE TRIGGER trg_movimiento_stock AFTER INSERT ON movimientos_inventario
            FOR EACH ROW EXECUTE FUNCTION aplicar_movimiento_stock()
        """
            )
        )

    factory = sessionmaker(bind=engine, autoflush=False)
    with factory.begin() as session:
        session.add(Usuario(id=1, auth_user_id=uuid.uuid4(), activo=True))
        session.add(
            Item(
                id=1,
                codigo="PRUEBA",
                nombre="Producto de prueba",
                precio_unitario=1,
                stock_actual=5,
                stock_minimo=0,
                activo=True,
            )
        )

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: Usuario(id=1, activo=True)
    yield engine, factory
    app.dependency_overrides.clear()
    engine.dispose()
    with admin_engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin_engine.dispose()


def state(factory):
    with factory() as session:
        product = session.get(Item, 1)
        moves = session.scalars(select(MovimientoInventario)).all()
        keys = session.scalars(select(IdempotencyKey)).all()
        return (
            product.stock_actual,
            [
                (m.tipo, m.cantidad, m.stock_anterior, m.stock_resultante, m.usuario_id)
                for m in moves
            ],
            len(keys),
        )


def send(quantity=4, reason="daño", key=None, product_id=1):
    headers = {"Idempotency-Key": key} if key else {}
    with TestClient(app) as client:
        return client.post(
            "/api/v1/inventory/exits",
            json={"producto_id": product_id, "cantidad": quantity, "motivo": reason},
            headers=headers,
        )


@pytest.mark.parametrize(
    ("quantity", "reason", "expected"), [(4, "daño", 1), (5, "merma", 0)]
)
def test_exit_updates_stock_once_and_persists_history(
    pg_api, quantity, reason, expected
):
    _, factory = pg_api
    response = send(quantity, reason)
    assert response.status_code == 201
    assert state(factory) == (expected, [("salida", quantity, 5, expected, 1)], 0)


@pytest.mark.parametrize("quantity", [6, 0, -1, 1.5])
def test_invalid_or_insufficient_quantity_has_no_effect(pg_api, quantity):
    _, factory = pg_api
    response = send(quantity)
    assert response.status_code == (409 if quantity == 6 else 422)
    assert state(factory) == (5, [], 0)


def test_replay_conflict_and_stock_are_atomic(pg_api):
    _, factory = pg_api
    first = send(4, key="X")
    repeated = send(4, key="X")
    changed = send(3, key="X")
    assert first.status_code == repeated.status_code == 201
    assert first.json() == repeated.json()
    assert changed.status_code == 409
    assert state(factory) == (1, [("salida", 4, 5, 1, 1)], 1)


@pytest.mark.parametrize(
    ("keys", "expected_status"),
    [
        (("concurrent-a", "concurrent-b"), [201, 409]),
        (("same-key", "same-key"), [201, 201]),
    ],
)
def test_concurrent_exits_serialize_on_product_lock(pg_api, keys, expected_status):
    engine, factory = pg_api
    attempted = threading.Event()
    count_lock = threading.Lock()
    attempts = []

    def before_execute(_conn, _cursor, statement, _params, _context, _many):
        if "FOR UPDATE" in statement.upper() and "PRODUCTOS" in statement.upper():
            with count_lock:
                attempts.append(1)
                if len(attempts) == 2:
                    attempted.set()

    with engine.connect() as lock_connection:
        transaction = lock_connection.begin()
        lock_connection.execute(
            text("SELECT id FROM productos WHERE id = 1 FOR UPDATE")
        )
        event.listen(engine, "before_cursor_execute", before_execute)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(send, 4, "daño", key) for key in keys]
                try:
                    assert attempted.wait(
                        timeout=15
                    ), "Both requests must attempt the locked row"
                finally:
                    transaction.commit()
                responses = [f.result(timeout=15) for f in futures]
                statuses = sorted(response.status_code for response in responses)
                if expected_status == [201, 201]:
                    assert responses[0].json() == responses[1].json()
        finally:
            event.remove(engine, "before_cursor_execute", before_execute)
            if transaction.is_active:
                transaction.rollback()

    assert statuses == expected_status
    assert state(factory) == (1, [("salida", 4, 5, 1, 1)], 1)


def test_failure_after_trigger_rolls_back_movement_and_stock(pg_api):
    engine, factory = pg_api

    def fail_key_insert(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().upper().startswith("INSERT INTO IDEMPOTENCY_KEYS"):
            raise SQLAlchemyError("forced test failure")

    event.listen(engine, "before_cursor_execute", fail_key_insert)
    try:
        response = send(4, key="failure")
        assert response.status_code == 500
    finally:
        event.remove(engine, "before_cursor_execute", fail_key_insert)
    assert state(factory) == (5, [], 0)
    assert send(4, key="recovery").status_code == 201
    assert state(factory) == (1, [("salida", 4, 5, 1, 1)], 1)


def test_missing_trigger_rolls_back_insert(pg_api):
    engine, factory = pg_api
    with engine.begin() as conn:
        conn.execute(
            text("DROP TRIGGER trg_movimiento_stock ON movimientos_inventario")
        )
    assert send(4, key="missing-trigger").status_code == 500
    assert state(factory) == (5, [], 0)


def test_expired_key_is_reused_after_24_hour_window(pg_api):
    from datetime import datetime, timedelta, timezone

    _, factory = pg_api
    assert send(1, key="expiry").status_code == 201
    with factory.begin() as session:
        key = session.scalar(
            select(IdempotencyKey).where(IdempotencyKey.key == "expiry")
        )
        key.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert send(2, key="expiry").status_code == 201
    assert state(factory) == (
        2,
        [("salida", 1, 5, 4, 1), ("salida", 2, 4, 2, 1)],
        1,
    )


@pytest.mark.parametrize(
    "real_index", [False, True], ids=["migration_index", "real_index_name"]
)
def test_concurrent_same_key_for_different_products_rolls_back_loser(
    pg_api, real_index
):
    engine, factory = pg_api
    if real_index:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE idempotency_keys DROP CONSTRAINT idempotency_keys_key_key"
                )
            )
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX idempotency_keys_created_at_key ON idempotency_keys (key)"
                )
            )
    with factory.begin() as session:
        session.add(
            Item(
                id=2,
                codigo="OTRO",
                nombre="Otro producto",
                precio_unitario=1,
                stock_actual=5,
                stock_minimo=0,
                activo=True,
            )
        )

    barrier = threading.Barrier(2)

    def sync_key_inserts(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().upper().startswith("INSERT INTO IDEMPOTENCY_KEYS"):
            barrier.wait(timeout=15)

    event.listen(engine, "before_cursor_execute", sync_key_inserts)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(send, 4, "daño", "shared-key", product_id)
                for product_id in (1, 2)
            ]
            statuses = sorted(f.result(timeout=20).status_code for f in futures)
    finally:
        event.remove(engine, "before_cursor_execute", sync_key_inserts)
    assert statuses == [201, 409]
    with factory() as session:
        stocks = sorted(session.scalars(select(Item.stock_actual)).all())
        movements = session.scalars(select(MovimientoInventario)).all()
        keys = session.scalars(select(IdempotencyKey)).all()
        assert stocks == [1, 5]
        assert len(movements) == len(keys) == 1
