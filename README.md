# Observatorio de Deforestación CORPOURABA (2000–2024)

Plataforma web institucional para **explorar, analizar, aprender y descargar**
los datos de deforestación de los **19 municipios** de la jurisdicción de
CORPOURABA (Urabá y Occidente antioqueño) entre **2000 y 2024**.

La plataforma consolida el monitoreo de bosque de la Corporación —shapefiles,
tablas Excel y rásters por periodo— en una serie homogénea de 18 periodos y la
expone en cuatro módulos:

| Módulo | Ruta | Qué ofrece |
|---|---|---|
| 🗺️ **Mapa interactivo** | `/mapa` | Choropleth municipal por periodo, slider temporal con timelapse, hotspots de deforestación, capas de contexto (áreas protegidas, resguardos, consejos comunitarios, cuencas, subregiones) |
| 📊 **Dashboard analítico** | `/dashboard` | KPIs, serie temporal, ranking municipal, comparador, heatmap municipio×periodo y predicción con banda de incertidumbre |
| 🌱 **Módulo educativo PRAES** | `/aprende` | Contenido por nivel escolar (Explorador/Guardián/Científico), quiz, juego «Salva el Bosque», historias locales y glosario |
| 📥 **Centro de descargas** | `/datos` | CSV/XLSX/GeoJSON/ZIP, generador de extractos filtrados, diccionario de datos y metodología |

Cifras de referencia de la serie: deforestación regional acumulada 2000–2024
≈ **46.041 ha**; pico medido 2015-2016 ≈ 4.970 ha (calibrado) y 2016-2017
≈ 3.938 ha; mínimo 2020-2021 ≈ 1.091 ha; jurisdicción ≈ 1,86 millones de ha.

> ⚠️ **Nota de honestidad de datos**: los periodos **2010-2012, 2015-2016,
> 2018-2019 y 2023-2024** no tienen fuente municipal directa y se publican como
> **estimaciones** (`estimado=true`), siempre con distintivo visual en la UI.
> Ver [docs/diccionario-datos.md](docs/diccionario-datos.md).

## Estructura del proyecto

```
observatorio-deforestacion/
├── SPEC.md                      ← contrato técnico (fuente de verdad)
├── README.md                    ← este documento
├── docs/
│   ├── arquitectura.md          ← componentes, flujo de datos y decisiones
│   ├── despliegue.md            ← producción, variables de entorno, nginx, Docker
│   └── diccionario-datos.md     ← diccionario de datos y metodología
├── etl/
│   ├── run_etl.py               ← ETL: datos crudos → data/processed
│   ├── load_postgis.py          ← carga data/processed → PostgreSQL/PostGIS
│   └── sql/schema.sql           ← esquema PostGIS (idempotente)
├── data/processed/              ← salidas del ETL (NO editar a mano)
│   ├── municipios.geojson       ← 19 límites municipales (WGS84)
│   ├── subregiones.geojson      ← 5 subregiones CORPOURABA
│   ├── serie_municipal.csv      ← 1.123 filas municipio × periodo × clase
│   ├── serie_regional.csv       ← agregado regional por periodo × clase
│   ├── metadata.json            ← fuentes, notas metodológicas, QA, log del ETL
│   ├── hotspots/<periodo>.geojson  ← polígonos de deforestación (12 periodos)
│   └── capas/*.geojson          ← áreas protegidas, resguardos, consejos, cuencas
├── backend/                     ← API REST (FastAPI, Python 3.10)
│   ├── app/                     ← main, config, repositorios, analytics, routers
│   ├── tests/test_api.py        ← pruebas con pytest + httpx
│   ├── requirements.txt         ← modo archivos (por defecto)
│   └── requirements-postgis.txt ← extras del modo PostGIS
└── frontend/                    ← Next.js 14 (App Router) + TypeScript + Tailwind
    └── src/{app,components,lib,store}
```

## Inicio rápido

Requisitos: **Python 3.10+** y **Node.js 18+** (recomendado 20). Puertos por
defecto: API `8000`, frontend `3000`.

### 1. Backend (API)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

- Documentación interactiva: <http://localhost:8000/docs> (la raíz `/` redirige allí).
- Verificación: `GET http://localhost:8000/api/v1/salud` →
  `{"estado":"ok","version":"1.0.0","modo_datos":"archivos"}`.
- El API carga `data/processed/` **en memoria** al arrancar; no necesita base
  de datos. Para desarrollo añade `--reload`.

Pruebas del backend:

```bash
cd backend
pip install -r requirements.txt   # incluye pytest y httpx
pytest tests/ -v
```

### 2. Frontend (web)

```bash
cd frontend
npm install
npm run dev
```

- Abre <http://localhost:3000>.
- El frontend lee `NEXT_PUBLIC_API_URL` (por defecto `http://localhost:8000`).
  Si el API corre en otra dirección, crea `frontend/.env.local` (puedes partir
  de `.env.local.example`):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Todo junto

Con ambos procesos corriendo (API en `8000`, web en `3000`) la plataforma queda
operativa. El CORS del API permite `http://localhost:3000` por defecto y es
configurable con la variable `CORS_ORIGINS` (lista separada por comas, admite `*`).

## Regenerar los datos (ETL)

`data/processed/` ya viene generado. Solo hace falta re-ejecutar el ETL si
cambian los datos crudos del monitoreo (carpetas por periodo con shapefiles,
Excel y rásters).

```bash
# Dependencias del ETL (NO son las del API en runtime)
pip install geopandas pyogrio rasterio shapely numpy pandas openpyxl xlrd

# Ejecución (rutas por defecto: --raw = paquete crudo, --out = data/processed)
python etl/run_etl.py --raw "RUTA/A/DATOS/CRUDOS" --out data/processed
```

El ETL ejecuta 6 pasos (límites municipales, serie municipal, estimación de
vacíos, hotspots, capas de contexto y QA contra las hojas «Cálculos» de los
Excel originales) y escribe `metadata.json` con el log completo y los
resultados de QA. Detalle de fuentes, calibraciones y estimaciones en
[docs/diccionario-datos.md](docs/diccionario-datos.md).

## Modo PostGIS (opcional)

Por defecto el API sirve todo desde archivos. Si se define `DATABASE_URL`, el
API usa PostgreSQL + PostGIS con la **misma interfaz de repositorio** (y hace
*fallback* automático a archivos si la conexión falla).

```bash
# 1. Dependencias adicionales
pip install -r backend/requirements.txt -r backend/requirements-postgis.txt

# 2. Cargar los datos procesados a la base (idempotente: DROP/CREATE)
python etl/load_postgis.py --database-url postgresql+psycopg2://usuario:clave@localhost:5432/observatorio

# 3. Arrancar el API apuntando a la base
#    (PowerShell: $env:DATABASE_URL = "..."; Linux/macOS: export DATABASE_URL=...)
DATABASE_URL=postgresql+psycopg2://usuario:clave@localhost:5432/observatorio \
  uvicorn app.main:app --port 8000
```

Con la base activa, `GET /api/v1/salud` responde `"modo_datos":"postgis"`.
Más detalles en [docs/despliegue.md](docs/despliegue.md).

## Variables de entorno

| Variable | Componente | Default | Descripción |
|---|---|---|---|
| `DATA_DIR` | backend / ETL | `data/processed` (relativo a la raíz) | Carpeta de datos procesados |
| `DATABASE_URL` | backend | *(vacía)* | Conexión PostGIS; vacía = modo archivos |
| `CORS_ORIGINS` | backend | `http://localhost:3000` | Orígenes permitidos, separados por coma |
| `NEXT_PUBLIC_API_URL` | frontend | `http://localhost:8000` | URL base del API (se fija en build) |

## Documentación

- [docs/arquitectura.md](docs/arquitectura.md) — diagrama de componentes,
  flujo de datos crudos → ETL → API → UI y decisiones de diseño.
- [docs/despliegue.md](docs/despliegue.md) — despliegue en producción
  (uvicorn/gunicorn, build de Next, nginx, PostGIS, Docker de referencia).
- [docs/diccionario-datos.md](docs/diccionario-datos.md) — diccionario de
  datos completo y metodología de estimaciones y calibraciones.
- [SPEC.md](SPEC.md) — contrato técnico completo (API, tipos, diseño, módulos).

## Créditos y atribución

- **Datos**: procesados a partir del monitoreo de bosque de **CORPOURABA**
  (Corporación para el Desarrollo Sostenible del Urabá), 2000–2024.
- **Mapa base**: teselas de CARTO — atribución obligatoria
  `© OpenStreetMap · © CARTO`.
- Los periodos estimados no constituyen cifra oficial; úsense solo como
  referencia (ver notas metodológicas en `data/processed/metadata.json`).
