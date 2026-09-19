"""
Endpoint de la bitácora de cambios (auditoría).

Expone en solo lectura la tabla `bitacora_cambio`: quién (cuenta de
`usuario_sistema`) realizó cada alta/edición/baja de un equipo,
atención de una alerta, o ejecución del bot RPA / motor de
priorización, y cuándo. Los registros los produce
`backend/app/crud.py::registrar_cambio`, llamado desde los routers de
escritura correspondientes inmediatamente después de confirmar la
operación de negocio.

"""

from flask import Blueprint, jsonify, request

from .. import crud
from ..auth import require_admin, require_token
from ..database import session

bp = Blueprint("bitacora", __name__, url_prefix="/api")


@bp.route("/bitacora", methods=["GET"])
@require_token
@require_admin
def get_bitacora():
    limite = request.args.get("limite", default=200, type=int)
    with session() as conn:
        return jsonify(
            crud.list_bitacora(
                conn,
                entidad=request.args.get("entidad"),
                usuario=request.args.get("usuario"),
                limite=limite,
            )
        )
