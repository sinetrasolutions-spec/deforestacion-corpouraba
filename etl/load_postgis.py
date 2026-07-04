"""Carga `data/processed` a PostgreSQL + PostGIS (modo opcional del API).

Uso:
    python etl/load_postgis.py --database-url postgresql+psycopg2://usuario:clave@localhost:5432/observatorio

    (también acepta la variable de entorno DATABASE_URL)

Idempotente: ejecuta `etl/sql/schema.sql` (DROP/CREATE) antes de insertar.
Requiere: pip install -r backend/requirements.txt -r backend/requirements-postgis.txt
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("DATA_DIR", str(RAIZ_PROYECTO / "data" / "processed")))
RUTA_SCHEMA = Path(__file__).resolve().parent / "sql" / "schema.sql"

_INSERTAR_MUNICIPIO = text(
    """
    INSERT INTO municipios (codigo_dane, municipio_key, nombre, subregion,
                            area_municipio_ha, centroide_lon, centroide_lat, geom)
    VALUES (:codigo_dane, :municipio_key, :nombre, :subregion, :area_ha, :lon, :lat,
            ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometria), 4326)))
    """
)

_INSERTAR_SUBREGION = text(
    """
    INSERT INTO subregiones (subregion, geom)
    VALUES (:subregion, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometria), 4326)))
    """
)

_INSERTAR_HOTSPOT = text(
    """
    INSERT INTO hotspots (periodo, municipio, ha, geom)
    VALUES (:periodo, :municipio, :ha,
            ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometria), 4326)))
    """
)

_INSERTAR_CAPA = text(
    """
    INSERT INTO capas (capa, nombre, propiedades, geom)
    VALUES (:capa, :nombre, CAST(:propiedades AS jsonb),
            ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometria), 4326)))
    """
)

_INSERTAR_METADATA = text("INSERT INTO metadatos (id, doc) VALUES (1, CAST(:doc AS jsonb))")


def leer_json(ruta: Path) -> dict:
    """Lee un JSON/GeoJSON en UTF-8."""
    return json.loads(ruta.read_text(encoding="utf-8"))


def cargar_esquema(conexion) -> None:
    """Ejecuta schema.sql (DROP/CREATE de todas las tablas)."""
    print(f"[1/6] Ejecutando esquema {RUTA_SCHEMA.name} ...")
    conexion.exec_driver_sql(RUTA_SCHEMA.read_text(encoding="utf-8"))


def cargar_municipios(conexion) -> int:
    """Inserta los 19 límites municipales con su centroide."""
    fc = leer_json(DATA_DIR / "municipios.geojson")
    filas = []
    for feature in fc["features"]:
        props = feature["properties"]
        centroide = props.get("centroide") or [None, None]
        filas.append(
            {
                "codigo_dane": props["codigo_dane"],
                "municipio_key": props["municipio_key"],
                "nombre": props["nombre"],
                "subregion": props["subregion"],
                "area_ha": props.get("area_municipio_ha"),
                "lon": centroide[0],
                "lat": centroide[1],
                "geometria": json.dumps(feature["geometry"]),
            }
        )
    conexion.execute(_INSERTAR_MUNICIPIO, filas)
    print(f"[2/6] municipios: {len(filas)} filas")
    return len(filas)


def cargar_subregiones(conexion) -> int:
    """Inserta las 5 subregiones."""
    fc = leer_json(DATA_DIR / "subregiones.geojson")
    filas = [
        {
            "subregion": feature["properties"]["subregion"],
            "geometria": json.dumps(feature["geometry"]),
        }
        for feature in fc["features"]
    ]
    conexion.execute(_INSERTAR_SUBREGION, filas)
    print(f"      subregiones: {len(filas)} filas")
    return len(filas)


def cargar_serie(conexion) -> int:
    """Inserta la serie municipal parseando `estimado` ('True'/'False') a bool."""
    df = pd.read_csv(
        DATA_DIR / "serie_municipal.csv", dtype={"codigo_dane": str}, encoding="utf-8"
    )
    df["estimado"] = df["estimado"].astype(str).str.strip().str.lower().eq("true")
    df.to_sql("serie_municipal", conexion, if_exists="append", index=False)
    print(f"[3/6] serie_municipal: {len(df)} filas")
    return len(df)


def cargar_hotspots(conexion) -> int:
    """Inserta los polígonos de hotspots de los 12 periodos disponibles."""
    total = 0
    print("[4/6] hotspots:")
    for ruta in sorted((DATA_DIR / "hotspots").glob("*.geojson")):
        periodo = ruta.stem
        fc = leer_json(ruta)
        filas = [
            {
                "periodo": periodo,
                "municipio": feature["properties"].get("municipio"),
                "ha": feature["properties"].get("ha"),
                "geometria": json.dumps(feature["geometry"]),
            }
            for feature in fc["features"]
        ]
        if filas:
            conexion.execute(_INSERTAR_HOTSPOT, filas)
        total += len(filas)
        print(f"      {periodo}: {len(filas)} polígonos")
    return total


def cargar_capas(conexion) -> int:
    """Inserta las capas de contexto conservando sus properties en jsonb."""
    total = 0
    print("[5/6] capas de contexto:")
    for ruta in sorted((DATA_DIR / "capas").glob("*.geojson")):
        id_capa = ruta.stem
        fc = leer_json(ruta)
        filas = [
            {
                "capa": id_capa,
                # cuencas usa 'nomb_cuenc' en vez de 'nombre'
                "nombre": feature["properties"].get("nombre")
                or feature["properties"].get("nomb_cuenc"),
                "propiedades": json.dumps(feature["properties"], ensure_ascii=False),
                "geometria": json.dumps(feature["geometry"]),
            }
            for feature in fc["features"]
        ]
        if filas:
            conexion.execute(_INSERTAR_CAPA, filas)
        total += len(filas)
        print(f"      {id_capa}: {len(filas)} unidades")
    return total


def cargar_metadata(conexion) -> None:
    """Inserta metadata.json como documento jsonb único."""
    doc = leer_json(DATA_DIR / "metadata.json")
    conexion.execute(_INSERTAR_METADATA, {"doc": json.dumps(doc, ensure_ascii=False)})
    print("[6/6] metadatos: 1 documento")


def verificar(conexion) -> None:
    """Resumen final de conteos por tabla."""
    print("\nVerificación:")
    for tabla in ("municipios", "subregiones", "serie_municipal", "hotspots", "capas", "metadatos"):
        n = conexion.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
        print(f"  {tabla}: {n} filas")


def main() -> int:
    """Punto de entrada del cargador."""
    parser = argparse.ArgumentParser(description="Carga data/processed a PostGIS.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="postgresql+psycopg2://usuario:clave@host:puerto/bd (o env DATABASE_URL)",
    )
    argumentos = parser.parse_args()
    if not argumentos.database_url:
        print("ERROR: indique --database-url o defina la variable DATABASE_URL.")
        return 1
    if not DATA_DIR.exists():
        print(f"ERROR: no existe el directorio de datos {DATA_DIR}. Ejecute antes run_etl.py.")
        return 1

    motor = create_engine(argumentos.database_url)
    with motor.begin() as conexion:  # transacción única: todo o nada
        cargar_esquema(conexion)
        cargar_municipios(conexion)
        cargar_subregiones(conexion)
        cargar_serie(conexion)
        cargar_hotspots(conexion)
        cargar_capas(conexion)
        cargar_metadata(conexion)
        verificar(conexion)
    print("\nCarga completada. Active el modo PostGIS exportando DATABASE_URL antes de iniciar el API.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
