"""Aplicación FastAPI del Observatorio de Deforestación CORPOURABA."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from . import config, schemas
from .config import crear_repositorio, obtener_repositorio
from .repository import RepositorioBase
from .routers import analisis, analitica, descargas, geo, series

PREFIJO = "/api/v1"


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Carga el repositorio de datos al arrancar (archivos o PostGIS)."""
    app.state.repo = crear_repositorio()
    yield


app = FastAPI(
    title="API Observatorio Deforestación CORPOURABA",
    version=config.VERSION,
    lifespan=ciclo_de_vida,
)

# CORS: orígenes desde env CORS_ORIGINS; con '*' no se permiten credenciales
_permitir_todo = "*" in config.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _permitir_todo else config.CORS_ORIGINS,
    allow_credentials=not _permitir_todo,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def raiz() -> RedirectResponse:
    """La raíz redirige a la documentación interactiva."""
    return RedirectResponse("/docs")


@app.get(f"{PREFIJO}/salud", response_model=schemas.Salud, tags=["sistema"])
def salud(repo: RepositorioBase = Depends(obtener_repositorio)):
    """Latido del servicio y modo de datos activo."""
    return {"estado": "ok", "version": config.VERSION, "modo_datos": repo.modo}


@app.get(f"{PREFIJO}/metadata", tags=["sistema"])
def metadata(repo: RepositorioBase = Depends(obtener_repositorio)) -> dict:
    """Contenido íntegro de metadata.json (diccionario y metodología)."""
    return repo.metadata


@app.get(f"{PREFIJO}/periodos", response_model=list[schemas.Periodo], tags=["sistema"])
def periodos(repo: RepositorioBase = Depends(obtener_repositorio)):
    """Los 18 periodos de monitoreo con su fuente y disponibilidad de hotspots."""
    return repo.periodos()


app.include_router(geo.router, prefix=PREFIJO)
app.include_router(series.router, prefix=PREFIJO)
app.include_router(analitica.router, prefix=PREFIJO)
app.include_router(analisis.router, prefix=PREFIJO)
app.include_router(descargas.router, prefix=PREFIJO)
