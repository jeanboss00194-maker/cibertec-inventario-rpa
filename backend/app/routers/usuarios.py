"""
Endpoints de cuentas de acceso al sistema (`usuario_sistema`).

"""

from flask import Blueprint, jsonify, request

from .. import crud
from ..auth import require_admin, require_token
from ..database import session

bp = Blueprint("usuarios", __name__, url_prefix="/api")


@bp.route("/auth/login", methods=["POST"])
@require_token
def login():
    datos = request.get_json(silent=True) or {}
    usuario = (datos.get("usuario") or "").strip()
    clave = datos.get("clave") or ""
    if not usuario or not clave:
        return jsonify({"error": "Usuario y contraseña son obligatorios."}), 400

    with session() as conn:
        cuenta = crud.validar_login(conn, usuario, clave)

    if cuenta is None:
        return jsonify({"error": "Usuario o contraseña incorrectos."}), 401
    return jsonify(cuenta)


@bp.route("/usuarios", methods=["GET"])
@require_token
@require_admin
def get_usuarios():
    with session() as conn:
        return jsonify(crud.list_usuarios(conn))
