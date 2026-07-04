"""Endpoints de series temporales: municipal, regional y comparación."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from .. import schemas
from ..config import obtener_repositorio
from ..repository import (
    CLASE_DEFORESTACION,
    ErrorDatos,
    RepositorioBase,
    filtrar_serie,
)

router = APIRouter(tags=["series"])

NOTA_EXCLUIDOS = (
    "Se excluyeron los periodos estimados (2010-2012, 2015-2016, 2018-2019 y "
    "2023-2024) del resultado."
)


def _filas_serie(df: pd.DataFrame) -> list[dict]:
    """Convierte el DataFrame filtrado a las filas del contrato (§6 FilaSerie)."""
    return [
        {
            "codigo_dane": str(fila.codigo_dane),
            "municipio": fila.municipio,
            "subregion": fila.subregion,
            "periodo": fila.periodo,
            "ano_inicio": int(fila.ano_inicio),
            "ano_fin": int(fila.ano_fin),
            "clase": fila.clase,
            "hectareas": round(float(fila.hectareas), 2),
            "hectareas_anuales": round(float(fila.hectareas_anuales), 2),
            "fuente": fila.fuente,
            "estimado": bool(fila.estimado),
        }
        for fila in df.itertuples(index=False)
    ]


def _nota_serie(df: pd.DataFrame, incluir_estimados: bool, metadata: dict) -> str | None:
    """Nota metodológica: presente si hay estimados o si fueron excluidos."""
    if not incluir_estimados:
        return NOTA_EXCLUIDOS
    if not df.empty and bool(df["estimado"].any()):
        return metadata.get(
            "nota_estimados",
            "El resultado incluye periodos estimados (estimado=True).",
        )
    return None


@router.get("/serie", response_model=schemas.RespuestaSerie)
def serie(
    municipio: list[str] | None = Query(
        None, description="Código DANE o nombre; repetible para varios municipios"
    ),
    subregion: str | None = Query(None),
    clase: str = Query(CLASE_DEFORESTACION),
    desde: int | None = Query(None, ge=2000, le=2024, description="Año inicial"),
    hasta: int | None = Query(None, ge=2000, le=2024, description="Año final"),
    incluir_estimados: bool = Query(True),
    repo: RepositorioBase = Depends(obtener_repositorio),
):
    """Serie municipal filtrada, con total en hectáreas y nota metodológica."""
    try:
        df = filtrar_serie(
            repo,
            municipios=municipio,
            subregion=subregion,
            clase=clase,
            desde=desde,
            hasta=hasta,
            incluir_estimados=incluir_estimados,
        )
    except ErrorDatos as error:
        raise HTTPException(error.codigo, error.mensaje) from error

    return {
        "data": _filas_serie(df),
        "total_ha": round(float(df["hectareas"].sum()), 2) if not df.empty else 0.0,
        "nota": _nota_serie(df, incluir_estimados, repo.metadata),
    }


@router.get("/serie/regional", response_model=schemas.RespuestaSerieRegional)
def serie_regional(
    clase: str = Query(CLASE_DEFORESTACION),
    incluir_estimados: bool = Query(True),
    repo: RepositorioBase = Depends(obtener_repositorio),
):
    """Serie agregada de toda la jurisdicción por periodo."""
    try:
        df = repo.serie_regional(clase, incluir_estimados)
    except ErrorDatos as error:
        raise HTTPException(error.codigo, error.mensaje) from error
    return {
        "data": [
            {
                "periodo": fila.periodo,
                "ano_inicio": int(fila.ano_inicio),
                "ano_fin": int(fila.ano_fin),
                "hectareas": round(float(fila.hectareas), 2),
                "hectareas_anuales": round(float(fila.hectareas_anuales), 2),
                "estimado": bool(fila.estimado),
            }
            for fila in df.itertuples(index=False)
        ]
    }


@router.get("/comparacion", response_model=schemas.RespuestaComparacion)
def comparacion(
    municipios: str = Query(
        ..., description="Códigos DANE (o nombres) separados por coma, entre 2 y 6"
    ),
    repo: RepositorioBase = Depends(obtener_repositorio),
):
    """Series anuales de deforestación de 2 a 6 municipios para el comparador."""
    valores = [v.strip() for v in municipios.split(",") if v.strip()]
    if not 2 <= len(valores) <= 6:
        raise HTTPException(422, "Debe indicar entre 2 y 6 municipios separados por coma.")

    data = []
    for valor in valores:
        try:
            codigo = repo.resolver_municipio(valor)
        except ErrorDatos as error:
            raise HTTPException(error.codigo, error.mensaje) from error
        df = repo.serie_municipio(codigo, CLASE_DEFORESTACION)
        data.append(
            {
                "municipio": repo.nombre_municipio(codigo),
                "codigo_dane": codigo,
                "serie": [
                    {
                        "periodo": fila.periodo,
                        "hectareas_anuales": round(float(fila.hectareas_anuales), 2),
                        "estimado": bool(fila.estimado),
                    }
                    for fila in df.itertuples(index=False)
                ],
            }
        )
    return {"data": data}
