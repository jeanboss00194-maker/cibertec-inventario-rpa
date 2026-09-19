"""
Endpoints del panel "Automatización RPA" del dashboard: permiten
disparar, desde la interfaz web, la misma lógica de conciliación que
ejecuta rpa_bot/bot_conciliacion.py desde una terminal.
"""

import csv
import io

from flask import Blueprint, jsonify, request

from .. import crud, rpa_engine
from ..auth import require_admin, require_token, usuario_actual
from ..database import session

bp = Blueprint("rpa", __name__, url_prefix="/api/rpa")


@bp.route("/generar-conteo", methods=["POST"])
@require_token
@require_admin
def generar_conteo():
    trimestre = (request.get_json(silent=True) or {}).get("trimestre", "oct")
    with session() as conn:
        filas = rpa_engine.generar_conteo_ejemplo(conn, trimestre=trimestre)
    n_disc = sum(1 for r in filas if r["cantidad_encontrada"] == 0 or r["estado_reportado"] == "Inoperativo")
    return jsonify({
        "total": len(filas),
        "con_discrepancia": n_disc,
        "archivo": str(rpa_engine.ARCHIVO_CONTEO.name),
        "preview": filas[:5],
    })


@bp.route("/ejecutar", methods=["POST"])
@require_token
@require_admin
def ejecutar():
    trimestre = request.form.get("trimestre") or (request.get_json(silent=True) or {}).get("trimestre", "oct")

    archivo = request.files.get("archivo")
    if archivo is not None:
        contenido = archivo.stream.read().decode("utf-8-sig")
        filas = list(csv.DictReader(io.StringIO(contenido)))
    else:
        try:
            filas = rpa_engine.leer_conteo_desde_archivo()
        except FileNotFoundError as e:
            return jsonify({"error": str(e)}), 400

    if not filas:
        return jsonify({"error": "El archivo de conteo no contiene registros."}), 400

    with session() as conn:
        resumen = rpa_engine.procesar_conteo_fisico(conn, filas, trimestre=trimestre)
        crud.registrar_cambio(
            conn,
            accion="ejecucion",
            entidad="rpa",
            referencia=f"trimestre {trimestre}",
            detalle=(
                f"Bot de conciliación ejecutado desde el dashboard: {resumen['conciliados']} conciliados, "
                f"{resumen['con_discrepancia']} con discrepancia, {resumen['alertas_generadas']} alertas generadas"
                + (f", {len(resumen['errores'])} error(es) controlado(s)" if resumen["errores"] else "")
            ),
            **usuario_actual(),
        )
    return jsonify(resumen)
