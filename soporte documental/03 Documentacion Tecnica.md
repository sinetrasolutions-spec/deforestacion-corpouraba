# Documentación Técnica (Manual del Sistema)

## Observatorio de Deforestación CORPOURABA 2000–2024

Este manual está dirigido a ingenieros y desarrolladores encargados del mantenimiento, la regeneración de datos y el despliegue de la plataforma. Describe la arquitectura, el stack, la estructura del repositorio, las rutas de la API, los procedimientos de ejecución local, la regeneración de datos y entregables, y el despliegue en Vercel. Todas las cifras, rutas y campos citados se han verificado contra el código y los datos reales del proyecto.

---

## 1. Arquitectura general

El Observatorio es una **aplicación Next.js 14 de proyecto único** que integra frontend y backend en un mismo despliegue, usando el **App Router**.

- **Backend nativo en Next.js.** El backend original estaba escrito en **FastAPI** (Python), y todavía se conserva como referencia bajo `backend/` (ver sección 3). Para desplegar todo-en-uno en Vercel, esa API se portó a **route handlers nativos de Next.js** ubicados en `frontend/src/app/api/v1/**`. Cada handler es una función `GET` (con `export const runtime = 'nodejs'` y `export const dynamic = 'force-dynamic'`) que delega la lógica en los módulos de `frontend/src/server/*.ts`.
- **Lógica de datos en `server/*.ts`.** El módulo `server/datos.ts` es una réplica en TypeScript del repositorio de datos de FastAPI: carga en memoria los CSV, GeoJSON y `metadata.json` desde `data/processed`, y expone helpers de filtrado, validación y caché (el objeto `_cache` se comparte entre invocaciones del módulo). Los módulos `analitica.ts`, `analisis.ts` y `descargas.ts` implementan los cálculos de KPIs, análisis temático y generación de descargas.
- **Empaquetado de datos con `outputFileTracingIncludes`.** Los datasets procesados viven en `data/processed`. Para que las funciones serverless de Vercel incluyan esos archivos, `next.config.mjs` declara:

  ```
  experimental: {
    outputFileTracingIncludes: {
      '/api/**': ['./data/processed/**/*'],
    },
  }
  ```

  Como el Root Directory de Vercel es `frontend/` (ver sección 9), existe una copia de los datos en **`frontend/data/processed`**, que es la ruta que los handlers resuelven en tiempo de ejecución mediante `path.join(process.cwd(), 'data', 'processed')`.
- **Sin dependencias de CDN en runtime.** Las fuentes se autoalojan vía `next/font`; no hay llamadas a CDN externos en tiempo de ejecución.
- **Frontend.** Las páginas (`app/page.tsx`, `dashboard`, `mapa`, `parches`, `aprende`, `datos`) consumen la API interna `/api/v1/**`. El mapa y el visor usan `react-leaflet`; las gráficas usan `Recharts`; el estado de cliente usa `zustand`; los estilos usan `Tailwind CSS`.

---

## 2. Stack y versiones

Versiones tomadas de `frontend/package.json` (frontend) y de `backend/requirements.txt` (backend legacy).

### Frontend (`frontend/package.json`)

| Dependencia | Versión |
| --- | --- |
| next | 14.2.15 |
| react | 18.3.1 |
| react-dom | 18.3.1 |
| react-leaflet | 4.2.1 |
| leaflet | 1.9.4 |
| recharts | 2.12.7 |
| zustand | ~4.5.5 |
| framer-motion | ^11.11.9 |
| lucide-react | ^0.454.0 |
| clsx | ^2.1.1 |
| jszip | ^3.10.1 |
| xlsx | ^0.18.5 |
| html-to-image | ~1.11.11 |

### Frontend — herramientas de desarrollo

| Dependencia | Versión |
| --- | --- |
| typescript | ^5.4.5 |
| tailwindcss | ~3.4.14 |
| postcss | ^8.4.47 |
| autoprefixer | ^10.4.20 |
| eslint | ^8.57.1 |
| eslint-config-next | 14.2.15 |
| @types/node | ^20.14.15 |
| @types/react | ^18.3.11 |
| @types/leaflet | ^1.9.12 |
| @types/geojson | ^7946.0.14 |

### Backend legacy (`backend/requirements.txt`)

| Dependencia | Versión |
| --- | --- |
| fastapi | >=0.110,<1.0 |
| uvicorn[standard] | >=0.29,<1.0 |
| pandas | >=2.0,<3.0 |
| openpyxl | >=3.1,<4.0 |
| pytest | >=8.0 |
| httpx | >=0.27 |

### ETL (Python)

El ETL requiere pila geoespacial: `geopandas`, `pyogrio`, `rasterio`, `numpy`, `pandas`, `shapely`. Los entregables Word usan Node.js con el módulo `docx`, y el dashboard Excel usa `openpyxl`.

---

## 3. Estructura de carpetas

Árbol comentado de la raíz `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion`:

```
observatorio-deforestacion/
├── README.md
├── SPEC.md                         Contrato API + diseño + estructura acordados
├── docs/                           Documentación complementaria
│
├── frontend/                       Aplicación Next.js 14 (App Router) — raíz de despliegue
│   ├── package.json
│   ├── next.config.mjs             outputFileTracingIncludes de data/processed
│   ├── data/processed/             Copia empaquetada de los datos (leída en runtime)
│   ├── public/                     Estáticos (logo-corpouraba.png, etc.)
│   └── src/
│       ├── app/
│       │   ├── layout.tsx, page.tsx, globals.css, icon.png
│       │   ├── dashboard/page.tsx      Módulo Dashboard
│       │   ├── mapa/page.tsx           Módulo Mapa (react-leaflet)
│       │   ├── parches/page.tsx        Visor de deforestación (línea de tiempo)
│       │   ├── aprende/page.tsx        Módulo Aprende (PRAES)
│       │   ├── datos/page.tsx          Centro de descargas
│       │   └── api/v1/                 Route handlers (backend nativo Next.js)
│       ├── components/                 dashboard/ mapa/ parches/ aprende/ datos/ ui/
│       ├── server/                     Lógica de backend en TypeScript
│       │   ├── datos.ts                Carga/caché de CSV+GeoJSON+metadata, validaciones
│       │   ├── analitica.ts            KPIs y agregados
│       │   ├── analisis.ts             Análisis temático (territorios, hallazgos)
│       │   └── descargas.ts            Generación de descargas (CSV, XLSX, ZIP)
│       └── lib/                        api.ts, colores.ts, format.ts, types.ts
│
├── etl/                            Pipeline de datos y generación de entregables
│   ├── run_etl.py                  ETL principal (crudo → data/processed)
│   ├── build_excel_dashboard.py   Dashboard Excel autónomo (openpyxl)
│   ├── consolidar_informe.py      Consolida análisis en entregables/informe_datos.json
│   ├── generar_informe.js         Genera el Informe Word (módulo docx)
│   ├── load_postgis.py            Carga opcional a PostGIS
│   ├── analisis/                  Scripts de análisis temático
│   └── sql/                       SQL de apoyo (PostGIS)
│
├── data/processed/                Datos canónicos generados por el ETL
│   ├── serie_municipal.csv        Municipio × periodo × clase (ha, fuente, estimado)
│   ├── serie_regional.csv         Agregado regional por periodo × clase
│   ├── metadata.json              Diccionario de datos, fuentes por periodo, QA, log
│   ├── municipios.geojson         Límites de los 19 municipios (WGS84)
│   ├── subregiones.geojson        5 subregiones CORPOURABA
│   ├── hotspots/<periodo>.geojson Polígonos de deforestación ≥1 ha por periodo
│   ├── capas/*.geojson            Capas de contexto y cartografía oficial
│   └── analisis/                  Salidas del análisis temático (series, resúmenes,
│                                  hallazgos.json, recurrencia.geojson, cartografia/)
│
├── entregables/                   Productos finales
│   ├── Dashboard_Deforestacion_CORPOURABA_2000-2024.xlsx
│   ├── Informe_Deforestacion_CORPOURABA_2000-2024.docx
│   └── informe_datos.json         Fuente de datos consolidada del informe
│
└── backend/                       API FastAPI original (legacy, referencia)
    ├── requirements.txt, requirements-postgis.txt
    ├── app/                        main.py, config.py, repository.py,
    │                               repository_postgis.py, analytics.py,
    │                               downloads.py, schemas.py, routers/
    └── tests/                      test_api.py
```

**Nota sobre `backend/`.** El backend FastAPI ya no participa en el despliegue web (que ahora corre íntegramente sobre las rutas Next.js). Se conserva como referencia y como implementación equivalente para escenarios con base de datos (`repository_postgis.py`). El módulo `server/datos.ts` es la réplica funcional en TypeScript de `app/repository.py`.

---

## 4. Rutas de la API

Todas las rutas cuelgan de `frontend/src/app/api/v1/`. Son handlers `GET` con `runtime = 'nodejs'` y `dynamic = 'force-dynamic'`. Lista real de rutas y lo que devuelve cada grupo:

### Salud y metadatos

| Ruta | Devuelve |
| --- | --- |
| `GET /api/v1/salud` | Estado del servicio: `{ estado: 'ok', version, modo_datos: 'archivos' }` |
| `GET /api/v1/metadata` | Diccionario de datos completo (`metadata.json`): clases, gridcode, periodos y fuentes, municipios, notas de estimados, QA |
| `GET /api/v1/periodos` | Lista de periodos con la bandera `tiene_hotspots` |
| `GET /api/v1/municipios` | Catálogo de los 19 municipios (código DANE, nombre, subregión) |
| `GET /api/v1/subregiones` | Las 5 subregiones territoriales |

### Series y KPIs

| Ruta | Devuelve |
| --- | --- |
| `GET /api/v1/kpis` | Indicadores agregados de deforestación (acepta `?incluir_estimados=false`) |
| `GET /api/v1/serie` | Serie municipal filtrable (municipios, subregión, clase, `desde`/`hasta`, estimados) |
| `GET /api/v1/serie/regional` | Serie regional agregada por periodo |
| `GET /api/v1/ranking` | Ranking de municipios por deforestación |
| `GET /api/v1/comparacion` | Comparación entre municipios/subregiones |
| `GET /api/v1/choropleth` | Datos para el mapa coroplético (ha por municipio) |
| `GET /api/v1/prediccion` | Serie con proyección/tendencia |

### Geometrías y capas del visor

| Ruta | Devuelve |
| --- | --- |
| `GET /api/v1/capas` | Índice de capas de contexto/cartografía oficial disponibles |
| `GET /api/v1/capas/[id]` | GeoJSON de una capa concreta (áreas protegidas, resguardos, consejos, cuencas, POMCAS, Ley 2ª, títulos mineros) |
| `GET /api/v1/hotspots/[periodo]` | Polígonos de deforestación (≥1 ha) del periodo |
| `GET /api/v1/parches` | Parches de deforestación para el explorador |
| `GET /api/v1/parches/resumen` | Resumen agregado de parches |

### Análisis temático (cruces con cartografía)

| Ruta | Devuelve |
| --- | --- |
| `GET /api/v1/analisis` | Índice de análisis temáticos disponibles |
| `GET /api/v1/analisis/resumen/[...dataset]` | Resumen de un dataset de análisis |
| `GET /api/v1/analisis/tabla/[...dataset]` | Tabla de datos de un análisis |
| `GET /api/v1/analisis/geo/[...dataset]` | GeoJSON asociado a un análisis |
| `GET /api/v1/analisis/territorios` | Deforestación por tipo de territorio/unidad |
| `GET /api/v1/analisis/territorios/[tipo]` | Detalle por tipo (AP, POMCAS, resguardos, consejos, etc.) |
| `GET /api/v1/analisis/hallazgos` | Hallazgos clave (`analisis/hallazgos.json`) |

### Descargas (Centro de descargas)

| Ruta | Devuelve |
| --- | --- |
| `GET /api/v1/descargas/serie.csv` | Serie municipal en CSV |
| `GET /api/v1/descargas/serie.xlsx` | Serie en Excel |
| `GET /api/v1/descargas/municipios.geojson` | Límites municipales |
| `GET /api/v1/descargas/hotspots/[archivo]` | Archivo de hotspots por periodo |
| `GET /api/v1/descargas/paquete.zip` | Paquete completo comprimido |

Los errores se serializan con `errorJson`, que traduce `ErrorDatos` a su código HTTP sugerido (404 para recursos desconocidos, 422 para parámetros inválidos, 500 para errores internos).

---

## 5. Requisitos previos

- **Node.js** ≥ 18.17 (recomendado 20.x, alineado con `@types/node` ^20). Incluye npm.
- **Python** 3.10 o superior para el ETL y los scripts de entregables.
- **Pila geoespacial de Python** para el ETL: `geopandas`, `pyogrio`, `rasterio`, `numpy`, `pandas`, `shapely`. En Windows se recomienda instalarlos con `pip` sobre wheels precompilados o vía `conda`, dado que `rasterio`/`pyogrio` dependen de GDAL.
- **Módulo Node `docx`** (global) para generar el Informe Word.
- **Git** y una cuenta con acceso al repositorio GitHub `sinetrasolutions-spec/deforestacion-corpouraba`.
- Datos crudos del paquete de monitoreo (shapefiles, Excel y rásters por periodo) si se va a regenerar el ETL; por defecto el ETL los busca en `E:\drive-download-20260703T192518Z-3-001`.

---

## 6. Cómo ejecutar en local

La aplicación web corre desde `frontend/`:

```
cd frontend
npm install
npm run dev
```

El servidor de desarrollo escucha en el **puerto 3000** (`next dev -p 3000` en `package.json`). Abrir `http://localhost:3000`.

Para una build de producción local:

```
npm run build
npm run start   # sirve en el puerto 3000 (next start -p 3000)
```

La aplicación lee los datos desde `frontend/data/processed`. Si esa carpeta no está sincronizada con `data/processed` (raíz), copie el contenido antes de arrancar, o vuelva a ejecutar el ETL (sección 7), que escribe la copia empaquetada.

---

## 7. Cómo regenerar los datos (ETL)

El pipeline `etl/run_etl.py` consolida el paquete crudo (shapefiles, Excel y rásters por periodo) en los datasets de `data/processed`.

```
python etl/run_etl.py [--raw RUTA_DATOS_CRUDOS] [--out RUTA_SALIDA]
```

- `--raw`: carpeta de datos crudos (por defecto `E:\drive-download-20260703T192518Z-3-001`).
- `--out`: carpeta de salida (por defecto `data/processed` en la raíz del proyecto).

**Qué produce:** `municipios.geojson`, `subregiones.geojson`, `serie_municipal.csv`, `serie_regional.csv`, `hotspots/<periodo>.geojson`, `capas/*.geojson` y `metadata.json`.

**Jerarquía de fuentes por periodo** (de mejor a peor), tal como la implementa el ETL:

1. **shapefile** de municipios (polígonos con `NOM_MUNICI` + área por geometría).
2. **excel** (tabla de atributos exportada, `*_Mpios_Dat.xls[x]`).
3. **cuencas** (Excel/dbf con `NOM_MUNICI` + `AREA HA`, cobertura parcial).
4. **raster** (zonal stats del ráster, vía `rasterio`).
5. **estimado** (interpolación/tendencia lineal; **siempre** marcado con `estimado=True`).

**Dependencias geoespaciales.** El ETL importa `geopandas`, `numpy`, `pandas`, `shapely` a nivel de módulo, y usa el motor **`pyogrio`** para leer vectoriales (`gpd.read_file(..., engine="pyogrio")`, con reintento en `latin-1`) y **`rasterio`** para las estadísticas zonales del ráster.

**CRS.** El paquete crudo está mayoritariamente en **EPSG:3115** (MAGNA-SIRGAS Bogotá / Colombia West, métrico), usado como fallback métrico; toda la salida web se reproyecta a **EPSG:4326** (WGS84).

**QA automático.** El último paso del ETL valida los totales calculados contra las hojas «Cálculos» de los Excel originales y registra la diferencia porcentual en `metadata.json` (campo `qa_calculos` y `log`). En la corrida actual las diferencias por periodo están todas por debajo del 0,3 % (p. ej. 2000-2002 y 2014-2015 con 0,00 %; 2016-2017 con 0,29 %). El total consolidado de deforestación (clase «Deforestación») es **46.845,5 ha**.

**Periodos.** 18 periodos entre 2000 y 2024. El periodo **2015-2016** se recupera como **dato MEDIDO** desde la tabla municipal `.dbf` (`Defor2015_2016_Mpios_Proj_Correg.dbf`), con `estimado=false`; su geometría `.shp` no se conservó, por lo que no aparece en el visor de polígonos, pero sus cifras en dashboard y serie son reales. Solo quedan **3 periodos estimados**: `2010-2012`, `2018-2019` y `2023-2024` (campo `vacios_estimados` en `metadata.json`).

Tras la corrida, sincronice la salida con la copia empaquetada del frontend (`frontend/data/processed`) para que la web sirva los datos actualizados.

---

## 8. Cómo regenerar los entregables

Los entregables viven en `entregables/`: el **Dashboard Excel** y el **Informe Word**.

### Dashboard Excel

```
python etl/build_excel_dashboard.py
```

Genera `entregables/Dashboard_Deforestacion_CORPOURABA_2000-2024.xlsx`: un libro autónomo y dinámico con fórmulas nativas (sin macros) — Portada, Dashboard (KPIs + gráficos), Consulta por municipio (desplegable), matriz municipio × periodo, serie regional, serie municipal, hoja auxiliar de cálculos y diccionario/metodología. Todos los agregados son fórmulas de Excel sobre la hoja de datos, de modo que el libro sea auditable y extensible. Requiere `openpyxl`. Debe ejecutarse **después** del ETL (o de cualquier recálculo de la serie) para reflejar cifras actualizadas.

### Informe Word

Es un proceso de dos pasos:

1. **Consolidación de datos (Python):**

   ```
   python etl/consolidar_informe.py
   ```

   Lee `data/processed` y `data/processed/analisis` (incluida la subcarpeta `cartografia/`) y escribe la fuente de datos consolidada `entregables/informe_datos.json`.

2. **Generación del documento (Node.js):**

   ```
   node etl/generar_informe.js
   ```

   Lee `entregables/informe_datos.json` y el logo `frontend/public/logo-corpouraba.png`, y escribe `entregables/Informe_Deforestacion_CORPOURABA_2000-2024.docx` usando el módulo **`docx`**.

   El generador **requiere el módulo `docx`**. Si no está en las dependencias locales del proyecto, instálelo de forma global y apunte `NODE_PATH` a la carpeta de módulos globales de npm antes de ejecutar el script, por ejemplo:

   ```
   npm install -g docx
   # Windows (PowerShell): $env:NODE_PATH = "$(npm root -g)"; node etl/generar_informe.js
   # Bash:                 NODE_PATH="$(npm root -g)" node etl/generar_informe.js
   ```

   Así el `require('docx')` del script resuelve el módulo desde la instalación global.

---

## 9. Despliegue en Vercel

El proyecto se despliega en Vercel con configuración de subcarpeta:

1. **Root Directory = `frontend`.** El repositorio contiene varias carpetas (ETL, backend, datos); la app Next.js está en `frontend/`, y ese debe ser el Root Directory del proyecto Vercel.
2. **Framework Preset = Next.js.** Debe quedar explícitamente en «Next.js».
3. **Redeploy** tras confirmar ambos ajustes.

**Fallo conocido — Framework Preset en «Other».** Cuando el Root Directory es `frontend`, Vercel a veces **no autodetecta** el framework y deja el Framework Preset en **«Other»**. En ese caso el sitio devuelve **404** (no se aplican el App Router ni las funciones serverless). La corrección es entrar a *Project Settings → General*, fijar manualmente **Framework Preset = Next.js**, guardar y **volver a desplegar (Redeploy)**. Verifíquelo tras el primer despliegue.

**Empaquetado de datos.** El `outputFileTracingIncludes` de `next.config.mjs` garantiza que `frontend/data/processed/**/*` se incluya en las funciones `/api/**`. Si se cambia la ubicación de los datos, ajuste ese patrón en consecuencia.

**Comprobación posdespliegue.** Consulte `GET /api/v1/salud` (debe responder `{ estado: 'ok', modo_datos: 'archivos' }`) y `GET /api/v1/kpis` para confirmar que los datos están empaquetados y accesibles.

---

## 10. Cómo incorporar un periodo nuevo o datos reales de los estimados

Para añadir un periodo nuevo o sustituir uno de los 3 periodos estimados (`2010-2012`, `2018-2019`, `2023-2024`) por su dato real:

1. **Coloque los archivos** del periodo en la carpeta de datos crudos (la que se pasa con `--raw`, por defecto `E:\drive-download-20260703T192518Z-3-001`), siguiendo la convención de nombres del paquete original (shapefile de municipios `Defor<AAAA>_<AAAA>_Mpios_Proj*.shp`, o la tabla de atributos `.xls`/`.dbf` con `NOM_MUNICI` + área por clase). El ETL selecciona la mejor fuente disponible según la jerarquía de la sección 7; un shapefile o una tabla municipal real desplaza automáticamente a la estimación.
2. **Ejecute el ETL:**

   ```
   python etl/run_etl.py
   ```

   El pipeline recalculará la serie, regenerará hotspots (si hay geometría del periodo), actualizará `metadata.json` (fuentes por periodo, `vacios_estimados`, QA) y marcará el periodo como `estimado=false` cuando provenga de dato medido.
3. **Regenere los entregables** afectados (sección 8): `build_excel_dashboard.py`, y `consolidar_informe.py` + `generar_informe.js`.
4. **Sincronice** `data/processed` → `frontend/data/processed` y **haga commit + push** para disparar el redeploy en Vercel.

Para un periodo **completamente nuevo** (posterior a 2024), añada además su definición al bloque `periodos` que produce el ETL, de modo que aparezca en `metadata.json` y, por tanto, en `/api/v1/periodos` y en el visor.

---

## 11. Repositorio y credenciales

- **Repositorio:** GitHub `sinetrasolutions-spec/deforestacion-corpouraba`.
- **Despliegue:** Vercel, conectado a la rama principal del repositorio (push → build automático).
- **Autores de la plataforma:** Alberto Vivas y Carlos Zuluaga.
- **Entidad:** CORPOURABA (Corporación para el Desarrollo Sostenible del Urabá).

**Manejo de secretos.** El despliegue en modo archivos **no requiere secretos ni variables de entorno**: los datos van empaquetados y los handlers los leen del sistema de archivos. No incluya credenciales en el repositorio. Si en el futuro se activa el backend PostGIS (`etl/load_postgis.py`, `backend/app/repository_postgis.py`), configure la cadena de conexión mediante variables de entorno del entorno de despliegue (nunca versionadas), y gestione los tokens de GitHub/Vercel exclusivamente en la configuración de cada plataforma.

---

Archivos de referencia (rutas absolutas):

- Configuración Next.js: `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\frontend\next.config.mjs`
- Dependencias frontend: `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\frontend\package.json`
- Lógica de datos servidor: `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\frontend\src\server\datos.ts`
- Rutas API: `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\frontend\src\app\api\v1\`
- ETL: `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\etl\run_etl.py`
- Entregables: `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\etl\build_excel_dashboard.py`, `consolidar_informe.py`, `generar_informe.js`
- Metadatos de datos: `E:\drive-download-20260703T192518Z-3-001\observatorio-deforestacion\data\processed\metadata.json`
