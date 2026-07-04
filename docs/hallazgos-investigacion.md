# Hallazgos de la investigación temática — Deforestación CORPOURABA 2000-2024

**Informe ejecutivo** · Generado por el equipo de análisis del Observatorio (5 líneas temáticas
mineradas en paralelo sobre el paquete crudo de monitoreo + verificación independiente).
Datos de soporte reproducibles en `etl/analisis/*.py` → `data/processed/analisis/`.

---

## Resumen de una página

Entre 2000 y 2024 la jurisdicción CORPOURABA perdió **≈46.041 ha por deforestación**
(serie principal validada; ~23% de los registros son estimados/calibrados por vacíos del
paquete original). La investigación temática revela que esa pérdida **no es aleatoria ni
dispersa**:

1. **Se desplaza hacia los territorios étnicos.** Los resguardos indígenas y consejos
   comunitarios pasaron de concentrar el **16,4%** de la deforestación mapeada (2002-2010)
   al **40,9%** (2019-2023). El pueblo **Embera Katío** concentra el 77% de la pérdida en
   resguardos (3.478 ha); el Consejo Comunitario Mayor del **Medio Atrato (ACIA)** es el
   territorio colectivo individual más afectado (1.255 ha).
2. **Es persistente y localizable.** El **72,2%** de las hectáreas deforestadas cae en
   1.039 celdas de 2×2 km con deforestación recurrente (≥3 periodos). Las celdas más
   activas (Mutatá y Dabeiba, eje de la vía al mar) repiten en **10 de 12 periodos**.
3. **Erosiona las figuras de protección.** **3.362 ha** se deforestaron dentro de áreas
   protegidas (12,6% de lo mapeado). El **DRMI Serranía de Abibe** concentra el 57% de esa
   pérdida (1.903 ha, pico 585 ha en 2015-2016).
4. **El balance neto es claramente negativo.** El bosque estable regional cayó de 908.114
   a 870.305 ha (**-37.809 ha, -4,2%**). La regeneración medida (726 ha) compensa apenas el
   **2,1%** de la pérdida. Turbo perdió más bosque en términos absolutos (-18.424 ha);
   **Carepa** conserva solo el 57% de su bosque de 2000.
5. **La frontera se mueve hacia las subregiones boscosas.** Caribe y Centro desaceleran su
   tasa relativa; **Atrato, Nutibara y Urrao aceleran** — consistente con el punto 1.

---

## Verificación independiente

Cada cifra material fue re-verificada con código independiente contra las fuentes:

| Chequeo | Resultado |
|---|---|
| Subconjuntos (AP, resguardos, consejos, cuencas) ≤ total regional por periodo | ✔ sin violaciones |
| Bosque estable 2022-2023 (dinámica) vs serie principal | ✔ dif. 0,00% (870.305 ha) |
| Fragmentación 2022-2023 vs hotspots fuente | ✔ dif. 0,00% (919 ha) |
| Total AP: 3.836 ha (bruto) vs 3.362 ha (informe) | ✔ explicado: el informe excluye el periodo 2006-2008 por geometría duplicada de 2002-2004 en el paquete original |

## Hallazgos por tema

### 1. Áreas protegidas (`areas_protegidas_serie.csv`, 10 periodos comparables)
- 21 áreas protegidas monitoreadas; 3.362 ha deforestadas dentro de AP = **12,6%** del
  total mapeado en los mismos periodos; participación con leve tendencia a la baja
  (-0,2 pp/año).
- Ranking: **Serranía de Abibe (DRMI) 1.903 ha** · Carauta (RFPN) 514 ha · PNN Las
  Orquídeas 334 ha · Ensenada de Rionegro (DRMI) 292 ha.
- Por categoría: los DRMI concentran 2.205 ha; las RFPN 731 ha; los PNN 354 ha.
- Advertencia de datos: la capa AP de 2006-2008 es una copia de la de 2002-2004
  (excluida del análisis temporal).

### 2. Territorios étnicos (`resguardos_serie.csv` 1.412 filas · `consejos_serie.csv` 275)
- 39 resguardos (5 pueblos) y 7 consejos comunitarios; cobertura completa en 10 periodos.
- Pérdida acumulada con medición de área: **4.513 ha en resguardos** y **2.269 ha en
  consejos**.
- Fracción étnica de la deforestación por periodo: 10,6% (2002-2004) → 29,5% (2016-2017)
  → **40,9% promedio 2019-2023**.
- Top resguardos: Murindó 583 ha · Chaquenodá 558 ha · Andabú 421 ha · Yaberaradó 344 ha
  (4,1% de su territorio, la mayor proporción).
- Regeneración casi nula en territorios étnicos (47,6 ha en total).

### 3. Cuencas hidrográficas (`cuencas_serie.csv`, 13 periodos con dato)
- 7 cuencas monitoreadas = 723.026 ha (38,9% de la jurisdicción). **No** comparable con el
  total regional; se reporta como subconjunto.
- **Río León: 6.333 ha (2,9% de su área), tendencia "empeora"** — es la cuenca del eje
  bananero. Turbo-Currulao: 2.604 ha.
- Total confiable en cuencas: 11.642 ha (11 periodos).
- Defecto de datos detectado y excluido: en 2021-2022 la columna de área venía pre-clip
  (2,7 M ha); 2023-2024 solo permite conteos (dbf sin geometría).

### 4. Dinámica de bosque (`dinamica_bosque.csv`, 21 columnas, 19 municipios × periodos)
- Regional: bosque estable 908.114 → 870.305 ha (**-4,2%**). Ningún municipio perdió aún
  más de la mitad de su bosque, pero **Carepa está en -43,2%**, Turbo -24,6%, Necoclí -23,8%.
- Cambio neto: deforestación medida 34.542 ha vs regeneración 726 ha (**relación 48:1**).
- Tasa relativa (pérdida anual / bosque remanente): Caribe 1,0%→0,3% y Centro 0,5%→0,3%
  (desaceleran); Atrato, Nutibara y Urrao suben (aceleran). Murindó perdió 8,9 puntos de
  cobertura de bosque, el mayor retroceso proporcional de cobertura.

### 5. Fragmentación y recurrencia (`fragmentacion.csv` + `recurrencia.geojson`)
- 9.107 parches ≥1 ha en 12 periodos = 25.169 ha mapeadas en parches. Mediana **1,7 ha**;
  92% de los parches <5 ha. Patrón de "colonización hormiga", estable en el tiempo; la
  densidad de parches aumenta (+1,4 parches/1000 ha·año) sin crecer el tamaño.
- Excepción: Turbo, con el parche máximo de la serie (**738,5 ha**) y 5.945 ha en parches.
- Recurrencia (celdas 2×2 km): el 50,9% de la jurisdicción registró deforestación al menos
  una vez; **1.039 celdas persistentes (≥3 periodos) concentran el 72,2% del área
  deforestada**. Frentes más persistentes: Mutatá y Dabeiba (10/12 periodos), Urrao (179
  celdas persistentes), Turbo (165), Dabeiba (152).

## Vacíos y limitaciones

- La serie principal estima/calibra 2010-2012, 2015-2016, 2018-2019 y 2023-2024 (~23% de
  los registros de deforestación); los análisis espaciales (AP, étnicos, fragmentación)
  solo usan periodos con geometría real — se declara la cobertura en cada CSV.
- Los hotspots cubren 12 de 18 periodos (≈87% de la deforestación medida); "deforestación
  mapeada" se refiere siempre a ese subconjunto.
- Capas temáticas con huecos: AP 2006-2008 duplicada; cuencas 2021-2022 con área pre-clip;
  2023-2024 sin geometría en todas las capas (solo conteos).

## Recomendaciones de visualización para la plataforma

| Hallazgo | Visualización sugerida |
|---|---|
| Desplazamiento a territorios étnicos | Línea de % étnico por periodo + capa de resguardos/consejos en el mapa |
| Frentes persistentes | Capa `recurrencia.geojson` (celdas ≥3 periodos) como overlay "Frentes activos" |
| Serranía de Abibe y AP | Ranking de AP + serie del DRMI en la sección de análisis |
| Bosque hoy vs 2000 | Barras divergentes por municipio (delta_ha / delta_pct) |
| Regeneración 48:1 | KPI comparativo en dashboard |
| León y cuencas | Ranking de cuencas + tendencia |
| Atomización | Histograma de tamaño de parche + densidad temporal |
