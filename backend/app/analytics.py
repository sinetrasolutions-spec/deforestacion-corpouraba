"""Cálculos analíticos: breaks, choropleth, ranking, KPIs y predicción."""
from __future__ import annotations

import numpy as np
import pandas as pd

METODO_PREDICCION = "regresión lineal sobre tasa anual"

ADVERTENCIA_PREDICCION = (
    "Proyección estadística de referencia (regresión lineal sobre la tasa anual "
    "histórica). No constituye una cifra oficial: la incertidumbre crece con el "
    "horizonte y la deforestación depende de factores no modelados."
)

ADVERTENCIA_SERIE_CORTA = (
    "Serie histórica insuficiente para ajustar una tendencia confiable; "
    "no se genera proyección."
)


def _redondear(valor: float, decimales: int = 2) -> float:
    """Redondeo defensivo a float nativo (evita np.float64 en las respuestas)."""
    return round(float(valor), decimales)


def calcular_breaks(valores: list[float]) -> list[float]:
    """Cortes de la escala choropleth.

    Quantiles [0.2, 0.4, 0.6, 0.8, 1.0] sobre los valores > 0 del periodo.
    Fallback si hay menos de 5 valores positivos: fracciones del máximo; y si
    no hay ningún positivo, escala unitaria fija para no romper la leyenda.
    """
    positivos = sorted(float(v) for v in valores if v is not None and v > 0)
    if len(positivos) >= 5:
        cuantiles = np.quantile(positivos, [0.2, 0.4, 0.6, 0.8, 1.0])
        return [_redondear(q) for q in cuantiles]
    if positivos:
        maximo = positivos[-1]
        return [_redondear(maximo * f) for f in (0.2, 0.4, 0.6, 0.8, 1.0)]
    return [1.0, 2.0, 3.0, 4.0, 5.0]


def construir_choropleth(df_periodo: pd.DataFrame, periodo: str, metrica: str) -> dict:
    """Valores por municipio + breaks para pintar el mapa (GET /choropleth).

    ``df_periodo``: filas de la clase Deforestación del periodo solicitado.
    """
    valores: dict[str, dict] = {}
    for fila in df_periodo.itertuples(index=False):
        valores[str(fila.codigo_dane)] = {
            "hectareas": _redondear(fila.hectareas),
            "hectareas_anuales": _redondear(fila.hectareas_anuales),
            "estimado": bool(fila.estimado),
            "municipio": fila.municipio,
        }
    medidas = [v[metrica] for v in valores.values()]
    return {
        "periodo": periodo,
        "metrica": metrica,
        "valores": valores,
        "breaks": calcular_breaks(medidas),
        "max": _redondear(max(medidas)) if medidas else 0.0,
    }


def calcular_ranking(
    df_defo: pd.DataFrame,
    periodo: str | None = None,
    n: int = 10,
    metrica: str = "hectareas",
) -> list[dict]:
    """Top-n de municipios por deforestación (GET /ranking).

    Sin ``periodo`` se acumula todo el rango 2000–2024: `hectareas` es la suma
    y `hectareas_anuales` la suma dividida por los años cubiertos.
    """
    if periodo is not None:
        base = df_defo[df_defo["periodo"] == periodo]
        tabla = base[
            ["codigo_dane", "municipio", "subregion", "hectareas", "hectareas_anuales", "estimado"]
        ].copy()
    else:
        # Años cubiertos por los periodos presentes (24 para la serie completa)
        periodos_unicos = df_defo.drop_duplicates("periodo")
        total_anos = int((periodos_unicos["ano_fin"] - periodos_unicos["ano_inicio"]).sum()) or 1
        tabla = (
            df_defo.groupby(["codigo_dane", "municipio", "subregion"], as_index=False)
            .agg(hectareas=("hectareas", "sum"), estimado=("estimado", "max"))
        )
        tabla["hectareas_anuales"] = tabla["hectareas"] / total_anos

    tabla = tabla.sort_values(metrica, ascending=False).head(n)
    resultado = []
    for posicion, fila in enumerate(tabla.itertuples(index=False), start=1):
        resultado.append(
            {
                "codigo_dane": str(fila.codigo_dane),
                "municipio": fila.municipio,
                "subregion": fila.subregion,
                "hectareas": _redondear(fila.hectareas),
                "hectareas_anuales": _redondear(fila.hectareas_anuales),
                "estimado": bool(fila.estimado),
                "posicion": posicion,
            }
        )
    return resultado


def calcular_kpis(df_defo: pd.DataFrame, incluir_estimados: bool = True) -> dict:
    """KPIs regionales de la clase Deforestación (GET /kpis).

    ``pct_datos_estimados`` se calcula siempre sobre la serie completa de
    Deforestación (independiente del filtro) para reportar transparencia.
    """
    base = df_defo if incluir_estimados else df_defo[~df_defo["estimado"]]

    por_periodo = (
        base.groupby(["periodo", "ano_inicio", "ano_fin"], as_index=False)
        .agg(hectareas=("hectareas", "sum"), estimado=("estimado", "max"))
    )
    total = float(base["hectareas"].sum())
    anos_cubiertos = int((por_periodo["ano_fin"] - por_periodo["ano_inicio"]).sum()) or 1

    critico = por_periodo.loc[por_periodo["hectareas"].idxmax()]
    menor = por_periodo.loc[por_periodo["hectareas"].idxmin()]

    por_municipio = base.groupby(["codigo_dane", "municipio"], as_index=False).agg(
        hectareas=("hectareas", "sum")
    )
    afectado = por_municipio.loc[por_municipio["hectareas"].idxmax()]

    return {
        "total_deforestado_ha": _redondear(total),
        "promedio_anual_ha": _redondear(total / anos_cubiertos),
        "periodo_mas_critico": {
            "periodo": critico["periodo"],
            "hectareas": _redondear(critico["hectareas"]),
            "estimado": bool(critico["estimado"]),
        },
        "municipio_mas_afectado": {
            "municipio": afectado["municipio"],
            "codigo_dane": str(afectado["codigo_dane"]),
            "hectareas": _redondear(afectado["hectareas"]),
        },
        "periodo_menor": {
            "periodo": menor["periodo"],
            "hectareas": _redondear(menor["hectareas"]),
            "estimado": bool(menor["estimado"]),
        },
        "n_periodos": int(por_periodo.shape[0]),
        "n_municipios": int(df_defo["codigo_dane"].nunique()),
        "pct_datos_estimados": _redondear(100.0 * float(df_defo["estimado"].mean()), 1),
    }


def calcular_prediccion(
    por_periodo: pd.DataFrame,
    horizonte: int = 3,
    incluir_estimados: bool = False,
) -> dict:
    """Proyección de la tasa anual (GET /prediccion).

    Ajusta ``numpy.polyfit`` de grado 1 sobre (punto medio del periodo,
    ha/año); intervalo = ±1.96·σ de los residuales; valores recortados a ≥ 0.
    ``por_periodo`` requiere columnas: periodo, ano_inicio, ano_fin,
    hectareas_anuales, estimado.
    """
    base = por_periodo if incluir_estimados else por_periodo[~por_periodo["estimado"]]
    base = base.sort_values("ano_inicio").reset_index(drop=True)

    historico = [
        {"periodo": fila.periodo, "hectareas_anuales": _redondear(fila.hectareas_anuales)}
        for fila in base.itertuples(index=False)
    ]

    if len(base) < 3:
        return {
            "historico": historico,
            "prediccion": [],
            "metodo": METODO_PREDICCION,
            "advertencia": ADVERTENCIA_SERIE_CORTA,
        }

    x = ((base["ano_inicio"] + base["ano_fin"]) / 2.0).to_numpy(dtype=float)
    y = base["hectareas_anuales"].to_numpy(dtype=float)
    coeficientes = np.polyfit(x, y, 1)
    residuales = y - np.polyval(coeficientes, x)
    sigma = float(np.std(residuales))

    ultimo_ano = int(base["ano_fin"].max())
    prediccion = []
    for paso in range(1, horizonte + 1):
        ano = ultimo_ano + paso
        valor = max(float(np.polyval(coeficientes, ano)), 0.0)
        inferior = max(valor - 1.96 * sigma, 0.0)
        superior = valor + 1.96 * sigma
        prediccion.append(
            {
                "ano": ano,
                "hectareas_anuales_estimadas": _redondear(valor),
                "intervalo": [_redondear(inferior), _redondear(superior)],
            }
        )

    return {
        "historico": historico,
        "prediccion": prediccion,
        "metodo": METODO_PREDICCION,
        "advertencia": ADVERTENCIA_PREDICCION,
    }
