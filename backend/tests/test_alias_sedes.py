"""
CP-04 (Sprint 5, módulo Bot RPA): "Registrar una sede con nomenclatura
no estándar ('Sede Norte') -> el bot la resuelve contra el catálogo
único como 'Independencia'".
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.alias_sedes import CATALOGO_SEDES, resolver_sede  # noqa: E402


class TestCP04ResolucionDeSedes(unittest.TestCase):
    def test_resuelve_sede_norte_a_independencia(self):
        self.assertEqual(resolver_sede("Sede Norte"), "Independencia")

    def test_resuelve_sede_bellavista_a_callao(self):
        self.assertEqual(resolver_sede("Sede Bellavista"), "Callao")

    def test_nombres_canonicos_pasan_sin_cambios(self):
        for sede in CATALOGO_SEDES:
            self.assertEqual(resolver_sede(sede), sede)

    def test_es_insensible_a_mayusculas_y_espacios(self):
        self.assertEqual(resolver_sede("  sede NORTE  "), "Independencia")
        self.assertEqual(resolver_sede("sede bellavista"), "Callao")

    def test_nombre_no_reconocido_lanza_valueerror(self):
        with self.assertRaises(ValueError):
            resolver_sede("Sede Inexistente XYZ")

    def test_catalogo_tiene_las_siete_sedes_de_cibertec(self):
        self.assertEqual(len(CATALOGO_SEDES), 7)
        for nombre in ["Arequipa", "Breña", "Callao", "Independencia",
                       "Lima Centro", "San Juan de Lurigancho", "Trujillo"]:
            self.assertIn(nombre, CATALOGO_SEDES)


if __name__ == "__main__":
    unittest.main()
