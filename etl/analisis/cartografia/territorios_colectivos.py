# -*- coding: utf-8 -*-
"""
Análisis cartografía oficial: TERRITORIOS COLECTIVOS × deforestación
====================================================================

Cruza los límites OFICIALES de territorios colectivos de la cartografía de
CORPOURABA (TERRITORIOS COLECTIVOS/Resguardos_Indigenas.shp y
Comunidades_Negras.shp, EPSG:3116) con los hotspots de deforestación ya
consolidados del Observatorio (12 periodos, polígonos >=1 ha, WGS84).

Método:
  * Todo se reproyecta a EPSG:3115 (MAGNA Colombia West) para áreas (ha = m²/1e4).
  * Geometrías inválidas -> buffer(0).
  * Cruce con gpd.overlay(intersection) por territorio × periodo.
  * Totales por capa calculados también sobre la UNIÓN disuelta (evita doble
    conteo por solapes internos y entre capas).
  * Comparación con el análisis previo derivado del paquete de monitoreo
    (analisis/resguardos_serie.csv, consejos_serie.csv) si existe, y con las
    capas web derivadas (capas/resguardos.geojson, consejos.geojson).

Salidas:
  data/processed/analisis/cartografia/territorios_oficiales.csv
  data/processed/analisis/cartografia/territorios_oficiales_resumen.json
  data/processed/capas/resguardos_oficial.geojson          (WGS84, <500 KB)
  data/processed/capas/comunidades_negras_oficial.geojson  (WGS84, <500 KB)

Uso:  python etl/analisis/cartografia/territorios_colectivos.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # …/etl
import run_etl  # helpers validados: read_shp, _ascii, PERIODOS

import geopandas as gpd
import numpy as np
import pandas as pd
from pyogrio import write_dataframe
from shapely import union_all

CART = Path(r"C:\Users\Desktop\Documents\Documentos\PROGRAMAS"
            r"\CONSULTAS CARTOGRÁFICAS\CARTOGRAFIA\TERRITORIOS COLECTIVOS")
BASE = Path(__file__).resolve().parents[3] / "data" / "processed"
OUT_DIR = BASE / "analisis" / "cartografia"
CAPAS = BASE / "capas"
METRIC = "EPSG:3115"
WGS84 = "EPSG:4326"

ANOS = {p: (i, f) for p, i, f in run_etl.PERIODOS}

# normalización de pueblo (alineada con etl/analisis/territorios_etnicos.py)
PUEBLO_NORM = {
    "EMBERA": "Embera",
    "EMBERA KATIO": "Embera Katío",
    "EMBERA CHAMI": "Embera Chamí",
    "EMBERA CHAMI / ZENU": "Embera Chamí-Zenú",
    "ZENU": "Senú/Zenú",
    "SENU": "Senú/Zenú",
    "CUNA": "Tule/Guna (Cuna)",
    "TULE": "Tule/Guna (Cuna)",
}

LOG: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    LOG.append(msg)


def valid(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Repara geometrías inválidas con buffer(0)."""
    bad = ~gdf.geometry.is_valid
    if bad.any():
        gdf = gdf.copy()
        gdf.loc[bad, "geometry"] = gdf.loc[bad, "geometry"].buffer(0)
        log(f"  [QA] {int(bad.sum())} geometría(s) inválida(s) reparada(s) con buffer(0)")
    return gdf


def clean(s):
    return " ".join(str(s).split()) if pd.notna(s) else None


# ---------------------------------------------------------------------------
# 1. Capas oficiales
# ---------------------------------------------------------------------------

def cargar_oficiales():
    info = {}

    shp_r = CART / "Resguardos_Indigenas.shp"
    res = run_etl.read_shp(shp_r)
    info["resguardos_crs_original"] = str(res.crs.to_epsg() or res.crs)
    res = valid(res.to_crs(METRIC))
    res = valid(res)  # revalida tras reproyección
    r = gpd.GeoDataFrame({
        "id_territorio": res["ID_RESGUAR"].map(clean),
        "nombre": res["NOMBRE_RES"].map(clean),
        "pueblo": res["PUEBLO"].map(
            lambda v: PUEBLO_NORM.get(run_etl._ascii(v), clean(v)) if pd.notna(v) else "Sin dato"),
        "municipio_oficial": res["MUNICIPIO"].map(clean),
        "ano_acto": pd.to_datetime(res["FECHA_ACTO"], errors="coerce").dt.year,
        "area_acto_ha": pd.to_numeric(res["AREA_ACTO_"], errors="coerce"),
    }, geometry=res.geometry, crs=METRIC)
    r["tipo"] = "resguardo"

    shp_c = CART / "Comunidades_Negras.shp"
    cn = run_etl.read_shp(shp_c)
    info["comunidades_crs_original"] = str(cn.crs.to_epsg() or cn.crs)
    cn = valid(cn.to_crs(METRIC))
    c = gpd.GeoDataFrame({
        "id_territorio": cn["ID_CONSEJO"].map(clean),
        "nombre": cn["NOMBRE_COM"].map(clean),
        "pueblo": None,
        "municipio_oficial": cn["MUNICIPIO"].map(clean),
        "ano_acto": pd.to_numeric(cn["ANO"], errors="coerce"),
        "area_acto_ha": pd.to_numeric(
            cn["AREA_TITUL"].astype(str).str.replace(".", "", regex=False)
                            .str.replace(",", ".", regex=False), errors="coerce"),
        "resolucion": cn["RESOLUCION"].map(clean),
    }, geometry=cn.geometry, crs=METRIC)
    c["tipo"] = "consejo_comunitario"

    for g, lbl in ((r, "resguardos"), (c, "comunidades negras")):
        g["area_oficial_ha"] = (g.geometry.area / 1e4).round(1)
        log(f"  {lbl}: {len(g)} territorios oficiales, "
            f"{g['area_oficial_ha'].sum():,.0f} ha (CRS original EPSG:"
            f"{info[('resguardos' if lbl == 'resguardos' else 'comunidades') + '_crs_original']})")
    return r, c, info


# ---------------------------------------------------------------------------
# 2. Jurisdicción y municipios (espacial, no el atributo oficial)
# ---------------------------------------------------------------------------

def contexto_jurisdiccion(gdf: gpd.GeoDataFrame, mpios: gpd.GeoDataFrame,
                          jur_union) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    inter = gdf.geometry.intersection(jur_union)
    gdf["ha_en_jurisdiccion"] = (inter.area / 1e4).round(1)
    gdf["pct_en_jurisdiccion"] = (100 * inter.area / gdf.geometry.area).round(1)
    ov = gpd.overlay(gdf[["id_territorio", "geometry"]],
                     mpios[["nombre", "geometry"]].rename(columns={"nombre": "mpio"}),
                     how="intersection", keep_geom_type=True)
    ov["ha"] = ov.geometry.area / 1e4
    ov = ov[ov["ha"] >= 1.0]
    mm = (ov.sort_values("ha", ascending=False)
            .groupby("id_territorio")["mpio"]
            .agg(lambda s: ", ".join(dict.fromkeys(s))))
    gdf["municipios"] = gdf["id_territorio"].map(mm).fillna("Fuera de la jurisdicción")
    return gdf


# ---------------------------------------------------------------------------
# 3. Cruce con hotspots
# ---------------------------------------------------------------------------

def cruzar_hotspots(res: gpd.GeoDataFrame, con: gpd.GeoDataFrame):
    periodos = sorted(p.stem for p in (BASE / "hotspots").glob("*.geojson"))
    log(f"  hotspots: {len(periodos)} periodos → {', '.join(periodos)}")

    u_res = union_all(res.geometry.values)
    u_con = union_all(con.geometry.values)
    u_col = union_all([u_res, u_con])
    solape_capas_ha = u_res.intersection(u_con).area / 1e4

    filas, por_periodo, qa_ha = [], [], []
    for pid in periodos:
        hs = gpd.read_file(BASE / "hotspots" / f"{pid}.geojson").to_crs(METRIC)
        hs = valid(hs)
        hs["_hsid"] = range(len(hs))
        geom_ha = hs.geometry.area.sum() / 1e4
        qa_ha.append(abs(geom_ha - hs["ha"].sum()) / max(geom_ha, 1e-9) * 100)

        tot = {"periodo": pid, "total_mapeado_ha": round(geom_ha, 1)}
        for lbl, u in (("resguardos", u_res), ("consejos", u_con), ("colectivos", u_col)):
            tot[f"defo_{lbl}_ha"] = round(
                hs.geometry.intersection(u).area.sum() / 1e4, 1)
        por_periodo.append(tot)

        for gdf in (res, con):
            ov = gpd.overlay(
                hs[["_hsid", "geometry"]],
                gdf[["tipo", "id_territorio", "geometry"]],
                how="intersection", keep_geom_type=True)
            if ov.empty:
                continue
            ov["defo_ha"] = ov.geometry.area / 1e4
            g = (ov.groupby(["tipo", "id_territorio"])
                   .agg(deforestacion_ha=("defo_ha", "sum"),
                        n_poligonos=("_hsid", "nunique")).reset_index())
            g["periodo"] = pid
            filas.append(g)
        log(f"    {pid}: mapeado {tot['total_mapeado_ha']:>8,.1f} ha | "
            f"colectivos {tot['defo_colectivos_ha']:>7,.1f} ha "
            f"({100 * tot['defo_colectivos_ha'] / max(tot['total_mapeado_ha'], 1e-9):.1f}%)")

    inter_df = pd.concat(filas, ignore_index=True)
    log(f"  [QA] divergencia máx. área geométrica vs propiedad 'ha' de hotspots: "
        f"{max(qa_ha):.2f}%")
    return inter_df, pd.DataFrame(por_periodo), periodos, round(solape_capas_ha, 1), u_col


# ---------------------------------------------------------------------------
# 4. Comparaciones (capa derivada y análisis previo)
# ---------------------------------------------------------------------------

def comparar_derivadas(periodos: list[str]) -> dict:
    out = {}
    for capa, lbl in (("resguardos", "resguardos"), ("consejos", "consejos")):
        f = CAPAS / f"{capa}.geojson"
        if not f.exists():
            out[lbl] = {"disponible": False}
            continue
        d = valid(gpd.read_file(f).to_crs(METRIC))
        u = union_all(d.geometry.values)
        defo = 0.0
        for pid in periodos:
            hs = valid(gpd.read_file(BASE / "hotspots" / f"{pid}.geojson").to_crs(METRIC))
            defo += hs.geometry.intersection(u).area.sum() / 1e4
        out[lbl] = {"disponible": True, "n_territorios": int(len(d)),
                    "area_ha": round(float(d.geometry.area.sum() / 1e4), 1),
                    "defo_mapeada_ha": round(defo, 1)}
    return out


def comparar_series_previas(periodos: list[str], defo_ofi: pd.DataFrame) -> dict:
    """Compara con analisis/resguardos_serie.csv y consejos_serie.csv (si existen)."""
    out = {}
    for archivo, col, lbl in (("resguardos_serie.csv", "defo_resguardos_ha", "resguardos"),
                              ("consejos_serie.csv", "defo_consejos_ha", "consejos")):
        f = BASE / "analisis" / archivo
        if not f.exists():
            out[lbl] = {"disponible": False,
                        "nota": f"{archivo} no existe al momento de este análisis"}
            continue
        prev = pd.read_csv(f)
        prev = prev[(prev["clase"] == "Deforestación")
                    & (prev["calidad_fuente"] != "solo_conteo")]
        pp = prev.groupby("periodo")["hectareas"].sum()
        comunes = [p for p in periodos if p in pp.index]
        mio = defo_ofi.set_index("periodo")[col]
        comp = [{"periodo": p, "previo_monitoreo_ha": round(float(pp[p]), 1),
                 "oficial_hotspots_ha": round(float(mio.get(p, 0)), 1)}
                for p in comunes]
        s_prev = sum(x["previo_monitoreo_ha"] for x in comp)
        s_mio = sum(x["oficial_hotspots_ha"] for x in comp)
        out[lbl] = {
            "disponible": True, "periodos_comunes": comunes,
            "suma_previo_monitoreo_ha": round(s_prev, 1),
            "suma_oficial_hotspots_ha": round(s_mio, 1),
            "razon_oficial_vs_previo": round(s_mio / s_prev, 3) if s_prev else None,
            "detalle_por_periodo": comp,
        }
    return out


# ---------------------------------------------------------------------------
# 5. Capas web
# ---------------------------------------------------------------------------

def escribir_capa(gdf: gpd.GeoDataFrame, nombre: str, props: list[str]) -> str:
    out = CAPAS / f"{nombre}.geojson"
    tol, size_kb = 60.0, None
    for _ in range(5):
        g = gdf[props + ["geometry"]].copy()
        g["geometry"] = g.geometry.simplify(tol, preserve_topology=True)
        g = valid(g).to_crs(WGS84)
        write_dataframe(g, out, driver="GeoJSON", COORDINATE_PRECISION=5)
        size_kb = out.stat().st_size / 1024
        if size_kb < 500:
            break
        tol *= 1.8
    log(f"  capa web {out.name}: {len(gdf)} territorios, {size_kb:.0f} KB "
        f"(tolerancia {tol:.0f} m)")
    return f"{out.name} ({size_kb:.0f} KB)"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log("=== Territorios colectivos oficiales × deforestación mapeada ===")

    log("[1/5] capas oficiales")
    res, con, info = cargar_oficiales()

    log("[2/5] contexto jurisdiccional")
    mpios = valid(gpd.read_file(BASE / "municipios.geojson").to_crs(METRIC))
    jur = union_all(mpios.geometry.values)
    jur_ha = jur.area / 1e4
    res = contexto_jurisdiccion(res, mpios, jur)
    con = contexto_jurisdiccion(con, mpios, jur)
    for g, lbl in ((res, "resguardos"), (con, "consejos")):
        fuera = g[g["pct_en_jurisdiccion"] < 50]
        log(f"  {lbl}: {len(fuera)} de {len(g)} territorios con <50% del área "
            f"dentro de la jurisdicción CORPOURABA")

    log("[3/5] cruce con hotspots (12 periodos)")
    inter, por_periodo, periodos, solape_capas_ha, u_col = cruzar_hotspots(res, con)

    # ---- serie larga territorio × periodo (incluye ceros) ----
    attrs = pd.concat([
        res[["tipo", "id_territorio", "nombre", "pueblo", "municipios",
             "area_oficial_ha", "pct_en_jurisdiccion"]],
        con[["tipo", "id_territorio", "nombre", "pueblo", "municipios",
             "area_oficial_ha", "pct_en_jurisdiccion"]],
    ], ignore_index=True)
    full = (attrs.merge(pd.DataFrame({"periodo": periodos}), how="cross")
                 .merge(inter, on=["tipo", "id_territorio", "periodo"], how="left"))
    full["deforestacion_ha"] = full["deforestacion_ha"].fillna(0).round(2)
    full["n_poligonos"] = full["n_poligonos"].fillna(0).astype(int)
    full["ano_inicio"] = full["periodo"].map(lambda p: ANOS[p][0])
    full["ano_fin"] = full["periodo"].map(lambda p: ANOS[p][1])
    full["pct_del_territorio"] = (100 * full["deforestacion_ha"]
                                  / full["area_oficial_ha"]).round(3)
    cols = ["tipo", "id_territorio", "nombre", "pueblo", "periodo", "ano_inicio",
            "ano_fin", "deforestacion_ha", "n_poligonos", "pct_del_territorio",
            "area_oficial_ha", "pct_en_jurisdiccion", "municipios"]
    full = full[cols].sort_values(["tipo", "nombre", "periodo"])
    csv_path = OUT_DIR / "territorios_oficiales.csv"
    full.to_csv(csv_path, index=False, encoding="utf-8-sig")
    log(f"  CSV: {csv_path.name} ({len(full)} filas)")

    # ---- totales por territorio ----
    tot_terr = (full.groupby(["tipo", "id_territorio", "nombre"], sort=False)
                    .agg(defo=("deforestacion_ha", "sum")).reset_index())
    map_tot = tot_terr.set_index("id_territorio")["defo"].round(1)
    res["deforestacion_ha_total"] = res["id_territorio"].map(map_tot).fillna(0)
    con["deforestacion_ha_total"] = con["id_territorio"].map(map_tot).fillna(0)
    ult = periodos[-1]
    map_ult = (full[full["periodo"] == ult]
               .set_index("id_territorio")["deforestacion_ha"].round(1))
    res["deforestacion_ha_ultimo_periodo"] = res["id_territorio"].map(map_ult).fillna(0)
    con["deforestacion_ha_ultimo_periodo"] = con["id_territorio"].map(map_ult).fillna(0)

    log("[4/5] comparaciones y síntesis")
    total_mapeado = float(por_periodo["total_mapeado_ha"].sum())
    d_res = float(por_periodo["defo_resguardos_ha"].sum())
    d_con = float(por_periodo["defo_consejos_ha"].sum())
    d_col = float(por_periodo["defo_colectivos_ha"].sum())
    por_periodo["pct_colectivos"] = (100 * por_periodo["defo_colectivos_ha"]
                                     / por_periodo["total_mapeado_ha"]).round(1)
    por_periodo["ano_inicio"] = por_periodo["periodo"].map(lambda p: ANOS[p][0])
    por_periodo["ano_fin"] = por_periodo["periodo"].map(lambda p: ANOS[p][1])

    tempranos = por_periodo[por_periodo["ano_fin"] <= 2010]["pct_colectivos"]
    tardios = por_periodo[por_periodo["ano_inicio"] >= 2019]["pct_colectivos"]
    tendencia = {
        "pct_promedio_2002_2010": round(float(tempranos.mean()), 1),
        "pct_promedio_2019_2023": round(float(tardios.mean()), 1),
        "pct_por_periodo": por_periodo[["periodo", "pct_colectivos"]]
            .set_index("periodo")["pct_colectivos"].to_dict(),
    }

    # densidad dentro/fuera (solo dentro de jurisdicción)
    col_in_jur_ha = u_col.intersection(jur).area / 1e4
    dens_in = d_col / col_in_jur_ha * 100
    dens_out = (total_mapeado - d_col) / (jur_ha - col_in_jur_ha) * 100

    def top(gdf, n=10):
        d = gdf.sort_values("deforestacion_ha_total", ascending=False).head(n)
        return [{k: (None if pd.isna(v) else v) for k, v in r.items()}
                for r in d[["nombre", "pueblo", "municipios", "area_oficial_ha",
                            "deforestacion_ha_total", "pct_en_jurisdiccion"]]
                .assign(pct_del_territorio=lambda x: (100 * x["deforestacion_ha_total"]
                                                      / x["area_oficial_ha"]).round(2))
                .to_dict("records")]

    pueblos = (full[full["tipo"] == "resguardo"]
               .groupby("pueblo")["deforestacion_ha"].sum().round(1)
               .sort_values(ascending=False))

    resumen = {
        "titulo": "Territorios colectivos oficiales y deforestación mapeada — CORPOURABA 2002-2023",
        "generado_por": "etl/analisis/cartografia/territorios_colectivos.py",
        "fuentes": {
            "resguardos": str(CART / "Resguardos_Indigenas.shp"),
            "comunidades_negras": str(CART / "Comunidades_Negras.shp"),
            "crs_original": info,
            "crs_analisis": METRIC,
            "hotspots": "data/processed/hotspots/*.geojson (12 de 18 periodos, "
                        "poligonos >=1 ha; ~87% de la deforestación medida 2000-2024)",
        },
        "universo": {
            "resguardos": int(len(res)),
            "area_resguardos_ha": round(float(res["area_oficial_ha"].sum()), 1),
            "pueblos": sorted(res["pueblo"].dropna().unique().tolist()),
            "consejos_comunitarios": int(len(con)),
            "area_consejos_ha": round(float(con["area_oficial_ha"].sum()), 1),
            "solape_resguardos_consejos_ha": solape_capas_ha,
            "area_colectivos_en_jurisdiccion_ha": round(float(col_in_jur_ha), 1),
            "pct_jurisdiccion_bajo_territorio_colectivo": round(100 * col_in_jur_ha / jur_ha, 1),
            "resguardos_mayormente_fuera_jurisdiccion":
                res.loc[res["pct_en_jurisdiccion"] < 50, "nombre"].tolist(),
            "consejos_mayormente_fuera_jurisdiccion":
                con.loc[con["pct_en_jurisdiccion"] < 50, "nombre"].tolist(),
        },
        "totales_2002_2023_mapeado": {
            "total_mapeado_ha": round(total_mapeado, 1),
            "defo_en_resguardos_ha": round(d_res, 1),
            "defo_en_consejos_ha": round(d_con, 1),
            "defo_en_colectivos_union_ha": round(d_col, 1),
            "doble_conteo_evitado_ha": round(d_res + d_con - d_col, 1),
            "pct_mapeado_en_colectivos": round(100 * d_col / total_mapeado, 1),
            "pct_mapeado_en_resguardos": round(100 * d_res / total_mapeado, 1),
            "pct_mapeado_en_consejos": round(100 * d_con / total_mapeado, 1),
            "densidad_defo_dentro_colectivos_pct_area": round(dens_in, 2),
            "densidad_defo_fuera_colectivos_pct_area": round(dens_out, 2),
        },
        "serie_por_periodo": por_periodo[
            ["periodo", "ano_inicio", "ano_fin", "total_mapeado_ha",
             "defo_resguardos_ha", "defo_consejos_ha", "defo_colectivos_ha",
             "pct_colectivos"]].to_dict("records"),
        "tendencia_pct_colectivos": tendencia,
        "top_resguardos": top(res),
        "top_consejos": top(con, 12),
        "deforestacion_por_pueblo": [
            {"pueblo": k, "defo_mapeada_ha": float(v)} for k, v in pueblos.items()],
        "comparacion_capas_derivadas": comparar_derivadas(periodos),
        "comparacion_series_previas": comparar_series_previas(periodos, por_periodo),
        "advertencias": [
            "Los hotspots cubren 12 de 18 periodos (~87% de la deforestación medida); "
            "todas las cifras son 'de la deforestación mapeada', no del total 2000-2024.",
            "Los hotspots solo incluyen polígonos >=1 ha: la deforestación difusa "
            "(<1 ha) dentro de los territorios no está contada.",
            "Las capas oficiales incluyen territorios parcial o totalmente fuera de la "
            "jurisdicción CORPOURABA (Chocó, Bajo Cauca); su deforestación solo se "
            "contabiliza dentro de la jurisdicción monitoreada.",
            "Capa oficial de resguardos: 1 geometría inválida reparada con buffer(0).",
            "Áreas calculadas en EPSG:3115 sobre geometría oficial reproyectada desde "
            "EPSG:3116; pueden diferir del área del acto administrativo (area_acto_ha).",
        ],
        "log": LOG,
    }

    log("[5/5] capas web")
    res_out = res.rename(columns={"id_territorio": "id_resguardo"})
    salida_r = escribir_capa(
        res_out, "resguardos_oficial",
        ["nombre", "pueblo", "id_resguardo", "municipios", "ano_acto",
         "area_oficial_ha", "pct_en_jurisdiccion",
         "deforestacion_ha_total", "deforestacion_ha_ultimo_periodo"])
    con_out = con.rename(columns={"id_territorio": "id_consejo"})
    salida_c = escribir_capa(
        con_out, "comunidades_negras_oficial",
        ["nombre", "id_consejo", "municipios", "ano_acto", "resolucion",
         "area_oficial_ha", "pct_en_jurisdiccion",
         "deforestacion_ha_total", "deforestacion_ha_ultimo_periodo"])
    resumen["capas_web"] = [salida_r, salida_c]

    (OUT_DIR / "territorios_oficiales_resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1, default=float),
        encoding="utf-8")
    log(f"JSON: territorios_oficiales_resumen.json → {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
