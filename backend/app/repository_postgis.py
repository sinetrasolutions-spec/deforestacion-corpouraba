"""Repositorio sobre PostGIS con la misma interfaz que RepositorioArchivos.

Se activa cuando existe ``DATABASE_URL`` (ver config.crear_repositorio). Al
inicializar carga en memoria la serie, geometrías y metadata desde las tablas
creadas por ``etl/load_postgis.py``; los hotspots se consultan por periodo con
caché. Si la conexión falla, el constructor lanza excepción y ``config``
recurre al modo archivos.
"""
from __future__ import annotations

import json

import pandas as pd
from sqlalchemy import create_engine, text

from .repository import RepositorioBase

_COLUMNAS_SERIE = (
    "codigo_dane, municipio, subregion, periodo, ano_inicio, ano_fin, "
    "clase, hectareas, hectareas_anuales, fuente, estimado"
)


class RepositorioPostgis(RepositorioBase):
    """Acceso a datos servido por PostgreSQL + PostGIS."""

    modo = "postgis"

    def __init__(self, database_url: str) -> None:
        super().__init__()
        self.motor = create_engine(database_url, pool_pre_ping=True)
        # Verificación temprana: si no hay BD, fallar aquí para permitir fallback
        with self.motor.connect() as conexion:
            conexion.execute(text("SELECT PostGIS_Version()"))
        self._cache_hotspots: dict[str, dict] = {}
        self._cargar()
        self._indexar()

    # ------------------------------------------------------------------ carga
    def _cargar(self) -> None:
        """Carga serie, metadata y geometrías a memoria (una sola vez)."""
        with self.motor.connect() as conexion:
            self.serie = pd.read_sql(
                text(f"SELECT {_COLUMNAS_SERIE} FROM serie_municipal"), conexion
            )
            self.serie["codigo_dane"] = self.serie["codigo_dane"].astype(str)
            self.serie["estimado"] = self.serie["estimado"].astype(bool)

            # La serie regional se agrega desde la municipal (mismos totales)
            self.regional = self._regional_desde_serie(self.serie)

            fila = conexion.execute(text("SELECT doc FROM metadatos WHERE id = 1")).fetchone()
            self.metadata = self._como_dict(fila[0]) if fila else {}

            self.municipios_fc = self._fc_municipios(conexion)
            self.subregiones_fc = self._fc_subregiones(conexion)
            self.capas = self._fc_capas(conexion)

    @staticmethod
    def _como_dict(valor) -> dict:
        """jsonb puede llegar como dict o como texto según el driver."""
        return valor if isinstance(valor, dict) else json.loads(valor)

    @staticmethod
    def _como_geometria(valor) -> dict:
        return valor if isinstance(valor, dict) else json.loads(valor)

    def _fc_municipios(self, conexion) -> dict:
        filas = conexion.execute(
            text(
                "SELECT municipio_key, codigo_dane, nombre, subregion, "
                "area_municipio_ha, centroide_lon, centroide_lat, "
                "ST_AsGeoJSON(geom) AS geometria FROM municipios ORDER BY codigo_dane"
            )
        ).mappings()
        features = [
            {
                "type": "Feature",
                "properties": {
                    "municipio_key": fila["municipio_key"],
                    "codigo_dane": fila["codigo_dane"],
                    "nombre": fila["nombre"],
                    "subregion": fila["subregion"],
                    "area_municipio_ha": fila["area_municipio_ha"],
                    "centroide": [fila["centroide_lon"], fila["centroide_lat"]],
                },
                "geometry": self._como_geometria(fila["geometria"]),
            }
            for fila in filas
        ]
        return {"type": "FeatureCollection", "features": features}

    def _fc_subregiones(self, conexion) -> dict:
        filas = conexion.execute(
            text(
                "SELECT subregion, ST_AsGeoJSON(geom) AS geometria "
                "FROM subregiones ORDER BY subregion"
            )
        ).mappings()
        features = [
            {
                "type": "Feature",
                "properties": {"subregion": fila["subregion"]},
                "geometry": self._como_geometria(fila["geometria"]),
            }
            for fila in filas
        ]
        return {"type": "FeatureCollection", "features": features}

    def _fc_capas(self, conexion) -> dict[str, dict]:
        capas: dict[str, dict] = {}
        filas = conexion.execute(
            text(
                "SELECT capa, propiedades, ST_AsGeoJSON(geom) AS geometria "
                "FROM capas ORDER BY capa, id"
            )
        ).mappings()
        for fila in filas:
            fc = capas.setdefault(fila["capa"], {"type": "FeatureCollection", "features": []})
            fc["features"].append(
                {
                    "type": "Feature",
                    "properties": self._como_dict(fila["propiedades"]),
                    "geometry": self._como_geometria(fila["geometria"]),
                }
            )
        return capas

    # ------------------------------------------------------------------ hotspots
    def hotspots_disponibles(self) -> list[str]:
        with self.motor.connect() as conexion:
            filas = conexion.execute(
                text("SELECT DISTINCT periodo FROM hotspots ORDER BY periodo")
            ).fetchall()
        return [fila[0] for fila in filas]

    def hotspots(self, periodo: str) -> dict | None:
        if periodo in self._cache_hotspots:
            return self._cache_hotspots[periodo]
        with self.motor.connect() as conexion:
            filas = conexion.execute(
                text(
                    "SELECT municipio, ha, ST_AsGeoJSON(geom) AS geometria "
                    "FROM hotspots WHERE periodo = :periodo ORDER BY id"
                ),
                {"periodo": periodo},
            ).mappings().fetchall()
        if not filas:
            return None
        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"municipio": fila["municipio"], "ha": fila["ha"]},
                    "geometry": self._como_geometria(fila["geometria"]),
                }
                for fila in filas
            ],
        }
        self._cache_hotspots[periodo] = fc
        return fc
