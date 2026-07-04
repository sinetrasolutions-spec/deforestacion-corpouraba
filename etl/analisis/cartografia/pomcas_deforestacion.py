# -*- coding: utf-8 -*-
"""
Deforestación por POMCA — CORPOURABA
====================================
Cruza los LÍMITES de los POMCAS (Planes de Ordenación y Manejo de Cuencas,
`ZONIFICACION AMBIENTAL POMCAS\\LIMITES_POMCAS.shp`, 1,6 MB — solo los bordes,
no las zonificaciones pesadas) con los polígonos de deforestación mapeados
(hotspots ≥1 ha, 12 periodos) para obtener la deforestación por POMCA y periodo.

Salidas:
  data/processed/analisis/cartografia/pomcas_serie.csv     POMCA × periodo × ha
  data/processed/analisis/cartografia/pomcas_resumen.json  ranking y cobertura
  data/processed/capas/pomcas.geojson                      capa web (WGS84)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import warnings

warnings.filterwarnings("ignore")
import geopandas as gpd
import pandas as pd

PROJ = Path(r"E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion")
CARTO = Path(r"C:\Users\Desktop\Documents\Documentos\PROGRAMAS\CONSULTAS CARTOGRÁFICAS\CARTOGRAFIA")
LIMITES = CARTO / "ZONIFICACION AMBIENTAL POMCAS" / "LIMITES_POMCAS.shp"
HOT = PROJ / "data" / "processed" / "hotspots"
OUT = PROJ / "data" / "processed" / "analisis" / "cartografia"
CAPAS = PROJ / "data" / "processed" / "capas"
METRICO = "EPSG:3115"

PERIODOS_ANO = {
    "2002-2004": 2002, "2004-2006": 2004, "2006-2008": 2006, "2008-2010": 2008,
    "2012-2013": 2012, "2013-2014": 2013, "2016-2017": 2016, "2017-2018": 2017,
    "2019-2020": 2019, "2020-2021": 2020, "2021-2022": 2021, "2022-2023": 2022,
}


def cargar_pomcas() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(LIMITES, engine="pyogrio")
    print("Columnas LIMITES_POMCAS:", list(gdf.columns))
    # detectar columna de nombre
    cand = [c for c in gdf.columns if c.lower() in
            ("nombre", "nom_pomca", "pomca", "nom_cuenca", "nombre_pom", "nombrepom", "n_pomca")]
    if not cand:
        cand = [c for c in gdf.columns if gdf[c].dtype == object and c.lower() != "geometry"]
    name_col = cand[0]
    print("Columna de nombre POMCA:", name_col)
    if gdf.crs is None:
        gdf = gdf.set_crs(METRICO)
    gdf = gdf.to_crs(METRICO)
    gdf["geometry"] = gdf.geometry.buffer(0)
    gdf["_pomca"] = gdf[name_col].astype(str).str.strip()
    gdf = gdf.dissolve(by="_pomca", as_index=False)[["_pomca", "geometry"]]
    print(f"POMCAS: {len(gdf)} -> {gdf['_pomca'].tolist()}")
    return gdf


def main() -> int:
    pomcas = cargar_pomcas()
    pomcas_sindex = pomcas.sindex
    filas = []
    defo_total = {p: 0.0 for p in pomcas["_pomca"]}
    npol_total = {p: 0 for p in pomcas["_pomca"]}

    for pid, ano in PERIODOS_ANO.items():
        ruta = HOT / f"{pid}.geojson"
        if not ruta.exists():
            continue
        hs = gpd.read_file(ruta, engine="pyogrio").to_crs(METRICO)
        hs["geometry"] = hs.geometry.buffer(0)
        # intersección espacial parche × POMCA (índice espacial → barato)
        inter = gpd.overlay(hs[["geometry"]], pomcas, how="intersection", keep_geom_type=True)
        if inter.empty:
            continue
        inter["ha"] = inter.geometry.area / 10_000.0
        agg = inter.groupby("_pomca").agg(ha=("ha", "sum"), n=("ha", "size")).reset_index()
        for _, r in agg.iterrows():
            filas.append({
                "pomca": r["_pomca"], "periodo": pid, "ano_inicio": ano,
                "deforestacion_ha": round(float(r["ha"]), 2), "n_poligonos": int(r["n"]),
            })
            defo_total[r["_pomca"]] += float(r["ha"])
            npol_total[r["_pomca"]] += int(r["n"])
        print(f"  {pid}: {agg['ha'].sum():,.0f} ha en POMCAS")

    serie = pd.DataFrame(filas).sort_values(["pomca", "ano_inicio"])
    serie.to_csv(OUT / "pomcas_serie.csv", index=False, encoding="utf-8-sig")

    # área de cada POMCA (para %)
    pomcas_area = pomcas.copy()
    pomcas_area["area_ha"] = pomcas_area.geometry.area / 10_000.0
    area_por = dict(zip(pomcas_area["_pomca"], pomcas_area["area_ha"]))

    ranking = sorted(
        ({"pomca": p, "deforestacion_ha": round(defo_total[p], 1),
          "n_poligonos": npol_total[p], "area_ha": round(area_por.get(p, 0), 1),
          "pct_del_pomca": round(100 * defo_total[p] / area_por[p], 3) if area_por.get(p) else None}
         for p in defo_total),
        key=lambda x: x["deforestacion_ha"], reverse=True,
    )
    resumen = {
        "tema": "Deforestación mapeada por POMCA (LIMITES_POMCAS × hotspots ≥1 ha)",
        "n_pomcas": len(pomcas),
        "periodos": list(PERIODOS_ANO),
        "deforestacion_total_ha": round(sum(defo_total.values()), 1),
        "nota": ("Deforestación mapeada (hotspots ≥1 ha, 12 de 18 periodos). Un parche "
                 "puede caer en más de un POMCA solo en las fronteras; la intersección "
                 "geométrica reparte el área sin duplicar."),
        "ranking": ranking,
    }
    (OUT / "pomcas_resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")

    # capa web
    web = pomcas.to_crs(METRICO).copy()
    web["deforestacion_ha_total"] = web["_pomca"].map(lambda p: round(defo_total.get(p, 0), 1))
    web["area_ha"] = web["_pomca"].map(lambda p: round(area_por.get(p, 0), 1))
    web = web.rename(columns={"_pomca": "nombre"})
    web["geometry"] = web.geometry.simplify(60, preserve_topology=True)
    web = web.to_crs("EPSG:4326")[["nombre", "area_ha", "deforestacion_ha_total", "geometry"]]
    web.to_file(CAPAS / "pomcas.geojson", driver="GeoJSON", COORDINATE_PRECISION=5)

    print(f"\nOK -> pomcas_serie.csv ({len(serie)} filas), pomcas_resumen.json, pomcas.geojson")
    print(f"Total deforestación mapeada en POMCAS: {sum(defo_total.values()):,.0f} ha")
    print("Top 3:", [(r['pomca'], r['deforestacion_ha']) for r in ranking[:3]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
