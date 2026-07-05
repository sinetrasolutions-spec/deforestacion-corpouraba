# Metodología y Fuentes de Datos

## 1. Propósito del documento

Este documento describe de forma técnica y verificable cómo se construyó la información que alimenta el **Observatorio de Deforestación CORPOURABA 2000–2024**. Detalla las fuentes institucionales empleadas, la unidad de análisis y el sistema de clases, los sistemas de referencia, el proceso de transformación de datos (ETL), la lógica de priorización de la mejor fuente por periodo, el tratamiento de los periodos estimados, la recuperación de 2015-2016 como dato medido, los cruces temáticos con la cartografía oficial, el control de calidad aplicado y las limitaciones conocidas del dato.

El principio rector es la **trazabilidad**: cada cifra publicada en la plataforma proviene de un archivo fuente identificable, y todo dato que no procede de una medición directa está marcado explícitamente como referencial.

## 2. Fuentes de datos

### 2.1 Paquete institucional de monitoreo de cambio de bosque

La base del Observatorio es el paquete oficial de monitoreo de cambio de bosque de CORPOURABA, organizado por **periodos de cambio** que cubren la jurisdicción de 19 municipios entre 2000 y 2024 (18 periodos). Este paquete combina tres tipos de insumos:

- **Shapefiles municipales** de cambio de bosque por periodo (por ejemplo `Defor2021_2022_Mpios_Proj_Correg.shp`), con la geometría y la tabla de atributos de área por municipio y clase de cobertura.
- **Tablas Excel** con las hojas de cálculo de área originales (archivos `Defor****_****_Mpios_Dat.xls`), incluidas las hojas "Cálculos" que sirven de referencia para el control de calidad.
- **Rásters departamentales** de Antioquia (`DEPTO_ANTIOQUIA_*`) con su tabla de atributos (RAT/VAT), empleados como respaldo para estadística zonal y para calibrar periodos sin dato municipal.

Adicionalmente, la capa de límites municipales de la jurisdicción se deriva del shapefile `Defor2021_2022_Mpios_Proj.shp`, disolviendo por municipio los 19 entes territoriales.

### 2.2 Cartografía oficial de contexto

Para los cruces temáticos se emplea la cartografía oficial de CORPOURABA y de fuentes nacionales, en su versión institucional:

- Áreas protegidas
- Resguardos indígenas
- Consejos comunitarios de comunidades negras
- Cuencas hidrográficas y POMCAS (Planes de Ordenación y Manejo de Cuencas)
- Reserva Forestal de la Ley 2ª de 1959 (Reserva Forestal del Pacífico; zonas Tipo A/B/C)
- Títulos mineros y solicitudes mineras vigentes (catastro minero, corte 2025-01-29)

En el **Visor de deforestación** estas capas se presentan sin el sufijo "(oficial)", mostrando únicamente su nombre institucional.

## 3. Unidad de análisis y sistema de clases

La unidad de análisis es el **cambio de cobertura de bosque por municipio y por periodo**. La superficie se contabiliza en hectáreas, calculada geométricamente en el sistema métrico de origen.

Cada polígono o registro se clasifica según el campo **`gridcode`**, con cinco clases:

| gridcode | Clase |
|---|---|
| 1 | Bosque Estable |
| 2 | Deforestación |
| 3 | Sin Información |
| 4 | Regeneración |
| 5 | No Bosque Estable |

El indicador principal del Observatorio es la clase **2 = Deforestación**. El análisis complementario de dinámica de bosque utiliza además las clases Bosque Estable (1) y Regeneración (4).

## 4. Sistemas de referencia (CRS)

- **CRS de origen:** EPSG:3115 (MAGNA-SIRGAS / Colombia Bogotá zone), sistema proyectado en metros. Todos los cálculos de área se realizan en este sistema métrico (o en el equivalente EPSG:3116 de algunas capas de cartografía oficial), garantizando superficies correctas en hectáreas. Algunas capas de la cartografía oficial (Ley 2ª, minería) vienen en EPSG:3116 y se reproyectan al sistema métrico común antes de medir áreas.
- **CRS de salida (web):** EPSG:4326 (WGS84, geográfico). Todas las capas publicadas para el visor y el mapa se entregan en WGS84 para su consumo con react-leaflet.

El flujo general es: **medir en proyectado (metros) → publicar en geográfico (grados)**, de modo que ninguna área se calcula en coordenadas geográficas.

## 5. Pipeline ETL paso a paso

El proceso de transformación está implementado en `etl/run_etl.py` y ejecuta seis pasos, que el propio script imprime en su registro de ejecución:

1. **[1/6] Límites municipales.** Se leen los límites municipales, se normalizan los nombres contra la tabla oficial de 19 municipios, se disuelven por municipio, se rellenan huecos, se simplifica la geometría (tolerancia de 80 m) y se reproyecta a WGS84. Resultado: 19 municipios.
2. **[2/6] Serie municipal por periodo.** Para cada uno de los 18 periodos se elige la mejor fuente disponible (ver sección 6) y se calcula el área por municipio y clase.
3. **[3/6] Estimación de vacíos.** Solo para la clase Deforestación, se rellenan los periodos sin fuente municipal (2010-2012, 2018-2019, 2023-2024), marcándolos con el indicador `estimado=true` (ver sección 7).
4. **[4/6] Hotspots de deforestación.** Se generan los polígonos de deforestación (parches, incluidos los de menos de 1 ha) por periodo, recortados a la jurisdicción y simplificados, para el visor y los cruces temáticos.
5. **[5/6] Capas de contexto (overlays).** Se procesan y publican las capas de áreas protegidas (21 unidades), resguardos (39), consejos comunitarios (7) y cuencas (7), junto con las demás capas de cartografía oficial.
6. **[6/6] Control de calidad.** Se compara la serie derivada contra las hojas "Cálculos" de los Excel originales (ver sección 9).

Las salidas se escriben en `data/processed/` (`serie_municipal.csv`, `serie_regional.csv`, `metadata.json`, `municipios.geojson`, `hotspots/`, `capas/`, `analisis/`).

## 6. Priorización de la mejor fuente por periodo

Cuando un periodo dispone de más de un insumo, el ETL aplica un orden de preferencia jerárquico, de mayor a menor confiabilidad geométrica y de medición:

1. **Shapefile municipal** (geometría + atributos por municipio y clase) — máxima prioridad.
2. **Tabla Excel** oficial del periodo.
3. **Tabla municipal `.dbf`** (atributos municipales sin geometría).
4. **Estadística zonal del ráster** departamental recortada a los municipios.
5. **Estimación** (interpolación / tendencia / calibración) — última opción, siempre marcada como referencial.

La asignación efectiva de fuente por periodo, según `metadata.json`, es la siguiente:

| Periodo | Fuente empleada |
|---|---|
| 2000-2002 | Excel |
| 2002-2004 | Shapefile |
| 2004-2006 | Shapefile |
| 2006-2008 | Shapefile |
| 2008-2010 | Shapefile |
| 2010-2012 | Estimado |
| 2012-2013 | Ráster (estadística zonal) |
| 2013-2014 | Shapefile |
| 2014-2015 | Excel |
| 2015-2016 | Tabla municipal `.dbf` (dato medido) |
| 2016-2017 | Shapefile |
| 2017-2018 | Shapefile |
| 2018-2019 | Estimado |
| 2019-2020 | Shapefile |
| 2020-2021 | Shapefile |
| 2021-2022 | Shapefile |
| 2022-2023 | Shapefile |
| 2023-2024 | Estimado |

De los 18 periodos, **15 provienen de medición directa** (shapefile, Excel, tabla `.dbf` o estadística zonal del ráster) y **3 son estimados**.

## 7. Periodos estimados y su método

Tres periodos carecen de datos municipales en el paquete original. Se rellenan únicamente para la clase Deforestación y se marcan con `estimado=true`. **Estas cifras deben usarse solo como referencia de tendencia, no como cifra oficial.**

- **2010-2012 — interpolación calibrada con el RAT departamental.** Se interpola la tasa anual entre los periodos vecinos y luego se **calibra contra el total departamental real** obtenido del RAT del ráster de Antioquia. Como el ráster cubre todo el departamento (~6,3 M ha) y no solo la jurisdicción, se aplica la participación histórica de la jurisdicción en el total departamental, estable en los periodos verificables (2008-2010 y 2012-2013): en la ejecución, deforestación departamental real de 17.546 ha × participación de la jurisdicción del 17,9% = objetivo de 3.135 ha (factor de escala 0,839). Fuente registrada: `estimado-calibrado-rat`.
- **2018-2019 — interpolación lineal.** Al existir periodos medidos antes y después, se promedia la tasa anual de deforestación de los periodos vecinos por municipio.
- **2023-2024 — extrapolación por tendencia.** Al no existir un periodo posterior medido, se ajusta una tendencia lineal sobre los tres periodos previos por municipio y se proyecta el valor anual.

Los valores estimados resultantes son: 2010-2012 = 3.134,9 ha; 2018-2019 = 1.800,2 ha; 2023-2024 = 1.596,8 ha (clase Deforestación, jurisdicción completa).

## 8. Recuperación de 2015-2016 como dato medido

El periodo **2015-2016** fue durante una fase intermedia un periodo estimado, porque la geometría (`.shp`) de ese cambio de bosque no se conservó en el paquete; el único cruce disponible era una tabla de cuencas que cubre solo una fracción de cada municipio (≈35 %), lo que obligaba a calibrar por cobertura y marcar el resultado como estimado.

Posteriormente se recuperó la **tabla de atributos municipal oficial** `Defor2015_2016_Mpios_Proj_Correg.dbf`, que contiene el **área real por municipio y clase de los 19 municipios**. Con ella, 2015-2016 pasó a ser **dato MEDIDO** (`estimado=false`): la lógica del ETL detecta la presencia de la tabla `.dbf` y, en ese caso, no aplica la calibración por cuencas (que queda como plan B). Los resultados confirmados:

- **Deforestación total 2015-2016 = 5.771 ha**, que constituye el **pico real de toda la serie 2000–2024**.
- **San Juan de Urabá registró 0 ha** de deforestación en el periodo, dato coherente con su tamaño y cobertura, contabilizado sin imputación.

Nota importante sobre el visor: como la geometría de polígonos de 2015-2016 no se conservó, este periodo **no aparece en el visor de parches**, pero **sus cifras en el dashboard y en la serie son reales** y provienen de la tabla municipal oficial.

## 9. Control de calidad

En el paso [6/6] la serie derivada se compara contra las hojas **"Cálculos"** de los Excel originales. El criterio de aceptación es una diferencia relativa **≤ 0,3 %**. Todos los periodos verificados cumplen ese umbral:

| Periodo | Hoja de referencia | Total referencia (ha) | Diferencia |
|---|---|---|---|
| 2000-2002 | Cálculos2002 | 1.590,3 | 0,00 % |
| 2004-2006 | Cálculos2006 | 3.028,2 | 0,22 % |
| 2008-2010 | Cálculos2010 | 2.927,9 | 0,22 % |
| 2014-2015 | Cálculos2015 | 2.887,5 | 0,00 % |
| 2016-2017 | Cálculos2017 | 3.942,2 | 0,29 % |
| 2017-2018 | Cálculos2018 | 1.768,7 | 0,20 % |
| 2019-2020 | Cálculos2020 | 1.740,6 | 0,19 % |
| 2020-2021 | Cálculos2021 | 1.092,8 | 0,19 % |
| 2021-2022 | Cálculos2022 | 2.330,2 | 0,20 % |
| 2022-2023 | Cálculos2023 | 1.158,4 | 0,19 % |

Estas diferencias milimétricas provienen de la disolución geométrica y la simplificación de límites, no de discrepancias metodológicas.

## 10. Cruces temáticos con la cartografía oficial

Los cruces temáticos se realizan **intersecando geométricamente los hotspots de deforestación (parches, incluidos los de menos de 1 ha) con las capas de cartografía oficial**, en el sistema proyectado métrico y repartiendo el área sin doble conteo. Se computan sobre los 12 periodos que cuentan con geometría de hotspots. Principales resultados verificados:

- **Minería.** Sobre 29.376,9 ha de deforestación mapeada, el **40,8 %** (11.988,4 ha) cae dentro de un título minero o una solicitud minera vigente: 14,9 % dentro de títulos otorgados y 25,9 % dentro de solicitudes en evaluación.
- **Áreas protegidas.** El **12,6 %** de la deforestación mapeada (3.362 ha en los 10 periodos comparables) ocurrió dentro de áreas protegidas; el DRMI Serranía de Abibe concentra 1.903 ha (57 % del total en AP).
- **Reserva Forestal Ley 2ª de 1959.** El 35,8 % de la deforestación mapeada intersecta la reserva (recortada previamente a la jurisdicción para no inflar el dato con deforestación externa del Chocó).
- **POMCAS y cuencas.** Las 7 cuencas monitoreadas acumulan deforestación mapeada; el POMCA del Río León encabeza con 4.738,5 ha.
- **Resguardos y consejos comunitarios.** La deforestación mapeada se cruza con los 39 resguardos y 7 consejos; el análisis muestra un desplazamiento de la presión hacia territorios étnicos (del 16,6 % de lo mapeado en 2002-2010 al 40,6 % en 2019-2023).

Todas estas cifras corresponden a **deforestación mapeada** (basada en la geometría de hotspots), no al total de la serie municipal, y así se declaran en la plataforma.

## 11. Limitaciones y nota de honestidad del dato

- **Cobertura de geometría.** Solo **12 de los 18 periodos** disponen de geometría de hotspots (parches, incluidos los de menos de 1 ha). Los cruces temáticos y el visor de parches se limitan por tanto a esos periodos.
- **Fracción mapeada.** La geometría de hotspots representa aproximadamente el **64 % de la deforestación** de la jurisdicción (≈29.918 ha de las 46.846 ha totales); el resto se conoce a nivel de agregado municipal (serie municipal) pero sin polígono asociado. Por eso los porcentajes de los cruces temáticos se calculan siempre sobre el subconjunto mapeado y no sobre el total de la serie.
- **Periodos estimados.** 2010-2012, 2018-2019 y 2023-2024 no son cifra oficial; son referencias de tendencia calculadas por interpolación, extrapolación o calibración, y están marcados con `estimado=true`.
- **2015-2016 sin geometría.** Es dato medido en cifras (tabla municipal `.dbf`), pero no tiene polígonos, por lo que no aparece en el visor de parches.
- **Umbral de parche.** Los hotspots aplican un umbral mínimo de 0,09 ha (un píxel de 30 m del ráster), por lo que incluyen los focos de menos de 1 ha; solo se descarta el ruido por debajo de ese tamaño. La deforestación no representada como polígono (los 6 periodos sin geometría) sí se contabiliza en la serie municipal cuando la fuente lo permite.

Estas limitaciones se comunican de forma transparente en la propia plataforma, de modo que ningún usuario confunda un dato estimado con una medición directa ni un porcentaje sobre lo mapeado con un porcentaje sobre el total de la jurisdicción.

---

Documento verificado contra archivos reales en `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion`:
- `data/processed/metadata.json` (fuentes por periodo, log del ETL, QA, overlays, nota 2015-2016 y estimados)
- `data/processed/serie_regional.csv` (pico 2015-2016 = 5.771,04 ha; total deforestación = 46.845,5 ha ≈ 46.846)
- `data/processed/analisis/cartografia/mineria_resumen.json` (40,8 % en minería), `figuras_resumen.json` (35,8 % Ley 2ª), `pomcas_resumen.json`, `hallazgos.json` (12,6 % en áreas protegidas)
- `etl/run_etl.py` (6 pasos, priorización de fuentes, calibración RAT participación 17,9 %, estimación por interpolación/tendencia, recuperación de 2015-2016 desde `.dbf`)
