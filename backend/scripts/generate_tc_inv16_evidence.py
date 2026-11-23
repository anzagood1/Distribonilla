from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import settings  # noqa: E402
from app.models.inventory import MovimientoInventario  # noqa: E402


def build_html(report: dict) -> str:
    status_class = "pass" if report["pass"] else "fail"
    status = "PASS" if report["pass"] else "FAIL"

    rows = "".join(
        f"""
        <tr>
          <td>{html.escape(str(m["fecha"]))}</td>
          <td><span class="badge {html.escape(m["tipo"])}">{html.escape(m["tipo"].upper())}</span></td>
          <td>{html.escape(str(m["cantidad"]))}</td>
          <td>{html.escape(str(m["stock_anterior"]))}</td>
          <td>{html.escape(str(m["stock_resultante"]))}</td>
        </tr>
        """
        for m in report["range_movements"]
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
    .queries {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .query {{ border: 1px solid #dfe4eb; border-radius: 9px; padding: 16px; background: #fafbfc; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px; border-bottom: 1px solid #e7eaf0; text-align: left; }}
    th {{ color: #667085; font-size: 12px; }}
    .badge {{ display: inline-block; border-radius: 999px; padding: 5px 8px; font-size: 12px; font-weight: 700; }}
    .entrada {{ color: #177a52; background: #eaf7f1; }}
    .salida {{ color: #9a6712; background: #fff4da; }}
    @media (max-width: 700px) {{ main {{ margin: 12px; }} .queries {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>{html.escape(report["case_id"])}</h1>
      <p>Evidencia registrada — Sprint 2</p>
    </div>
    <span class="status {status_class}">{status} · LOCAL</span>
  </header>
  <section class="card info">
    <strong>Información de evidencia</strong>
    <p>Fecha de ejecución: {html.escape(report["timestamp"])}</p>
    <p>Base: {html.escape(report["database_host"])}</p>
    <p>Producto consultado: {report["product_id"]}</p>
  </section>
  <section class="card">
    <h2>Resultado esperado</h2>
    <p>Solo aparecen movimientos del rango; el período vacío informa sin resultados.</p>
  </section>
  <section class="card">
    <h2>Consultas aplicadas</h2>
    <div class="queries">
      <article class="query">
        <h3>Período con registros</h3>
        <p>{html.escape(report["range_query"])}</p>
        <strong>{len(report["range_movements"])} movimiento(s)</strong>
        <pre>{html.escape(json.dumps(report["range_movements"], ensure_ascii=False, indent=2))}</pre>
      </article>
      <article class="query">
        <h3>Período vacío</h3>
        <p>{html.escape(report["empty_query"])}</p>
        <strong>{len(report["empty_movements"])} movimiento(s)</strong>
        <pre>[]</pre>
      </article>
    </div>
  </section>
  <section class="card">
    <h2>Movimientos del período con registros</h2>
    <table>
      <thead><tr><th>Fecha</th><th>Tipo</th><th>Cantidad</th><th>Stock anterior</th><th>Stock resultante</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>
</main>
</body>
</html>
"""


def serialize(movement: MovimientoInventario) -> dict:
    return {
        "id": movement.id,
        "tipo": movement.tipo,
        "cantidad": movement.cantidad,
        "fecha": movement.fecha.isoformat() if movement.fecha else None,
        "stock_anterior": movement.stock_anterior,
        "stock_resultante": movement.stock_resultante,
        "motivo": movement.motivo,
        "notas": movement.notas,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--product-id", type=int, required=True)
    parser.add_argument("--from-date", default="2026-11-21")
    parser.add_argument("--to-date", default="2026-11-22")
    args = parser.parse_args()

    api_url = args.api_url.rstrip("/")
    range_url = f"{api_url}/api/v1/inventory/items/{args.product_id}/movements"
    range_response = httpx.get(
        range_url,
        params={"from_date": args.from_date, "to_date": args.to_date},
        timeout=20,
    )
    empty_response = httpx.get(
        range_url,
        params={"from_date": "2030-01-01", "to_date": "2030-01-31"},
        timeout=20,
    )
    range_response.raise_for_status()
    empty_response.raise_for_status()
    range_movements = range_response.json()
    empty_movements = empty_response.json()

    passed = (
        len(range_movements) > 0
        and len(empty_movements) == 0
        and all(
            args.from_date <= movement["fecha"][:10] <= args.to_date
            for movement in range_movements
        )
    )

    report = {
        "case_id": "TC-INV-16",
        "group": "GRUPO5-14",
        "hu": "HU13",
        "requirement": "R28",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database_host": settings.DATABASE_URL.split("@")[-1].split("/")[0],
        "product_id": args.product_id,
        "range_query": f"{args.from_date} a {args.to_date}",
        "empty_query": "2030-01-01 a 2030-01-31",
        "range_movements": range_movements,
        "empty_movements": empty_movements,
        "pass": passed,
    }

    evidence_dir = ROOT / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    json_path = evidence_dir / "TC-INV-16.json"
    html_path = evidence_dir / "TC-INV-16.html"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    html_path.write_text(build_html(report), encoding="utf-8")
    print(json.dumps({"pass": passed, "json": str(json_path), "html": str(html_path)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
