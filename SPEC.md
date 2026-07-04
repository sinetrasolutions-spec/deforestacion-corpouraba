# SPEC — Observatorio de Deforestación CORPOURABA (2000–2024)

Contrato técnico compartido. **Todo constructor (humano o agente) debe ceñirse a
este documento.** Rutas relativas a la raíz del proyecto
`E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion`.

## 1. Objetivo

Plataforma web institucional para explorar, analizar, aprender y descargar la
deforestación de los 19 municipios de la jurisdicción CORPOURABA (Urabá y
Occidente antioqueño), 2000–2024. Cuatro módulos: mapa interactivo, dashboard
analítico, módulo educativo PRAES y centro de descargas. Idioma de UI: español.

## 2. Estructura del proyecto

```
observatorio-deforestacion/
├── SPEC.md                      ← este documento
├── README.md                    ← visión general + inicio rápido   [docs]
├── docs/
│   ├── arquitectura.md          [docs]
│   ├── despliegue.md            [docs]
│   └── diccionario-datos.md     [docs]
├── etl/
│   ├── run_etl.py               ✔ HECHO — no tocar
│   ├── load_postgis.py          [backend] carga processed → PostGIS
│   └── sql/schema.sql           [backend]
├── data/processed/              ✔ HECHO — generado por el ETL, no tocar
│   ├── municipios.geojson  subregiones.geojson  metadata.json
│   ├── serie_municipal.csv  serie_regional.csv
│   ├── hotspots/<periodo>.geojson   (12 periodos, ver §4)
│   └── capas/{areas_protegidas,resguardos,consejos,cuencas}.geojson
├── backend/                     [backend]
│   ├── app/
│   │   ├── main.py              FastAPI app + CORS + routers
│   │   ├── config.py            rutas de datos, DATABASE_URL opcional
│   │   ├── repository.py        acceso a datos EN MEMORIA (archivos)
│   │   ├── repository_postgis.py misma interfaz sobre PostGIS (si DATABASE_URL)
│   │   ├── schemas.py           modelos Pydantic
│   │   ├── analytics.py         KPIs, ranking, breaks, predicción
│   │   ├── downloads.py         CSV/XLSX/GeoJSON/ZIP dinámicos
│   │   └── routers/{geo,series,analitica,descargas}.py
│   ├── tests/test_api.py        pytest + httpx TestClient
│   ├── requirements.txt         fastapi, uvicorn[standard], pandas, openpyxl
│   └── requirements-postgis.txt sqlalchemy, geoalchemy2, psycopg2-binary, geopandas
└── frontend/                    [f-core + módulos]
    ├── package.json  tsconfig.json  tailwind.config.ts  postcss.config.js
    ├── next.config.mjs  .env.local.example
    └── src/
        ├── app/
        │   ├── layout.tsx  page.tsx  globals.css        [f-core]
        │   ├── mapa/page.tsx                            [f-mapa]
        │   ├── dashboard/page.tsx                       [f-dash]
        │   ├── aprende/page.tsx                         [f-edu]
        │   └── datos/page.tsx                           [f-datos]
        ├── components/
        │   ├── ui/          (Navbar, Footer, ThemeToggle, KpiCard, Loader,
        │   │                 SectionHeading, Badge, BotonExportar)  [f-core]
        │   ├── mapa/        [f-mapa]
        │   ├── dashboard/   [f-dash]
        │   ├── aprende/     [f-edu]
        │   └── datos/       [f-datos]
        ├── lib/
        │   ├── api.ts       cliente HTTP tipado (contrato §5)      [f-core]
        │   ├── types.ts     tipos compartidos (§6)                 [f-core]
        │   ├── format.ts    formateo es-CO de números/ha           [f-core]
        │   └── colores.ts   escala choropleth + tokens (§7)        [f-core]
        └── store/useAppStore.ts   zustand (§6.4)                   [f-core]
```

Etiquetas `[...]`: quién escribe cada zona. **Nadie escribe fuera de su zona.**

## 3. Stack (versiones fijadas)

- **Frontend**: Next.js `14.2.15` (App Router) · React `18.3.1` · TypeScript `^5.4`
  · Tailwind CSS `3.4.x` · leaflet `1.9.4` + react-leaflet `4.2.1` ·
  recharts `2.12.7` · framer-motion `11.x` · zustand `4.5.x` ·
  lucide-react `0.4xx` · html-to-image `1.11.x` · clsx.
- **Basemap**: teselas CARTO (sin API key):
  claro `https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png`,
  oscuro `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`.
  Atribución obligatoria: `© OpenStreetMap · © CARTO`.
- **Backend**: Python 3.10 · FastAPI · uvicorn · pandas · openpyxl.
  Sin geopandas en runtime del API (los GeoJSON se sirven como JSON crudo).
- **BD opcional**: PostgreSQL + PostGIS vía `DATABASE_URL`; el API funciona
  100% sin BD leyendo `data/processed/` (modo por defecto).
- Puertos: API `8000`, frontend `3000`. Frontend lee `NEXT_PUBLIC_API_URL`
  (default `http://localhost:8000`).
- **Prohibido**: CDNs externos en runtime (fuentes, JS, CSS), API keys.
  Iconos = lucide-react; ilustraciones = SVG inline propio.

## 4. Datos procesados (LEER, no regenerar)

### 4.1 `serie_municipal.csv` (1.123 filas) — columnas exactas
`codigo_dane,municipio,subregion,periodo,ano_inicio,ano_fin,clase,hectareas,hectareas_anuales,fuente,estimado`

Ejemplo real:
`05045,Apartadó,Centro,2002-2004,2002,2004,Deforestación,127.91,63.96,shapefile,False`

- `clase` ∈ {Bosque Estable, Deforestación, No Bosque Estable, Regeneración, Sin Información}
- `fuente` ∈ {shapefile, excel, cuencas-calibrado, raster, estimado, estimado-calibrado-rat}
- `estimado` ∈ {True, False} (string en CSV — parsear con cuidado)
- Periodos (18): 2000-2002, 2002-2004, 2004-2006, 2006-2008, 2008-2010,
  2010-2012, 2012-2013, 2013-2014, 2014-2015, 2015-2016, 2016-2017, 2017-2018,
  2018-2019, 2019-2020, 2020-2021, 2021-2022, 2022-2023, 2023-2024.
  Los 5 primeros duran 2 años (usar `hectareas_anuales` para comparar).
- Periodos con `estimado=True` en Deforestación: 2010-2012, 2015-2016,
  2018-2019, 2023-2024 (mostrar SIEMPRE con distintivo visual).
- Clases distintas de Deforestación NO existen para los periodos estimados.

### 4.2 `municipios.geojson` — 19 features, WGS84
properties: `municipio_key` (p.ej. `APARTADO`), `codigo_dane` (`05045`),
`nombre` (`Apartadó`), `subregion` ∈ {Caribe, Centro, Atrato, Nutibara, Urrao},
`area_municipio_ha`, `centroide` `[lon, lat]`.

### 4.3 `hotspots/<periodo>.geojson` — solo 12 periodos
Disponibles: 2002-2004, 2004-2006, 2006-2008, 2008-2010, 2012-2013, 2013-2014,
2016-2017, 2017-2018, 2019-2020, 2020-2021, 2021-2022, 2022-2023.
properties: `municipio` (nombre bonito o null), `ha`.
La UI debe degradar con elegancia cuando un periodo no tiene hotspots.

### 4.4 `capas/*.geojson`
- `areas_protegidas` (21): `nombre`, `categoria`, `area_ha`, `deforestacion_ha_ultimo_periodo`
- `resguardos` (39): `nombre`, `pueblo`, + ídem
- `consejos` (7): `nombre`, + ídem
- `cuencas` (7): `nomb_cuenc`, + ídem

### 4.5 `metadata.json`
Diccionario completo: periodos+fuentes, municipios, notas metodológicas
(`nota_estimados`, `nota_2015_2016`), QA (`qa_calculos`), log del ETL.

### 4.6 Cifras de referencia (validación rápida)
Deforestación regional total 2000–2024 ≈ **46.041 ha**. Pico medido:
2015-2016 ≈ 4.970 ha (calibrado) y 2016-2017 ≈ 3.938 ha. Mínimo: 2020-2021 ≈
1.091 ha. Jurisdicción ≈ 1.86 M ha.

## 5. Contrato API (todas bajo `/api/v1`)

| Método/Ruta | Query | Respuesta (200) |
|---|---|---|
| GET `/salud` | — | `{"estado":"ok","version":"1.0.0","modo_datos":"archivos"\|"postgis"}` |
| GET `/metadata` | — | contenido de metadata.json |
| GET `/periodos` | — | `[{"id":"2002-2004","ano_inicio":2002,"ano_fin":2004,"anos":2,"fuente":"shapefile","tiene_hotspots":true}]` |
| GET `/municipios` | — | FeatureCollection §4.2 |
| GET `/subregiones` | — | FeatureCollection |
| GET `/serie` | `municipio` (codigo_dane o nombre, repetible), `subregion`, `clase` (default `Deforestación`), `desde` (año), `hasta`, `incluir_estimados` (default `true`) | `{"data":[FilaSerie...],"total_ha":n,"nota":str\|null}` |
| GET `/serie/regional` | `clase`, `incluir_estimados` | `{"data":[{"periodo","ano_inicio","ano_fin","hectareas","hectareas_anuales","estimado"}]}` |
| GET `/choropleth` | `periodo` (req.), `metrica`=`hectareas`\|`hectareas_anuales` | `{"periodo","metrica","valores":{"05045":{"hectareas":..,"hectareas_anuales":..,"estimado":false,"municipio":"Apartadó"}},"breaks":[b1..b5],"max":n}` breaks = quantiles p20..p100 sobre los 19 valores |
| GET `/ranking` | `periodo` (default: todo el rango), `n` (10), `metrica` | `{"data":[{"codigo_dane","municipio","subregion","hectareas","hectareas_anuales","estimado","posicion"}]}` |
| GET `/kpis` | `incluir_estimados` | `{"total_deforestado_ha","promedio_anual_ha","periodo_mas_critico":{"periodo","hectareas","estimado"},"municipio_mas_afectado":{"municipio","codigo_dane","hectareas"},"periodo_menor":{...},"n_periodos","n_municipios","pct_datos_estimados"}` |
| GET `/comparacion` | `municipios` = códigos separados por coma (2–6) | `{"data":[{"municipio","codigo_dane","serie":[{"periodo","hectareas_anuales","estimado"}]}]}` |
| GET `/hotspots/{periodo}` | — | FeatureCollection; **404** → `{"detail":"...","disponibles":[...]}` |
| GET `/capas` | — | `{"capas":[{"id":"areas_protegidas","nombre":"Áreas protegidas","unidades":21}...]}` |
| GET `/capas/{id}` | — | FeatureCollection |
| GET `/prediccion` | `municipio` (opcional → regional), `horizonte` (1–5, default 3), `incluir_estimados` (default false) | `{"historico":[{"periodo","hectareas_anuales"}],"prediccion":[{"ano","hectareas_anuales_estimadas","intervalo":[lo,hi]}],"metodo":"regresión lineal sobre tasa anual","advertencia":str}` |
| GET `/descargas/serie.csv` | mismos filtros de `/serie` | text/csv con BOM UTF-8 y cabecera de metadatos comentada `#` |
| GET `/descargas/serie.xlsx` | ídem | XLSX con hojas `datos` + `metadatos` |
| GET `/descargas/municipios.geojson` | — | archivo |
| GET `/descargas/hotspots/{periodo}.geojson` | — | archivo |
| GET `/descargas/paquete.zip` | — | zip de todo `data/processed` |

Errores: FastAPI estándar `{"detail": "..."}`. Validación con Query/Pydantic.
CORS: permitir `http://localhost:3000` y `*` configurable con env `CORS_ORIGINS`.
Nombres de municipio se aceptan con o sin tildes, case-insensitive.

## 6. Tipos compartidos frontend (`src/lib/types.ts` — EXACTO)

```ts
export type Clase = 'Bosque Estable'|'Deforestación'|'No Bosque Estable'|'Regeneración'|'Sin Información';
export interface Periodo { id: string; ano_inicio: number; ano_fin: number; anos: number; fuente: string; tiene_hotspots: boolean; }
export interface FilaSerie { codigo_dane: string; municipio: string; subregion: string; periodo: string; ano_inicio: number; ano_fin: number; clase: Clase; hectareas: number; hectareas_anuales: number; fuente: string; estimado: boolean; }
export interface ValorChoropleth { hectareas: number; hectareas_anuales: number; estimado: boolean; municipio: string; }
export interface Choropleth { periodo: string; metrica: 'hectareas'|'hectareas_anuales'; valores: Record<string, ValorChoropleth>; breaks: number[]; max: number; }
export interface Kpis { total_deforestado_ha: number; promedio_anual_ha: number; periodo_mas_critico: { periodo: string; hectareas: number; estimado: boolean }; municipio_mas_afectado: { municipio: string; codigo_dane: string; hectareas: number }; periodo_menor: { periodo: string; hectareas: number; estimado: boolean }; n_periodos: number; n_municipios: number; pct_datos_estimados: number; }
export interface ItemRanking { codigo_dane: string; municipio: string; subregion: string; hectareas: number; hectareas_anuales: number; estimado: boolean; posicion: number; }
export interface Prediccion { historico: { periodo: string; hectareas_anuales: number }[]; prediccion: { ano: number; hectareas_anuales_estimadas: number; intervalo: [number, number] }[]; metodo: string; advertencia: string; }
export type Subregion = 'Caribe'|'Centro'|'Atrato'|'Nutibara'|'Urrao';
```

### 6.2 Cliente API (`src/lib/api.ts`) — firmas exportadas EXACTAS
```ts
export const API_URL: string; // process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
export async function getPeriodos(): Promise<Periodo[]>;
export async function getMunicipios(): Promise<GeoJSON.FeatureCollection>;
export async function getChoropleth(periodo: string, metrica?: 'hectareas'|'hectareas_anuales'): Promise<Choropleth>;
export async function getSerie(params?: { municipio?: string[]; subregion?: string; clase?: string; desde?: number; hasta?: number; incluirEstimados?: boolean }): Promise<{ data: FilaSerie[]; total_ha: number; nota: string|null }>;
export async function getSerieRegional(clase?: string, incluirEstimados?: boolean): Promise<{ data: { periodo: string; ano_inicio: number; ano_fin: number; hectareas: number; hectareas_anuales: number; estimado: boolean }[] }>;
export async function getRanking(periodo?: string, n?: number, metrica?: string): Promise<{ data: ItemRanking[] }>;
export async function getKpis(incluirEstimados?: boolean): Promise<Kpis>;
export async function getComparacion(codigos: string[]): Promise<{ data: { municipio: string; codigo_dane: string; serie: { periodo: string; hectareas_anuales: number; estimado: boolean }[] }[] }>;
export async function getHotspots(periodo: string): Promise<GeoJSON.FeatureCollection|null>; // null si 404
export async function getCapa(id: string): Promise<GeoJSON.FeatureCollection>;
export async function getPrediccion(municipio?: string, horizonte?: number): Promise<Prediccion>;
export function urlDescarga(ruta: string, params?: Record<string,string>): string; // p.ej. urlDescarga('serie.csv', {...})
```

### 6.3 `src/lib/format.ts`
```ts
export function fmtHa(n: number): string;        // '3.938 ha' es-CO sin decimales
export function fmtNum(n: number, dec?: number): string;
export function fmtPct(n: number): string;
```

### 6.4 Store zustand (`src/store/useAppStore.ts`)
```ts
interface AppState {
  periodoActivo: string;             // default '2022-2023'
  metrica: 'hectareas'|'hectareas_anuales';
  reproduciendo: boolean;            // timelapse
  capasActivas: string[];            // ids de overlays + 'hotspots'
  municipioSeleccionado: string|null;// codigo_dane
  incluirEstimados: boolean;         // default true
  setPeriodo(p: string): void; setMetrica(m: AppState['metrica']): void;
  toggleReproduccion(): void; toggleCapa(id: string): void;
  setMunicipio(c: string|null): void; setIncluirEstimados(v: boolean): void;
}
```

## 7. Diseño visual

### 7.1 Tokens Tailwind (extend en `tailwind.config.ts`)
```
colors: {
  bosque:  {50:'#ECF8F0',100:'#D2EEDC',300:'#7BC796',500:'#2E8B57',600:'#1F7347',700:'#175E3A',800:'#0F4A2D',900:'#0B3D25',950:'#062818'},
  alerta:  {50:'#FFF8F1',100:'#FEECDC',300:'#FDBA74',500:'#F97316',600:'#EA580C',700:'#C2410C',800:'#9A3412',900:'#7C2D12'},
  fuego:   {500:'#DC2626',700:'#B91C1C',900:'#7F1D1D'},
  tierra:  {100:'#F5F0E8',300:'#D9CDB8',500:'#A8927A',700:'#6B5744'},
}
fontFamily: { display: ['var(--font-display)'], body: ['var(--font-body)'] }
```
Fuentes vía `next/font/google` (se autoalojan en build, sin CDN en runtime):
display = `Fraunces` (títulos, aire National Geographic), body = `Inter`.

### 7.2 Escala choropleth (`src/lib/colores.ts`)
```ts
export const RAMPA_DEFORESTACION = ['#FEF3C7','#FDBA74','#F97316','#DC2626','#7F1D1D']; // 5 clases por breaks
export function colorPara(valor: number|undefined, breaks: number[]): string; // undefined → '#E5E7EB'
export const COLOR_SIN_DATOS = '#E5E7EB';
export const PATRON_ESTIMADO = { dashArray: '4 3', fillOpacity: 0.55 }; // polígonos estimados
```
Municipios con dato estimado: borde `dashArray '4 3'` + badge "estimado" en
tooltip/leyenda. Dark mode: clase `dark` en `<html>` (persistida en
localStorage, default sistema).

### 7.3 Personalidad
Editorial-cartográfica: titulares Fraunces grandes, datos protagonistas,
verde bosque profundo + ámbar/rojo de alerta, generoso espacio en blanco,
microanimaciones framer-motion (fade-up al entrar en viewport, contadores
animados en KPIs). Nada de stock photos: SVG propios e iconografía lucide.
Responsive: móvil primero en /aprende y /datos; /mapa y /dashboard optimizados
desktop pero usables en móvil (paneles colapsables).

## 8. Especificación por módulo

### 8.1 `/` Landing [f-core]
Hero a pantalla completa (gradiente bosque-950→900 con SVG topográfico sutil
animado), titular «Observatorio de Deforestación de Urabá», subtítulo con
periodo 2000–2024 y 19 municipios, CTA a /mapa y /aprende. Franja de KPIs
reales (fetch `/kpis`) con contadores animados. 4 tarjetas de módulos.
Sección «¿Cómo leer estos datos?» con nota honesta sobre periodos estimados.
Footer institucional (CORPOURABA · datos procesados del monitoreo de bosque).

### 8.2 `/mapa` [f-mapa]
- Mapa Leaflet full-height (bajo navbar). Import dinámico `ssr:false`.
- Choropleth de 19 municipios coloreado por `/choropleth?periodo=X&metrica=Y`.
- **Slider temporal** de 18 periodos con marcas de año + botón ▶ timelapse
  (avanza cada 1.4 s, loop, pausable) — usa el store.
- Tooltips hover: nombre, periodo, ha, ha/año, badge «estimado» si aplica.
- Click municipio → panel lateral: sparkline de su serie completa (recharts),
  posición en ranking, área municipio, subregión, botón «Ver en dashboard»
  (navega `/dashboard?municipio=05045`) y «Descargar CSV».
- Toggles de capas: Hotspots del periodo (si `tiene_hotspots`; si no,
  aviso «sin polígonos para este periodo»), Áreas protegidas, Resguardos,
  Consejos comunitarios, Cuencas, Subregiones. Estilos distinguibles
  (líneas/fills tenues), popup con nombre + deforestación reciente.
- Leyenda dinámica con breaks del endpoint y franja «estimado» (dash).
- Zoom inteligente: botón «ajustar a jurisdicción» (fitBounds), doble-click
  municipio → fitBounds del feature.
- Controles flotantes estilo tarjeta (backdrop-blur), responsive (colapsan
  a bottom-sheet en móvil).

### 8.3 `/dashboard` [f-dash]
- Barra de filtros sticky: subregión (select), municipios (multiselect chips),
  rango de periodos (slider doble), toggle «incluir estimados», botón limpiar.
  Lee `?municipio=` de la URL al montar.
- Fila KPI: 4 KpiCard animadas (total, promedio anual, periodo crítico,
  municipio más afectado) — recalculadas según filtros (cliente sobre /serie).
- Gráficos (recharts, todos con botón exportar PNG vía html-to-image y CSV):
  1. **Serie temporal** área+línea de ha/año regional o filtrada; periodos
     estimados con relleno rayado/punto hueco + ReferenceArea sombreada.
  2. **Ranking** barras horizontales top-10 por periodo o acumulado, color
     por rampa, click barra → fija municipio en filtros.
  3. **Comparador** líneas de hasta 6 municipios (ha/año) con leyenda
     interactiva (usa /comparacion).
  4. **Heatmap** municipio×periodo (div-grid con colorPara), tooltip por celda.
  5. **Predicción** (si hay municipio único o regional): línea histórica +
     proyección punteada con banda de intervalo + advertencia visible.
- Nota al pie con fuentes por periodo (de /metadata) y % datos estimados.

### 8.4 `/aprende` [f-edu] — módulo PRAES
- Selector de nivel persistente (tabs): 🌱 Explorador (primaria),
  🌿 Guardián (secundaria), 🌳 Científico (media). El contenido de cada
  sección se adapta al nivel (3 variantes de texto).
- Secciones storytelling con scroll (framer-motion reveal):
  1. «¿Qué es la deforestación?» — SVG animado árbol→tocón, comparaciones
     locales (1 ha ≈ 1½ canchas de fútbol; el pico 2015-2016 ≈ 7.000 canchas).
  2. «¿Por qué pasa en Urabá?» — tarjetas causas (ganadería, cultivos,
     tala, vías) con iconos.
  3. «Impactos» — biodiversidad (jaguar, tití, guacamaya), agua, clima local.
  4. «Bosque y clima» — CO₂: explicación por nivel.
  5. «Soluciones basadas en la naturaleza» — restauración, acuerdos,
     sistemas agroforestales, qué puede hacer un colegio (PRAES).
- **Quiz** «¿Cuánto sabes del bosque de Urabá?»: 8 preguntas por nivel con
  datos reales de la serie, feedback inmediato, puntaje final con mensaje
  y confeti CSS (sin líb. externa).
- **Juego «Salva el Bosque»**: tablero 8×8 DOM/CSS; brotes 🌱 aparecen y
  amenazas 🔥🪓 se propagan por turnos (tick 900 ms); click en amenaza la
  apaga, click en celda vacía siembra; 90 s; barra de «hectáreas salvadas»;
  al final relaciona el puntaje con los datos reales de un municipio.
  Teclado-accesible (celdas = buttons).
- **Historias locales**: 4 tarjetas narrativas basadas en datos reales
  (Turbo y el manglar, Mutatá y la serranía de Abibe, Urrao y el páramo,
  Vigía del Fuerte y el Atrato) — cada una cierra con su mini-sparkline.
- Glosario expandible (accordion) y guía docente descargable (usa
  `urlDescarga`) — enlace a /datos.

### 8.5 `/datos` [f-datos]
- Tarjetas de dataset: Serie municipal (CSV/XLSX), Serie regional (CSV),
  Límites municipales (GeoJSON), Hotspots por periodo (GeoJSON, select),
  Capas de contexto (GeoJSON, select), Paquete completo (ZIP).
- Generador de extracto: selects municipio(s)/periodo/clase/formato →
  botón descarga con `urlDescarga('serie.csv'|'serie.xlsx', params)`.
- Diccionario de datos (tabla desde §4.1) + metodología completa:
  jerarquía de fuentes por periodo (tabla desde /metadata), explicación de
  estimaciones y calibraciones (RAT 2010-2012, cuencas 2015-2016), QA vs
  hojas Cálculos, CRS de origen y salida, licencia/atribución sugerida.
- Vista previa de tabla (primeras 50 filas de /serie con filtros aplicados).

## 9. Backend — detalles de implementación

- `repository.py`: carga en memoria al startup (lifespan): DataFrame de serie
  (parseando `estimado` a bool), dicts de GeoJSON, metadata. Índices simples
  por codigo_dane y nombre normalizado (sin tildes, upper).
- `analytics.py`: breaks = quantiles [0.2,0.4,0.6,0.8,1.0] de los valores >0
  del periodo (fallback si <5 valores). Predicción: numpy polyfit grado 1
  sobre (punto medio del periodo, ha/año) con `incluir_estimados=False` por
  defecto; intervalo = ±1.96·σ residual; clip ≥0; advertencia fija sobre
  incertidumbre. KPIs según §5.
- `downloads.py`: CSV con BOM y cabecera `#` de metadatos (título, fecha,
  filtros, nota estimados); XLSX con hoja `metadatos`; ZIP con zipfile stdlib
  en streaming a memoria (los archivos son <5 MB).
- `main.py`: `FastAPI(title='API Observatorio Deforestación CORPOURABA',
  version='1.0.0')`, CORS desde env, routers con prefijo `/api/v1`, `/`
  redirige a `/docs`.
- `config.py`: `DATA_DIR` = env `DATA_DIR` o `../data/processed` relativo al
  paquete; `DATABASE_URL` opcional activa repository_postgis (import perezoso;
  si falla la conexión → log warning y fallback a archivos).
- `load_postgis.py` + `schema.sql`: tablas `municipios(geom MultiPolygon 4326)`,
  `serie_municipal`, `hotspots(periodo, municipio, ha, geom)`, `capas(...)`,
  índices GIST + índices por (periodo, codigo_dane). Idempotente (DROP/CREATE).
- Tests: salud, periodos (18), municipios (19 features), choropleth de un
  periodo válido e inválido (422/404), kpis coherentes (total ≈ 46.041±100),
  serie con filtros, hotspots 404 con `disponibles`, descargas CSV/XLSX no
  vacías y con BOM.

## 10. Convenciones

- TS `strict: true`; sin `any` salvo GeoJSON de terceros tipado con
  `@types/geojson`. Componentes función + hooks; client components solo donde
  hay interactividad (`'use client'`).
- Español en UI y comentarios; identificadores en español coherentes.
- Accesibilidad: roles/aria en controles custom, contraste AA, `prefers-reduced-motion`
  respetado (framer-motion `useReducedMotion`).
- Python: type hints, docstrings breves, ruff-clean (sin imports muertos).
- Ningún constructor ejecuta servidores ni `npm install`; la integración se
  hace en fase posterior.
```
