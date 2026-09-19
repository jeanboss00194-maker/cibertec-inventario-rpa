"""
Pruebas de INTEGRACIÓN (no unitarias): requieren el servidor Flask real
corriendo en http://127.0.0.1:5000 
"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

API_URL = "http://127.0.0.1:5000/api"
API_TOKEN = "cibertec-demo-2026"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


def _servidor_disponible() -> bool:
    try:
        r = requests.get(f"{API_URL}/salud", timeout=1.5)
        return r.status_code == 200
    except requests.RequestException:
        return False


_SERVIDOR_ACTIVO = _servidor_disponible()


@unittest.skipUnless(
    _SERVIDOR_ACTIVO,
    "Requiere el servidor Flask activo — ejecute 'python run.py' en otra terminal antes de correr esta prueba.",
)
class TestIntegracionRPA(unittest.TestCase):
    def test_cp03_fila_con_asistente_inexistente_no_detiene_el_proceso(self):
        """CP-03: 'Simular formulario de conteo físico incompleto' -> excepción
        de negocio controlada, sin caída del proceso."""
        from rpa_bot.bot_conciliacion import ErrorTransaccion, inicializar, procesar_transaccion

        equipos, asistentes = inicializar()
        codigo_valido = next(iter(equipos))
        fila_incompleta = {
            "codigo_activo_case": codigo_valido,
            "cantidad_esperada": "1",
            "cantidad_encontrada": "1",
            "estado_reportado": "Operativo",
            "asistente": "Nombre Que No Está Registrado",
            "sede_reportada": "",
        }
        # La excepción debe ser del tipo controlado del bot (ErrorTransaccion),
        # nunca una excepción no manejada que tumbe el proceso completo — esto
        # es exactamente lo que el bucle principal de ejecutar() captura y
        # continúa procesando la siguiente fila (ver bot_conciliacion.py).
        with self.assertRaises(ErrorTransaccion):
            procesar_transaccion(fila_incompleta, equipos, asistentes, {"resuelto": False})

    def test_cp04_bot_resuelve_alias_de_sede_en_vivo(self):
        """CP-04 contra la API real: un nombre alternativo de sede consistente
        con el registro maestro debe resolverse sin error."""
        from rpa_bot.bot_conciliacion import inicializar, procesar_transaccion

        equipos, asistentes = inicializar()
        equipo_independencia = next(
            (c for c, e in equipos.items() if e["nombre_sede"] == "Independencia"), None
        )
        if equipo_independencia is None:
            self.skipTest("No hay equipos de Independencia cargados (ejecute backend/seed.py).")
        asistente_cualquiera = next(iter(asistentes))

        fila = {
            "codigo_activo_case": equipo_independencia,
            "cantidad_esperada": "1",
            "cantidad_encontrada": "1",
            "estado_reportado": "Operativo",
            "asistente": asistente_cualquiera,
            "sede_reportada": "Sede Norte",
        }
        resultado_alias = {"resuelto": False}
        resultado = procesar_transaccion(fila, equipos, asistentes, resultado_alias)
        self.assertEqual(resultado["diferencia"], 0)
        self.assertTrue(resultado_alias["resuelto"])

    def test_cp07_tiempo_de_respuesta_al_filtrar(self):
        """CP-07: 'El panel actualiza en menos de 2 segundos' al aplicar
        filtros de sede y tipo de ambiente — se mide el mismo conjunto de
        llamadas que dispara el frontend (app.js::refrescarTodo)."""
        inicio = time.time()
        requests.get(f"{API_URL}/indicadores?sede=Lima Centro", headers=HEADERS, timeout=5)
        requests.get(f"{API_URL}/priorizacion-renovacion?sede=Lima Centro&top=200", headers=HEADERS, timeout=5)
        requests.get(f"{API_URL}/alertas?estado=activa", headers=HEADERS, timeout=5)
        requests.get(f"{API_URL}/equipos?sede=Lima Centro&tipo_ambiente=Laboratorio", headers=HEADERS, timeout=5)
        duracion = time.time() - inicio
        self.assertLess(duracion, 2.0, f"El panel debe actualizar en menos de 2s (tomó {duracion:.2f}s)")


if __name__ == "__main__":
    unittest.main()
