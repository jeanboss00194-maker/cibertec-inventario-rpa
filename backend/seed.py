#!/usr/bin/env python3
"""
Script de generación de datos (seed) — Sistema de Inventario CIBERTEC
========================================================================

Este script puebla la base de datos con un conjunto de datos que
reproduce, a nivel agregado, la distribución REAL de equipos e
infraestructura de CIBERTEC extraída del archivo institucional
"Inventario General de Equipos de Cómputo" (hoja "Plan de
Mantenimiento" / "Consolidado"), entregado por la usuaria como
insumo de la investigación.

Decisión metodológica y de protección de datos (documentada también
en el README del proyecto):
  * Se reproducen fielmente los TOTALES agregados por sede y tipo de
    equipo, la proporción de categorías (Avanzada/Estándar), la
    distribución empírica de marcas y de años de uso, y la cantidad
    real de ambientes (aulas/laboratorios) por sede.
  * NO se reproduce ningún identificador real de equipo (IP, MAC,
    Service Tag) ni se usan los nombres de los asistentes reales
    encontrados en el archivo fuente. Todos los códigos de activo,
    service tags y nombres de asistente en esta base de datos son
    SINTÉTICOS, generados por este script para fines de demostración.
  * El coordinador de aulas y laboratorios (rol institucional citado
    en la documentación del Sprint 1) no se modela como registro en
    esta base de datos operativa: la tabla `asistente` corresponde al
    personal que ejecuta la verificación física trimestral.

Totales objetivo (fuente: hoja "Plan de Mantenimiento", cifra que
coincide entre hojas del archivo original — 1,893 equipos, 93
ambientes, 7 sedes):

    Sede                      Desktop  iMac  Laptop  Workstation  Total
    Arequipa                       9    43      39          131    222
    Breña                         14    41      29          188    272
    Callao                         9    25      32          140    206
    Independencia                 40    22      48          293    403
    Lima Centro                   20     4       6          388    418
    San Juan de Lurigancho        12    31      29          126    198
    Trujillo                       0     2      23          149    174
    ----------------------------------------------------------------
    TOTAL                        104   168     206         1415   1893

Ejecución:
    python backend/seed.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.database import init_db, session  # noqa: E402

random.seed(2026)  # reproducibilidad para la sustentación

# ---------------------------------------------------------------------
# 1. Sedes y su distribución REAL de equipos por tipo (fuente: Excel)
# ---------------------------------------------------------------------
SEDES = {
    "Arequipa": {
        "ciudad": "Arequipa",
        "n_ambientes": 7,
        "prefijo": "AQP",
        "equipos": {"Desktop": 9, "iMac": 43, "Laptop": 39, "Workstation": 131},
    },
    "Breña": {
        "ciudad": "Lima",
        "n_ambientes": 10,
        "prefijo": "BRE",
        "equipos": {"Desktop": 14, "iMac": 41, "Laptop": 29, "Workstation": 188},
    },
    "Callao": {
        "ciudad": "Callao",
        "n_ambientes": 7,
        "prefijo": "CAL",
        "equipos": {"Desktop": 9, "iMac": 25, "Laptop": 32, "Workstation": 140},
    },
    "Independencia": {
        "ciudad": "Lima",
        "n_ambientes": 22,
        "prefijo": "IND",
        "equipos": {"Desktop": 40, "iMac": 22, "Laptop": 48, "Workstation": 293},
    },
    "Lima Centro": {
        "ciudad": "Lima",
        "n_ambientes": 24,
        "prefijo": "LC",
        "equipos": {"Desktop": 20, "iMac": 4, "Laptop": 6, "Workstation": 388},
    },
    "San Juan de Lurigancho": {
        "ciudad": "Lima",
        "n_ambientes": 11,
        "prefijo": "SJL",
        "equipos": {"Desktop": 12, "iMac": 31, "Laptop": 29, "Workstation": 126},
    },
    "Trujillo": {
        "ciudad": "Trujillo",
        "n_ambientes": 12,
        "prefijo": "TRU",
        "equipos": {"Desktop": 0, "iMac": 2, "Laptop": 23, "Workstation": 149},
    },
}

# Proporción real del tipo de ambiente (hoja de ambientes/uso, agregada)
TIPO_AMBIENTE_PESOS = [("Laboratorio", 0.78), ("Taller", 0.09), ("Aula", 0.07), ("Multipropósito", 0.06)]

# Proporción real de categoría dentro de cada tipo de equipo
CATEGORIA_PESOS = {
    "Workstation": [("Avanzada", 0.78), ("Estándar", 0.22)],
    "Laptop": [("Avanzada", 0.925), ("Estándar", 0.075)],
    "Desktop": [("Estándar", 0.67), ("Avanzada", 0.33)],
    "iMac": [("Avanzada", 1.0)],  # los iMac del parque son, en su totalidad, equipos de gama alta
}

# Distribución real de marca (agregada, hoja Consolidado). Apple se
# asigna únicamente a iMac (coherente con el catálogo institucional);
# HP y Dell se reparten entre los demás tipos.
MARCA_PESOS_NO_IMAC = [("HP", 0.89), ("Dell", 0.11)]

MODELOS = {
    ("Workstation", "HP"): ["HP Z2 Tower G9", "HP Z1 G9", "HP ProDesk 600 G9"],
    ("Workstation", "Dell"): ["Dell Precision 3660", "Dell OptiPlex 7020 Tower"],
    ("Desktop", "HP"): ["HP ProDesk 400 G9", "HP EliteDesk 800 G9"],
    ("Desktop", "Dell"): ["Dell OptiPlex 3000", "Dell Vostro 3888"],
    ("Laptop", "HP"): ["HP ProBook 440 G9", "HP EliteBook 640 G9"],
    ("Laptop", "Dell"): ["Dell Latitude 5440", "Dell Vostro 5410"],
    ("iMac", "Apple"): ['iMac 24" M1 (2021)', 'iMac 21.5" (2019)'],
}

# Distribución empírica real de "años de uso" (hoja Plan de
# Mantenimiento), usada como tabla de pesos para el muestreo aleatorio
ANIOS_USO_PESOS = [
    (0, 425), (1, 448), (2, 48), (3, 76), (4, 67),
    (6, 176), (7, 268), (8, 235), (9, 60), (10, 1), (11, 13), (12, 18),
]

ANIO_ACTUAL = 2026

# Nombres SINTÉTICOS de asistentes (no corresponden a personal real de
# CIBERTEC) — dos por sede, responsables de la verificación física.
NOMBRES_ASISTENTES = [
    "Diego Alania Salazar", "Fiorella Campos Medina", "Renzo Huamán Torres",
    "Katherine Villar Ponce", "Bruno Cárdenas Ruiz", "Milagros Paredes Soto",
    "Jhonatan Quispe Farfán", "Andrea Ochoa Rivas", "Cristian Del Águila Vega",
    "Naomi Bendezú Castro", "Marco Sifuentes León", "Estefanía Guzmán Pinto",
    "Josué Mamani Chura", "Valeria Rosales Injante",
]

TRIMESTRES_HISTORICOS = ["ene", "abr", "jul"]  # el trimestre "oct" queda para la demo en vivo del bot RPA

# Cuentas de acceso a la interfaz web (tabla `usuario_sistema`). El
# usuario "coordinador" es la cuenta original de demostración de la
# sustentación (se conserva por compatibilidad); "jgarcia" es una
# segunda cuenta de Administrador provista por la investigadora. Las 5
# cuentas de rol "Limitado" son SINTÉTICAS (mismo criterio de la lista
# NOMBRES_ASISTENTES) y sirven para demostrar el control de acceso por
# rol: no pueden dar de alta/editar/eliminar equipos ni ejecutar el bot
# RPA o el motor analítico (backend/app/auth.py::require_admin), y la
# interfaz les oculta esas secciones (frontend/app.js).
CLAVE_DEMO_USUARIOS = "cibertec2026"  # una sola clave de demostración académica para las 7 cuentas
USUARIOS_SISTEMA = [
    # (nombre_completo, usuario, rol)
    ("Martha García", "coordinador", "Administrador"),
    ("Jean García Chota", "jgarcia", "Administrador"),
    ("Camila Torres Fernández", "ctorres", "Limitado"),
    ("Julio Espinoza Delgado", "jespinoza", "Limitado"),
    ("Grecia Ninahuanca Palomino", "gninahuanca", "Limitado"),
    ("Sebastián Rojas Medina", "srojas", "Limitado"),
    ("Paola Guevara Ríos", "pguevara", "Limitado"),
]


def elegir_ponderado(pares):
    opciones, pesos = zip(*pares)
    return random.choices(opciones, weights=pesos, k=1)[0]


def elegir_anios_uso():
    valores, pesos = zip(*ANIOS_USO_PESOS)
    return random.choices(valores, weights=pesos, k=1)[0]


def generar_service_tag(prefijo: str, i: int) -> str:
    """Identificador sintético (NO reproduce service tags reales)."""
    sufijo = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789", k=5))
    return f"SN-{prefijo}-{sufijo}"


def seed():
    init_db(reset=True)
    asistentes_pool = list(NOMBRES_ASISTENTES)
    random.shuffle(asistentes_pool)
    idx_asistente = 0

    with session() as conn:
        # --- Sedes -----------------------------------------------------
        id_sede_por_nombre = {}
        for nombre, cfg in SEDES.items():
            cur = conn.execute(
                "INSERT INTO sede (nombre, ciudad) VALUES (?, ?)", (nombre, cfg["ciudad"])
            )
            id_sede_por_nombre[nombre] = cur.lastrowid

        # --- Asistentes (2 por sede, sintéticos) ------------------------
        id_asistentes_por_sede: dict[str, list[int]] = {}
        for nombre in SEDES:
            ids = []
            for _ in range(2):
                nom = asistentes_pool[idx_asistente % len(asistentes_pool)]
                idx_asistente += 1
                cur = conn.execute(
                    "INSERT INTO asistente (nombre, sede_asignada) VALUES (?, ?)",
                    (f"{nom}", nombre),
                )
                ids.append(cur.lastrowid)
            id_asistentes_por_sede[nombre] = ids

        # --- Espacios (ambientes reales por sede) -----------------------
        espacios_por_sede: dict[str, list[int]] = {}
        for nombre, cfg in SEDES.items():
            ids = []
            for i in range(1, cfg["n_ambientes"] + 1):
                tipo_amb = elegir_ponderado(TIPO_AMBIENTE_PESOS)
                capacidad = random.choice([20, 24, 28, 30, 32, 35, 40])
                codigo = f"{cfg['prefijo']}-{100 + i}"
                cur = conn.execute(
                    """INSERT INTO espacio (id_sede, codigo_aula, capacidad, tipo_ambiente)
                       VALUES (?, ?, ?, ?)""",
                    (id_sede_por_nombre[nombre], codigo, capacidad, tipo_amb),
                )
                ids.append(cur.lastrowid)
            espacios_por_sede[nombre] = ids

        # --- Equipos (distribución real por sede y tipo_pc) -------------
        equipos_creados: list[tuple[int, str]] = []  # (id_equipo, sede) para conciliaciones
        contador_global = 0
        for nombre, cfg in SEDES.items():
            espacios = espacios_por_sede[nombre]
            for tipo_pc, cantidad in cfg["equipos"].items():
                for _ in range(cantidad):
                    contador_global += 1
                    categoria = elegir_ponderado(CATEGORIA_PESOS[tipo_pc])
                    marca = "Apple" if tipo_pc == "iMac" else elegir_ponderado(MARCA_PESOS_NO_IMAC)
                    modelo = random.choice(MODELOS.get((tipo_pc, marca), [f"{marca} genérico"]))
                    anios_uso = elegir_anios_uso()
                    anio_recepcion = ANIO_ACTUAL - anios_uso
                    leasing = elegir_ponderado([("Leasing", 0.55), ("Propio", 0.45)])
                    estado_case = elegir_ponderado([("Operativo", 0.998), ("Inoperativo", 0.002)])
                    estado_monitor = elegir_ponderado([("Operativo", 0.99), ("Inoperativo", 0.01)])
                    codigo_activo = f"CASE-{cfg['prefijo']}-{contador_global:05d}"
                    service_tag = generar_service_tag(cfg["prefijo"], contador_global)
                    id_espacio = random.choice(espacios)

                    cur = conn.execute(
                        """INSERT INTO equipo
                           (id_espacio, codigo_activo_case, service_tag_case, tipo_pc, categoria,
                            marca, modelo, anio_recepcion, anios_uso, leasing_o_propio,
                            estado_case, estado_monitor)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            id_espacio, codigo_activo, service_tag, tipo_pc, categoria,
                            marca, modelo, anio_recepcion, anios_uso, leasing,
                            estado_case, estado_monitor,
                        ),
                    )
                    equipos_creados.append((cur.lastrowid, nombre, estado_case))

        # --- Conciliaciones históricas (ene, abr, jul) -------------------
        # Se simula que, en cada trimestre pasado, el proceso MANUAL de
        # verificación (previo a la automatización) tenía una tasa de
        # discrepancia de ~6-9%, consistente con el problema descrito en
        # el Sprint 1 (errores humanos en el conteo). El trimestre "oct"
        # se deja sin poblar para que el bot RPA lo genere en la demo.
        for id_equipo, sede, estado_case in equipos_creados:
            id_asistente = random.choice(id_asistentes_por_sede[sede])
            for trimestre in TRIMESTRES_HISTORICOS:
                hay_discrepancia = random.random() < 0.07
                cantidad_esperada = 1
                if hay_discrepancia:
                    cantidad_encontrada = 0
                    estado_reportado = random.choice(["Faltante", "Inoperativo"])
                else:
                    cantidad_encontrada = 1
                    estado_reportado = "Operativo" if estado_case == "Operativo" else "Inoperativo"
                diferencia = cantidad_encontrada - cantidad_esperada
                fecha = {"ene": f"{ANIO_ACTUAL}-01-15", "abr": f"{ANIO_ACTUAL}-04-15",
                         "jul": f"{ANIO_ACTUAL}-07-15"}[trimestre]

                cur = conn.execute(
                    """INSERT INTO conciliacion
                       (id_equipo, id_asistente, trimestre, cantidad_esperada,
                        cantidad_encontrada, estado_reportado, diferencia, fecha)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (id_equipo, id_asistente, trimestre, cantidad_esperada,
                     cantidad_encontrada, estado_reportado, diferencia, fecha),
                )
                if diferencia != 0:
                    conn.execute(
                        """INSERT INTO alerta (id_equipo, tipo_alerta, fecha_generacion, estado)
                           VALUES (?, 'faltante', ?, 'atendida')""",
                        (id_equipo, fecha),
                    )
                if estado_reportado == "Inoperativo":
                    conn.execute(
                        """INSERT INTO alerta (id_equipo, tipo_alerta, fecha_generacion, estado)
                           VALUES (?, 'inoperativo', ?, 'atendida')""",
                        (id_equipo, fecha),
                    )

        # --- Alertas de fin de vida útil (equipos con >= 7 años) ---------
        for id_equipo, sede, estado_case in equipos_creados:
            row = conn.execute("SELECT anios_uso FROM equipo WHERE id_equipo = ?", (id_equipo,)).fetchone()
            if row["anios_uso"] >= 7:
                conn.execute(
                    """INSERT INTO alerta (id_equipo, tipo_alerta, fecha_generacion, estado)
                       VALUES (?, 'fin_vida_util', ?, 'activa')""",
                    (id_equipo, f"{ANIO_ACTUAL}-07-15"),
                )

        # --- Cuentas de acceso al sistema (login de la interfaz web) ----
        for nombre_completo, usuario, rol in USUARIOS_SISTEMA:
            conn.execute(
                """INSERT INTO usuario_sistema (nombre_completo, usuario, clave, rol, activo)
                   VALUES (?, ?, ?, ?, 1)""",
                (nombre_completo, usuario, CLAVE_DEMO_USUARIOS, rol),
            )

    total_equipos = sum(sum(cfg["equipos"].values()) for cfg in SEDES.values())
    total_ambientes = sum(cfg["n_ambientes"] for cfg in SEDES.values())
    print(f"Semilla generada: {total_equipos} equipos, {total_ambientes} ambientes, "
          f"{len(SEDES)} sedes, {len(TRIMESTRES_HISTORICOS)} trimestres históricos cargados.")
    print(f"Cuentas de acceso creadas: {len(USUARIOS_SISTEMA)} "
          f"({sum(1 for _, _, r in USUARIOS_SISTEMA if r == 'Administrador')} Administrador, "
          f"{sum(1 for _, _, r in USUARIOS_SISTEMA if r == 'Limitado')} Limitado) — "
          f"clave de demostración para todas: '{CLAVE_DEMO_USUARIOS}'.")
    print("El trimestre 'oct' quedó sin datos: ejecutar rpa_bot/bot_conciliacion.py para la demo en vivo.")


if __name__ == "__main__":
    seed()
