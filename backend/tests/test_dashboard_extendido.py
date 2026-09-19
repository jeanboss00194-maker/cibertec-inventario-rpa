"""
Pruebas del backend agregado para el dashboard multi-sección (login)
"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.tests.test_api import BaseAPITest  # noqa: E402


class TestCrudEquipos(BaseAPITest):
    def test_crear_editar_eliminar_equipo(self):
        payload = {
            "id_espacio": self._id_espacio_disponible(),
            "codigo_activo_case": "CASE-NUEVO-001",
            "tipo_pc": "Desktop",
            "marca": "HP",
            "modelo": "ProDesk",
        }
        resp = self.client.post("/api/equipos", headers=self.headers_admin, json=payload)
        self.assertEqual(resp.status_code, 201)
        id_equipo = resp.get_json()["id_equipo"]

        resp = self.client.patch(f"/api/equipos/{id_equipo}", headers=self.headers_admin,
                                  json={"estado_case": "Inoperativo"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["estado_case"], "Inoperativo")

        resp = self.client.get(f"/api/equipos/{id_equipo}", headers=self.headers)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.delete(f"/api/equipos/{id_equipo}", headers=self.headers_admin)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(f"/api/equipos/{id_equipo}", headers=self.headers)
        self.assertEqual(resp.status_code, 404)

    def test_crear_equipo_con_codigo_duplicado_devuelve_409(self):
        payload = {
            "id_espacio": self._id_espacio_disponible(),
            "codigo_activo_case": "CASE-TEST-001",  # ya sembrado en BaseAPITest
            "tipo_pc": "Desktop", "marca": "HP", "modelo": "ProDesk",
        }
        resp = self.client.post("/api/equipos", headers=self.headers_admin, json=payload)
        self.assertEqual(resp.status_code, 409)

    def test_crear_equipo_con_espacio_inexistente_devuelve_422(self):
        payload = {"id_espacio": 999999, "codigo_activo_case": "CASE-X", "tipo_pc": "Desktop",
                   "marca": "HP", "modelo": "ProDesk"}
        resp = self.client.post("/api/equipos", headers=self.headers_admin, json=payload)
        self.assertEqual(resp.status_code, 422)

    def _id_espacio_disponible(self):
        from backend.app.database import session
        with session() as conn:
            return conn.execute("SELECT id_espacio FROM espacio LIMIT 1").fetchone()[0]


class TestActividadReciente(BaseAPITest):
    def test_devuelve_lista_ordenada(self):
        self._post_conciliacion(self.ids_equipos[0], cantidad_encontrada=1)
        resp = self.client.get("/api/actividad-reciente?limite=5", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        datos = resp.get_json()
        self.assertLessEqual(len(datos), 5)
        self.assertTrue(any(d["tipo"] == "conciliacion" for d in datos))


class TestRPAEnLinea(BaseAPITest):
    """Botones 'Generar conteo de ejemplo' y 'Ejecutar Robot' del panel
    Automatización RPA — misma lógica que rpa_bot/bot_conciliacion.py,
    ejecutada en proceso en lugar de por HTTP externo."""

    def test_generar_conteo_y_ejecutar_robot(self):
        resp = self.client.post("/api/rpa/generar-conteo", headers=self.headers_admin, json={"trimestre": "oct"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["total"], 20)  # 20 equipos sembrados en BaseAPITest

        resp = self.client.post("/api/rpa/ejecutar", headers=self.headers_admin, json={"trimestre": "oct"})
        self.assertEqual(resp.status_code, 200)
        resultado = resp.get_json()
        self.assertEqual(resultado["total"], 20)
        self.assertEqual(resultado["errores"], [])
        self.assertIn("bitacora", resultado)
        self.assertGreater(len(resultado["bitacora"]), 0)

    def test_ejecutar_con_archivo_csv_subido(self):
        csv_contenido = (
            "codigo_activo_case,cantidad_esperada,cantidad_encontrada,estado_reportado,asistente,sede_reportada\n"
            "CASE-TEST-001,1,0,Faltante,Asistente de Prueba,Independencia\n"
        )
        data = {"archivo": (io.BytesIO(csv_contenido.encode("utf-8")), "conteo.csv"), "trimestre": "oct"}
        resp = self.client.post("/api/rpa/ejecutar", headers=self.headers_admin,
                                 data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        resultado = resp.get_json()
        self.assertEqual(resultado["total"], 1)
        self.assertEqual(resultado["con_discrepancia"], 1)
        self.assertEqual(resultado["alertas_generadas"], 1)

    def test_ejecutar_sin_archivo_previo_devuelve_400(self):
        # El archivo de conteo vive en una ruta fija en disco (no aislada
        # por prueba, a diferencia de la BD temporal), así que se borra
        # explícitamente aquí para simular con certeza el caso "aún no se
        # generó ni subió ningún conteo".
        from backend.app import rpa_engine
        rpa_engine.ARCHIVO_CONTEO.unlink(missing_ok=True)

        resp = self.client.post("/api/rpa/ejecutar", headers=self.headers_admin, json={"trimestre": "oct"})
        self.assertEqual(resp.status_code, 400)


class TestAnaliticaEnLinea(BaseAPITest):
    def test_ejecutar_motor_actualiza_equipos(self):
        resp = self.client.post("/api/analitica/ejecutar", headers=self.headers_admin, json={})
        self.assertEqual(resp.status_code, 200)
        datos = resp.get_json()
        self.assertEqual(datos["equipos_actualizados"], 20)
        self.assertIn("distribucion_prioridad", datos)
        self.assertIn("top10", datos)

        resp = self.client.get("/api/priorizacion-renovacion?top=20", headers=self.headers)
        prior = resp.get_json()
        self.assertTrue(all(p["score_renovacion"] is not None for p in prior))


class TestAutenticacionUsuarios(BaseAPITest):
    """POST /api/auth/login contra la tabla `usuario_sistema` — respalda
    la pantalla de acceso (login.html) del sistema multi-sección."""

    def test_login_administrador_devuelve_rol_correcto(self):
        resp = self.client.post("/api/auth/login", headers=self.headers,
                                 json={"usuario": "admin.prueba", "clave": "clave123"})
        self.assertEqual(resp.status_code, 200)
        datos = resp.get_json()
        self.assertEqual(datos["rol"], "Administrador")
        self.assertEqual(datos["nombre_completo"], "Admin de Prueba")

    def test_login_es_insensible_a_mayusculas_en_el_usuario(self):
        resp = self.client.post("/api/auth/login", headers=self.headers,
                                 json={"usuario": "ADMIN.PRUEBA", "clave": "clave123"})
        self.assertEqual(resp.status_code, 200)

    def test_login_clave_incorrecta_devuelve_401(self):
        resp = self.client.post("/api/auth/login", headers=self.headers,
                                 json={"usuario": "admin.prueba", "clave": "incorrecta"})
        self.assertEqual(resp.status_code, 401)

    def test_login_cuenta_inactiva_devuelve_401(self):
        resp = self.client.post("/api/auth/login", headers=self.headers,
                                 json={"usuario": "inactivo.prueba", "clave": "clave123"})
        self.assertEqual(resp.status_code, 401)

    def test_login_campos_faltantes_devuelve_400(self):
        resp = self.client.post("/api/auth/login", headers=self.headers, json={"usuario": "admin.prueba"})
        self.assertEqual(resp.status_code, 400)

    def test_listado_de_usuarios_requiere_rol_administrador(self):
        resp = self.client.get("/api/usuarios", headers=self.headers_limitado)
        self.assertEqual(resp.status_code, 403)
        resp = self.client.get("/api/usuarios", headers=self.headers_admin)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(any(u["usuario"] == "admin.prueba" for u in resp.get_json()))


class TestControlDeAccesoPorRol(BaseAPITest):
    """Una cuenta con rol 'Limitado' no puede modificar el inventario ni
    disparar el bot RPA o el motor analítico desde la interfaz — la
    interfaz oculta esas acciones, y la API las rechaza igual si de
    todos modos se invocan (auth.py::require_admin)."""

    def test_alta_de_equipo_rechazada_sin_rol_administrador(self):
        payload = {
            "id_espacio": self._id_espacio_disponible(),
            "codigo_activo_case": "CASE-LIMITADO-001",
            "tipo_pc": "Desktop", "marca": "HP", "modelo": "ProDesk",
        }
        resp = self.client.post("/api/equipos", headers=self.headers_limitado, json=payload)
        self.assertEqual(resp.status_code, 403)

        resp = self.client.post("/api/equipos", headers=self.headers, json=payload)  # sin X-Rol en absoluto
        self.assertEqual(resp.status_code, 403)

    def test_ejecutar_rpa_rechazado_sin_rol_administrador(self):
        resp = self.client.post("/api/rpa/generar-conteo", headers=self.headers_limitado, json={"trimestre": "oct"})
        self.assertEqual(resp.status_code, 403)

    def test_ejecutar_analitica_rechazado_sin_rol_administrador(self):
        resp = self.client.post("/api/analitica/ejecutar", headers=self.headers_limitado, json={})
        self.assertEqual(resp.status_code, 403)

    def test_lectura_de_equipos_permitida_con_rol_limitado(self):
        # Las consultas (GET) no requieren rol Administrador — un usuario
        # "Limitado" sí debe poder ver el inventario, solo no modificarlo.
        resp = self.client.get("/api/equipos", headers=self.headers_limitado)
        self.assertEqual(resp.status_code, 200)

    def _id_espacio_disponible(self):
        from backend.app.database import session
        with session() as conn:
            return conn.execute("SELECT id_espacio FROM espacio LIMIT 1").fetchone()[0]


if __name__ == "__main__":
    unittest.main()
