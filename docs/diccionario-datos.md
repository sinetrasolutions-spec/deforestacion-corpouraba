# Diccionario de datos — Observatorio de Deforestación CORPOURABA

Describe todos los productos de `data/processed/` (generados por `etl/run_etl.py` y
los scripts de `etl/analisis/`). Regeneración: `python etl/run_etl.py`.

## 1. serie_municipal.csv (serie principal, 1.123+ filas)

Una fila por municipio × periodo × clase de cobertura.

| Columna | Tipo | Descripción |
|---|---|---|
| `codigo_dane` | texto (5) | Código DANE del municipio, con cero inicial (`05045`) |
| `municipio` | texto | Nombre oficial con tildes (`Apartadó`) |
| `subregion` | texto | Subregión CORPOURABA: `Caribe`, `Centro`, `Atrato`, `Nutibara`, `Urrao` |
| `periodo` | texto | Periodo de monitoreo (`2002-2004`); 18 periodos entre 2000 y 2024 |
| `ano_inicio` / `ano_fin` | entero | Años extremos del periodo (los 5 primeros duran 2 años) |
| `clase` | texto | `Bosque Estable` · `Deforestación` · `No Bosque Estable` · `Regeneración` · `Sin Información` |
| `hectareas` | decimal | Hectáreas de la clase en el municipio y periodo |
| `hectareas_anuales` | decimal | `hectareas / años del periodo` — **usar siempre para comparar periodos** |
| `fuente` | texto | `shapefile` · `excel` · `cuencas-calibrado` · `raster` · `estimado` · `estimado-calibrado-rat` |
| `estimado` | booleano | `True` = sin medición municipal directa; tratar como referencia |

**Correspondencia gridcode** (rásters y capas originales): 1 = Bosque Estable,
2 = Deforestación, 3 = Sin Información, 4 = Regeneración, 5 = No Bosque Estable.

**Periodos estimados/calibrados**: `2010-2012` (total departamental real del RAT ×
participación ~18% de la jurisdicción), `2015-2016` (cuencas calibradas con factores
municipio×clase de 2016-2017), `2018-2019` (interpolación), `2023-2024` (tendencia).
Para los periodos estimados solo existe la clase `Deforestación`.

**Control de calidad**: diferencia ≤0,3% frente a las hojas «Cálculos» de los Excel
institucionales en los 10 periodos comparables (ver `metadata.json → qa_calculos`).

## 2. serie_regional.csv

Agregado regional: `periodo, ano_inicio, ano_fin, clase, hectareas, hectareas_anuales,
estimado` (estimado = True si algún municipio del periodo es estimado).
Total Deforestación 2000-2024 ≈ **46.041 ha**.

## 3. municipios.geojson / subregiones.geojson

WGS84 (EPSG:4326), simplificados para web (tolerancia 80 m).
Properties de municipios: `municipio_key`, `codigo_dane`, `nombre`, `subregion`,
`area_municipio_ha`, `centroide` `[lon, lat]`. Origen: disolución de la capa municipal
2021-2022 (EPSG:3115), huecos internos <1 km² eliminados.

## 4. hotspots/&lt;periodo&gt;.geojson (12 periodos)

Polígonos de deforestación **≥1 ha**, simplificados (40 m), WGS84.
Properties: `municipio` (nombre o null), `ha`. Disponibles: 2002-2004, 2004-2006,
2006-2008, 2008-2010, 2012-2013 (vectorizado del ráster), 2013-2014, 2016-2017,
2017-2018, 2019-2020, 2020-2021, 2021-2022, 2022-2023 — cubren ≈87% de la
deforestación medida. «Deforestación mapeada» en los análisis = este subconjunto.

## 5. capas/*.geojson (overlays del mapa)

| Capa | Unidades | Origen | Properties clave |
|---|---|---|---|
| `areas_protegidas` | 21 | paquete de monitoreo 2022-2023 | `nombre`, `categoria`, `area_ha`, `deforestacion_ha_ultimo_periodo` |
| `resguardos` | 39 | ídem | `nombre`, `pueblo`, ídem |
| `consejos` | 7 | ídem | `nombre`, ídem |
| `cuencas` | 7 | ídem | `nomb_cuenc`, ídem |
| `titulos_mineros` | 537 | cartografía oficial (ANM) | `nombre`, titular/mineral/estado, `deforestacion_ha_total` |
| `resguardos_oficial` | 40 | cartografía oficial | `nombre`, `deforestacion_ha_total` |
| `comunidades_negras_oficial` | 12 | cartografía oficial | `nombre`, `deforestacion_ha_total` |
| *(+ las que agregue la investigación cartográfica: `ley_segunda`, `areas_protegidas_oficial`, `ecosistemas_estrategicos`, `pdet`)* | | | |

## 6. analisis/ (productos de la investigación temática)

Tablas CSV (UTF-8 BOM) y resúmenes JSON por línea de investigación; servidos por
`/api/v1/analisis/*`:

- `areas_protegidas_serie.csv` — AP × periodo × clase (10 periodos comparables)
- `resguardos_serie.csv` / `consejos_serie.csv` — territorios étnicos × periodo × clase
- `cuencas_serie.csv` — cuenca × periodo × clase, con flags de calidad de área
- `dinamica_bosque.csv` — municipio × periodo: bosque estable, no bosque, regeneración,
  sin información, deforestación, `pct_cobertura_bosque`, `tasa_perdida_relativa`
  (pérdida anual / bosque previo), `cambio_neto_ha`
- `fragmentacion.csv` — periodo × municipio: `n_parches`, `ha_total`, tamaños
  (medio/mediano/máx), `pct_parches_grandes` (>10 ha)
- `recurrencia.geojson` — celdas 2×2 km con deforestación en ≥3 periodos
  (`conteo_periodos`, `ha_acumuladas`, `municipio`) — «frentes persistentes»
- `hallazgos.json` — hallazgos verificados para la plataforma:
  `{id, tema, titulo, cifra, unidad, periodo_referencia, descripcion, relevancia}`
- `cartografia/*.csv|json` — cruces con la cartografía oficial (minería, territorios
  oficiales, figuras de protección, ecosistemas, ordenamiento/PDET) +
  `hallazgos_cartografia.json`

## 7. metadata.json

Diccionario maestro: periodos con su fuente, municipios con códigos DANE, notas
metodológicas (`nota_estimados`, `nota_2015_2016`), QA contra hojas Cálculos, log del
ETL. Servido íntegro en `/api/v1/metadata`.

## 8. CRS y unidades

- **Origen**: EPSG:3115 (MAGNA-SIRGAS / Colombia Oeste) y MAGNA-SIRGAS Bogotá
  (≈EPSG:3116); áreas calculadas siempre en CRS métrico (`ha = m²/10.000`).
- **Salida web**: EPSG:4326 (WGS84), coordenadas con 5 decimales.
- Rásters `DEPTO_ANTIOQUIA_*`: 30 m nominal (~0,093 ha/píxel), cubren TODO el
  departamento — los totales de su RAT no son comparables con la jurisdicción sin
  ajustar por participación.

## 9. Atribución sugerida

> CORPOURABA — Observatorio de Deforestación de Urabá (2000-2024). Datos procesados
> del monitoreo institucional de bosque. Plataforma creada por Alberto Vivas y
> Carlos Zuluaga.
