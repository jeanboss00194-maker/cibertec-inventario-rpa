"""
Capa de operaciones de datos (CRUD) — Sistema de Inventario CIBERTEC
=====================================================================

Funciones de acceso a datos usadas por los routers de la API. Se
implementan con SQL parametrizado directo sobre `sqlite3` (sin ORM),
manteniendo el mismo modelo de datos definido en `database.py`.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any, Optional


def row_to_dict(row: sqlite3.Row | None) -> Optional[dict]:
    return dict(row) if row is not None else None


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------
# Sedes / Espacios
# ---------------------------------------------------------------------

def list_sedes(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM sede ORDER BY nombre").fetchall()
    return rows_to_list(rows)


def list_espacios(conn: sqlite3.Connection, id_sede: int | None = None) -> list[dict]:
    if id_sede:
        rows = conn.execute(
            """SELECT e.*, s.nombre AS nombre_sede
               FROM espacio e JOIN sede s ON s.id_sede = e.id_sede
               WHERE e.id_sede = ? ORDER BY e.codigo_aula""",
            (id_sede,),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT e.*, s.nombre AS nombre_sede
               FROM espacio e JOIN sede s ON s.id_sede = e.id_sede
               ORDER BY s.nombre, e.codigo_aula"""
        ).fetchall()
    return rows_to_list(rows)


# ---------------------------------------------------------------------
# Asistentes
# ---------------------------------------------------------------------

def list_asistentes(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM asistente ORDER BY nombre").fetchall()
    return rows_to_list(rows)


# ---------------------------------------------------------------------
# Usuarios del sistema (cuentas de acceso a la interfaz — RF-01/RNF-03)
# ---------------------------------------------------------------------

def list_usuarios(conn: sqlite3.Connection) -> list[dict]:
    """Lista las cuentas de acceso SIN exponer la clave."""
    rows = conn.execute(
        """SELECT id_usuario, nombre_completo, usuario, rol, activo
           FROM usuario_sistema ORDER BY (rol = 'Administrador') DESC, nombre_completo"""
    ).fetchall()
    return rows_to_list(rows)


def validar_login(conn: sqlite3.Connection, usuario: str, clave: str) -> Optional[dict]:
    """Valida usuario/clave contra `usuario_sistema` (cuenta activa). Devuelve
    los datos públicos de la cuenta (sin clave) si son válidos, o None."""
    row = conn.execute(
        """SELECT id_usuario, nombre_completo, usuario, rol, activo FROM usuario_sistema
           WHERE lower(usuario) = lower(?) AND clave = ? AND activo = 1""",
        (usuario.strip(), clave),
    ).fetchone()
    return row_to_dict(row)


# ---------------------------------------------------------------------
# Equipos
# ---------------------------------------------------------------------

def list_equipos(
    conn: sqlite3.Connection,
    sede: str | None = None,
    tipo_ambiente: str | None = None,
    tipo_pc: str | None = None,
    estado_case: str | None = None,
) -> list[dict]:
    query = """
        SELECT eq.*, es.codigo_aula, es.tipo_ambiente, s.nombre AS nombre_sede
        FROM equipo eq
        JOIN espacio es ON es.id_espacio = eq.id_espacio
        JOIN sede s ON s.id_sede = es.id_sede
        WHERE 1 = 1
    """
    params: list[Any] = []
    if sede:
        query += " AND s.nombre = ?"
        params.append(sede)
    if tipo_ambiente:
        query += " AND es.tipo_ambiente = ?"
        params.append(tipo_ambiente)
    if tipo_pc:
        query += " AND eq.tipo_pc = ?"
        params.append(tipo_pc)
    if estado_case:
        query += " AND eq.estado_case = ?"
        params.append(estado_case)
    query += " ORDER BY s.nombre, es.codigo_aula, eq.codigo_activo_case"
    rows = conn.execute(query, params).fetchall()
    return rows_to_list(rows)


def get_equipo_by_codigo(conn: sqlite3.Connection, codigo_activo_case: str) -> Optional[dict]:
    row = conn.execute(
        "SELECT * FROM equipo WHERE codigo_activo_case = ?", (codigo_activo_case,)
    ).fetchone()
    return row_to_dict(row)


def get_equipo_by_id(conn: sqlite3.Connection, id_equipo: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM equipo WHERE id_equipo = ?", (id_equipo,)).fetchone()
    return row_to_dict(row)


def get_asistente_by_nombre(conn: sqlite3.Connection, nombre: str) -> Optional[dict]:
    row = conn.execute("SELECT * FROM asistente WHERE nombre = ?", (nombre,)).fetchone()
    return row_to_dict(row)


CAMPOS_EDITABLES_EQUIPO = {
    "codigo_activo_case", "service_tag_case", "tipo_pc", "categoria", "marca", "modelo",
    "anio_recepcion", "anios_uso", "leasing_o_propio", "estado_case", "estado_monitor",
    "id_espacio",
}


def create_equipo(conn: sqlite3.Connection, data: dict) -> dict:
    """Módulo 4 del dashboard: registrar un activo nuevo directamente desde la UI."""
    columnas = [
        "id_espacio", "codigo_activo_case", "service_tag_case", "tipo_pc", "categoria",
        "marca", "modelo", "anio_recepcion", "anios_uso", "leasing_o_propio",
        "estado_case", "estado_monitor",
    ]
    valores = [data.get(c) for c in columnas]
    valores[columnas.index("estado_case")] = data.get("estado_case") or "Operativo"
    valores[columnas.index("estado_monitor")] = data.get("estado_monitor") or "Operativo"
    valores[columnas.index("leasing_o_propio")] = data.get("leasing_o_propio") or "Propio"
    cur = conn.execute(
        f"INSERT INTO equipo ({', '.join(columnas)}) VALUES ({', '.join('?' * len(columnas))})",
        valores,
    )
    return get_equipo_by_id(conn, cur.lastrowid)


def update_equipo(conn: sqlite3.Connection, id_equipo: int, data: dict) -> Optional[dict]:
    campos = {k: v for k, v in data.items() if k in CAMPOS_EDITABLES_EQUIPO}
    if not campos:
        return get_equipo_by_id(conn, id_equipo)
    set_clause = ", ".join(f"{k} = ?" for k in campos)
    conn.execute(
        f"UPDATE equipo SET {set_clause} WHERE id_equipo = ?",
        (*campos.values(), id_equipo),
    )
    return get_equipo_by_id(conn, id_equipo)


def delete_equipo(conn: sqlite3.Connection, id_equipo: int) -> bool:
    conn.execute("DELETE FROM alerta WHERE id_equipo = ?", (id_equipo,))
    conn.execute("DELETE FROM conciliacion WHERE id_equipo = ?", (id_equipo,))
    cur = conn.execute("DELETE FROM equipo WHERE id_equipo = ?", (id_equipo,))
    return cur.rowcount > 0


def get_actividad_reciente(conn: sqlite3.Connection, limite: int = 8) -> list[dict]:
    """Combina las últimas conciliaciones y alertas en una sola bitácora,
    para el panel 'Últimas actividades' del dashboard principal."""
    conciliaciones = conn.execute(
        """SELECT c.fecha AS fecha, 'conciliacion' AS tipo, eq.codigo_activo_case AS referencia,
                  s.nombre AS sede
           FROM conciliacion c
           JOIN equipo eq ON eq.id_equipo = c.id_equipo
           JOIN espacio es ON es.id_espacio = eq.id_espacio
           JOIN sede s ON s.id_sede = es.id_sede
           ORDER BY c.id_conciliacion DESC LIMIT ?""",
        (limite,),
    ).fetchall()
    alertas = conn.execute(
        """SELECT al.fecha_generacion AS fecha, 'alerta' AS tipo, eq.codigo_activo_case AS referencia,
                  al.tipo_alerta AS detalle, s.nombre AS sede
           FROM alerta al
           JOIN equipo eq ON eq.id_equipo = al.id_equipo
           JOIN espacio es ON es.id_espacio = eq.id_espacio
           JOIN sede s ON s.id_sede = es.id_sede
           ORDER BY al.id_alerta DESC LIMIT ?""",
        (limite,),
    ).fetchall()
    combinado = rows_to_list(conciliaciones) + rows_to_list(alertas)
    combinado.sort(key=lambda r: r["fecha"], reverse=True)
    return combinado[:limite]


# ---------------------------------------------------------------------
# Conciliaciones (núcleo del proceso RPA — PDD Sprint 3)
# ---------------------------------------------------------------------

def create_conciliacion(conn: sqlite3.Connection, data: dict) -> dict:
    """
    Inserta un registro de conciliación trimestral para un equipo y,
    si corresponde (diferencia != 0 o estado reportado distinto de
    'Operativo'), genera automáticamente una alerta — replicando la
    lógica de decisión del bot RPA descrita en el PDD del Sprint 3.
    """
    cantidad_esperada = int(data["cantidad_esperada"])
    cantidad_encontrada = int(data["cantidad_encontrada"])
    diferencia = cantidad_encontrada - cantidad_esperada
    estado_reportado = data.get("estado_reportado", "Operativo")
    fecha = data.get("fecha") or date.today().isoformat()

    cur = conn.execute(
        """INSERT INTO conciliacion
           (id_equipo, id_asistente, trimestre, cantidad_esperada,
            cantidad_encontrada, estado_reportado, diferencia, fecha)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["id_equipo"],
            data["id_asistente"],
            data["trimestre"],
            cantidad_esperada,
            cantidad_encontrada,
            estado_reportado,
            diferencia,
            fecha,
        ),
    )
    id_conciliacion = cur.lastrowid

    alertas_generadas = []
    if diferencia != 0:
        alertas_generadas.append(_crear_alerta(conn, data["id_equipo"], "faltante", fecha))
    if estado_reportado.lower() == "inoperativo":
        alertas_generadas.append(_crear_alerta(conn, data["id_equipo"], "inoperativo", fecha))
        conn.execute(
            "UPDATE equipo SET estado_case = 'Inoperativo' WHERE id_equipo = ?",
            (data["id_equipo"],),
        )

    row = conn.execute(
        "SELECT * FROM conciliacion WHERE id_conciliacion = ?", (id_conciliacion,)
    ).fetchone()
    result = row_to_dict(row)
    result["alertas_generadas"] = alertas_generadas
    return result


def _crear_alerta(conn: sqlite3.Connection, id_equipo: int, tipo_alerta: str, fecha: str) -> dict:
    cur = conn.execute(
        """INSERT INTO alerta (id_equipo, tipo_alerta, fecha_generacion, estado)
           VALUES (?, ?, ?, 'activa')""",
        (id_equipo, tipo_alerta, fecha),
    )
    row = conn.execute("SELECT * FROM alerta WHERE id_alerta = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


def list_conciliaciones(
    conn: sqlite3.Connection, sede: str | None = None, trimestre: str | None = None
) -> list[dict]:
    query = """
        SELECT c.*, eq.codigo_activo_case, eq.tipo_pc, s.nombre AS nombre_sede,
               a.nombre AS nombre_asistente
        FROM conciliacion c
        JOIN equipo eq ON eq.id_equipo = c.id_equipo
        JOIN espacio es ON es.id_espacio = eq.id_espacio
        JOIN sede s ON s.id_sede = es.id_sede
        JOIN asistente a ON a.id_asistente = c.id_asistente
        WHERE 1 = 1
    """
    params: list[Any] = []
    if sede:
        query += " AND s.nombre = ?"
        params.append(sede)
    if trimestre:
        query += " AND c.trimestre = ?"
        params.append(trimestre)
    query += " ORDER BY c.fecha DESC, c.id_conciliacion DESC"
    rows = conn.execute(query, params).fetchall()
    return rows_to_list(rows)


# ---------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------

def list_alertas(conn: sqlite3.Connection, estado: str | None = None) -> list[dict]:
    query = """
        SELECT al.*, eq.codigo_activo_case, eq.tipo_pc, s.nombre AS nombre_sede,
               es.codigo_aula
        FROM alerta al
        JOIN equipo eq ON eq.id_equipo = al.id_equipo
        JOIN espacio es ON es.id_espacio = eq.id_espacio
        JOIN sede s ON s.id_sede = es.id_sede
        WHERE 1 = 1
    """
    params: list[Any] = []
    if estado:
        query += " AND al.estado = ?"
        params.append(estado)
    query += " ORDER BY al.fecha_generacion DESC, al.id_alerta DESC"
    rows = conn.execute(query, params).fetchall()
    return rows_to_list(rows)


def atender_alerta(conn: sqlite3.Connection, id_alerta: int) -> Optional[dict]:
    conn.execute("UPDATE alerta SET estado = 'atendida' WHERE id_alerta = ?", (id_alerta,))
    row = conn.execute("SELECT * FROM alerta WHERE id_alerta = ?", (id_alerta,)).fetchone()
    return row_to_dict(row)


# ---------------------------------------------------------------------
# Indicadores (KPIs para el dashboard — wireframe Sprint 4)
# ---------------------------------------------------------------------

def get_indicadores(conn: sqlite3.Connection, sede: str | None = None) -> dict:
    where = "WHERE 1 = 1"
    params: list[Any] = []
    if sede:
        where += " AND s.nombre = ?"
        params.append(sede)

    total = conn.execute(
        f"""SELECT COUNT(*) AS n FROM equipo eq
            JOIN espacio es ON es.id_espacio = eq.id_espacio
            JOIN sede s ON s.id_sede = es.id_sede {where}""",
        params,
    ).fetchone()["n"]

    operativos = conn.execute(
        f"""SELECT COUNT(*) AS n FROM equipo eq
            JOIN espacio es ON es.id_espacio = eq.id_espacio
            JOIN sede s ON s.id_sede = es.id_sede {where} AND eq.estado_case = 'Operativo'""",
        params,
    ).fetchone()["n"]

    con_fallas = conn.execute(
        f"""SELECT COUNT(*) AS n FROM equipo eq
            JOIN espacio es ON es.id_espacio = eq.id_espacio
            JOIN sede s ON s.id_sede = es.id_sede {where} AND eq.estado_case != 'Operativo'""",
        params,
    ).fetchone()["n"]

    faltantes = conn.execute(
        f"""SELECT COUNT(DISTINCT al.id_equipo) AS n FROM alerta al
            JOIN equipo eq ON eq.id_equipo = al.id_equipo
            JOIN espacio es ON es.id_espacio = eq.id_espacio
            JOIN sede s ON s.id_sede = es.id_sede
            {where} AND al.tipo_alerta = 'faltante' AND al.estado = 'activa'""",
        params,
    ).fetchone()["n"]

    mas_7_anios = conn.execute(
        f"""SELECT COUNT(*) AS n FROM equipo eq
            JOIN espacio es ON es.id_espacio = eq.id_espacio
            JOIN sede s ON s.id_sede = es.id_sede {where} AND eq.anios_uso >= 7""",
        params,
    ).fetchone()["n"]

    por_trimestre = conn.execute(
        f"""SELECT c.trimestre, COUNT(*) AS n_conciliaciones,
                   SUM(CASE WHEN c.diferencia != 0 THEN 1 ELSE 0 END) AS n_discrepancias
            FROM conciliacion c
            JOIN equipo eq ON eq.id_equipo = c.id_equipo
            JOIN espacio es ON es.id_espacio = eq.id_espacio
            JOIN sede s ON s.id_sede = es.id_sede {where}
            GROUP BY c.trimestre
            ORDER BY CASE c.trimestre WHEN 'ene' THEN 1 WHEN 'abr' THEN 2
                                       WHEN 'jul' THEN 3 WHEN 'oct' THEN 4 END""",
        params,
    ).fetchall()

    por_sede = conn.execute(
        """SELECT s.nombre AS sede, COUNT(*) AS total_equipos,
                  SUM(CASE WHEN eq.estado_case = 'Operativo' THEN 1 ELSE 0 END) AS operativos
           FROM equipo eq
           JOIN espacio es ON es.id_espacio = eq.id_espacio
           JOIN sede s ON s.id_sede = es.id_sede
           GROUP BY s.nombre ORDER BY s.nombre"""
    ).fetchall()

    return {
        "cantidad_equipos": total,
        "equipos_operativos": operativos,
        "equipos_con_fallas": con_fallas,
        "equipos_faltantes_activos": faltantes,
        "equipos_mas_7_anios": mas_7_anios,
        "por_trimestre": rows_to_list(por_trimestre),
        "por_sede": rows_to_list(por_sede),
    }


# ---------------------------------------------------------------------
# Priorización de renovación (motor analítico CRISP-DM — Sprint 3/4)
# ---------------------------------------------------------------------

def bulk_update_priorizacion(conn: sqlite3.Connection, resultados: list[dict]) -> int:
    """
    Recibe una lista de {codigo_activo_case, prioridad_renovacion, score_renovacion}
    calculada por el motor analítico (analitica/motor_priorizacion.py) y
    actualiza cada equipo. Devuelve la cantidad de filas actualizadas.
    """
    actualizados = 0
    for r in resultados:
        cur = conn.execute(
            """UPDATE equipo SET prioridad_renovacion = ?, score_renovacion = ?
               WHERE codigo_activo_case = ?""",
            (r["prioridad_renovacion"], r["score_renovacion"], r["codigo_activo_case"]),
        )
        actualizados += cur.rowcount
    return actualizados


def list_priorizacion(conn: sqlite3.Connection, sede: str | None = None, top: int = 50) -> list[dict]:
    query = """
        SELECT eq.codigo_activo_case, eq.tipo_pc, eq.categoria, eq.marca, eq.modelo,
               eq.anios_uso, eq.estado_case, eq.prioridad_renovacion, eq.score_renovacion,
               s.nombre AS nombre_sede, es.codigo_aula
        FROM equipo eq
        JOIN espacio es ON es.id_espacio = eq.id_espacio
        JOIN sede s ON s.id_sede = es.id_sede
        WHERE eq.score_renovacion IS NOT NULL
    """
    params: list[Any] = []
    if sede:
        query += " AND s.nombre = ?"
        params.append(sede)
    query += " ORDER BY eq.score_renovacion DESC LIMIT ?"
    params.append(top)
    rows = conn.execute(query, params).fetchall()
    return rows_to_list(rows)


# ---------------------------------------------------------------------
# Bitácora de cambios (auditoría — quién hizo qué, sobre qué y cuándo)
# ---------------------------------------------------------------------

def registrar_cambio(
    conn: sqlite3.Connection,
    *,
    usuario: str,
    accion: str,
    entidad: str,
    id_entidad: Any = None,
    referencia: str | None = None,
    detalle: str | None = None,
    nombre_usuario: str | None = None,
    rol: str | None = None,
) -> dict:
    """Inserta un registro en la bitácora de cambios (tabla
    `bitacora_cambio`): quién (`usuario`, cuenta de `usuario_sistema`
    declarada por el cliente — ver `backend/app/auth.py::usuario_actual`),
    qué acción ('alta' | 'edicion' | 'baja' | 'atencion' | 'ejecucion'),
    sobre qué entidad ('equipo' | 'alerta' | 'priorizacion' | 'rpa') y
    cuándo (marca de tiempo del servidor, no del cliente).

    Se llama desde los routers de escritura (equipos, alertas,
    renovacion, analitica, rpa) inmediatamente después de que la
    operación de negocio se confirma, para que la bitácora quede
    consistente con los datos que efectivamente cambiaron."""
    fecha_hora = datetime.now().isoformat(timespec="seconds")
    cur = conn.execute(
        """INSERT INTO bitacora_cambio
           (fecha_hora, usuario, nombre_usuario, rol, entidad, id_entidad, referencia, accion, detalle)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            fecha_hora,
            usuario,
            nombre_usuario or None,
            rol or None,
            entidad,
            str(id_entidad) if id_entidad is not None else None,
            referencia,
            accion,
            detalle,
        ),
    )
    row = conn.execute("SELECT * FROM bitacora_cambio WHERE id_bitacora = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


def list_bitacora(
    conn: sqlite3.Connection,
    entidad: str | None = None,
    usuario: str | None = None,
    limite: int = 200,
) -> list[dict]:
    """Lista la bitácora de cambios, más reciente primero. Respalda el
    panel 'Bitácora de cambios' del dashboard (solo Administrador)."""
    query = "SELECT * FROM bitacora_cambio WHERE 1 = 1"
    params: list[Any] = []
    if entidad:
        query += " AND entidad = ?"
        params.append(entidad)
    if usuario:
        query += " AND usuario = ?"
        params.append(usuario)
    query += " ORDER BY id_bitacora DESC LIMIT ?"
    params.append(limite)
    rows = conn.execute(query, params).fetchall()
    return rows_to_list(rows)
