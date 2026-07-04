# -*- coding: utf-8 -*-
"""
Serie de deforestacion por AREA PROTEGIDA (NOMBRE x CATEGORIA) x periodo x clase
================================================================================
CORPOURABA 2000-2024. Capas *_AProteg* = interseccion de las clases de cambio de
bosque (gridcode 1..5) con el Sistema de Areas Protegidas de la jurisdiccion.

FUENTES POR PERIODO
  - shapefile con geometria EPSG:3115 (metrico) -> ha = area/10000  (10 periodos utiles)
      2002-2004, 2004-2006, 2008-2010, 2015-2016, 2016-2017, 2017-2018,
      2019-2020, 2020-2021, 2021-2022, 2022-2023
  - 2006-2008: shapefile Y Excel presentes PERO son DUPLICADO EXACTO de 2002-2004
      (verificado: defo ha identica area por area; 474.1 ha; n=9498). Se conserva
      en la serie con flag es_duplicado=True y se EXCLUYE de todos los agregados
      para no doble-contar. (El municipal 2006-2008 NO esta duplicado: 2539 vs 3718 ha.)
  - 2023-2024: .dbf huerfano sin geometria ni columna de area -> SOLO CONTEOS de
      poligonos (gridcode 1,2,4). Sin hectareas ni %.
  - AUSENTE en el paquete (sin capa AProteg utilizable): 2000-2002, 2010-2012,
      2012-2013, 2013-2014, 2014-2015, 2018-2019 (esta ultima ni siquiera tiene carpeta).

CLASE: se deriva del gridcode oficial (1=Bosque Estable, 2=Deforestacion,
  3=Sin Informacion, 4=Regeneracion, 5=No Bosque Estable). Mas robusto que el texto
  Tipo_Cober/Cobertura, que trae erratas (acento grave 'Deforestaciòn' en 2015-2016)
  y cambia de nombre de columna ('Cobertura' en 2016-2017).

VALIDACION: area geometrica vs columna 'AREA HA' del Excel 2022-2023 -> desviacion 0.018%.
  Cada NOMBRE mapea a exactamente UNA CATEGORIA (sin ambiguedad). 21 areas, 6 categorias.

Salidas:
  data/processed/analisis/areas_protegidas_serie.csv    (UTF-8 BOM, snake_case es)
  data/processed/analisis/areas_protegidas_resumen.json
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\etl")
import run_etl
import numpy as np
import pandas as pd
from pyogrio import read_dataframe

RAW = Path(r"E:\drive-download-20260703T192518Z-3-001")
OUT = Path(r"E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\analisis")
OUT.mkdir(parents=True, exist_ok=True)
SERIE_REG = Path(r"E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\serie_regional.csv")

METRIC = "EPSG:3115"
PANIOS = {p: (i, f) for p, i, f in run_etl.PERIODOS}

# Fuentes con geometria. 2006-2008 incluido pero se marca duplicado y se excluye de agregados.
SHP = {
    "2002-2004": "2002-2004/Defor2002_2004_AProteg.shp",
    "2004-2006": "2004-2006/Defor2004_2006_AProteg.shp",
    "2006-2008": "2006-2008/Defor2006_2008_Mpios_Aproteg.shp",  # DUPLICADO de 2002-2004
    "2008-2010": "2008-2010/Defor2008_2010_Aproteg.shp",
    "2015-2016": "2015-2016/Defor2015_2016_AProteg.shp",
    "2016-2017": "2016-2017/Defor2016_2017_AProteg.shp",
    "2017-2018": "2017-2018/Defor2017_2018_AProteg.shp",
    "2019-2020": "2019-2020/Defor2019_2020_AProteg.shp",
    "2020-2021": "2020-2021/Defor2020_2021_AProteg.shp",
    "2021-2022": "2021-2022/Defor2021_2022_Aproteg.shp",
    "2022-2023": "2022-2023/Defor2022_2023_AProteg.shp",
}
DBF_ONLY = {"2023-2024": "2023-2024/Defor2023-2024_AProteg.dbf"}
DUPLICADOS = {"2006-2008": "2002-2004"}   # periodo -> del que es copia
AUSENTES = ["2000-2002", "2010-2012", "2012-2013", "2013-2014", "2014-2015", "2018-2019"]

# Periodos con geometria INDEPENDIENTE (excluye el duplicado) -> base de todos los agregados
GEO_UTILES = [p for p in SHP if p not in DUPLICADOS]

QA = []
def log(m): print(m, flush=True); QA.append(m)


def clean_txt(s) -> str:
    return "" if pd.isna(s) else " ".join(str(s).split()).strip()


def clase_de_gridcode(gc):
    """gridcode oficial 1..5 -> etiqueta bonita. Cae a None si invalido."""
    try:
        key = run_etl.GRIDCODE_CLASE.get(int(gc))
        return run_etl.CLASES[key] if key else None
    except (ValueError, TypeError):
        return None


def clase_de_fila(row):
    c = clase_de_gridcode(row.get("gridcode"))
    if c:
        return c
    for col in ("Tipo_Cober", "Cobertura"):
        if col in row and pd.notna(row[col]):
            k = run_etl.match_clase(row[col])
            if k:
                return run_etl.CLASES[k]
    return None


def cargar():
    filas, qa = [], []
    # ---- periodos con geometria ----
    for pid, rel in SHP.items():
        ini, fin = PANIOS[pid]
        es_dup = pid in DUPLICADOS
        g = run_etl.read_shp(RAW / rel)
        if g.crs is None:
            g = g.set_crs(METRIC)
        elif not g.crs.is_projected:
            g = g.to_crs(METRIC)
        g["_ha"] = g.geometry.area / 10_000.0
        g["_clase"] = g.apply(clase_de_fila, axis=1)
        g["_nombre"] = g["NOMBRE"].map(clean_txt)
        g["_categoria"] = g["CATEGORIA"].map(clean_txt)
        sin_clase = int(g["_clase"].isna().sum())
        flag = f"duplicado_de_{DUPLICADOS[pid]}" if es_dup else "geometria_epsg3115"
        grp = (g.dropna(subset=["_clase"])
                 .groupby(["_nombre", "_categoria", "_clase"])
                 .agg(hectareas=("_ha", "sum"), n_poligonos=("_ha", "size")).reset_index())
        for _, r in grp.iterrows():
            filas.append({
                "periodo": pid, "ano_inicio": ini, "ano_fin": fin,
                "nombre": r["_nombre"], "categoria": r["_categoria"], "clase": r["_clase"],
                "hectareas": round(float(r["hectareas"]), 2),
                "hectareas_anuales": round(float(r["hectareas"]) / max(1, fin - ini), 2),
                "n_poligonos": int(r["n_poligonos"]),
                "fuente": "shapefile", "flag_calidad": flag, "es_duplicado": es_dup,
                "usado_en_agregados": (not es_dup),
            })
        qa.append({"periodo": pid, "fuente": "shapefile", "n_pol": int(len(g)),
                   "ha_total": round(float(g["_ha"].sum()), 1),
                   "defo_ha": round(float(g[g["gridcode"] == 2]["_ha"].sum()), 1),
                   "poligonos_sin_clase": sin_clase, "es_duplicado": es_dup})

    # ---- 2023-2024: dbf huerfano -> solo conteos ----
    for pid, rel in DBF_ONLY.items():
        ini, fin = PANIOS[pid]
        d = read_dataframe(RAW / rel, read_geometry=False)
        txt = " ".join(str(v) for c in d.columns if d[c].dtype == object
                       for v in d[c].dropna().head(3))
        if "�" in txt:
            try:
                d = read_dataframe(RAW / rel, read_geometry=False, encoding="latin-1")
            except Exception:
                pass
        d["_clase"] = d.apply(clase_de_fila, axis=1)
        d["_nombre"] = d["NOMBRE"].map(clean_txt)
        d["_categoria"] = d["CATEGORIA"].map(clean_txt)
        grp = (d.dropna(subset=["_clase"])
                 .groupby(["_nombre", "_categoria", "_clase"]).size()
                 .reset_index(name="n_poligonos"))
        for _, r in grp.iterrows():
            filas.append({
                "periodo": pid, "ano_inicio": ini, "ano_fin": fin,
                "nombre": r["_nombre"], "categoria": r["_categoria"], "clase": r["_clase"],
                "hectareas": np.nan, "hectareas_anuales": np.nan,
                "n_poligonos": int(r["n_poligonos"]),
                "fuente": "dbf_huerfano", "flag_calidad": "solo_conteo_sin_area",
                "es_duplicado": False, "usado_en_agregados": False,
            })
        qa.append({"periodo": pid, "fuente": "dbf_huerfano", "n_pol": int(len(d)),
                   "ha_total": None,
                   "defo_n_poligonos": int((d["gridcode"] == 2).sum()),
                   "poligonos_sin_clase": int(d["_clase"].isna().sum()), "es_duplicado": False})

    return pd.DataFrame(filas), qa


def main():
    df, qa = cargar()
    df = df.sort_values(["periodo", "categoria", "nombre", "clase"]).reset_index(drop=True)
    cols = ["periodo", "ano_inicio", "ano_fin", "nombre", "categoria", "clase",
            "hectareas", "hectareas_anuales", "n_poligonos", "fuente",
            "flag_calidad", "es_duplicado", "usado_en_agregados"]
    df[cols].to_csv(OUT / "areas_protegidas_serie.csv", index=False, encoding="utf-8-sig")
    log(f"serie -> areas_protegidas_serie.csv ({len(df)} filas)")

    # ============ AGREGADOS (solo periodos con geometria independiente) ============
    defo = df[(df["clase"] == "Deforestación") & df["hectareas"].notna()
              & df["usado_en_agregados"]].copy()

    # 1) Ranking de AP por deforestacion total acumulada
    rank_pa = (defo.groupby(["nombre", "categoria"])
                    .agg(defo_ha_total=("hectareas", "sum"),
                         periodos_con_dato=("periodo", "nunique"),
                         defo_ha_anual_media=("hectareas_anuales", "mean"))
                    .reset_index().sort_values("defo_ha_total", ascending=False))
    rank_pa["defo_ha_total"] = rank_pa["defo_ha_total"].round(1)
    rank_pa["defo_ha_anual_media"] = rank_pa["defo_ha_anual_media"].round(1)
    # periodo pico por AP
    idx_pico = defo.groupby(["nombre", "categoria"])["hectareas"].idxmax()
    pico = defo.loc[idx_pico, ["nombre", "categoria", "periodo", "hectareas"]]
    pico = pico.rename(columns={"periodo": "periodo_pico", "hectareas": "defo_ha_pico"})
    rank_pa = rank_pa.merge(pico, on=["nombre", "categoria"], how="left")

    # 2) Ranking por CATEGORIA
    rank_cat = (defo.groupby("categoria")
                     .agg(defo_ha_total=("hectareas", "sum"),
                          n_areas=("nombre", "nunique"))
                     .reset_index().sort_values("defo_ha_total", ascending=False))
    rank_cat["defo_ha_total"] = rank_cat["defo_ha_total"].round(1)

    # 3) top celdas AP x periodo
    top_celdas = (defo.sort_values("hectareas", ascending=False)
                      .head(20)[["nombre", "categoria", "periodo", "hectareas", "hectareas_anuales"]]
                      .round(1).to_dict("records"))

    # 4) % de la deforestacion de la jurisdiccion DENTRO de AP, por periodo
    reg = pd.read_csv(SERIE_REG)
    reg_defo = reg[reg["clase"] == "Deforestación"].set_index("periodo")
    pct_rows = []
    for pid in GEO_UTILES:
        ap_ha = float(defo[defo["periodo"] == pid]["hectareas"].sum())
        jur_ha = float(reg_defo.loc[pid, "hectareas"]) if pid in reg_defo.index else np.nan
        jur_est = bool(reg_defo.loc[pid, "estimado"]) if pid in reg_defo.index else None
        ini, fin = PANIOS[pid]
        pct_rows.append({
            "periodo": pid, "ano_inicio": ini, "ano_fin": fin,
            "defo_ap_ha": round(ap_ha, 1),
            "defo_jurisdiccion_ha": round(jur_ha, 1) if jur_ha == jur_ha else None,
            "pct_dentro_ap": round(100 * ap_ha / jur_ha, 2) if (jur_ha and jur_ha == jur_ha) else None,
            "jurisdiccion_estimada": jur_est,
        })
    pct_df = pd.DataFrame(pct_rows)
    tot_ap = float(defo["hectareas"].sum())
    tot_jur = float(reg_defo.loc[[p for p in GEO_UTILES if p in reg_defo.index], "hectareas"].sum())
    pct_global = round(100 * tot_ap / tot_jur, 2)
    # tendencia del % (regresion sobre ano medio)
    pp = pct_df.dropna(subset=["pct_dentro_ap"]).copy()
    pp["ano_medio"] = (pp["ano_inicio"] + pp["ano_fin"]) / 2
    pend_pct = float(np.polyfit(pp["ano_medio"], pp["pct_dentro_ap"], 1)[0]) if len(pp) >= 3 else None

    # 5) Aceleracion reciente: tasa anual media 2019-2023 vs 2015-2018
    recientes = ["2019-2020", "2020-2021", "2021-2022", "2022-2023"]
    base = ["2015-2016", "2016-2017", "2017-2018"]
    def tasa_media(ps):
        return defo[defo["periodo"].isin(ps)].groupby(["nombre", "categoria"])["hectareas_anuales"].mean()
    acc = pd.DataFrame({"tasa_anual_2019_2023": tasa_media(recientes),
                        "tasa_anual_2015_2018": tasa_media(base)}).fillna(0.0)
    acc["delta_ha_anual"] = (acc["tasa_anual_2019_2023"] - acc["tasa_anual_2015_2018"]).round(2)
    acc["factor"] = np.where(acc["tasa_anual_2015_2018"] > 0.1,
                             (acc["tasa_anual_2019_2023"] / acc["tasa_anual_2015_2018"]).round(2), np.nan)
    acc = acc.round(2).sort_values("delta_ha_anual", ascending=False).reset_index()

    # 6) Series de las AP de interes (incluye conteo 2023-2024)
    interes = {
        "PNN Paramillo": ("Paramillo", "Parque Nacional Natural"),
        "PNN Los Katíos": ("Los Katío", "Parque Nacional Natural"),
        "PNN Las Orquídeas": ("Las Orquideas", "Parque Nacional Natural"),
        "RFPN Río León": ("Río León", "Reserva Forestal Protectora Nacional"),
        "RFPN Urrao (De Urrao)": ("De Urrao", "Reserva Forestal Protectora Nacional"),
        "RFPN Carauta": ("Carauta", "Reserva Forestal Protectora Nacional"),
    }
    series_interes = {}
    for etq, (nom, cat) in interes.items():
        sub = defo[(defo["nombre"] == nom) & (defo["categoria"] == cat)]
        serie_p = {r["periodo"]: round(float(r["hectareas"]), 2) for _, r in sub.iterrows()}
        cnt_23 = int(df[(df["nombre"] == nom) & (df["categoria"] == cat)
                        & (df["periodo"] == "2023-2024") & (df["clase"] == "Deforestación")]
                     ["n_poligonos"].sum())
        rec = sub[sub["periodo"].isin(recientes)]["hectareas_anuales"].mean()
        bas = sub[sub["periodo"].isin(base)]["hectareas_anuales"].mean()
        series_interes[etq] = {
            "nombre_dato": nom, "categoria": cat,
            "defo_ha_total_periodos_utiles": round(float(sub["hectareas"].sum()), 2),
            "defo_ha_por_periodo": serie_p,
            "tasa_anual_media_2015_2018": round(float(bas), 2) if bas == bas else 0.0,
            "tasa_anual_media_2019_2023": round(float(rec), 2) if rec == rec else 0.0,
            "conteo_poligonos_defo_2023_2024": cnt_23,
        }

    resumen = {
        "tema": "Deforestacion en areas protegidas — CORPOURABA 2000-2024",
        "generado": pd.Timestamp.now(tz="UTC").isoformat(),
        "unidad": "hectareas (area geometrica EPSG:3115); % adimensional",
        "cobertura_temporal": {
            "periodos_geometria_utiles": GEO_UTILES,
            "n_periodos_geometria_utiles": len(GEO_UTILES),
            "periodo_duplicado_excluido": DUPLICADOS,
            "periodo_solo_conteo": list(DBF_ONLY.keys()),
            "periodos_ausentes_en_paquete": AUSENTES,
        },
        "n_areas_protegidas": int(df[["nombre", "categoria"]].drop_duplicates().shape[0]),
        "areas_protegidas": sorted(
            f"{n} | {c}" for n, c in df[["nombre", "categoria"]].drop_duplicates().itertuples(index=False)),
        "deforestacion_ap_total_ha": round(tot_ap, 1),
        "deforestacion_jurisdiccion_ha_mismos_periodos": round(tot_jur, 1),
        "pct_global_dentro_ap": pct_global,
        "pct_dentro_ap_pendiente_por_ano": round(pend_pct, 3) if pend_pct is not None else None,
        "ranking_ap_por_deforestacion": rank_pa.head(15).round(1).to_dict("records"),
        "ranking_por_categoria": rank_cat.to_dict("records"),
        "top_celdas_ap_x_periodo": top_celdas,
        "pct_dentro_ap_por_periodo": pct_df.to_dict("records"),
        "aceleracion_2019_2023_vs_2015_2018": acc.head(12).to_dict("records"),
        "series_areas_de_interes": series_interes,
        "qa_por_periodo": qa,
        "notas": [
            "Clase derivada del gridcode oficial (1=Bosque Estable,2=Deforestacion,3=Sin "
            "Informacion,4=Regeneracion,5=No Bosque Estable); mas robusto que Tipo_Cober/Cobertura.",
            "Area desde geometria EPSG:3115; validado contra columna 'AREA HA' del Excel "
            "2022-2023 con desviacion 0.018%. Cada NOMBRE mapea a una unica CATEGORIA.",
            "2006-2008 (capa AProteg, shp y Excel) es DUPLICADO EXACTO de 2002-2004 (474.1 ha, "
            "n=9498, identico area por area). Se conserva en el CSV con es_duplicado=true y se "
            "EXCLUYE de todos los agregados. El municipal 2006-2008 NO esta duplicado (2539 ha).",
            "2023-2024 es .dbf huerfano sin geometria ni columna de area: SOLO conteos de "
            "poligonos por clase (gridcode 1,2,4). Sin hectareas ni %.",
            "2000-2002, 2010-2012, 2012-2013, 2013-2014, 2014-2015 y 2018-2019 no traen capa "
            "AProteg utilizable; esos periodos no entran en la serie ni en el %.",
            "El % dentro de AP compara defo de la capa AProteg contra serie_regional.csv (defo "
            "municipal), misma clasificacion por periodo. En 2015-2016 el denominador municipal "
            "es estimado/calibrado por cuencas (jurisdiccion_estimada=true): menor confianza.",
            "PNN Paramillo entra a CORPOURABA solo por un borde: su huella y su deforestacion "
            "dentro de la jurisdiccion son pequenas; la mayor parte del PNN esta en otras CAR.",
        ],
    }
    (OUT / "areas_protegidas_resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    log("resumen -> areas_protegidas_resumen.json")

    # ---------- consola: hallazgos ----------
    print("\n=== % DEFORESTACION DENTRO DE AP POR PERIODO (excl. duplicado 2006-2008) ===")
    print(pct_df.to_string(index=False))
    print(f"\nGLOBAL: {tot_ap:,.0f} ha en AP / {tot_jur:,.0f} ha jurisdiccion (mismos periodos) = {pct_global}%")
    print(f"Tendencia del %: pendiente {pend_pct:+.3f} pp/ano" if pend_pct is not None else "")
    print("\n=== TOP 12 AP POR DEFORESTACION TOTAL ACUMULADA (ha) ===")
    print(rank_pa.head(12)[["nombre", "categoria", "defo_ha_total", "periodos_con_dato",
                            "periodo_pico", "defo_ha_pico"]].to_string(index=False))
    print("\n=== DEFORESTACION POR CATEGORIA (ha, acumulado) ===")
    print(rank_cat.to_string(index=False))
    print("\n=== TOP 12 CELDAS AP x PERIODO ===")
    for c in top_celdas[:12]:
        print(f"  {c['hectareas']:>8.1f} ha  {c['periodo']}  {c['nombre']} | {c['categoria']}")
    print("\n=== ACELERACION 2019-2023 vs 2015-2018 (ha/ano) ===")
    print(acc.head(10).to_string(index=False))
    print("\n=== SERIES AP DE INTERES ===")
    for etq, d in series_interes.items():
        print(f"  {etq}: total {d['defo_ha_total_periodos_utiles']} ha | "
              f"base15-18 {d['tasa_anual_media_2015_2018']} vs rec19-23 {d['tasa_anual_media_2019_2023']} ha/ano | "
              f"conteo_23_24={d['conteo_poligonos_defo_2023_2024']}")
        print(f"       por_periodo={d['defo_ha_por_periodo']}")


if __name__ == "__main__":
    main()
