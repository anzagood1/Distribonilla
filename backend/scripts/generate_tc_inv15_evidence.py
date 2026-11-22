from __future__ import annotations

import argparse
import html
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.inventory import MovimientoInventario  # noqa: E402


def login(api_url: str) -> str:
    email = os.getenv("TC_INV15_EMAIL")
    password = os.getenv("TC_INV15_PASSWORD")
    if not email or not password:
        raise RuntimeError(
            "Configure TC_INV15_EMAIL y TC_INV15_PASSWORD antes de ejecutar la evidencia."
        )

    response = httpx.post(
        f"{api_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=20,
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    if not isinstance(token, str) or not token:
        raise RuntimeError("La autenticación no devolvió un access_token válido.")
    return token


def post_movement(
    api_url: str,
    token: str,
    route: str,
    payload: dict,
    idempotency_key: str,
) -> tuple[int, dict]:
    response = httpx.post(
        f"{api_url}{route}",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": idempotency_key,
        },
        timeout=20,
    )
    try:
        body = response.json()
    except json.JSONDecodeError:
        body = {"detail": response.text}
    return response.status_code, body


def build_html(report: dict) -> str:
    status = "PASS" if report["pass"] else "FAIL"
    status_class = "pass" if report["pass"] else "fail"
    movements = "".join(
        f"""
        <article class="movement">
          <strong>{html.escape(str(movement["tipo"]).upper())}</strong>
          <dl>
            <dt>Cantidad</dt><dd>{html.escape(str(movement["cantidad"]))}</dd>
            <dt>Stock anterior</dt><dd>{html.escape(str(movement["stock_anterior"]))}</dd>
            <dt>Stock resultante</dt><dd>{html.escape(str(movement["stock_resultante"]))}</dd>
            <dt>Fecha</dt><dd>{html.escape(str(movement["fecha"]))}</dd>
            <dt>Notas</dt><dd>{html.escape(str(movement["notas"]))}</dd>
          </dl>
        </article>
        """
        for movement in report["database_movements"]
    )
    requests_html = "".join(
        f"""
        <article class="request">
          <h3>{html.escape(request["name"])}</h3>
          <p>HTTP {request["status"]}</p>
          <pre>{html.escape(json.dumps(request, ensure_ascii=False, indent=2))}</pre>
        </article>
        """
        for request in report["requests"]
    )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(report["case_id"])}</title>
  <style>
    body {{ margin: 0; background: #eef2f7; color: #172033; font-family: Arial, sans-serif; }}
    main {{ max-width: 1100px; margin: 24px auto; }}
    header {{ display: flex; justify-content: space-between; align-items: center; padding: 24px; border-radius: 12px; background: #123e66; color: white; }}
    .status {{ padding: 8px 12px; border-radius: 999px; font-weight: 700; }}
    .pass {{ background: #1b7f58; }} .fail {{ background: #b42318; }}
    .card {{ margin-top: 18px; border-radius: 10px; padding: 22px; background: white; box-shadow: 0 4px 16px #0001; }}
    .info {{ background: #eaf6fb; border-left: 4px solid #138aa5; }}
    .movements, .requests {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .movement, .request {{ border: 1px solid #dfe4eb; border-radius: 9px; padding: 16px; }}
    dl {{ display: grid; grid-template-columns: 120px 1fr; gap: 8px; margin: 12px 0 0; }}
    dt {{ color: #667085; }} dd {{ margin: 0; font-weight: 700; }}
    pre {{ overflow: auto; max-height: 420px; background: #f7f8fa; padding: 12px; }}
    @media (max-width: 700px) {{ main {{ margin: 12px; }} .movements, .requests {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>{html.escape(report["case_id"])}</h1>
      <p>Evidencia registrada — {html.escape(report["result"])}</p>
    </div>
    <span class="status {status_class}">{status} · LOCAL</span>
  </header>
  <section class="card info">
    <strong>Información de evidencia</strong>
    <p>Fecha: {html.escape(report["timestamp"])}</p>
    <p>Base: {html.escape(report["database_host"])}</p>
    <p>Producto: {html.escape(str(report["product_id"]))}</p>
  </section>
  <section class="card">
    <h2>Resultado esperado</h2>
    <p>{html.escape(report["expected"])}</p>
  </section>
  <section class="card">
    <h2>Peticiones y respuestas reales</h2>
    <div class="requests">{requests_html}</div>
  </section>
  <section class="card">
    <h2>Historial persistido</h2>
    <div class="movements">{movements}</div>
  </section>
</main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--product-id", type=int, required=True)
    parser.add_argument("--entry-quantity", type=int, default=5)
    parser.add_argument("--exit-quantity", type=int, default=2)
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    token = login(api_url)
    run_id = uuid.uuid4().hex[:8]
    entry_note = f"Entrada TC-INV-15-{run_id}"
    exit_note = f"Salida TC-INV-15-{run_id}"

    entry_status, entry_body = post_movement(
        api_url,
        token,
        "/api/v1/inventory/entries",
        {
            "producto_id": args.product_id,
            "cantidad": args.entry_quantity,
            "motivo": "Compra de prueba",
            "notas": entry_note,
        },
        f"tc-inv-15-entry-{run_id}",
    )
    exit_status, exit_body = post_movement(
        api_url,
        token,
        "/api/v1/inventory/exits",
        {
            "producto_id": args.product_id,
            "cantidad": args.exit_quantity,
            "motivo": "ajuste",
            "notas": exit_note,
        },
        f"tc-inv-15-exit-{run_id}",
    )

    db = SessionLocal()
    try:
        movements = db.scalars(
            select(MovimientoInventario)
            .where(
                MovimientoInventario.producto_id == args.product_id,
                MovimientoInventario.notas.in_([entry_note, exit_note]),
            )
            .order_by(MovimientoInventario.fecha.asc())
        ).all()
        database_movements = [
            {
                "tipo": movement.tipo,
                "cantidad": movement.cantidad,
                "fecha": movement.fecha.isoformat() if movement.fecha else None,
                "notas": movement.notas,
                "stock_anterior": movement.stock_anterior,
                "stock_resultante": movement.stock_resultante,
            }
            for movement in movements
        ]
    finally:
        db.close()

    types = [movement["tipo"] for movement in database_movements]
    passed = (
        entry_status == 201
        and exit_status == 201
        and types == ["entrada", "salida"]
        and len(database_movements) == 2
    )
    timestamp = datetime.now(timezone.utc).isoformat()

    report = {
        "case_id": "TC-INV-15",
        "group": "GRUPO5-14",
        "hu": "HU13",
        "requirement": "R27",
        "result": "Sprint 2",
        "timestamp": timestamp,
        "database_host": settings.DATABASE_URL.split("@")[-1].split("/")[0],
        "product_id": args.product_id,
        "pass": passed,
        "expected": (
            "Ambos movimientos deben persistir con fechas, cantidades, tipo "
            "y stock anterior/resultante consistentes."
        ),
        "requests": [
            {
                "name": "Solicitud 1 - Entrada",
                "status": entry_status,
                "route": "/api/v1/inventory/entries",
                "method": "POST",
                "response": entry_body,
            },
            {
                "name": "Solicitud 2 - Salida",
                "status": exit_status,
                "route": "/api/v1/inventory/exits",
                "method": "POST",
                "response": exit_body,
            },
        ],
        "database_movements": database_movements,
    }

    evidence_dir = ROOT / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    json_path = evidence_dir / "TC-INV-15.json"
    html_path = evidence_dir / "TC-INV-15.html"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    html_path.write_text(build_html(report), encoding="utf-8")

    print(json.dumps({"pass": passed, "json": str(json_path), "html": str(html_path)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
