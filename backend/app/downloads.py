"""Generación de descargas dinámicas: CSV, XLSX, GeoJSON y ZIP en memoria."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

#: Marca de orden de bytes UTF-8 para que Excel abra los CSV con tildes.
BOM_UTF8 = b"\xef\xbb\xbf"

TITULO = "Observatorio de Deforestación CORPOURABA (2000–2024)"
ATRIBUCION = (
    "Fuente: CORPOURABA — monitoreo de bosque de la jurisdicción; "
    "datos procesados por el ETL del Observatorio."
)
NOTA_ESTIMADOS = (
    "Los periodos 2010-2012, 2015-2016, 2018-2019 y 2023-2024 contienen valores "
    "estimados (columna estimado=True); úselos solo como referencia."
)


def _describir_filtros(filtros: dict) -> str:
    """Serializa los filtros aplicados de forma legible."""
    partes = [
        f"{clave}={valor}"
        for clave, valor in filtros.items()
        if valor not in (None, [], "")
    ]
    return "; ".join(partes) if partes else "sin filtros (serie completa)"


def _lineas_metadatos(filtros: dict) -> list[str]:
    """Cabecera de metadatos comentada con '#' para el CSV."""
    return [
        TITULO,
        f"Generado: {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"Filtros: {_describir_filtros(filtros)}",
        f"Nota: {NOTA_ESTIMADOS}",
        ATRIBUCION,
    ]


def csv_serie(df: pd.DataFrame, filtros: dict) -> bytes:
    """CSV UTF-8 con BOM y cabecera de metadatos comentada con '#'."""
    encabezado = "".join(f"# {linea}\n" for linea in _lineas_metadatos(filtros))
    cuerpo = df.to_csv(index=False, lineterminator="\n")
    return BOM_UTF8 + (encabezado + cuerpo).encode("utf-8")


def xlsx_serie(df: pd.DataFrame, filtros: dict) -> bytes:
    """XLSX con hojas `datos` y `metadatos` (motor openpyxl)."""
    metadatos = pd.DataFrame(
        [
            ("titulo", TITULO),
            ("generado", datetime.now(timezone.utc).isoformat(timespec="seconds")),
            ("filtros", _describir_filtros(filtros)),
            ("filas", str(len(df))),
            ("nota_estimados", NOTA_ESTIMADOS),
            ("atribucion", ATRIBUCION),
        ],
        columns=["campo", "valor"],
    )
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as escritor:
        df.to_excel(escritor, sheet_name="datos", index=False)
        metadatos.to_excel(escritor, sheet_name="metadatos", index=False)
    return buffer.getvalue()


def geojson_bytes(fc: dict) -> bytes:
    """Serializa una FeatureCollection a bytes UTF-8 (tildes legibles)."""
    return json.dumps(fc, ensure_ascii=False).encode("utf-8")


def zip_paquete(data_dir: Path) -> bytes:
    """ZIP en memoria con todo `data/processed` (los archivos suman <5 MB)."""
    buffer = io.BytesIO()
    data_dir = Path(data_dir)
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as paquete:
        for ruta in sorted(data_dir.rglob("*")):
            if ruta.is_file():
                paquete.write(ruta, arcname=str(ruta.relative_to(data_dir)))
    return buffer.getvalue()
