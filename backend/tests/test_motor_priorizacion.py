"""
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd  # noqa: E402

from analitica.motor_priorizacion import calcular_prioridad  # noqa: E402


def _equipo(codigo, anios, categoria, estado, incidencias):
    return {
        "codigo_activo_case": codigo,
        "anios_uso": anios,
        "categoria": categoria,
        "estado_case": estado,
        "n_incidencias": incidencias,
        "nombre_sede": "Lima Centro",
        "tipo_pc": "Workstation",
    }


class TestCP09MotorDePriorizacion(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame([
            _equipo("E01", 0, "Avanzada", "Operativo", 0),
            _equipo("E02", 1, "Avanzada", "Operativo", 0),
            _equipo("E03", 1, "Avanzada", "Operativo", 1),
            _equipo("E04", 2, "Avanzada", "Operativo", 0),
            _equipo("E05", 7, "Estándar", "Operativo", 1),
            _equipo("E06", 8, "Estándar", "Operativo", 2),
            _equipo("E07", 9, "Estándar", "Inoperativo", 3),
            _equipo("E08", 10, "Estándar", "Inoperativo", 4),
            _equipo("E09", 11, "Estándar", "Inoperativo", 4),
            _equipo("E10", 12, "Estándar", "Inoperativo", 5),
            _equipo("E11", 0, "Avanzada", "Operativo", 0),
            _equipo("E12", 6, "Estándar", "Operativo", 1),
        ])

    def test_scores_en_rango_valido(self):
        resultado = calcular_prioridad(self.df)
        self.assertTrue((resultado["score_renovacion"] >= 0).all())
        self.assertTrue((resultado["score_renovacion"] <= 1).all())

    def test_equipos_de_mayor_riesgo_tienen_mayor_score_promedio(self):
        resultado = calcular_prioridad(self.df)
        riesgo_alto = resultado[(resultado["anios_uso"] >= 9) & (resultado["estado_case"] == "Inoperativo")]
        riesgo_bajo = resultado[(resultado["anios_uso"] <= 1) & (resultado["estado_case"] == "Operativo")]
        self.assertGreater(riesgo_alto["score_renovacion"].mean(), riesgo_bajo["score_renovacion"].mean())

    def test_prioridad_alta_tiene_mayor_score_promedio_que_baja(self):
        resultado = calcular_prioridad(self.df)
        promedios = resultado.groupby("prioridad_renovacion")["score_renovacion"].mean()
        if "Alta" in promedios.index and "Baja" in promedios.index:
            self.assertGreater(promedios["Alta"], promedios["Baja"])

    def test_las_tres_etiquetas_de_prioridad_son_validas(self):
        resultado = calcular_prioridad(self.df)
        self.assertTrue(set(resultado["prioridad_renovacion"].unique()).issubset({"Alta", "Media", "Baja"}))


if __name__ == "__main__":
    unittest.main()
