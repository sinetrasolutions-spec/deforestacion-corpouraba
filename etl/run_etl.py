# -*- coding: utf-8 -*-
"""
ETL — Observatorio de Deforestación CORPOURABA (2000–2024)
===========================================================

Consolida el paquete crudo de monitoreo de bosque (shapefiles, Excel y rásters
por periodo) en datasets listos para la web:

  data/processed/
    municipios.geojson        Límites municipales (19) disueltos + subregión
    subregiones.geojson       Subregiones territoriales CORPOURABA (5)
    serie_municipal.csv       Serie municipio × periodo × clase (ha, fuente, flag)
    serie_regional.csv        Agregado regional por periodo × clase
    hotspots/<periodo>.geojson  Polígonos de deforestación simplificados
    capas/*.geojson           Áreas protegidas, resguardos, consejos, cuencas
    metadata.json             Diccionario de datos, fuentes por periodo, QA

Jerarquía de fuentes por periodo (de mejor a peor):
  1. shapefile   Mpios (polígonos con NOM_MUNICI + área por geometría)
  2. excel       Tabla de atributos exportada (*_Mpios_Dat.xls[x])
  3. cuencas     Excel/dbf de cuencas con NOM_MUNICI + AREA HA (cobertura parcial)
  4. raster      Zonal stats del ráster DEPTO_ANTIOQUIA_<periodo>.img
  5. estimado    Interpolación/tendencia lineal — SIEMPRE con estimado=True

Uso:
  python etl/run_etl.py [--raw RUTA_DATOS_CRUDOS] [--out RUTA_SALIDA]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

if hasattr(sys.stdout, "reconfigure"):  # consolas Windows cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.ops import unary_union

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

DEFAULT_RAW = Path(r"E:\drive-download-20260703T192518Z-3-001")
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "processed"

WGS84 = "EPSG:4326"
METRIC_FALLBACK = "EPSG:3115"  # MAGNA-SIRGAS / Colombia West — CRS dominante del paquete

# Municipios canónicos: ascii → (nombre bonito, código DANE, subregión CORPOURABA)
MUNICIPIOS = {
    "ABRIAQUI":            ("Abriaquí", "05004", "Nutibara"),
    "APARTADO":            ("Apartadó", "05045", "Centro"),
    "ARBOLETES":           ("Arboletes", "05051", "Caribe"),
    "CANASGORDAS":         ("Cañasgordas", "05138", "Nutibara"),
    "CAREPA":              ("Carepa", "05147", "Centro"),
    "CHIGORODO":           ("Chigorodó", "05172", "Centro"),
    "DABEIBA":             ("Dabeiba", "05234", "Nutibara"),
    "FRONTINO":            ("Frontino", "05284", "Nutibara"),
    "GIRALDO":             ("Giraldo", "05306", "Nutibara"),
    "MURINDO":             ("Murindó", "05475", "Atrato"),
    "MUTATA":              ("Mutatá", "05480", "Centro"),
    "NECOCLI":             ("Necoclí", "05490", "Caribe"),
    "PEQUE":               ("Peque", "05543", "Nutibara"),
    "SAN JUAN DE URABA":   ("San Juan de Urabá", "05659", "Caribe"),
    "SAN PEDRO DE URABA":  ("San Pedro de Urabá", "05665", "Caribe"),
    "TURBO":               ("Turbo", "05837", "Centro"),
    "URAMITA":             ("Uramita", "05842", "Nutibara"),
    "URRAO":               ("Urrao", "05847", "Urrao"),
    "VIGIA DEL FUERTE":    ("Vigía del Fuerte", "05873", "Atrato"),
}

CLASES = {
    "BOSQUE ESTABLE":    "Bosque Estable",
    "DEFORESTACION":     "Deforestación",
    "NO BOSQUE ESTABLE": "No Bosque Estable",
    "REGENERACION":      "Regeneración",
    "SIN INFORMACION":   "Sin Información",
}
# gridcode oficial del paquete (verificado contra Tipo_Cober en múltiples periodos)
GRIDCODE_CLASE = {1: "BOSQUE ESTABLE", 2: "DEFORESTACION", 3: "SIN INFORMACION",
                  4: "REGENERACION", 5: "NO BOSQUE ESTABLE"}
# Erratas conocidas en los datos originales
CLASE_ALIASES = {"NO BOSQUE ESTBLE": "NO BOSQUE ESTABLE"}

# Definición de periodos: id, año inicio, año fin
PERIODOS = [
    ("2000-2002", 2000, 2002), ("2002-2004", 2002, 2004), ("2004-2006", 2004, 2006),
    ("2006-2008", 2006, 2008), ("2008-2010", 2008, 2010), ("2010-2012", 2010, 2012),
    ("2012-2013", 2012, 2013), ("2013-2014", 2013, 2014), ("2014-2015", 2014, 2015),
    ("2015-2016", 2015, 2016), ("2016-2017", 2016, 2017), ("2017-2018", 2017, 2018),
    ("2018-2019", 2018, 2019), ("2019-2020", 2019, 2020), ("2020-2021", 2020, 2021),
    ("2021-2022", 2021, 2022), ("2022-2023", 2022, 2023), ("2023-2024", 2023, 2024),
]

# Shapefile municipal preferido por periodo (rutas relativas a RAW).
# Orden dentro de la lista = preferencia (el corregido y proyectado primero).
SHP_MPIOS = {
    "2002-2004": ["2002-2004/Defor2002_2004_Mpios_Proj_Corr.shp",
                  "2002-2004/Defor2002_2004_Mpios_Proje.shp"],
    "2004-2006": ["2004-2006/Defor2004_2006_Mpios_Proj_Corr.shp",
                  "2004-2006/Defor2004_2006_Mpios_Proj.shp"],
    "2006-2008": ["2006-2008/Defor2006_2008_Mpios_V2_Proj_Corr.shp",
                  "2006-2008/Defor2006_2008_Mpios_Proj.shp"],
    "2008-2010": ["2008-2010/Defor2008_2010_Mpios_Proj_Correj.shp",
                  "2008-2010/Defor2008_2010_Mpios_Proj.shp"],
    "2013-2014": ["2013-2014/Corregida14.shp", "2013-2014/Defor2013_2014_Mpios.shp"],
    "2016-2017": ["2016-2017/Defor2016_2017_Mpios_Proj_Correg.shp",
                  "2016-2017/Defor2016_2017_Mpios_Proj.shp"],
    "2017-2018": ["2017-2018/Defor2017_2018_Mpios_Proj_Correg.shp",
                  "2017-2018/Defor2017_2018_Mpios_Proj.shp"],
    "2019-2020": ["2019-2020/Defor2019_2020_Mpios_Proj_Correg.shp",
                  "2019-2020/Defor2019_2020_Mpios_Proj.shp"],
    "2020-2021": ["2020-2021/Defor2020_2021_Mpios_Proj_Correg.shp",
                  "2020-2021/Defor2020_2021_Mpios_Proj.shp"],
    "2021-2022": ["2021-2022/Defor2021_2022_Mpios_Proj_Correg.shp",
                  "2021-2022/Defor2021_2022_Mpios_Proj.shp"],
    "2022-2023": ["2022-2023/Defor2022_2023_Mpios_Proj_Correg.shp",
                  "2022-2023/Defor2022_2023_Mpios_Proj.shp"],
}
EXCEL_MPIOS = {
    "2000-2002": "2000-2002/Defor2000_2002_Mpios_Dat.xls",
    "2014-2015": "2014-2015/Defor2014_2015_Mpios_Dat.xls",
}
# Tabla de atributos municipal (.dbf del shapefile cuya geometría se perdió,
# pero conserva NOM_MUNICI + Tipo_Cober + AREA_ha reales por polígono).
DBF_MPIOS = {
    "2015-2016": "2015-2016/Defor2015_2016_Mpios_Proj_Correg.dbf",
}
# Solo se usa como respaldo si el .dbf municipal del periodo no existiera.
EXCEL_CUENCAS = {
    "2015-2016": "2015-2016/Defor2015-2016_Cuenc_Dat.xlsx",
}
RASTER_MPIOS = {
    "2012-2013": "2012-2013/DEPTO_ANTIOQUIA_2012_2013.img",
}
# Periodos sin fuente municipal → estimación marcada
ESTIMADOS = ["2010-2012", "2018-2019", "2023-2024"]

# Área mínima (ha) de un polígono para aparecer en el visor de hotspots.
# 0.09 ha = 1 píxel del ráster (30 m); incluye los focos de menos de 1 ha.
MIN_HA_HOTSPOT = 0.09

# Capa de referencia para límites municipales (la más reciente completa con CRS)
SHP_LIMITES = "2021-2022/Defor2021_2022_Mpios_Proj.shp"

# Overlays (periodo más reciente con shapefile completo)
OVERLAYS = {
    "areas_protegidas": ("2022-2023/Defor2022_2023_AProteg.shp", ["NOMBRE", "CATEGORIA"]),
    "resguardos":       ("2022-2023/Defor2022_2023_RInd.shp",    ["NOMBRE", "PUEBLO"]),
    "consejos":         ("2022-2023/Defor2022_2023_CCom.shp",    ["NOMBRE"]),
    "cuencas":          ("2022-2023/Defor2022_2023_Cuenc.shp",   ["NOMB CUENC"]),
}

QA_LOG: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    QA_LOG.append(msg)


# ---------------------------------------------------------------------------
# Normalización de texto (nombres con encoding roto: 'CA�ASGORDAS', 'APARTAD�')
# ---------------------------------------------------------------------------

def _ascii(s: str) -> str:
    """Mayúsculas sin tildes; U+FFFD y '?' se vuelven comodín '.'"""
    s = str(s).strip().upper()
    s = s.replace("�", ".").replace("?", ".")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s)
    return s


def _match(raw: str, canon: dict[str, object] | list[str]) -> str | None:
    """Empareja un nombre crudo (posiblemente con bytes perdidos) contra canónicos."""
    key = _ascii(raw)
    keys = list(canon)
    if key in keys:
        return key
    if "." in key:  # comodín por carácter perdido
        pat = re.compile("^" + re.escape(key).replace("\\.", ".") + "$")
        hits = [k for k in keys if pat.match(k)]
        if len(hits) == 1:
            return hits[0]
    # último recurso: comparación sin ningún separador
    flat = re.sub(r"[^A-Z]", "", key)
    hits = [k for k in keys if re.sub(r"[^A-Z]", "", k) == flat]
    return hits[0] if len(hits) == 1 else None


def match_municipio(raw: str) -> str | None:
    return _match(raw, MUNICIPIOS)


def match_clase(raw: str) -> str | None:
    key = _ascii(raw)
    if key in CLASE_ALIASES:
        return CLASE_ALIASES[key]
    return _match(raw, CLASES)


def norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Nombres de columna homogéneos: AREA_ha / AREA HA / AREA-HA → AREA_HA."""
    ren = {}
    for c in df.columns:
        if str(c).lower() == "geometry":
            continue  # nunca tocar la columna de geometría activa
        cu = re.sub(r"[\s\-]+", "_", str(c).strip().upper())
        ren[c] = cu
    return df.rename(columns=ren)


# ---------------------------------------------------------------------------
# Lectura de fuentes
# ---------------------------------------------------------------------------

def read_shp(path: Path) -> gpd.GeoDataFrame:
    """Lee shapefile forzando latin-1 si el UTF-8 declarado produce mojibake."""
    gdf = gpd.read_file(path, engine="pyogrio")
    text_cols = [c for c in gdf.columns if gdf[c].dtype == object]
    sample = " ".join(str(v) for c in text_cols for v in gdf[c].dropna().head(3))
    if "�" in sample:
        try:
            gdf = gpd.read_file(path, engine="pyogrio", encoding="latin-1")
        except Exception:
            pass  # nos quedamos con la versión con comodines; _match los resuelve
    return gdf


def stats_from_table(df: pd.DataFrame, periodo: str, fuente: str,
                     area_col_hints=("AREA_HA",)) -> pd.DataFrame:
    """Tabla cruda (una fila por polígono) → municipio × clase → hectáreas."""
    df = norm_cols(df)
    area_col = next((c for c in area_col_hints if c in df.columns), None)
    if area_col is None:
        raise ValueError(f"{periodo}/{fuente}: sin columna de área ({list(df.columns)})")
    clase_col = "TIPO_COBER" if "TIPO_COBER" in df.columns else "COBERTURA"
    out = []
    df = df.dropna(subset=["NOM_MUNICI"])
    for (m_raw, c_raw), grp in df.groupby(["NOM_MUNICI", clase_col], dropna=False):
        m = match_municipio(m_raw)
        c = match_clase(c_raw) if pd.notna(c_raw) else None
        if m is None or c is None:
            if grp[area_col].sum() > 1:
                log(f"  [WARN] {periodo}: sin match municipio/clase: {m_raw!r}/{c_raw!r} "
                    f"({grp[area_col].sum():.1f} ha descartadas)")
            continue
        out.append({"municipio_key": m, "periodo": periodo, "clase": c,
                    "hectareas": float(grp[area_col].sum()),
                    "fuente": fuente, "estimado": False})
    return pd.DataFrame(out)


def stats_from_shp(path: Path, periodo: str) -> pd.DataFrame:
    """Shapefile municipal → agrega por municipio × clase usando área geométrica."""
    gdf = read_shp(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(METRIC_FALLBACK)
    elif not gdf.crs.is_projected:
        gdf = gdf.to_crs(METRIC_FALLBACK)
    gdf["_ha"] = gdf.geometry.area / 10_000.0
    df = pd.DataFrame(gdf.drop(columns="geometry"))
    df = norm_cols(df)
    df["AREA_HA"] = gdf["_ha"].values
    return stats_from_table(df, periodo, "shapefile")


def stats_from_raster(path: Path, periodo: str, municipios: gpd.GeoDataFrame) -> pd.DataFrame:
    """Zonal stats: cuenta píxeles por clase dentro de cada municipio."""
    import rasterio
    from rasterio import features

    with rasterio.open(path) as src:
        data = src.read(1)
        transform = src.transform
        pixel_ha = abs(transform.a * transform.e) / 10_000.0
        mpios = municipios.to_crs(src.crs)
        shapes = [(geom, idx + 1) for idx, geom in enumerate(mpios.geometry)]
        zones = features.rasterize(shapes, out_shape=data.shape, transform=transform,
                                   fill=0, dtype="uint16")
    out = []
    for idx, row in enumerate(mpios.itertuples()):
        mask = zones == idx + 1
        vals, counts = np.unique(data[mask], return_counts=True)
        for v, n in zip(vals, counts):
            clase = GRIDCODE_CLASE.get(int(v))
            if clase is None:
                continue
            out.append({"municipio_key": row.municipio_key, "periodo": periodo,
                        "clase": clase, "hectareas": float(n) * pixel_ha,
                        "fuente": "raster", "estimado": False})
    return pd.DataFrame(out)


def read_vat_regional(raw: Path, periodo: str) -> dict[str, float] | None:
    """Tabla de atributos del ráster (.img.vat.dbf) → hectáreas por clase.

    Para 2010-2012 el ráster se perdió pero su RAT sobrevive: los conteos de
    píxel dan el total REGIONAL real por clase (los rásters hermanos están
    recortados a la jurisdicción — verificado contra los vectores al ±0.2%).
    """
    vat = raw / periodo / f"DEPTO_ANTIOQUIA_{periodo.replace('-', '_')}.img.vat.dbf"
    if not vat.exists():
        return None
    try:
        from pyogrio import read_dataframe
        df = read_dataframe(vat, read_geometry=False)
    except Exception as e:
        log(f"  [WARN] no se pudo leer RAT {vat.name}: {e}")
        return None
    df = norm_cols(df)
    val_col = next((c for c in df.columns if c in ("VALUE", "VAL")), None)
    cnt_col = next((c for c in df.columns if "COUNT" in c), None)
    if val_col is None or cnt_col is None:
        log(f"  [WARN] RAT {vat.name} sin columnas Value/Count: {list(df.columns)}")
        return None
    # tamaño de píxel tomado de un ráster hermano de la misma malla
    pixel_ha = 0.09  # 30 m nominal
    try:
        import rasterio
        with rasterio.open(raw / RASTER_MPIOS["2012-2013"]) as src:
            pixel_ha = abs(src.transform.a * src.transform.e) / 10_000.0
    except Exception:
        pass
    out: dict[str, float] = {}
    for _, r in df.iterrows():
        clase = GRIDCODE_CLASE.get(int(r[val_col]))
        if clase:
            out[clase] = out.get(clase, 0.0) + float(r[cnt_col]) * pixel_ha
    return out or None


def hotspots_from_raster(raw: Path, out_dir: Path, periodo: str,
                         municipios: gpd.GeoDataFrame) -> int:
    """Vectoriza la clase Deforestación del ráster para el mapa de hotspots."""
    import rasterio
    from rasterio import features as rfeatures

    with rasterio.open(raw / RASTER_MPIOS[periodo]) as src:
        data = src.read(1)
        mask = data == 2  # DEFORESTACION
        shapes = rfeatures.shapes(data, mask=mask, transform=src.transform)
        geoms = [shape(g) for g, v in shapes]
        crs = src.crs
    gdf = gpd.GeoDataFrame(geometry=geoms, crs=crs)
    gdf["ha"] = (gdf.geometry.area / 10_000).round(2)
    gdf = gdf[gdf["ha"] >= MIN_HA_HOTSPOT]
    gdf["geometry"] = gdf.geometry.simplify(25, preserve_topology=True)
    mpios = municipios.to_crs(crs)[["municipio_key", "geometry"]]
    cent = gdf.copy()
    cent["geometry"] = cent.geometry.representative_point()
    joined = gpd.sjoin(cent, mpios, how="left", predicate="within")
    gdf["municipio"] = joined["municipio_key"].map(
        lambda k: MUNICIPIOS[k][0] if pd.notna(k) and k in MUNICIPIOS else None).values
    # El ráster cubre todo Antioquia: recortar a la jurisdicción (parches con
    # municipio asignado). Evita inflar los hotspots con deforestación externa.
    fuera = gdf["municipio"].isna().sum()
    if fuera:
        log(f"  {periodo}: {fuera} parches fuera de la jurisdicción descartados")
    gdf = gdf[gdf["municipio"].notna()]
    gdf = gdf.to_crs(WGS84)[["municipio", "ha", "geometry"]]
    path = out_dir / f"{periodo}.geojson"
    gdf.to_file(path, driver="GeoJSON", COORDINATE_PRECISION=5)
    log(f"  {periodo}: {len(gdf)} polígonos (≥{MIN_HA_HOTSPOT} ha) desde ráster "
        f"({path.stat().st_size/1024:.0f} KB)")
    return len(gdf)


# ---------------------------------------------------------------------------
# Límites municipales
# ---------------------------------------------------------------------------

def _fill_holes(geom, min_area_m2: float = 1_000_000.0):
    """Elimina huecos interiores pequeños producto del dissolve de teselas."""
    def fill(poly: Polygon) -> Polygon:
        rings = [r for r in poly.interiors if Polygon(r).area >= min_area_m2]
        return Polygon(poly.exterior, rings)
    if isinstance(geom, Polygon):
        return fill(geom)
    if isinstance(geom, MultiPolygon):
        return MultiPolygon([fill(p) for p in geom.geoms])
    return geom


def build_municipios(raw: Path) -> gpd.GeoDataFrame:
    log(f"[1/6] Límites municipales desde {SHP_LIMITES} ...")
    gdf = read_shp(raw / SHP_LIMITES)
    if gdf.crs is None:
        gdf = gdf.set_crs(METRIC_FALLBACK)
    gdf["municipio_key"] = gdf["NOM_MUNICI"].map(match_municipio)
    perdidos = gdf[gdf["municipio_key"].isna()]["NOM_MUNICI"].unique()
    if len(perdidos):
        log(f"  [WARN] nombres sin match en límites: {perdidos}")
    gdf = gdf.dropna(subset=["municipio_key"])
    gdf["geometry"] = gdf.geometry.buffer(0)
    diss = gdf.dissolve(by="municipio_key", as_index=False)[["municipio_key", "geometry"]]
    diss["geometry"] = diss.geometry.apply(_fill_holes)
    diss["geometry"] = diss.geometry.simplify(80, preserve_topology=True)
    diss["nombre"] = diss["municipio_key"].map(lambda k: MUNICIPIOS[k][0])
    diss["codigo_dane"] = diss["municipio_key"].map(lambda k: MUNICIPIOS[k][1])
    diss["subregion"] = diss["municipio_key"].map(lambda k: MUNICIPIOS[k][2])
    diss["area_municipio_ha"] = (diss.geometry.area / 10_000).round(1)
    diss = diss.to_crs(WGS84)
    cent = diss.geometry.representative_point()
    diss["centroide"] = [[round(p.x, 5), round(p.y, 5)] for p in cent]
    if len(diss) != 19:
        log(f"  [WARN] se esperaban 19 municipios, hay {len(diss)}")
    log(f"  OK: {len(diss)} municipios")
    return diss


# ---------------------------------------------------------------------------
# Serie municipal
# ---------------------------------------------------------------------------

def build_serie(raw: Path, municipios: gpd.GeoDataFrame) -> pd.DataFrame:
    log("[2/6] Serie municipal por periodo ...")
    frames = []

    for pid, *_ in PERIODOS:
        if pid in SHP_MPIOS:
            src = next((raw / p for p in SHP_MPIOS[pid] if (raw / p).exists()), None)
            if src is None:
                log(f"  [WARN] {pid}: shapefiles esperados no existen"); continue
            df = stats_from_shp(src, pid)
            log(f"  {pid}: shapefile ({src.name}) → {df['hectareas'].sum():,.0f} ha")
        elif pid in EXCEL_MPIOS:
            xl = pd.ExcelFile(raw / EXCEL_MPIOS[pid])
            hoja = xl.sheet_names[0]
            df = stats_from_table(xl.parse(hoja), pid, "excel")
            log(f"  {pid}: excel ({hoja}) → {df['hectareas'].sum():,.0f} ha")
        elif pid in DBF_MPIOS and (raw / DBF_MPIOS[pid]).exists():
            from pyogrio import read_dataframe
            dbf = raw / DBF_MPIOS[pid]
            df = stats_from_table(read_dataframe(dbf, read_geometry=False), pid,
                                  "dbf-municipal")
            n = df["municipio_key"].nunique()
            log(f"  {pid}: tabla municipal dbf ({dbf.name}) → "
                f"{df['hectareas'].sum():,.0f} ha, {n}/19 municipios (dato REAL)")
        elif pid in EXCEL_CUENCAS:
            xl = pd.ExcelFile(raw / EXCEL_CUENCAS[pid])
            df = stats_from_table(xl.parse(xl.sheet_names[0]), pid, "cuencas",
                                  area_col_hints=("AREA_HA", "AREA"))
            n = df["municipio_key"].nunique()
            log(f"  {pid}: excel de cuencas → {n}/19 municipios (cobertura parcial)")
        elif pid in RASTER_MPIOS:
            df = stats_from_raster(raw / RASTER_MPIOS[pid], pid, municipios)
            log(f"  {pid}: zonal stats ráster → {df['hectareas'].sum():,.0f} ha")
        else:
            continue  # periodos estimados se rellenan después
        frames.append(df)

    serie = pd.concat(frames, ignore_index=True)
    serie = calibrar_cuencas_2015_2016(raw, serie)
    serie = estimar_vacios(serie)
    serie = calibrar_con_rat(raw, serie)
    serie = decorar(serie)
    return serie


def calibrar_cuencas_2015_2016(raw: Path, serie: pd.DataFrame) -> pd.DataFrame:
    """2015-2016 solo existe vía cruce con cuencas, que cubren una fracción de
    cada municipio (≈35% en promedio). 2016-2017 tiene AMBAS fuentes, lo que
    permite derivar un factor municipio×clase (mpios/cuencas) y corregir el
    sesgo de cobertura. Resultado marcado estimado=True por transparencia."""
    ruta = raw / "2016-2017" / "Defor2016-2017_Cuenc_Dat.xlsx"
    if "2015-2016" not in set(serie["periodo"]) or not ruta.exists():
        return serie
    # Si 2015-2016 ya salió de una fuente real (tabla municipal .dbf), no se
    # calibra ni se estima: el cruce con cuencas solo era el plan B.
    if not ((serie["periodo"] == "2015-2016") & (serie["fuente"] == "cuencas")).any():
        return serie
    xl = pd.ExcelFile(ruta)
    cu17 = stats_from_table(xl.parse(xl.sheet_names[0]), "2016-2017", "cuencas",
                            area_col_hints=("AREA_HA", "AREA"))
    mp17 = serie[(serie["periodo"] == "2016-2017") & (serie["fuente"] == "shapefile")]
    cu = cu17.set_index(["municipio_key", "clase"])["hectareas"]
    mp = mp17.set_index(["municipio_key", "clase"])["hectareas"]
    factores = (mp / cu).dropna().clip(lower=0.5, upper=12.0)
    mask = (serie["periodo"] == "2015-2016") & (serie["fuente"] == "cuencas")
    idx = serie.loc[mask].set_index(["municipio_key", "clase"]).index
    f = pd.Series(factores.reindex(idx).values, index=serie.loc[mask].index).fillna(1.0)
    antes = serie.loc[mask & (serie["clase"] == "DEFORESTACION"), "hectareas"].sum()
    serie.loc[mask, "hectareas"] = serie.loc[mask, "hectareas"] * f
    serie.loc[mask, "fuente"] = "cuencas-calibrado"
    serie.loc[mask, "estimado"] = True
    despues = serie.loc[mask & (serie["clase"] == "DEFORESTACION"), "hectareas"].sum()
    log(f"  2015-2016: calibración por cuencas {antes:,.0f} ha -> {despues:,.0f} ha "
        f"(factores municipio×clase desde 2016-2017)")
    # municipios ausentes del cruce de cuencas (Murindó, Vigía del Fuerte):
    presentes = set(serie.loc[mask, "municipio_key"])
    faltan = [m for m in MUNICIPIOS if m not in presentes]
    filas = []
    for mkey in faltan:
        vecinos = []
        for p in ("2014-2015", "2016-2017"):
            v = serie[(serie["periodo"] == p) & (serie["municipio_key"] == mkey) &
                      (serie["clase"] == "DEFORESTACION") & (~serie["estimado"])]
            if len(v):
                vecinos.append(float(v["hectareas"].sum()))
        if vecinos:
            filas.append({"municipio_key": mkey, "periodo": "2015-2016",
                          "clase": "DEFORESTACION",
                          "hectareas": round(float(np.mean(vecinos)), 2),
                          "fuente": "estimado", "estimado": True})
    if filas:
        log(f"  2015-2016: {len(filas)} municipios sin cobertura de cuencas "
            f"estimados por interpolación: {[MUNICIPIOS[f['municipio_key']][0] for f in filas]}")
        serie = pd.concat([serie, pd.DataFrame(filas)], ignore_index=True)
    return serie


def calibrar_con_rat(raw: Path, serie: pd.DataFrame) -> pd.DataFrame:
    """Corrige el total de 2010-2012 usando el RAT del ráster departamental.

    Los rásters DEPTO_ANTIOQUIA_* cubren TODO Antioquia (~6.3 M ha), no solo la
    jurisdicción. El RAT de 2010-2012 da la deforestación departamental real;
    la participación de la jurisdicción en el total departamental es estable en
    los periodos verificables (2008-2010 y 2012-2013), así que:
        objetivo = defo_dptal(2010-2012) × participación_promedio
    y las estimaciones municipales se escalan a ese objetivo."""
    reg = read_vat_regional(raw, "2010-2012")
    if not reg or "DEFORESTACION" not in reg:
        log("  [INFO] 2010-2012: sin RAT utilizable; queda estimación pura")
        return serie
    participaciones = []
    for p in ("2008-2010", "2012-2013"):
        dep = read_vat_regional(raw, p)
        if not dep or "DEFORESTACION" not in dep:
            continue
        jur = serie[(serie["periodo"] == p) & (serie["clase"] == "DEFORESTACION") &
                    (~serie["estimado"])]["hectareas"].sum()
        if jur > 0 and dep["DEFORESTACION"] > 0:
            participaciones.append(jur / dep["DEFORESTACION"])
    if not participaciones:
        log("  [INFO] 2010-2012: sin periodos de referencia para participación; "
            "queda estimación pura")
        return serie
    share = float(np.mean(participaciones))
    objetivo = reg["DEFORESTACION"] * share
    mask = ((serie["periodo"] == "2010-2012") & (serie["clase"] == "DEFORESTACION")
            & serie["estimado"])
    suma = serie.loc[mask, "hectareas"].sum()
    if suma <= 0:
        return serie
    factor = objetivo / suma
    serie.loc[mask, "hectareas"] = (serie.loc[mask, "hectareas"] * factor).round(2)
    serie.loc[mask, "fuente"] = "estimado-calibrado-rat"
    log(f"  2010-2012: defo. dptal real {reg['DEFORESTACION']:,.0f} ha × participación "
        f"jurisdicción {share:.1%} = objetivo {objetivo:,.0f} ha (factor {factor:.3f})")
    return serie


def estimar_vacios(serie: pd.DataFrame) -> pd.DataFrame:
    """Rellena DEFORESTACION para periodos sin fuente, con flag estimado=True."""
    log("[3/6] Estimación de vacíos (solo clase Deforestación, flag estimado) ...")
    orden = [p[0] for p in PERIODOS]
    defo = (serie[serie["clase"] == "DEFORESTACION"]
            .pivot_table(index="municipio_key", columns="periodo",
                         values="hectareas", aggfunc="sum"))
    # anualizar para comparar periodos de 1 y 2 años
    nyears = {p: (fin - ini) for p, ini, fin in PERIODOS}
    filas = []
    for pid in ESTIMADOS:
        i = orden.index(pid)
        for mkey in MUNICIPIOS:
            antes = [orden[j] for j in range(i - 1, -1, -1)
                     if orden[j] in defo.columns and pd.notna(defo.at[mkey, orden[j]])
                     if mkey in defo.index]
            despues = [orden[j] for j in range(i + 1, len(orden))
                       if orden[j] in defo.columns and pd.notna(defo.at[mkey, orden[j]])
                       if mkey in defo.index]
            val_anual = None
            if antes and despues:  # interpolación lineal en tasa anual
                a, d = antes[0], despues[0]
                va = defo.at[mkey, a] / nyears[a]
                vd = defo.at[mkey, d] / nyears[d]
                val_anual = (va + vd) / 2.0
            elif len(antes) >= 3:  # extrapolación: tendencia de los 3 previos
                xs = np.arange(3)
                ys = np.array([defo.at[mkey, antes[k]] / nyears[antes[k]]
                               for k in (2, 1, 0)])
                coef = np.polyfit(xs, ys, 1)
                val_anual = max(0.0, float(np.polyval(coef, 3)))
            elif antes:
                val_anual = defo.at[mkey, antes[0]] / nyears[antes[0]]
            if val_anual is None:
                continue
            filas.append({"municipio_key": mkey, "periodo": pid,
                          "clase": "DEFORESTACION",
                          "hectareas": round(val_anual * nyears[pid], 2),
                          "fuente": "estimado", "estimado": True})
        log(f"  {pid}: estimado para {sum(1 for f in filas if f['periodo'] == pid)} municipios")
    return pd.concat([serie, pd.DataFrame(filas)], ignore_index=True)


def decorar(serie: pd.DataFrame) -> pd.DataFrame:
    """Añade columnas legibles y anualizadas; ordena."""
    meta = {p: (ini, fin) for p, ini, fin in PERIODOS}
    serie["ano_inicio"] = serie["periodo"].map(lambda p: meta[p][0])
    serie["ano_fin"] = serie["periodo"].map(lambda p: meta[p][1])
    ny = (serie["ano_fin"] - serie["ano_inicio"]).clip(lower=1)
    serie["hectareas"] = serie["hectareas"].round(2)
    serie["hectareas_anuales"] = (serie["hectareas"] / ny).round(2)
    serie["municipio"] = serie["municipio_key"].map(lambda k: MUNICIPIOS[k][0])
    serie["codigo_dane"] = serie["municipio_key"].map(lambda k: MUNICIPIOS[k][1])
    serie["subregion"] = serie["municipio_key"].map(lambda k: MUNICIPIOS[k][2])
    serie["clase"] = serie["clase"].map(CLASES)
    cols = ["codigo_dane", "municipio", "subregion", "periodo", "ano_inicio", "ano_fin",
            "clase", "hectareas", "hectareas_anuales", "fuente", "estimado"]
    return (serie[cols + ["municipio_key"]]
            .sort_values(["periodo", "municipio", "clase"])
            .reset_index(drop=True))


# ---------------------------------------------------------------------------
# Hotspots (polígonos de deforestación por periodo, simplificados)
# ---------------------------------------------------------------------------

def build_hotspots(raw: Path, out: Path,
                   municipios: gpd.GeoDataFrame) -> dict[str, int]:
    log("[4/6] Hotspots de deforestación por periodo ...")
    hotdir = out / "hotspots"
    hotdir.mkdir(parents=True, exist_ok=True)
    resumen = {}
    for pid in RASTER_MPIOS:
        try:
            resumen[pid] = hotspots_from_raster(raw, hotdir, pid, municipios)
        except Exception as e:
            log(f"  [WARN] hotspots ráster {pid}: {e}")
    for pid, rutas in SHP_MPIOS.items():
        src = next((raw / p for p in rutas if (raw / p).exists()), None)
        if src is None:
            continue
        gdf = read_shp(src)
        if gdf.crs is None:
            gdf = gdf.set_crs(METRIC_FALLBACK)
        clase_col = "Tipo_Cober" if "Tipo_Cober" in gdf.columns else "Cobertura"
        gdf["_clase"] = gdf[clase_col].map(match_clase)
        defo = gdf[gdf["_clase"] == "DEFORESTACION"].copy()
        if defo.empty:
            continue
        if not defo.crs.is_projected:
            defo = defo.to_crs(METRIC_FALLBACK)
        defo["ha"] = (defo.geometry.area / 10_000).round(2)
        defo = defo[defo["ha"] >= MIN_HA_HOTSPOT]  # incluye focos < 1 ha
        defo["municipio"] = defo["NOM_MUNICI"].map(
            lambda x: MUNICIPIOS.get(match_municipio(x), (None,))[0])
        defo["geometry"] = defo.geometry.simplify(25, preserve_topology=True)
        defo = defo.to_crs(WGS84)[["municipio", "ha", "geometry"]]
        path = hotdir / f"{pid}.geojson"
        defo.to_file(path, driver="GeoJSON", COORDINATE_PRECISION=5)
        resumen[pid] = len(defo)
        log(f"  {pid}: {len(defo)} polígonos (≥{MIN_HA_HOTSPOT} ha) "
            f"({path.stat().st_size/1024:.0f} KB)")
    return resumen


# ---------------------------------------------------------------------------
# Overlays
# ---------------------------------------------------------------------------

def build_overlays(raw: Path, out: Path) -> dict[str, int]:
    log("[5/6] Capas de contexto (overlays) ...")
    capdir = out / "capas"
    capdir.mkdir(parents=True, exist_ok=True)
    resumen = {}
    for nombre, (ruta, campos) in OVERLAYS.items():
        src = raw / ruta
        if not src.exists():
            log(f"  [WARN] overlay {nombre}: no existe {ruta}")
            continue
        gdf = read_shp(src)
        if gdf.crs is None:
            gdf = gdf.set_crs(METRIC_FALLBACK)
        gdf = norm_cols(gdf)
        campos_n = [re.sub(r"[\s\-]+", "_", c.upper()) for c in campos]
        campos_ok = [c for c in campos_n if c in gdf.columns]
        if not campos_ok:
            log(f"  [WARN] overlay {nombre}: faltan campos {campos_n} en {list(gdf.columns)}")
            continue
        clase_col = "TIPO_COBER" if "TIPO_COBER" in gdf.columns else (
            "COBERTURA" if "COBERTURA" in gdf.columns else None)
        proj = gdf if gdf.crs.is_projected else gdf.to_crs(METRIC_FALLBACK)
        proj["_ha"] = proj.geometry.area / 10_000
        # deforestación reciente dentro de cada unidad
        defo_ha = {}
        if clase_col:
            d = proj[proj[clase_col].map(match_clase) == "DEFORESTACION"]
            defo_ha = d.groupby(campos_ok[0])["_ha"].sum().round(1).to_dict()
        proj["geometry"] = proj.geometry.buffer(0)
        diss = proj.dissolve(by=campos_ok[0], as_index=False)
        diss["area_ha"] = diss.geometry.area / 10_000
        diss["deforestacion_ha_ultimo_periodo"] = (
            diss[campos_ok[0]].map(defo_ha).fillna(0.0))
        diss["geometry"] = diss.geometry.simplify(60, preserve_topology=True)
        keep = campos_ok + ["area_ha", "deforestacion_ha_ultimo_periodo", "geometry"]
        diss = diss.to_crs(WGS84)[keep]
        diss.columns = [c.lower() for c in diss.columns[:-1]] + ["geometry"]
        diss["area_ha"] = diss["area_ha"].round(1)
        path = capdir / f"{nombre}.geojson"
        diss.to_file(path, driver="GeoJSON", COORDINATE_PRECISION=5)
        resumen[nombre] = len(diss)
        log(f"  {nombre}: {len(diss)} unidades ({path.stat().st_size/1024:.0f} KB)")
    return resumen


# ---------------------------------------------------------------------------
# QA: comparar contra hojas 'Cálculos' cuando existen
# ---------------------------------------------------------------------------

def qa_calculos(raw: Path, serie: pd.DataFrame) -> list[dict]:
    log("[6/6] QA contra hojas 'Cálculos' de los Excel originales ...")
    checks = []
    for pid, ini, fin in PERIODOS:
        carpeta = raw / pid
        if not carpeta.exists():
            continue
        for xls in carpeta.glob("*Mpios_Dat.xls*"):
            try:
                xl = pd.ExcelFile(xls)
                hoja = next((s for s in xl.sheet_names if _ascii(s).startswith("CALCULOS")), None)
                if hoja is None:
                    continue
                df = norm_cols(xl.parse(hoja))
                col_def = next((c for c in df.columns if _ascii(c).startswith("DEFORESTACI")), None)
                col_mun = next((c for c in df.columns if _ascii(c).startswith("MUNICIPIO")), None)
                if col_def is None or col_mun is None:
                    continue
                df["_m"] = df[col_mun].map(lambda x: match_municipio(x) if pd.notna(x) else None)
                ref = df.dropna(subset=["_m"]).groupby("_m")[col_def].sum()
                mio = (serie[(serie["periodo"] == pid) &
                             (serie["clase"] == "Deforestación") &
                             (~serie["estimado"])]
                       .groupby("municipio_key")["hectareas"].sum())
                comunes = ref.index.intersection(mio.index)
                if not len(comunes):
                    continue
                diff = float((mio[comunes] - ref[comunes]).abs().sum())
                tot = float(ref[comunes].sum())
                pct = 100.0 * diff / tot if tot else 0.0
                checks.append({"periodo": pid, "hoja": hoja, "archivo": xls.name,
                               "total_referencia_ha": round(tot, 1),
                               "diferencia_abs_ha": round(diff, 1),
                               "diferencia_pct": round(pct, 2)})
                nivel = "OK" if pct < 5 else "REVISAR"
                log(f"  {pid} vs {hoja}: dif {pct:.2f}% [{nivel}]")
            except Exception as e:
                log(f"  [WARN] QA {xls.name}: {e}")
    return checks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    raw, out = args.raw, args.out
    out.mkdir(parents=True, exist_ok=True)

    municipios = build_municipios(raw)
    serie = build_serie(raw, municipios)
    hot = build_hotspots(raw, out, municipios)
    over = build_overlays(raw, out)
    checks = qa_calculos(raw, serie)

    # --- salidas ---
    mun_out = municipios[["municipio_key", "codigo_dane", "nombre", "subregion",
                          "area_municipio_ha", "centroide", "geometry"]]
    mun_out.to_file(out / "municipios.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)

    sub = municipios.dissolve(by="subregion", as_index=False)[["subregion", "geometry"]]
    sub["geometry"] = sub.geometry.simplify(0.001, preserve_topology=True)
    sub.to_file(out / "subregiones.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)

    serie.drop(columns=["municipio_key"]).to_csv(out / "serie_municipal.csv",
                                                 index=False, encoding="utf-8-sig")
    regional = (serie.groupby(["periodo", "ano_inicio", "ano_fin", "clase"], as_index=False)
                .agg(hectareas=("hectareas", "sum"),
                     hectareas_anuales=("hectareas_anuales", "sum"),
                     estimado=("estimado", "any")))
    regional.to_csv(out / "serie_regional.csv", index=False, encoding="utf-8-sig")

    metadata = {
        "titulo": "Observatorio de Deforestación CORPOURABA 2000–2024",
        "generado": datetime.now(timezone.utc).isoformat(),
        "crs_salida": WGS84,
        "crs_origen": "EPSG:3115 / MAGNA-SIRGAS Bogotá (métricos)",
        "clases": {v: k for k, v in CLASES.items()},
        "gridcode": {str(k): CLASES[v] for k, v in GRIDCODE_CLASE.items()},
        "periodos": [{"id": p, "ano_inicio": i, "ano_fin": f, "anos": f - i,
                      "fuente": ("shapefile" if p in SHP_MPIOS else
                                 "excel" if p in EXCEL_MPIOS else
                                 "tabla municipal (dbf)" if p in DBF_MPIOS else
                                 "cuencas (parcial)" if p in EXCEL_CUENCAS else
                                 "raster (zonal stats)" if p in RASTER_MPIOS else
                                 "estimado")}
                     for p, i, f in PERIODOS],
        "municipios": [{"key": k, "nombre": v[0], "codigo_dane": v[1], "subregion": v[2]}
                       for k, v in MUNICIPIOS.items()],
        "vacios_estimados": ESTIMADOS,
        "nota_estimados": ("2010-2012, 2018-2019 y 2023-2024 carecen de datos municipales "
                           "en el paquete original; se estiman por interpolación/tendencia "
                           "de la tasa anual y se marcan con estimado=true. 2010-2012 se "
                           "calibra además con el total departamental real del RAT del "
                           "ráster (× participación histórica de la jurisdicción ~18%). "
                           "Usar solo como referencia, no como cifra oficial."),
        "nota_2015_2016": ("2015-2016 se calcula con la tabla de atributos municipal "
                           "oficial (Defor2015_2016_Mpios_Proj_Correg.dbf): área real por "
                           "municipio y clase de los 19 municipios (San Juan de Urabá con "
                           "0 ha de deforestación). Es dato MEDIDO (estimado=false), no una "
                           "estimación. La geometría (.shp) de este periodo no se conservó, "
                           "por lo que no aparece en el visor de polígonos, pero las cifras "
                           "del dashboard y la serie son reales."),
        "hotspots_features": hot,
        "overlays_unidades": over,
        "qa_calculos": checks,
        "log": QA_LOG,
    }
    (out / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=1),
                                       encoding="utf-8")

    log(f"\nETL COMPLETO → {out}")
    log(f"  serie_municipal: {len(serie)} filas | periodos: {serie['periodo'].nunique()}"
        f" | municipios: {serie['municipio'].nunique()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
