-- =============================================================================
-- Esquema PostGIS del Observatorio de Deforestación CORPOURABA (2000–2024)
-- Idempotente: DROP/CREATE de todas las tablas. Lo ejecuta etl/load_postgis.py
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- Orden de borrado: primero las tablas con claves foráneas
DROP TABLE IF EXISTS serie_municipal;
DROP TABLE IF EXISTS hotspots;
DROP TABLE IF EXISTS capas;
DROP TABLE IF EXISTS subregiones;
DROP TABLE IF EXISTS metadatos;
DROP TABLE IF EXISTS municipios;

-- Límites municipales (19 features, WGS84)
CREATE TABLE municipios (
    codigo_dane       varchar(5) PRIMARY KEY,
    municipio_key     text NOT NULL,
    nombre            text NOT NULL,
    subregion         text NOT NULL,
    area_municipio_ha double precision,
    centroide_lon     double precision,
    centroide_lat     double precision,
    geom              geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX municipios_geom_gix ON municipios USING GIST (geom);
CREATE INDEX municipios_subregion_ix ON municipios (subregion);

-- Subregiones de la jurisdicción (5)
CREATE TABLE subregiones (
    id        serial PRIMARY KEY,
    subregion text NOT NULL,
    geom      geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX subregiones_geom_gix ON subregiones USING GIST (geom);

-- Serie municipal por periodo y clase (1.123 filas)
CREATE TABLE serie_municipal (
    id                serial PRIMARY KEY,
    codigo_dane       varchar(5) NOT NULL REFERENCES municipios (codigo_dane),
    municipio         text NOT NULL,
    subregion         text NOT NULL,
    periodo           text NOT NULL,
    ano_inicio        integer NOT NULL,
    ano_fin           integer NOT NULL,
    clase             text NOT NULL,
    hectareas         double precision NOT NULL,
    hectareas_anuales double precision NOT NULL,
    fuente            text NOT NULL,
    estimado          boolean NOT NULL
);
CREATE INDEX serie_periodo_dane_ix ON serie_municipal (periodo, codigo_dane);
CREATE INDEX serie_clase_ix ON serie_municipal (clase);
CREATE INDEX serie_dane_clase_ix ON serie_municipal (codigo_dane, clase);

-- Polígonos de deforestación ≥ 1 ha por periodo (12 periodos)
CREATE TABLE hotspots (
    id        serial PRIMARY KEY,
    periodo   text NOT NULL,
    municipio text,               -- puede ser NULL (fuera de límite municipal)
    ha        double precision,
    geom      geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX hotspots_periodo_ix ON hotspots (periodo);
CREATE INDEX hotspots_geom_gix ON hotspots USING GIST (geom);

-- Capas de contexto: áreas protegidas, resguardos, consejos y cuencas
CREATE TABLE capas (
    id          serial PRIMARY KEY,
    capa        text NOT NULL,    -- id de la capa (p. ej. 'areas_protegidas')
    nombre      text,
    propiedades jsonb NOT NULL,   -- properties originales del GeoJSON
    geom        geometry(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX capas_capa_ix ON capas (capa);
CREATE INDEX capas_geom_gix ON capas USING GIST (geom);

-- metadata.json completo (fila única)
CREATE TABLE metadatos (
    id  integer PRIMARY KEY CHECK (id = 1),
    doc jsonb NOT NULL
);
