"""
Endpoint de priorización de renovación — resultado del motor analítico
CRISP-DM (analitica/motor_priorizacion.py), Sprint 3.
"""

from flask import Blueprint, jsonify, request

from .. import crud
from ..auth import require_token, usuario_actual
from ..database import session

bp = Blueprint("renovacion", __name__, url_prefix="/api")


@bp.route("/priorizacion-renovacion", methods=["POST"])
@require_token
def post_priorizacion():
    data = request.get_json(silent=True) or {}
    resultados = data.get("resultados")
    if not isinstance(resultados, list) or not resultados:
        return jsonify({"error": "Se espera { \"resultados\": [ {codigo_activo_case, "
                                  "prioridad_renovacion, score_renovacion}, ... ] }"}), 400
    with session() as conn:
        actualizados = crud.bulk_update_priorizacion(conn, resultados)
        crud.registrar_cambio(
            conn,
            accion="ejecucion",
            entidad="priorizacion",
            detalle=f"Actualización de priorización de renovación: {actualizados} equipo(s) actualizado(s)",
            **usuario_actual(),
        )
    return jsonify({"equipos_actualizados": actualizados}), 200


@bp.route("/priorizacion-renovacion", methods=["GET"])
@require_token
def get_priorizacion():
    top = request.args.get("top", default=50, type=int)
    with session() as conn:
        return jsonify(crud.list_priorizacion(conn, sede=request.args.get("sede"), top=top))
