# -*- coding: utf-8 -*-
"""
DINÁMICA DE BOSQUE — Observatorio Deforestación CORPOURABA (2000-2024)
=====================================================================

Construye `dinamica_bosque.csv` (municipio × periodo) re-leyendo las MISMAS
fuentes municipales del ETL principal (run_etl.SHP_MPIOS / EXCEL_MPIOS /
RASTER_MPIOS) para obtener las 5 clases por municipio, y calcula:

  bosque_estable_ha, no_bosque_ha, regeneracion_ha, sin_informacion_ha,
  deforestacion_ha, pct_cobertura_bosque, tasa_perdida_relativa,
  cambio_neto_ha.

Fuentes de clases completas (Bosque/No Bosque/Regen/Sin Info/Defo):
  - shapefile municipal (área desde geometría)  -> real
  - excel municipal (columna AREA_HA)            -> real
  - raster zonal stats (2012-2013)               -> real
Periodos solo-deforestación (sin dato de bosque en el paquete):
  - 2010-2012, 2018-2019, 2023-2024 (estimados) y 2015-2016 (cuencas
    calibrado, parcial) -> se toma la deforestación de serie_municipal.csv
    y las columnas de bosque quedan NaN, con flag de calidad.
"""
from __future__ import annotations
import sys, json
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\etl")
import run_etl  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAW = run_etl.DEFAULT_RAW
OUT = Path(r"E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\analisis")
OUT.mkdir(parents=True, exist_ok=True)
SERIE_MUN = Path(r"E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\serie_municipal.csv")

PERIODOS = run_etl.PERIODOS
NYEARS = {p: max(1, fin - ini) for p, ini, fin in PERIODOS}
ORDEN = [p[0] for p in PERIODOS]
CLASES_PRETTY = run_etl.CLASES  # ASCII key -> nombre bonito

# clases -> nombre de columna wide
COL = {
    "Bosque Estable": "bosque_estable_ha",
    "No Bosque Estable": "no_bosque_ha",
    "Regeneración": "regeneracion_ha",
    "Sin Información": "sin_informacion_ha",
    "Deforestación": "deforestacion_ha",
}


def leer_fuentes_reales() -> pd.DataFrame:
    """Re-lee las fuentes municipales con clases completas (shp/excel/raster)."""
    print("[1] Municipios (para zonal stats del raster)...")
    municipios = run_etl.build_municipios(RAW)
    frames = []
    for pid, ini, fin in PERIODOS:
        df = None
        fuente = None
        if pid in run_etl.SHP_MPIOS:
            src = next((RAW / p for p in run_etl.SHP_MPIOS[pid] if (RAW / p).exists()), None)
            if src is not None:
                df = run_etl.stats_from_shp(src, pid)
                fuente = "shapefile"
        elif pid in run_etl.EXCEL_MPIOS:
            xl = pd.ExcelFile(RAW / run_etl.EXCEL_MPIOS[pid])
            df = run_etl.stats_from_table(xl.parse(xl.sheet_names[0]), pid, "excel")
            fuente = "excel"
        elif pid in run_etl.RASTER_MPIOS:
            df = run_etl.stats_from_raster(RAW / run_etl.RASTER_MPIOS[pid], pid, municipios)
            fuente = "raster"
        if df is None or df.empty:
            continue
        df["fuente"] = fuente
        df["estimado"] = False
        frames.append(df[["municipio_key", "periodo", "clase", "hectareas", "fuente", "estimado"]])
        n = df["municipio_key"].nunique()
        print(f"    {pid}: {fuente} -> {n} municipios, {df['hectareas'].sum():,.0f} ha")
    real = pd.concat(frames, ignore_index=True)
    # clase ascii -> nombre bonito
    real["clase"] = real["clase"].map(CLASES_PRETTY)
    return real


def leer_estimados_defo() -> pd.DataFrame:
    """Toma deforestación de periodos sin bosque (estimados / cuencas) de serie_municipal."""
    sm = pd.read_csv(SERIE_MUN, encoding="utf-8-sig")
    # re-map municipio_key desde codigo_dane
    dane2key = {v[1]: k for k, v in run_etl.MUNICIPIOS.items()}
    sm["municipio_key"] = sm["codigo_dane"].astype(str).str.zfill(5).map(dane2key)
    periodos_sin_bosque = {"2010-2012", "2015-2016", "2018-2019", "2023-2024"}
    sub = sm[(sm["periodo"].isin(periodos_sin_bosque)) & (sm["clase"] == "Deforestación")].copy()
    out = sub[["municipio_key", "periodo", "clase", "hectareas", "fuente", "estimado"]].copy()
    return out


def construir_wide(long: pd.DataFrame) -> pd.DataFrame:
    """Long (municipio×periodo×clase) -> wide con columnas por clase + metadatos."""
    meta_p = {p: (ini, fin) for p, ini, fin in PERIODOS}
    # pivot
    wide = (long.pivot_table(index=["municipio_key", "periodo"], columns="clase",
                             values="hectareas", aggfunc="sum"))
    wide = wide.reset_index()
    # asegurar todas las columnas de clase
    for pretty, colname in COL.items():
        if pretty not in wide.columns:
            wide[pretty] = np.nan
    ren = {pretty: colname for pretty, colname in COL.items()}
    wide = wide.rename(columns=ren)
    for colname in COL.values():
        if colname not in wide.columns:
            wide[colname] = np.nan

    # fuente / estimado por (municipio, periodo)
    fe = (long.groupby(["municipio_key", "periodo"])
          .agg(fuente=("fuente", lambda s: s.mode().iat[0] if len(s.mode()) else s.iloc[0]),
               estimado=("estimado", "any")).reset_index())
    wide = wide.merge(fe, on=["municipio_key", "periodo"], how="left")

    # metadatos municipio
    wide["municipio"] = wide["municipio_key"].map(lambda k: run_etl.MUNICIPIOS[k][0])
    wide["codigo_dane"] = wide["municipio_key"].map(lambda k: run_etl.MUNICIPIOS[k][1])
    wide["subregion"] = wide["municipio_key"].map(lambda k: run_etl.MUNICIPIOS[k][2])
    wide["ano_inicio"] = wide["periodo"].map(lambda p: meta_p[p][0])
    wide["ano_fin"] = wide["periodo"].map(lambda p: meta_p[p][1])
    wide["n_anos"] = wide["periodo"].map(NYEARS)
    return wide


def calcular_metricas(wide: pd.DataFrame) -> pd.DataFrame:
    """pct_cobertura_bosque, tasa_perdida_relativa, cambio_neto_ha + flags."""
    b = wide["bosque_estable_ha"]
    nb = wide["no_bosque_ha"]
    rg = wide["regeneracion_ha"].fillna(0.0)
    si = wide["sin_informacion_ha"]
    de = wide["deforestacion_ha"]

    # área con información = bosque + no_bosque + defo + regen (todo menos Sin Info)
    area_info = b.fillna(0) + nb.fillna(0) + de.fillna(0) + rg
    # solo válido cuando hay dato de bosque
    tiene_bosque = wide["bosque_estable_ha"].notna()
    wide["area_con_informacion_ha"] = np.where(tiene_bosque, area_info, np.nan).round(2)
    wide["pct_cobertura_bosque"] = np.where(
        tiene_bosque & (area_info > 0), 100.0 * b / area_info, np.nan)
    wide["pct_cobertura_bosque"] = wide["pct_cobertura_bosque"].round(2)

    # cambio_neto_ha = deforestación - regeneración
    wide["cambio_neto_ha"] = (de.fillna(0) - rg).round(2)

    # tasa_perdida_relativa: defo del periodo / bosque estable del periodo ANTERIOR, anualizada
    # = 100 * (defo/n_años) / bosque_prev   (% anual del bosque en pie perdido)
    wide = wide.sort_values(["municipio_key", "ano_inicio"]).reset_index(drop=True)
    tasa = []
    bosque_prev_ha = []
    periodo_prev_ref = []
    for mkey, grp in wide.groupby("municipio_key", sort=False):
        # último bosque conocido antes de cada periodo
        last_b = None
        last_p = None
        for _, row in grp.iterrows():
            pid = row["periodo"]
            de_p = row["deforestacion_ha"]
            ny = row["n_anos"]
            if last_b is not None and last_b > 0 and pd.notna(de_p):
                t = 100.0 * (de_p / ny) / last_b
            else:
                t = np.nan
            tasa.append(round(t, 4) if pd.notna(t) else np.nan)
            bosque_prev_ha.append(round(last_b, 2) if last_b is not None else np.nan)
            periodo_prev_ref.append(last_p)
            # actualizar bosque conocido si este periodo lo trae
            if pd.notna(row["bosque_estable_ha"]):
                last_b = float(row["bosque_estable_ha"])
                last_p = pid
    wide["bosque_estable_previo_ha"] = bosque_prev_ha
    wide["periodo_bosque_previo"] = periodo_prev_ref
    wide["tasa_perdida_relativa"] = tasa  # % anual del bosque previo

    # flag de calidad de fuente
    def calidad(r):
        if r["fuente"] == "shapefile":
            return "shapefile_geometria"
        if r["fuente"] == "excel":
            return "excel_tabla"
        if r["fuente"] == "raster":
            return "raster_zonal"
        if pd.isna(r["bosque_estable_ha"]) and r["estimado"]:
            return "solo_defo_estimada"
        return "cuencas_calibrado" if str(r["fuente"]).startswith("cuencas") else "otro"
    wide["calidad_fuente"] = wide.apply(calidad, axis=1)
    return wide


def redondear(wide: pd.DataFrame) -> pd.DataFrame:
    for c in ["bosque_estable_ha", "no_bosque_ha", "regeneracion_ha",
              "sin_informacion_ha", "deforestacion_ha"]:
        wide[c] = wide[c].round(2)
    cols = ["codigo_dane", "municipio", "subregion", "periodo", "ano_inicio", "ano_fin",
            "n_anos", "bosque_estable_ha", "no_bosque_ha", "regeneracion_ha",
            "sin_informacion_ha", "deforestacion_ha", "area_con_informacion_ha",
            "pct_cobertura_bosque", "bosque_estable_previo_ha", "periodo_bosque_previo",
            "tasa_perdida_relativa", "cambio_neto_ha", "fuente", "calidad_fuente", "estimado"]
    return wide[cols].sort_values(["municipio", "ano_inicio"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Análisis de preguntas
# --------------------------------------------------------------------------
def analisis(wide: pd.DataFrame) -> dict:
    res = {}
    P0 = "2000-2002"
    PHOY = "2022-2023"  # último periodo con clases completas (bosque)
    w = wide.copy()

    # --- 1. bosque hoy vs 2000 por municipio ---
    b0 = w[w["periodo"] == P0].set_index("municipio")["bosque_estable_ha"]
    bh = w[w["periodo"] == PHOY].set_index("municipio")["bosque_estable_ha"]
    c0 = w[w["periodo"] == P0].set_index("municipio")["pct_cobertura_bosque"]
    ch = w[w["periodo"] == PHOY].set_index("municipio")["pct_cobertura_bosque"]
    comp = pd.DataFrame({"bosque_2000_2002_ha": b0, "bosque_2022_2023_ha": bh,
                         "cobertura_2000_2002_pct": c0, "cobertura_2022_2023_pct": ch})
    comp["delta_ha"] = (comp["bosque_2022_2023_ha"] - comp["bosque_2000_2002_ha"]).round(1)
    comp["delta_pct"] = (100.0 * comp["delta_ha"] / comp["bosque_2000_2002_ha"]).round(1)
    comp["delta_cobertura_pp"] = (comp["cobertura_2022_2023_pct"] - comp["cobertura_2000_2002_pct"]).round(1)
    comp = comp.round(1).sort_values("delta_ha")
    res["bosque_hoy_vs_2000"] = comp.reset_index().to_dict(orient="records")
    res["regional_bosque_2000_2002_ha"] = round(float(b0.sum()), 1)
    res["regional_bosque_2022_2023_ha"] = round(float(bh.sum()), 1)
    res["regional_delta_ha"] = round(float(bh.sum() - b0.sum()), 1)
    res["regional_delta_pct"] = round(100.0 * (bh.sum() - b0.sum()) / b0.sum(), 2)

    # --- 2. dónde la regeneración compensa la pérdida (acumulado real) ---
    real = w[w["estimado"] == False]  # noqa: E712  (solo periodos con clases reales)
    acc = (real.groupby("municipio")
           .agg(defo_total_ha=("deforestacion_ha", "sum"),
                regen_total_ha=("regeneracion_ha", "sum")).reset_index())
    acc["cambio_neto_total_ha"] = (acc["defo_total_ha"] - acc["regen_total_ha"]).round(1)
    acc["ratio_regen_defo_pct"] = (100.0 * acc["regen_total_ha"] / acc["defo_total_ha"]).round(2)
    acc = acc.round(1).sort_values("ratio_regen_defo_pct", ascending=False)
    res["regeneracion_vs_perdida"] = acc.to_dict(orient="records")
    res["regional_defo_real_ha"] = round(float(acc["defo_total_ha"].sum()), 1)
    res["regional_regen_real_ha"] = round(float(acc["regen_total_ha"].sum()), 1)

    # --- 3. municipios que perdieron > 50% de su bosque (2000->2022) ---
    perdio = comp[comp["delta_pct"] <= -50.0]
    res["perdieron_mas_mitad"] = perdio.reset_index()[
        ["municipio", "bosque_2000_2002_ha", "bosque_2022_2023_ha", "delta_pct"]
    ].to_dict(orient="records")

    # --- 4. tasa relativa por subregión: acelera o desacelera ---
    # agregado subregión × periodo (solo periodos con bosque previo real)
    valid = w[w["tasa_perdida_relativa"].notna() & (w["estimado"] == False)].copy()  # noqa: E712
    sub_per = (valid.groupby(["subregion", "periodo", "ano_inicio"])
               .agg(defo_ha=("deforestacion_ha", "sum"),
                    bosque_prev_ha=("bosque_estable_previo_ha", "sum"),
                    n_anos=("n_anos", "first")).reset_index())
    sub_per["tasa_pct_anual"] = (100.0 * (sub_per["defo_ha"] / sub_per["n_anos"])
                                 / sub_per["bosque_prev_ha"]).round(4)
    sub_per = sub_per.sort_values(["subregion", "ano_inicio"])
    # comparar primer tercio vs último tercio de periodos por subregión
    tendencia = {}
    for sub, g in sub_per.groupby("subregion"):
        g = g.sort_values("ano_inicio")
        early = g[g["ano_inicio"] <= 2008]["tasa_pct_anual"].mean()
        late = g[g["ano_inicio"] >= 2017]["tasa_pct_anual"].mean()
        tendencia[sub] = {
            "tasa_media_2000_2008_pct_anual": round(float(early), 4) if pd.notna(early) else None,
            "tasa_media_2017_2023_pct_anual": round(float(late), 4) if pd.notna(late) else None,
            "cambio": ("acelera" if pd.notna(early) and pd.notna(late) and late > early
                       else "desacelera" if pd.notna(early) and pd.notna(late) else "sin_dato"),
        }
    res["tasa_por_subregion_tendencia"] = tendencia
    res["tasa_subregion_periodo"] = sub_per.round(4).to_dict(orient="records")
    return res


def main() -> int:
    real = leer_fuentes_reales()
    est = leer_estimados_defo()
    long = pd.concat([real, est], ignore_index=True)
    wide = construir_wide(long)
    wide = calcular_metricas(wide)
    out = redondear(wide)

    csv_path = OUT / "dinamica_bosque.csv"
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"[2] dinamica_bosque.csv -> {len(out)} filas ({csv_path})")

    # coherencia vs serie_regional (deforestación real)
    reg = pd.read_csv(Path(r"E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\serie_regional.csv"),
                      encoding="utf-8-sig")
    defo_ref = reg[reg["clase"] == "Deforestación"].set_index("periodo")["hectareas"]
    defo_mio = out.groupby("periodo")["deforestacion_ha"].sum()
    print("[3] Coherencia deforestación (mio vs serie_regional):")
    for p in ORDEN:
        a = defo_mio.get(p, np.nan)
        b = defo_ref.get(p, np.nan)
        if pd.notna(a) and pd.notna(b):
            d = 100 * abs(a - b) / b if b else 0
            print(f"    {p}: {a:,.0f} vs {b:,.0f} ha  (dif {d:.2f}%)")

    res = analisis(wide)
    res["_meta"] = {
        "generado": pd.Timestamp.utcnow().isoformat(),
        "periodos_con_bosque": sorted(out[out["bosque_estable_ha"].notna()]["periodo"].unique().tolist()),
        "periodos_solo_defo": sorted(out[out["bosque_estable_ha"].isna()]["periodo"].unique().tolist()),
        "periodo_base": "2000-2002",
        "periodo_actual_bosque": "2022-2023",
        "nota_cobertura": ("pct_cobertura_bosque = bosque_estable / (bosque + no_bosque + defo + regen). "
                           "Normaliza por la variable superficie 'Sin Información' de cada bienio, "
                           "por lo que es más comparable que la ha bruta de bosque."),
        "nota_tasa": ("tasa_perdida_relativa = 100 * (defo/n_años) / bosque_estable del periodo previo "
                      "con dato (% anual del bosque en pie perdido)."),
        "advertencia_bosque_estable": ("El área 'Bosque Estable' de cada bienio depende de la cobertura "
                                       "'Sin Información' de ese año; sus fluctuaciones NO son todas cambio "
                                       "real de bosque. 2015-2016 (cuencas parcial) y 2016-2017 (Sin Info alta) "
                                       "son atípicos de cobertura, no de deforestación."),
    }
    json_path = OUT / "dinamica_resumen.json"
    json_path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[4] dinamica_resumen.json -> {json_path}")

    # impresión de hallazgos clave
    print("\n===== HALLAZGOS =====")
    print(f"Bosque regional 2000-02: {res['regional_bosque_2000_2002_ha']:,.0f} ha | "
          f"2022-23: {res['regional_bosque_2022_2023_ha']:,.0f} ha | "
          f"delta {res['regional_delta_ha']:,.0f} ha ({res['regional_delta_pct']}%)")
    print("\nMayores pérdidas de bosque (ha, 2000->2022):")
    for r in res["bosque_hoy_vs_2000"][:6]:
        print(f"  {r['municipio']:<20} {r['bosque_2000_2002_ha']:>10,.0f} -> "
              f"{r['bosque_2022_2023_ha']:>10,.0f}  ({r['delta_pct']:+.1f}%)  "
              f"cobertura {r['cobertura_2000_2002_pct']}->{r['cobertura_2022_2023_pct']}%")
    print("\nMayores ganancias de bosque (ha):")
    for r in res["bosque_hoy_vs_2000"][-5:]:
        print(f"  {r['municipio']:<20} {r['bosque_2000_2002_ha']:>10,.0f} -> "
              f"{r['bosque_2022_2023_ha']:>10,.0f}  ({r['delta_pct']:+.1f}%)")
    print("\nPerdieron > 50% del bosque:")
    if res["perdieron_mas_mitad"]:
        for r in res["perdieron_mas_mitad"]:
            print(f"  {r['municipio']}: {r['delta_pct']}%")
    else:
        print("  Ninguno (usando bosque_estable bruto 2000-02 vs 2022-23).")
    print("\nRegeneración vs pérdida (top ratio regen/defo):")
    for r in res["regeneracion_vs_perdida"][:6]:
        print(f"  {r['municipio']:<20} defo {r['defo_total_ha']:>8,.0f}  regen {r['regen_total_ha']:>7,.1f}  "
              f"ratio {r['ratio_regen_defo_pct']}%  neto {r['cambio_neto_total_ha']:,.0f}")
    print("\nTasa relativa por subregión (2000-08 vs 2017-23, % anual del bosque):")
    for sub, t in res["tasa_por_subregion_tendencia"].items():
        print(f"  {sub:<12} {t['tasa_media_2000_2008_pct_anual']} -> "
              f"{t['tasa_media_2017_2023_pct_anual']}  [{t['cambio']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
