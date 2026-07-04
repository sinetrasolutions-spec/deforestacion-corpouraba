"""Configuración del API: rutas de datos, CORS y selección de repositorio."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import Request

logger = logging.getLogger("observatorio")

VERSION = "1.0.0"

# Raíz del proyecto: backend/app/config.py → ../../ = observatorio-deforestacion
_RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

#: Carpeta de datos procesados; sobreescribible con la variable de entorno DATA_DIR.
DATA_DIR = Path(os.environ.get("DATA_DIR", str(_RAIZ_PROYECTO / "data" / "processed")))

#: Cadena de conexión opcional a PostgreSQL/PostGIS. Si está vacía se usan archivos.
DATABASE_URL: str | None = os.environ.get("DATABASE_URL") or None

#: Orígenes CORS permitidos, separados por coma en la env CORS_ORIGINS.
CORS_ORIGINS: list[str] = [
    origen.strip()
    for origen in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origen.strip()
]


def crear_repositorio():
    """Crea el repositorio de datos.

    Si hay DATABASE_URL intenta PostGIS (import perezoso); si la conexión o las
    dependencias fallan, registra un warning y cae al modo archivos (default).
    """
    if DATABASE_URL:
        try:
            from .repository_postgis import RepositorioPostgis

            repo = RepositorioPostgis(DATABASE_URL)
            logger.info("Repositorio PostGIS activo (%s).", DATABASE_URL.split("@")[-1])
            return repo
        except Exception as exc:  # noqa: BLE001 — cualquier fallo implica fallback
            logger.warning("PostGIS no disponible (%s); usando archivos.", exc)
    from .repository import RepositorioArchivos

    return RepositorioArchivos(DATA_DIR)


def obtener_repositorio(request: Request):
    """Dependencia FastAPI: devuelve el repositorio creado en el lifespan."""
    return request.app.state.repo
