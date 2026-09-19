"""
Aplicación Flask — Sistema de Sistematización del Inventario de Equipos
de Cómputo (CIBERTEC)
==========================================================================

Ejecución local:
    python -m backend.app.main
o bien, usando el script de conveniencia en la raíz del proyecto:
    python run.py
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from .database import init_db, DB_PATH
from .routers import (
    alertas,
    analitica,
    bitacora,
    conciliaciones,
    equipos,
    indicadores,
    renovacion,
    rpa,
    sedes,
    usuarios,
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)

    # Aplica el esquema (CREATE TABLE/INDEX IF NOT EXISTS) en cada arranque,
    # exista o no ya la base de datos: es idempotente y no destruye datos
    # existentes (para reiniciar de cero se usa backend/seed.py), pero SÍ
    # crea sobre una base de datos ya sembrada cualquier tabla añadida
    # después — como `bitacora_cambio` — que aún no exista en el archivo
    # .db que se venía usando.
    init_db(reset=False)

    app.register_blueprint(sedes.bp)
    app.register_blueprint(equipos.bp)
    app.register_blueprint(conciliaciones.bp)
    app.register_blueprint(alertas.bp)
    app.register_blueprint(indicadores.bp)
    app.register_blueprint(renovacion.bp)
    app.register_blueprint(rpa.bp)
    app.register_blueprint(analitica.bp)
    app.register_blueprint(usuarios.bp)
    app.register_blueprint(bitacora.bp)

    @app.route("/api/salud", methods=["GET"])
    def salud():
        return jsonify({"estado": "ok", "servicio": "cibertec-inventario-api"})

    # --- Front-end estático (dashboard) -----------------------------
    @app.route("/", defaults={"ruta": "index.html"})
    @app.route("/<path:ruta>")
    def frontend(ruta: str):
        archivo = FRONTEND_DIR / ruta
        if not archivo.exists() or archivo.is_dir():
            ruta = "index.html"
        return send_from_directory(FRONTEND_DIR, ruta)

    return app


app = create_app()

if __name__ == "__main__":
    print(f"Base de datos: {DB_PATH}")
    print("Iniciando servidor en http://127.0.0.1:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)
