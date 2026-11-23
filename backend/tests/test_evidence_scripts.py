"""Exercise evidence generators with local fixtures and no live services."""

import json
import sys
from datetime import UTC, datetime
from types import SimpleNamespace

import httpx
import pytest

from scripts import generate_tc_inv15_evidence as inv15
from scripts import generate_tc_inv16_evidence as inv16


def response(method, url, status, *, body=None, text=None):
    request = httpx.Request(method, url)
    if body is not None:
        return httpx.Response(status, json=body, request=request)
    return httpx.Response(status, text=text or "", request=request)


def test_inv15_login_rejects_missing_credentials_without_http(monkeypatch):
    monkeypatch.delenv("TC_INV15_EMAIL", raising=False)
    monkeypatch.delenv("TC_INV15_PASSWORD", raising=False)
    monkeypatch.setattr(
        inv15.httpx, "post", lambda *args, **kwargs: pytest.fail("HTTP called")
    )
    with pytest.raises(RuntimeError, match="TC_INV15_EMAIL"):
        inv15.login("http://127.0.0.1:1")


def test_inv15_login_checks_http_status_and_token_shape(monkeypatch):
    monkeypatch.setenv("TC_INV15_EMAIL", "fixture@example.invalid")
    monkeypatch.setenv("TC_INV15_PASSWORD", "fixture-only")
    url = "http://127.0.0.1:1/api/auth/login"
    observed = []

    def fake_post(request_url, **kwargs):
        observed.append((request_url, kwargs))
        return response(
            "POST", request_url, 200, body={"access_token": "fixture-token"}
        )

    monkeypatch.setattr(inv15.httpx, "post", fake_post)
    assert inv15.login("http://127.0.0.1:1") == "fixture-token"
    assert observed[0][0] == url
    assert observed[0][1]["json"] == {
        "email": "fixture@example.invalid",
        "password": "fixture-only",
    }

    monkeypatch.setattr(
        inv15.httpx,
        "post",
        lambda *a, **k: response("POST", url, 200, body={"access_token": ""}),
    )
    with pytest.raises(RuntimeError, match="access_token"):
        inv15.login("http://127.0.0.1:1")

    monkeypatch.setattr(
        inv15.httpx,
        "post",
        lambda *a, **k: response("POST", url, 401, body={"detail": "invalid"}),
    )
    with pytest.raises(httpx.HTTPStatusError):
        inv15.login("http://127.0.0.1:1")


def test_inv15_post_movement_preserves_status_and_handles_non_json(monkeypatch):
    observed = []

    def fake_post(url, **kwargs):
        observed.append((url, kwargs))
        status = 201 if len(observed) == 1 else 409
        return response(
            "POST",
            url,
            status,
            body={"id": 4} if status == 201 else None,
            text="conflict",
        )

    monkeypatch.setattr(inv15.httpx, "post", fake_post)
    args = (
        "http://127.0.0.1:1",
        "fixture-token",
        "/api/v1/inventory/entries",
        {"cantidad": 4},
        "fixture-key",
    )
    assert inv15.post_movement(*args) == (201, {"id": 4})
    assert inv15.post_movement(*args) == (409, {"detail": "conflict"})
    assert observed[0][1]["headers"] == {
        "Authorization": "Bearer fixture-token",
        "Idempotency-Key": "fixture-key",
    }
    assert observed[0][1]["json"] == {"cantidad": 4}


def test_inv15_html_escapes_untrusted_report_fields():
    report = {
        "pass": False,
        "case_id": "<script>",
        "result": "<bad>",
        "timestamp": "2026-11-22",
        "database_host": "127.0.0.1",
        "product_id": 1,
        "expected": "<unsafe>",
        "requests": [
            {"name": "<request>", "status": 409, "response": {"detail": "<bad>"}}
        ],
        "database_movements": [
            {
                "tipo": "<entry>",
                "cantidad": 4,
                "stock_anterior": 5,
                "stock_resultante": 9,
                "fecha": "2026-11-22",
                "notas": "<note>",
            }
        ],
    }
    page = inv15.build_html(report)
    assert 'class="status fail"' in page
    assert "&lt;script&gt;" in page and "<script>" not in page
    assert "&lt;request&gt;" in page and "&lt;unsafe&gt;" in page
    assert "&lt;NOTE&gt;" not in page and "&lt;note&gt;" in page


@pytest.mark.parametrize("exit_status,expected", [(201, 0), (409, 1)])
def test_inv15_main_records_entry_and_exit_with_mocked_db(
    monkeypatch, tmp_path, exit_status, expected
):
    monkeypatch.setattr(inv15, "ROOT", tmp_path)
    monkeypatch.setattr(inv15, "login", lambda url: "fixture-token")
    monkeypatch.setattr(
        inv15.settings, "DATABASE_URL", "postgresql://127.0.0.1:1/fixture"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["inv15", "--product-id", "8", "--entry-quantity", "4", "--exit-quantity", "2"],
    )
    calls = []

    def fake_post(url, token, route, payload, key):
        calls.append((route, payload, key))
        return (201 if len(calls) == 1 else exit_status), {"id": len(calls)}

    monkeypatch.setattr(inv15, "post_movement", fake_post)
    movements = (
        [
            SimpleNamespace(
                tipo="entrada",
                cantidad=4,
                fecha=datetime(2026, 11, 22, tzinfo=UTC),
                notas="Entrada",
                stock_anterior=5,
                stock_resultante=9,
            ),
            SimpleNamespace(
                tipo="salida",
                cantidad=2,
                fecha=datetime(2026, 11, 22, tzinfo=UTC),
                notas="Salida",
                stock_anterior=9,
                stock_resultante=7,
            ),
        ]
        if exit_status == 201
        else []
    )
    closed = []

    class FakeSession:
        def scalars(self, statement):
            assert statement is not None
            return SimpleNamespace(all=lambda: movements)

        def close(self):
            closed.append(True)

    monkeypatch.setattr(inv15, "SessionLocal", FakeSession)
    assert inv15.main() == expected
    assert (
        len(calls) == 2
        and calls[0][0].endswith("/entries")
        and calls[1][0].endswith("/exits")
    )
    assert calls[0][1]["cantidad"] == 4 and calls[1][1]["cantidad"] == 2
    assert closed == [True]
    report = json.loads(
        (tmp_path / "evidence" / "TC-INV-15.json").read_text(encoding="utf-8")
    )
    assert report["pass"] is (expected == 0)
    assert len(report["database_movements"]) == len(movements)
    assert (tmp_path / "evidence" / "TC-INV-15.html").is_file()


def test_inv16_serializes_movement_and_missing_date():
    movement = SimpleNamespace(
        id=2,
        tipo="salida",
        cantidad=4,
        fecha=None,
        stock_anterior=5,
        stock_resultante=1,
        motivo="merma",
        notas=None,
    )
    assert inv16.serialize(movement) == {
        "id": 2,
        "tipo": "salida",
        "cantidad": 4,
        "fecha": None,
        "stock_anterior": 5,
        "stock_resultante": 1,
        "motivo": "merma",
        "notas": None,
    }
    movement.fecha = datetime(2026, 11, 22, tzinfo=UTC)
    assert inv16.serialize(movement)["fecha"].startswith("2026-11-22")


def test_inv16_html_escapes_range_and_movement_values():
    report = {
        "pass": True,
        "case_id": "<script>",
        "timestamp": "2026-11-22",
        "database_host": "127.0.0.1",
        "product_id": 8,
        "range_query": "<range>",
        "empty_query": "2030-01",
        "range_movements": [
            {
                "fecha": "2026-11-22",
                "tipo": "<salida>",
                "cantidad": 4,
                "stock_anterior": 5,
                "stock_resultante": 1,
            }
        ],
        "empty_movements": [],
    }
    page = inv16.build_html(report)
    assert 'class="status pass"' in page
    assert "&lt;script&gt;" in page and "<script>" not in page
    assert "&lt;salida&gt;" in page and "&lt;range&gt;" in page


@pytest.mark.parametrize(
    "rows,expected",
    [
        (
            [
                {
                    "fecha": "2026-11-22T12:00:00Z",
                    "tipo": "salida",
                    "cantidad": 4,
                    "stock_anterior": 5,
                    "stock_resultante": 1,
                }
            ],
            0,
        ),
        ([], 1),
    ],
)
def test_inv16_main_records_filtered_and_empty_ranges(
    monkeypatch, tmp_path, rows, expected
):
    monkeypatch.setattr(inv16, "ROOT", tmp_path)
    monkeypatch.setattr(
        inv16.settings, "DATABASE_URL", "postgresql://127.0.0.1:1/fixture"
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "inv16",
            "--product-id",
            "8",
            "--from-date",
            "2026-11-21",
            "--to-date",
            "2026-11-22",
        ],
    )
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return response("GET", url, 200, body=rows if len(calls) == 1 else [])

    monkeypatch.setattr(inv16.httpx, "get", fake_get)
    assert inv16.main() == expected
    assert len(calls) == 2
    assert calls[0][1]["params"] == {"from_date": "2026-11-21", "to_date": "2026-11-22"}
    assert calls[1][1]["params"] == {"from_date": "2030-01-01", "to_date": "2030-01-31"}
    report = json.loads(
        (tmp_path / "evidence" / "TC-INV-16.json").read_text(encoding="utf-8")
    )
    assert report["pass"] is (expected == 0)
    assert report["range_movements"] == rows and report["empty_movements"] == []
    assert (tmp_path / "evidence" / "TC-INV-16.html").is_file()


def test_inv16_main_raises_on_http_error_without_writing_evidence(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(inv16, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["inv16", "--product-id", "8"])
    url = "http://127.0.0.1:8000/api/v1/inventory/items/8/movements"
    monkeypatch.setattr(
        inv16.httpx,
        "get",
        lambda *a, **k: response("GET", url, 503, body={"detail": "fixture"}),
    )
    with pytest.raises(httpx.HTTPStatusError):
        inv16.main()
    assert not (tmp_path / "evidence").exists()
