"""Pruebas del API del Observatorio (SPEC §9): pytest + httpx TestClient.

Se ejecutan contra el modo archivos leyendo data/processed real:
    cd backend && python -m pytest tests -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Permite `python -m pytest` desde backend/ o desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

PREFIJO = "/api/v1"
BOM_UTF8 = b"\xef\xbb\xbf"
PERIODOS_ESTIMADOS = {"2010-2012", "2015-2016", "2018-2019", "2023-2024"}


@pytest.fixture(scope="module")
def cliente():
    """TestClient con lifespan activo (carga del repositorio)."""
    with TestClient(app) as cliente_http:
        yield cliente_http


# ---------------------------------------------------------------- sistema
def test_salud(cliente):
    respuesta = cliente.get(f"{PREFIJO}/salud")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "ok"
    assert cuerpo["version"] == "1.0.0"
    assert cuerpo["modo_datos"] in ("archivos", "postgis")


def test_metadata(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/metadata").json()
    assert len(cuerpo["periodos"]) == 18
    assert len(cuerpo["municipios"]) == 19
    assert "nota_estimados" in cuerpo


def test_periodos(cliente):
    respuesta = cliente.get(f"{PREFIJO}/periodos")
    assert respuesta.status_code == 200
    periodos = respuesta.json()
    assert len(periodos) == 18
    primero = periodos[0]
    assert set(primero) == {"id", "ano_inicio", "ano_fin", "anos", "fuente", "tiene_hotspots"}
    por_id = {p["id"]: p for p in periodos}
    assert por_id["2002-2004"]["tiene_hotspots"] is True
    assert por_id["2000-2002"]["tiene_hotspots"] is False
    assert por_id["2000-2002"]["anos"] == 2
    assert sum(1 for p in periodos if p["tiene_hotspots"]) == 12


# ---------------------------------------------------------------- geo
def test_municipios(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/municipios").json()
    assert cuerpo["type"] == "FeatureCollection"
    assert len(cuerpo["features"]) == 19
    props = cuerpo["features"][0]["properties"]
    assert {"municipio_key", "codigo_dane", "nombre", "subregion", "area_municipio_ha", "centroide"} <= set(props)


def test_subregiones(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/subregiones").json()
    assert cuerpo["type"] == "FeatureCollection"
    assert len(cuerpo["features"]) == 5


def test_choropleth_valido(cliente):
    respuesta = cliente.get(f"{PREFIJO}/choropleth", params={"periodo": "2022-2023"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["periodo"] == "2022-2023"
    assert cuerpo["metrica"] == "hectareas"
    assert len(cuerpo["breaks"]) == 5
    assert cuerpo["max"] > 0
    assert "05045" in cuerpo["valores"]
    valor = cuerpo["valores"]["05045"]
    assert set(valor) == {"hectareas", "hectareas_anuales", "estimado", "municipio"}
    assert valor["municipio"] == "Apartadó"
    # breaks no decrecientes y el último es el máximo
    assert cuerpo["breaks"] == sorted(cuerpo["breaks"])
    assert cuerpo["breaks"][-1] == pytest.approx(cuerpo["max"], rel=0.01)


def test_choropleth_periodo_estimado_marcado(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/choropleth", params={"periodo": "2015-2016"}).json()
    assert all(v["estimado"] for v in cuerpo["valores"].values())


def test_choropleth_invalido(cliente):
    # Periodo inexistente → 404 con detalle
    respuesta = cliente.get(f"{PREFIJO}/choropleth", params={"periodo": "1999-2000"})
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()
    # Sin periodo → 422 (validación de FastAPI)
    assert cliente.get(f"{PREFIJO}/choropleth").status_code == 422
    # Métrica inválida → 422
    respuesta = cliente.get(
        f"{PREFIJO}/choropleth", params={"periodo": "2022-2023", "metrica": "otra"}
    )
    assert respuesta.status_code == 422


def test_hotspots_ok(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/hotspots/2022-2023").json()
    assert cuerpo["type"] == "FeatureCollection"
    assert len(cuerpo["features"]) == 396
    props = cuerpo["features"][0]["properties"]
    assert "ha" in props and "municipio" in props


def test_hotspots_404_con_disponibles(cliente):
    respuesta = cliente.get(f"{PREFIJO}/hotspots/2000-2002")
    assert respuesta.status_code == 404
    cuerpo = respuesta.json()
    assert "detail" in cuerpo
    assert len(cuerpo["disponibles"]) == 12
    assert "2022-2023" in cuerpo["disponibles"]


def test_capas(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/capas").json()
    unidades = {c["id"]: c["unidades"] for c in cuerpo["capas"]}
    # Las 4 capas núcleo del ETL deben existir siempre; la investigación
    # cartográfica añade capas oficiales adicionales (subconjunto, no igualdad).
    nucleo = {
        "areas_protegidas": 21,
        "resguardos": 39,
        "consejos": 7,
        "cuencas": 7,
    }
    assert nucleo.items() <= unidades.items()
    fc = cliente.get(f"{PREFIJO}/capas/areas_protegidas").json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 21
    assert cliente.get(f"{PREFIJO}/capas/no_existe").status_code == 404


# ---------------------------------------------------------------- series
def test_serie_por_municipio_con_y_sin_tildes(cliente):
    con_tilde = cliente.get(f"{PREFIJO}/serie", params={"municipio": "Apartadó"}).json()
    sin_tilde = cliente.get(f"{PREFIJO}/serie", params={"municipio": "apartado"}).json()
    por_codigo = cliente.get(f"{PREFIJO}/serie", params={"municipio": "05045"}).json()
    assert con_tilde["data"], "la serie de Apartadó no debe estar vacía"
    assert all(f["codigo_dane"] == "05045" for f in con_tilde["data"])
    assert all(f["clase"] == "Deforestación" for f in con_tilde["data"])
    assert con_tilde["total_ha"] == sin_tilde["total_ha"] == por_codigo["total_ha"]
    assert con_tilde["total_ha"] > 0


def test_serie_filtros_combinados(cliente):
    respuesta = cliente.get(
        f"{PREFIJO}/serie",
        params={"subregion": "Caribe", "desde": 2016, "hasta": 2018},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["data"]
    assert all(f["subregion"] == "Caribe" for f in cuerpo["data"])
    assert all(f["ano_inicio"] >= 2016 and f["ano_fin"] <= 2018 for f in cuerpo["data"])


def test_serie_sin_estimados(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/serie", params={"incluir_estimados": "false"}).json()
    assert all(not f["estimado"] for f in cuerpo["data"])
    assert not {f["periodo"] for f in cuerpo["data"]} & PERIODOS_ESTIMADOS
    assert cuerpo["nota"]  # avisa que se excluyeron los estimados


def test_serie_con_estimados_trae_nota(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/serie").json()
    assert cuerpo["nota"] is not None
    assert cuerpo["total_ha"] == pytest.approx(46041, abs=100)


def test_serie_parametros_invalidos(cliente):
    assert cliente.get(f"{PREFIJO}/serie", params={"clase": "Selva"}).status_code == 422
    assert cliente.get(f"{PREFIJO}/serie", params={"subregion": "Pacífico"}).status_code == 422
    assert cliente.get(f"{PREFIJO}/serie", params={"municipio": "Narnia"}).status_code == 404


def test_serie_regional(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/serie/regional").json()
    assert len(cuerpo["data"]) == 18
    estimados = {f["periodo"] for f in cuerpo["data"] if f["estimado"]}
    assert estimados == PERIODOS_ESTIMADOS
    sin_estimados = cliente.get(
        f"{PREFIJO}/serie/regional", params={"incluir_estimados": "false"}
    ).json()
    assert len(sin_estimados["data"]) == 14


# ---------------------------------------------------------------- analítica
def test_kpis_coherentes(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/kpis").json()
    assert cuerpo["total_deforestado_ha"] == pytest.approx(46041, abs=100)
    assert cuerpo["n_periodos"] == 18
    assert cuerpo["n_municipios"] == 19
    assert cuerpo["periodo_mas_critico"]["periodo"] == "2015-2016"
    assert cuerpo["periodo_mas_critico"]["estimado"] is True
    assert cuerpo["periodo_menor"]["periodo"] == "2020-2021"
    assert cuerpo["periodo_menor"]["hectareas"] == pytest.approx(1091, abs=10)
    assert 0 < cuerpo["pct_datos_estimados"] < 100
    assert cuerpo["promedio_anual_ha"] == pytest.approx(
        cuerpo["total_deforestado_ha"] / 24, rel=0.01
    )


def test_kpis_sin_estimados(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/kpis", params={"incluir_estimados": "false"}).json()
    assert cuerpo["n_periodos"] == 14
    assert cuerpo["periodo_mas_critico"]["periodo"] == "2016-2017"
    assert cuerpo["total_deforestado_ha"] < 46041


def test_ranking(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/ranking", params={"periodo": "2022-2023", "n": 5}).json()
    data = cuerpo["data"]
    assert len(data) == 5
    assert [f["posicion"] for f in data] == [1, 2, 3, 4, 5]
    hectareas = [f["hectareas"] for f in data]
    assert hectareas == sorted(hectareas, reverse=True)
    acumulado = cliente.get(f"{PREFIJO}/ranking").json()["data"]
    assert len(acumulado) == 10
    assert acumulado[0]["hectareas"] > acumulado[-1]["hectareas"]
    assert cliente.get(f"{PREFIJO}/ranking", params={"periodo": "1990-1992"}).status_code == 404


def test_comparacion(cliente):
    respuesta = cliente.get(f"{PREFIJO}/comparacion", params={"municipios": "05045,05837"})
    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert [m["codigo_dane"] for m in data] == ["05045", "05837"]
    assert data[0]["municipio"] == "Apartadó"
    assert data[0]["serie"]
    punto = data[0]["serie"][0]
    assert set(punto) == {"periodo", "hectareas_anuales", "estimado"}
    # Cantidad fuera de rango → 422
    assert cliente.get(f"{PREFIJO}/comparacion", params={"municipios": "05045"}).status_code == 422


def test_prediccion_regional(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/prediccion").json()
    assert cuerpo["metodo"] == "regresión lineal sobre tasa anual"
    assert cuerpo["advertencia"]
    assert len(cuerpo["historico"]) == 14  # por defecto excluye estimados
    assert len(cuerpo["prediccion"]) == 3
    anos = [p["ano"] for p in cuerpo["prediccion"]]
    assert anos == sorted(anos)
    for punto in cuerpo["prediccion"]:
        inferior, superior = punto["intervalo"]
        assert 0 <= inferior <= punto["hectareas_anuales_estimadas"] <= superior


def test_prediccion_municipal(cliente):
    cuerpo = cliente.get(
        f"{PREFIJO}/prediccion", params={"municipio": "Turbo", "horizonte": 5}
    ).json()
    assert len(cuerpo["prediccion"]) == 5
    assert cliente.get(f"{PREFIJO}/prediccion", params={"horizonte": 9}).status_code == 422


# ---------------------------------------------------------------- descargas
def test_descarga_csv_con_bom_y_metadatos(cliente):
    respuesta = cliente.get(f"{PREFIJO}/descargas/serie.csv", params={"municipio": "Turbo"})
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/csv")
    contenido = respuesta.content
    assert contenido.startswith(BOM_UTF8)
    texto = contenido.decode("utf-8-sig")
    assert texto.startswith("# ")
    assert "codigo_dane" in texto
    assert "Turbo" in texto


def test_descarga_xlsx(cliente):
    respuesta = cliente.get(f"{PREFIJO}/descargas/serie.xlsx")
    assert respuesta.status_code == 200
    assert respuesta.content[:2] == b"PK"  # firma ZIP de los .xlsx
    assert len(respuesta.content) > 1000
    assert "spreadsheetml" in respuesta.headers["content-type"]


def test_descarga_municipios_geojson(cliente):
    respuesta = cliente.get(f"{PREFIJO}/descargas/municipios.geojson")
    assert respuesta.status_code == 200
    assert b"FeatureCollection" in respuesta.content


def test_descarga_hotspots(cliente):
    respuesta = cliente.get(f"{PREFIJO}/descargas/hotspots/2022-2023.geojson")
    assert respuesta.status_code == 200
    assert b"FeatureCollection" in respuesta.content
    faltante = cliente.get(f"{PREFIJO}/descargas/hotspots/2000-2002.geojson")
    assert faltante.status_code == 404
    assert "disponibles" in faltante.json()


def test_descarga_paquete_zip(cliente):
    respuesta = cliente.get(f"{PREFIJO}/descargas/paquete.zip")
    assert respuesta.status_code == 200
    assert respuesta.content[:2] == b"PK"
    assert len(respuesta.content) > 10_000


# ------------------------------------------------------------- analisis


def test_analisis_catalogo_y_hallazgos(cliente):
    cuerpo = cliente.get(f"{PREFIJO}/analisis").json()
    ids_tablas = {t["id"] for t in cuerpo["tablas"]}
    assert "dinamica_bosque" in ids_tablas
    hal = cliente.get(f"{PREFIJO}/analisis/hallazgos").json()
    assert hal["total"] >= 10
    relevancias = [h["relevancia"] for h in hal["hallazgos"]]
    assert relevancias == sorted(relevancias, reverse=True)


def test_analisis_tabla_con_filtros(cliente):
    cuerpo = cliente.get(
        f"{PREFIJO}/analisis/tabla/dinamica_bosque", params={"municipio": "Turbo"}
    ).json()
    assert cuerpo["total_filas"] > 0
    assert all(f["municipio"] == "Turbo" for f in cuerpo["filas"])
    assert cliente.get(f"{PREFIJO}/analisis/tabla/no_existe").status_code == 404
    assert cliente.get(f"{PREFIJO}/analisis/tabla/..%2F..%2Fetc").status_code in (404, 422)


def test_analisis_geo_recurrencia(cliente):
    fc = cliente.get(f"{PREFIJO}/analisis/geo/recurrencia").json()
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 500
