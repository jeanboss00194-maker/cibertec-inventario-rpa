"""
Capa de acceso a datos — Sistema de Inventario de Equipos de Cómputo (CIBERTEC)
================================================================================

Implementa, sobre SQLite (biblioteca estándar de Python, sin dependencias
externas), el modelo entidad-relación definido en el Sprint 3 del proyecto
de investigación:

    SEDE (1) ---- (N) ESPACIO (1) ---- (N) EQUIPO (1) ---- (N) CONCILIACION
    ASISTENTE (1) ---- (N) CONCILIACION
    EQUIPO (1) ---- (N) ALERTA
    USUARIO_SISTEMA (1) ---- (N) BITACORA_CAMBIO (auditoría de quién hizo qué)

Se eligió SQLite en lugar de SQL Server (propuesto en la arquitectura del
Sprint 2 como tecnología de producción) para que el prototipo se ejecute de
forma autocontenida, sin instalación de un motor de base de datos externo,
lo cual es apropiado para una demostración académica. El esquema y las
consultas usan SQL estándar, por lo que migrar a SQL Server o PostgreSQL en
una implementación productiva no requiere cambios de diseño, solo de motor.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "inventario_cibertec.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sede (
    id_sede     INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL UNIQUE,
    ciudad      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS espacio (
    id_espacio    INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sede       INTEGER NOT NULL REFERENCES sede(id_sede),
    codigo_aula   TEXT NOT NULL,
    capacidad     INTEGER NOT NULL,
    tipo_ambiente TEXT NOT NULL CHECK (tipo_ambiente IN ('Aula', 'Laboratorio', 'Taller', 'Multipropósito'))
);

CREATE TABLE IF NOT EXISTS asistente (
    id_asistente   INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre         TEXT NOT NULL,
    sede_asignada  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usuario_sistema (
    id_usuario      INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_completo TEXT NOT NULL,
    usuario         TEXT NOT NULL UNIQUE,
    clave           TEXT NOT NULL,
    rol             TEXT NOT NULL CHECK (rol IN ('Administrador', 'Limitado')),
    activo          INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS equipo (
    id_equipo            INTEGER PRIMARY KEY AUTOINCREMENT,
    id_espacio           INTEGER NOT NULL REFERENCES espacio(id_espacio),
    codigo_activo_case   TEXT NOT NULL UNIQUE,
    service_tag_case     TEXT NOT NULL,
    tipo_pc              TEXT NOT NULL CHECK (tipo_pc IN ('Workstation', 'Desktop', 'iMac', 'Laptop')),
    categoria            TEXT NOT NULL,
    marca                TEXT NOT NULL,
    modelo               TEXT NOT NULL,
    anio_recepcion       INTEGER NOT NULL,
    anios_uso            INTEGER NOT NULL,
    leasing_o_propio     TEXT NOT NULL CHECK (leasing_o_propio IN ('Leasing', 'Propio')),
    estado_case          TEXT NOT NULL DEFAULT 'Operativo',
    estado_monitor       TEXT NOT NULL DEFAULT 'Operativo',
    prioridad_renovacion TEXT,
    score_renovacion     REAL
);

CREATE TABLE IF NOT EXISTS conciliacion (
    id_conciliacion     INTEGER PRIMARY KEY AUTOINCREMENT,
    id_equipo           INTEGER NOT NULL REFERENCES equipo(id_equipo),
    id_asistente        INTEGER NOT NULL REFERENCES asistente(id_asistente),
    trimestre           TEXT NOT NULL CHECK (trimestre IN ('ene', 'abr', 'jul', 'oct')),
    cantidad_esperada   INTEGER NOT NULL,
    cantidad_encontrada INTEGER NOT NULL,
    estado_reportado    TEXT NOT NULL,
    diferencia          INTEGER NOT NULL,
    fecha               TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerta (
    id_alerta        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_equipo        INTEGER NOT NULL REFERENCES equipo(id_equipo),
    tipo_alerta      TEXT NOT NULL CHECK (tipo_alerta IN ('faltante', 'inoperativo', 'fin_vida_util')),
    fecha_generacion TEXT NOT NULL,
    estado           TEXT NOT NULL DEFAULT 'activa' CHECK (estado IN ('activa', 'atendida'))
);

-- Bitácora de cambios (auditoría): registra QUIÉN (cuenta de
-- `usuario_sistema`) realizó QUÉ acción (alta/edición/baja/atención/
-- ejecución), sobre QUÉ entidad y CUÁNDO. Ver backend/app/crud.py
-- (registrar_cambio / list_bitacora) y backend/app/auth.py
-- (usuario_actual) para la nota de diseño sobre el alcance de esta
-- identidad en el prototipo: se toma de la cuenta con la que se
-- inició sesión (misma capa de confianza que el encabezado X-Rol ya
-- usado por require_admin), no de una sesión firmada por el servidor.
CREATE TABLE IF NOT EXISTS bitacora_cambio (
    id_bitacora     INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_hora      TEXT NOT NULL,
    usuario         TEXT NOT NULL,
    nombre_usuario  TEXT,
    rol             TEXT,
    entidad         TEXT NOT NULL CHECK (entidad IN ('equipo', 'alerta', 'priorizacion', 'rpa')),
    id_entidad      TEXT,
    referencia      TEXT,
    accion          TEXT NOT NULL CHECK (accion IN ('alta', 'edicion', 'baja', 'atencion', 'ejecucion')),
    detalle         TEXT
);

CREATE INDEX IF NOT EXISTS idx_equipo_espacio ON equipo(id_espacio);
CREATE INDEX IF NOT EXISTS idx_espacio_sede ON espacio(id_sede);
CREATE INDEX IF NOT EXISTS idx_conciliacion_equipo ON conciliacion(id_equipo);
CREATE INDEX IF NOT EXISTS idx_alerta_equipo ON alerta(id_equipo);
CREATE INDEX IF NOT EXISTS idx_bitacora_fecha ON bitacora_cambio(fecha_hora DESC);
CREATE INDEX IF NOT EXISTS idx_bitacora_usuario ON bitacora_cambio(usuario);
"""


def get_connection() -> sqlite3.Connection:
    """Abre una conexión con claves foráneas activas y filas accesibles por nombre de columna."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def session():
    """Context manager que abre una conexión, confirma al salir y la cierra siempre."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(reset: bool = False) -> None:
    """Crea el esquema. Si reset=True, elimina el archivo de base de datos existente primero."""
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    with session() as conn:
        conn.executescript(SCHEMA)


if __name__ == "__main__":
    init_db(reset=True)
    print(f"Base de datos inicializada en: {DB_PATH}")
