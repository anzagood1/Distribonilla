from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.endpoints.inventory_exits import register_inventory_exit
from app.models.inventory import IdempotencyKey, MovimientoInventario, Usuario
from app.models.item import Item
from app.schemas.inventory_exits import InventoryExitCreate


def entry(quantity=4, reason="daño"):
    return InventoryExitCreate(producto_id=1, cantidad=quantity, motivo=reason)


def make_db(product, existing=None, apply_trigger=True):
    item_query = Mock()
    item_query.filter.return_value = item_query
    item_query.with_for_update.return_value = item_query
    item_query.first.return_value = product
    key_query = Mock()
    key_query.filter.return_value = key_query
    key_query.first.return_value = existing
    db = Mock()
    db.query.side_effect = lambda model: item_query if model is Item else key_query
    added = []
    db.add.side_effect = added.append

    def flush():
        for obj in added:
            if isinstance(obj, MovimientoInventario) and obj.id is None:
                obj.id = 42

    def refresh(obj, attribute_names=None):
        if apply_trigger:
            obj.stock_actual = next(
                movement.stock_resultante
                for movement in added
                if isinstance(movement, MovimientoInventario)
            )

    db.flush.side_effect = flush
    db.refresh.side_effect = refresh
    return db, added, item_query


@pytest.mark.parametrize("quantity", [0, -1, 1.5, True, "4"])
def test_reject_invalid_quantities(quantity):
    with pytest.raises(ValidationError):
        entry(quantity)


@pytest.mark.parametrize("reason", ["robo", "", "DANO"])
def test_reject_unsupported_reason(reason):
    with pytest.raises(ValidationError):
        entry(reason=reason)


@pytest.mark.parametrize(
    ("quantity", "reason", "remaining"), [(4, "daño", 1), (5, "merma", 0)]
)
def test_exit_records_snapshot_and_trigger_is_sole_stock_writer(
    quantity, reason, remaining
):
    product = Item(id=1, activo=True, stock_actual=5)
    db, added, query = make_db(product)
    result = register_inventory_exit(
        entry(quantity, reason), db, Usuario(id=7, activo=True)
    )
    assert (result.tipo, result.stock_anterior, result.stock_resultante) == (
        "salida",
        5,
        remaining,
    )
    assert result.usuario_id == 7 and result.motivo == reason
    assert product.stock_actual == remaining
    assert sum(isinstance(obj, MovimientoInventario) for obj in added) == 1
    query.with_for_update.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.parametrize("product", [None, Item(id=1, activo=False, stock_actual=5)])
def test_missing_or_inactive_product(product):
    db, added, _ = make_db(product)
    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(), db, Usuario(id=7, activo=True))
    assert error.value.status_code == 404
    assert not added
    db.commit.assert_not_called()


def test_insufficient_stock_does_not_insert():
    product = Item(id=1, activo=True, stock_actual=5)
    db, added, _ = make_db(product)
    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(6), db, Usuario(id=7, activo=True))
    assert error.value.status_code == 409
    assert product.stock_actual == 5 and not added
    db.commit.assert_not_called()


def test_absent_or_incorrect_trigger_rolls_back():
    product = Item(id=1, activo=True, stock_actual=5)
    db, _, _ = make_db(product, apply_trigger=False)
    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(), db, Usuario(id=7, activo=True))
    assert error.value.status_code == 500
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_database_failure_rolls_back_without_details():
    product = Item(id=1, activo=True, stock_actual=5)
    db, _, _ = make_db(product)
    db.flush.side_effect = SQLAlchemyError("private database details")
    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(), db, Usuario(id=7, activo=True))
    assert error.value.status_code == 500
    assert "private" not in error.value.detail
    db.rollback.assert_called_once()


def test_replay_and_conflict_are_bound_to_actor_and_request():
    product = Item(id=1, activo=True, stock_actual=5)
    db, added, _ = make_db(product)
    first = register_inventory_exit(entry(), db, Usuario(id=7, activo=True), "X")
    key = next(obj for obj in added if isinstance(obj, IdempotencyKey))
    assert key.route == "/api/v1/inventory/exits" and key.user_id == 7
    db2, added2, _ = make_db(product, key)
    assert (
        register_inventory_exit(entry(), db2, Usuario(id=7, activo=True), "X")
        == key.response_body
    )
    assert first["stock_resultante"] == 1 and not added2
    for altered_entry, user_id in [(entry(3), 7), (entry(), 8)]:
        db3, added3, _ = make_db(product, key)
        with pytest.raises(HTTPException) as error:
            register_inventory_exit(
                altered_entry, db3, Usuario(id=user_id, activo=True), "X"
            )
        assert error.value.status_code == 409 and not added3


def test_expired_key_can_be_reused():
    product = Item(id=1, activo=True, stock_actual=5)
    previous = IdempotencyKey(
        key="X", expires_at=datetime.now(UTC) - timedelta(seconds=1)
    )
    db, added, _ = make_db(product, previous)
    register_inventory_exit(entry(), db, Usuario(id=7, activo=True), "X")
    db.delete.assert_called_once_with(previous)
    assert any(isinstance(obj, IdempotencyKey) for obj in added)
    db.commit.assert_called_once()


def test_missing_auth_is_401(client):
    response = client.post(
        "/api/v1/inventory/exits",
        json={"producto_id": 1, "cantidad": 4, "motivo": "daño"},
    )
    assert response.status_code == 401


def test_authenticated_http_exit_and_invalid_quantity(client, monkeypatch):
    from app.api.dependencies import get_current_user, get_db
    from app.main import app

    product = Item(id=1, activo=True, stock_actual=5)
    db, added, _ = make_db(product)
    app.dependency_overrides[get_current_user] = lambda: Usuario(id=7, activo=True)
    app.dependency_overrides[get_db] = lambda: db
    payload = {"producto_id": 1, "cantidad": 4, "motivo": "daño"}
    response = client.post(
        "/api/v1/inventory/exits", json=payload, headers={"Idempotency-Key": "X"}
    )
    assert response.status_code == 201
    assert response.json()["stock_resultante"] == 1
    assert sum(isinstance(obj, MovimientoInventario) for obj in added) == 1

    added.clear()
    response = client.post("/api/v1/inventory/exits", json={**payload, "cantidad": 1.5})
    assert response.status_code == 422 and not added


def test_cors_allows_idempotency_header(client):
    response = client.options(
        "/api/v1/inventory/exits",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
        },
    )
    assert response.status_code == 200
    assert "idempotency-key" in response.headers["access-control-allow-headers"].lower()


def test_initial_product_query_failure_rolls_back():
    db = Mock()
    db.query.side_effect = SQLAlchemyError("unavailable")
    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(), db, Usuario(id=7, activo=True))
    assert error.value.status_code == 500
    db.rollback.assert_called_once()


def test_authenticated_but_unregistered_user_is_403(client, monkeypatch):
    import uuid

    fake = Mock()
    fake.auth.get_user.return_value.user.id = str(uuid.uuid4())
    monkeypatch.setattr("app.api.dependencies.create_supabase_client", lambda: fake)
    response = client.post(
        "/api/v1/inventory/exits",
        json={"producto_id": 1, "cantidad": 4, "motivo": "daño"},
        headers={"Authorization": "Bearer simulated"},
    )
    assert response.status_code == 403


def test_unique_key_integrity_conflict_is_409(monkeypatch):
    from sqlalchemy.exc import IntegrityError

    import app.api.endpoints.inventory_exits as exits

    product = Item(id=1, activo=True, stock_actual=5)
    db, _, _ = make_db(product)
    existing = IdempotencyKey(
        key="X",
        request_hash="different",
        route=exits.EXIT_ROUTE,
        user_id=7,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        response_body={"id": 33},
    )
    db.query(IdempotencyKey).filter().first.side_effect = [None, None, existing]
    cause = Exception("duplicate")
    cause.pgcode = "23505"
    cause.diag = Mock(
        table_name="idempotency_keys",
        schema_name="public",
        constraint_name="some_unique_index",
    )
    db.flush.side_effect = IntegrityError("insert", {}, cause)
    inspector = Mock()
    inspector.get_indexes.return_value = [
        {"name": "some_unique_index", "unique": True, "column_names": ["key"]}
    ]
    monkeypatch.setattr(exits, "inspect", lambda _conn: inspector)

    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(), db, Usuario(id=7, activo=True), "X")
    assert error.value.status_code == 409
    db.rollback.assert_called_once()
    db.flush.assert_called_once()
    inspector.get_indexes.assert_called_once()


def test_unique_violation_on_unrelated_index_stays_500(monkeypatch):
    from sqlalchemy.exc import IntegrityError

    import app.api.endpoints.inventory_exits as exits

    db, _, _ = make_db(Item(id=1, activo=True, stock_actual=5))
    cause = Exception("duplicate")
    cause.pgcode = "23505"
    cause.diag = Mock(
        table_name="idempotency_keys",
        schema_name="public",
        constraint_name="other_index",
    )
    db.flush.side_effect = IntegrityError("insert", {}, cause)
    inspector = Mock()
    inspector.get_indexes.return_value = [
        {"name": "other_index", "unique": True, "column_names": ["movement_id"]}
    ]
    monkeypatch.setattr(exits, "inspect", lambda _conn: inspector)
    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(), db, Usuario(id=7, activo=True), "X")
    assert error.value.status_code == 500
    db.rollback.assert_called_once()


def test_unexpected_failure_rolls_back_without_exposing_details():
    product = Item(id=1, activo=True, stock_actual=5)
    db, _, _ = make_db(product)
    db.flush.side_effect = RuntimeError("private implementation details")
    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(), db, Usuario(id=7, activo=True))
    assert error.value.status_code == 500
    assert "private" not in error.value.detail
    db.rollback.assert_called_once()


@pytest.mark.parametrize(
    ("notes", "expected"), [("  lote  ", "lote"), ("  ", None), (None, None)]
)
def test_notes_are_normalized(notes, expected):
    assert (
        InventoryExitCreate(
            producto_id=1, cantidad=1, motivo="ajuste", notas=notes
        ).notas
        == expected
    )


@pytest.mark.parametrize("kind", ["identical", "other_user", "other_route", "expired"])
def test_race_recovery_respects_identity_route_and_expiry(monkeypatch, kind):
    import hashlib
    import json

    from sqlalchemy.exc import IntegrityError

    import app.api.endpoints.inventory_exits as exits

    request = entry()
    digest = hashlib.sha256(
        json.dumps(
            request.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    existing = IdempotencyKey(
        key="X",
        request_hash=digest,
        route="/other" if kind == "other_route" else exits.EXIT_ROUTE,
        user_id=8 if kind == "other_user" else 7,
        expires_at=datetime.now(UTC) + timedelta(hours=-1 if kind == "expired" else 1),
        response_body={"id": 33},
    )
    db, _, _ = make_db(Item(id=1, activo=True, stock_actual=5))
    db.query(IdempotencyKey).filter().first.side_effect = [
        None,
        None,
        existing,
        existing,
        existing,
    ]
    cause = Exception("duplicate")
    cause.pgcode = "23505"
    cause.diag = Mock(
        table_name="idempotency_keys",
        schema_name="public",
        constraint_name="unique_idx",
    )
    original_flush = db.flush.side_effect
    flush_count = [0]

    def fail_once():
        flush_count[0] += 1
        if flush_count[0] == 1 or kind != "expired":
            raise IntegrityError("insert", {}, cause)
        return original_flush()

    db.flush.side_effect = fail_once
    inspector = Mock()
    inspector.get_indexes.return_value = [
        {"name": "unique_idx", "unique": True, "column_names": ["key"]}
    ]
    monkeypatch.setattr(exits, "inspect", lambda _conn: inspector)
    if kind == "identical":
        assert register_inventory_exit(
            request, db, Usuario(id=7, activo=True), "X"
        ) == {"id": 33}
    elif kind == "expired":
        result = register_inventory_exit(request, db, Usuario(id=7, activo=True), "X")
        assert result["stock_resultante"] == 1
        db.delete.assert_called_once_with(existing)
        db.commit.assert_called_once()
    else:
        with pytest.raises(HTTPException) as error:
            register_inventory_exit(request, db, Usuario(id=7, activo=True), "X")
        assert error.value.status_code == 409
    db.rollback.assert_called_once()


@pytest.mark.parametrize(
    "index",
    [
        {"name": "idx", "unique": True, "column_names": ["key", "route"]},
        {
            "name": "idx",
            "unique": True,
            "column_names": ["key"],
            "dialect_options": {"postgresql_where": "route IS NOT NULL"},
        },
        {"name": "idx", "unique": False, "column_names": ["key"]},
    ],
)
def test_race_recovery_rejects_indexes_that_do_not_uniquely_cover_key(
    monkeypatch, index
):
    from sqlalchemy.exc import IntegrityError

    import app.api.endpoints.inventory_exits as exits

    db, _, _ = make_db(Item(id=1, activo=True, stock_actual=5))
    cause = Exception("duplicate")
    cause.pgcode = "23505"
    cause.diag = Mock(
        table_name="idempotency_keys", schema_name="public", constraint_name="idx"
    )
    db.flush.side_effect = IntegrityError("insert", {}, cause)
    inspector = Mock()
    inspector.get_indexes.return_value = [index]
    monkeypatch.setattr(exits, "inspect", lambda _conn: inspector)
    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(), db, Usuario(id=7, activo=True), "X")
    assert error.value.status_code == 500
    db.rollback.assert_called_once()


def test_race_recovery_metadata_failure_rolls_back(monkeypatch):
    from sqlalchemy.exc import IntegrityError

    import app.api.endpoints.inventory_exits as exits

    db, _, _ = make_db(Item(id=1, activo=True, stock_actual=5))
    cause = Exception("duplicate")
    cause.pgcode = "23505"
    cause.diag = Mock(
        table_name="idempotency_keys", schema_name="public", constraint_name="idx"
    )
    db.flush.side_effect = IntegrityError("insert", {}, cause)
    inspector = Mock()
    inspector.get_indexes.side_effect = SQLAlchemyError("catalog unavailable")
    monkeypatch.setattr(exits, "inspect", lambda _conn: inspector)
    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(), db, Usuario(id=7, activo=True), "X")
    assert error.value.status_code == 500
    assert db.rollback.call_count == 2


def test_expired_race_retry_is_bounded(monkeypatch):
    from sqlalchemy.exc import IntegrityError

    import app.api.endpoints.inventory_exits as exits

    db, _, _ = make_db(Item(id=1, activo=True, stock_actual=5))
    expired = IdempotencyKey(
        key="X", expires_at=datetime.now(UTC) - timedelta(seconds=1)
    )
    db.query(IdempotencyKey).filter().first.side_effect = [
        None,
        None,
        expired,
        expired,
        expired,
        expired,
    ]
    cause = Exception("duplicate")
    cause.pgcode = "23505"
    cause.diag = Mock(
        table_name="idempotency_keys", schema_name="public", constraint_name="idx"
    )
    db.flush.side_effect = IntegrityError("insert", {}, cause)
    inspector = Mock()
    inspector.get_indexes.return_value = [
        {"name": "idx", "unique": True, "column_names": ["key"]}
    ]
    monkeypatch.setattr(exits, "inspect", lambda _conn: inspector)
    with pytest.raises(HTTPException) as error:
        register_inventory_exit(entry(), db, Usuario(id=7, activo=True), "X")
    assert error.value.status_code == 500
    assert db.rollback.call_count == 2
    assert db.flush.call_count == 2
    assert inspector.get_indexes.call_count == 2
    assert db.query(IdempotencyKey).filter().first.call_count == 6
    db.commit.assert_not_called()
