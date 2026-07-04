"""Endpoints de descargas: CSV, XLSX, GeoJSON y paquete ZIP."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from .. import downloads
from ..config import DATA_DIR, obtener_repositorio
from ..repository import CLASE_DEFORESTACION, ErrorDatos, RepositorioBase, filtrar_serie

router = APIRouter(prefix="/descargas", tags=["descargas"])

MEDIA_CSV = "text/csv; charset=utf-8"
MEDIA_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MEDIA_GEOJSON = "application/geo+json"


def _adjunto(nombre: str) -> dict[str, str]:
    """Cabecera Content-Disposition de descarga."""
    return {"Content-Disposition": f'attachment; filename="{nombre}"'}


def _serie_filtrada(
    repo: RepositorioBase,
    municipio: list[str] | None,
    subregion: str | None,
    clase: str,
    desde: int | None,
    hasta: int | None,
    incluir_estimados: bool,
):
    """Aplica los mismos filtros de /serie y devuelve (df, filtros legibles)."""
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
    filtros = {
        "municipio": ", ".join(municipio) if municipio else None,
        "subregion": subregion,
        "clase": clase,
        "desde": desde,
        "hasta": hasta,
        "incluir_estimados": incluir_estimados,
    }
    return df, filtros


def _agregar_regional(df):
    """Colapsa la serie municipal a totales regionales por periodo × clase."""
    return (
        df.groupby(["periodo", "ano_inicio", "ano_fin", "clase"], as_index=False)
        .agg(
            hectareas=("hectareas", "sum"),
            hectareas_anuales=("hectareas_anuales", "sum"),
            estimado=("estimado", "any"),
        )
        .sort_values("ano_inicio")
        .round({"hectareas": 2, "hectareas_anuales": 2})
    )


@router.get("/serie.csv")
def descargar_serie_csv(
    municipio: list[str] | None = Query(None),
    subregion: str | None = Query(None),
    clase: str = Query(CLASE_DEFORESTACION),
    desde: int | None = Query(None, ge=2000, le=2024),
    hasta: int | None = Query(None, ge=2000, le=2024),
    incluir_estimados: bool = Query(True),
    agregado: str | None = Query(None, pattern="^regional$",
                                 description="'regional' colapsa a totales por periodo"),
    repo: RepositorioBase = Depends(obtener_repositorio),
):
    """CSV con BOM UTF-8 y cabecera de metadatos comentada con '#'."""
    df, filtros = _serie_filtrada(
        repo, municipio, subregion, clase, desde, hasta, incluir_estimados
    )
    nombre = "serie_deforestacion_corpouraba.csv"
    if agregado == "regional":
        df = _agregar_regional(df)
        filtros["agregado"] = "regional"
        nombre = "serie_regional_deforestacion_corpouraba.csv"
    return Response(
        content=downloads.csv_serie(df, filtros),
        media_type=MEDIA_CSV,
        headers=_adjunto(nombre),
    )


@router.get("/serie.xlsx")
def descargar_serie_xlsx(
    municipio: list[str] | None = Query(None),
    subregion: str | None = Query(None),
    clase: str = Query(CLASE_DEFORESTACION),
    desde: int | None = Query(None, ge=2000, le=2024),
    hasta: int | None = Query(None, ge=2000, le=2024),
    incluir_estimados: bool = Query(True),
    agregado: str | None = Query(None, pattern="^regional$",
                                 description="'regional' colapsa a totales por periodo"),
    repo: RepositorioBase = Depends(obtener_repositorio),
):
    """XLSX con hojas `datos` y `metadatos`."""
    df, filtros = _serie_filtrada(
        repo, municipio, subregion, clase, desde, hasta, incluir_estimados
    )
    nombre = "serie_deforestacion_corpouraba.xlsx"
    if agregado == "regional":
        df = _agregar_regional(df)
        filtros["agregado"] = "regional"
        nombre = "serie_regional_deforestacion_corpouraba.xlsx"
    return Response(
        content=downloads.xlsx_serie(df, filtros),
        media_type=MEDIA_XLSX,
        headers=_adjunto(nombre),
    )


@router.get("/municipios.geojson")
def descargar_municipios(repo: RepositorioBase = Depends(obtener_repositorio)):
    """Límites municipales en GeoJSON (WGS84)."""
    return Response(
        content=downloads.geojson_bytes(repo.municipios_fc),
        media_type=MEDIA_GEOJSON,
        headers=_adjunto("municipios_corpouraba.geojson"),
    )


@router.get("/hotspots/{periodo}.geojson")
def descargar_hotspots(periodo: str, repo: RepositorioBase = Depends(obtener_repositorio)):
    """Hotspots de un periodo en GeoJSON; 404 con los periodos disponibles."""
    fc = repo.hotspots(periodo)
    if fc is None:
        return JSONResponse(
            status_code=404,
            content={
                "detail": f"No hay hotspots para el periodo '{periodo}'.",
                "disponibles": repo.hotspots_disponibles(),
            },
        )
    return Response(
        content=downloads.geojson_bytes(fc),
        media_type=MEDIA_GEOJSON,
        headers=_adjunto(f"hotspots_{periodo}.geojson"),
    )


@router.get("/paquete.zip")
def descargar_paquete():
    """ZIP con todo el contenido de data/processed."""
    return Response(
        content=downloads.zip_paquete(DATA_DIR),
        media_type="application/zip",
        headers=_adjunto("observatorio_corpouraba_datos.zip"),
    )
