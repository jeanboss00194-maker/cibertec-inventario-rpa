"""
Endpoint del panel "Dashboard Inteligente": dispara, desde la
interfaz, el mismo motor CRISP-DM que analitica/motor_priorizacion.py
ejecuta desde una terminal — reutilizando su función pura
`calcular_prioridad` (índice compuesto + KMeans de validación) sobre
los datos ya cargados en la base de datos, sin pasar por HTTP.
"""

import sys
from pathlib import Path

import pandas as pd
from flask import Blueprint, jsonify

from .. import crud
from ..auth import require_admin, require_token, usuario_actual
from ..database import session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from analitica.motor_priorizacion import calcular_prioridad  # noqa: E402

bp = Blueprint("analitica", __name__, url_prefix="/api/analitica")


@bp.route("/ejecutar", methods=["POST"])
@require_token
@require_admin
def ejecutar():
    with session() as conn:
        equipos = crud.list_equipos(conn)
        alertas = crud.list_alertas(conn)

    if not equipos:
        return jsonify({"error": "No hay equipos cargados. Ejecute backend/seed.py primero."}), 400

    df = pd.DataFrame(equipos)
    incidencias: dict[str, int] = {}
    for a in alertas:
        incidencias[a["codigo_activo_case"]] = incidencias.get(a["codigo_activo_case"], 0) + 1
    df["n_incidencias"] = df["codigo_activo_case"].map(incidencias).fillna(0).astype(int)

    resultado = calcular_prioridad(df)

    with session() as conn:
        actualizados = crud.bulk_update_priorizacion(
            conn,
            resultado[["codigo_activo_case", "prioridad_renovacion", "score_renovacion"]].to_dict(orient="records"),
        )
        crud.registrar_cambio(
            conn,
            accion="ejecucion",
            entidad="priorizacion",
            detalle=f"Motor CRISP-DM ejecutado desde el dashboard: {actualizados} equipo(s) actualizado(s)",
            **usuario_actual(),
        )

    distribucion = resultado["prioridad_renovacion"].value_counts().to_dict()
    top10 = (
        resultado.sort_values("score_renovacion", ascending=False)
        .head(10)[["codigo_activo_case", "nombre_sede", "tipo_pc", "anios_uso",
                    "estado_case", "score_renovacion", "prioridad_renovacion"]]
        .to_dict(orient="records")
    )

    return jsonify({
        "equipos_actualizados": actualizados,
        "distribucion_prioridad": distribucion,
        "top10": top10,
    })
