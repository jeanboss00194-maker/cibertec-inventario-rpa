"""
Pruebas de la bitácora de cambios (auditoría).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.tests.test_api import BaseAPITest  # noqa: E402


class TestBitacoraCrudEquipos(BaseAPITest):
    def test_alta_edicion_y_baja_de_equipo_quedan_en_la_bitacora(self):
        payload = {
            "id_espacio": self._id_espacio_disponible(),
            "codigo_activo_case": "CASE-BITACORA-001",
            "tipo_pc": "Desktop", "marca": "HP", "modelo": "ProDesk",
        }
        resp = self.client.post("/api/equipos", headers=self.headers_admin, json=payload)
        self.assertEqual(resp.status_code, 201)
        id_equipo = resp.get_json()["id_equipo"]

        resp = self.client.patch(f"/api/equipos/{id_equipo}", headers=self.headers_admin,
                                  json={"estado_case": "Inoperativo"})
        self.assertEqual(resp.status_code, 200)

        resp = self.client.delete(f"/api/equipos/{id_equipo}", headers=self.headers_admin)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/api/bitacora?entidad=equipo", headers=self.headers_admin)
        self.assertEqual(resp.status_code, 200)
        registros = [r for r in resp.get_json() if r["referencia"] == "CASE-BITACORA-001"]
        acciones = [r["accion"] for r in registros]

        # Más reciente primero: baja, edición, alta.
        self.assertEqual(acciones, ["baja", "edicion", "alta"])
        self.assertTrue(all(r["usuario"] == "admin.prueba" for r in registros))
        self.assertTrue(all(r["nombre_usuario"] == "Admin de Prueba" for r in registros))
        self.assertTrue(all(r["rol"] == "Administrador" for r in registros))
        self.assertIn("estado_case", next(r["detalle"] for r in registros if r["accion"] == "edicion"))

    def test_edicion_sin_cambios_reales_no_registra_bitacora(self):
        """PATCH con un valor idéntico al actual no debe generar un
        registro de auditoría vacío de significado."""
        payload = {
            "id_espacio": self._id_espacio_disponible(),
            "codigo_activo_case": "CASE-BITACORA-002",
            "tipo_pc": "Desktop", "marca": "HP", "modelo": "ProDesk",
            "estado_case": "Operativo",
        }
        resp = self.client.post("/api/equipos", headers=self.headers_admin, json=payload)
        id_equipo = resp.get_json()["id_equipo"]

        resp = self.client.patch(f"/api/equipos/{id_equipo}", headers=self.headers_admin,
                                  json={"estado_case": "Operativo"})
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/api/bitacora?entidad=equipo", headers=self.headers_admin)
        registros = [r for r in resp.get_json() if r["referencia"] == "CASE-BITACORA-002"]
        self.assertEqual([r["accion"] for r in registros], ["alta"])

    def _id_espacio_disponible(self):
        from backend.app.database import session
        with session() as conn:
            return conn.execute("SELECT id_espacio FROM espacio LIMIT 1").fetchone()[0]


class TestBitacoraAlertasYProcesos(BaseAPITest):
    def test_atencion_de_alerta_queda_en_la_bitacora(self):
        self._post_conciliacion(self.ids_equipos[0], cantidad_encontrada=0, estado_reportado="Faltante")
        id_alerta = self.client.get("/api/alertas?estado=activa", headers=self.headers).get_json()[0]["id_alerta"]

        resp = self.client.post(f"/api/alertas/{id_alerta}/atender", headers=self.headers_admin)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get("/api/bitacora?entidad=alerta", headers=self.headers_admin)
        registros = resp.get_json()
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0]["accion"], "atencion")
        self.assertEqual(registros[0]["usuario"], "admin.prueba")

    def test_ejecucion_de_rpa_y_analitica_quedan_en_la_bitacora(self):
        resp = self.client.post("/api/rpa/generar-conteo", headers=self.headers_admin, json={"trimestre": "oct"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post("/api/rpa/ejecutar", headers=self.headers_admin, json={"trimestre": "oct"})
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post("/api/analitica/ejecutar", headers=self.headers_admin, json={})
        self.assertEqual(resp.status_code, 200)

        registros = self.client.get("/api/bitacora", headers=self.headers_admin).get_json()
        entidades = [r["entidad"] for r in registros]
        self.assertIn("rpa", entidades)
        self.assertIn("priorizacion", entidades)
        self.assertTrue(all(r["usuario"] == "admin.prueba" for r in registros
                             if r["entidad"] in ("rpa", "priorizacion")))

    def test_conciliacion_por_bot_de_terminal_no_tiene_usuario_del_sistema(self):
        """El bot RPA de terminal (rpa_bot/bot_conciliacion.py) llama a
        /api/conciliaciones directamente por HTTP, sin pasar por el
        dashboard ni por una cuenta de usuario_sistema logueada — por
        eso esa ruta no registra bitácora de cambios (no es un alta/
        edición/baja de equipo, alerta o proceso propio del dashboard).
        Esta prueba documenta esa distinción de forma explícita."""
        resp = self._post_conciliacion(self.ids_equipos[0], cantidad_encontrada=1)
        self.assertEqual(resp.status_code, 201)
        registros = self.client.get("/api/bitacora", headers=self.headers_admin).get_json()
        self.assertEqual(registros, [])


class TestBitacoraControlDeAcceso(BaseAPITest):
    def test_bitacora_requiere_rol_administrador(self):
        resp = self.client.get("/api/bitacora", headers=self.headers_limitado)
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get("/api/bitacora", headers=self.headers)  # sin X-Rol en absoluto
        self.assertEqual(resp.status_code, 403)

        resp = self.client.get("/api/bitacora", headers=self.headers_admin)
        self.assertEqual(resp.status_code, 200)

    def test_sin_x_usuario_se_registra_como_sistema(self):
        """Una llamada que llega con el token válido pero sin el
        encabezado X-Usuario (por ejemplo, un script externo que no pasa
        por el login del dashboard) no debe dejar el campo vacío."""
        payload = {
            "id_espacio": self._id_espacio_disponible(),
            "codigo_activo_case": "CASE-BITACORA-003",
            "tipo_pc": "Desktop", "marca": "HP", "modelo": "ProDesk",
        }
        headers_sin_identidad = {**self.headers, "X-Rol": "Administrador"}
        resp = self.client.post("/api/equipos", headers=headers_sin_identidad, json=payload)
        self.assertEqual(resp.status_code, 201)

        registros = self.client.get("/api/bitacora?entidad=equipo", headers=self.headers_admin).get_json()
        registro = next(r for r in registros if r["referencia"] == "CASE-BITACORA-003")
        self.assertEqual(registro["usuario"], "sistema")

    def _id_espacio_disponible(self):
        from backend.app.database import session
        with session() as conn:
            return conn.execute("SELECT id_espacio FROM espacio LIMIT 1").fetchone()[0]


if __name__ == "__main__":
    unittest.main()
