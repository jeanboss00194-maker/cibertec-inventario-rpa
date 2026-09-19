"""
Catálogo único de sedes y resolución de nombres alternativos.

"""

from __future__ import annotations

CATALOGO_SEDES = [
    "Arequipa",
    "Breña",
    "Callao",
    "Independencia",
    "Lima Centro",
    "San Juan de Lurigancho",
    "Trujillo",
]

# Nombres alternativos / informales detectados en el archivo institucional
ALIAS_SEDES = {
    "sede norte": "Independencia",
    "sede bellavista": "Callao",
}

_CANONICOS_LOWER = {s.lower(): s for s in CATALOGO_SEDES}


def resolver_sede(nombre: str) -> str:
    """
    Normaliza un nombre de sede (canónico o alternativo) al nombre
    único del catálogo. Lanza ValueError si no se reconoce.
    """
    clave = nombre.strip().lower()
    if clave in _CANONICOS_LOWER:
        return _CANONICOS_LOWER[clave]
    if clave in ALIAS_SEDES:
        return ALIAS_SEDES[clave]
    raise ValueError(
        f"Sede '{nombre}' no reconocida en el catálogo único. "
        f"Sedes válidas: {', '.join(CATALOGO_SEDES)} "
        f"(alias conocidos: {', '.join(ALIAS_SEDES)})"
    )
