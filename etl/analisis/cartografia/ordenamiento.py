# -*- coding: utf-8 -*-
"""
CONFLICTO DE USO DEL SUELO — Deforestacion vs POF y zonificacion POMCA (CORPOURABA)
===================================================================================
Cruza la cartografia oficial de ordenamiento de CORPOURABA con los hotspots de
deforestacion mapeada del Observatorio para medir cuanta perdida de bosque cae en
zonas cuya zonificacion es de proteccion/conservacion o forestal (conflicto de uso).

Insumos de ordenamiento (SOLO estas dos familias de capas):
  - PLANES DE ORDENACION FORESTAL (POF): Aptitud Forestal_POF, Atrato_POF,
    Uraba_POF, Urrao_POF (columna de zonificacion ZONIFICACI, EPSG:3116).
    Export_Output.shp es duplicado exacto de Aptitud Forestal en CTM12 y se
    descarta; PLANES_ORDENACION_FORESTAL.shp trae solo los limites de los planes
    (contexto) y no se cruza.
  - ZONIFICACION AMBIENTAL POMCAS: 7 zonificaciones aprobadas (columna comun
    ZONI_AMBI, EPSG:3116) + LIMITES_POMCAS (limites) + POMCAS_Sin_Aprobar (contexto).

Insumos del Observatorio:
  - hotspots/<periodo>.geojson  (12 de 18 periodos, WGS84, props {municipio, ha})
  - municipios.geojson          (19 municipios)
  - serie_regional.csv          (18 periodos; total deforestacion ~46.044 ha)

Metodo:
  - CRS real de cada capa -> reproyeccion a EPSG:3115 (MAGNA-SIRGAS / Colombia
    West) para area; ha = area/10000; geometrias invalidas -> buffer(0).
  - Cada categoria original de zonificacion se asigna a un grupo simplificado y
    este a un bucket-objetivo {proteccion/conservacion, forestal, produccion, otro}
    (mapeo documentado en el JSON).
  - Los POF pueden solaparse entre si y POF con POMCA: los totales por bucket usan
    uniones DISUELTAS (unary_union) para no doble-contar; las filas por capa del
    CSV NO deben sumarse entre capas.
  - overlay(intersection) hotspot x categoria para el detalle municipio/categoria.
  - Verificacion: ningun subconjunto de un periodo puede superar la deforestacion
    mapeada del periodo (assert) ni el total regional (serie_regional.csv).

Salidas:
  data/processed/analisis/cartografia/ordenamiento_conflicto.csv
  data/processed/analisis/cartografia/ordenamiento_resumen.json
  data/processed/capas/zonificacion_conflicto.geojson  (proteccion+forestal, WGS84)
  data/processed/analisis/hallazgos_cartografia.json    (append de hallazgos)
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
POF_DIR = CARTO / 'PLANES DE ORDENACIÓN FORESTAL'
POM_DIR = CARTO / 'ZONIFICACION AMBIENTAL POMCAS'
BASE = Path(r'E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion')
PROCESSED = BASE / 'data' / 'processed'
HOTDIR = PROCESSED / 'hotspots'
OUT = PROCESSED / 'analisis' / 'cartografia'
ANALISIS = PROCESSED / 'analisis'
CAPAS = PROCESSED / 'capas'
OUT.mkdir(parents=True, exist_ok=True)
CAPAS.mkdir(parents=True, exist_ok=True)

METRIC = 'EPSG:3115'
WGS84 = 'EPSG:4326'
PERIODO_ANIOS = {p: (i, f) for p, i, f in run_etl.PERIODOS}
PERIODOS_HOT = [p for p, _, _ in run_etl.PERIODOS if (HOTDIR / f'{p}.geojson').exists()]

# ---------------------------------------------------------------------------
# Grupos simplificados de zonificacion y su bucket-objetivo
# ---------------------------------------------------------------------------
PROT = 'proteccion_conservacion'   # bucket-objetivo: proteccion/conservacion
FMIX = 'forestal_protector_mixto'  # bucket-objetivo: forestal
FPRO = 'forestal_productor'        # bucket-objetivo: forestal
USO = 'produccion'                 # bucket-objetivo: produccion
OTRA = 'otro'                      # bucket-objetivo: otro

# grupo simplificado -> bucket-objetivo {proteccion/conservacion, forestal, produccion, otro}
BUCKET = {PROT: 'proteccion_conservacion', FMIX: 'forestal', FPRO: 'forestal',
          USO: 'produccion', OTRA: 'otro'}

GRUPOS_DESC = {
    PROT: ('Proteccion / conservacion: areas forestales protectoras y de reserva (POF), '
           'SINAP, areas protegidas, importancia ambiental, amenazas naturales, '
           'reglamentacion especial, estrategias/areas complementarias de conservacion, '
           'preservacion, conservacion, restauracion/rehabilitacion (ambiental), '
           'recuperacion como zona de manejo ambiental, humedales y cuerpos de agua.'),
    FMIX: ('Forestal protector-productor / sistemas forestales protectores (FPR): bosque '
           'con funcion protectora dominante que admite algun uso sostenible.'),
    FPRO: ('Forestal productor: areas de produccion forestal (AFPD, FPD, bosque en/sin '
           'explotacion). La perdida aqui puede corresponder a aprovechamiento autorizado, '
           'no necesariamente a conflicto.'),
    USO: ('Uso multiple / produccion agropecuaria: cultivos (CPI/CPS/CTI/CTS), pastoreo '
          '(PIN/PSI), sistemas agrosilvicolas/silvopastoriles (AGS/ASP/SPA), areas '
          'agricolas, uso multiple, usos tradicionales, produccion sostenible y '
          'recuperacion PARA el uso multiple.'),
    OTRA: ('Urbano / infraestructura / enclaves licenciados: areas urbanas, asentamientos, '
           'areas licenciadas, titulo minero, desarrollo minero/portuario, PCH, vias.'),
}
# Niveles de conflicto (subconjuntos de grupos)
CONFLICTO_DEF = {
    'conflicto_estricto': [PROT],                # solo proteccion/conservacion estricta
    'conflicto_protector': [PROT, FMIX],         # + forestal protector-productor
    'conflicto_forestal_amplio': [PROT, FMIX, FPRO],  # + forestal productor
}


def sin_tildes(s: str) -> str:
    s = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in s if not unicodedata.combining(c)).upper()


def norm_cat(s) -> str:
    """Categoria original con espacios colapsados (se conserva para el CSV)."""
    return ' '.join(str(s).split()) if pd.notna(s) else 'Sin dato'


def clasificar(cat: str) -> str:
    """Asigna la categoria original a un grupo simplificado (reglas por prioridad).

    El sufijo '(Condicionada/o)' y el simbolo '(C)'/'©' de los POMCA indican
    condicionamiento de uso pero NO cambian la vocacion de la zona -> se ignoran.
    """
    t = sin_tildes(norm_cat(cat))
    t = t.replace('(CONDICIONADA)', '').replace('(CONDICIONADO)', '')
    t = t.replace('(C)', '').replace('()', '')          # '©'->'(C)' via sin_tildes NFKD
    t = ' '.join(t.split())
    if t == 'AIA':                       # Areas de Importancia Ambiental (Directos al Cauca)
        return PROT
    if t == 'CRE':                       # conservacion/recuperacion/recreacion
        return PROT
    # 1) recuperacion PARA el uso multiple -> lado productivo (guia POMCA 2014)
    if 'RECUPERACION PARA' in t and 'MULTIPLE' in t:
        return USO
    # 2) urbano / infraestructura / enclaves licenciados
    if any(k in t for k in ('URBAN', 'ASENTAMIENTO', 'LICENCIAD', 'TITULO MINERO',
                            'DESARROLLO MINERO', 'DESARROLLO PORTUARIO',
                            'CENTRALES HIDROELECTRICAS', 'PEQUENAS CENTRALES', 'VIA AL MAR')):
        return OTRA
    # 3) prefijos codificados de los POF (Aptitud Forestal y Uraba)
    for pref, g in (('AFPD-PP', FPRO), ('AFPD-PR', FMIX), ('AFPP-US', FMIX), ('AFPP', FMIX),
                    ('AFPT-P', PROT), ('AFPT-R', PROT), ('AFPT', PROT), ('ARF', PROT),
                    ('AFPD', FPRO), ('AUM', USO)):
        if t.startswith(pref):
            return g
    # 4) sistemas forestales protectores (FPR) -> protector-productor
    if 'FPR' in t or 'FORESTALES PROTECTORES' in t:
        return FMIX
    # 5) forestal productor
    if any(k in t for k in ('FPD', 'FORESTAL PRODUCTOR', 'BOSQUE EN EXPLOTACION',
                            'BOSQUE SIN EXPLOTACION', 'USO SOSTENIBLE-BOSQUE')):
        return FPRO
    # 6) protectora-productora (Urrao/Uraba texto largo)
    if 'PROTECTORA-PRODUCTORA' in t or 'PROTECTORA PRODUCTORA' in t:
        return FMIX
    # 7) proteccion / conservacion / restauracion
    if any(k in t for k in ('SINAP', 'PROTEGIDA', 'PRESERVACION', 'CONSERVACION',
                            'PROTECCION', 'IMPORTANCIA AMBIENTAL', 'AMENAZAS', 'RESTAUR',
                            'REHABILITACION', 'HUMEDAL', 'CUERPOS DE AGUA',
                            'REGLAMENTACION ESPECIAL', 'COMPLEMENTARIA',
                            'PROTECTORAS', 'FORESTALES PARA LA PROTECCION')):
        return PROT
    # 7b) recuperacion / recuperacion(preserv) sueltas (zona de manejo ambiental)
    if t in ('RECUPERACION', 'RECUPERQACION') or 'RECUPERACION (PRESERV' in t:
        return PROT
    # 8) uso multiple / produccion agropecuaria
    if any(k in t for k in ('CULTIVOS', 'PASTOREO', 'AGROSILV', 'SILVOPAST', 'SILVOPAT',
                            'AGRICOLA', 'USO MULTIPLE', 'USOS TRADICIONALES',
                            'PRODUCCION SOSTENIBLE', 'USO SOSTENIBLE',
                            'AGS', 'ASP', 'SPA', 'CPI', 'CPS', 'CTI', 'CTS', 'PIN', 'PSI')):
        return USO
    return 'sin_mapear'


def fix(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    bad = ~gdf.geometry.is_valid
    if bad.any():
        gdf.loc[bad, 'geometry'] = gdf.loc[bad, 'geometry'].buffer(0)
    return gdf


def cargar_zonificacion(path: Path, capa: str, fuente: str, col_cat: str) -> gpd.GeoDataFrame:
    """Lee shp, normaliza la categoria, clasifica en grupos y disuelve por categoria."""
    g = run_etl.read_shp(path)
    crs_orig = str(g.crs)
    g = fix(g.to_crs(METRIC))
    g['categoria'] = g[col_cat].map(norm_cat)
    g['grupo'] = g['categoria'].map(clasificar)
    dis = g[['categoria', 'grupo', 'geometry']].dissolve(by='categoria', aggfunc='first').reset_index()
    dis = fix(gpd.GeoDataFrame(dis, geometry='geometry', crs=METRIC))
    dis['bucket'] = dis['grupo'].map(BUCKET)
    dis['area_categoria_ha'] = dis.geometry.area / 1e4
    dis['capa'] = capa
    dis['fuente'] = fuente
    sm = dis[dis['grupo'] == 'sin_mapear']
    if len(sm):
        raise SystemExit(f'CATEGORIAS SIN MAPEAR en {capa}: {sm["categoria"].tolist()}')
    print(f'  {capa}: {len(g)} feats -> {len(dis)} categorias | CRS origen {crs_orig} | '
          f'{dis["area_categoria_ha"].sum():,.0f} ha zonificadas')
    return dis


# ---------------------------------------------------------------------------
# [1/5] Jurisdiccion y capas de ordenamiento
# ---------------------------------------------------------------------------

print('[1/5] Municipios y capas de ordenamiento (POF + POMCA) ...')
mun = gpd.read_file(PROCESSED / 'municipios.geojson').to_crs(METRIC)
mun = fix(mun)
mun['area_ha_3115'] = mun.geometry.area / 1e4
U_JUR = unary_union(mun.geometry.values)
jur_ha = U_JUR.area / 1e4
print(f'  jurisdiccion: {len(mun)} municipios, {jur_ha:,.0f} ha')

POF_CAPAS = [  # (archivo, nombre capa, columna categoria)
    ('Aptitud Forestal_POF.shp', 'POF Aptitud Forestal', 'ZONIFICACI'),
    ('Atrato_POF.shp', 'POF Atrato', 'ZONIFICACI'),
    ('Uraba_POF.shp', 'POF Urabá', 'ZONIFICACI'),
    ('Urrao_POF.shp', 'POF Urrao', 'ZONIFICACI'),
]
POM_CAPAS = [
    'Directos al Cauca entre Río San Juan e Ituago',
    'Río Canaletes, Los Córdobas y otros arroyos',
    'Río León', 'Río Mulaticos', 'Río San Juan', 'Río Sucio Alto', 'Río Turbo-Currulao',
]
capas = {}   # nombre -> gdf disuelto por categoria
for shp, nombre, col in POF_CAPAS:
    capas[nombre] = cargar_zonificacion(POF_DIR / shp, nombre, 'POF', col)
for nombre in POM_CAPAS:
    capas[f'POMCA {nombre}'] = cargar_zonificacion(
        POM_DIR / f'{nombre}.shp', f'POMCA {nombre}', 'POMCA', 'ZONI_AMBI')

limites_pomca = fix(run_etl.read_shp(POM_DIR / 'LIMITES_POMCAS.shp').to_crs(METRIC))
sin_aprobar = fix(run_etl.read_shp(POM_DIR / 'POMCAS_Sin_Aprobar.shp').to_crs(METRIC))
U_SIN_APROBAR = unary_union(sin_aprobar.geometry.values)
print(f'  LIMITES_POMCAS: {len(limites_pomca)} cuencas aprobadas, '
      f'{limites_pomca.geometry.area.sum()/1e4:,.0f} ha | '
      f'sin aprobar: {len(sin_aprobar)} cuencas, {U_SIN_APROBAR.area/1e4:,.0f} ha')


# uniones disueltas por fuente y nivel de conflicto (sin doble conteo)
def union_grupos(fuente: str, grupos: list) -> object:
    geoms = [geom for c in capas.values() if c['fuente'].iat[0] == fuente
             for geom in c[c['grupo'].isin(grupos)].geometry.values]
    return unary_union(geoms) if geoms else None


U = {}
TODOS_GRUPOS = [PROT, FMIX, FPRO, USO, OTRA]
for fte in ('POF', 'POMCA'):
    U[(fte, 'cobertura')] = union_grupos(fte, TODOS_GRUPOS)
    for nivel, grupos in CONFLICTO_DEF.items():
        U[(fte, nivel)] = union_grupos(fte, grupos)
# combinacion POF+POMCA sin doble conteo (union disuelta de ambos instrumentos)
U_ANY_PROT = unary_union([U[('POF', 'conflicto_estricto')], U[('POMCA', 'conflicto_estricto')]])
U_ANY_PROTECTOR = unary_union([U[('POF', 'conflicto_protector')], U[('POMCA', 'conflicto_protector')]])
U_ANY_FORESTAL = unary_union([U[('POF', 'conflicto_forestal_amplio')], U[('POMCA', 'conflicto_forestal_amplio')]])

# solapes entre planes POF (sus filas del CSV no deben sumarse entre capas)
pof_cov = {n: unary_union(capas[n].geometry.values) for _, n, _ in POF_CAPAS}
solapes_pof = {}
nombres_pof = list(pof_cov)
for i, a in enumerate(nombres_pof):
    for b in nombres_pof[i + 1:]:
        ha = pof_cov[a].intersection(pof_cov[b]).area / 1e4
        if ha > 1:
            solapes_pof[f'{a} + {b}'] = round(ha, 0)
print('  solapes entre planes POF (ha):', solapes_pof or 'ninguno')

cov_ha = {fte: U[(fte, 'cobertura')].area / 1e4 for fte in ('POF', 'POMCA')}
print(f"  cobertura POF {cov_ha['POF']:,.0f} ha "
      f"({100*U[('POF','cobertura')].intersection(U_JUR).area/1e4/jur_ha:.1f}% jur) | "
      f"POMCA aprobados {cov_ha['POMCA']:,.0f} ha "
      f"({100*U[('POMCA','cobertura')].intersection(U_JUR).area/1e4/jur_ha:.1f}% jur)")

# ---------------------------------------------------------------------------
# [2/5] Cruce hotspots x zonificacion por periodo
# ---------------------------------------------------------------------------

print('[2/5] Cruce hotspots x ordenamiento por periodo ...')
rows = []          # CSV: fuente/capa/periodo/categoria
serie_fuente = []  # JSON: series con uniones disueltas
qa_periodos = []
mun_prot = []      # piezas municipio x conflicto estricto (cualquier instrumento)
ANY_PROT_GDF = gpd.GeoDataFrame({'zona': ['proteccion_cualquier_instrumento']},
                                geometry=[U_ANY_PROT], crs=METRIC)

for pid in PERIODOS_HOT:
    ini, fin = PERIODO_ANIOS[pid]
    ny = max(1, fin - ini)
    h = fix(gpd.read_file(HOTDIR / f'{pid}.geojson').to_crs(METRIC))
    if 'municipio' in h.columns:
        h['municipio'] = h['municipio'].fillna('Sin asignar')
    else:
        h['municipio'] = 'Sin asignar'
    h['ha_geo'] = h.geometry.area / 1e4
    tot = float(h['ha_geo'].sum())

    fila = {'periodo': pid, 'ano_inicio': ini, 'ano_fin': fin,
            'defo_mapeada_ha': round(tot, 1)}
    for fte in ('POF', 'POMCA'):
        for clave in ('cobertura', 'conflicto_estricto', 'conflicto_protector',
                      'conflicto_forestal_amplio'):
            a = float(h.geometry.intersection(U[(fte, clave)]).area.sum()) / 1e4
            assert a <= tot + 0.5, f'{pid} {fte} {clave}: {a} > total {tot}'
            fila[f'{fte.lower()}_{clave}_ha'] = round(a, 1)
    for clave, geom in (('cualquiera_proteccion', U_ANY_PROT),
                        ('cualquiera_protector', U_ANY_PROTECTOR),
                        ('cualquiera_forestal_amplio', U_ANY_FORESTAL),
                        ('pomca_sin_aprobar', U_SIN_APROBAR)):
        a = float(h.geometry.intersection(geom).area.sum()) / 1e4
        assert a <= tot + 0.5, f'{pid} {clave}: {a} > total {tot}'
        fila[f'{clave}_ha'] = round(a, 1)
    serie_fuente.append(fila)

    # detalle por capa x categoria (overlay conserva municipio para los tops)
    for nombre, capa in capas.items():
        ov = gpd.overlay(h[['municipio', 'geometry']],
                         capa[['categoria', 'grupo', 'bucket', 'geometry']],
                         how='intersection', keep_geom_type=True)
        ov['ha'] = ov.geometry.area / 1e4 if len(ov) else 0.0
        por_cat = ov.groupby('categoria')['ha'].sum() if len(ov) else pd.Series(dtype=float)
        for _, r in capa.iterrows():
            ha = float(por_cat.get(r['categoria'], 0.0))
            rows.append({'fuente': r['fuente'], 'capa': nombre, 'periodo': pid,
                         'ano_inicio': ini, 'ano_fin': fin,
                         'categoria': r['categoria'], 'grupo': r['grupo'],
                         'bucket': r['bucket'],
                         'hectareas': round(ha, 2),
                         'hectareas_anuales': round(ha / ny, 2),
                         'pct_defo_mapeada_periodo': round(100 * ha / tot, 2) if tot else 0.0,
                         'area_categoria_ha': round(float(r['area_categoria_ha']), 1),
                         'deforestacion_mapeada_periodo_ha': round(tot, 2)})

    ovp = gpd.overlay(h[['municipio', 'geometry']], ANY_PROT_GDF,
                      how='intersection', keep_geom_type=True)
    if len(ovp):
        ovp['ha'] = ovp.geometry.area / 1e4
        ovp['periodo'] = pid
        mun_prot.append(pd.DataFrame(ovp.drop(columns='geometry')))

    ha_prop = round(float(h['ha'].sum()), 1) if 'ha' in h.columns else None
    qa_periodos.append({'periodo': pid, 'n_hotspots': int(len(h)),
                        'ha_geometrica': round(tot, 1), 'ha_propiedad': ha_prop})
    print(f"  {pid}: {len(h):>4} hotspots {tot:>9,.1f} ha | POF prot "
          f"{fila['pof_conflicto_estricto_ha']:>8,.1f} | POMCA prot "
          f"{fila['pomca_conflicto_estricto_ha']:>8,.1f} | cualquiera prot "
          f"{fila['cualquiera_proteccion_ha']:>8,.1f}")

df = pd.DataFrame(rows)
df.to_csv(OUT / 'ordenamiento_conflicto.csv', index=False, encoding='utf-8-sig')
print('csv ->', OUT / 'ordenamiento_conflicto.csv', f'({len(df)} filas)')

# ---------------------------------------------------------------------------
# [3/5] Agregados
# ---------------------------------------------------------------------------

print('[3/5] Agregados ...')
sf = pd.DataFrame(serie_fuente)
tot_map = float(sf['defo_mapeada_ha'].sum())
pct = lambda a, b: round(100 * a / b, 2) if b else None

tot_espacial = {c: round(float(sf[c].sum()), 1) for c in sf.columns
                if c.endswith('_ha') and c != 'defo_mapeada_ha'}
por_grupo_fuente = (df.groupby(['fuente', 'grupo'])['hectareas'].sum().round(1)
                    .unstack(fill_value=0.0).to_dict('index'))
por_capa_grupo = (df.groupby(['capa', 'grupo'])['hectareas'].sum().round(1)
                  .unstack(fill_value=0.0))

reg = pd.read_csv(PROCESSED / 'serie_regional.csv')
reg_defo = reg[reg['clase'] == 'Deforestación']
serie_total_18p = float(reg_defo['hectareas'].sum())
serie_12p = float(reg_defo[reg_defo['periodo'].isin(PERIODOS_HOT)]['hectareas'].sum())

mp = pd.concat(mun_prot, ignore_index=True) if mun_prot else pd.DataFrame(columns=['municipio', 'ha'])
top_mun_prot = (mp.groupby('municipio')['ha'].sum().sort_values(ascending=False)
                .head(12).round(1).reset_index()
                .rename(columns={'ha': 'deforestacion_en_proteccion_ha'}).to_dict('records'))

top_cat = (df.groupby(['fuente', 'capa', 'categoria', 'grupo', 'bucket'])['hectareas'].sum()
           .sort_values(ascending=False).head(15).round(1).reset_index()
           .rename(columns={'hectareas': 'deforestacion_ha'}).to_dict('records'))

# ranking por periodo del % en proteccion (cualquier instrumento)
ranking_periodos = (sf[['periodo', 'defo_mapeada_ha', 'cualquiera_proteccion_ha']].copy())
ranking_periodos['pct_en_proteccion'] = (
    100 * ranking_periodos['cualquiera_proteccion_ha'] / ranking_periodos['defo_mapeada_ha']).round(2)
ranking_periodos = ranking_periodos.sort_values('pct_en_proteccion', ascending=False).to_dict('records')

# tendencia por bloques
bloques = {'2002_2010': ['2002-2004', '2004-2006', '2006-2008', '2008-2010'],
           '2012_2018': ['2012-2013', '2013-2014', '2016-2017', '2017-2018'],
           '2019_2023': ['2019-2020', '2020-2021', '2021-2022', '2022-2023']}
tend = {}
for bl, pids in bloques.items():
    sub = sf[sf['periodo'].isin(pids)]
    anos = sum(PERIODO_ANIOS[p][1] - PERIODO_ANIOS[p][0] for p in pids)
    tm = float(sub['defo_mapeada_ha'].sum())
    prot = float(sub['cualquiera_proteccion_ha'].sum())
    fore = float(sub['cualquiera_forestal_amplio_ha'].sum())
    tend[bl] = {'anos_cubiertos': anos, 'defo_mapeada_ha': round(tm, 1),
                'en_proteccion_ha': round(prot, 1),
                'en_proteccion_ha_anual': round(prot / anos, 1),
                'pct_en_proteccion': pct(prot, tm),
                'en_forestal_amplio_ha': round(fore, 1),
                'pct_en_forestal_amplio': pct(fore, tm)}

# ---------------------------------------------------------------------------
# [4/5] Capa web zonificacion_conflicto.geojson (proteccion + forestal)
# ---------------------------------------------------------------------------

print('[4/5] Capa web zonificacion_conflicto.geojson ...')
# deforestacion total (12 periodos) por categoria (para la propiedad de la capa)
defo_cat = df.groupby(['capa', 'categoria'])['hectareas'].sum()

# una fila por (capa, categoria) de proteccion o forestal, geometria disuelta
piezas_web = []
for nombre, capa in capas.items():
    sel = capa[capa['bucket'].isin(['proteccion_conservacion', 'forestal'])]
    for _, r in sel.iterrows():
        piezas_web.append({
            'nombre': f"{nombre} :: {r['categoria']}",
            'categoria': BUCKET[r['grupo']],   # bucket-objetivo
            'grupo': r['grupo'],
            'fuente': r['fuente'],
            'deforestacion_ha_total': round(float(defo_cat.get((nombre, r['categoria']), 0.0)), 1),
            'geometry': r['geometry'],
        })
web = gpd.GeoDataFrame(piezas_web, geometry='geometry', crs=METRIC)
# recorta a la jurisdiccion para reducir peso (la zonificacion se extiende fuera)
web['geometry'] = web.geometry.intersection(U_JUR)
web = web[~web.geometry.is_empty & web.geometry.notna()]
web = fix(web)
# recorta el nombre a algo razonable
web['nombre'] = web['nombre'].map(lambda s: s if len(s) <= 90 else s[:87] + '...')

capa_path = CAPAS / 'zonificacion_conflicto.geojson'
tol_final = None
for tol in (60, 100, 150, 220, 300, 400):
    w = web.copy()
    w['geometry'] = w.geometry.simplify(tol, preserve_topology=True)
    w = w[~w.geometry.is_empty & w.geometry.notna()]
    w = fix(w).to_crs(WGS84)
    if capa_path.exists():
        capa_path.unlink()
    w.to_file(capa_path, driver='GeoJSON', COORDINATE_PRECISION=5)
    kb = capa_path.stat().st_size / 1024
    print(f'  tolerancia {tol} m -> {kb:.0f} KB ({len(w)} features)')
    tol_final = tol
    if kb < 500:
        break

# ---------------------------------------------------------------------------
# [5/5] Resumen JSON + hallazgos
# ---------------------------------------------------------------------------

print('[5/5] Resumen JSON ...')
# mapeo documentado: categoria original -> grupo -> bucket
mapeo_doc = {n: {c['categoria']: {'grupo': c['grupo'], 'bucket': c['bucket']}
                 for _, c in cap.sort_values('categoria').iterrows()}
             for n, cap in capas.items()}

# totales por bucket-objetivo (uniones disueltas POF+POMCA, sin doble conteo)
defo_proteccion = tot_espacial['cualquiera_proteccion_ha']
defo_protector = tot_espacial['cualquiera_protector_ha']
defo_forestal_amplio = tot_espacial['cualquiera_forestal_amplio_ha']

resumen = {
    'titulo': ('Conflicto de uso del suelo — deforestacion mapeada vs zonificacion de '
               'proteccion/forestal (POF y POMCA), jurisdiccion CORPOURABA'),
    'fuentes': {
        'pof': ('PLANES DE ORDENACION FORESTAL: Aptitud Forestal_POF, Atrato_POF, '
                'Uraba_POF, Urrao_POF (columna ZONIFICACI, CRS origen EPSG:3116). '
                'Export_Output.shp es duplicado de Aptitud Forestal en CTM12 y se descarto; '
                'PLANES_ORDENACION_FORESTAL.shp trae solo limites y no se cruza.'),
        'pomca': ('ZONIFICACION AMBIENTAL POMCAS: 7 zonificaciones aprobadas '
                  '(columna comun ZONI_AMBI, CRS origen EPSG:3116) + LIMITES_POMCAS + '
                  'POMCAS_Sin_Aprobar (contexto).'),
        'observatorio': ('hotspots/<periodo>.geojson (12 periodos, WGS84, props municipio/ha); '
                         'municipios.geojson (19); serie_regional.csv (18 periodos).'),
    },
    'metodo': ('CRS real de cada capa -> reproyeccion a EPSG:3115 para area (ha=area/10000); '
               'geometrias invalidas -> buffer(0); overlay(intersection) hotspot x categoria. '
               'Totales por bucket con uniones disueltas (unary_union) POF+POMCA para no '
               'doble-contar. Las capas POF se solapan entre si: las filas por capa del CSV '
               'no deben sumarse entre capas.'),
    'unidad': 'hectareas (area geometrica EPSG:3115)',
    'buckets_objetivo': {
        'proteccion_conservacion': 'Zonas de proteccion o conservacion (grupo proteccion_conservacion).',
        'forestal': 'Zonas forestales (grupos forestal_protector_mixto + forestal_productor).',
        'produccion': 'Uso multiple / produccion agropecuaria (grupo produccion).',
        'otro': 'Urbano / infraestructura / enclaves licenciados (grupo otro).',
    },
    'grupos_simplificados': GRUPOS_DESC,
    'grupo_a_bucket': BUCKET,
    'definiciones_conflicto': {
        'conflicto_estricto': 'proteccion_conservacion (bucket proteccion/conservacion)',
        'conflicto_protector': 'proteccion_conservacion + forestal_protector_mixto',
        'conflicto_forestal_amplio': 'proteccion_conservacion + forestal (protector + productor)',
    },
    'mapeo_categorias': mapeo_doc,
    'notas_mapeo': [
        'El sufijo (Condicionada/o) y el simbolo (C)/copyright de los POMCA indican '
        'condicionamiento de uso pero no cambian la vocacion de la zona: se ignoran al clasificar.',
        'Recuperacion / Recuperqacion (POMCA Mulaticos), Recuperacion y Recuperacion(Preserv '
        'por Inundac) (POMCA San Juan) se asignan a proteccion_conservacion: en esos POMCA la '
        'recuperacion es una zona de manejo ambiental. Es una decision documentada y discutible.',
        'Toda "recuperacion PARA el uso multiple" va a produccion (guia POMCA 2014).',
        'Humedal (POF Atrato) y Cuerpos de Agua Naturales (POMCA Canaletes) -> proteccion_conservacion.',
        'Areas con Reglamentacion Especial (territorios etnicos, etc.), AIA y CRE cuentan como '
        'proteccion_conservacion segun la estructura de la guia POMCA (subzona de proteccion).',
        'AFPD/FPD (forestal productor) y sistemas forestales protectores FPR (protector-productor) '
        'se separan de la proteccion estricta: por eso el conflicto se reporta en tres niveles.',
        'Titulo Minero, PCH, Via al Mar, desarrollo minero/portuario, areas licenciadas, urbanas '
        'y asentamientos -> otro.',
    ],
    'cobertura_instrumentos': {
        'jurisdiccion_ha': round(jur_ha, 0),
        'pof_cobertura_ha': round(cov_ha['POF'], 0),
        'pof_pct_jurisdiccion': pct(U[('POF', 'cobertura')].intersection(U_JUR).area / 1e4, jur_ha),
        'pomca_aprobados_ha': round(cov_ha['POMCA'], 0),
        'pomca_pct_jurisdiccion': pct(U[('POMCA', 'cobertura')].intersection(U_JUR).area / 1e4, jur_ha),
        'pomca_sin_aprobar_ha': round(U_SIN_APROBAR.area / 1e4, 0),
        'solapes_entre_planes_pof_ha': solapes_pof,
        'area_por_capa_y_grupo_ha': {c: {g: round(v, 0) for g, v in
                                         (capas[c].groupby('grupo')['area_categoria_ha'].sum()).items()}
                                     for c in capas},
    },
    'conflicto_uso_totales_12_periodos_mapeados': {
        'deforestacion_mapeada_ha': round(tot_map, 1),
        'en_proteccion_conservacion_ha': defo_proteccion,
        'pct_en_proteccion_conservacion': pct(defo_proteccion, tot_map),
        'en_proteccion_mas_forestal_protector_ha': defo_protector,
        'pct_en_proteccion_mas_forestal_protector': pct(defo_protector, tot_map),
        'en_proteccion_mas_forestal_amplio_ha': defo_forestal_amplio,
        'pct_en_proteccion_mas_forestal_amplio': pct(defo_forestal_amplio, tot_map),
        'detalle_por_fuente_y_nivel_ha': {k: {'hectareas': v, 'pct_defo_mapeada': pct(v, tot_map)}
                                          for k, v in tot_espacial.items()},
        'nota': ('cualquiera_* combina POF y POMCA con union disuelta (sin doble conteo). '
                 'No sumar POF + POMCA porque se solapan territorialmente. Ningun valor '
                 'supera la deforestacion mapeada del periodo (asserts) ni el total regional.'),
    },
    'deforestacion_por_grupo_y_fuente_ha': por_grupo_fuente,
    'deforestacion_por_capa_y_grupo_ha': {c: {g: float(v) for g, v in r.items() if v > 0}
                                          for c, r in por_capa_grupo.iterrows()},
    'serie_por_periodo': serie_fuente,
    'ranking_periodos_por_pct_en_proteccion': ranking_periodos,
    'tendencia_por_bloques': tend,
    'top_categorias_por_deforestacion': top_cat,
    'top_municipios_deforestacion_en_proteccion': top_mun_prot,
    'capa_web': {'ruta': str(capa_path),
                 'tolerancia_simplificacion_m': tol_final,
                 'tamano_kb': round(capa_path.stat().st_size / 1024, 0),
                 'contenido': 'zonas de proteccion/conservacion y forestales, con deforestacion_ha_total (12 periodos)'},
    'contexto_cobertura_temporal': {
        'periodos_con_hotspots': PERIODOS_HOT,
        'n_periodos_mapeados': len(PERIODOS_HOT),
        'n_periodos_serie': 18,
        'deforestacion_serie_12_periodos_ha': round(serie_12p, 1),
        'deforestacion_serie_18_periodos_ha': round(serie_total_18p, 1),
        'pct_serie_cubierta_por_hotspots': pct(serie_12p, serie_total_18p),
        'nota': ('Todos los porcentajes son "de la deforestacion MAPEADA" (hotspots >=1 ha '
                 'de 12 de los 18 periodos, ~{:.0f}% de la serie), NO del total 2000-2024.'
                 .format(100 * serie_12p / serie_total_18p)),
    },
    'qa': {
        'por_periodo': qa_periodos,
        'ningun_subconjunto_supera_total_mapeado': True,   # asserts en [2/5]
        'ningun_subconjunto_supera_total_regional': bool(
            defo_forestal_amplio <= serie_total_18p and tot_map <= serie_total_18p + 1),
        'defo_mapeada_geometrica_ha': round(tot_map, 1),
        'serie_regional_12p_ha': round(serie_12p, 1),
        'serie_regional_18p_ha': round(serie_total_18p, 1),
    },
    'notas': [
        'Se usa "deforestacion mapeada": hotspots >=1 ha de 12 de los 18 periodos '
        '(~{:.0f}% de la serie regional); NO es el total 2000-2024.'.format(
            100 * serie_12p / serie_total_18p),
        'Los planes POF se solapan entre si (ver solapes_entre_planes_pof_ha) y POF con '
        'POMCA: las filas por capa del CSV no deben sumarse entre capas; los totales por '
        'bucket/nivel usan uniones disueltas (unary_union) sin doble conteo.',
        'Los instrumentos son fotos actuales del ordenamiento; cruzarlos con deforestacion '
        'historica es retrospectivo (parte de la perdida puede ser anterior a la aprobacion '
        'del plan). Coincidencia espacial no implica atribucion causal.',
        'En zonas forestal_productor la perdida puede corresponder a aprovechamiento '
        'autorizado; por eso el conflicto se reporta en tres niveles (estricto, protector, amplio).',
        'El area geometrica de los hotspots difiere levemente de serie_regional.csv porque '
        'son poligonos >=1 ha simplificados.',
    ],
}
(OUT / 'ordenamiento_resumen.json').write_text(
    json.dumps(resumen, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
print('json ->', OUT / 'ordenamiento_resumen.json')

# ---------------------------------------------------------------------------
# hallazgos_cartografia.json (crear o append sin borrar)
# ---------------------------------------------------------------------------
hall_path = ANALISIS / 'hallazgos_cartografia.json'
existentes = []
if hall_path.exists():
    try:
        existentes = json.loads(hall_path.read_text(encoding='utf-8'))
        if not isinstance(existentes, list):
            existentes = []
    except Exception:
        existentes = []
ids_prev = {h.get('id') for h in existentes if isinstance(h, dict)}

periodo_top = ranking_periodos[0]
bl_ultimo = tend['2019_2023']
nuevos = [
    {'id': 'ordenamiento_defo_en_proteccion',
     'tema': 'ordenamiento',
     'titulo': 'Deforestación en zonas de protección/conservación',
     'cifra': defo_proteccion,
     'unidad': 'ha',
     'periodo_referencia': '12 periodos mapeados',
     'descripcion': (f'{defo_proteccion:,.0f} ha de la deforestacion mapeada ({pct(defo_proteccion, tot_map)}% '
                     f'de {tot_map:,.0f} ha) cayeron en zonas zonificadas como proteccion/conservacion '
                     f'por POF o POMCA (union disuelta, sin doble conteo).'),
     'relevancia': 9},
    {'id': 'ordenamiento_defo_forestal_amplio',
     'tema': 'ordenamiento',
     'titulo': 'Pérdida en zonas de protección o forestales',
     'cifra': defo_forestal_amplio,
     'unidad': 'ha',
     'periodo_referencia': '12 periodos mapeados',
     'descripcion': (f'{defo_forestal_amplio:,.0f} ha ({pct(defo_forestal_amplio, tot_map)}% de lo mapeado) '
                     f'cayeron en zonas de proteccion o forestales (protector + productor) segun POF/POMCA; '
                     f'parte de la porcion forestal-productor puede ser aprovechamiento autorizado.'),
     'relevancia': 8},
    {'id': 'ordenamiento_periodo_pico_proteccion',
     'tema': 'ordenamiento',
     'titulo': 'Periodo con mayor conflicto en protección',
     'cifra': periodo_top['pct_en_proteccion'],
     'unidad': '% de la defo mapeada',
     'periodo_referencia': periodo_top['periodo'],
     'descripcion': (f'En {periodo_top["periodo"]} el {periodo_top["pct_en_proteccion"]}% de la deforestacion '
                     f'mapeada ({periodo_top["cualquiera_proteccion_ha"]:,.0f} de '
                     f'{periodo_top["defo_mapeada_ha"]:,.0f} ha) ocurrio en zonas de proteccion/conservacion, '
                     f'el mayor porcentaje de los 12 periodos.'),
     'relevancia': 7},
    {'id': 'ordenamiento_top_municipio_proteccion',
     'tema': 'ordenamiento',
     'titulo': f'Municipio con más deforestación en protección: {top_mun_prot[0]["municipio"]}',
     'cifra': top_mun_prot[0]['deforestacion_en_proteccion_ha'],
     'unidad': 'ha',
     'periodo_referencia': '12 periodos mapeados',
     'descripcion': (f'{top_mun_prot[0]["municipio"]} concentra {top_mun_prot[0]["deforestacion_en_proteccion_ha"]:,.0f} '
                     f'ha de deforestacion mapeada dentro de zonas de proteccion/conservacion (cualquier '
                     f'instrumento), el mayor de la jurisdiccion.'),
     'relevancia': 7},
]
combinado = existentes + [h for h in nuevos if h['id'] not in ids_prev]
# si ya existian con ese id, actualiza en sitio
by_id = {h['id']: h for h in nuevos}
combinado = [by_id.get(h['id'], h) if isinstance(h, dict) and h.get('id') in by_id else h
             for h in combinado]
hall_path.write_text(json.dumps(combinado, ensure_ascii=False, indent=1, default=str),
                     encoding='utf-8')
print('hallazgos ->', hall_path, f'({len(combinado)} objetos, +{len([h for h in nuevos if h["id"] not in ids_prev])} nuevos)')

# ---------------------------------------------------------------------------
# Consola: hallazgos
# ---------------------------------------------------------------------------
print('\n=== CONFLICTO DE USO (12 periodos mapeados) ===')
print(f'Deforestacion mapeada: {tot_map:,.1f} ha '
      f'(serie 12p: {serie_12p:,.1f} ha; serie 18p: {serie_total_18p:,.1f} ha)')
print(f'  En proteccion/conservacion:        {defo_proteccion:>9,.1f} ha  '
      f'({pct(defo_proteccion, tot_map)}% de lo mapeado)')
print(f'  + forestal protector (mixto):      {defo_protector:>9,.1f} ha  '
      f'({pct(defo_protector, tot_map)}%)')
print(f'  + forestal productor (amplio):     {defo_forestal_amplio:>9,.1f} ha  '
      f'({pct(defo_forestal_amplio, tot_map)}%)')
print('\n=== DESGLOSE ESPACIAL (uniones disueltas) ===')
for k, v in tot_espacial.items():
    print(f'  {k:<34} {v:>9,.1f} ha  ({pct(v, tot_map)}%)')
print('\n=== POR GRUPO Y FUENTE (suma de capas; puede haber solapes entre capas) ===')
for fte, d in por_grupo_fuente.items():
    print(f'  {fte}: ' + ' | '.join(f'{g}={v:,.0f}' for g, v in sorted(d.items())))
print('\n=== TOP CATEGORIAS ===')
for r in top_cat[:10]:
    print(f"  {r['deforestacion_ha']:>8,.1f} ha  [{r['grupo']}] {r['capa']} :: {r['categoria'][:60]}")
print('\n=== TOP MUNICIPIOS (defo en proteccion, cualquier instrumento) ===')
for r in top_mun_prot[:8]:
    print(f"  {r['deforestacion_en_proteccion_ha']:>8,.1f} ha  {r['municipio']}")
print('\n=== RANKING PERIODOS POR % EN PROTECCION ===')
for r in ranking_periodos:
    print(f"  {r['periodo']}: {r['pct_en_proteccion']:>5.1f}%  "
          f"({r['cualquiera_proteccion_ha']:,.1f} / {r['defo_mapeada_ha']:,.1f} ha)")
print('\n=== TENDENCIA POR BLOQUES ===')
for bl, d in tend.items():
    print(f"  {bl}: proteccion {d['en_proteccion_ha_anual']:,.1f} ha/ano ({d['pct_en_proteccion']}%) | "
          f"forestal amplio {d['pct_en_forestal_amplio']}%")
print('\nOK')
