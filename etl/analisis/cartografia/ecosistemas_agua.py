# -*- coding: utf-8 -*-
"""
ECOSISTEMAS ESTRATEGICOS Y AGUA vs BOSQUE — cartografia oficial CORPOURABA vs deforestacion mapeada
====================================================================================================
Cruza las capas de la cartografia oficial de CORPOURABA con los hotspots de deforestacion
(>=1 ha) del Observatorio (12 periodos, WGS84).

CAPAS (C:\\...\\CARTOGRAFIA):
  ECOSISTEMAS ESTRATEGICOS\\ (12 shapefiles, todos EPSG:3116 = MAGNA Bogota central):
    - Acuifero_Profundos_Uraba.shp / Acuifero_Someros_Uraba.shp  -> Acuiferos
    - Bosque_Seco_Tropical_CORPOURABA.shp                        -> Bosque seco tropical
    - Humedales_CORPOURABA.shp                                   -> Humedales
    - Paramos_CORPOURABA.shp                                     -> Paramos
    - Zonificacion_Manglares_MADS.shp                            -> Manglares
    - Pendientes_Mayores_Al_100.shp                             -> Pendientes >100% (fragilidad)
    - Zonificacion_UACD.shp                                      -> Zonificacion bahia (UAC Darien)
    - ECOSISTEMAS_IDEAM.shp  (mapa wall-to-wall de 53 clases)    -> se reporta APARTE, natural vs agro
    - Rondas/Zonificacion_Ronda_Hidrica_*  (hidrico)            -> se agregan con retiros
  CARTOGRAFIA BASE\\Retiros_Hidricos.shp (102.463 franjas ~30 m, EPSG:3116)

EXCLUSIONES (orden del usuario): NO se leen GESTION RIESGO, PDET, AREAS DE VIDA.

METODO:
  - CRS real de cada capa (EPSG:3116) -> reproyectar todo a EPSG:3115 (metrico, ha=area/10000).
  - hotspots to_crs(3115); buffer(0) para reparar geometrias.
  - overlay/intersection contra la union disuelta de cada tipo (sin doble conteo dentro de un tipo).
  - Los distintos tipos SI pueden solaparse entre si (p.ej. IDEAM con todo): se declara.
  - Ningun subconjunto por periodo puede superar la deforestacion mapeada del periodo (se verifica).

SALIDAS:
  data/processed/analisis/cartografia/ecosistemas_deforestacion.csv  (tipo x periodo x ha, UTF-8 BOM)
  data/processed/analisis/cartografia/ecosistemas_resumen.json
  data/processed/capas/ecosistemas_estrategicos.geojson  (union tipificada, WGS84, simplify ~60 m)
"""
from __future__ import annotations
import sys, json, unicodedata
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\etl')
import run_etl  # PERIODOS, read_shp

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union

CARTO = Path(r'C:\Users\Desktop\Documents\Documentos\PROGRAMAS\CONSULTAS CARTOGRÁFICAS\CARTOGRAFIA')
ECO = CARTO / 'ECOSISTEMAS ESTRATEGICOS'
RETIROS_SHP = CARTO / 'CARTOGRAFIA BASE' / 'Retiros_Hidricos.shp'
BASE = Path(r'E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion')
PROCESSED = BASE / 'data' / 'processed'
HOTDIR = PROCESSED / 'hotspots'
OUT = PROCESSED / 'analisis' / 'cartografia'
CAPAS = PROCESSED / 'capas'
OUT.mkdir(parents=True, exist_ok=True)
CAPAS.mkdir(parents=True, exist_ok=True)

METRIC = 'EPSG:3115'
WGS84 = 'EPSG:4326'
FECHA_CORTE_CAPA = '2025-02'  # fecha de los shapefiles de ecosistemas (feb 2025)
PERIODO_ANIOS = {p: (i, f) for p, i, f in run_etl.PERIODOS}
PERIODOS_HOT = [p for p, _, _ in run_etl.PERIODOS if (HOTDIR / f'{p}.geojson').exists()]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def sin_tildes(s: str) -> str:
    s = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in s if not unicodedata.combining(c)).upper()


def fix(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Repara geometrias invalidas (buffer 0) y descarta vacias."""
    gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].copy()
    bad = ~gdf.geometry.is_valid
    if bad.any():
        gdf.loc[bad, 'geometry'] = gdf.loc[bad, 'geometry'].buffer(0)
    gdf = gdf[gdf.geometry.is_valid & ~gdf.geometry.is_empty]
    return gdf


def force2d(geom):
    """Elimina la dimension Z (algunas rondas son Polygon Z)."""
    from shapely import wkb
    if geom is None:
        return geom
    if not geom.has_z:
        return geom
    return wkb.loads(wkb.dumps(geom, output_dimension=2))


def cargar(nombre_shp: str, path: Path = None) -> gpd.GeoDataFrame:
    """Carga un shapefile, aplana a 2D, reproyecta a METRIC y repara."""
    p = path if path is not None else (ECO / nombre_shp)
    g = run_etl.read_shp(p) if hasattr(run_etl, 'read_shp') else gpd.read_file(p)
    if any(g.geometry.has_z):
        g['geometry'] = g.geometry.map(force2d)
    crs_orig = str(g.crs)
    g = g.to_crs(METRIC)
    g = fix(g)
    return g, crs_orig


def union_de(nombre_shp: str, path: Path = None):
    g, crs_orig = cargar(nombre_shp, path)
    u = unary_union(g.geometry.values)
    if not u.is_valid:
        u = u.buffer(0)
    area_ha = u.area / 1e4
    print(f'  {Path(nombre_shp).name}: {len(g):>4} feats | CRS {crs_orig} -> {METRIC} | union {area_ha:>12,.1f} ha')
    return u, area_ha, len(g)


# Clasificacion de las 53 clases IDEAM: natural vs agro/artificial
IDEAM_AGRO_ART = {
    'Agroecosistema Cafetero', 'Agroecosistema Cañero', 'Agroecosistema Forestal',
    'Agroecosistema Ganadero', 'Agroecosistema Palmero', 'Agroecosistema Platanero y Bananero',
    'Agroecosistema de Cultivos Permanentes', 'Agroecosistema de Cultivos Transitorios',
    'Agroecosistema de Mosaico de Cultivos y Espacios Naturales',
    'Agroecosistema de Mosaico de Cultivos y Pastos',
    'Agroecosistema de Mosaico de Cultivos, Pastos y Espacios Naturales',
    'Agroecosistema de Mosaico de Pastos y Espacios Naturales',
    'Territorio Artificializado', 'Transicional Transformado',
    'Transicional Transformado Costero', 'Vegetación Secundaria',
    'Cuerpo de Agua Artificial',
}


def clasificar_ideam(v: str) -> str:
    v = str(v)
    if v in IDEAM_AGRO_ART:
        return 'agro_artificial'
    return 'natural'


# ---------------------------------------------------------------------------
# [1] Carga de capas de ecosistemas estrategicos
# ---------------------------------------------------------------------------

print('[1/6] Uniones de ecosistemas estrategicos ...')

# Tipos "ecosistema estrategico" (excluye hidrico y excluye IDEAM que va aparte)
tipos_eco = {}   # tipo -> (union, area_ha, n)

# Acuiferos = profundos U someros
gp, _ = cargar('Acuifero_Profundos_Uraba.shp')
gs, _ = cargar('Acuifero_Someros_Uraba.shp')
u_acu = unary_union(list(gp.geometry.values) + list(gs.geometry.values))
if not u_acu.is_valid:
    u_acu = u_acu.buffer(0)
tipos_eco['Acuíferos'] = (u_acu, u_acu.area / 1e4, len(gp) + len(gs))
print(f'  Acuiferos (profundos+someros): {len(gp)+len(gs)} feats | union {u_acu.area/1e4:,.1f} ha')

tipos_eco['Bosque seco tropical'] = union_de('Bosque_Seco_Tropical_CORPOURABA.shp')
tipos_eco['Humedales'] = union_de('Humedales_CORPOURABA.shp')
tipos_eco['Páramos'] = union_de('Paramos_CORPOURABA.shp')
tipos_eco['Manglares'] = union_de('Zonificacion_Manglares_MADS.shp')
tipos_eco['Pendientes >100%'] = union_de('Pendientes_Mayores_Al_100.shp')
tipos_eco['Zonificación bahía (UAC Darién)'] = union_de('Zonificacion_UACD.shp')

# IDEAM: mapa wall-to-wall, se reporta APARTE dividido en natural vs agro/artificial
print('  ECOSISTEMAS_IDEAM (mapa wall-to-wall, se reporta aparte) ...')
g_ideam, crs_ideam = cargar('ECOSISTEMAS_IDEAM.shp')
g_ideam['grupo'] = g_ideam['ecos_gener'].map(clasificar_ideam)
u_ideam_nat = unary_union(g_ideam.loc[g_ideam['grupo'] == 'natural', 'geometry'].values)
if not u_ideam_nat.is_valid:
    u_ideam_nat = u_ideam_nat.buffer(0)
ideam_nat_ha = u_ideam_nat.area / 1e4
print(f'    IDEAM natural: {int((g_ideam.grupo=="natural").sum())} feats | union {ideam_nat_ha:,.1f} ha')

# ---------------------------------------------------------------------------
# [2] Capas hidricas (retiros / rondas) -> se reportan como grupo "agua"
# ---------------------------------------------------------------------------

print('[2/6] Uniones hidricas (retiros y rondas) ...')
tipos_agua = {}
tipos_agua['Rondas hídricas (ríos)'] = union_de('Rondas_Hidricas_CORPOURABA.shp')
# Rondas zonificadas Chigorodo y Currulao (tienen Z)
tipos_agua['Ronda zonificada Chigorodó'] = union_de('Zonificacion_Ronda_Hidrica_Río Chigorodó.shp')
tipos_agua['Ronda zonificada Currulao'] = union_de('Zonificacion_Ronda_Hidrica_Río Currulao.shp')

# Retiros hidricos: capa grande (102k polig ~30m). Union disuelta.
print('  Retiros_Hidricos.shp (grande) ...')
g_ret, crs_ret = cargar('Retiros_Hidricos.shp', path=RETIROS_SHP)
u_ret = unary_union(g_ret.geometry.values)
if not u_ret.is_valid:
    u_ret = u_ret.buffer(0)
ret_ha = u_ret.area / 1e4
tipos_agua['Retiros hídricos de cauces'] = (u_ret, ret_ha, len(g_ret))
print(f'    Retiros: {len(g_ret)} feats | CRS {crs_ret} -> {METRIC} | union {ret_ha:,.1f} ha')

# Union total "agua" (retiros + rondas), sin doble conteo entre ellas
u_agua = unary_union([t[0] for t in tipos_agua.values()])
if not u_agua.is_valid:
    u_agua = u_agua.buffer(0)
agua_ha = u_agua.area / 1e4
print(f'  UNION agua (retiros+rondas): {agua_ha:,.1f} ha')

# ---------------------------------------------------------------------------
# [3] Jurisdiccion (para % de cobertura de cada capa)
# ---------------------------------------------------------------------------

mun = gpd.read_file(PROCESSED / 'municipios.geojson').to_crs(METRIC)
mun = fix(mun)
U_JUR = unary_union(mun.geometry.values)
if not U_JUR.is_valid:
    U_JUR = U_JUR.buffer(0)
jur_ha = U_JUR.area / 1e4
print(f'  jurisdiccion: {jur_ha:,.1f} ha')

# ---------------------------------------------------------------------------
# [4] Cruce hotspots x cada tipo por periodo
# ---------------------------------------------------------------------------

print('[3/6] Cruce hotspots x tipos por periodo ...')
rows = []
qa = []
# orden de reporte: ecosistemas estrategicos, luego IDEAM natural, luego cada tipo de agua
tipos_cross = dict(tipos_eco)
tipos_cross['Ecosistemas naturales (IDEAM)'] = (u_ideam_nat, ideam_nat_ha, int((g_ideam.grupo == 'natural').sum()))
for k, v in tipos_agua.items():
    tipos_cross[k] = v
tipos_cross['Agua (retiros+rondas, unión)'] = (u_agua, agua_ha, sum(t[2] for t in tipos_agua.values()))

# grupos para clasificar cada tipo en el CSV/JSON
GRUPO = {'Ecosistemas naturales (IDEAM)': 'ideam_referencia',
         'Rondas hídricas (ríos)': 'agua', 'Ronda zonificada Chigorodó': 'agua',
         'Ronda zonificada Currulao': 'agua', 'Retiros hídricos de cauces': 'agua',
         'Agua (retiros+rondas, unión)': 'agua_union'}

defo_periodo = {}
for pid in PERIODOS_HOT:
    ini, fin = PERIODO_ANIOS[pid]
    ny = max(1, fin - ini)
    h = gpd.read_file(HOTDIR / f'{pid}.geojson').to_crs(METRIC)
    h = fix(h)
    h['ha_geo'] = h.geometry.area / 1e4
    tot = float(h['ha_geo'].sum())
    defo_periodo[pid] = tot
    hgeom = h.geometry
    fila = {'periodo': pid, 'defo_mapeada_ha': round(tot, 2)}
    for tipo, (u, _, _) in tipos_cross.items():
        a = float(hgeom.intersection(u).area.sum()) / 1e4
        a = max(0.0, a)
        rows.append({
            'periodo': pid, 'ano_inicio': ini, 'ano_fin': fin,
            'grupo': GRUPO.get(tipo, 'ecosistema_estrategico'),
            'tipo_ecosistema': tipo,
            'hectareas': round(a, 2),
            'hectareas_anuales': round(a / ny, 2),
            'pct_periodo': round(100 * a / tot, 2) if tot else 0.0,
            'deforestacion_mapeada_periodo_ha': round(tot, 2),
        })
        fila[tipo] = round(a, 1)
    qa.append(fila)
    print(f'  {pid}: {tot:>8,.1f} ha mapeada | agua {fila["Agua (retiros+rondas, unión)"]:>7,.1f} | '
          f'BsT {fila["Bosque seco tropical"]:>6,.1f} | IDEAMnat {fila["Ecosistemas naturales (IDEAM)"]:>7,.1f}')

df = pd.DataFrame(rows)
df.to_csv(OUT / 'ecosistemas_deforestacion.csv', index=False, encoding='utf-8-sig')
print('csv ->', OUT / 'ecosistemas_deforestacion.csv', f'({len(df)} filas)')

# ---------------------------------------------------------------------------
# [5] Verificacion de consistencia y agregados
# ---------------------------------------------------------------------------

print('[4/6] Verificacion y agregados ...')
tot_map = sum(defo_periodo.values())

# VERIFICACION: ningun tipo por periodo puede superar la deforestacion mapeada del periodo
violaciones = []
for r in rows:
    if r['hectareas'] > r['deforestacion_mapeada_periodo_ha'] + 0.01:
        violaciones.append((r['periodo'], r['tipo_ecosistema'], r['hectareas'],
                            r['deforestacion_mapeada_periodo_ha']))
if violaciones:
    print('  !!! VIOLACIONES (subconjunto > total del periodo):')
    for v in violaciones:
        print('   ', v)
else:
    print('  OK: ningun tipo supera la deforestacion mapeada de su periodo.')

# serie regional para contexto de cobertura
reg = pd.read_csv(PROCESSED / 'serie_regional.csv')
reg_defo = reg[reg['clase'] == 'Deforestación']
serie_total_18p = float(reg_defo['hectareas'].sum())
serie_12p = float(reg_defo[reg_defo['periodo'].isin(PERIODOS_HOT)]['hectareas'].sum())

# totales por tipo (12 periodos)
por_tipo = (df.groupby(['grupo', 'tipo_ecosistema'])['hectareas'].sum()
            .round(1).reset_index().sort_values('hectareas', ascending=False))

def pct(a, b):
    return round(100 * a / b, 2) if b else None

resumen_tipos = []
for _, r in por_tipo.iterrows():
    tipo = r['tipo_ecosistema']
    u, cap_ha, n = tipos_cross[tipo]
    inter_jur = u.intersection(U_JUR).area / 1e4
    resumen_tipos.append({
        'tipo_ecosistema': tipo, 'grupo': r['grupo'], 'n_poligonos_capa': int(n),
        'area_capa_ha': round(cap_ha, 1),
        'area_capa_dentro_jurisdiccion_ha': round(inter_jur, 1),
        'pct_jurisdiccion_cubierto': pct(inter_jur, jur_ha),
        'deforestacion_mapeada_dentro_ha': round(float(r['hectareas']), 1),
        'pct_defo_mapeada': pct(float(r['hectareas']), tot_map),
        'pct_capa_deforestada': pct(float(r['hectareas']), cap_ha),
    })

# tendencia por bloques (solo tipos con senal): usar grupos clave
bloques = {'2002_2010': ['2002-2004', '2004-2006', '2006-2008', '2008-2010'],
           '2012_2018': ['2012-2013', '2013-2014', '2016-2017', '2017-2018'],
           '2019_2023': ['2019-2020', '2020-2021', '2021-2022', '2022-2023']}
tipos_clave = ['Agua (retiros+rondas, unión)', 'Ecosistemas naturales (IDEAM)',
               'Bosque seco tropical', 'Humedales', 'Pendientes >100%',
               'Zonificación bahía (UAC Darién)']
tend = {}
for bl, pids in bloques.items():
    anos = sum(PERIODO_ANIOS[p][1] - PERIODO_ANIOS[p][0] for p in pids)
    sub = df[df['periodo'].isin(pids)]
    tm = float(sub.drop_duplicates('periodo')['deforestacion_mapeada_periodo_ha'].sum())
    d = {'anos_cubiertos': anos, 'defo_mapeada_ha': round(tm, 1)}
    for tipo in tipos_clave:
        ha = float(sub[sub['tipo_ecosistema'] == tipo]['hectareas'].sum())
        d[tipo] = {'ha': round(ha, 1), 'ha_anual': round(ha / anos, 1),
                   'pct_mapeada': pct(ha, tm)}
    tend[bl] = d

# ---------------------------------------------------------------------------
# [6] Capa web ecosistemas_estrategicos.geojson (union tipificada por 'tipo')
# ---------------------------------------------------------------------------

print('[5/6] Capa web ecosistemas_estrategicos.geojson ...')
defo_total_tipo = df.groupby('tipo_ecosistema')['hectareas'].sum().round(1)

# Se publican los ecosistemas estrategicos (poligonos) + IDEAM natural.
# El agua (retiros/rondas) NO se publica en esta capa (es lineal/franjas, va aparte);
# se incluye la union hidrica como un solo tipo para el mapa si aporta.
web_defs = [
    ('Acuíferos', tipos_eco['Acuíferos'][0]),
    ('Bosque seco tropical', tipos_eco['Bosque seco tropical'][0]),
    ('Humedales', tipos_eco['Humedales'][0]),
    ('Páramos', tipos_eco['Páramos'][0]),
    ('Manglares', tipos_eco['Manglares'][0]),
    ('Pendientes >100%', tipos_eco['Pendientes >100%'][0]),
    ('Zonificación bahía (UAC Darién)', tipos_eco['Zonificación bahía (UAC Darién)'][0]),
    ('Ecosistemas naturales (IDEAM)', u_ideam_nat),
    ('Retiros y rondas hídricas', u_agua),
]
web_rows = []
for tipo, u in web_defs:
    web_rows.append({'nombre': tipo, 'tipo': tipo,
                     'deforestacion_ha_total': float(defo_total_tipo.get(tipo, defo_total_tipo.get('Agua (retiros+rondas, unión)', 0.0)) if tipo == 'Retiros y rondas hídricas' else defo_total_tipo.get(tipo, 0.0)),
                     'geometry': u})
web = gpd.GeoDataFrame(web_rows, geometry='geometry', crs=METRIC)
web['deforestacion_ha_total'] = web['deforestacion_ha_total'].round(1)

capa_path = CAPAS / 'ecosistemas_estrategicos.geojson'
tol_final = None
for tol in (60, 100, 150, 220, 300):
    w = web.copy()
    w['geometry'] = w.geometry.simplify(tol, preserve_topology=True)
    w = w[~w.geometry.is_empty & w.geometry.notna()]
    w = fix(w).to_crs(WGS84)
    if capa_path.exists():
        capa_path.unlink()
    w.to_file(capa_path, driver='GeoJSON', COORDINATE_PRECISION=5)
    kb = capa_path.stat().st_size / 1024
    print(f'  tolerancia {tol} m -> {kb:.0f} KB')
    tol_final = tol
    if kb < 500:
        break

# ---------------------------------------------------------------------------
# Resumen JSON
# ---------------------------------------------------------------------------

print('[6/6] Resumen JSON ...')
# separar agua vs ecosistemas para el resumen
eco_only = [r for r in resumen_tipos if r['grupo'] == 'ecosistema_estrategico']
ideam_ref = [r for r in resumen_tipos if r['grupo'] == 'ideam_referencia']
agua_only = [r for r in resumen_tipos if r['grupo'] in ('agua', 'agua_union')]

# top periodo por tipo agua-union e ideam
agua_union_serie = df[df['tipo_ecosistema'] == 'Agua (retiros+rondas, unión)'][
    ['periodo', 'hectareas', 'hectareas_anuales', 'pct_periodo', 'deforestacion_mapeada_periodo_ha']
].to_dict('records')

resumen = {
    'titulo': 'Ecosistemas estrategicos y retiros hidricos vs deforestacion mapeada, CORPOURABA',
    'fecha_capas': FECHA_CORTE_CAPA,
    'fuente_capas': ('Cartografia oficial CORPOURABA: ECOSISTEMAS ESTRATEGICOS (12 shapefiles) y '
                     'CARTOGRAFIA BASE/Retiros_Hidricos.shp; CRS origen EPSG:3116 (MAGNA Bogota).'),
    'exclusiones_por_orden_usuario': ['GESTION RIESGO', 'PDET', 'AREAS DE VIDA'],
    'unidad': 'hectareas (area geometrica EPSG:3115)',
    'jurisdiccion_ha': round(jur_ha, 1),
    'totales_12_periodos_mapeados': {
        'deforestacion_mapeada_ha': round(tot_map, 1),
        'por_tipo': resumen_tipos,
    },
    'ecosistemas_estrategicos': eco_only,
    'ecosistemas_ideam_referencia': ideam_ref,
    'retiros_hidricos_y_rondas': agua_only,
    'serie_agua_union_por_periodo': agua_union_serie,
    'tendencia_por_bloques': tend,
    'contexto_cobertura': {
        'periodos_con_hotspots': PERIODOS_HOT,
        'n_periodos_mapeados': len(PERIODOS_HOT),
        'n_periodos_serie_total': int(reg_defo['periodo'].nunique()),
        'deforestacion_serie_12_periodos_ha': round(serie_12p, 1),
        'deforestacion_serie_18_periodos_ha': round(serie_total_18p, 1),
        'pct_serie_cubierta_por_hotspots': pct(serie_12p, serie_total_18p),
    },
    'verificacion_consistencia': {
        'ningun_tipo_supera_total_periodo': len(violaciones) == 0,
        'violaciones': violaciones,
    },
    'capa_web': {'ruta': str(capa_path), 'n_features': int(len(web)),
                 'tolerancia_simplificacion_m': tol_final,
                 'tamano_kb': round(capa_path.stat().st_size / 1024, 0)},
    'notas': [
        'Los hotspots cubren 12 de 18 periodos de la serie; TODOS los porcentajes son '
        '"de la deforestacion MAPEADA" (poligonos >=1 ha), no del total 2000-2024.',
        'ECOSISTEMAS_IDEAM es un mapa wall-to-wall (53 clases) que cubre toda la jurisdiccion; '
        'se reporta solo la fraccion "natural" (bosques, arbustales, manglar, paramo, humedales, '
        'sabanas, etc.), excluyendo agroecosistemas y territorio artificializado. Por ser '
        'wall-to-wall SOLAPA con las demas capas: no se debe sumar con ellas.',
        'Cada tipo se cruza contra su union disuelta (sin doble conteo DENTRO del tipo). '
        'Distintos tipos SI pueden solaparse entre si (p.ej. un humedal dentro de un retiro '
        'hidrico): NO sumar tipos entre si salvo la union "Agua (retiros+rondas)".',
        'Acuiferos, bosque seco, humedales, paramos, manglares y pendientes cubren solo partes '
        'de la jurisdiccion (ver pct_jurisdiccion_cubierto); no son coberturas totales.',
        'Retiros_Hidricos son franjas de proteccion de cauces (~30 m); su interseccion con '
        'deforestacion indica tala en la zona de proteccion hidrica legal.',
        'Coincidencia espacial no es atribucion causal.',
        'Zonificacion bahia (UAC Darien) y rondas zonificadas Chigorodo/Currulao son zonificaciones '
        'de manejo; la interseccion mide deforestacion dentro de esas zonas, no incumplimiento.',
    ],
}
(OUT / 'ecosistemas_resumen.json').write_text(
    json.dumps(resumen, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print('json ->', OUT / 'ecosistemas_resumen.json')

# ---------------------------------------------------------------------------
# Consola: hallazgos
# ---------------------------------------------------------------------------

print('\n=== TOTALES (12 periodos mapeados) ===')
print(f'Deforestacion mapeada: {tot_map:,.1f} ha (serie 12p {serie_12p:,.1f} | serie 18p {serie_total_18p:,.1f})')
print('\n=== DEFORESTACION MAPEADA DENTRO DE CADA TIPO ===')
for r in resumen_tipos:
    print(f"  {r['deforestacion_mapeada_dentro_ha']:>9,.1f} ha ({str(r['pct_defo_mapeada']):>5}% mapeada) "
          f"| cubre {str(r['pct_jurisdiccion_cubierto']):>5}% jur | {r['tipo_ecosistema']}")
print('\n=== TENDENCIA POR BLOQUES (tipos clave, ha/año) ===')
for bl, d in tend.items():
    print(f"  {bl} ({d['anos_cubiertos']} años, mapeada {d['defo_mapeada_ha']:,.0f} ha):")
    for tipo in tipos_clave:
        print(f"      {d[tipo]['ha_anual']:>7,.1f} ha/año ({str(d[tipo]['pct_mapeada']):>5}%) {tipo}")
print('\nOK')
