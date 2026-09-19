#!/usr/bin/env python3
"""
Motor Analítico de Priorización de Renovación — CIBERTEC
===========================================================================

Implementa, con pandas + scikit-learn, el modelo analítico descrito en
el Sprint 3 bajo la metodología CRISP-DM (Chapman et al., 2000)

"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API_URL = "http://127.0.0.1:5000/api"
API_TOKEN = "cibertec-demo-2026"
HEADERS = {"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}

PESO_ANTIGUEDAD = 0.45
PESO_ESTADO = 0.25
PESO_CATEGORIA = 0.15
PESO_INCIDENCIAS = 0.15

MAPA_CATEGORIA_RIESGO = {"Estándar": 1.0, "Avanzada": 0.5}  # equipos "Estándar" son de gama más limitada
MAPA_ESTADO_RIESGO = {"Inoperativo": 1.0, "Operativo": 0.0}


def obtener_equipos() -> pd.DataFrame:
    r = requests.get(f"{API_URL}/equipos", headers=HEADERS, timeout=30)
    r.raise_for_status()
    return pd.DataFrame(r.json())


def obtener_incidencias_por_equipo() -> pd.Series:
    """Cuenta alertas históricas (cualquier estado) por código de activo,
    como proxy del historial de incidencias de cada equipo."""
    r = requests.get(f"{API_URL}/alertas", headers=HEADERS, timeout=30)
    r.raise_for_status()
    alertas = pd.DataFrame(r.json())
    if alertas.empty:
        return pd.Series(dtype=int)
    return alertas.groupby("codigo_activo_case").size()


def calcular_prioridad(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["riesgo_categoria"] = df["categoria"].map(MAPA_CATEGORIA_RIESGO).fillna(0.5)
    df["riesgo_estado"] = df["estado_case"].map(MAPA_ESTADO_RIESGO).fillna(0.0)

    escalador = MinMaxScaler()
    df[["antiguedad_norm", "incidencias_norm"]] = escalador.fit_transform(
        df[["anios_uso", "n_incidencias"]]
    )

    df["score_renovacion"] = (
        PESO_ANTIGUEDAD * df["antiguedad_norm"]
        + PESO_ESTADO * df["riesgo_estado"]
        + PESO_CATEGORIA * df["riesgo_categoria"]
        + PESO_INCIDENCIAS * df["incidencias_norm"]
    ).round(4)

    percentil = df["score_renovacion"].rank(method="average", pct=True)
    df["prioridad_renovacion"] = pd.cut(
        percentil, bins=[0, 1 / 3, 2 / 3, 1.0001], labels=["Baja", "Media", "Alta"], include_lowest=True,
    ).astype(str)

    X = df[["antiguedad_norm", "riesgo_estado", "riesgo_categoria", "incidencias_norm"]].values
    n_clusters = min(3, len(np.unique(X, axis=0)))
    if n_clusters >= 2:
        kmeans = KMeans(n_clusters=n_clusters, random_state=2026, n_init=10)
        df["cluster"] = kmeans.fit_predict(X)
    else:
        df["cluster"] = 0

    return df


def publicar_resultados(df: pd.DataFrame) -> dict:
    resultados = df[["codigo_activo_case", "prioridad_renovacion", "score_renovacion"]].to_dict(
        orient="records"
    )
    r = requests.post(
        f"{API_URL}/priorizacion-renovacion", headers=HEADERS,
        json={"resultados": resultados}, timeout=30,
    )
    r.raise_for_status()
    return r.json()


def ejecutar():
    print("=" * 70)
    print(" Motor Analítico de Priorización de Renovación (CRISP-DM) — CIBERTEC")
    print("=" * 70)

    print("Extrayendo equipos desde la API...")
    equipos = obtener_equipos()
    print(f"  {len(equipos)} equipos obtenidos.")

    print("Extrayendo historial de incidencias (alertas)...")
    incidencias = obtener_incidencias_por_equipo()
    equipos["n_incidencias"] = equipos["codigo_activo_case"].map(incidencias).fillna(0).astype(int)

    print("Calculando índice compuesto de riesgo y clustering de validación (KMeans, k=3)...")
    resultado = calcular_prioridad(equipos)

    print("\nDistribución de prioridad de renovación calculada:")
    print(resultado["prioridad_renovacion"].value_counts().to_string())

    print("\nTop 10 equipos con mayor prioridad de renovación:")
    top10 = resultado.sort_values("score_renovacion", ascending=False).head(10)
    print(top10[["codigo_activo_case", "nombre_sede", "tipo_pc", "anios_uso",
                 "estado_case", "score_renovacion", "prioridad_renovacion"]].to_string(index=False))

    print("\nPublicando resultados en la API (POST /api/priorizacion-renovacion)...")
    respuesta = publicar_resultados(resultado)
    print(f"  {respuesta['equipos_actualizados']} equipos actualizados en la base de datos.")
    print("=" * 70)


if __name__ == "__main__":
    ejecutar()
