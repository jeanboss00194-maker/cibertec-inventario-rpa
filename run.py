#!/usr/bin/env python3
"""
Script de conveniencia para ejecutar el sistema completo desde la raíz
del proyecto (pensado para abrirse y ejecutarse directamente desde
Visual Studio Code, con F5 o "python run.py").

Uso:
    python run.py
Luego abrir http://127.0.0.1:5000 en el navegador.

Token de autenticación para llamadas a la API (ver backend/app/auth.py):
    Authorization: Bearer cibertec-demo-2026
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app.main import app  # noqa: E402
from backend.app.database import DB_PATH  # noqa: E402

if __name__ == "__main__":
    print("=" * 70)
    print(" Sistema de Sistematización del Inventario de Equipos — CIBERTEC")
    print("=" * 70)
    print(f" Base de datos : {DB_PATH}")
    print(" Dashboard     : http://127.0.0.1:5000")
    print(" API           : http://127.0.0.1:5000/api/...")
    print(" Token API     : Bearer cibertec-demo-2026")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, debug=False)
