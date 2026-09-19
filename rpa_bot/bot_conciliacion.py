#!/usr/bin/env python3
"""
Bot RPA de Conciliación de Inventario — CIBERTEC
===================================================================
"""

from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app.alias_sedes import resolver_sede  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
ARCHIVO_ENTRADA = BASE_DIR / "input" / "conteo_fisico_oct.csv"
DIR_LOGS = BASE_DIR / "logs"

API_URL = "http://127.0.0.1:5000/api"
# Debe coincidir con CIBERTEC_API_TOKEN / el valor por defecto en backend/app/auth.py
API_TOKEN = "cibertec-demo-2026"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}
TRIMESTRE = "oct"


class ErrorTransaccion(Exception):
    """Equivalente al 'BusinessRuleException' del REFramework de UiPath."""


def log(mensaje: str, nivel: str = "INFO") -> None:
    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{marca}] [{nivel}] {mensaje}")


def inicializar() -> tuple[dict[str, dict], dict[str, int]]:
    """Estado 'Init' del REFramework: valida conectividad y descarga el
    registro maestro (equipos y asistentes) para resolver códigos a IDs."""
    log("Estado INIT: verificando conectividad con la API...")
    r = requests.get(f"{API_URL}/salud", timeout=5)
    r.raise_for_status()
    log(f"API disponible: {r.json()}")

    log("Descargando registro maestro de equipos...")
    r = requests.get(f"{API_URL}/equipos", headers=HEADERS, timeout=30)
    r.raise_for_status()
    equipos = {e["codigo_activo_case"]: e for e in r.json()}
    log(f"  {len(equipos)} equipos cargados desde el registro maestro.")

    log("Descargando padrón de asistentes...")
    r = requests.get(f"{API_URL}/asistentes", headers=HEADERS, timeout=30)
    r.raise_for_status()
    asistentes = {a["nombre"]: a["id_asistente"] for a in r.json()}
    log(f"  {len(asistentes)} asistentes cargados.")

    return equipos, asistentes


def obtener_cola_transacciones() -> list[dict]:
    """Estado 'Get Transaction Data': lee el archivo de conteo físico."""
    log(f"Estado GET_TRANSACTION_DATA: leyendo {ARCHIVO_ENTRADA.name} ...")
    if not ARCHIVO_ENTRADA.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de conteo físico en {ARCHIVO_ENTRADA}. "
            f"Ejecute primero: python rpa_bot/generar_input_conteo.py"
        )
    with open(ARCHIVO_ENTRADA, newline="", encoding="utf-8") as f:
        cola = list(csv.DictReader(f))
    log(f"  {len(cola)} transacciones (equipos) en cola para el trimestre '{TRIMESTRE}'.")
    return cola


def procesar_transaccion(fila: dict, equipos: dict, asistentes: dict, resultado_alias: dict) -> dict:
    """Estado 'Process Transaction': compara físico vs. sistema y
    registra el resultado a través de la API (que aplica la misma
    regla de negocio del diagrama de flujo para generar alertas)."""
    codigo = fila["codigo_activo_case"]
    equipo = equipos.get(codigo)
    if equipo is None:
        raise ErrorTransaccion(f"Código de activo '{codigo}' no existe en el registro maestro.")

    id_asistente = asistentes.get(fila["asistente"])
    if id_asistente is None:
        raise ErrorTransaccion(f"Asistente '{fila['asistente']}' no está registrado.")

    # Resolución de sede contra el catálogo único (CP-04, Sprint 5): el
    # personal de campo a veces registra un nombre informal ("Sede Norte",
    # "Sede Bellavista"); el bot lo normaliza y valida consistencia contra
    # la sede real del equipo en el registro maestro antes de continuar.
    sede_reportada_cruda = fila.get("sede_reportada", "").strip()
    if sede_reportada_cruda:
        try:
            sede_resuelta = resolver_sede(sede_reportada_cruda)
        except ValueError as e:
            raise ErrorTransaccion(str(e)) from e
        if sede_resuelta != equipo["nombre_sede"]:
            raise ErrorTransaccion(
                f"Inconsistencia de sede para '{codigo}': el conteo reporta "
                f"'{sede_reportada_cruda}' (resuelta a '{sede_resuelta}') pero el "
                f"registro maestro indica '{equipo['nombre_sede']}'."
            )
        if sede_resuelta.lower() != sede_reportada_cruda.lower():
            resultado_alias["resuelto"] = True
            log(f"  Sede '{sede_reportada_cruda}' resuelta a '{sede_resuelta}' "
                f"(catálogo único) para el equipo {codigo}.", nivel="DEBUG")

    payload = {
        "id_equipo": equipo["id_equipo"],
        "id_asistente": id_asistente,
        "trimestre": TRIMESTRE,
        "cantidad_esperada": int(fila["cantidad_esperada"]),
        "cantidad_encontrada": int(fila["cantidad_encontrada"]),
        "estado_reportado": fila["estado_reportado"],
    }
    r = requests.post(f"{API_URL}/conciliaciones", headers=HEADERS, json=payload, timeout=10)
    if r.status_code != 201:
        raise ErrorTransaccion(f"La API rechazó la conciliación de '{codigo}': {r.text}")
    return r.json()


def ejecutar() -> dict:
    inicio = time.time()
    log("=" * 70)
    log(f"BOT RPA — Conciliación de Inventario Trimestral ({TRIMESTRE.upper()} {datetime.now().year})")
    log("=" * 70)

    equipos, asistentes = inicializar()
    cola = obtener_cola_transacciones()

    resumen = {"total": len(cola), "conciliados": 0, "con_discrepancia": 0,
               "alertas_generadas": 0, "errores": [], "sedes_resueltas_por_alias": 0}

    log("Estado PROCESS_TRANSACTION: procesando cola, transacción por transacción...")
    for i, fila in enumerate(cola, start=1):
        resultado_alias = {"resuelto": False}
        try:
            resultado = procesar_transaccion(fila, equipos, asistentes, resultado_alias)
            if resultado["diferencia"] == 0 and resultado["estado_reportado"] == "Operativo":
                resumen["conciliados"] += 1
            else:
                resumen["con_discrepancia"] += 1
            resumen["alertas_generadas"] += len(resultado.get("alertas_generadas", []))
            if resultado_alias["resuelto"]:
                resumen["sedes_resueltas_por_alias"] += 1
        except ErrorTransaccion as e:
            # Equivalente a un "Business Exception" del REFramework: se
            # registra y el bot continúa con la siguiente transacción.
            resumen["errores"].append({"fila": i, "codigo": fila.get("codigo_activo_case"), "error": str(e)})
            log(f"  [FILA {i}] Excepción de negocio: {e}", nivel="WARN")
        except requests.RequestException as e:
            # Equivalente a un "System Exception": error de conectividad.
            resumen["errores"].append({"fila": i, "codigo": fila.get("codigo_activo_case"), "error": str(e)})
            log(f"  [FILA {i}] Excepción de sistema: {e}", nivel="ERROR")

        if i % 300 == 0 or i == len(cola):
            log(f"  Progreso: {i}/{len(cola)} transacciones procesadas...")

    duracion = time.time() - inicio
    resumen["duracion_segundos"] = round(duracion, 2)

    log("Estado END_PROCESS: generando reporte de ejecución...")
    log("-" * 70)
    log(f"Total de equipos verificados : {resumen['total']}")
    log(f"Conciliados sin novedad      : {resumen['conciliados']}")
    log(f"Con discrepancia             : {resumen['con_discrepancia']}")
    log(f"Alertas generadas            : {resumen['alertas_generadas']}")
    log(f"Sedes resueltas por alias    : {resumen['sedes_resueltas_por_alias']} (CP-04)")
    log(f"Errores de transacción       : {len(resumen['errores'])}")
    log(f"Tiempo de ejecución          : {duracion:.2f} s")
    log("-" * 70)

    DIR_LOGS.mkdir(parents=True, exist_ok=True)
    archivo_log = DIR_LOGS / f"ejecucion_{TRIMESTRE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(archivo_log, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
    log(f"Reporte guardado en: {archivo_log}")

    return resumen


if __name__ == "__main__":
    try:
        ejecutar()
    except requests.ConnectionError:
        log("No se pudo conectar con la API. ¿Está corriendo el servidor? "
            "Ejecute 'python run.py' en otra terminal antes de correr el bot.", nivel="ERROR")
        sys.exit(1)
