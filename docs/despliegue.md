# Despliegue en producción — Observatorio de Deforestación CORPOURABA

Guía para poner la plataforma en producción: backend FastAPI, frontend
Next.js, proxy inverso nginx, modo PostGIS opcional y Dockerfiles de
referencia. Para el desarrollo local ver el [README](../README.md).

## 1. Topología recomendada

```
Internet ──► nginx (:80/:443, TLS)
              ├── /api/… , /docs , /openapi.json ──► uvicorn/gunicorn (:8000)  [FastAPI]
              └── resto ─────────────────────────► next start (:3000)          [Next.js]
                                                        │
                                    (opcional) PostgreSQL + PostGIS (:5432)
```

Un solo servidor Linux modesto basta: el API sirve datos precargados en
memoria (< 100 MB de RSS) y el frontend es una aplicación Next estándar.

## 2. Variables de entorno

| Variable | Componente | Default | Producción típica |
|---|---|---|---|
| `DATA_DIR` | backend | `<raíz>/data/processed` | `/srv/observatorio/data/processed` |
| `DATABASE_URL` | backend | *(vacía → modo archivos)* | `postgresql+psycopg2://obs:***@localhost:5432/observatorio` |
| `CORS_ORIGINS` | backend | `http://localhost:3000` | `https://observatorio.corpouraba.gov.co` (separar varios con coma; `*` desactiva credenciales) |
| `NEXT_PUBLIC_API_URL` | frontend | `http://localhost:8000` | `https://observatorio.corpouraba.gov.co` (mismo origen, vía nginx) |

> ⚠️ `NEXT_PUBLIC_API_URL` se **incrusta en tiempo de build** de Next.js.
> Si cambia, hay que reconstruir el frontend (`npm run build`).
>
> 💡 Si nginx sirve API y web bajo el **mismo dominio** (recomendado),
> `NEXT_PUBLIC_API_URL` puede ser ese dominio y `CORS_ORIGINS` deja de ser
> crítico (las peticiones son del mismo origen).

## 3. Backend en producción

### 3.1 Instalación

```bash
cd /srv/observatorio            # raíz del proyecto desplegado
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
# solo si se usará PostGIS:
pip install -r backend/requirements-postgis.txt
```

### 3.2 uvicorn (sencillo) o gunicorn (recomendado en Linux)

```bash
# Opción A — uvicorn con varios workers
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2

# Opción B — gunicorn como gestor de procesos (solo Linux)
cd backend
gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 2 \
  --bind 127.0.0.1:8000 \
  --timeout 60 \
  --access-logfile - --error-logfile -
```

Notas:

- Cada worker carga su propia copia de los datos en memoria; con el tamaño
  del dataset, 2 workers son más que suficientes.
- Enlazar a `127.0.0.1`: nginx es la única cara pública.
- En Windows Server, usar la opción A (gunicorn no soporta Windows) o Docker.

### 3.3 Servicio systemd (Linux)

```ini
# /etc/systemd/system/observatorio-api.service
[Unit]
Description=API Observatorio Deforestación CORPOURABA
After=network.target

[Service]
User=observatorio
WorkingDirectory=/srv/observatorio/backend
Environment=DATA_DIR=/srv/observatorio/data/processed
Environment=CORS_ORIGINS=https://observatorio.corpouraba.gov.co
# Environment=DATABASE_URL=postgresql+psycopg2://obs:***@localhost:5432/observatorio
ExecStart=/srv/observatorio/.venv/bin/gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 127.0.0.1:8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now observatorio-api
curl -s http://127.0.0.1:8000/api/v1/salud   # → {"estado":"ok",...}
```

## 4. Frontend en producción

```bash
cd frontend
npm ci                                   # instala exactamente el lockfile
NEXT_PUBLIC_API_URL=https://observatorio.corpouraba.gov.co npm run build
npm run start                            # next start -p 3000
```

Servicio systemd equivalente:

```ini
# /etc/systemd/system/observatorio-web.service
[Unit]
Description=Frontend Observatorio Deforestación CORPOURABA
After=network.target

[Service]
User=observatorio
WorkingDirectory=/srv/observatorio/frontend
Environment=NODE_ENV=production
ExecStart=/usr/bin/npm run start
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## 5. nginx como proxy inverso

```nginx
# /etc/nginx/sites-available/observatorio.conf
server {
    listen 80;
    server_name observatorio.corpouraba.gov.co;
    # Producción real: añadir listen 443 ssl + certificados (p. ej. certbot)

    # Compresión: los GeoJSON y CSV comprimen ~80 %
    gzip on;
    gzip_types application/json application/geo+json text/csv text/plain;
    gzip_min_length 1024;

    # ---- API FastAPI -------------------------------------------------------
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        # el paquete.zip puede tardar unos segundos en generarse
        proxy_buffering off;
    }

    # Documentación interactiva del API (opcional exponerla)
    location = /docs        { proxy_pass http://127.0.0.1:8000; }
    location = /openapi.json { proxy_pass http://127.0.0.1:8000; }

    # ---- Frontend Next.js --------------------------------------------------
    location /_next/static/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_cache_valid 200 7d;       # assets con hash: cachear agresivamente
        add_header Cache-Control "public, max-age=604800, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/observatorio.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Con este esquema, API y web comparten origen: el navegador llama a
`https://observatorio.corpouraba.gov.co/api/v1/...` y no hay CORS de por medio.

## 6. Modo PostGIS (opcional)

El API funciona al 100 % sin base de datos. PostGIS aporta consultas
espaciales ad hoc e integración con otras herramientas SIG de la Corporación.

```bash
# 1. Crear base y usuario (una vez)
sudo -u postgres psql -c "CREATE USER obs WITH PASSWORD '***';"
sudo -u postgres psql -c "CREATE DATABASE observatorio OWNER obs;"
# La extensión postgis la crea el propio schema.sql (CREATE EXTENSION IF NOT EXISTS postgis),
# para lo cual el usuario necesita permisos suficientes (o crearla antes como superusuario):
sudo -u postgres psql -d observatorio -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# 2. Cargar los datos procesados (idempotente: DROP/CREATE + inserciones)
source /srv/observatorio/.venv/bin/activate
python etl/load_postgis.py \
  --database-url postgresql+psycopg2://obs:***@localhost:5432/observatorio

# 3. Activar en el servicio del API (descomentar DATABASE_URL en systemd) y reiniciar
sudo systemctl restart observatorio-api
curl -s http://127.0.0.1:8000/api/v1/salud    # → "modo_datos":"postgis"
```

Si la base se cae o la URL es inválida, el API registra un *warning* y sigue
funcionando en modo archivos: la plataforma nunca queda fuera de servicio por
la base de datos. Tras cada re-ejecución del ETL, repetir el paso 2.

## 7. Actualización de datos (nuevo periodo de monitoreo)

1. Colocar los archivos crudos del nuevo periodo en el paquete de origen.
2. Registrar el periodo/fuente en `etl/run_etl.py` (constantes `PERIODOS` y
   `SHP_MPIOS`/`EXCEL_MPIOS`/…) y ejecutar
   `python etl/run_etl.py --raw <crudos> --out data/processed`.
3. Revisar el QA en `data/processed/metadata.json` (`qa_calculos`, `log`).
4. Sincronizar `data/processed/` al servidor y reiniciar el API
   (`systemctl restart observatorio-api`); recarga todo al arrancar.
5. Si el modo PostGIS está activo: `python etl/load_postgis.py ...` de nuevo.

## 8. Docker (opcional, de referencia)

Los siguientes Dockerfiles son **de referencia** y se documentan aquí (no
existen como archivos en el repositorio). Crear `docker/Dockerfile.api`,
`docker/Dockerfile.web` y `docker-compose.yml` con este contenido si se opta
por contenedores. El contexto de build es la **raíz del proyecto**.

### 8.1 `docker/Dockerfile.api`

```dockerfile
# API FastAPI — modo archivos (los datos van dentro de la imagen)
FROM python:3.10-slim

WORKDIR /app

# Dependencias primero para aprovechar la caché de capas
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Código del API y datos procesados
COPY backend/app ./app
COPY data/processed /data/processed

ENV DATA_DIR=/data/processed \
    CORS_ORIGINS=http://localhost:3000

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

> Para el modo PostGIS en Docker, añadir
> `COPY backend/requirements-postgis.txt ./` +
> `RUN pip install --no-cache-dir -r requirements-postgis.txt`
> y pasar `DATABASE_URL` como variable de entorno del contenedor.

### 8.2 `docker/Dockerfile.web`

```dockerfile
# Frontend Next.js — build multi-etapa
FROM node:20-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./
# NEXT_PUBLIC_API_URL se incrusta en el build: pasarla como build-arg
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/next.config.mjs ./next.config.mjs
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next

EXPOSE 3000
CMD ["npm", "run", "start"]
```

### 8.3 `docker-compose.yml`

```yaml
services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    environment:
      CORS_ORIGINS: "http://localhost:3000"
      # DATABASE_URL: "postgresql+psycopg2://obs:***@db:5432/observatorio"
    ports:
      - "8000:8000"

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile.web
      args:
        # URL del API tal como la ve el NAVEGADOR (no la red interna de compose)
        NEXT_PUBLIC_API_URL: "http://localhost:8000"
    ports:
      - "3000:3000"
    depends_on:
      - api

  # Opcional: base PostGIS para el modo con base de datos
  # db:
  #   image: postgis/postgis:16-3.4
  #   environment:
  #     POSTGRES_DB: observatorio
  #     POSTGRES_USER: obs
  #     POSTGRES_PASSWORD: "***"
  #   volumes:
  #     - pgdata:/var/lib/postgresql/data
  #   ports:
  #     - "5432:5432"

# volumes:
#   pgdata:
```

> ⚠️ `NEXT_PUBLIC_API_URL` debe ser la URL **pública** del API (la que usa el
> navegador del usuario), no el nombre del servicio de compose (`http://api:8000`
> solo resuelve dentro de la red de contenedores).

## 9. Lista de verificación post-despliegue

- [ ] `GET /api/v1/salud` responde `{"estado":"ok","version":"1.0.0",...}` con
      el `modo_datos` esperado (`archivos` o `postgis`).
- [ ] `GET /api/v1/periodos` devuelve 18 periodos; `GET /api/v1/municipios`,
      19 features.
- [ ] `GET /api/v1/kpis` → `total_deforestado_ha` ≈ 46.041 ha.
- [ ] La landing carga y los KPIs animados muestran cifras reales.
- [ ] `/mapa` pinta el choropleth y el timelapse recorre los 18 periodos;
      las teselas CARTO cargan con la atribución `© OpenStreetMap · © CARTO`.
- [ ] `/datos` descarga `serie.csv` (abre con tildes correctas en Excel — BOM),
      `serie.xlsx` y `paquete.zip`.
- [ ] Los periodos estimados aparecen con su distintivo visual en mapa y dashboard.
- [ ] HTTPS activo y compresión gzip verificada sobre `/api/v1/municipios`.
