# -*- coding: utf-8 -*-
"""
Análisis de CUENCAS HIDROGRÁFICAS — Observatorio Deforestación CORPOURABA
=========================================================================
Serie por cuenca ('NOMB CUENC' / IDCU) × periodo × clase (gridcode), 2000-2024.

Las 7 cuencas monitoreadas (IDCU estable y verificado en todos los periodos):
  1 Turbo Currulao · 2 Sucio Alto · 3 San Juan · 4 Mulaticos ·
  5 León · 6 Cauca · 7 Canalete

Fuente por periodo (jerarquía):
  1. shapefile completo (.shp+.shx+.dbf, CRS métrico EPSG:3115) -> ha desde GEOMETRÍA
  2. Excel *_Cuenc*_Dat.xls[x] con columna de área -> ha desde columna SI valida
  3. .dbf huérfano sin geometría ni área -> solo conteo de polígonos (flag)

CALIDAD DE ÁREA (hallazgo clave del paquete):
  La columna 'AREA_ha'/'AREA HA' guarda, en varios periodos, el área del polígono
  de cobertura ORIGINAL antes de recortarlo contra la cuenca (pre-clip). Prueba:
  en 2022-2023 la columna suma 2.766.595 ha pero la geometría suma 723.026 ha (real).
  Por eso el área SOLO es confiable desde geometría, o desde una columna cuyo total
  de cuenca coincide con la referencia geométrica (~722.980 ha, límites fijos).
  Se valida cada periodo sin geometría contra esa referencia:
    - 2000-2002 y 2006-2008 (xlsx): total 722.858 ha  -> columna CONFIABLE (clipeada)
    - 2021-2022 (xlsx):             total 2.749.067 ha -> columna NO confiable (pre-clip)
    - 2023-2024 (dbf huérfano):     sin columna de área -> solo conteo
  Los periodos con área NO confiable se conservan (conteo + valor crudo marcado)
  pero se EXCLUYEN de rankings de hectáreas, % de área y tendencia.

Periodos SIN capa de cuencas en el paquete (vacío declarado):
  2010-2012 (solo .shx/.prj), 2012-2013 y 2013-2014 (no hay capa),
  2014-2015 (solo .shx/.prj), 2018-2019 (carpeta inexistente).

Salidas:
  data/processed/analisis/cuencas_serie.csv     (UTF-8 BOM, snake_case es)
  data/processed/analisis/cuencas_resumen.json
"""
from __future__ import annotations
import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, r"E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\etl")
import run_etl
import numpy as np
import pandas as pd
import geopandas as gpd
from pyogrio import read_dataframe

RAW = run_etl.DEFAULT_RAW
OUT = Path(r"E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\analisis")
OUT.mkdir(parents=True, exist_ok=True)
METRIC = run_etl.METRIC_FALLBACK
GRIDCODE = run_etl.GRIDCODE_CLASE   # 1..5 -> etiqueta ASCII
CLASES = run_etl.CLASES             # ASCII -> etiqueta bonita
PERIODOS = {p: (i, f) for p, i, f in run_etl.PERIODOS}

# Cuenca canónica por IDCU (nombre estable verificado en todos los periodos)
CUENCAS = {1: "Turbo Currulao", 2: "Sucio Alto", 3: "San Juan",
           4: "Mulaticos", 5: "León", 6: "Cauca", 7: "Canalete"}

# Resolución de fuente por periodo. Tipo: 'shp' | 'xlsx' | 'dbf'
FUENTES = {
    "2000-2002": ("xlsx", "2000-2002/Defor2000_2002_Cuenca_Dat.xlsx"),
    "2002-2004": ("shp",  "2002-2004/Defor2002_2004_Cuenca.shp"),
    "2004-2006": ("shp",  "2004-2006/Defor2004_2006_Cuenc.shp"),
    "2006-2008": ("xlsx", "2006-2008/Defor2006_2008_Cuenc_Dat.xlsx"),  # shp sin .shx
    "2008-2010": ("shp",  "2008-2010/Defor2008_2010_Cuenc.shp"),
    "2015-2016": ("shp",  "2015-2016/Defor2015_2016_Cuenc.shp"),
    "2016-2017": ("shp",  "2016-2017/Defor2016_2017_Cuenc.shp"),
    "2017-2018": ("shp",  "2017-2018/Defor2017_2018_Cuenc.shp"),
    "2019-2020": ("shp",  "2019-2020/Defor2019_2020_Cuenc.shp"),
    "2020-2021": ("shp",  "2020-2021/Defor2020_2021_Cuenc.shp"),
    "2021-2022": ("xlsx", "2021-2022/Defor2021-2022_Cuenc_Dat.xlsx"),  # sin shp; área pre-clip
    "2022-2023": ("shp",  "2022-2023/Defor2022_2023_Cuenc.shp"),
    "2023-2024": ("dbf",  "2023-2024/Defor2023-2024_Cuenc.dbf"),       # huérfano sin geom/área
}
# Declarados sin capa utilizable en el paquete
VACIOS = ["2010-2012", "2012-2013", "2013-2014", "2014-2015", "2018-2019"]

# Tolerancia para aceptar la columna de área de un periodo sin geometría:
# su total de las 7 cuencas debe estar a ±12% de la referencia geométrica.
TOL_AREA = 0.12

QA = []
def log(m):
    print(m, flush=True); QA.append(m)


def area_col(df):
    for c in df.columns:
        cu = str(c).strip().upper().replace("-", " ").replace("_", " ")
        if cu in ("AREA HA", "AREA", "AREA HA "):
            return c
    return None


def clasificar(gridcode, tipo_cober):
    """gridcode oficial primero; si falta usa Tipo_Cober con match_clase (maneja errata)."""
    try:
        gc = int(gridcode)
        if gc in GRIDCODE:
            return GRIDCODE[gc]
    except (ValueError, TypeError):
        pass
    m = run_etl.match_clase(tipo_cober) if pd.notna(tipo_cober) else None
    return m


def idcu_canon(row):
    """Mapea a IDCU canónico; si IDCU inválido intenta por nombre (tolera mojibake)."""
    try:
        v = int(row["IDCU"])
        if v in CUENCAS:
            return v
    except (ValueError, TypeError, KeyError):
        pass
    nm = run_etl._ascii(row.get("NOMB CUENC", ""))
    for k, name in CUENCAS.items():
        if run_etl._ascii(name) == nm:
            return k
    return None


def leer(periodo, tipo, rel):
    """Devuelve DataFrame con _idcu, _clase, _ha, _metodo, _tiene_area."""
    path = RAW / rel
    if not path.exists():
        log(f"  [WARN] {periodo}: no existe {rel}")
        return None
    if tipo == "shp":
        g = run_etl.read_shp(path)
        if g.crs is None:
            g = g.set_crs(METRIC)
        proj = g if g.crs.is_projected else g.to_crs(METRIC)
        df = pd.DataFrame(g.drop(columns="geometry"))
        df["_ha"] = (proj.geometry.area / 10_000.0).values
        metodo, tiene_area = "geometria", True
    elif tipo == "xlsx":
        xl = pd.ExcelFile(path)
        df = xl.parse(xl.sheet_names[0])
        ac = area_col(df)
        if ac is None:
            log(f"  [WARN] {periodo}: Excel sin columna de área -> solo conteo")
            df["_ha"] = np.nan
            metodo, tiene_area = "conteo", False
        else:
            df["_ha"] = pd.to_numeric(df[ac], errors="coerce")
            metodo, tiene_area = "columna_area", True
    elif tipo == "dbf":
        df = read_dataframe(path, read_geometry=False)
        ac = area_col(df)
        if ac is not None:
            df["_ha"] = pd.to_numeric(df[ac], errors="coerce")
            metodo, tiene_area = "columna_area", True
        else:
            df["_ha"] = np.nan
            metodo, tiene_area = "conteo", False
    else:
        return None

    # normalizar nombre 'NOMB CUENC' si viniera con guion bajo
    if "NOMB CUENC" not in df.columns:
        cand = [c for c in df.columns if str(c).strip().upper().replace("_", " ") == "NOMB CUENC"]
        if cand:
            df = df.rename(columns={cand[0]: "NOMB CUENC"})
    df["_idcu"] = df.apply(idcu_canon, axis=1)
    df["_clase"] = [clasificar(gc, tc) for gc, tc in
                    zip(df.get("gridcode", pd.Series([None] * len(df))),
                        df.get("Tipo_Cober", pd.Series([None] * len(df))))]
    df["_metodo"] = metodo
    df["_tiene_area"] = tiene_area
    return df


def main():
    log("[1/4] Lectura de capas de cuencas por periodo ...")
    raw_por_periodo = {}   # periodo -> (df, metodo, tiene_area, total_area)
    for periodo in [p for p, *_ in run_etl.PERIODOS]:
        if periodo in VACIOS:
            log(f"  {periodo}: SIN capa de cuencas utilizable -> vacío declarado")
            continue
        if periodo not in FUENTES:
            log(f"  {periodo}: sin fuente configurada -> omitido")
            continue
        tipo, rel = FUENTES[periodo]
        df = leer(periodo, tipo, rel)
        if df is None:
            continue
        tiene_area = bool(df["_tiene_area"].iloc[0])
        total_area = float(df["_ha"].sum()) if tiene_area else np.nan
        raw_por_periodo[periodo] = (df, tipo, df["_metodo"].iloc[0], tiene_area, total_area)

    # referencia geométrica de área total de las 7 cuencas (límites fijos)
    ref_areas = [t[4] for p, t in raw_por_periodo.items() if t[2] == "geometria"]
    area_ref_total = float(np.median(ref_areas))
    log(f"  referencia geométrica área total 7 cuencas = {area_ref_total:,.0f} ha "
        f"(mediana de {len(ref_areas)} periodos con geometría)")

    # segunda pasada: decidir confiabilidad de área y armar la serie larga
    filas = []
    calidad_periodo = {}
    for periodo, (df, tipo, metodo, tiene_area, total_area) in raw_por_periodo.items():
        ini, fin = PERIODOS[periodo]
        if not tiene_area:
            area_confiable = False
            flag = "solo_conteo_sin_area"
        elif metodo == "geometria":
            area_confiable = True
            flag = "geometria_metrica"
        else:  # columna: validar contra referencia
            desv = abs(total_area - area_ref_total) / area_ref_total
            area_confiable = desv <= TOL_AREA
            flag = ("columna_validada_ok" if area_confiable
                    else "columna_area_preclip_no_confiable")
        calidad_periodo[periodo] = {
            "fuente_tipo": tipo, "metodo": metodo,
            "area_total_ha": None if pd.isna(total_area) else round(total_area, 1),
            "area_confiable": area_confiable, "flag_calidad": flag,
        }
        sin_idcu = int(df["_idcu"].isna().sum())
        if sin_idcu:
            log(f"    [WARN] {periodo}: {sin_idcu} filas sin IDCU canónico (descartadas)")
        g = df.dropna(subset=["_idcu", "_clase"])
        agg = g.groupby(["_idcu", "_clase"]).agg(
            hectareas=("_ha", "sum"), n_poligonos=("_ha", "size")).reset_index()
        marca = ("OK" if area_confiable else
                 ("SOLO CONTEO" if not tiene_area else "AREA NO CONFIABLE"))
        tot = agg["hectareas"].sum()
        log(f"  {periodo}: {tipo}/{metodo} -> {agg['_idcu'].nunique()} cuencas, "
            f"{('%.0f ha' % tot) if tiene_area else 'sin área'}  [{marca}]")
        for _, r in agg.iterrows():
            ha = None if (pd.isna(r["hectareas"]) or not tiene_area) else round(float(r["hectareas"]), 2)
            filas.append({
                "idcu": int(r["_idcu"]),
                "cuenca": CUENCAS[int(r["_idcu"])],
                "periodo": periodo, "ano_inicio": ini, "ano_fin": fin,
                "clase": CLASES.get(r["_clase"], r["_clase"]),
                "hectareas": ha,
                "hectareas_anuales": None if ha is None else round(ha / max(1, fin - ini), 2),
                "n_poligonos": int(r["n_poligonos"]),
                "fuente": f"{tipo}:{metodo}",
                "area_confiable": area_confiable,
                "flag_calidad": flag,
            })

    serie = pd.DataFrame(filas).sort_values(
        ["cuenca", "periodo", "clase"]).reset_index(drop=True)
    serie = serie[["idcu", "cuenca", "periodo", "ano_inicio", "ano_fin", "clase",
                   "hectareas", "hectareas_anuales", "n_poligonos", "fuente",
                   "area_confiable", "flag_calidad"]]
    serie.to_csv(OUT / "cuencas_serie.csv", index=False, encoding="utf-8-sig")
    log(f"  cuencas_serie.csv: {len(serie)} filas | "
        f"periodos con dato: {serie['periodo'].nunique()}")

    # ---- [2/4] Área monitoreada por cuenca (referencia geométrica) ----
    log("[2/4] Área por cuenca y cobertura de la jurisdicción ...")
    conf = serie[serie["area_confiable"]].copy()   # solo periodos con área confiable
    ref_periodo = "2022-2023"
    area_ref = (serie[serie["periodo"] == ref_periodo]
                .groupby(["idcu", "cuenca"])["hectareas"].sum())
    # respaldo: promedio de área total por periodo con geometría
    geo_mask = serie["fuente"].str.contains("geometria")
    area_prom = (serie[geo_mask].groupby(["periodo", "idcu"])["hectareas"].sum()
                 .groupby("idcu").mean())

    # ---- [3/4] Deforestación por cuenca, % de área y tendencia (solo confiable) ----
    log("[3/4] Deforestación por cuenca, % de área y tendencia (área confiable) ...")
    defo = conf[conf["clase"] == "Deforestación"].copy()
    n_periodos_conf = defo["periodo"].nunique()
    defo_tot = defo.groupby(["idcu", "cuenca"])["hectareas"].sum()

    cuencas_json = []
    for idcu, nombre in CUENCAS.items():
        d = defo[defo["idcu"] == idcu].dropna(subset=["hectareas_anuales"]).copy()
        d["ano_medio"] = (d["ano_inicio"] + d["ano_fin"]) / 2.0
        d = d.sort_values("ano_medio")
        # área de referencia de la cuenca (2022-2023 geometría)
        area = None
        if (idcu, nombre) in area_ref.index and pd.notna(area_ref.loc[(idcu, nombre)]):
            area = float(area_ref.loc[(idcu, nombre)])
        elif idcu in area_prom.index:
            area = float(area_prom.loc[idcu])
        total = float(defo_tot.get((idcu, nombre), np.nan))
        pct = round(100.0 * total / area, 2) if area and pd.notna(total) else None

        # bloques temprano (fin<=2010) vs reciente (inicio>=2015), ambos 100% confiables
        temprano = d[d["ano_fin"] <= 2010]["hectareas_anuales"]
        reciente = d[d["ano_inicio"] >= 2015]["hectareas_anuales"]
        m_temp = round(float(temprano.mean()), 2) if len(temprano) else None
        m_rec = round(float(reciente.mean()), 2) if len(reciente) else None
        pendiente = None
        if len(d) >= 3:
            coef = np.polyfit(d["ano_medio"].values, d["hectareas_anuales"].values, 1)
            pendiente = round(float(coef[0]), 3)
        # clasificación robusta al hueco 2010-2015: reciente vs temprano
        tendencia = "sin_datos"
        ratio = None
        if m_temp is not None and m_rec is not None and m_temp > 0:
            ratio = round(m_rec / m_temp, 2)
            if ratio >= 1.25:
                tendencia = "empeora"
            elif ratio <= 0.80:
                tendencia = "mejora"
            else:
                tendencia = "estable"
        elif pendiente is not None:
            tendencia = ("empeora" if pendiente > 0.5 else
                         "mejora" if pendiente < -0.5 else "estable")

        regen = float(conf[(conf["idcu"] == idcu) &
                           (conf["clase"] == "Regeneración")]["hectareas"].sum())
        bosque_est = float(conf[(conf["periodo"] == ref_periodo) & (conf["idcu"] == idcu) &
                                (conf["clase"] == "Bosque Estable")]["hectareas"].sum())
        cuencas_json.append({
            "idcu": idcu, "cuenca": nombre,
            "area_monitoreada_ha_ref2022_2023": round(area, 1) if area else None,
            "bosque_estable_ha_2022_2023": round(bosque_est, 1) if bosque_est else None,
            "deforestacion_total_ha_confiable": round(total, 1) if pd.notna(total) else None,
            "deforestacion_pct_de_area": pct,
            "deforestacion_anual_temprana_00_10_ha": m_temp,
            "deforestacion_anual_reciente_15_23_ha": m_rec,
            "ratio_reciente_vs_temprano": ratio,
            "regeneracion_total_ha_confiable": round(regen, 1),
            "balance_neto_regen_menos_defo_ha": round(regen - total, 1) if pd.notna(total) else None,
            "tendencia": tendencia,
            "pendiente_ha_anual_por_ano": pendiente,
            "n_periodos_confiables_con_defo": int(len(d)),
        })

    rank_ha = sorted([c for c in cuencas_json if c["deforestacion_total_ha_confiable"] is not None],
                     key=lambda c: c["deforestacion_total_ha_confiable"], reverse=True)
    rank_pct = sorted([c for c in cuencas_json if c["deforestacion_pct_de_area"] is not None],
                      key=lambda c: c["deforestacion_pct_de_area"], reverse=True)

    # ---- [4/4] Cobertura y coherencia ----
    log("[4/4] Cobertura y coherencia con la serie regional ...")
    area_total_cuencas = float(area_ref.sum())
    juris_ha = None
    mgj = OUT.parent / "municipios.geojson"
    if mgj.exists():
        m = gpd.read_file(mgj)
        if not m.crs.is_projected:
            m = m.to_crs(METRIC)
        juris_ha = float(m.geometry.area.sum() / 10_000.0)
    cobertura_pct = round(100.0 * area_total_cuencas / juris_ha, 1) if juris_ha else None

    defo_total_conf = float(defo["hectareas"].sum())

    # deforestación por periodo (confiable) para ver la evolución temporal
    defo_por_periodo = (defo.groupby(["periodo", "ano_inicio", "ano_fin"])["hectareas"]
                        .sum().round(1).reset_index()
                        .sort_values("ano_inicio").to_dict(orient="records"))

    resumen = {
        "tema": "Cuencas hidrográficas — deforestación 2000-2024 (CORPOURABA)",
        "generado": pd.Timestamp.now(tz="UTC").isoformat(),
        "cuencas_total": len(CUENCAS),
        "cuencas": {str(k): v for k, v in CUENCAS.items()},
        "calidad_area": {
            "hallazgo": ("La columna 'AREA_ha'/'AREA HA' es en varios periodos el área "
                         "del polígono de cobertura ANTES de recortarlo contra la cuenca "
                         "(pre-clip): en 2022-2023 suma 2.766.595 ha vs 723.026 ha reales "
                         "de la geometría. El área solo se toma de geometría o de columnas "
                         "cuyo total coincide con la referencia."),
            "area_ref_geometrica_7cuencas_ha": round(area_ref_total, 1),
            "tolerancia_validacion_columna": TOL_AREA,
            "calidad_por_periodo": calidad_periodo,
        },
        "cobertura": {
            "nota": ("Las 7 cuencas cubren SOLO parte de la jurisdicción (franja de Urabá y "
                     "flancos noroccidentales). No es comparable con el total regional de 19 "
                     "municipios. Área de referencia: geometría 2022-2023."),
            "area_monitoreada_cuencas_ha": round(area_total_cuencas, 1),
            "area_jurisdiccion_ha_aprox": round(juris_ha, 1) if juris_ha else None,
            "cobertura_pct_de_jurisdiccion": cobertura_pct,
        },
        "periodos_con_datos": sorted(serie["periodo"].unique().tolist()),
        "periodos_area_confiable": sorted(conf["periodo"].unique().tolist()),
        "periodos_area_no_confiable": sorted(
            serie[~serie["area_confiable"]]["periodo"].unique().tolist()),
        "periodos_vacios_declarados": VACIOS,
        "fuentes_por_periodo": {p: f"{t}:{r.split('/')[-1]}" for p, (t, r) in FUENTES.items()},
        "coherencia": {
            "nota": ("Deforestación acumulada DENTRO de las cuencas, sumando solo los "
                     f"{n_periodos_conf} periodos con área confiable. Es menor que el total "
                     "regional (~46.041 ha, 2000-2024) porque las cuencas cubren una fracción "
                     "del territorio y faltan 5 periodos (2010-2015 y 2018-2019) sin capa, más "
                     "2021-2022 (área pre-clip) y 2023-2024 (sin área) excluidos."),
            "deforestacion_total_en_cuencas_ha_confiable": round(defo_total_conf, 1),
            "referencia_regional_2000_2024_ha": 46041,
            "deforestacion_por_periodo_confiable": defo_por_periodo,
        },
        "ranking_por_hectareas": [
            {"cuenca": c["cuenca"],
             "deforestacion_total_ha": c["deforestacion_total_ha_confiable"],
             "pct_de_area": c["deforestacion_pct_de_area"],
             "tendencia": c["tendencia"]}
            for c in rank_ha],
        "ranking_por_pct_area": [
            {"cuenca": c["cuenca"], "pct_de_area": c["deforestacion_pct_de_area"],
             "deforestacion_total_ha": c["deforestacion_total_ha_confiable"]}
            for c in rank_pct],
        "detalle_cuencas": cuencas_json,
        "log": QA,
    }
    (OUT / "cuencas_resumen.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    log("  cuencas_resumen.json escrito")

    # resumen impreso
    print("\n===== RANKING POR HECTÁREAS DEFORESTADAS (área confiable) =====")
    for c in rank_ha:
        print(f"  {c['cuenca']:16s} {c['deforestacion_total_ha_confiable']:>8.1f} ha  "
              f"({c['deforestacion_pct_de_area']}% de su área)  [{c['tendencia']}]")
    print("\n===== RANKING POR % DE ÁREA DEFORESTADA =====")
    for c in rank_pct:
        print(f"  {c['cuenca']:16s} {str(c['deforestacion_pct_de_area'])+'%':>7s}  "
              f"({c['deforestacion_total_ha_confiable']:.1f} ha)")
    print("\n===== TENDENCIA temprana (2000-2010) vs reciente (2015-2023) =====")
    for c in cuencas_json:
        print(f"  {c['cuenca']:16s} temprana={c['deforestacion_anual_temprana_00_10_ha']} "
              f"reciente={c['deforestacion_anual_reciente_15_23_ha']} "
              f"ratio={c['ratio_reciente_vs_temprano']} -> {c['tendencia']}")
    print(f"\nCobertura cuencas: {area_total_cuencas:,.0f} ha "
          f"= {cobertura_pct}% de la jurisdicción ({juris_ha:,.0f} ha)")
    print(f"Deforestación acumulada en cuencas (confiable): {defo_total_conf:,.0f} ha "
          f"en {n_periodos_conf} periodos (vs {46041:,} ha regional 2000-2024)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
