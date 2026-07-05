# Diccionario de Datos

## Observatorio de Deforestación CORPOURABA 2000–2024

Este documento describe, campo por campo, todos los conjuntos de datos procesados que alimentan la plataforma web del Observatorio de Deforestación de la Corporación para el Desarrollo Sostenible del Urabá (CORPOURABA). Es la referencia técnica oficial para interpretar, reutilizar o auditar la información.

Todos los conjuntos residen en la carpeta `data/processed/`. El sistema de referencia de coordenadas de origen de la cartografía es **EPSG:3115 (MAGNA-SIRGAS / Colombia Bogotá zone, métrico)** y todas las capas publicadas en la web se entregan en **EPSG:4326 (WGS84, geográfico)**. Las cifras de deforestación se expresan en **hectáreas (ha)**, calculadas sobre la geometría métrica original.

La cobertura es de **19 municipios**, **25 años (2000–2024)** y **18 periodos** de análisis.

---

## 1. Series de deforestación

### 1.1 `serie_municipal.csv`

Serie principal de la plataforma: área por municipio, periodo y clase de cobertura. Contiene 1.131 filas de datos.

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `codigo_dane` | texto | Código DANE del municipio (5 dígitos, con cero a la izquierda) | Ej. `05004`. Ver tabla de municipios (§8) |
| `municipio` | texto | Nombre del municipio | Ej. `Abriaquí` |
| `subregion` | texto | Subregión de la jurisdicción a la que pertenece el municipio | Atrato, Caribe, Centro, Nutibara, Urrao (§7) |
| `periodo` | texto | Identificador del periodo de análisis | Ej. `2000-2002` (§6) |
| `ano_inicio` | entero | Año inicial del periodo | 2000–2023 |
| `ano_fin` | entero | Año final del periodo | 2002–2024 |
| `clase` | texto | Clase de cobertura/cambio | Bosque Estable, Deforestación, No Bosque Estable, Regeneración, Sin Información (§5) |
| `hectareas` | decimal | Área total de la clase en el periodo | hectáreas (ha) |
| `hectareas_anuales` | decimal | Área dividida por el número de años del periodo (tasa anualizada) | ha/año |
| `fuente` | texto | Origen del dato de ese registro | excel, shapefile, raster, dbf-municipal, estimado, estimado-calibrado-rat (§9) |
| `estimado` | booleano | Indica si el valor es estimado (no medido) | `True` / `False` |

### 1.2 `serie_regional.csv`

Serie agregada para toda la jurisdicción (suma de los 19 municipios) por periodo y clase.

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `periodo` | texto | Identificador del periodo | Ej. `2000-2002` (§6) |
| `ano_inicio` | entero | Año inicial del periodo | 2000–2023 |
| `ano_fin` | entero | Año final del periodo | 2002–2024 |
| `clase` | texto | Clase de cobertura/cambio | Ver §5 |
| `hectareas` | decimal | Área total regional de la clase en el periodo | hectáreas (ha) |
| `hectareas_anuales` | decimal | Área anualizada | ha/año |
| `estimado` | booleano | Marca si el agregado incluye estimación | `True` / `False` |

---

## 2. Metadatos: `metadata.json`

Documento maestro de metadatos generado por el ETL. Sus claves principales son:

| Clave | Tipo | Descripción |
|---|---|---|
| `titulo` | texto | Título del observatorio |
| `generado` | texto (ISO 8601) | Fecha y hora de generación de los datos |
| `crs_origen` | texto | CRS de la cartografía original (`EPSG:3115 / MAGNA-SIRGAS Bogotá`) |
| `crs_salida` | texto | CRS de las capas publicadas (`EPSG:4326`) |
| `clases` | objeto | Mapeo del nombre normalizado de clase a su etiqueta cruda del shapefile (§5) |
| `gridcode` | objeto | Mapeo del código numérico de píxel/clase (gridcode) a su nombre (§5) |
| `periodos` | lista | Los 18 periodos, cada uno con `id`, `ano_inicio`, `ano_fin`, `anos` y `fuente` (§6) |
| `municipios` | lista | Los 19 municipios con `key`, `nombre`, `codigo_dane` y `subregion` (§8) |
| `vacios_estimados` | lista | Periodos sin dato municipal medido, cubiertos por estimación: `2010-2012`, `2018-2019`, `2023-2024` |
| `nota_estimados` | texto | Explicación del método de estimación de los tres periodos vacíos (interpolación/tendencia; 2010-2012 calibrado con el total departamental del RAT del ráster × participación de la jurisdicción ~18%) |
| `nota_2015_2016` | texto | Aclara que 2015-2016 es dato MEDIDO desde la tabla municipal `.dbf` oficial (`Defor2015_2016_Mpios_Proj_Correg.dbf`), no una estimación; su geometría no se conservó, por lo que no aparece en el visor de polígonos |
| `hotspots_features` | objeto | Número de polígonos de hotspot por periodo |
| `overlays_unidades` | objeto | Número de unidades por capa de contexto (areas_protegidas: 21, resguardos: 39, consejos: 7, cuencas: 7) |
| `qa_calculos` | lista | Control de calidad: por periodo, compara el total calculado contra la hoja "Cálculos" del Excel original (`total_referencia_ha`, `diferencia_abs_ha`, `diferencia_pct`) |
| `log` | lista | Traza de ejecución del ETL, paso a paso |

---

## 3. Capas base

### 3.1 `municipios.geojson` (properties)

Polígonos de los 19 municipios de la jurisdicción.

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `municipio_key` | texto | Clave interna del municipio en mayúsculas sin tildes | Ej. `ABRIAQUI` |
| `codigo_dane` | texto | Código DANE (5 dígitos) | Ej. `05004` |
| `nombre` | texto | Nombre del municipio | Ej. `Abriaquí` |
| `subregion` | texto | Subregión (§7) | Atrato, Caribe, Centro, Nutibara, Urrao |
| `area_municipio_ha` | decimal | Área del municipio | hectáreas (ha) |
| `centroide` | lista [lon, lat] | Coordenadas del centroide | grados decimales (WGS84) |

### 3.2 `subregiones.geojson` (properties)

Polígonos de las 5 subregiones (disolución de municipios).

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `subregion` | texto | Nombre de la subregión | Atrato, Caribe, Centro, Nutibara, Urrao |

---

## 4. Hotspots de deforestación: `hotspots/<periodo>.geojson`

Un archivo por periodo con polígonos individuales de deforestación de ≥1 ha (parches). Existen 12 archivos: `2002-2004`, `2004-2006`, `2006-2008`, `2008-2010`, `2012-2013`, `2013-2014`, `2016-2017`, `2017-2018`, `2019-2020`, `2020-2021`, `2021-2022`, `2022-2023`.

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `municipio` | texto | Municipio donde cae el parche | Ej. `Arboletes` |
| `ha` | decimal | Área del parche de deforestación | hectáreas (ha) |

Geometría: `Polygon`. Nota: el identificador del periodo (`periodo`, `ano_inicio`) está implícito en el nombre del archivo; los parches por debajo de 1 ha y los ubicados fuera de la jurisdicción se descartan en el ETL.

---

## 5. Códigos de clase (gridcode ↔ nombre)

Correspondencia entre el código numérico del ráster/shapefile (`gridcode`), el nombre normalizado usado en toda la plataforma y la etiqueta cruda del origen.

| gridcode | Nombre normalizado (clase) | Etiqueta cruda origen |
|---|---|---|
| 1 | Bosque Estable | BOSQUE ESTABLE |
| 2 | Deforestación | DEFORESTACION |
| 3 | Sin Información | SIN INFORMACION |
| 4 | Regeneración | REGENERACION |
| 5 | No Bosque Estable | NO BOSQUE ESTABLE |

---

## 6. Periodos y su fuente

Los 18 periodos de análisis, con sus años y el origen del dato (campo `fuente` en `metadata.json`). Los periodos marcados como estimados son **2010-2012**, **2018-2019** y **2023-2024**.

| Periodo | Año inicio | Año fin | Años | Fuente |
|---|---|---|---|---|
| 2000-2002 | 2000 | 2002 | 2 | excel |
| 2002-2004 | 2002 | 2004 | 2 | shapefile |
| 2004-2006 | 2004 | 2006 | 2 | shapefile |
| 2006-2008 | 2006 | 2008 | 2 | shapefile |
| 2008-2010 | 2008 | 2010 | 2 | shapefile |
| 2010-2012 | 2010 | 2012 | 2 | estimado |
| 2012-2013 | 2012 | 2013 | 1 | raster (zonal stats) |
| 2013-2014 | 2013 | 2014 | 1 | shapefile |
| 2014-2015 | 2014 | 2015 | 1 | excel |
| 2015-2016 | 2015 | 2016 | 1 | tabla municipal (dbf) — dato medido |
| 2016-2017 | 2016 | 2017 | 1 | shapefile |
| 2017-2018 | 2017 | 2018 | 1 | shapefile |
| 2018-2019 | 2018 | 2019 | 1 | estimado |
| 2019-2020 | 2019 | 2020 | 1 | shapefile |
| 2020-2021 | 2020 | 2021 | 1 | shapefile |
| 2021-2022 | 2021 | 2022 | 1 | shapefile |
| 2022-2023 | 2022 | 2023 | 1 | shapefile |
| 2023-2024 | 2023 | 2024 | 1 | estimado |

---

## 7. Subregiones

Las cinco subregiones en que se agrupan los 19 municipios de la jurisdicción.

| Subregión | Descripción |
|---|---|
| Atrato | Municipios ribereños del Atrato (Murindó, Vigía del Fuerte) |
| Caribe | Franja costera del Urabá antioqueño norte |
| Centro | Eje bananero y sur de Urabá (incluye Turbo, Apartadó, Mutatá) |
| Nutibara | Occidente montañoso de Antioquia |
| Urrao | Municipio de Urrao (páramo y suroccidente) |

---

## 8. Municipios y código DANE

Los 19 municipios de la jurisdicción CORPOURABA (extraídos de `metadata.json`).

| Código DANE | Municipio | Subregión |
|---|---|---|
| 05004 | Abriaquí | Nutibara |
| 05045 | Apartadó | Centro |
| 05051 | Arboletes | Caribe |
| 05138 | Cañasgordas | Nutibara |
| 05147 | Carepa | Centro |
| 05172 | Chigorodó | Centro |
| 05234 | Dabeiba | Nutibara |
| 05284 | Frontino | Nutibara |
| 05306 | Giraldo | Nutibara |
| 05475 | Murindó | Atrato |
| 05480 | Mutatá | Centro |
| 05490 | Necoclí | Caribe |
| 05543 | Peque | Nutibara |
| 05659 | San Juan de Urabá | Caribe |
| 05665 | San Pedro de Urabá | Caribe |
| 05837 | Turbo | Centro |
| 05842 | Uramita | Nutibara |
| 05847 | Urrao | Urrao |
| 05873 | Vigía del Fuerte | Atrato |

---

## 9. Valores del campo `fuente`

Origen del dato de cada registro de la serie (campo `fuente` en `serie_municipal.csv`).

| Valor | Significado |
|---|---|
| `excel` | Tabla de atributos exportada a Excel (`.xls`) del paquete original |
| `shapefile` | Cálculo de área sobre la geometría del shapefile de ese periodo |
| `raster` | Estadística zonal sobre el ráster clasificado (periodo 2012-2013) |
| `dbf-municipal` | Tabla de atributos municipal `.dbf` oficial (periodo 2015-2016, dato medido) |
| `estimado` | Valor interpolado/por tendencia para periodos sin dato municipal |
| `estimado-calibrado-rat` | Estimación de 2010-2012 calibrada con el total departamental real del RAT del ráster × participación histórica de la jurisdicción (~18%) |

---

## 10. Capas de contexto: `capas/*.geojson`

Capas oficiales de la cartografía CORPOURABA para superponer en el visor. Se muestran en la web sin el sufijo "(oficial)".

| Archivo | Representa | Nº de unidades |
|---|---|---|
| `areas_protegidas.geojson` | Áreas protegidas (versión derivada del análisis) | 21 |
| `areas_protegidas_oficial.geojson` | Áreas protegidas — capa oficial CORPOURABA | 21 |
| `resguardos.geojson` | Resguardos indígenas (versión derivada) | 39 |
| `resguardos_oficial.geojson` | Resguardos indígenas — capa oficial | 40 |
| `consejos.geojson` | Consejos comunitarios de comunidades negras (derivada) | 7 |
| `comunidades_negras_oficial.geojson` | Consejos comunitarios — capa oficial | 12 |
| `cuencas.geojson` | Cuencas hidrográficas ordenadas | 7 |
| `pomcas.geojson` | POMCAS (Planes de Ordenación y Manejo de Cuencas) | 7 |
| `ley_segunda.geojson` | Reserva Forestal de Ley 2ª de 1959 (por tipo A/B/C) | 4 |
| `titulos_mineros.geojson` | Títulos y solicitudes mineras del catastro | 537 |

### 10.1 Properties por capa

**`areas_protegidas.geojson`** / **`consejos.geojson`** / **`resguardos.geojson`** / **`cuencas.geojson`** (capas derivadas)

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `nombre` / `nomb_cuenc` | texto | Nombre de la unidad (en cuencas el campo es `nomb_cuenc`) | — |
| `categoria` | texto | Categoría de manejo (solo áreas protegidas) | Ej. `Distrito Regional de Manejo Integrado` |
| `pueblo` | texto | Pueblo indígena (solo resguardos) | Ej. `EMBERA KATIO` |
| `area_ha` | decimal | Área de la unidad | hectáreas (ha) |
| `deforestacion_ha_ultimo_periodo` | decimal | Deforestación en el último periodo mapeado | hectáreas (ha) |

**`areas_protegidas_oficial.geojson`** / **`ley_segunda.geojson`** / **`pomcas.geojson`** (capas oficiales)

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `nombre` | texto | Nombre de la unidad/zona | — |
| `categoria` | texto | Categoría (áreas protegidas, Ley 2ª) | Ej. `Tipo A` |
| `figura` | texto | Figura de protección | Ej. `Reserva Forestal Ley 2a de 1959` |
| `area_ha` | decimal | Área de la unidad | hectáreas (ha) |
| `deforestacion_ha_total` | decimal | Deforestación total acumulada mapeada | hectáreas (ha) |

**`comunidades_negras_oficial.geojson`** / **`resguardos_oficial.geojson`** (territorios colectivos oficiales)

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `nombre` | texto | Nombre del territorio colectivo | — |
| `id_consejo` / `id_resguardo` | texto | Identificador del territorio | — |
| `pueblo` | texto | Pueblo indígena (solo resguardos) | Ej. `Embera Katío` |
| `municipios` | texto | Municipio(s) donde se ubica | Ej. `Murindó` |
| `ano_acto` | entero | Año del acto administrativo de constitución | — |
| `resolucion` | texto | Resolución de creación (solo consejos) | — |
| `area_oficial_ha` | decimal | Área oficial del territorio | hectáreas (ha) |
| `pct_en_jurisdiccion` | decimal | Porcentaje del territorio dentro de la jurisdicción | % |
| `deforestacion_ha_total` | decimal | Deforestación total acumulada | hectáreas (ha) |
| `deforestacion_ha_ultimo_periodo` | decimal | Deforestación del último periodo | hectáreas (ha) |

**`titulos_mineros.geojson`**

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `nombre` | texto | Código del título/solicitud | Ej. `B7187005` |
| `tipo` | texto | Tipo de registro minero | `titulo`, `solicitud` |
| `titular` | texto | Titular del derecho minero | — |
| `mineral` | texto | Grupo de mineral | Ej. `Metálicos (oro y asociados)` |
| `minerales_detalle` | texto | Descripción detallada del mineral | — |
| `estado` | texto | Estado del título | Activo, Suspendido, Archivado, etc. |
| `etapa` | texto | Etapa del proyecto | Explotación, Exploración, Construcción y montaje, Sin dato |
| `clasificacion` | texto | Clasificación por tamaño | Ej. `Mediana` |
| `municipios` | texto | Municipios que abarca | Ej. `DABEIBA, MURINDÓ` |
| `ano` | entero | Año de otorgamiento | — |
| `area_ha` | decimal | Área del título | hectáreas (ha) |
| `deforestacion_ha_total` | decimal | Deforestación total mapeada dentro del título | hectáreas (ha) |

---

## 11. Análisis temáticos: `analisis/`

Conjuntos derivados que sustentan el módulo de análisis del dashboard. Cada tema tiene una serie (`*_serie.csv`) o tabla y, generalmente, un resumen (`*_resumen.json`).

### 11.1 `analisis/areas_protegidas_serie.csv`

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `periodo`, `ano_inicio`, `ano_fin` | texto/entero | Periodo de análisis | §6 |
| `nombre` | texto | Nombre del área protegida | — |
| `categoria` | texto | Categoría de manejo | — |
| `clase` | texto | Clase de cobertura | §5 |
| `hectareas` | decimal | Área de la clase dentro del AP | ha |
| `hectareas_anuales` | decimal | Área anualizada | ha/año |
| `n_poligonos` | entero | Nº de polígonos que aportan al valor | — |
| `fuente` | texto | Origen del dato | shapefile, etc. |
| `flag_calidad` | texto | Marca de calidad de la geometría | Ej. `geometria_epsg3115` |
| `es_duplicado` | booleano | Registro potencialmente duplicado | `True`/`False` |
| `usado_en_agregados` | booleano | Si el registro entra en los agregados | `True`/`False` |

### 11.2 `analisis/resguardos_serie.csv` y `analisis/consejos_serie.csv`

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `periodo`, `ano_inicio`, `ano_fin` | texto/entero | Periodo de análisis | §6 |
| `resguardo` / `consejo` | texto | Nombre del territorio colectivo | — |
| `pueblo` | texto | Pueblo indígena (solo resguardos) | — |
| `clase` | texto | Clase de cobertura | §5 |
| `hectareas` | decimal | Área de la clase | ha |
| `hectareas_anuales` | decimal | Área anualizada | ha/año |
| `poligonos` | entero | Nº de polígonos | — |
| `fuente` | texto | Origen del dato | shapefile, excel |
| `calidad_fuente` | texto | Calidad del dato | Ej. `geometria`, `solo_conteo` |

### 11.3 `analisis/cuencas_serie.csv`

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `idcu` | entero | Identificador de la cuenca | — |
| `cuenca` | texto | Nombre de la cuenca | Ej. `Canalete` |
| `periodo`, `ano_inicio`, `ano_fin` | texto/entero | Periodo de análisis | §6 |
| `clase` | texto | Clase de cobertura | §5 |
| `hectareas` | decimal | Área de la clase | ha |
| `hectareas_anuales` | decimal | Área anualizada | ha/año |
| `n_poligonos` | entero | Nº de polígonos | — |
| `fuente` | texto | Origen del dato | Ej. `xlsx:columna_area` |
| `area_confiable` | booleano | Si el área es confiable | `True`/`False` |
| `flag_calidad` | texto | Marca de calidad | Ej. `columna_validada_ok` |

### 11.4 `analisis/dinamica_bosque.csv`

Balance de cobertura boscosa por municipio y periodo.

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `codigo_dane`, `municipio`, `subregion` | texto | Identificación del municipio | §8 |
| `periodo`, `ano_inicio`, `ano_fin`, `n_anos` | texto/entero | Periodo y su duración | §6 |
| `bosque_estable_ha` | decimal | Bosque estable | ha |
| `no_bosque_ha` | decimal | No bosque estable | ha |
| `regeneracion_ha` | decimal | Regeneración | ha |
| `sin_informacion_ha` | decimal | Sin información | ha |
| `deforestacion_ha` | decimal | Deforestación | ha |
| `area_con_informacion_ha` | decimal | Área con información | ha |
| `pct_cobertura_bosque` | decimal | Porcentaje de cobertura de bosque | % |
| `bosque_estable_previo_ha` | decimal | Bosque estable del periodo anterior | ha |
| `periodo_bosque_previo` | texto | Periodo de referencia previo | §6 |
| `tasa_perdida_relativa` | decimal | Tasa de pérdida relativa | fracción |
| `cambio_neto_ha` | decimal | Cambio neto de bosque | ha |
| `fuente` | texto | Origen del dato | §9 |
| `calidad_fuente` | texto | Calidad del dato | Ej. `excel_tabla`, `shapefile_geometria` |
| `estimado` | booleano | Si es estimado | `True`/`False` |

### 11.5 `analisis/fragmentacion.csv`

Métricas de fragmentación de los parches de deforestación por municipio y periodo.

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `periodo`, `ano_inicio`, `ano_fin` | texto/entero | Periodo | §6 |
| `municipio`, `codigo_dane`, `subregion` | texto | Municipio | §8 |
| `n_parches` | entero | Número de parches de deforestación | — |
| `ha_total` | decimal | Área total de los parches | ha |
| `tamano_medio_ha` | decimal | Tamaño medio de parche | ha |
| `tamano_mediano_ha` | decimal | Tamaño mediano de parche | ha |
| `tamano_max_ha` | decimal | Tamaño del parche mayor | ha |
| `pct_parches_grandes` | decimal | Porcentaje de parches grandes | % |
| `fuente_calidad` | texto | Calidad de la fuente | Ej. `shapefile_ok` |

### 11.6 `analisis/recurrencia.geojson` (properties)

Malla de celdas donde recurre la deforestación a lo largo de los periodos.

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `cell_id` | entero | Identificador de la celda | — |
| `conteo_periodos` | entero | Nº de periodos con deforestación en la celda | — |
| `ha_acumuladas` | decimal | Deforestación acumulada en la celda | ha |
| `tamano_max_parche_ha` | decimal | Parche mayor registrado | ha |
| `municipio` | texto | Municipio de la celda | §8 |
| `subregion` | texto | Subregión | §7 |
| `periodos` | texto | Lista de periodos con deforestación (separados por coma) | Ej. `2002-2004,2004-2006,...` |
| `area_celda_ha` | decimal | Área total de la celda | ha |

---

## 12. Análisis de cartografía oficial: `analisis/cartografia/`

Cruces de la deforestación mapeada con las capas oficiales de CORPOURABA.

### 12.1 `analisis/cartografia/mineria_deforestacion.csv`

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `periodo`, `ano_inicio`, `ano_fin` | texto/entero | Periodo | §6 |
| `categoria` | texto | Situación minera del parche | `solo_titulo`, `solo_solicitud`, `titulo_y_solicitud`, `fuera` |
| `hectareas` | decimal | Deforestación en esa categoría | ha |
| `hectareas_anuales` | decimal | Área anualizada | ha/año |
| `pct_periodo` | decimal | % de la deforestación del periodo en esa categoría | % |
| `deforestacion_mapeada_periodo_ha` | decimal | Deforestación total mapeada del periodo (denominador) | ha |

### 12.2 `analisis/cartografia/figuras_proteccion.csv`

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `figura` | texto | Figura de protección | `Ley 2a de 1959`, `Area protegida`, `AEIA importancia alta` |
| `periodo`, `ano_inicio`, `ano_fin` | texto/entero | Periodo | §6 |
| `hectareas_dentro` | decimal | Deforestación dentro de la figura | ha |
| `hectareas_anuales` | decimal | Área anualizada | ha/año |
| `pct_mapeado_periodo` | decimal | % de la deforestación mapeada del periodo | % |
| `deforestacion_mapeada_periodo_ha` | decimal | Deforestación total mapeada del periodo | ha |

### 12.3 `analisis/cartografia/territorios_oficiales.csv`

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `tipo` | texto | Tipo de territorio colectivo | `resguardo`, `consejo_comunitario` |
| `id_territorio` | texto | Identificador del territorio | — |
| `nombre` | texto | Nombre del territorio | — |
| `pueblo` | texto | Pueblo indígena (si aplica) | — |
| `periodo`, `ano_inicio`, `ano_fin` | texto/entero | Periodo | §6 |
| `deforestacion_ha` | decimal | Deforestación dentro del territorio | ha |
| `n_poligonos` | entero | Nº de polígonos | — |
| `pct_del_territorio` | decimal | % del territorio deforestado | % |
| `area_oficial_ha` | decimal | Área oficial del territorio | ha |
| `pct_en_jurisdiccion` | decimal | % del territorio dentro de la jurisdicción | % |
| `municipios` | texto | Municipios que abarca | §8 |

### 12.4 `analisis/cartografia/pomcas_serie.csv`

| Campo | Tipo | Descripción | Valores/Unidad |
|---|---|---|---|
| `pomca` | texto | Nombre del POMCA | — |
| `periodo`, `ano_inicio` | texto/entero | Periodo | §6 |
| `deforestacion_ha` | decimal | Deforestación dentro del POMCA | ha |
| `n_poligonos` | entero | Nº de polígonos | — |

---

## 13. Resúmenes de análisis (`*_resumen.json` y `hallazgos.json`)

Documentos JSON con agregados, rankings, series y narrativa listos para el dashboard. Sus claves principales:

| Archivo | Contenido / claves principales |
|---|---|
| `analisis/dinamica_resumen.json` | Balance de bosque: `bosque_hoy_vs_2000`, `regional_delta_ha`, `regional_delta_pct`, `regional_defo_real_ha`, `regional_regen_real_ha`, `perdieron_mas_mitad`, `tasa_por_subregion_tendencia` |
| `analisis/fragmentacion_resumen.json` | `concentracion_vs_atomizacion`, `tendencia_tamano_parche`, `recurrencia`, `ranking_municipios_fragmentacion`, `respuestas` |
| `analisis/areas_protegidas_resumen.json` | `n_areas_protegidas`, `deforestacion_ap_total_ha`, `pct_global_dentro_ap`, `ranking_ap_por_deforestacion`, `ranking_por_categoria`, `aceleracion_2019_2023_vs_2015_2018`, `qa_por_periodo` |
| `analisis/cuencas_resumen.json` | `cuencas_total`, `calidad_area`, `ranking_por_hectareas`, `ranking_por_pct_area`, `detalle_cuencas` |
| `analisis/territorios_etnicos_resumen.json` | `totales`, `fraccion_etnica_por_periodo`, `top_resguardos_deforestacion`, `deforestacion_por_pueblo`, `top_consejos_deforestacion`, `qa_solape_resguardos_consejos` |
| `analisis/cartografia/mineria_resumen.json` | `capas` (títulos: n, por_estado, por_etapa, por_mineral_grupo, área; solicitudes), `pct_jurisdiccion_titulada`, `fecha_corte_capa_minera`, `fuente_capa` |
| `analisis/cartografia/figuras_resumen.json` | `capas`, `totales_12_periodos_mapeados`, `ranking_zonas_ley2a`, `ranking_areas_protegidas`, `deforestacion_por_clase_aeia_ha`, `qa_por_periodo` |
| `analisis/cartografia/pomcas_resumen.json` | `n_pomcas`, `deforestacion_total_ha`, `ranking` |
| `analisis/cartografia/territorios_oficiales_resumen.json` | `totales_2002_2023_mapeado`, `serie_por_periodo`, `tendencia_pct_colectivos`, `top_resguardos`, `top_consejos`, `deforestacion_por_pueblo` |
| `analisis/hallazgos.json` | Lista de 14 hallazgos clave; cada uno con `id`, `tema`, `titulo`, `cifra`, `unidad`, `periodo_referencia`, `descripcion`, `relevancia` |

---

## 14. Notas de uso

- Los tres periodos estimados (**2010-2012, 2018-2019, 2023-2024**) deben usarse solo como referencia, nunca como cifra oficial; se identifican con `estimado=True`.
- El periodo **2015-2016 es dato medido real** (recuperado de la tabla municipal `.dbf`); sus cifras son oficiales, aunque no dispone de geometría en el visor de polígonos.
- Todas las áreas se calculan sobre la geometría métrica original (EPSG:3115); las capas web se sirven reproyectadas a EPSG:4326.
- La validación de calidad (`qa_calculos` en `metadata.json`) muestra diferencias por debajo del 0,3 % frente a las hojas "Cálculos" de los Excel originales, confirmando la consistencia de la serie.

---

Rutas de referencia (absolutas):
- `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\serie_municipal.csv`
- `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\metadata.json`
- `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\municipios.geojson`
- `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\hotspots\`
- `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\capas\`
- `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\analisis\`
