"""
Autenticación por token — RNF-03 (Sprint 1: "El acceso a la API debe
restringirse mediante autenticación basada en token").

"""

from __future__ import annotations

import os
from functools import wraps
from urllib.parse import unquote

from flask import jsonify, request

API_TOKEN = os.environ.get("CIBERTEC_API_TOKEN", "cibertec-demo-2026")

# Rutas que no requieren autenticación (health check y front-end estático)
RUTAS_PUBLICAS = {"/api/salud"}


def require_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer ") or header.split(" ", 1)[1] != API_TOKEN:
            return jsonify({"error": "No autorizado. Se requiere token Bearer válido."}), 401
        return f(*args, **kwargs)

    return wrapper


def require_admin(f):
    """Control de acceso por rol (RF-01, extensión de la gestión de
    usuarios): las operaciones que modifican datos (alta/edición/baja de
    equipos) o disparan procesos (RPA, motor analítico) requieren una
    cuenta con rol 'Administrador'.

    Igual que el token estático de `require_token`, el rol se recibe en
    un encabezado que declara el propio cliente (`X-Rol`, escrito por
    `frontend/app.js` a partir del rol que devolvió `/api/auth/login`) —
    es una segunda barrera de UI/rol, no un reemplazo de autenticación
    real por usuario. Sirve para que un usuario con acceso "Limitado" no
    pueda ejecutar estas acciones aunque manipule la interfaz, aun
    cuando la app de escritorio siga usando el mismo token de API
    compartido (ver sección de trabajo futuro del README)."""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-Rol") != "Administrador":
            return jsonify({"error": "Acción restringida a usuarios con rol Administrador."}), 403
        return f(*args, **kwargs)

    return wrapper


def usuario_actual() -> dict:
    """Identidad declarada por el cliente para la BITÁCORA DE CAMBIOS
    (registro de quién ejecutó cada alta/edición/baja), no para
    autenticación. Se toma de los encabezados `X-Usuario` /
    `X-Nombre-Usuario`, que `frontend/app.js` agrega automáticamente a
    partir de la cuenta con la que se inició sesión (misma información
    que devuelve `POST /api/auth/login` y que ya se usa, vía `X-Rol`,
    para `require_admin`).

    Igual que el token estático y que `X-Rol`, esto es información que
    declara el propio cliente: no está firmada ni verificada
    criptográficamente por el servidor, por lo que en este prototipo la
    bitácora registra fielmente "con qué cuenta se hizo el cambio",
    pero no ofrece la garantía de identidad de una autenticación de
    producción (ver sección 11, trabajo futuro, del README). Cuando el
    encabezado no llega (por ejemplo, una llamada directa a la API sin
    pasar por el dashboard, como el bot RPA de terminal) se registra
    como `"sistema"` en vez de dejar el campo vacío."""
    def _decodificar(valor: str) -> str:
        # frontend/app.js codifica estos encabezados con
        # encodeURIComponent porque los encabezados HTTP no son UTF-8
        # nativo (un nombre con tildes/ñ llegaría corrupto sin esto).
        try:
            return unquote(valor)
        except Exception:
            return valor

    return {
        "usuario": _decodificar(request.headers.get("X-Usuario") or "") or "sistema",
        "nombre_usuario": _decodificar(request.headers.get("X-Nombre-Usuario") or ""),
        "rol": request.headers.get("X-Rol") or "",
    }
