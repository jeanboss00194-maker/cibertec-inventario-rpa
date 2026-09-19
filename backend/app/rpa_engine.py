"""
Motor de conciliación en proceso — usado por el botón "Ejecutar Robot"
del panel "Automatización RPA" del dashboard.

"""

from __future__ import annotations

import csv
import random
import sqlite3
from datetime import date
from pathlib import Path

from . import crud
from .alias_sedes import resolver_sede

DIR_INPUT = Path(__file__).resolve().parent.parent.parent / "rpa_bot" / "input"
ARCHIVO_CONTEO = DIR_INPUT / "conteo_fisico_oct.csv"

ALIAS_DE_CAMPO = {"Independencia": "Sede Norte", "Callao": "Sede Bellavista"}


class ErrorTransaccion(Exception):
    pass


def generar_conteo_ejemplo(conn: sqlite3.Connection, trimestre: str = "oct", seed: int | None = None) -> list[dict]:
    """Simula el archivo de conteo físico de campo (ver rpa_bot/generar_input_conteo.py)
    y lo guarda en disco para que quede disponible también para el bot de terminal."""
    rng = random.Random(seed)
    equipos = crud.list_equipos(conn)
    asistentes_por_sede: dict[str, list[str]] = {}
    for a in crud.list_asistentes(conn):
        asistentes_por_sede.setdefault(a["sede_asignada"], []).append(a["nombre"])

    filas = []
    for eq in equipos:
        sede = eq["nombre_sede"]
        asistentes_sede = asistentes_por_sede.get(sede) or ["Asistente sin asignar"]
        asistente = rng.choice(asistentes_sede)
        discrepancia = rng.random() < 0.05
        if discrepancia:
            tipo = rng.choice(["faltante", "inoperativo"])
            cantidad_encontrada = 0 if tipo == "faltante" else 1
            estado_reportado = "Faltante" if tipo == "faltante" else "Inoperativo"
        else:
            cantidad_encontrada = 1
            estado_reportado = eq["estado_case"]

        sede_reportada = sede
        if sede in ALIAS_DE_CAMPO and rng.random() < 0.15:
            sede_reportada = ALIAS_DE_CAMPO[sede]

        filas.append({
            "codigo_activo_case": eq["codigo_activo_case"],
            "cantidad_esperada": 1,
            "cantidad_encontrada": cantidad_encontrada,
            "estado_reportado": estado_reportado,
            "asistente": asistente,
            "sede_reportada": sede_reportada,
        })

    DIR_INPUT.mkdir(parents=True, exist_ok=True)
    with open(ARCHIVO_CONTEO, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["codigo_activo_case", "cantidad_esperada", "cantidad_encontrada",
                           "estado_reportado", "asistente", "sede_reportada"]
        )
        writer.writeheader()
        writer.writerows(filas)

    return filas


def leer_conteo_desde_archivo(ruta: Path = ARCHIVO_CONTEO) -> list[dict]:
    if not ruta.exists():
        raise FileNotFoundError(
            "No hay un archivo de conteo físico disponible. Genere uno primero "
            "(botón 'Generar conteo de ejemplo') o suba un archivo CSV."
        )
    with open(ruta, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def procesar_conteo_fisico(conn: sqlite3.Connection, filas: list[dict], trimestre: str = "oct") -> dict:
    """Núcleo del bot RPA (mismo diagrama de flujo del Sprint 3), ejecutado
    en proceso. Devuelve un resumen + una bitácora de líneas de log, en el
    mismo formato que produce rpa_bot/bot_conciliacion.py::ejecutar()."""
    equipos_por_codigo = {e["codigo_activo_case"]: e for e in crud.list_equipos(conn)}
    asistentes_por_nombre = {a["nombre"]: a["id_asistente"] for a in crud.list_asistentes(conn)}

    bitacora = [
        f"Estado INIT: {len(equipos_por_codigo)} equipos y {len(asistentes_por_nombre)} "
        f"asistentes cargados desde el registro maestro.",
        f"Estado GET_TRANSACTION_DATA: {len(filas)} transacciones en cola para el trimestre '{trimestre}'.",
        "Estado PROCESS_TRANSACTION: procesando cola, transacción por transacción...",
    ]

    resumen = {
        "total": len(filas), "conciliados": 0, "con_discrepancia": 0,
        "alertas_generadas": 0, "errores": [], "sedes_resueltas_por_alias": 0,
    }

    for i, fila in enumerate(filas, start=1):
        try:
            codigo = fila["codigo_activo_case"]
            equipo = equipos_por_codigo.get(codigo)
            if equipo is None:
                raise ErrorTransaccion(f"Código de activo '{codigo}' no existe en el registro maestro.")

            id_asistente = asistentes_por_nombre.get(fila["asistente"])
            if id_asistente is None:
                raise ErrorTransaccion(f"Asistente '{fila['asistente']}' no está registrado.")

            sede_cruda = (fila.get("sede_reportada") or "").strip()
            if sede_cruda:
                try:
                    sede_resuelta = resolver_sede(sede_cruda)
                except ValueError as e:
                    raise ErrorTransaccion(str(e)) from e
                if sede_resuelta != equipo["nombre_sede"]:
                    raise ErrorTransaccion(
                        f"Inconsistencia de sede para '{codigo}': reporta '{sede_cruda}' "
                        f"pero el registro maestro indica '{equipo['nombre_sede']}'."
                    )
                if sede_resuelta.lower() != sede_cruda.lower():
                    resumen["sedes_resueltas_por_alias"] += 1

            payload = {
                "id_equipo": equipo["id_equipo"],
                "id_asistente": id_asistente,
                "trimestre": trimestre,
                "cantidad_esperada": int(fila["cantidad_esperada"]),
                "cantidad_encontrada": int(fila["cantidad_encontrada"]),
                "estado_reportado": fila["estado_reportado"],
                "fecha": date.today().isoformat(),
            }
            resultado = crud.create_conciliacion(conn, payload)
            if resultado["diferencia"] == 0 and resultado["estado_reportado"] == "Operativo":
                resumen["conciliados"] += 1
            else:
                resumen["con_discrepancia"] += 1
            resumen["alertas_generadas"] += len(resultado.get("alertas_generadas", []))
        except ErrorTransaccion as e:
            resumen["errores"].append({"fila": i, "codigo": fila.get("codigo_activo_case"), "error": str(e)})

    bitacora.append(f"Estado END_PROCESS: {resumen['conciliados']} conciliados sin novedad, "
                     f"{resumen['con_discrepancia']} con discrepancia, "
                     f"{resumen['alertas_generadas']} alertas generadas.")
    if resumen["sedes_resueltas_por_alias"]:
        bitacora.append(f"Sedes resueltas contra el catálogo único: {resumen['sedes_resueltas_por_alias']} (CP-04).")
    if resumen["errores"]:
        bitacora.append(f"Errores de transacción controlados: {len(resumen['errores'])} (no detuvieron el proceso).")
    bitacora.append("Registrando resultado en la base de datos... Proceso completado.")

    resumen["bitacora"] = bitacora
    return resumen
