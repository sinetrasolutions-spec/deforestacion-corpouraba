"""Endpoints geoespaciales: municipios, subregiones, choropleth, hotspots y capas."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from .. import analytics, schemas
from ..config import obtener_repositorio
from ..repository import CLASE_DEFORESTACION, ErrorDatos, RepositorioBase

router = APIRouter(tags=["geo"])


@router.get("/municipios")
def municipios(repo: RepositorioBase = Depends(obtener_repositorio)) -> dict:
    """FeatureCollection de los 19 municipios de la jurisdicción (WGS84)."""
    return repo.municipios_fc


@router.get("/subregiones")
def subregiones(repo: RepositorioBase = Depends(obtener_repositorio)) -> dict:
    """FeatureCollection de las 5 subregiones."""
    return repo.subregiones_fc


@router.get("/choropleth", response_model=schemas.RespuestaChoropleth)
def choropleth(
    periodo: str = Query(..., description="Periodo, p. ej. 2022-2023"),
    metrica: schemas.Metrica = Query("hectareas"),
    repo: RepositorioBase = Depends(obtener_repositorio),
):
    """Valores de deforestación por municipio + breaks (quantiles p20..p100)."""
    try:
        repo.validar_periodo(periodo)
    except ErrorDatos as error:
        raise HTTPException(error.codigo, error.mensaje) from error
    df = repo.serie[
        (repo.serie["clase"] == CLASE_DEFORESTACION) & (repo.serie["periodo"] == periodo)
    ]
    return analytics.construir_choropleth(df, periodo, metrica)


@router.get("/hotspots/{periodo}")
def hotspots(periodo: str, repo: RepositorioBase = Depends(obtener_repositorio)):
    """Polígonos de hotspots del periodo; 404 con la lista de disponibles."""
    fc = repo.hotspots(periodo)
    if fc is None:
        return JSONResponse(
            status_code=404,
            content={
                "detail": f"No hay hotspots para el periodo '{periodo}'.",
                "disponibles": repo.hotspots_disponibles(),
            },
        )
    return fc


@router.get("/parches")
def parches(
    periodo: str | None = Query(None, description="Periodo específico; si se omite, todos"),
    min_ha: float = Query(0.0, ge=0, description="Área mínima del parche en hectáreas"),
    municipio: str | None = Query(None, description="Filtra por municipio (nombre o código DANE)"),
    repo: RepositorioBase = Depends(obtener_repositorio),
):
    """Parches de deforestación (≥1 ha) de uno o todos los periodos, etiquetados
    con periodo/ano_inicio/municipio/ha para el explorador de parches."""
    try:
        return repo.parches(periodo=periodo, min_ha=min_ha, municipio=municipio)
    except ErrorDatos as error:
        raise HTTPException(error.codigo, error.mensaje) from error


@router.get("/capas", response_model=schemas.RespuestaCapas)
def capas(repo: RepositorioBase = Depends(obtener_repositorio)):
    """Catálogo de capas de contexto con su número de unidades."""
    return {"capas": repo.capas_disponibles()}


@router.get("/capas/{id_capa}")
def capa(id_capa: str, repo: RepositorioBase = Depends(obtener_repositorio)) -> dict:
    """FeatureCollection de una capa de contexto (overlay)."""
    try:
        return repo.capa(id_capa)
    except ErrorDatos as error:
        raise HTTPException(error.codigo, error.mensaje) from error
