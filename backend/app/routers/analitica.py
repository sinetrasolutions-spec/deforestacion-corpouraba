"""Endpoints analíticos: KPIs, ranking y predicción."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .. import analytics, schemas
from ..config import obtener_repositorio
from ..repository import CLASE_DEFORESTACION, ErrorDatos, RepositorioBase

router = APIRouter(tags=["analítica"])


def _defo(repo: RepositorioBase):
    """Filas de la clase Deforestación de la serie municipal."""
    return repo.serie[repo.serie["clase"] == CLASE_DEFORESTACION]


@router.get("/kpis", response_model=schemas.Kpis)
def kpis(
    incluir_estimados: bool = Query(True),
    repo: RepositorioBase = Depends(obtener_repositorio),
):
    """Indicadores clave regionales 2000–2024."""
    return analytics.calcular_kpis(_defo(repo), incluir_estimados)


@router.get("/ranking", response_model=schemas.RespuestaRanking)
def ranking(
    periodo: str | None = Query(None, description="Sin periodo: acumulado 2000–2024"),
    n: int = Query(10, ge=1, le=19),
    metrica: schemas.Metrica = Query("hectareas"),
    repo: RepositorioBase = Depends(obtener_repositorio),
):
    """Top-n de municipios más deforestados, por periodo o acumulado."""
    if periodo is not None:
        try:
            repo.validar_periodo(periodo)
        except ErrorDatos as error:
            raise HTTPException(error.codigo, error.mensaje) from error
    return {"data": analytics.calcular_ranking(_defo(repo), periodo, n, metrica)}


@router.get("/prediccion", response_model=schemas.RespuestaPrediccion)
def prediccion(
    municipio: str | None = Query(None, description="Código DANE o nombre; vacío = regional"),
    horizonte: int = Query(3, ge=1, le=5),
    incluir_estimados: bool = Query(False),
    repo: RepositorioBase = Depends(obtener_repositorio),
):
    """Proyección de la tasa anual de deforestación (regresión lineal)."""
    try:
        if municipio:
            codigo = repo.resolver_municipio(municipio)
            base = repo.serie_municipio(codigo, CLASE_DEFORESTACION)
        else:
            base = repo.serie_regional(CLASE_DEFORESTACION, incluir_estimados=True)
    except ErrorDatos as error:
        raise HTTPException(error.codigo, error.mensaje) from error

    columnas = ["periodo", "ano_inicio", "ano_fin", "hectareas_anuales", "estimado"]
    return analytics.calcular_prediccion(base[columnas], horizonte, incluir_estimados)
