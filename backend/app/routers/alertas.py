"""Endpoints de alertas generadas por el proceso de conciliación."""

from flask import Blueprint, jsonify, request

from .. import crud
from ..auth import require_token, usuario_actual
from ..database import session

bp = Blueprint("alertas", __name__, url_prefix="/api")


@bp.route("/alertas", methods=["GET"])
@require_token
def get_alertas():
    with session() as conn:
        return jsonify(crud.list_alertas(conn, estado=request.args.get("estado")))


@bp.route("/alertas/<int:id_alerta>/atender", methods=["POST"])
@require_token
def atender_alerta(id_alerta: int):
    with session() as conn:
        resultado = crud.atender_alerta(conn, id_alerta)
        if resultado is not None:
            equipo = crud.get_equipo_by_id(conn, resultado["id_equipo"])
            crud.registrar_cambio(
                conn,
                accion="atencion",
                entidad="alerta",
                id_entidad=id_alerta,
                referencia=equipo["codigo_activo_case"] if equipo else None,
                detalle=f"Alerta de tipo '{resultado['tipo_alerta']}' marcada como atendida",
                **usuario_actual(),
            )
    if resultado is None:
        return jsonify({"error": "Alerta no encontrada"}), 404
    return jsonify(resultado)
