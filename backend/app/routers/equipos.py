"""
CRUD completo de equipos — respalda el módulo "Gestión de Inventario"
del dashboard (alta, edición y baja de un activo desde la interfaz),
además del listado con filtros ya usado por el panel principal.
"""

from flask import Blueprint, jsonify, request

from .. import crud
from ..auth import require_admin, require_token, usuario_actual
from ..database import session

bp = Blueprint("equipos", __name__, url_prefix="/api")

CAMPOS_REQUERIDOS_ALTA = {"id_espacio", "codigo_activo_case", "tipo_pc", "marca", "modelo"}


@bp.route("/equipos", methods=["GET"])
@require_token
def get_equipos():
    with session() as conn:
        return jsonify(
            crud.list_equipos(
                conn,
                sede=request.args.get("sede"),
                tipo_ambiente=request.args.get("tipo_ambiente"),
                tipo_pc=request.args.get("tipo_pc"),
                estado_case=request.args.get("estado_case"),
            )
        )


@bp.route("/equipos/<int:id_equipo>", methods=["GET"])
@require_token
def get_equipo(id_equipo: int):
    with session() as conn:
        equipo = crud.get_equipo_by_id(conn, id_equipo)
    if equipo is None:
        return jsonify({"error": "Equipo no encontrado"}), 404
    return jsonify(equipo)


@bp.route("/equipos", methods=["POST"])
@require_token
@require_admin
def post_equipo():
    data = request.get_json(silent=True) or {}
    faltantes = CAMPOS_REQUERIDOS_ALTA - data.keys()
    if faltantes:
        return jsonify({"error": f"Campos faltantes: {sorted(faltantes)}"}), 400
    with session() as conn:
        espacio = conn.execute(
            "SELECT 1 FROM espacio WHERE id_espacio = ?", (data["id_espacio"],)
        ).fetchone()
        if espacio is None:
            return jsonify({"error": f"No existe el ambiente id_espacio={data['id_espacio']}"}), 422
        existente = conn.execute(
            "SELECT 1 FROM equipo WHERE codigo_activo_case = ?", (data["codigo_activo_case"],)
        ).fetchone()
        if existente is not None:
            return jsonify({"error": f"El código de activo '{data['codigo_activo_case']}' ya existe"}), 409
        data.setdefault("service_tag_case", f"SN-{data['codigo_activo_case']}")
        data.setdefault("categoria", "Estándar")
        data.setdefault("anio_recepcion", 2026)
        data.setdefault("anios_uso", 0)
        equipo = crud.create_equipo(conn, data)
        crud.registrar_cambio(
            conn,
            accion="alta",
            entidad="equipo",
            id_entidad=equipo["id_equipo"],
            referencia=equipo["codigo_activo_case"],
            detalle=f"Alta de {equipo['tipo_pc']} {equipo['marca']} {equipo['modelo']}",
            **usuario_actual(),
        )
    return jsonify(equipo), 201


@bp.route("/equipos/<int:id_equipo>", methods=["PATCH"])
@require_token
@require_admin
def patch_equipo(id_equipo: int):
    data = request.get_json(silent=True) or {}
    with session() as conn:
        antes = crud.get_equipo_by_id(conn, id_equipo)
        if antes is None:
            return jsonify({"error": "Equipo no encontrado"}), 404
        equipo = crud.update_equipo(conn, id_equipo, data)
        campos_cambiados = sorted(
            campo for campo in crud.CAMPOS_EDITABLES_EQUIPO
            if campo in data and antes.get(campo) != equipo.get(campo)
        )
        if campos_cambiados:
            crud.registrar_cambio(
                conn,
                accion="edicion",
                entidad="equipo",
                id_entidad=id_equipo,
                referencia=equipo["codigo_activo_case"],
                detalle=f"Campos modificados: {', '.join(campos_cambiados)}",
                **usuario_actual(),
            )
    return jsonify(equipo)


@bp.route("/equipos/<int:id_equipo>", methods=["DELETE"])
@require_token
@require_admin
def delete_equipo(id_equipo: int):
    with session() as conn:
        equipo = crud.get_equipo_by_id(conn, id_equipo)
        eliminado = crud.delete_equipo(conn, id_equipo)
        if eliminado:
            crud.registrar_cambio(
                conn,
                accion="baja",
                entidad="equipo",
                id_entidad=id_equipo,
                referencia=equipo["codigo_activo_case"] if equipo else None,
                detalle="Baja del activo (incluye sus conciliaciones y alertas asociadas)",
                **usuario_actual(),
            )
    if not eliminado:
        return jsonify({"error": "Equipo no encontrado"}), 404
    return jsonify({"eliminado": True, "id_equipo": id_equipo})
