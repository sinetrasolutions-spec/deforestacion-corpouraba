"""Acceso a datos en memoria leyendo `data/processed` (modo por defecto).

Define también la clase base compartida con el repositorio PostGIS: ambas
implementaciones exponen exactamente la misma interfaz, de modo que los
routers no distinguen el origen de los datos.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pandas as pd

#: Clases de cobertura válidas (columna `clase` de la serie).
CLASES_VALIDAS: list[str] = [
    "Bosque Estable",
    "Deforestación",
    "No Bosque Estable",
    "Regeneración",
    "Sin Información",
]

#: Subregiones válidas de la jurisdicción CORPOURABA.
SUBREGIONES_VALIDAS: list[str] = ["Caribe", "Centro", "Atrato", "Nutibara", "Urrao"]

#: Nombres legibles de las capas de contexto (overlays).
NOMBRES_CAPAS: dict[str, str] = {
    "areas_protegidas": "Áreas protegidas",
    "resguardos": "Resguardos indígenas",
    "consejos": "Consejos comunitarios",
    "cuencas": "Cuencas",
    # Capas de la cartografía oficial (cruces con la deforestación)
    "areas_protegidas_oficial": "Áreas protegidas (oficial)",
    "resguardos_oficial": "Resguardos indígenas (oficial)",
    "comunidades_negras_oficial": "Consejos comunitarios (oficial)",
    "titulos_mineros": "Títulos mineros",
    "ley_segunda": "Reserva forestal Ley 2ª",
    "ecosistemas_estrategicos": "Ecosistemas estratégicos",
    "zonificacion_conflicto": "Zonas de conflicto de uso",
    "pdet": "Municipios PDET",
}

CLASE_DEFORESTACION = "Deforestación"


def normalizar(texto: str) -> str:
    """MAYÚSCULAS, sin tildes ni espacios repetidos (para comparar nombres)."""
    plano = unicodedata.normalize("NFD", str(texto))
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return " ".join(plano.upper().split())


#: Índices normalizados para validar clase y subregión con o sin tildes.
_CLASES_NORM = {normalizar(c): c for c in CLASES_VALIDAS}
_SUBREGIONES_NORM = {normalizar(s): s for s in SUBREGIONES_VALIDAS}


class ErrorDatos(Exception):
    """Error de parámetro o dato inexistente, con código HTTP sugerido."""

    def __init__(self, mensaje: str, codigo: int = 422) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def validar_clase(clase: str) -> str:
    """Devuelve el nombre canónico de la clase o lanza ErrorDatos(422)."""
    canonica = _CLASES_NORM.get(normalizar(clase))
    if canonica is None:
        raise ErrorDatos(
            f"Clase desconocida: '{clase}'. Válidas: {', '.join(CLASES_VALIDAS)}.", 422
        )
    return canonica


def validar_subregion(subregion: str) -> str:
    """Devuelve el nombre canónico de la subregión o lanza ErrorDatos(422)."""
    canonica = _SUBREGIONES_NORM.get(normalizar(subregion))
    if canonica is None:
        raise ErrorDatos(
            f"Subregión desconocida: '{subregion}'. Válidas: {', '.join(SUBREGIONES_VALIDAS)}.",
            422,
        )
    return canonica


class RepositorioBase:
    """Interfaz común de acceso a datos (archivos o PostGIS).

    Las subclases deben poblar en su constructor: ``serie`` (DataFrame
    municipal), ``regional`` (DataFrame regional), ``metadata`` (dict),
    ``municipios_fc`` y ``subregiones_fc`` (FeatureCollections) y ``capas``
    (dict id → FeatureCollection), y luego llamar a ``_indexar()``.
    """

    modo: str = "archivos"

    def __init__(self) -> None:
        self.serie: pd.DataFrame = pd.DataFrame()
        self.regional: pd.DataFrame = pd.DataFrame()
        self.metadata: dict = {}
        self.municipios_fc: dict = {}
        self.subregiones_fc: dict = {}
        self.capas: dict[str, dict] = {}
        self._indice_municipios: dict[str, str] = {}
        self._nombre_por_codigo: dict[str, str] = {}

    # ------------------------------------------------------------------ índices
    def _indexar(self) -> None:
        """Construye índices por código DANE y nombre normalizado (sin tildes)."""
        for feature in self.municipios_fc.get("features", []):
            props = feature.get("properties", {})
            codigo = str(props.get("codigo_dane", ""))
            nombre = str(props.get("nombre", ""))
            clave = str(props.get("municipio_key", ""))
            if not codigo:
                continue
            self._nombre_por_codigo[codigo] = nombre
            self._indice_municipios[codigo] = codigo
            self._indice_municipios[normalizar(nombre)] = codigo
            if clave:
                self._indice_municipios[normalizar(clave)] = codigo

    def resolver_municipio(self, valor: str) -> str:
        """Resuelve código DANE o nombre (con/sin tildes, case-insensitive)."""
        codigo = self._indice_municipios.get(str(valor).strip()) or self._indice_municipios.get(
            normalizar(valor)
        )
        if codigo is None:
            raise ErrorDatos(f"Municipio no reconocido: '{valor}'.", 404)
        return codigo

    def nombre_municipio(self, codigo: str) -> str:
        """Nombre bonito del municipio a partir del código DANE."""
        return self._nombre_por_codigo.get(codigo, codigo)

    # ------------------------------------------------------------------ catálogo
    def periodos(self) -> list[dict]:
        """Lista de periodos del metadata + bandera `tiene_hotspots`."""
        disponibles = set(self.hotspots_disponibles())
        return [
            {**periodo, "tiene_hotspots": periodo["id"] in disponibles}
            for periodo in self.metadata.get("periodos", [])
        ]

    def ids_periodos(self) -> list[str]:
        """Identificadores de los 18 periodos, en orden cronológico."""
        return [p["id"] for p in self.metadata.get("periodos", [])]

    def validar_periodo(self, periodo: str) -> str:
        """Valida que el periodo exista en la serie o lanza ErrorDatos(404)."""
        ids = self.ids_periodos()
        if periodo not in ids:
            raise ErrorDatos(
                f"Periodo desconocido: '{periodo}'. Disponibles: {', '.join(ids)}.", 404
            )
        return periodo

    def capas_disponibles(self) -> list[dict]:
        """Resumen de capas de contexto: id, nombre legible y unidades."""
        return [
            {
                "id": id_capa,
                "nombre": NOMBRES_CAPAS.get(id_capa, id_capa),
                "unidades": len(fc.get("features", [])),
            }
            for id_capa, fc in self.capas.items()
        ]

    def capa(self, id_capa: str) -> dict:
        """FeatureCollection de una capa de contexto o ErrorDatos(404)."""
        fc = self.capas.get(id_capa)
        if fc is None:
            raise ErrorDatos(
                f"Capa desconocida: '{id_capa}'. Disponibles: {', '.join(self.capas)}.", 404
            )
        return fc

    # ------------------------------------------------------------------ series
    def serie_regional(self, clase: str, incluir_estimados: bool = True) -> pd.DataFrame:
        """Serie regional filtrada por clase, opcionalmente sin estimados."""
        clase_ok = validar_clase(clase)
        df = self.regional[self.regional["clase"] == clase_ok]
        if not incluir_estimados:
            df = df[~df["estimado"]]
        return df.sort_values("ano_inicio").reset_index(drop=True)

    def serie_municipio(self, codigo_dane: str, clase: str = CLASE_DEFORESTACION) -> pd.DataFrame:
        """Serie de un municipio (por defecto la clase Deforestación)."""
        clase_ok = validar_clase(clase)
        df = self.serie[
            (self.serie["codigo_dane"] == codigo_dane) & (self.serie["clase"] == clase_ok)
        ]
        return df.sort_values("ano_inicio").reset_index(drop=True)

    # ------------------------------------------------------------------ hotspots
    def hotspots_disponibles(self) -> list[str]:
        """Periodos con archivo de hotspots. Implementado en subclases."""
        raise NotImplementedError

    def hotspots(self, periodo: str) -> dict | None:
        """FeatureCollection de hotspots del periodo o None si no existe."""
        raise NotImplementedError

    def parches(
        self,
        periodo: str | None = None,
        min_ha: float = 0.0,
        municipio: str | None = None,
    ) -> dict:
        """Parches de deforestación (hotspots ≥1 ha) de uno o TODOS los periodos.

        Cada feature se etiqueta con ``periodo``, ``ano_inicio``, ``municipio`` y
        ``ha`` para el explorador de parches (vista acumulada 2000-2024). Filtros
        opcionales por periodo, área mínima y municipio (nombre o código DANE).
        Reutiliza ``hotspots()`` de la subclase, por lo que sirve tanto en modo
        archivos como PostGIS.
        """
        ano_por_periodo = {
            p["id"]: p.get("ano_inicio") for p in self.metadata.get("periodos", [])
        }
        if periodo is not None:
            self.validar_periodo(periodo)
            periodos = [periodo] if periodo in self.hotspots_disponibles() else []
        else:
            periodos = self.hotspots_disponibles()

        objetivo_mun: str | None = None
        if municipio:
            try:
                objetivo_mun = normalizar(self.nombre_municipio(self.resolver_municipio(municipio)))
            except ErrorDatos:
                objetivo_mun = normalizar(municipio)

        features: list[dict] = []
        total_ha = 0.0
        por_periodo: dict[str, dict] = {}
        for pid in periodos:
            fc = self.hotspots(pid)
            if not fc:
                continue
            ano = ano_por_periodo.get(pid)
            for feat in fc.get("features", []):
                props = feat.get("properties") or {}
                try:
                    ha = float(props.get("ha") or 0.0)
                except (TypeError, ValueError):
                    ha = 0.0
                if ha < min_ha:
                    continue
                mun = props.get("municipio")
                if objetivo_mun is not None and (
                    mun is None or normalizar(str(mun)) != objetivo_mun
                ):
                    continue
                features.append(
                    {
                        "type": "Feature",
                        "geometry": feat.get("geometry"),
                        "properties": {
                            "periodo": pid,
                            "ano_inicio": ano,
                            "municipio": mun,
                            "ha": round(ha, 2),
                        },
                    }
                )
                total_ha += ha
                agg = por_periodo.setdefault(pid, {"periodo": pid, "ano_inicio": ano, "n": 0, "ha": 0.0})
                agg["n"] += 1
                agg["ha"] += ha

        for agg in por_periodo.values():
            agg["ha"] = round(agg["ha"], 1)

        return {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "n_parches": len(features),
                "ha_total": round(total_ha, 1),
                "periodos": periodos,
                "min_ha": min_ha,
                "por_periodo": sorted(por_periodo.values(), key=lambda x: x["ano_inicio"] or 0),
            },
        }

    # ------------------------------------------------------------------ auxiliar
    @staticmethod
    def _regional_desde_serie(serie: pd.DataFrame) -> pd.DataFrame:
        """Agrega la serie municipal a nivel regional (suma por periodo/clase)."""
        regional = (
            serie.groupby(["periodo", "ano_inicio", "ano_fin", "clase"], as_index=False)
            .agg(
                hectareas=("hectareas", "sum"),
                hectareas_anuales=("hectareas_anuales", "sum"),
                estimado=("estimado", "max"),
            )
        )
        regional["estimado"] = regional["estimado"].astype(bool)
        return regional


def _parsear_estimado(columna: pd.Series) -> pd.Series:
    """Convierte la columna `estimado` ('True'/'False' string o bool) a bool."""
    return columna.astype(str).str.strip().str.lower().eq("true")


class RepositorioArchivos(RepositorioBase):
    """Repositorio que carga todo `data/processed` en memoria al arrancar."""

    modo = "archivos"

    def __init__(self, data_dir: Path) -> None:
        super().__init__()
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise FileNotFoundError(f"No existe el directorio de datos: {self.data_dir}")

        # Serie municipal: codigo_dane como texto (conserva el cero inicial)
        self.serie = pd.read_csv(
            self.data_dir / "serie_municipal.csv",
            dtype={"codigo_dane": str},
            encoding="utf-8",
        )
        self.serie["estimado"] = _parsear_estimado(self.serie["estimado"])

        # Serie regional precalculada por el ETL
        self.regional = pd.read_csv(self.data_dir / "serie_regional.csv", encoding="utf-8")
        self.regional["estimado"] = _parsear_estimado(self.regional["estimado"])

        self.metadata = self._leer_json(self.data_dir / "metadata.json")
        self.municipios_fc = self._leer_json(self.data_dir / "municipios.geojson")
        self.subregiones_fc = self._leer_json(self.data_dir / "subregiones.geojson")
        self.capas = {
            ruta.stem: self._leer_json(ruta)
            for ruta in sorted((self.data_dir / "capas").glob("*.geojson"))
        }
        self._cache_hotspots: dict[str, dict] = {}
        self._indexar()

    @staticmethod
    def _leer_json(ruta: Path) -> dict:
        """Lee un JSON/GeoJSON en UTF-8."""
        return json.loads(ruta.read_text(encoding="utf-8"))

    def hotspots_disponibles(self) -> list[str]:
        return sorted(ruta.stem for ruta in (self.data_dir / "hotspots").glob("*.geojson"))

    def hotspots(self, periodo: str) -> dict | None:
        if periodo not in self.hotspots_disponibles():
            return None
        if periodo not in self._cache_hotspots:
            self._cache_hotspots[periodo] = self._leer_json(
                self.data_dir / "hotspots" / f"{periodo}.geojson"
            )
        return self._cache_hotspots[periodo]


def filtrar_serie(
    repo: RepositorioBase,
    municipios: list[str] | None = None,
    subregion: str | None = None,
    clase: str = CLASE_DEFORESTACION,
    desde: int | None = None,
    hasta: int | None = None,
    incluir_estimados: bool = True,
) -> pd.DataFrame:
    """Aplica los filtros del contrato de `/serie` sobre la serie municipal.

    Lanza :class:`ErrorDatos` (422 parámetro inválido, 404 municipio
    inexistente) para que el router lo traduzca a HTTPException.
    """
    df = repo.serie
    clase_ok = validar_clase(clase)
    df = df[df["clase"] == clase_ok]

    if municipios:
        codigos = [repo.resolver_municipio(m) for m in municipios]
        df = df[df["codigo_dane"].isin(codigos)]
    if subregion:
        df = df[df["subregion"] == validar_subregion(subregion)]
    if desde is not None:
        df = df[df["ano_inicio"] >= desde]
    if hasta is not None:
        df = df[df["ano_fin"] <= hasta]
    if not incluir_estimados:
        df = df[~df["estimado"]]

    return df.sort_values(["ano_inicio", "codigo_dane"]).reset_index(drop=True)
