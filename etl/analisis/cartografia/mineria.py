# -*- coding: utf-8 -*-
"""
MINERIA vs BOSQUE — Titulos mineros y solicitudes vigentes vs deforestacion mapeada
====================================================================================
Cruza la cartografia oficial de CORPOURABA (catastro minero, corte 2025-01-29):
  - Titulos Mineros.shp             (197 poligonos, EPSG:3116)
  - Solicitudes Vigentes Mineria.shp (340 poligonos, EPSG:3116)
con los hotspots de deforestacion >=1 ha del Observatorio (12 periodos, WGS84).

Metodo:
  - Todo reproyectado a EPSG:3115 (MAGNA-SIRGAS / Colombia West); ha = area/10000.
  - Geometrias invalidas -> buffer(0).
  - Dentro/fuera con categorias MUTUAMENTE EXCLUYENTES (solo_titulo, solo_solicitud,
    titulo_y_solicitud, fuera) usando uniones disueltas (sin doble conteo).
  - Atribucion por titulo/solicitud (titular, mineral, estado) via gpd.overlay.
  - Sensibilidad temporal: serie "dentro de titulos otorgados a la fecha del periodo"
    usando FECHA_DE_A (inscripcion) y FECHA_DE01 (vencimiento).

Salidas:
  data/processed/analisis/cartografia/mineria_deforestacion.csv
  data/processed/analisis/cartografia/mineria_resumen.json
  data/processed/capas/titulos_mineros.geojson  (capa web WGS84 simplificada)
"""
from __future__ import annotations
import sys, json, re, unicodedata
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\etl')
import run_etl  # match_municipio, MUNICIPIOS, PERIODOS, read_shp

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union

CARTO = Path(r'C:\Users\Desktop\Documents\Documentos\PROGRAMAS\CONSULTAS CARTOGRÁFICAS\CARTOGRAFIA\TITULOS MINEROS')
BASE = Path(r'E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion')
PROCESSED = BASE / 'data' / 'processed'
HOTDIR = PROCESSED / 'hotspots'
OUT = PROCESSED / 'analisis' / 'cartografia'
CAPAS = PROCESSED / 'capas'
OUT.mkdir(parents=True, exist_ok=True)
CAPAS.mkdir(parents=True, exist_ok=True)

METRIC = 'EPSG:3115'
WGS84 = 'EPSG:4326'
FECHA_CORTE_CAPA = '2025-01-29'  # CreaDate del .shp.xml de ambas capas
PERIODO_ANIOS = {p: (i, f) for p, i, f in run_etl.PERIODOS}
PERIODOS_HOT = [p for p, _, _ in run_etl.PERIODOS if (HOTDIR / f'{p}.geojson').exists()]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def sin_tildes(s: str) -> str:
    s = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in s if not unicodedata.combining(c)).upper()


def clean_titular(s) -> str:
    """'(57500) EXPLORACIONES CHOCO COLOMBIA S.A.S' -> 'EXPLORACIONES CHOCO COLOMBIA S.A.S'"""
    if pd.isna(s):
        return 'Sin dato'
    return re.sub(r'^\(\d+\)\s*', '', ' '.join(str(s).split())).strip() or 'Sin dato'


METAL_KW = ['ORO', 'PLATA', 'PLATINO', 'METALES PRECIOSOS', 'COBRE', 'ZINC', 'MOLIBDENO',
            'NIQUEL', 'MANGANESO', 'VOLFRANIO', 'TUNGSTENO', 'HIERRO', 'COLTAN', 'CROMO']
CARBON_KW = ['CARBON', 'ANTRACITA', 'HULLA']
CONSTR_KW = ['ARENA', 'GRAVA', 'ARCILLA', 'RECEBO', 'TRITURADO', 'CALIZA', 'ARENISCA',
             'PIEDRA', 'MATERIALES DE CONSTRUC', 'AGREGADOS', 'CALCITA', 'CAOLIN', 'YESO',
             'ROCA', 'CASCAJO', 'GRANITO', 'MARMOL', 'CANTERA']


def grupo_mineral(row) -> str:
    """Grupo simplificado por prioridad metalicos > carbon > construccion > otros."""
    txt = sin_tildes(f"{row.get('MINERALES', '')} {row.get('MINERALES_', '')}")
    if any(k in txt for k in METAL_KW):
        return 'Metálicos (oro y asociados)'
    if any(k in txt for k in CARBON_KW):
        return 'Carbón'
    if any(k in txt for k in CONSTR_KW):
        return 'Materiales de construcción'
    return 'Otros / sin dato'


def fix(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    bad = ~gdf.geometry.is_valid
    if bad.any():
        gdf.loc[bad, 'geometry'] = gdf.loc[bad, 'geometry'].buffer(0)
    return gdf


def cargar_capa(nombre_shp: str, tipo: str) -> gpd.GeoDataFrame:
    g = run_etl.read_shp(CARTO / nombre_shp)
    crs_orig = str(g.crs)
    g = g.to_crs(METRIC)
    g = fix(g)
    g['tipo'] = tipo
    g['codigo'] = g['TENURE_ID'].astype(str).str.strip()
    g['titular'] = g['SOLICITANT'].map(clean_titular)
    g['estado'] = g['TITULO_EST'].fillna('Sin dato').map(lambda s: ' '.join(str(s).split()))
    g['etapa'] = g['ETAPA'].fillna('Sin dato')
    g['clasificacion'] = g['CLASIFICAC'].fillna('Sin dato')
    g['municipios_capa'] = g['MUNICIPIOS'].fillna('')
    g['mineral_grupo'] = g.apply(grupo_mineral, axis=1)
    g['minerales_detalle'] = (g['MINERALES_'].fillna(g['MINERALES']).fillna('Sin dato')
                              .map(lambda s: ' '.join(str(s).split())))
    g['area_titulo_ha'] = (g.geometry.area / 1e4).round(1)  # area geometrica en 3115
    fecha_ini = g['FECHA_DE_A'] if tipo == 'titulo' else g['FECHA_DE_S']
    if tipo == 'titulo':
        fecha_ini = fecha_ini.fillna(g['FECHA_DE_E']).fillna(g['FECHA_DE_S'])
    g['ano_inicio_derecho'] = pd.to_datetime(fecha_ini).dt.year
    g['ano_fin_derecho'] = (pd.to_datetime(g['FECHA_DE01']).dt.year
                            if tipo == 'titulo' else np.nan)
    g['uid'] = tipo + ':' + g['codigo']
    print(f'  {nombre_shp}: {len(g)} feats | CRS origen {crs_orig} -> {METRIC} | '
          f'area total {g["area_titulo_ha"].sum():,.0f} ha')
    return g


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------

print('[1/5] Capas oficiales de mineria ...')
tit = cargar_capa('Títulos Mineros.shp', 'titulo')
sol = cargar_capa('Solicitudes Vigentes Mineria.shp', 'solicitud')

U_TIT = unary_union(tit.geometry.values)
U_SOL = unary_union(sol.geometry.values)

mun = gpd.read_file(PROCESSED / 'municipios.geojson').to_crs(METRIC)
mun = fix(mun)
U_JUR = unary_union(mun.geometry.values)
jur_ha = U_JUR.area / 1e4
tit_jur_ha = U_TIT.intersection(U_JUR).area / 1e4
sol_jur_ha = U_SOL.intersection(U_JUR).area / 1e4
print(f'  jurisdiccion: {jur_ha:,.0f} ha | titulos dentro jur: {tit_jur_ha:,.0f} ha '
      f'({100*tit_jur_ha/jur_ha:.2f}%) | solicitudes dentro jur: {sol_jur_ha:,.0f} ha '
      f'({100*sol_jur_ha/jur_ha:.2f}%)')

# ---------------------------------------------------------------------------
# Cruce por periodo
# ---------------------------------------------------------------------------

print('[2/5] Cruce hotspots x mineria por periodo ...')
rows = []            # CSV periodo x categoria
serie_vigencia = []  # sensibilidad por vigencia del titulo
piezas_tit = []      # atribucion por titulo
piezas_sol = []      # atribucion por solicitud
qa_periodos = []

ATT = ['uid', 'codigo', 'titular', 'estado', 'etapa', 'mineral_grupo', 'geometry']

for pid in PERIODOS_HOT:
    ini, fin = PERIODO_ANIOS[pid]
    ny = max(1, fin - ini)
    h = gpd.read_file(HOTDIR / f'{pid}.geojson').to_crs(METRIC)
    h = fix(h)
    h['municipio'] = h['municipio'].fillna('Sin asignar')
    h['ha_geo'] = h.geometry.area / 1e4
    tot = float(h['ha_geo'].sum())

    inter_t = h.geometry.intersection(U_TIT)
    inter_s = h.geometry.intersection(U_SOL)
    a_t = float(inter_t.area.sum()) / 1e4
    a_s = float(inter_s.area.sum()) / 1e4
    a_ts = float(inter_t.intersection(U_SOL).area.sum()) / 1e4
    cat = {
        'solo_titulo': a_t - a_ts,
        'solo_solicitud': a_s - a_ts,
        'titulo_y_solicitud': a_ts,
        'fuera': tot - (a_t + a_s - a_ts),
    }
    for c, ha in cat.items():
        rows.append({'periodo': pid, 'ano_inicio': ini, 'ano_fin': fin, 'categoria': c,
                     'hectareas': round(ha, 2), 'hectareas_anuales': round(ha / ny, 2),
                     'pct_periodo': round(100 * ha / tot, 2) if tot else 0.0,
                     'deforestacion_mapeada_periodo_ha': round(tot, 2)})

    # sensibilidad: solo titulos ya otorgados (y no vencidos) en el periodo
    vig = tit[(tit['ano_inicio_derecho'].notna()) & (tit['ano_inicio_derecho'] <= fin) &
              (tit['ano_fin_derecho'].isna() | (tit['ano_fin_derecho'] >= ini))]
    a_vig = 0.0
    if len(vig):
        a_vig = float(h.geometry.intersection(unary_union(vig.geometry.values)).area.sum()) / 1e4
    serie_vigencia.append({'periodo': pid, 'ano_inicio': ini, 'ano_fin': fin,
                           'n_titulos_otorgados': int(len(vig)),
                           'ha_dentro_titulos_capa_actual': round(a_t, 2),
                           'ha_dentro_titulos_otorgados_en_el_periodo': round(a_vig, 2),
                           'pct_periodo_otorgados': round(100 * a_vig / tot, 2) if tot else 0.0})

    # atribucion por titulo / solicitud (puede haber doble conteo si se solapan entre si)
    for capa, dest in ((tit, piezas_tit), (sol, piezas_sol)):
        ov = gpd.overlay(h[['municipio', 'geometry']], capa[ATT],
                         how='intersection', keep_geom_type=True)
        if len(ov):
            ov['ha'] = ov.geometry.area / 1e4
            ov['periodo'] = pid
            dest.append(pd.DataFrame(ov.drop(columns='geometry')))

    qa_periodos.append({'periodo': pid, 'n_hotspots': int(len(h)),
                        'ha_geometrica': round(tot, 1),
                        'ha_propiedad': round(float(h['ha'].sum()), 1)})
    print(f'  {pid}: {len(h):>4} hotspots {tot:>9,.1f} ha | titulo {a_t:>7,.1f} '
          f'| solicitud {a_s:>7,.1f} | ambos {a_ts:>6,.1f} | fuera {cat["fuera"]:>9,.1f}')

df = pd.DataFrame(rows)
df.to_csv(OUT / 'mineria_deforestacion.csv', index=False, encoding='utf-8-sig')
print('csv ->', OUT / 'mineria_deforestacion.csv', f'({len(df)} filas)')

# ---------------------------------------------------------------------------
# Agregados y hallazgos
# ---------------------------------------------------------------------------

print('[3/5] Agregados ...')
tot_map = float(df[df['categoria'] == 'fuera']['deforestacion_mapeada_periodo_ha'].sum())
ha_cat = df.groupby('categoria')['hectareas'].sum()
d_tit = float(ha_cat['solo_titulo'] + ha_cat['titulo_y_solicitud'])
d_sol = float(ha_cat['solo_solicitud'] + ha_cat['titulo_y_solicitud'])
d_union = float(ha_cat['solo_titulo'] + ha_cat['solo_solicitud'] + ha_cat['titulo_y_solicitud'])

reg = pd.read_csv(PROCESSED / 'serie_regional.csv')
reg_defo = reg[reg['clase'] == 'Deforestación']
serie_total_18p = float(reg_defo['hectareas'].sum())
serie_12p = float(reg_defo[reg_defo['periodo'].isin(PERIODOS_HOT)]['hectareas'].sum())

pt = pd.concat(piezas_tit, ignore_index=True) if piezas_tit else pd.DataFrame()
ps = pd.concat(piezas_sol, ignore_index=True) if piezas_sol else pd.DataFrame()
doble_conteo_tit = float(pt['ha'].sum()) - d_tit  # solapes titulo-titulo

# tendencia por bloques (tasa anual y % del mapeado)
bloques = {'2002_2010': ['2002-2004', '2004-2006', '2006-2008', '2008-2010'],
           '2012_2018': ['2012-2013', '2013-2014', '2016-2017', '2017-2018'],
           '2019_2023': ['2019-2020', '2020-2021', '2021-2022', '2022-2023']}
tend = {}
for bl, pids in bloques.items():
    sub = df[df['periodo'].isin(pids)]
    anos = sum(PERIODO_ANIOS[p][1] - PERIODO_ANIOS[p][0] for p in pids)
    dt = float(sub[sub['categoria'].isin(['solo_titulo', 'titulo_y_solicitud'])]['hectareas'].sum())
    ds = float(sub[sub['categoria'].isin(['solo_solicitud', 'titulo_y_solicitud'])]['hectareas'].sum())
    tm = float(sub[sub['categoria'] == 'fuera']['deforestacion_mapeada_periodo_ha'].unique().sum())
    tend[bl] = {'anos_cubiertos': anos,
                'defo_mapeada_ha': round(tm, 1),
                'dentro_titulos_ha': round(dt, 1),
                'dentro_titulos_ha_anual': round(dt / anos, 1),
                'pct_dentro_titulos': round(100 * dt / tm, 2),
                'dentro_solicitudes_ha': round(ds, 1),
                'dentro_solicitudes_ha_anual': round(ds / anos, 1),
                'pct_dentro_solicitudes': round(100 * ds / tm, 2)}

def top(dfp, keys, n=12):
    if dfp.empty:
        return []
    g = (dfp.groupby(keys)['ha'].sum().sort_values(ascending=False).head(n)
         .round(1).reset_index().rename(columns={'ha': 'deforestacion_ha'}))
    return g.to_dict('records')

top_mun_tit = top(pt, ['municipio'])
top_mun_sol = top(ps, ['municipio'])
top_titulares = top(pt, ['titular'])
top_titulos = top(pt, ['codigo', 'titular', 'mineral_grupo', 'estado', 'etapa'])
top_solicitudes = top(ps, ['codigo', 'titular', 'mineral_grupo', 'estado'])
por_mineral_tit = top(pt, ['mineral_grupo'], n=10)
por_mineral_sol = top(ps, ['mineral_grupo'], n=10)
por_etapa = top(pt, ['etapa'], n=10)
por_estado_tit = top(pt, ['estado'], n=10)

# ---------------------------------------------------------------------------
# Capa web
# ---------------------------------------------------------------------------

print('[4/5] Capa web titulos_mineros.geojson ...')
defo_uid = pd.concat([pt, ps], ignore_index=True).groupby('uid')['ha'].sum() if len(pt) or len(ps) else pd.Series(dtype=float)

web = pd.concat([tit, sol], ignore_index=True)
web = gpd.GeoDataFrame(web, geometry='geometry', crs=METRIC)
web['nombre'] = web['codigo']
web['mineral'] = web['mineral_grupo']
web['minerales_detalle'] = web['minerales_detalle'].map(
    lambda s: s if len(s) <= 140 else s[:137] + '...')
web['municipios'] = web['municipios_capa'].map(lambda s: ' '.join(str(s).split()))
web['area_ha'] = web['area_titulo_ha']
web['ano'] = web['ano_inicio_derecho'].astype('Int64')
web['deforestacion_ha_total'] = web['uid'].map(defo_uid).fillna(0.0).round(1)

KEEP = ['nombre', 'tipo', 'titular', 'mineral', 'minerales_detalle', 'estado', 'etapa',
        'clasificacion', 'municipios', 'ano', 'area_ha', 'deforestacion_ha_total', 'geometry']
web = web[KEEP]
capa_path = CAPAS / 'titulos_mineros.geojson'
for tol in (60, 100, 150, 220):
    w = web.copy()
    w['geometry'] = w.geometry.simplify(tol, preserve_topology=True)
    w = fix(w).to_crs(WGS84)
    if capa_path.exists():
        capa_path.unlink()
    w.to_file(capa_path, driver='GeoJSON', COORDINATE_PRECISION=5)
    kb = capa_path.stat().st_size / 1024
    print(f'  tolerancia {tol} m -> {kb:.0f} KB')
    if kb < 500:
        break
tol_final = tol

# ---------------------------------------------------------------------------
# Resumen JSON
# ---------------------------------------------------------------------------

print('[5/5] Resumen JSON ...')
pct = lambda a, b: round(100 * a / b, 2) if b else None
resumen = {
    'titulo': 'Mineria vs bosque — titulos y solicitudes mineras vs deforestacion mapeada, CORPOURABA',
    'fecha_corte_capa_minera': FECHA_CORTE_CAPA,
    'fuente_capa': 'Cartografia oficial CORPOURABA / catastro minero (Titulos Mineros.shp, Solicitudes Vigentes Mineria.shp), CRS origen EPSG:3116',
    'unidad': 'hectareas (area geometrica EPSG:3115)',
    'capas': {
        'titulos': {
            'n': int(len(tit)),
            'por_estado': tit['estado'].value_counts().to_dict(),
            'por_etapa': tit['etapa'].value_counts().to_dict(),
            'por_mineral_grupo': tit['mineral_grupo'].value_counts().to_dict(),
            'area_total_ha': round(float(tit['area_titulo_ha'].sum()), 0),
            'area_dentro_jurisdiccion_ha': round(tit_jur_ha, 0),
            'pct_jurisdiccion_titulada': pct(tit_jur_ha, jur_ha),
            'rango_otorgamiento': [int(tit['ano_inicio_derecho'].min()),
                                   int(tit['ano_inicio_derecho'].max())],
        },
        'solicitudes': {
            'n': int(len(sol)),
            'por_estado': sol['estado'].value_counts().to_dict(),
            'por_mineral_grupo': sol['mineral_grupo'].value_counts().to_dict(),
            'area_total_ha': round(float(sol['area_titulo_ha'].sum()), 0),
            'area_dentro_jurisdiccion_ha': round(sol_jur_ha, 0),
            'pct_jurisdiccion_solicitada': pct(sol_jur_ha, jur_ha),
            'rango_radicacion': [int(sol['ano_inicio_derecho'].min()),
                                 int(sol['ano_inicio_derecho'].max())],
        },
        'jurisdiccion_ha': round(jur_ha, 0),
    },
    'totales_12_periodos_mapeados': {
        'deforestacion_mapeada_ha': round(tot_map, 1),
        'dentro_titulos_ha': round(d_tit, 1),
        'pct_dentro_titulos': pct(d_tit, tot_map),
        'dentro_solicitudes_ha': round(d_sol, 1),
        'pct_dentro_solicitudes': pct(d_sol, tot_map),
        'dentro_titulo_o_solicitud_ha': round(d_union, 1),
        'pct_dentro_titulo_o_solicitud': pct(d_union, tot_map),
        'solape_titulo_y_solicitud_ha': round(float(ha_cat['titulo_y_solicitud']), 1),
        'fuera_ha': round(float(ha_cat['fuera']), 1),
    },
    'contexto_cobertura': {
        'periodos_con_hotspots': PERIODOS_HOT,
        'deforestacion_serie_12_periodos_ha': round(serie_12p, 1),
        'deforestacion_serie_18_periodos_ha': round(serie_total_18p, 1),
        'pct_serie_cubierta_por_hotspots': pct(serie_12p, serie_total_18p),
        'nota': ('Los hotspots cubren 12 de 18 periodos; todos los porcentajes son '
                 '"de la deforestacion MAPEADA" (poligonos >=1 ha), no del total 2000-2024.'),
    },
    'serie_por_periodo': df.to_dict('records'),
    'tendencia_por_bloques': tend,
    'sensibilidad_vigencia_titulos': serie_vigencia,
    'doble_conteo_por_solape_entre_titulos_ha': round(max(0.0, doble_conteo_tit), 2),
    'top_municipios_dentro_titulos': top_mun_tit,
    'top_municipios_dentro_solicitudes': top_mun_sol,
    'top_titulares_por_deforestacion': top_titulares,
    'top_titulos_por_deforestacion': top_titulos,
    'top_solicitudes_por_deforestacion': top_solicitudes,
    'deforestacion_por_mineral_titulos': por_mineral_tit,
    'deforestacion_por_mineral_solicitudes': por_mineral_sol,
    'deforestacion_por_etapa_titulos': por_etapa,
    'deforestacion_por_estado_titulos': por_estado_tit,
    'capa_web': {'ruta': str(capa_path), 'n_features': int(len(web)),
                 'tolerancia_simplificacion_m': tol_final,
                 'tamano_kb': round(capa_path.stat().st_size / 1024, 0)},
    'qa_por_periodo': qa_periodos,
    'notas': [
        f'La capa minera es una foto del catastro al {FECHA_CORTE_CAPA}: cruzarla con '
        'deforestacion historica es retrospectivo. La serie sensibilidad_vigencia_titulos '
        'recalcula cada periodo usando SOLO titulos ya otorgados (FECHA_DE_A) y no vencidos.',
        'Categorias del CSV mutuamente excluyentes (solo_titulo, solo_solicitud, '
        'titulo_y_solicitud, fuera); suman la deforestacion mapeada del periodo.',
        'Los hotspots cubren 12 de 18 periodos (~87% de la deforestacion medida en la serie); '
        'ademas son poligonos >=1 ha simplificados, por eso su area geometrica difiere '
        'levemente de serie_regional.csv.',
        'La capa incluye titulos/solicitudes que se extienden fuera de la jurisdiccion '
        '(Choco, Cordoba): area_titulo_ha es el poligono completo, pero los cruces solo '
        'ocurren dentro de la jurisdiccion porque los hotspots estan dentro.',
        'Grupo mineral asignado por prioridad metalicos > carbon > materiales de construccion '
        '> otros sobre los campos MINERALES/MINERALES_ (un titulo mixto cuenta como metalico).',
        'En las tablas por titulo/titular puede haber leve doble conteo donde dos titulos se '
        'solapan entre si (cuantificado en doble_conteo_por_solape_entre_titulos_ha); los '
        'totales dentro/fuera usan uniones disueltas y NO tienen doble conteo.',
        'Coincidencia espacial no es atribucion causal: deforestacion dentro de un titulo no '
        'implica que el titular la causo.',
    ],
}
(OUT / 'mineria_resumen.json').write_text(
    json.dumps(resumen, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print('json ->', OUT / 'mineria_resumen.json')

# ---------------------------------------------------------------------------
# Consola: hallazgos
# ---------------------------------------------------------------------------

print('\n=== TOTALES (12 periodos mapeados) ===')
print(f"Deforestacion mapeada: {tot_map:,.1f} ha "
      f"(serie 12p: {serie_12p:,.1f} ha; serie 18p: {serie_total_18p:,.1f} ha)")
print(f"Dentro de titulos:      {d_tit:,.1f} ha = {pct(d_tit, tot_map)}% de lo mapeado")
print(f"Dentro de solicitudes:  {d_sol:,.1f} ha = {pct(d_sol, tot_map)}% de lo mapeado")
print(f"Titulo o solicitud:     {d_union:,.1f} ha = {pct(d_union, tot_map)}%")
print('\n=== % DENTRO DE TITULOS POR PERIODO ===')
piv = df[df['categoria'].isin(['solo_titulo', 'titulo_y_solicitud'])].groupby(
    ['periodo'])[['hectareas']].sum()
piv['pct'] = df[df['categoria'] == 'fuera'].set_index('periodo')['deforestacion_mapeada_periodo_ha']
piv['pct'] = (100 * piv['hectareas'] / piv['pct']).round(2)
print(piv.to_string())
print('\n=== TENDENCIA POR BLOQUES ===')
for bl, d in tend.items():
    print(f"  {bl}: dentro titulos {d['dentro_titulos_ha_anual']:,.1f} ha/año "
          f"({d['pct_dentro_titulos']}%) | solicitudes {d['dentro_solicitudes_ha_anual']:,.1f} "
          f"ha/año ({d['pct_dentro_solicitudes']}%)")
print('\n=== VIGENCIA (titulos otorgados a la fecha del periodo) ===')
for r in serie_vigencia:
    print(f"  {r['periodo']}: capa actual {r['ha_dentro_titulos_capa_actual']:>8,.1f} ha | "
          f"otorgados {r['ha_dentro_titulos_otorgados_en_el_periodo']:>8,.1f} ha "
          f"({r['n_titulos_otorgados']} titulos)")
print('\n=== TOP MUNICIPIOS DENTRO DE TITULOS ===')
for r in top_mun_tit[:8]:
    print(f"  {r['deforestacion_ha']:>8,.1f} ha  {r['municipio']}")
print('\n=== TOP TITULARES ===')
for r in top_titulares[:8]:
    print(f"  {r['deforestacion_ha']:>8,.1f} ha  {r['titular']}")
print('\n=== TOP TITULOS ===')
for r in top_titulos[:8]:
    print(f"  {r['deforestacion_ha']:>8,.1f} ha  {r['codigo']} | {r['titular'][:45]} | "
          f"{r['mineral_grupo']} | {r['estado']} | {r['etapa']}")
print('\n=== POR MINERAL (titulos) ===')
for r in por_mineral_tit:
    print(f"  {r['deforestacion_ha']:>8,.1f} ha  {r['mineral_grupo']}")
print('\nOK')
