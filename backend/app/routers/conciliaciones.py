"""
Endpoint central del proceso RPA de conciliación trimestral.

"""

from flask import Blueprint, jsonify, request

from .. import crud
from ..auth import require_token
from ..database import session

bp = Blueprint("conciliaciones", __name__, url_prefix="/api")

CAMPOS_REQUERIDOS = {
    "id_equipo",
    "id_asistente",
    "trimestre",
    "cantidad_esperada",
    "cantidad_encontrada",
}


@bp.route("/conciliaciones", methods=["POST"])
@require_token
def post_conciliacion():
    data = request.get_json(silent=True) or {}
    faltantes = CAMPOS_REQUERIDOS - data.keys()
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {sorted(faltantes)}"}), 400
    if data["trimestre"] not in ("ene", "abr", "jul", "oct"):
        return jsonify({"error": "trimestre debe ser uno de: ene, abr, jul, oct"}), 400

    with session() as conn:
        equipo = crud.get_equipo_by_id(conn, data["id_equipo"])
        if equipo is None:
            # 422: la petición está bien formada pero hace referencia a una
            # entidad que no existe en el registro maestro (CP-06, Sprint 5).
            return jsonify({"error": f"No existe equipo con id_equipo={data['id_equipo']}"}), 422
        asistente = conn.execute(
            "SELECT 1 FROM asistente WHERE id_asistente = ?", (data["id_asistente"],)
        ).fetchone()
        if asistente is None:
            return jsonify({"error": f"No existe asistente con id_asistente={data['id_asistente']}"}), 422
        resultado = crud.create_conciliacion(conn, data)
    return jsonify(resultado), 201


@bp.route("/conciliaciones", methods=["GET"])
@require_token
def get_conciliaciones():
    with session() as conn:
        return jsonify(
            crud.list_conciliaciones(
                conn, sede=request.args.get("sede"), trimestre=request.args.get("trimestre")
            )
        )
