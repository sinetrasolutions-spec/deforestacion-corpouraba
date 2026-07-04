"""Endpoints de la investigación temática: hallazgos, tablas y capas de análisis.

Sirven los productos de ``data/processed/analisis/`` (generados por los scripts
de ``etl/analisis/``). El catálogo es dinámico: los archivos nuevos aparecen sin
reiniciar el API. Se leen en cada petición (son pequeños y locales).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ..config import DATA_DIR

router = APIRouter(prefix="/analisis", tags=["analisis"])

_ID_SEGURO = re.compile(r"^[a-z0-9_]+(/[a-z0-9_]+)?$")


def _dir_analisis() -> Path:
    carpeta = DATA_DIR / "analisis"
    if not carpeta.is_dir():
        raise HTTPException(404, "No hay resultados de análisis generados todavía.")
    return carpeta


def _resolver(dataset: str, extension: str) -> Path:
    """Convierte un id como 'cartografia/mineria_deforestacion' en ruta segura."""
    if not _ID_SEGURO.match(dataset):
        raise HTTPException(422, f"Identificador de dataset inválido: '{dataset}'.")
    ruta = (_dir_analisis() / dataset).with_suffix(extension)
    if not ruta.is_file():
        raise HTTPException(404, f"No existe el dataset '{dataset}{extension}'.")
    return ruta


@router.get("")
def catalogo() -> dict:
    """Catálogo de productos de análisis disponibles (tablas, resúmenes y capas)."""
    carpeta = _dir_analisis()
    tablas, resumenes, capas = [], [], []
    for ruta in sorted(carpeta.rglob("*")):
        if not ruta.is_file():
            continue
        rel = ruta.relative_to(carpeta).as_posix()
        id_ = rel.rsplit(".", 1)[0]
        if ruta.suffix == ".csv":
            tablas.append({"id": id_, "archivo": rel})
        elif ruta.suffix == ".geojson":
            capas.append({"id": id_, "archivo": rel})
        elif ruta.suffix == ".json" and ruta.stem != "hallazgos":
            resumenes.append({"id": id_, "archivo": rel})
    return {"tablas": tablas, "resumenes": resumenes, "capas": capas}


@router.get("/hallazgos")
def hallazgos() -> dict:
    """Hallazgos consolidados de todas las líneas de investigación.

    Une ``hallazgos.json`` (paquete de monitoreo) con
    ``hallazgos_cartografia.json`` (cartografía oficial), ordenados por
    relevancia descendente.
    """
    carpeta = _dir_analisis()
    todos: list[dict] = []
    for nombre in ("hallazgos.json", "hallazgos_cartografia.json"):
        ruta = carpeta / nombre
        if ruta.is_file():
            try:
                todos.extend(json.loads(ruta.read_text(encoding="utf-8-sig")))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise HTTPException(500, f"{nombre} corrupto: {exc}") from exc
    if not todos:
        raise HTTPException(404, "Aún no hay hallazgos publicados.")
    todos.sort(key=lambda h: h.get("relevancia", 0), reverse=True)
    return {"hallazgos": todos, "total": len(todos)}


@router.get("/tabla/{dataset:path}")
def tabla(
    dataset: str,
    municipio: str | None = Query(None, description="Filtra si la tabla tiene columna municipio"),
    periodo: str | None = Query(None, description="Filtra si la tabla tiene columna periodo"),
    limite: int = Query(5000, ge=1, le=50000),
) -> dict:
    """Tabla de análisis en JSON (filas), con filtros básicos opcionales."""
    ruta = _resolver(dataset, ".csv")
    df = pd.read_csv(ruta, encoding="utf-8-sig")
    if municipio and "municipio" in df.columns:
        objetivo = municipio.strip().casefold()
        df = df[df["municipio"].astype(str).str.casefold() == objetivo]
    if periodo and "periodo" in df.columns:
        df = df[df["periodo"].astype(str) == periodo]
    total = int(len(df))
    df = df.head(limite)
    df = df.where(pd.notna(df), None)
    return {
        "dataset": dataset,
        "columnas": list(df.columns),
        "filas": df.to_dict(orient="records"),
        "total_filas": total,
        "truncado": total > limite,
    }


@router.get("/resumen/{dataset:path}")
def resumen(dataset: str) -> dict:
    """Resumen JSON de una línea de análisis (agregados clave del minero)."""
    ruta = _resolver(dataset, ".json")
    return json.loads(ruta.read_text(encoding="utf-8-sig"))


@router.get("/geo/{dataset:path}")
def geo(dataset: str) -> dict:
    """Capa GeoJSON de análisis (p. ej. 'recurrencia' — frentes persistentes)."""
    ruta = _resolver(dataset, ".geojson")
    return json.loads(ruta.read_text(encoding="utf-8"))


# --- Deforestación por unidad territorial (áreas protegidas, POMCAS, etc.) ----

# Configuración por tipo: archivo CSV, columna de nombre, columna secundaria,
# y de dónde sale la deforestación (columna directa o filtro por clase).
_TERRITORIOS: dict[str, dict] = {
    "areas_protegidas": {
        "titulo": "Áreas protegidas",
        "archivo": "areas_protegidas_serie.csv",
        "col_nombre": "nombre",
        "col_sec": "categoria",
        "por_clase": True,
        "col_area": None,
    },
    "resguardos": {
        "titulo": "Resguardos indígenas",
        "archivo": "cartografia/territorios_oficiales.csv",
        "filtro": ("tipo", "resguardo"),
        "col_nombre": "nombre",
        "col_sec": "pueblo",
        "col_defo": "deforestacion_ha",
        "col_area": "area_oficial_ha",
    },
    "consejos": {
        "titulo": "Consejos comunitarios",
        "archivo": "cartografia/territorios_oficiales.csv",
        "filtro": ("tipo", "consejo_comunitario"),
        "col_nombre": "nombre",
        "col_sec": "municipios",
        "col_defo": "deforestacion_ha",
        "col_area": "area_oficial_ha",
    },
    "pomcas": {
        "titulo": "POMCAS (cuencas ordenadas)",
        "archivo": "cartografia/pomcas_serie.csv",
        "col_nombre": "pomca",
        "col_sec": None,
        "col_defo": "deforestacion_ha",
        "col_area": None,
    },
    "cuencas": {
        "titulo": "Cuencas hidrográficas",
        "archivo": "cuencas_serie.csv",
        "col_nombre": "cuenca",
        "col_sec": None,
        "por_clase": True,
        "col_area": None,
    },
}


@router.get("/territorios")
def territorios_catalogo() -> dict:
    """Tipos de unidad territorial disponibles y si tienen datos generados."""
    carpeta = _dir_analisis()
    tipos = []
    for tid, cfg in _TERRITORIOS.items():
        ruta = (carpeta / cfg["archivo"])
        tipos.append({"id": tid, "titulo": cfg["titulo"], "disponible": ruta.is_file()})
    return {"tipos": tipos}


@router.get("/territorios/{tipo}")
def territorios(
    tipo: str,
    periodo: str | None = Query(None, description="Filtra a un periodo; si se omite, acumulado"),
) -> dict:
    """Ranking de deforestación por unidad para un tipo de territorio.

    Devuelve cada unidad con su deforestación mapeada (acumulada o de un periodo
    concreto), número de periodos con dato, área oficial y % del territorio,
    ordenadas de mayor a menor. Incluye la lista de periodos disponibles para
    alimentar la barra de tiempo del dashboard.
    """
    cfg = _TERRITORIOS.get(tipo)
    if cfg is None:
        raise HTTPException(
            422, f"Tipo desconocido: '{tipo}'. Disponibles: {', '.join(_TERRITORIOS)}."
        )
    ruta = _dir_analisis() / cfg["archivo"]
    if not ruta.is_file():
        raise HTTPException(404, f"Aún no hay datos de '{tipo}' ({cfg['archivo']}).")
    df = pd.read_csv(ruta, encoding="utf-8-sig")

    if cfg.get("filtro"):
        col, val = cfg["filtro"]
        df = df[df[col].astype(str).str.strip().str.lower() == val.lower()]

    nombre = cfg["col_nombre"]
    if cfg.get("por_clase"):
        df = df[df["clase"] == "Deforestación"].copy()
        df["_defo"] = df["hectareas"]
    else:
        df["_defo"] = df[cfg["col_defo"]]

    df = df.dropna(subset=[nombre])

    # Periodos disponibles (antes de filtrar) para la barra de tiempo
    periodos_disponibles = (
        sorted(str(p) for p in df["periodo"].dropna().unique()) if "periodo" in df else []
    )
    if periodo and "periodo" in df.columns:
        df = df[df["periodo"].astype(str) == periodo]

    unidades = []
    for clave, grp in df.groupby(nombre):
        total = float(grp["_defo"].sum())
        sec = None
        if cfg.get("col_sec") and cfg["col_sec"] in grp.columns:
            valores = [str(v) for v in grp[cfg["col_sec"]].dropna().unique() if str(v) != "nan"]
            sec = valores[0] if valores else None
        area = None
        pct = None
        if cfg.get("col_area") and cfg["col_area"] in grp.columns:
            area_vals = grp[cfg["col_area"]].dropna()
            if len(area_vals):
                area = round(float(area_vals.iloc[0]), 1)
                if area:
                    pct = round(100 * total / area, 3)
        unidades.append({
            "nombre": str(clave),
            "detalle": sec,
            "deforestacion_ha": round(total, 2),
            "n_periodos": int(grp["periodo"].nunique()) if "periodo" in grp else None,
            "area_ha": area,
            "pct_del_territorio": pct,
        })
    unidades.sort(key=lambda x: x["deforestacion_ha"], reverse=True)
    return {
        "tipo": tipo,
        "titulo": cfg["titulo"],
        "periodo": periodo,
        "periodos_disponibles": periodos_disponibles,
        "n_unidades": len(unidades),
        "deforestacion_total_ha": round(sum(u["deforestacion_ha"] for u in unidades), 1),
        "nota": "Deforestación mapeada dentro de cada unidad. Ver metodología en /datos.",
        "unidades": unidades,
    }
