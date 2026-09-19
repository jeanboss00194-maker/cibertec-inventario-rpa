"""Endpoints de catálogo: sedes, espacios y asistentes."""

from flask import Blueprint, jsonify, request

from .. import crud
from ..auth import require_token
from ..database import session

bp = Blueprint("sedes", __name__, url_prefix="/api")


@bp.route("/sedes", methods=["GET"])
@require_token
def get_sedes():
    with session() as conn:
        return jsonify(crud.list_sedes(conn))


@bp.route("/espacios", methods=["GET"])
@require_token
def get_espacios():
    id_sede = request.args.get("id_sede", type=int)
    with session() as conn:
        return jsonify(crud.list_espacios(conn, id_sede=id_sede))


@bp.route("/asistentes", methods=["GET"])
@require_token
def get_asistentes():
    with session() as conn:
        return jsonify(crud.list_asistentes(conn))


@bp.route("/actividad-reciente", methods=["GET"])
@require_token
def get_actividad_reciente():
    limite = request.args.get("limite", default=8, type=int)
    with session() as conn:
        return jsonify(crud.get_actividad_reciente(conn, limite=limite))
