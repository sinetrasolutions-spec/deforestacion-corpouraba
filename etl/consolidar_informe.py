# -*- coding: utf-8 -*-
"""Consolida todos los datos del análisis en un único JSON para el informe Word."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pandas as pd

PROC = Path(__file__).resolve().parent.parent / "data" / "processed"
AN = PROC / "analisis"
CART = AN / "cartografia"
OUT = Path(__file__).resolve().parent.parent / "entregables" / "informe_datos.json"


def load_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception as e:
        return {"_error": str(e)}


D = {}

# --- Serie regional (deforestación por periodo) ---
reg = pd.read_csv(PROC / "serie_regional.csv", encoding="utf-8-sig")
reg_d = reg[reg["clase"] == "Deforestación"].sort_values("ano_inicio")
D["serie_regional"] = reg_d[["periodo", "ano_inicio", "ano_fin", "hectareas",
                             "hectareas_anuales", "estimado"]].to_dict("records")
D["total_deforestacion_ha"] = round(float(reg_d["hectareas"].sum()), 1)
pico = reg_d.loc[reg_d["hectareas_anuales"].idxmax()]
minimo = reg_d.loc[reg_d["hectareas_anuales"].idxmin()]
D["pico"] = {"periodo": pico["periodo"], "ha": round(float(pico["hectareas"]), 1),
             "ha_anual": round(float(pico["hectareas_anuales"]), 1)}
D["minimo"] = {"periodo": minimo["periodo"], "ha": round(float(minimo["hectareas"]), 1),
               "ha_anual": round(float(minimo["hectareas_anuales"]), 1)}

# --- Serie municipal: ranking y por subregión ---
mun = pd.read_csv(PROC / "serie_municipal.csv", encoding="utf-8-sig", dtype={"codigo_dane": str})
md = mun[mun["clase"] == "Deforestación"]
rank = (md.groupby(["codigo_dane", "municipio", "subregion"])["hectareas"].sum()
        .reset_index().sort_values("hectareas", ascending=False))
rank["hectareas"] = rank["hectareas"].round(1)
D["ranking_municipios"] = rank.to_dict("records")
sub = (md.groupby("subregion")["hectareas"].sum().round(1)
       .sort_values(ascending=False).reset_index())
D["por_subregion"] = sub.to_dict("records")

# --- Clases (composición del cambio de cobertura) ---
por_clase = (mun.groupby("clase")["hectareas"].sum().round(0)).to_dict()
D["por_clase_total"] = {k: round(v, 0) for k, v in por_clase.items()}

# --- Resúmenes temáticos ---
D["dinamica"] = load_json(AN / "dinamica_resumen.json")
D["fragmentacion"] = load_json(AN / "fragmentacion_resumen.json")
D["areas_protegidas"] = load_json(AN / "areas_protegidas_resumen.json")
D["territorios_etnicos"] = load_json(AN / "territorios_etnicos_resumen.json")
D["cuencas"] = load_json(AN / "cuencas_resumen.json")
D["figuras"] = load_json(CART / "figuras_resumen.json")
D["pomcas"] = load_json(CART / "pomcas_resumen.json")
D["mineria"] = load_json(CART / "mineria_resumen.json")
D["territorios_oficiales"] = load_json(CART / "territorios_oficiales_resumen.json")

# --- Hallazgos ---
D["hallazgos"] = load_json(AN / "hallazgos.json")

# --- Metadata (fuentes por periodo, notas, QA) ---
meta = load_json(PROC / "metadata.json")
D["periodos_meta"] = meta.get("periodos", [])
D["municipios_meta"] = meta.get("municipios", [])
D["nota_estimados"] = meta.get("nota_estimados", "")
D["nota_2015_2016"] = meta.get("nota_2015_2016", "")
D["qa_calculos"] = meta.get("qa_calculos", [])
D["crs_origen"] = meta.get("crs_origen", "")
D["crs_salida"] = meta.get("crs_salida", "")

import math


def limpiar(o):
    """Reemplaza NaN/Inf por None (JSON estándar no los admite)."""
    if isinstance(o, float):
        return None if (math.isnan(o) or math.isinf(o)) else o
    if isinstance(o, dict):
        return {k: limpiar(v) for k, v in o.items()}
    if isinstance(o, list):
        return [limpiar(v) for v in o]
    return o


OUT.write_text(json.dumps(limpiar(D), ensure_ascii=False, indent=1, allow_nan=False),
               encoding="utf-8")
print("OK ->", OUT)
print("total:", D["total_deforestacion_ha"], "ha | pico:", D["pico"], "| min:", D["minimo"])
print("municipios ranking top3:", [(r["municipio"], r["hectareas"]) for r in D["ranking_municipios"][:3]])
print("subregiones:", [(r["subregion"], r["hectareas"]) for r in D["por_subregion"]])
print("clases:", D["por_clase_total"])
print("hallazgos:", len(D["hallazgos"]) if isinstance(D["hallazgos"], list) else "err")
