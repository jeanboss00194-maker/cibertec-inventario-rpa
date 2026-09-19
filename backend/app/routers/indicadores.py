"""Endpoint de KPIs consumido por el dashboard (wireframe Sprint 4)."""

from flask import Blueprint, jsonify, request

from .. import crud
from ..auth import require_token
from ..database import session

bp = Blueprint("indicadores", __name__, url_prefix="/api")


@bp.route("/indicadores", methods=["GET"])
@require_token
def get_indicadores():
    with session() as conn:
        return jsonify(crud.get_indicadores(conn, sede=request.args.get("sede")))
