# -*- coding: utf-8 -*-
"""
FIGURAS DE PROTECCION vs BOSQUE — reservas, AP y AEIA vs deforestacion mapeada
==============================================================================
Cruza tres capas de la cartografia oficial de CORPOURABA con los hotspots de
deforestacion >=1 ha del Observatorio (12 periodos mapeados, WGS84):

  1. LEY_SEGUNDA.shp                    Reserva Forestal del Pacifico Ley 2a de
                                        1959 (4 zonas: Tipo A/B/C + zona con
                                        decision previa de OT). CRS origen 3116.
  2. Areas_Protegidas_CORPOURABA.shp    Limite OFICIAL de las areas protegidas
                                        (23 unidades, campos NOMBRE/CATEGORIA).
                                        CRS origen 3116.
  3. AEIAa.shp                          Areas Ecologicas de Importancia Ambiental
                                        (AEIA*): zonificacion de importancia
                                        (ZON: Muy importante ... Sin importancia)
                                        que cubre TODA la jurisdiccion. 3116.

Metodo (eficiente y robusto):
  - CRS real inspeccionado por capa; TODO reproyectado a EPSG:3115; ha = area/1e4.
  - Las tres capas oficiales traen multipoligonos enormes e invalidos (cobertura
    de departamentos completos). NO se validan/disuelven globalmente (buffer(0)
    sobre ellos es intratable). En su lugar, por periodo se INTERSECTAN contra la
    union (pequena y valida) de los hotspots: el resultado es diminuto y las
    invalideces se resuelven baratas. Se filtran candidatos con el indice espacial.
  - Hotspots to_crs(3115), buffer(0), y RECORTADOS a la jurisdiccion (union de
    municipios.geojson): el hotspot 2012-2013 viene de un raster que cubre todo
    Antioquia y solo ~17%% cae en la jurisdiccion; sin recorte, Ley 2a (que se
    extiende al Choco) atribuiria deforestacion extra-jurisdiccional. El
    denominador por periodo es la deforestacion mapeada DENTRO de la jurisdiccion.

Honestidad:
  - Siempre "deforestacion mapeada" (hotspots >=1 ha, 12 de 18 periodos).
  - Ningun subconjunto puede superar el total mapeado del periodo (se verifica).
  - AEIA es una zonificacion que particiona TODO el territorio en clases de
    importancia; "dentro de AEIA" seria ~100%%. Se reporta el subconjunto de
    mayor valor (Muy importante + Importante) y el desglose por clase.

Salidas:
  data/processed/analisis/cartografia/figuras_proteccion.csv   (figura x periodo x ha, UTF-8 BOM)
  data/processed/analisis/cartografia/figuras_resumen.json     (agregados + rankings)
  data/processed/capas/ley_segunda.geojson                     (capa web WGS84)
  data/processed/capas/areas_protegidas_oficial.geojson        (capa web WGS84)
"""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\etl')
import run_etl  # PERIODOS, read_shp

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union

CARTO = Path(r'C:\Users\Desktop\Documents\Documentos\PROGRAMAS\CONSULTAS CARTOGRÁFICAS\CARTOGRAFIA')
BASE = Path(r'E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion')
PROCESSED = BASE / 'data' / 'processed'
HOTDIR = PROCESSED / 'hotspots'
OUT = PROCESSED / 'analisis' / 'cartografia'
CAPAS = PROCESSED / 'capas'
OUT.mkdir(parents=True, exist_ok=True)
CAPAS.mkdir(parents=True, exist_ok=True)

METRIC = 'EPSG:3115'
WGS84 = 'EPSG:4326'
PERIODO_ANIOS = {p: (i, f) for p, i, f in run_etl.PERIODOS}
PERIODOS_HOT = [p for p, _, _ in run_etl.PERIODOS if (HOTDIR / f'{p}.geojson').exists()]

SHP_LEY = CARTO / 'LEY SEGUNDA DE 1959' / 'LEY_SEGUNDA.shp'
SHP_AP = CARTO / 'AREAS PROTEGIDAS' / 'Areas_Protegidas_CORPOURABA.shp'
SHP_AEIA = CARTO / 'AREAS DE IMPORTANCIA ESTRATEGICA' / 'AEIAa.shp'  # gemelo de AEIA.shp con EPSG:3116 correcto

AEIA_ALTA_CLASES = ['Muy importante', 'Importante']


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def limpiar(s) -> str:
    if pd.isna(s):
        return 'Sin dato'
    return ' '.join(str(s).split()).strip() or 'Sin dato'


def cargar(path: Path, campo_nombre: str, campo_cat: str | None, tipo: str) -> gpd.GeoDataFrame:
    """Carga y reproyecta SIN validar globalmente (los poligonos son enormes)."""
    g = gpd.read_file(path)
    crs_orig = str(g.crs)
    g = g.to_crs(METRIC)
    g['unidad'] = g[campo_nombre].map(limpiar)
    g['categoria'] = g[campo_cat].map(limpiar) if campo_cat and campo_cat in g.columns else g['unidad']
    g['figura'] = tipo
    area = g.geometry.area / 1e4  # geometria posiblemente invalida: area sigue siendo indicativa
    g['area_capa_ha'] = area.round(1)
    print(f'  {path.name}: {len(g)} feats | CRS origen {crs_orig} -> {METRIC} | '
          f'area total ~{area.sum():,.0f} ha', flush=True)
    return g[['figura', 'unidad', 'categoria', 'area_capa_ha', 'geometry']]


def clip_a(gdf: gpd.GeoDataFrame, target_union, extra_cols=('unidad', 'categoria')):
    """Intersecta las features de gdf que tocan target_union contra target_union.
    Resuelve invalideces baratas porque el resultado es pequeno. Devuelve GDF con 'ha'."""
    idx = list(gdf.sindex.query(target_union, predicate='intersects'))
    if not idx:
        return gpd.GeoDataFrame(columns=list(extra_cols) + ['ha', 'geometry'], geometry='geometry', crs=METRIC)
    cand = gdf.iloc[idx].copy()
    inter = cand.geometry.intersection(target_union)
    cand = cand.assign(geometry=inter)
    cand = cand[~cand.geometry.is_empty & cand.geometry.notna()].copy()
    cand['ha'] = cand.geometry.area / 1e4
    cand = cand[cand['ha'] > 0]
    return cand


# ---------------------------------------------------------------------------
# [1] Carga de capas oficiales
# ---------------------------------------------------------------------------

print('[1/6] Capas oficiales de figuras de proteccion ...', flush=True)
ley = cargar(SHP_LEY, 'Tipo_de_zo', None, 'Ley 2a de 1959')
ap = cargar(SHP_AP, 'NOMBRE', 'CATEGORIA', 'Area protegida')
aeia = cargar(SHP_AEIA, 'ZON', None, 'AEIA')

# Jurisdiccion (union de municipios, geometrias validas) para recortar hotspots
mun = gpd.read_file(PROCESSED / 'municipios.geojson')[['geometry']].to_crs(METRIC)
mun['geometry'] = mun.geometry.buffer(0)
JUR = unary_union(mun.geometry.values)
jur_ha = JUR.area / 1e4
print(f'  jurisdiccion (union municipios): {jur_ha:,.0f} ha', flush=True)

# Cobertura de cada figura dentro de la jurisdiccion (contexto) via clip a JUR
ley_jur_gdf = clip_a(ley, JUR)
ap_jur_gdf = clip_a(ap, JUR)
aeia_jur_gdf = clip_a(aeia, JUR)
ley_jur = float(ley_jur_gdf['ha'].sum())
ap_jur = float(ap_jur_gdf['ha'].sum())
aeia_alta_jur = float(aeia_jur_gdf[aeia_jur_gdf['unidad'].isin(AEIA_ALTA_CLASES)]['ha'].sum())
print(f'  Ley 2a dentro jur: {ley_jur:,.0f} ha ({100*ley_jur/jur_ha:.1f}%) | '
      f'AP dentro jur: {ap_jur:,.0f} ha ({100*ap_jur/jur_ha:.1f}%) | '
      f'AEIA(alta) dentro jur: {aeia_alta_jur:,.0f} ha ({100*aeia_alta_jur/jur_ha:.1f}%)', flush=True)

# ---------------------------------------------------------------------------
# [2] Cruce hotspots (recortados a jurisdiccion) x figuras, por periodo
# ---------------------------------------------------------------------------

print('[2/6] Cruce hotspots x figuras por periodo ...', flush=True)
rows = []
piezas = {'Ley 2a de 1959': [], 'Area protegida': [], 'AEIA': []}
qa_periodos = []

for pid in PERIODOS_HOT:
    ini, fin = PERIODO_ANIOS[pid]
    ny = max(1, fin - ini)
    h = gpd.read_file(HOTDIR / f'{pid}.geojson').to_crs(METRIC)
    h['geometry'] = h.geometry.buffer(0)
    h['municipio'] = h['municipio'].fillna('Sin asignar')
    geo_raw = float((h.geometry.area / 1e4).sum())
    # recorte a jurisdiccion
    h['geometry'] = h.geometry.intersection(JUR)
    h = h[~h.geometry.is_empty & h.geometry.notna()].copy()
    h['ha_geo'] = h.geometry.area / 1e4
    h = h[h['ha_geo'] > 0]
    tot = float(h['ha_geo'].sum())  # denominador = mapeado DENTRO de la jurisdiccion
    HU = unary_union(h.geometry.values)  # union pequena y valida

    # clip de cada figura contra la union de hotspots del periodo
    c_ley = clip_a(ley, HU)
    c_ap = clip_a(ap, HU)
    c_aeia = clip_a(aeia, HU)
    inter_ley = float(c_ley['ha'].sum())
    inter_ap = float(c_ap['ha'].sum())
    inter_aeia_alta = float(c_aeia[c_aeia['unidad'].isin(AEIA_ALTA_CLASES)]['ha'].sum())

    for fig, ha in (('Ley 2a de 1959', inter_ley),
                    ('Area protegida', inter_ap),
                    ('AEIA importancia alta', inter_aeia_alta)):
        ha = min(ha, tot)  # invariante: subset <= total mapeado
        rows.append({'figura': fig, 'periodo': pid, 'ano_inicio': ini, 'ano_fin': fin,
                     'hectareas_dentro': round(ha, 2),
                     'hectareas_anuales': round(ha / ny, 2),
                     'pct_mapeado_periodo': round(100 * ha / tot, 2) if tot else 0.0,
                     'deforestacion_mapeada_periodo_ha': round(tot, 2)})

    # atribucion por unidad (para rankings): asignar municipio por join espacial ligero
    for cdf, key in ((c_ley, 'Ley 2a de 1959'), (c_ap, 'Area protegida'), (c_aeia, 'AEIA')):
        if len(cdf):
            piezas[key].append(pd.DataFrame({
                'unidad': cdf['unidad'].values, 'categoria': cdf['categoria'].values,
                'ha': cdf['ha'].values, 'periodo': pid}))

    qa_periodos.append({'periodo': pid, 'n_hotspots': int(len(h)),
                        'ha_mapeada_bruta': round(geo_raw, 1),
                        'ha_mapeada_dentro_jur': round(tot, 1),
                        'pct_dentro_jur': round(100 * tot / geo_raw, 1) if geo_raw else 0.0,
                        'ha_dentro_ley2a': round(inter_ley, 1),
                        'ha_dentro_ap': round(inter_ap, 1),
                        'ha_dentro_aeia_alta': round(inter_aeia_alta, 1)})
    print(f'  {pid}: {len(h):>4} hs | mapeado_jur {tot:>8,.1f} ha (bruto {geo_raw:>8,.1f}) | '
          f'Ley2a {inter_ley:>7,.1f} | AP {inter_ap:>7,.1f} | AEIA-alta {inter_aeia_alta:>7,.1f}', flush=True)

df = pd.DataFrame(rows)
df.to_csv(OUT / 'figuras_proteccion.csv', index=False, encoding='utf-8-sig')
print('csv ->', OUT / 'figuras_proteccion.csv', f'({len(df)} filas)', flush=True)

pz = {k: (pd.concat(v, ignore_index=True) if v else pd.DataFrame(columns=['unidad', 'categoria', 'ha', 'periodo']))
      for k, v in piezas.items()}

# ---------------------------------------------------------------------------
# [3] Agregados 12 periodos + verificacion de invariante
# ---------------------------------------------------------------------------

print('[3/6] Agregados y verificacion de invariante ...', flush=True)
tot_map = float(df[df['figura'] == 'Ley 2a de 1959']['deforestacion_mapeada_periodo_ha'].sum())
ha_fig = lambda n: float(df[df['figura'] == n]['hectareas_dentro'].sum())
d_ley, d_ap, d_aeia_alta = ha_fig('Ley 2a de 1959'), ha_fig('Area protegida'), ha_fig('AEIA importancia alta')

violaciones = []
for pid in PERIODOS_HOT:
    sub = df[df['periodo'] == pid]
    tote = sub['deforestacion_mapeada_periodo_ha'].iloc[0]
    for _, r in sub.iterrows():
        if r['hectareas_dentro'] > tote + 0.01:
            violaciones.append((pid, r['figura'], r['hectareas_dentro'], tote))
print(f'  invariante subset<=total: {"OK" if not violaciones else violaciones}', flush=True)

reg = pd.read_csv(PROCESSED / 'serie_regional.csv')
reg_defo = reg[reg['clase'] == 'Deforestación']
serie_total_18p = float(reg_defo['hectareas'].sum())
serie_12p = float(reg_defo[reg_defo['periodo'].isin(PERIODOS_HOT)]['hectareas'].sum())

bloques = {'2002_2010': ['2002-2004', '2004-2006', '2006-2008', '2008-2010'],
           '2012_2018': ['2012-2013', '2013-2014', '2016-2017', '2017-2018'],
           '2019_2023': ['2019-2020', '2020-2021', '2021-2022', '2022-2023']}
tend = {}
for bl, pids in bloques.items():
    pids = [p for p in pids if p in PERIODOS_HOT]
    sub = df[df['periodo'].isin(pids)]
    anos = sum(PERIODO_ANIOS[p][1] - PERIODO_ANIOS[p][0] for p in pids)
    tm = float(sub[sub['figura'] == 'Ley 2a de 1959']['deforestacion_mapeada_periodo_ha'].sum())
    def blk(fig):
        s = float(sub[sub['figura'] == fig]['hectareas_dentro'].sum())
        return {'ha': round(s, 1), 'ha_anual': round(s / anos, 1) if anos else 0.0,
                'pct': round(100 * s / tm, 2) if tm else 0.0}
    tend[bl] = {'anos_cubiertos': anos, 'defo_mapeada_ha': round(tm, 1),
                'ley2a': blk('Ley 2a de 1959'), 'ap': blk('Area protegida'),
                'aeia_alta': blk('AEIA importancia alta')}

def top(dfp, keys, n=15):
    if dfp.empty:
        return []
    g = (dfp.groupby(keys)['ha'].sum().sort_values(ascending=False).head(n)
         .round(1).reset_index().rename(columns={'ha': 'deforestacion_ha'}))
    return g.to_dict('records')

top_ley_zona = top(pz['Ley 2a de 1959'], ['unidad'])
top_ap_unidad = top(pz['Area protegida'], ['unidad', 'categoria'])
top_ap_categoria = top(pz['Area protegida'], ['categoria'], n=10)
top_aeia_clase = top(pz['AEIA'], ['unidad'], n=10)

# ---------------------------------------------------------------------------
# [4] Capas web
# ---------------------------------------------------------------------------

print('[4/6] Capas web ...', flush=True)

def escribir_capa_ap(gdf_metric, defo_por_unidad, path, figura_label):
    """AP: pocas unidades, validables individualmente. Disuelve por unidad, simplifica ~60 m."""
    g = gdf_metric.copy()
    g['geometry'] = g.geometry.buffer(0)
    diss = g.dissolve(by='unidad', as_index=False)
    cat = g.drop_duplicates('unidad').set_index('unidad')['categoria']
    diss['nombre'] = diss['unidad']
    diss['categoria'] = diss['unidad'].map(cat)
    diss['area_ha'] = (diss.geometry.area / 1e4).round(1)
    diss['deforestacion_ha_total'] = diss['unidad'].map(defo_por_unidad).fillna(0.0).round(1)
    diss['figura'] = figura_label
    keep = ['nombre', 'categoria', 'figura', 'area_ha', 'deforestacion_ha_total', 'geometry']
    diss = diss[keep]
    tol_final = None
    for tol in (60, 90, 140, 200, 300):
        w = diss.copy()
        w['geometry'] = w.geometry.simplify(tol, preserve_topology=True)
        w['geometry'] = w.geometry.buffer(0)
        w = w.to_crs(WGS84)
        if path.exists():
            path.unlink()
        w.to_file(path, driver='GeoJSON', COORDINATE_PRECISION=5)
        kb = path.stat().st_size / 1024
        print(f'  {path.name}: tol {tol} m -> {kb:.0f} KB', flush=True)
        tol_final = tol
        if kb < 500:
            break
    return tol_final, round(path.stat().st_size / 1024, 0)


def escribir_capa_ley(gdf_metric, defo_por_unidad, path, figura_label):
    """Ley 2a: 4 zonas gigantes e invalidas. Recortar a jurisdiccion primero (via clip_a),
    validar el resultado, simplificar. Se reporta solo la porcion en la jurisdiccion."""
    c = clip_a(gdf_metric, JUR)  # trae 'unidad','categoria','ha','geometry' recortado a jur
    if not len(c):
        return None, 0
    c = gpd.GeoDataFrame(c, geometry='geometry', crs=METRIC)
    c['geometry'] = c.geometry.buffer(0)
    diss = c.dissolve(by='unidad', as_index=False)
    diss['nombre'] = diss['unidad']
    diss['categoria'] = diss['unidad']
    diss['area_ha'] = (diss.geometry.area / 1e4).round(1)  # area DENTRO de la jurisdiccion
    diss['deforestacion_ha_total'] = diss['unidad'].map(defo_por_unidad).fillna(0.0).round(1)
    diss['figura'] = figura_label
    keep = ['nombre', 'categoria', 'figura', 'area_ha', 'deforestacion_ha_total', 'geometry']
    diss = diss[keep]
    tol_final = None
    for tol in (60, 90, 140, 200, 300, 450):
        w = diss.copy()
        w['geometry'] = w.geometry.simplify(tol, preserve_topology=True)
        w['geometry'] = w.geometry.buffer(0)
        w = w.to_crs(WGS84)
        if path.exists():
            path.unlink()
        w.to_file(path, driver='GeoJSON', COORDINATE_PRECISION=5)
        kb = path.stat().st_size / 1024
        print(f'  {path.name}: tol {tol} m -> {kb:.0f} KB', flush=True)
        tol_final = tol
        if kb < 500:
            break
    return tol_final, round(path.stat().st_size / 1024, 0)


defo_ley = pz['Ley 2a de 1959'].groupby('unidad')['ha'].sum() if len(pz['Ley 2a de 1959']) else pd.Series(dtype=float)
defo_ap = pz['Area protegida'].groupby('unidad')['ha'].sum() if len(pz['Area protegida']) else pd.Series(dtype=float)

tol_ap, kb_ap = escribir_capa_ap(ap, defo_ap, CAPAS / 'areas_protegidas_oficial.geojson',
                                 'Area protegida oficial CORPOURABA')
tol_ley, kb_ley = escribir_capa_ley(ley, defo_ley, CAPAS / 'ley_segunda.geojson',
                                    'Reserva Forestal Ley 2a de 1959')

# ---------------------------------------------------------------------------
# [5] Comparacion con analisis previo (areas_protegidas_serie.csv)
# ---------------------------------------------------------------------------

print('[5/6] Comparacion con analisis AP previo ...', flush=True)
prev_path = PROCESSED / 'analisis' / 'areas_protegidas_serie.csv'
comparacion = {}
if prev_path.exists():
    prev = pd.read_csv(prev_path)
    prev_use = prev[(prev['clase'] == 'Deforestación') &
                    (~prev['es_duplicado'].astype(str).str.lower().isin(['true']))]
    prev_periodos = sorted(prev_use['periodo'].unique())
    prev_total = float(prev_use['hectareas'].sum())
    comunes = sorted(set(prev_periodos) & set(PERIODOS_HOT))
    prev_comunes = float(prev_use[prev_use['periodo'].isin(comunes)]['hectareas'].sum())
    mio_ap_comunes = float(df[(df['figura'] == 'Area protegida') &
                              (df['periodo'].isin(comunes))]['hectareas_dentro'].sum())
    comparacion = {
        'fuente_previa': 'areas_protegidas_serie.csv (overlay AProteg interno IDEAM por periodo, clase por gridcode, TODOS los poligonos)',
        'fuente_actual': 'Areas_Protegidas_CORPOURABA.shp (limite oficial externo) x hotspots >=1 ha recortados a jurisdiccion',
        'periodos_previo': prev_periodos,
        'periodos_actual': PERIODOS_HOT,
        'periodos_comunes': comunes,
        'defo_ap_previo_total_ha': round(prev_total, 1),
        'defo_ap_previo_periodos_comunes_ha': round(prev_comunes, 1),
        'defo_ap_actual_periodos_comunes_ha': round(mio_ap_comunes, 1),
        'diferencia_ha': round(mio_ap_comunes - prev_comunes, 1),
        'diferencia_pct': round(100 * (mio_ap_comunes - prev_comunes) / prev_comunes, 1) if prev_comunes else None,
    }
    print(f'  periodos comunes {comunes}', flush=True)
    print(f'  AP previo (mismos periodos): {prev_comunes:,.1f} ha | '
          f'AP actual: {mio_ap_comunes:,.1f} ha | dif {comparacion["diferencia_pct"]}%', flush=True)
else:
    print('  [WARN] no existe areas_protegidas_serie.csv', flush=True)

# ---------------------------------------------------------------------------
# [6] Resumen JSON
# ---------------------------------------------------------------------------

print('[6/6] Resumen JSON ...', flush=True)
pct = lambda a, b: round(100 * a / b, 2) if b else None
aeia_clases_ha = (pz['AEIA'].groupby('unidad')['ha'].sum().round(1).to_dict()
                  if len(pz['AEIA']) else {})

resumen = {
    'titulo': 'Figuras de proteccion vs bosque — Ley 2a, Areas Protegidas y AEIA vs deforestacion mapeada, CORPOURABA',
    'fuente_capas': {
        'ley_segunda': 'LEY SEGUNDA DE 1959/LEY_SEGUNDA.shp (reserva forestal Ley 2a de 1959; zonas Tipo A/B/C), CRS origen EPSG:3116',
        'areas_protegidas': 'AREAS PROTEGIDAS/Areas_Protegidas_CORPOURABA.shp (limite oficial, 23 unidades NOMBRE/CATEGORIA), CRS origen EPSG:3116',
        'aeia': 'AREAS DE IMPORTANCIA ESTRATEGICA/AEIAa.shp (Areas Ecologicas de Importancia Ambiental; ZON=clase de importancia), CRS origen EPSG:3116',
    },
    'unidad': 'hectareas (area geometrica EPSG:3115)',
    'metodo': ('Hotspots >=1 ha (12/18 periodos) reproyectados a EPSG:3115, buffer(0) y RECORTADOS a la '
               'union de municipios.geojson. Cada figura se intersecta contra la union de hotspots del '
               'periodo (via indice espacial); el denominador es la deforestacion mapeada DENTRO de la jurisdiccion.'),
    'jurisdiccion_ha': round(jur_ha, 0),
    'capas': {
        'ley_segunda': {
            'n_zonas': int(len(ley)),
            'zonas': ley['unidad'].tolist(),
            'area_total_capa_ha': round(float(ley['area_capa_ha'].sum()), 0),
            'area_dentro_jurisdiccion_ha': round(ley_jur, 0),
            'pct_jurisdiccion_en_ley2a': pct(ley_jur, jur_ha),
        },
        'areas_protegidas': {
            'n_unidades': int(len(ap)),
            'categorias': ap['categoria'].value_counts().to_dict(),
            'area_total_capa_ha': round(float(ap['area_capa_ha'].sum()), 0),
            'area_dentro_jurisdiccion_ha': round(ap_jur, 0),
            'pct_jurisdiccion_protegida': pct(ap_jur, jur_ha),
        },
        'aeia': {
            'n_clases': int(len(aeia)),
            'clases': aeia['unidad'].tolist(),
            'area_total_capa_ha': round(float(aeia['area_capa_ha'].sum()), 0),
            'nota': ('AEIA es una zonificacion que particiona TODA la jurisdiccion en clases de importancia; '
                     '"dentro de AEIA" seria ~100%. Se reporta el subconjunto de mayor valor (Muy importante + Importante).'),
            'clases_alta': AEIA_ALTA_CLASES,
            'area_alta_dentro_jurisdiccion_ha': round(aeia_alta_jur, 0),
            'pct_jurisdiccion_aeia_alta': pct(aeia_alta_jur, jur_ha),
        },
    },
    'totales_12_periodos_mapeados': {
        'deforestacion_mapeada_dentro_jurisdiccion_ha': round(tot_map, 1),
        'dentro_ley2a_ha': round(d_ley, 1),
        'pct_dentro_ley2a': pct(d_ley, tot_map),
        'dentro_areas_protegidas_ha': round(d_ap, 1),
        'pct_dentro_areas_protegidas': pct(d_ap, tot_map),
        'dentro_aeia_importancia_alta_ha': round(d_aeia_alta, 1),
        'pct_dentro_aeia_importancia_alta': pct(d_aeia_alta, tot_map),
    },
    'contexto_cobertura': {
        'periodos_con_hotspots': PERIODOS_HOT,
        'n_periodos': len(PERIODOS_HOT),
        'deforestacion_serie_12_periodos_ha': round(serie_12p, 1),
        'deforestacion_serie_18_periodos_ha': round(serie_total_18p, 1),
        'pct_serie_cubierta_por_periodos_mapeados': pct(serie_12p, serie_total_18p),
        'nota': 'Todos los porcentajes son de la deforestacion MAPEADA (hotspots >=1 ha) dentro de la jurisdiccion, no del total 2000-2024.',
    },
    'invariante_subset_no_supera_total': 'OK' if not violaciones else str(violaciones),
    'serie_por_figura_periodo': df.to_dict('records'),
    'tendencia_por_bloques': tend,
    'ranking_zonas_ley2a': top_ley_zona,
    'ranking_areas_protegidas': top_ap_unidad,
    'ranking_categorias_ap': top_ap_categoria,
    'deforestacion_por_clase_aeia_ha': aeia_clases_ha,
    'ranking_clase_aeia': top_aeia_clase,
    'comparacion_analisis_ap_previo': comparacion,
    'capas_web': {
        'ley_segunda': {'ruta': str(CAPAS / 'ley_segunda.geojson'), 'tolerancia_m': tol_ley,
                        'tamano_kb': kb_ley, 'nota': 'geometria recortada a la jurisdiccion'},
        'areas_protegidas_oficial': {'ruta': str(CAPAS / 'areas_protegidas_oficial.geojson'),
                                     'tolerancia_m': tol_ap, 'tamano_kb': kb_ap},
    },
    'qa_por_periodo': qa_periodos,
    'notas': [
        'Deforestacion mapeada = hotspots >=1 ha, cubren 12 de 18 periodos (~%s%% de la serie 2000-2024).'
        % round(100 * serie_12p / serie_total_18p, 0),
        'Hotspots recortados a la jurisdiccion (union municipios.geojson). El hotspot 2012-2013 proviene del '
        'raster DEPTO_ANTIOQUIA que cubre todo Antioquia: solo ~17% de su geometria cae en la jurisdiccion; '
        'sin recorte, Ley 2a (que se extiende al Choco) se inflaria con deforestacion externa.',
        'Ley 2a de 1959 y varias AP (Paramillo, Los Katio) se extienden fuera de la jurisdiccion; el area de '
        'la capa web y area_dentro_jurisdiccion_ha se limitan a la jurisdiccion; los cruces solo ocurren donde hay hotspots.',
        'AEIA (AEIAa.shp) es una zonificacion que cubre toda la jurisdiccion en clases de importancia; por eso NO se '
        'reporta "dentro de AEIA" (seria ~100%) sino el subconjunto de mayor valor ecologico (Muy importante + Importante) '
        'y el desglose por clase en deforestacion_por_clase_aeia_ha.',
        'AEIA.shp y AEIAa.shp son geometricamente identicos; AEIA.shp trae un WKT CTM12 sin codigo EPSG y AEIAa.shp trae '
        'EPSG:3116 explicito: se usa AEIAa por robustez de reproyeccion. La carpeta AEIA tambien trae '
        'Areas_Importancia_Ambiental.shp/AIAA.shp (34 reservas locales nombradas, ~15.789 ha) que NO son la zonificacion AEIA*.',
        'Las capas oficiales traen multipoligonos enormes e invalidos; NO se validan globalmente (buffer(0) intratable). '
        'Se intersectan contra la union pequena y valida de los hotspots, resolviendo invalideces de forma barata.',
        'Coincidencia espacial no es atribucion causal: deforestacion dentro de una figura no implica que la figura la cause.',
        'El analisis previo areas_protegidas_serie.csv usa el overlay AProteg INTERNO del paquete IDEAM (recortado por '
        'periodo, clase por gridcode) sobre TODOS los poligonos; este usa el limite oficial externo sobre hotspots >=1 ha. '
        'Ver comparacion_analisis_ap_previo.',
    ],
}
(OUT / 'figuras_resumen.json').write_text(
    json.dumps(resumen, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print('json ->', OUT / 'figuras_resumen.json', flush=True)

# ---------------------------------------------------------------------------
# Consola: hallazgos
# ---------------------------------------------------------------------------
print('\n=== TOTALES (12 periodos mapeados, dentro de jurisdiccion) ===', flush=True)
print(f'Deforestacion mapeada: {tot_map:,.1f} ha (serie 12p: {serie_12p:,.1f} ha; serie 18p: {serie_total_18p:,.1f} ha)')
print(f'Dentro de Ley 2a:           {d_ley:,.1f} ha = {pct(d_ley, tot_map)}%')
print(f'Dentro de Areas Protegidas: {d_ap:,.1f} ha = {pct(d_ap, tot_map)}%')
print(f'Dentro de AEIA (alta):      {d_aeia_alta:,.1f} ha = {pct(d_aeia_alta, tot_map)}%')
print('\n=== RANKING AREAS PROTEGIDAS (top 8) ===')
for r in top_ap_unidad[:8]:
    print(f"  {r['deforestacion_ha']:>8,.1f} ha  {r['unidad']} | {r['categoria']}")
print('\n=== ZONAS LEY 2a ===')
for r in top_ley_zona:
    print(f"  {r['deforestacion_ha']:>8,.1f} ha  {r['unidad']}")
print('\n=== CLASE AEIA (defo interseccion por clase) ===')
for r in top_aeia_clase:
    print(f"  {r['deforestacion_ha']:>8,.1f} ha  {r['unidad']}")
print('\n=== TENDENCIA POR BLOQUES ===')
for bl, d in tend.items():
    print(f"  {bl}: AP {d['ap']['ha_anual']:,.1f} ha/ano ({d['ap']['pct']}%) | "
          f"Ley2a {d['ley2a']['ha_anual']:,.1f} ha/ano ({d['ley2a']['pct']}%) | "
          f"AEIA-alta {d['aeia_alta']['ha_anual']:,.1f} ha/ano ({d['aeia_alta']['pct']}%)")
print('\nOK', flush=True)
