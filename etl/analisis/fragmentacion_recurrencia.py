# -*- coding: utf-8 -*-
"""
FRAGMENTACION Y RECURRENCIA ESPACIAL DE LA DEFORESTACION - CORPOURABA 2002-2023
================================================================================
Entrada : data/processed/hotspots/*.geojson  (12 periodos, parches deforestacion
          >=1 ha, columnas: municipio, ha, geometry en EPSG:4326)
          data/processed/municipios.geojson   (mascara jurisdiccion, 19 mpios)

Salidas : data/processed/analisis/fragmentacion.csv        (periodo x municipio)
          data/processed/analisis/recurrencia.geojson      (celdas >=3 periodos, WGS84)
          data/processed/analisis/fragmentacion_resumen.json

Decisiones metodologicas (verificadas):
 - AREA = columna 'ha' (coherente con la serie validada). La geometria GeoJSON
   esta generalizada (~6-8% menos area que cualquier CRS metrico o equal-area),
   por lo que la geometria se usa SOLO para operaciones espaciales (asignacion a
   celdas/municipios y apportionment), no para reportar area.
 - 2012-2013 proviene de un raster departamental (todo Antioquia): 3.406 parches
   (8.522,6 ha) caen FUERA de los 19 municipios CORPOURABA. Se recortan a la
   jurisdiccion y se marca con flag de calidad.
 - Recurrencia: rejilla 2x2 km construida en EPSG:3115, exportada en WGS84.
"""
import sys, os, json, glob, warnings
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import box
from shapely import make_valid

BASE = r'E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion'
HOT  = os.path.join(BASE, 'data', 'processed', 'hotspots')
OUT  = os.path.join(BASE, 'data', 'processed', 'analisis')
os.makedirs(OUT, exist_ok=True)

CRS_M = 3115            # MAGNA-SIRGAS / Colombia West zone (metrico)
CRS_WGS = 4326
CELL = 2000.0          # tamano de celda en metros (~2x2 km)
UMBRAL_GRANDE = 10.0   # ha, parche "grande"
UMBRAL_PERSIST = 3     # nº de periodos para "zona persistente"

def periodo_ano(fname):
    base = os.path.basename(fname).replace('.geojson', '')
    a, b = base.split('-')
    return base, int(a), int(b)

# ---------------------------------------------------------------------------
# 0. Cargar mascara de jurisdiccion y tabla de municipios
# ---------------------------------------------------------------------------
mun = gpd.read_file(os.path.join(BASE, 'data', 'processed', 'municipios.geojson'))
mun_m = mun.to_crs(CRS_M)
mun_m['geometry'] = mun_m.geometry.apply(make_valid)
juris = mun_m.geometry.union_all()

# nombre -> (codigo_dane, subregion, area_mpio_ha)
info_mpio = {r['nombre']: (str(r['codigo_dane']), r['subregion'], float(r['area_municipio_ha']))
             for _, r in mun.iterrows()}

files = sorted(glob.glob(os.path.join(HOT, '*.geojson')))
print(f'[i] {len(files)} periodos de hotspots encontrados')

# ---------------------------------------------------------------------------
# 1. FRAGMENTACION  (periodo x municipio)  + serie regional por periodo
# ---------------------------------------------------------------------------
frag_rows = []
reg_rows = []
qa = {}                 # notas de calidad por periodo
patches_by_period = {}  # cache para recurrencia (solo geometria en jurisdiccion)

for f in files:
    per, a0, a1 = periodo_ano(f)
    g = gpd.read_file(f)
    n_total = len(g)
    ha_total_bruto = float(g['ha'].sum())
    # recorte a jurisdiccion: parches con municipio None caen fuera (verificado)
    fuera = g['municipio'].isna()
    n_fuera = int(fuera.sum()); ha_fuera = float(g.loc[fuera, 'ha'].sum())
    g = g[~fuera].copy()
    if n_fuera:
        qa[per] = (f'raster_departamental_recortado: {n_fuera} parches / '
                   f'{ha_fuera:.1f} ha fuera de los 19 mpios CORPOURABA (excluidos)')

    # geometria valida en metrico para recurrencia
    gm = g.to_crs(CRS_M)
    gm['geometry'] = gm.geometry.apply(make_valid)
    gm['_pa'] = gm.geometry.area           # area geometrica del parche (m2) p/ apportionment
    gm['periodo'] = per
    patches_by_period[per] = gm[['municipio', 'ha', '_pa', 'periodo', 'geometry']].copy()

    # metricas regionales del periodo (jurisdiccion)
    ha = g['ha'].values
    grandes = ha > UMBRAL_GRANDE
    reg_rows.append(dict(
        periodo=per, ano_inicio=a0, ano_fin=a1,
        n_parches=int(len(g)),
        ha_total=round(float(ha.sum()), 2),
        tamano_medio_ha=round(float(np.mean(ha)), 3),
        tamano_mediano_ha=round(float(np.median(ha)), 3),
        tamano_max_ha=round(float(np.max(ha)), 2),
        pct_parches_grandes=round(100.0 * grandes.sum() / len(g), 2),
        share_ha_grandes=round(100.0 * ha[grandes].sum() / ha.sum(), 2),
        densidad_parches_1000ha=round(1000.0 * len(g) / ha.sum(), 2),
        n_parches_fuera_juris=n_fuera,
        ha_fuera_juris=round(ha_fuera, 1),
    ))

    # por municipio
    for mnm, sub in g.groupby('municipio'):
        h = sub['ha'].values
        gr = h > UMBRAL_GRANDE
        dane, subreg, _ = info_mpio.get(mnm, ('', '', np.nan))
        frag_rows.append(dict(
            periodo=per, ano_inicio=a0, ano_fin=a1,
            municipio=mnm, codigo_dane=dane, subregion=subreg,
            n_parches=int(len(sub)),
            ha_total=round(float(h.sum()), 2),
            tamano_medio_ha=round(float(np.mean(h)), 3),
            tamano_mediano_ha=round(float(np.median(h)), 3),
            tamano_max_ha=round(float(np.max(h)), 2),
            pct_parches_grandes=round(100.0 * gr.sum() / len(sub), 2),
            fuente_calidad=('raster_depto_recortado' if per == '2012-2013' else 'shapefile_ok'),
        ))
    print(f'  {per}: {len(g)} parches jurisdiccion | {ha.sum():8.1f} ha'
          + (f'  [+{n_fuera} fuera]' if n_fuera else ''))

frag = pd.DataFrame(frag_rows).sort_values(['periodo', 'ha_total'], ascending=[True, False])
frag.to_csv(os.path.join(OUT, 'fragmentacion.csv'), index=False, encoding='utf-8-sig')
reg = pd.DataFrame(reg_rows).sort_values('ano_inicio')
print(f'[ok] fragmentacion.csv -> {len(frag)} filas (periodo x municipio)')

# ---------------------------------------------------------------------------
# 2. REJILLA 2x2 km  y  RECURRENCIA
# ---------------------------------------------------------------------------
minx, miny, maxx, maxy = juris.bounds
x0 = np.floor(minx / CELL) * CELL
y0 = np.floor(miny / CELL) * CELL
xs = np.arange(x0, maxx + CELL, CELL)
ys = np.arange(y0, maxy + CELL, CELL)
cells = []
cid = 0
for x in xs:
    for y in ys:
        cells.append((cid, box(x, y, x + CELL, y + CELL)))
        cid += 1
grid = gpd.GeoDataFrame({'cell_id': [c[0] for c in cells]},
                        geometry=[c[1] for c in cells], crs=CRS_M)
# conservar solo celdas que intersectan la jurisdiccion
jur_gdf = gpd.GeoDataFrame(geometry=[juris], crs=CRS_M)
grid = gpd.sjoin(grid, jur_gdf, predicate='intersects').drop(columns='index_right')
grid = grid.drop_duplicates('cell_id').reset_index(drop=True)
# area de cada celda DENTRO de la jurisdiccion (ha)
grid['area_celda_ha'] = grid.geometry.intersection(juris).area / 10000.0
print(f'[i] rejilla: {len(grid)} celdas de 2x2 km intersectan la jurisdiccion')

# acumuladores
conteo = {cid: set() for cid in grid['cell_id']}          # periodos con defor
ha_cell = {cid: 0.0 for cid in grid['cell_id']}           # ha acumulada (apportioned)
ha_cell_mpio = {cid: {} for cid in grid['cell_id']}       # ha por municipio en la celda
maxparche = {cid: 0.0 for cid in grid['cell_id']}         # mayor parche que toca la celda

grid_idx = grid[['cell_id', 'geometry']]
for per, gm in patches_by_period.items():
    inter = gpd.overlay(gm, grid_idx, how='intersection', keep_geom_type=True)
    if inter.empty:
        continue
    inter['piece_area'] = inter.geometry.area
    # ha apportioned = ha_parche * (area_pieza / area_parche_geom)
    inter['piece_ha'] = inter['ha'] * (inter['piece_area'] / inter['_pa']).clip(upper=1.0)
    for cid, sub in inter.groupby('cell_id'):
        ph = float(sub['piece_ha'].sum())
        if ph <= 0:
            continue
        conteo[cid].add(per)
        ha_cell[cid] += ph
        maxparche[cid] = max(maxparche[cid], float(sub['ha'].max()))
        for mnm, s2 in sub.groupby('municipio'):
            ha_cell_mpio[cid][mnm] = ha_cell_mpio[cid].get(mnm, 0.0) + float(s2['piece_ha'].sum())

grid['conteo_periodos'] = grid['cell_id'].map(lambda c: len(conteo[c]))
grid['ha_acumuladas'] = grid['cell_id'].map(lambda c: round(ha_cell[c], 2))
grid['tamano_max_parche_ha'] = grid['cell_id'].map(lambda c: round(maxparche[c], 2))
def dom_mpio(c):
    d = ha_cell_mpio[c]
    if not d:
        return ('', '')
    m = max(d, key=d.get)
    return (m, info_mpio.get(m, ('', '', np.nan))[1])
grid['municipio'] = grid['cell_id'].map(lambda c: dom_mpio(c)[0])
grid['subregion'] = grid['cell_id'].map(lambda c: dom_mpio(c)[1])
grid['periodos'] = grid['cell_id'].map(lambda c: ','.join(sorted(conteo[c])))

# distribucion de recurrencia sobre TODAS las celdas con >=1 periodo
dist = grid['conteo_periodos'].value_counts().sort_index()
dist = {int(k): int(v) for k, v in dist.items()}

# exportar celdas persistentes (>=3 periodos) en WGS84
persist = grid[grid['conteo_periodos'] >= UMBRAL_PERSIST].copy()
persist = persist.sort_values(['conteo_periodos', 'ha_acumuladas'], ascending=False)
persist_wgs = persist.to_crs(CRS_WGS)[
    ['cell_id', 'conteo_periodos', 'ha_acumuladas', 'tamano_max_parche_ha',
     'municipio', 'subregion', 'periodos', 'area_celda_ha', 'geometry']].copy()
persist_wgs['area_celda_ha'] = persist_wgs['area_celda_ha'].round(1)
persist_wgs.to_file(os.path.join(OUT, 'recurrencia.geojson'), driver='GeoJSON')
print(f'[ok] recurrencia.geojson -> {len(persist_wgs)} celdas persistentes (>= {UMBRAL_PERSIST} periodos)')

# ---------------------------------------------------------------------------
# 3. ANALISIS: concentracion vs atomizacion, tendencia, frentes
# ---------------------------------------------------------------------------
# 3a. distribucion de tamano de parche (todos los periodos, jurisdiccion)
allp = pd.concat([p[['municipio', 'ha']] for p in patches_by_period.values()], ignore_index=True)
ha_all = np.sort(allp['ha'].values)
n_all = len(ha_all); ha_sum = ha_all.sum()
def share_ha_below(t):  # % del area en parches < t ha
    return round(100.0 * ha_all[ha_all < t].sum() / ha_sum, 2)
def share_n_below(t):
    return round(100.0 * (ha_all < t).sum() / n_all, 2)
# Gini de tamanos de parche
cum = np.cumsum(ha_all)
gini = round(float((n_all + 1 - 2 * (cum / cum[-1]).sum()) / n_all), 4)
# share del area en el 1% y 5% de parches mas grandes
def top_share(frac):
    k = max(1, int(round(frac * n_all)))
    return round(100.0 * ha_all[-k:].sum() / ha_sum, 2)

# 3b. tendencia del tamano medio y mediano en el tiempo (regresion lineal simple)
yrs = reg['ano_inicio'].values.astype(float)
def slope(y):
    return float(np.polyfit(yrs, y, 1)[0])
tend_medio = slope(reg['tamano_medio_ha'].values)
tend_mediano = slope(reg['tamano_mediano_ha'].values)
tend_densidad = slope(reg['densidad_parches_1000ha'].values)
tend_pctgrandes = slope(reg['pct_parches_grandes'].values)
early = reg[reg['ano_inicio'] <= 2010]
late = reg[reg['ano_inicio'] >= 2016]

# 3c. municipios: recurrencia y fragmentacion acumulada
mpio_tot = frag.groupby('municipio').agg(
    n_parches=('n_parches', 'sum'),
    ha_total=('ha_total', 'sum'),
    periodos_activos=('periodo', 'nunique'),
    tamano_max_ha=('tamano_max_ha', 'max')).reset_index()
mpio_tot['tamano_medio_ha'] = (mpio_tot['ha_total'] / mpio_tot['n_parches']).round(3)
mpio_tot = mpio_tot.sort_values('n_parches', ascending=False)

# municipios con mas celdas persistentes
if len(persist):
    pers_mpio = persist.groupby('municipio').agg(
        celdas_persistentes=('cell_id', 'count'),
        ha_acumuladas=('ha_acumuladas', 'sum'),
        conteo_max=('conteo_periodos', 'max')).reset_index()
    pers_mpio = pers_mpio.sort_values('celdas_persistentes', ascending=False)
else:
    pers_mpio = pd.DataFrame()

# top celdas persistentes
top_cells = persist.head(15)[['cell_id', 'conteo_periodos', 'ha_acumuladas',
                              'municipio', 'subregion', 'periodos']].to_dict('records')

resumen = {
    'meta': {
        'tema': 'Fragmentacion y recurrencia espacial de la deforestacion',
        'fuente': 'data/processed/hotspots/*.geojson (parches deforestacion >=1 ha)',
        'jurisdiccion': 'CORPOURABA - 19 municipios',
        'periodos_disponibles': list(reg['periodo']),
        'n_periodos': int(len(reg)),
        'periodos_faltantes': ['2000-2002', '2010-2012', '2014-2015', '2015-2016',
                               '2018-2019', '2023-2024'],
        'base_area': ("columna 'ha' (coherente con serie validada); geometria GeoJSON "
                      "generalizada ~6-8% menor, usada solo para operaciones espaciales"),
        'crs_trabajo': f'EPSG:{CRS_M} (metrico) -> export EPSG:{CRS_WGS}',
        'tamano_celda': '2 x 2 km (400 ha)',
        'notas_calidad': qa,
        'total_ha_jurisdiccion_12periodos': round(float(reg['ha_total'].sum()), 1),
        'total_parches_jurisdiccion': int(reg['n_parches'].sum()),
    },
    'concentracion_vs_atomizacion': {
        'n_parches_total': int(n_all),
        'ha_total': round(float(ha_sum), 1),
        'tamano_medio_ha': round(float(ha_sum / n_all), 3),
        'tamano_mediano_ha': round(float(np.median(ha_all)), 3),
        'pct_parches_menores_2ha': share_n_below(2.0),
        'share_ha_en_parches_menores_2ha': share_ha_below(2.0),
        'pct_parches_menores_5ha': share_n_below(5.0),
        'share_ha_en_parches_menores_5ha': share_ha_below(5.0),
        'pct_parches_mayores_10ha': round(100.0 * (ha_all > UMBRAL_GRANDE).sum() / n_all, 2),
        'share_ha_en_parches_mayores_10ha': round(100.0 * ha_all[ha_all > UMBRAL_GRANDE].sum() / ha_sum, 2),
        'gini_tamano_parche': gini,
        'share_ha_top1pct_parches': top_share(0.01),
        'share_ha_top5pct_parches': top_share(0.05),
        'interpretacion': None,   # se rellena abajo
    },
    'tendencia_tamano_parche': {
        'pendiente_tamano_medio_ha_por_ano': round(tend_medio, 4),
        'pendiente_tamano_mediano_ha_por_ano': round(tend_mediano, 4),
        'pendiente_densidad_parches_1000ha_por_ano': round(tend_densidad, 4),
        'pendiente_pct_parches_grandes_por_ano': round(tend_pctgrandes, 4),
        'tamano_medio_periodo_temprano_<=2010': round(float(early['tamano_medio_ha'].mean()), 3),
        'tamano_medio_periodo_reciente_>=2016': round(float(late['tamano_medio_ha'].mean()), 3),
        'pct_grandes_temprano_<=2010': round(float(early['pct_parches_grandes'].mean()), 2),
        'pct_grandes_reciente_>=2016': round(float(late['pct_parches_grandes'].mean()), 2),
        'serie_por_periodo': reg.to_dict('records'),
    },
    'recurrencia': {
        'n_celdas_jurisdiccion': int(len(grid)),
        'n_celdas_con_deforestacion': int((grid['conteo_periodos'] >= 1).sum()),
        'pct_jurisdiccion_tocada': round(100.0 * (grid['conteo_periodos'] >= 1).sum() / len(grid), 1),
        'distribucion_conteo_periodos': dist,
        'n_celdas_persistentes_>=3': int(len(persist)),
        'ha_acumuladas_en_persistentes': round(float(persist['ha_acumuladas'].sum()), 1),
        'pct_ha_en_persistentes': round(100.0 * persist['ha_acumuladas'].sum() / ha_sum, 1),
        'conteo_periodos_max': int(grid['conteo_periodos'].max()),
        'municipios_mas_celdas_persistentes': pers_mpio.to_dict('records') if len(pers_mpio) else [],
        'top_celdas_persistentes': top_cells,
    },
    'ranking_municipios_fragmentacion': mpio_tot.to_dict('records'),
    'respuestas': {},
}

# interpretacion automatica
c = resumen['concentracion_vs_atomizacion']
c['interpretacion'] = (
    f"Atomizada en numero: {c['pct_parches_menores_5ha']}% de los parches son <5 ha, "
    f"pero concentran solo {c['share_ha_en_parches_menores_5ha']}% del area; el "
    f"{c['share_ha_top5pct_parches']}% del area deforestada se concentra en el 5% "
    f"de parches mas grandes (Gini={c['gini_tamano_parche']}). "
    "Dualidad: numericamente atomizada, pero el area se concentra en pocos parches grandes."
)

top_pers_txt = '; '.join(
    f"{r['municipio']} (celdas x{r['celdas_persistentes']}, {r['ha_acumuladas']:.0f} ha)"
    for r in resumen['recurrencia']['municipios_mas_celdas_persistentes'][:5])
resumen['respuestas'] = {
    'atomiza_o_concentra': c['interpretacion'],
    'tendencia_tamano': (
        f"Tamano medio de parche pasa de {resumen['tendencia_tamano_parche']['tamano_medio_periodo_temprano_<=2010']} ha "
        f"(<=2010) a {resumen['tendencia_tamano_parche']['tamano_medio_periodo_reciente_>=2016']} ha (>=2016); "
        f"pendiente {tend_medio:+.4f} ha/ano. "
        f"% parches grandes (>10 ha): {resumen['tendencia_tamano_parche']['pct_grandes_temprano_<=2010']}% -> "
        f"{resumen['tendencia_tamano_parche']['pct_grandes_reciente_>=2016']}%."),
    'frentes_persistentes': (
        f"{len(persist)} celdas de 2x2 km con deforestacion en >=3 periodos "
        f"({resumen['recurrencia']['ha_acumuladas_en_persistentes']:.0f} ha acumuladas, "
        f"{resumen['recurrencia']['pct_ha_en_persistentes']}% del area). "
        f"Municipios con mas frentes persistentes: {top_pers_txt}."),
}

with open(os.path.join(OUT, 'fragmentacion_resumen.json'), 'w', encoding='utf-8') as fh:
    json.dump(resumen, fh, ensure_ascii=False, indent=2)
print('[ok] fragmentacion_resumen.json')

# ---- salida de consola resumida ----
print('\n===== SINTESIS =====')
print('Concentracion:', c['interpretacion'])
print('Tendencia    :', resumen['respuestas']['tendencia_tamano'])
print('Frentes      :', resumen['respuestas']['frentes_persistentes'])
print('\nTop 8 celdas persistentes:')
for r in top_cells[:8]:
    print(f"  cell {r['cell_id']:>5} | {r['conteo_periodos']} periodos | "
          f"{r['ha_acumuladas']:7.1f} ha | {r['municipio']} ({r['subregion']}) | {r['periodos']}")
print('\nMunicipios por celdas persistentes:')
for r in resumen['recurrencia']['municipios_mas_celdas_persistentes']:
    print(f"  {r['municipio']:<20} celdas={r['celdas_persistentes']:>3}  "
          f"ha={r['ha_acumuladas']:8.1f}  conteo_max={r['conteo_max']}")
