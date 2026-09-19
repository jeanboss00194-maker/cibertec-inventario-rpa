"""
Ejecución:
    python -m unittest discover -s backend/tests -v
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app import database as db_module  # noqa: E402
from backend.app.auth import API_TOKEN  # noqa: E402
from backend.app.database import init_db, session  # noqa: E402


class BaseAPITest(unittest.TestCase):
    """Crea una base de datos temporal con un padrón mínimo de prueba."""

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp()
        db_module.DB_PATH = Path(self._tmp_dir) / "test.db"

        init_db(reset=True)
        self._sembrar_padron_minimo()

        from backend.app.main import create_app  # import diferido: usa DB_PATH ya parcheado

        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        self.headers = {"Authorization": f"Bearer {API_TOKEN}"}
        # Variantes con el encabezado de rol (auth.py::require_admin) para
        # los endpoints que modifican datos o disparan procesos (CRUD de
        # equipos, RPA, motor analítico) — ver TestControlDeAccesoPorRol.
        # Los encabezados X-Usuario/X-Nombre-Usuario reproducen lo que
        # frontend/app.js agrega automáticamente a partir de la cuenta con
        # la que se inició sesión (ver auth.py::usuario_actual): permiten
        # probar que la bitácora de cambios (backend/tests/test_bitacora.py)
        # queda asociada a la cuenta correcta, no solo al rol.
        self.headers_admin = {
            **self.headers, "X-Rol": "Administrador",
            "X-Usuario": "admin.prueba", "X-Nombre-Usuario": "Admin de Prueba",
        }
        self.headers_limitado = {
            **self.headers, "X-Rol": "Limitado",
            "X-Usuario": "limitado.prueba", "X-Nombre-Usuario": "Limitado de Prueba",
        }

    def tearDown(self):
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _sembrar_padron_minimo(self):
        """20 equipos en una sede, 1 asistente — suficiente para los CP definidos."""
        with session() as conn:
            conn.execute("INSERT INTO sede (nombre, ciudad) VALUES ('Independencia', 'Lima')")
            id_sede = conn.execute("SELECT id_sede FROM sede").fetchone()[0]
            conn.execute(
                """INSERT INTO espacio (id_sede, codigo_aula, capacidad, tipo_ambiente)
                   VALUES (?, 'IND-101', 30, 'Laboratorio')""",
                (id_sede,),
            )
            id_espacio = conn.execute("SELECT id_espacio FROM espacio").fetchone()[0]
            conn.execute(
                "INSERT INTO asistente (nombre, sede_asignada) VALUES ('Asistente de Prueba', 'Independencia')"
            )
            self.id_asistente = conn.execute("SELECT id_asistente FROM asistente").fetchone()[0]

            conn.executemany(
                """INSERT INTO usuario_sistema (nombre_completo, usuario, clave, rol, activo)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    ("Admin de Prueba", "admin.prueba", "clave123", "Administrador", 1),
                    ("Limitado de Prueba", "limitado.prueba", "clave123", "Limitado", 1),
                    ("Cuenta Inactiva", "inactivo.prueba", "clave123", "Limitado", 0),
                ],
            )

            self.ids_equipos = []
            for i in range(1, 21):
                cur = conn.execute(
                    """INSERT INTO equipo
                       (id_espacio, codigo_activo_case, service_tag_case, tipo_pc, categoria,
                        marca, modelo, anio_recepcion, anios_uso, leasing_o_propio)
                       VALUES (?, ?, ?, 'Workstation', 'Avanzada', 'HP', 'Z2', 2020, 6, 'Propio')""",
                    (id_espacio, f"CASE-TEST-{i:03d}", f"TAG-{i:03d}"),
                )
                self.ids_equipos.append(cur.lastrowid)

    def _post_conciliacion(self, id_equipo, cantidad_encontrada, estado_reportado="Operativo", trimestre="ene"):
        return self.client.post(
            "/api/conciliaciones",
            headers=self.headers,
            json={
                "id_equipo": id_equipo,
                "id_asistente": self.id_asistente,
                "trimestre": trimestre,
                "cantidad_esperada": 1,
                "cantidad_encontrada": cantidad_encontrada,
                "estado_reportado": estado_reportado,
            },
        )


class TestAutenticacion(BaseAPITest):
    """RNF-03 (Sprint 1): la API debe exigir un token Bearer válido."""

    def test_sin_token_devuelve_401(self):
        resp = self.client.get("/api/sedes")
        self.assertEqual(resp.status_code, 401)

    def test_token_invalido_devuelve_401(self):
        resp = self.client.get("/api/sedes", headers={"Authorization": "Bearer token-incorrecto"})
        self.assertEqual(resp.status_code, 401)

    def test_token_valido_devuelve_200(self):
        resp = self.client.get("/api/sedes", headers=self.headers)
        self.assertEqual(resp.status_code, 200)


class TestCP01ConciliacionSinDiscrepancias(BaseAPITest):
    """CP-01 (Bot RPA): conciliar una sede sin discrepancias -> 0 alertas."""

    def test_conciliacion_sin_discrepancias_no_genera_alertas(self):
        for id_equipo in self.ids_equipos:
            resp = self._post_conciliacion(id_equipo, cantidad_encontrada=1, estado_reportado="Operativo")
            self.assertEqual(resp.status_code, 201)
            self.assertEqual(resp.get_json()["alertas_generadas"], [])

        alertas = self.client.get("/api/alertas?estado=activa", headers=self.headers).get_json()
        self.assertEqual(len(alertas), 0)


class TestCP02ConciliacionConDoceDiscrepancias(BaseAPITest):
    """CP-02 (Bot RPA): 12 equipos con diferencia -> 12 alertas registradas."""

    def test_doce_equipos_con_diferencia_generan_doce_alertas(self):
        equipos_con_diferencia = self.ids_equipos[:12]
        equipos_sin_diferencia = self.ids_equipos[12:]

        for id_equipo in equipos_con_diferencia:
            resp = self._post_conciliacion(id_equipo, cantidad_encontrada=0, estado_reportado="Faltante")
            self.assertEqual(resp.status_code, 201)

        for id_equipo in equipos_sin_diferencia:
            resp = self._post_conciliacion(id_equipo, cantidad_encontrada=1, estado_reportado="Operativo")
            self.assertEqual(resp.status_code, 201)

        alertas = self.client.get("/api/alertas?estado=activa", headers=self.headers).get_json()
        self.assertEqual(len(alertas), 12)
        self.assertTrue(all(a["tipo_alerta"] == "faltante" for a in alertas))


class TestCP05CP06API(BaseAPITest):
    """CP-05 / CP-06 (API): POST /api/conciliaciones con datos válidos e inválidos."""

    def test_cp05_post_conciliacion_valida_devuelve_201(self):
        resp = self._post_conciliacion(self.ids_equipos[0], cantidad_encontrada=1)
        self.assertEqual(resp.status_code, 201)
        cuerpo = resp.get_json()
        self.assertIn("id_conciliacion", cuerpo)
        self.assertEqual(cuerpo["diferencia"], 0)

    def test_cp06_post_conciliacion_equipo_inexistente_devuelve_422(self):
        resp = self._post_conciliacion(id_equipo=999999, cantidad_encontrada=1)
        self.assertEqual(resp.status_code, 422)

    def test_post_conciliacion_campos_faltantes_devuelve_400_controlado(self):
        # Regla de negocio incompleta (equivalente, a nivel API, del
        # comportamiento de excepción controlada exigido en CP-03 para el bot.
        resp = self.client.post("/api/conciliaciones", headers=self.headers, json={"id_equipo": 1})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    def test_post_conciliacion_trimestre_invalido_devuelve_400(self):
        resp = self._post_conciliacion(self.ids_equipos[0], cantidad_encontrada=1, trimestre="dic")
        self.assertEqual(resp.status_code, 400)


class TestCP10FlujoExtremoAExtremo(BaseAPITest):
    """CP-10: conteo -> conciliación -> alerta -> panel, para una sede."""

    def test_flujo_completo_una_sede(self):
        import time

        inicio = time.time()

        # 1. "Conteo": se reporta un equipo faltante
        equipo_afectado = self.ids_equipos[0]
        resp = self._post_conciliacion(equipo_afectado, cantidad_encontrada=0, estado_reportado="Faltante", trimestre="oct")
        self.assertEqual(resp.status_code, 201)

        # 2. La alerta debe existir y estar activa
        alertas = self.client.get("/api/alertas?estado=activa", headers=self.headers).get_json()
        self.assertTrue(any(a["id_equipo"] == equipo_afectado for a in alertas))

        # 3. El panel (indicadores) debe reflejar el equipo faltante
        indicadores = self.client.get("/api/indicadores?sede=Independencia", headers=self.headers).get_json()
        self.assertEqual(indicadores["equipos_faltantes_activos"], 1)

        # 4. El motor de priorización puede consumir/actualizar el equipo
        resp_prior = self.client.post(
            "/api/priorizacion-renovacion",
            headers=self.headers,
            json={"resultados": [{"codigo_activo_case": "CASE-TEST-001",
                                   "prioridad_renovacion": "Alta", "score_renovacion": 0.9}]},
        )
        self.assertEqual(resp_prior.status_code, 200)

        duracion = time.time() - inicio
        self.assertLess(duracion, 600, "El flujo completo debe tomar menos de 10 minutos (CP-10)")


if __name__ == "__main__":
    unittest.main()
