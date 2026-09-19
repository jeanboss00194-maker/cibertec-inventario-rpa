#!/usr/bin/env python3
"""
Generador del archivo de entrada para el bot RPA — trimestre "oct"
=====================================================================

"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.database import session  # noqa: E402

random.seed(20261031)

DIR_SALIDA = Path(__file__).resolve().parent / "input"
ARCHIVO_SALIDA = DIR_SALIDA / "conteo_fisico_oct.csv"

# Nombres alternativos que el personal de campo escribe a veces en el
# formulario en lugar del nombre canónico (restricción real documentada
# en el Sprint 1). El bot debe resolverlos contra el catálogo único
# (ver backend/app/alias_sedes.py) — comportamiento validado por CP-04.
ALIAS_DE_CAMPO = {"Independencia": "Sede Norte", "Callao": "Sede Bellavista"}


def generar():
    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    filas = []
    with session() as conn:
        equipos = conn.execute(
            """SELECT eq.codigo_activo_case, eq.estado_case, s.nombre AS sede
               FROM equipo eq JOIN espacio es ON es.id_espacio = eq.id_espacio
               JOIN sede s ON s.id_sede = es.id_sede"""
        ).fetchall()
        asistentes_por_sede: dict[str, list[str]] = {}
        for row in conn.execute("SELECT nombre, sede_asignada FROM asistente").fetchall():
            asistentes_por_sede.setdefault(row["sede_asignada"], []).append(row["nombre"])

    for eq in equipos:
        asistente = random.choice(asistentes_por_sede[eq["sede"]])
        discrepancia = random.random() < 0.05
        if discrepancia:
            tipo = random.choice(["faltante", "inoperativo"])
            if tipo == "faltante":
                cantidad_encontrada = 0
                estado_reportado = "Faltante"
            else:
                cantidad_encontrada = 1
                estado_reportado = "Inoperativo"
        else:
            cantidad_encontrada = 1
            estado_reportado = eq["estado_case"]  # coincide con el registro maestro

        # ~15% de los registros de Independencia y Callao llegan con el
        # nombre informal de sede usado por el personal de campo, tal como
        # ocurre en el archivo institucional real (Sprint 1, Restricciones).
        sede_reportada = eq["sede"]
        if eq["sede"] in ALIAS_DE_CAMPO and random.random() < 0.15:
            sede_reportada = ALIAS_DE_CAMPO[eq["sede"]]

        filas.append({
            "codigo_activo_case": eq["codigo_activo_case"],
            "cantidad_esperada": 1,
            "cantidad_encontrada": cantidad_encontrada,
            "estado_reportado": estado_reportado,
            "asistente": asistente,
            "sede_reportada": sede_reportada,
        })

    with open(ARCHIVO_SALIDA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["codigo_activo_case", "cantidad_esperada", "cantidad_encontrada",
                           "estado_reportado", "asistente", "sede_reportada"]
        )
        writer.writeheader()
        writer.writerows(filas)

    n_disc = sum(1 for r in filas if r["cantidad_encontrada"] == 0 or r["estado_reportado"] == "Inoperativo")
    n_alias = sum(1 for r, eq in zip(filas, equipos) if r["sede_reportada"] != eq["sede"])
    print(f"Archivo de conteo físico generado: {ARCHIVO_SALIDA}")
    print(f"  Total de registros      : {len(filas)}")
    print(f"  Con discrepancia        : {n_disc} (~{100*n_disc/len(filas):.1f}%)")
    print(f"  Con nombre de sede alternativo (a resolver por el bot): {n_alias}")


if __name__ == "__main__":
    generar()
