# -*- coding: utf-8 -*-
"""
Análisis: TERRITORIOS ÉTNICOS — Observatorio de Deforestación CORPOURABA 2000-2024
===================================================================================

Construye las series por resguardo indígena (NOMBRE × PUEBLO) y por consejo
comunitario (NOMBRE) × periodo × clase de cobertura, a partir de las capas
*_RInd / *_RI_Dat y *_CCom / *_CC_Dat del paquete crudo.

Jerarquía de fuentes por periodo y capa:
  1. shapefile completo (geometría en CRS métrico) → hectáreas desde geometría
  2. Excel *_Dat.xlsx con columna de área ('AREA HA')  → hectáreas de la tabla
  3. Excel/dbf sin columna de área → SOLO conteo de polígonos (hectareas = NaN,
     calidad_fuente='solo_conteo')
  4. sin fuente → periodo declarado ausente

Notas de calidad detectadas y manejadas:
  * 2023-2024 usa un gridcode distinto (1=Bosque Estable, 2=Deforestación,
    4=No Bosque Estable). Por eso la clase se toma SIEMPRE del texto
    Tipo_Cober/Cobertura (via run_etl.match_clase) y el gridcode solo es
    respaldo con el mapa estándar.
  * Mojibake UTF-8→latin1 en el dbf huérfano 2023-2024 ('ManatÃ­es') → reparado.
  * 2023-2024 no tiene datos de resguardos (solo .shx/.prj/.qmd huérfanos).
  * 2018-2019 no existe como carpeta en el paquete crudo.

Salidas (data/processed/analisis/):
  resguardos_serie.csv, consejos_serie.csv, territorios_etnicos_resumen.json

Uso:  python etl/analisis/territorios_etnicos.py
"""
from __future__ import annotations

import json
import sys
import warnings
from collections import Counter
from pathlib import Path

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run_etl  # helpers verificados del ETL principal

import geopandas as gpd
import numpy as np
import pandas as pd
from pyogrio import read_dataframe

RAW = Path(r"E:\drive-download-20260703T192518Z-3-001")
OUT = RAW / "observatorio-deforestacion" / "data" / "processed" / "analisis"
PROCESSED = RAW / "observatorio-deforestacion" / "data" / "processed"
METRIC = "EPSG:3115"

PERIODOS = run_etl.PERIODOS  # 18 periodos 2000-2024 (incluye 2018-2019 sin carpeta)
NYEARS = {p: (f - i) for p, i, f in PERIODOS}

# ---------------------------------------------------------------------------
# Inventario de fuentes por periodo × capa (verificado contra el paquete crudo)
# ('shp'|'xlsx'|'dbf', ruta relativa) en orden de preferencia; [] = sin fuente
# ---------------------------------------------------------------------------
FUENTES = {
    "resguardos": {
        "2000-2002": [("xlsx", "2000-2002/Defor2000_2002_RI_Dat.xlsx")],
        "2002-2004": [("shp", "2002-2004/Defor2002_2004_RInd.shp")],
        "2004-2006": [("shp", "2004-2006/Defor2004_2006_RInd.shp")],
        "2006-2008": [("shp", "2006-2008/Defor2006_2008_RInd.shp"),
                      ("xlsx", "2006-2008/Defor2006_2008_RI_Dat.xlsx")],
        "2008-2010": [("shp", "2008-2010/Defor2008_2010_RInd.shp")],
        "2015-2016": [("shp", "2015-2016/Defor2015_2016_RInd.shp"),
                      ("xlsx", "2015-2016/Defor2015-2016_RI_Dat.xlsx")],
        "2016-2017": [("shp", "2016-2017/Defor2016_2017_RInd.shp"),
                      ("xlsx", "2016-2017/Defor2016-2017_RI_Dat.xlsx")],
        "2017-2018": [("shp", "2017-2018/Defor2017_2018_RInd.shp")],
        "2019-2020": [("shp", "2019-2020/Defor2019_2020_RInd.shp"),
                      ("xlsx", "2019-2020/Defor2019-2020_RI_Dat.xlsx")],
        "2020-2021": [("shp", "2020-2021/Defor2020_2021_RInd.shp"),
                      ("xlsx", "2020-2021/Defor2020-2021_RI_Dat.xlsx")],
        "2021-2022": [("shp", "2021-2022/Defor2021_2022_RInd.shp"),
                      ("xlsx", "2021-2022/Defor2021-2022_RI_Dat.xlsx")],
        "2022-2023": [("shp", "2022-2023/Defor2022_2023_RInd.shp"),
                      ("xlsx", "2022-2023/Defor2022-2023_RI_Dat.xlsx")],
        # 2010-2012, 2012-2013, 2013-2014, 2014-2015, 2018-2019, 2023-2024: sin fuente
    },
    "consejos": {
        "2002-2004": [("shp", "2002-2004/Defor2002_2004_CCom.shp"),
                      ("xlsx", "2002-2004/Defor2002_2004_CC_Dat.xlsx")],
        "2004-2006": [("shp", "2004-2006/Defor2004_2006_CCom.shp")],
        "2006-2008": [("shp", "2006-2008/Defor2006_2008_Mpios_V2_Proj_Corr_CCom.shp"),
                      ("xlsx", "2006-2008/Defor2006_2008_CC_Dat.xlsx")],
        "2008-2010": [("shp", "2008-2010/Defor2008_2010_CCom.shp")],
        "2014-2015": [("xlsx", "2014-2015/Defor2014_2015_CC_Dat.xlsx")],   # sin área
        "2015-2016": [("dbf", "2015-2016/Defor2015_2016_CCom.dbf")],       # sin área
        "2016-2017": [("shp", "2016-2017/Defor2016_2017_CCom.shp"),
                      ("xlsx", "2016-2017/Defor2016-2017_CC_Dat.xlsx")],
        "2017-2018": [("shp", "2017-2018/Defor2017_2018_CCom.shp")],
        "2019-2020": [("shp", "2019-2020/Defor2019_2020_CCom.shp"),
                      ("xlsx", "2019-2020/Defor2019-2020_CC_Dat.xlsx")],
        "2020-2021": [("shp", "2020-2021/Defor2020_2021_CCom.shp"),
                      ("xlsx", "2020-2021/Defor2020-2021_CC_Dat.xlsx")],
        "2021-2022": [("shp", "2021-2022/Defor2021_2022_CCom.shp"),
                      ("xlsx", "2021-2022/Defor2021-2022_CC_Dat.xlsx")],
        "2022-2023": [("shp", "2022-2023/Defor2022_2023_CCom.shp"),
                      ("xlsx", "2022-2023/Defor2022-2023_CC_Dat.xlsx")],
        "2023-2024": [("xlsx", "2023-2024/Defor2023-2024_CC_Dat.xlsx"),
                      ("dbf", "2023-2024/Defor2023-2024_CCom.dbf")],
        # 2000-2002, 2010-2012, 2012-2013, 2013-2014, 2018-2019: sin fuente
    },
}

# Normalización de pueblo indígena (grafías variables entre periodos)
PUEBLO_NORM = {
    "EMBERA": "Embera",
    "EMBERA KATIO": "Embera Katío",
    "EMBERA CHAMI ZENU": "Embera Chamí-Zenú",
    "EMBERA CHAMI": "Embera Chamí",
    "SENU": "Senú/Zenú",
    "ZENU": "Senú/Zenú",
    "CUNA": "Tule/Guna (Cuna)",
    "TULE": "Tule/Guna (Cuna)",
    "GUNA": "Tule/Guna (Cuna)",
}

LOG: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    LOG.append(msg)


def fix_moji(s):
    """Repara mojibake UTF-8 leído como latin-1 ('ManatÃ­es' → 'Manatíes')."""
    if not isinstance(s, str):
        return s
    if "Ã" in s or "Â" in s:
        try:
            rep = s.encode("latin-1").decode("utf-8")
            if "Ã" not in rep:
                return rep
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    return " ".join(s.split())


def clean_name(s):
    if not isinstance(s, str):
        return s
    return " ".join(fix_moji(s).split())


def norm_pueblo(raw) -> str:
    if pd.isna(raw):
        return "Sin dato"
    key = run_etl._ascii(raw)
    return PUEBLO_NORM.get(key, str(raw).strip().title())


def clase_fila(tipo, gridcode) -> str | None:
    """Clase de cobertura: texto Tipo_Cober manda; gridcode solo de respaldo."""
    if pd.notna(tipo):
        c = run_etl.match_clase(tipo)
        if c:
            return c
    if pd.notna(gridcode):
        try:
            return run_etl.GRIDCODE_CLASE.get(int(gridcode))
        except (ValueError, TypeError):
            return None
    return None


# ---------------------------------------------------------------------------
# Lectura de una fuente → DataFrame plano con columnas estándar
# ---------------------------------------------------------------------------

def leer_fuente(kind: str, rel: str, periodo: str):
    """→ (df[NOMBRE, PUEBLO?, CLASE, HA], fuente, calidad) o None si ilegible."""
    path = RAW / rel
    if not path.exists():
        return None
    if kind == "shp":
        gdf = run_etl.read_shp(path)
        if gdf.crs is None:
            gdf = gdf.set_crs(METRIC)
        elif not gdf.crs.is_projected:
            gdf = gdf.to_crs(METRIC)
        ha = gdf.geometry.area / 10_000.0
        df = pd.DataFrame(gdf.drop(columns="geometry"))
        df = run_etl.norm_cols(df)
        df["_HA"] = ha.values
        return df, "shapefile", "geometria"
    if kind == "xlsx":
        df = run_etl.norm_cols(pd.read_excel(path))
    else:  # dbf huérfano
        df = run_etl.norm_cols(read_dataframe(path, read_geometry=False))
    area_col = next((c for c in ("AREA_HA", "AREA") if c in df.columns), None)
    if area_col:
        df["_HA"] = pd.to_numeric(df[area_col], errors="coerce")
        return df, "excel" if kind == "xlsx" else "dbf", "tabla_area"
    df["_HA"] = np.nan
    return df, "excel" if kind == "xlsx" else "dbf", "solo_conteo"


def procesar_capa(capa: str) -> pd.DataFrame:
    """Serie territorio × periodo × clase para 'resguardos' o 'consejos'."""
    filas = []
    for pid, ini, fin in PERIODOS:
        candidatos = FUENTES[capa].get(pid, [])
        elegido = None
        for kind, rel in candidatos:
            res = leer_fuente(kind, rel, pid)
            if res is not None:
                # preferir la primera fuente CON área; si es solo_conteo,
                # mirar si otro candidato trae área
                if res[2] != "solo_conteo" or elegido is None:
                    elegido = (kind, rel, res)
                if res[2] != "solo_conteo":
                    break
        if elegido is None:
            log(f"  {capa} {pid}: SIN FUENTE")
            continue
        kind, rel, (df, fuente, calidad) = elegido
        df = df.copy()
        df["NOMBRE"] = df["NOMBRE"].map(clean_name)
        tipo_col = next((c for c in ("TIPO_COBER", "COBERTURA") if c in df.columns), None)
        grid_col = "GRIDCODE" if "GRIDCODE" in df.columns else None
        df["_CLASE"] = [
            clase_fila(r[tipo_col] if tipo_col else np.nan,
                       r[grid_col] if grid_col else np.nan)
            for _, r in df.iterrows()
        ]
        sin_clase = int(df["_CLASE"].isna().sum())
        if sin_clase:
            log(f"  [WARN] {capa} {pid}: {sin_clase} filas sin clase reconocible")
        df = df.dropna(subset=["_CLASE", "NOMBRE"])
        if capa == "resguardos":
            df["_PUEBLO"] = df.get("PUEBLO", pd.Series(index=df.index, dtype=object)) \
                              .map(norm_pueblo)
            claves = ["NOMBRE", "_PUEBLO", "_CLASE"]
        else:
            claves = ["NOMBRE", "_CLASE"]
        agg = (df.groupby(claves, dropna=False)
                 .agg(hectareas=("_HA", "sum"), poligonos=("_HA", "size"))
                 .reset_index())
        if calidad == "solo_conteo":
            agg["hectareas"] = np.nan
        agg["periodo"], agg["fuente"], agg["calidad_fuente"] = pid, fuente, calidad
        filas.append(agg)
        tot = agg["hectareas"].sum()
        log(f"  {capa} {pid}: {fuente}/{calidad} → "
            f"{agg['NOMBRE'].nunique()} territorios, "
            f"{'%.0f ha' % tot if pd.notna(tot) and calidad != 'solo_conteo' else 'solo conteos'}")
    if not filas:
        return pd.DataFrame()
    serie = pd.concat(filas, ignore_index=True)

    # nombre canónico por clave ascii (grafías varían entre periodos)
    serie["_KEY"] = serie["NOMBRE"].map(run_etl._ascii)
    canon = (serie.groupby("_KEY")["NOMBRE"]
                  .agg(lambda s: Counter(s).most_common(1)[0][0]))
    serie["NOMBRE"] = serie["_KEY"].map(canon)
    if capa == "resguardos":
        # pueblo canónico por resguardo (algún periodo trae grafía distinta)
        pcanon = (serie.groupby("_KEY")["_PUEBLO"]
                       .agg(lambda s: Counter(s).most_common(1)[0][0]))
        serie["_PUEBLO"] = serie["_KEY"].map(pcanon)
        serie = (serie.groupby(["_KEY", "NOMBRE", "_PUEBLO", "_CLASE", "periodo",
                                "fuente", "calidad_fuente"], dropna=False)
                      .agg(hectareas=("hectareas", "sum"), poligonos=("poligonos", "sum"))
                      .reset_index())
    serie["ano_inicio"] = serie["periodo"].map({p: i for p, i, f in PERIODOS})
    serie["ano_fin"] = serie["periodo"].map({p: f for p, i, f in PERIODOS})
    ny = serie["periodo"].map(NYEARS).clip(lower=1)
    serie["hectareas"] = serie["hectareas"].round(2)
    serie["hectareas_anuales"] = (serie["hectareas"] / ny).round(2)
    serie["clase"] = serie["_CLASE"].map(run_etl.CLASES)
    return serie


# ---------------------------------------------------------------------------
# QA: solapamiento resguardos ∩ consejos (2022-2023, mejor periodo con geometría)
# ---------------------------------------------------------------------------

def qa_solape() -> dict:
    try:
        ri = run_etl.read_shp(RAW / "2022-2023/Defor2022_2023_RInd.shp")
        cc = run_etl.read_shp(RAW / "2022-2023/Defor2022_2023_CCom.shp")
        for g in (ri, cc):
            if g.crs is None:
                g.set_crs(METRIC, inplace=True)
        u_ri = ri.geometry.buffer(0).union_all()
        u_cc = cc.geometry.buffer(0).union_all()
        inter = u_ri.intersection(u_cc).area / 10_000.0
        return {"periodo": "2022-2023",
                "area_resguardos_ha": round(u_ri.area / 10_000, 1),
                "area_consejos_ha": round(u_cc.area / 10_000, 1),
                "solape_ha": round(inter, 1)}
    except Exception as e:
        log(f"  [WARN] QA solape falló: {e}")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    log("=== Series por territorio étnico ===")
    res = procesar_capa("resguardos")
    con = procesar_capa("consejos")

    cols_r = ["periodo", "ano_inicio", "ano_fin", "resguardo", "pueblo", "clase",
              "hectareas", "hectareas_anuales", "poligonos", "fuente", "calidad_fuente"]
    res_out = res.rename(columns={"NOMBRE": "resguardo", "_PUEBLO": "pueblo"})[cols_r] \
                 .sort_values(["periodo", "resguardo", "clase"])
    res_out.to_csv(OUT / "resguardos_serie.csv", index=False, encoding="utf-8-sig")

    cols_c = ["periodo", "ano_inicio", "ano_fin", "consejo", "clase",
              "hectareas", "hectareas_anuales", "poligonos", "fuente", "calidad_fuente"]
    con_out = con.rename(columns={"NOMBRE": "consejo"})[cols_c] \
                 .sort_values(["periodo", "consejo", "clase"])
    con_out.to_csv(OUT / "consejos_serie.csv", index=False, encoding="utf-8-sig")
    log(f"CSV: resguardos_serie ({len(res_out)} filas), consejos_serie ({len(con_out)} filas)")

    # ---------------- síntesis ----------------
    DEF, REG = "Deforestación", "Regeneración"
    reg_ref = pd.read_csv(PROCESSED / "serie_regional.csv")
    defo_reg = (reg_ref[reg_ref["clase"] == DEF]
                .set_index("periodo")["hectareas"].to_dict())

    r_area = res_out[res_out["calidad_fuente"] != "solo_conteo"]
    c_area = con_out[con_out["calidad_fuente"] != "solo_conteo"]

    # fracción étnica de la deforestación jurisdiccional, por periodo
    per_r = set(r_area["periodo"]); per_c = set(c_area["periodo"])
    fraccion = []
    for pid, ini, fin in PERIODOS:
        dr = r_area[(r_area["periodo"] == pid) & (r_area["clase"] == DEF)]["hectareas"].sum() \
            if pid in per_r else None
        dc = c_area[(c_area["periodo"] == pid) & (c_area["clase"] == DEF)]["hectareas"].sum() \
            if pid in per_c else None
        tot_jur = defo_reg.get(pid)
        if dr is None and dc is None:
            continue
        etnica = (dr or 0.0) + (dc or 0.0)
        fraccion.append({
            "periodo": pid, "ano_inicio": ini, "ano_fin": fin,
            "defo_resguardos_ha": None if dr is None else round(dr, 1),
            "defo_consejos_ha": None if dc is None else round(dc, 1),
            "defo_etnica_ha": round(etnica, 1),
            "defo_jurisdiccion_ha": None if tot_jur is None else round(tot_jur, 1),
            "pct_etnica": None if not tot_jur else round(100 * etnica / tot_jur, 1),
            "cobertura": "completa" if (dr is not None and dc is not None) else "parcial",
        })

    # tendencia con periodos de cobertura completa
    comp = [f for f in fraccion if f["cobertura"] == "completa" and f["pct_etnica"]]
    primeros = [f["pct_etnica"] for f in comp if f["ano_fin"] <= 2010]
    ultimos = [f["pct_etnica"] for f in comp if f["ano_inicio"] >= 2019]
    tendencia = {
        "pct_promedio_2002_2010": round(float(np.mean(primeros)), 1) if primeros else None,
        "pct_promedio_2019_2023": round(float(np.mean(ultimos)), 1) if ultimos else None,
        "periodos_usados": [f["periodo"] for f in comp],
    }

    def top(df, keys, clase, n=15):
        d = df[df["clase"] == clase]
        g = (d.groupby(keys)["hectareas"].sum().sort_values(ascending=False).head(n))
        out = []
        for k, v in g.items():
            row = dict(zip(keys, k if isinstance(k, tuple) else (k,)))
            row["hectareas_total"] = round(float(v), 1)
            out.append(row)
        return out

    # área del territorio (2022-2023, geometría) para intensidad
    area22_r = (r_area[r_area["periodo"] == "2022-2023"]
                .groupby("resguardo")["hectareas"].sum().to_dict())
    area22_c = (c_area[c_area["periodo"] == "2022-2023"]
                .groupby("consejo")["hectareas"].sum().to_dict())

    top_res = top(r_area, ["resguardo", "pueblo"], DEF)
    for t in top_res:
        a = area22_r.get(t["resguardo"])
        t["area_territorio_ha_2022_2023"] = round(a, 1) if a else None
        t["pct_del_territorio"] = round(100 * t["hectareas_total"] / a, 2) if a else None
    top_con = top(c_area, ["consejo"], DEF)
    for t in top_con:
        a = area22_c.get(t["consejo"])
        t["area_territorio_ha_2022_2023"] = round(a, 1) if a else None
        t["pct_del_territorio"] = round(100 * t["hectareas_total"] / a, 2) if a else None

    pueblos = (r_area[r_area["clase"] == DEF]
               .groupby("pueblo")["hectareas"].sum().sort_values(ascending=False))
    pueblos_json = [{"pueblo": k, "defo_total_ha": round(float(v), 1)}
                    for k, v in pueblos.items()]

    resumen = {
        "titulo": "Territorios étnicos y dinámica del bosque — CORPOURABA 2000-2024",
        "generado_por": "etl/analisis/territorios_etnicos.py",
        "universo": {
            "resguardos_distintos": int(res_out["resguardo"].nunique()),
            "pueblos": sorted(res_out["pueblo"].dropna().unique().tolist()),
            "consejos_distintos": int(con_out["consejo"].nunique()),
        },
        "cobertura_fuentes": {
            "resguardos": {p: (res_out[res_out['periodo'] == p]['fuente'].iloc[0]
                               + "/" + res_out[res_out['periodo'] == p]['calidad_fuente'].iloc[0])
                           if p in set(res_out['periodo']) else "ausente"
                           for p, *_ in PERIODOS},
            "consejos": {p: (con_out[con_out['periodo'] == p]['fuente'].iloc[0]
                             + "/" + con_out[con_out['periodo'] == p]['calidad_fuente'].iloc[0])
                         if p in set(con_out['periodo']) else "ausente"
                         for p, *_ in PERIODOS},
        },
        "totales": {
            "defo_resguardos_ha_suma_periodos_con_area": round(
                float(r_area[r_area["clase"] == DEF]["hectareas"].sum()), 1),
            "defo_consejos_ha_suma_periodos_con_area": round(
                float(c_area[c_area["clase"] == DEF]["hectareas"].sum()), 1),
            "regen_resguardos_ha": round(
                float(r_area[r_area["clase"] == REG]["hectareas"].sum()), 1),
            "regen_consejos_ha": round(
                float(c_area[c_area["clase"] == REG]["hectareas"].sum()), 1),
        },
        "fraccion_etnica_por_periodo": fraccion,
        "tendencia_fraccion_etnica": tendencia,
        "top_resguardos_deforestacion": top_res,
        "deforestacion_por_pueblo": pueblos_json,
        "top_consejos_deforestacion": top_con,
        "top_regeneracion_resguardos": top(r_area, ["resguardo", "pueblo"], REG, 10),
        "top_regeneracion_consejos": top(c_area, ["consejo"], REG, 10),
        "qa_solape_resguardos_consejos": qa_solape(),
        "advertencias": [
            "2010-2012, 2012-2013 y 2013-2014 sin ninguna fuente étnica; "
            "2018-2019 no existe como carpeta en el paquete crudo.",
            "Resguardos 2000-2002: Excel sin columna de área → solo conteo de polígonos.",
            "Resguardos 2014-2015 y 2023-2024: sin datos (solo metadatos .qmd/.shx huérfanos).",
            "Consejos 2000-2002: sin datos. Consejos 2014-2015 (Excel) y 2015-2016 "
            "(dbf huérfano) sin columna de área → solo conteo de polígonos.",
            "2023-2024 usa un gridcode distinto al estándar (4=No Bosque Estable); "
            "la clase se tomó del texto Tipo_Cober, no del gridcode.",
            "La fracción étnica compara contra serie_regional.csv (incluye periodos "
            "estimados); en periodos de cobertura 'parcial' falta una de las dos capas.",
            "Suma de periodos multi-anuales: los periodos 2000-2010 son bienales; "
            "usar hectareas_anuales para comparar intensidades.",
        ],
        "log": LOG,
    }
    (OUT / "territorios_etnicos_resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"JSON: territorios_etnicos_resumen.json → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
