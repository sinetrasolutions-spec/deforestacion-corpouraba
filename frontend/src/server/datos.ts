/**
 * Acceso a datos del lado servidor (route handlers de Next.js).
 * Réplica en TypeScript del repositorio FastAPI: carga en memoria los CSV,
 * GeoJSON y metadata de ./data/processed y expone helpers de filtrado y
 * validación. Se cachea entre invocaciones (módulo compartido).
 */
import fs from 'node:fs';
import path from 'node:path';

export const VERSION = '1.0.0';
export const CLASE_DEFORESTACION = 'Deforestación';

export const CLASES_VALIDAS = [
  'Bosque Estable', 'Deforestación', 'No Bosque Estable', 'Regeneración', 'Sin Información',
];
export const SUBREGIONES_VALIDAS = ['Caribe', 'Centro', 'Atrato', 'Nutibara', 'Urrao'];

export const NOMBRES_CAPAS: Record<string, string> = {
  areas_protegidas: 'Áreas protegidas',
  resguardos: 'Resguardos indígenas',
  consejos: 'Consejos comunitarios',
  cuencas: 'Cuencas',
  pomcas: 'POMCAS',
  areas_protegidas_oficial: 'Áreas protegidas',
  resguardos_oficial: 'Resguardos indígenas',
  comunidades_negras_oficial: 'Consejos comunitarios',
  titulos_mineros: 'Títulos mineros',
  ley_segunda: 'Reserva forestal Ley 2ª',
  ecosistemas_estrategicos: 'Ecosistemas estratégicos',
  zonificacion_conflicto: 'Zonas de conflicto de uso',
  pdet: 'Municipios PDET',
};

/** Error con código HTTP sugerido (equivalente a ErrorDatos). */
export class ErrorDatos extends Error {
  constructor(mensaje: string, public codigo = 422) {
    super(mensaje);
  }
}

export const DATA_DIR = path.join(process.cwd(), 'data', 'processed');

// ── utilidades ───────────────────────────────────────────────────────────
export function normalizar(texto: unknown): string {
  return String(texto ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase()
    .split(/\s+/)
    .filter(Boolean)
    .join(' ');
}

/** Parser CSV mínimo con soporte de campos entre comillas. */
export function parseCsv(texto: string): Record<string, string>[] {
  const filas: string[][] = [];
  let campo = '';
  let fila: string[] = [];
  let enComillas = false;
  for (let i = 0; i < texto.length; i += 1) {
    const c = texto[i];
    if (enComillas) {
      if (c === '"') {
        if (texto[i + 1] === '"') { campo += '"'; i += 1; } else { enComillas = false; }
      } else { campo += c; }
    } else if (c === '"') { enComillas = true; }
    else if (c === ',') { fila.push(campo); campo = ''; }
    else if (c === '\n') { fila.push(campo); filas.push(fila); fila = []; campo = ''; }
    else if (c === '\r') { /* ignorar */ }
    else { campo += c; }
  }
  if (campo !== '' || fila.length) { fila.push(campo); filas.push(fila); }
  if (!filas.length) return [];
  const cab = filas[0].map((h) => h.replace(/^﻿/, '').trim());
  return filas.slice(1)
    .filter((f) => f.some((v) => v !== ''))
    .map((f) => Object.fromEntries(cab.map((h, i) => [h, f[i] ?? ''])));
}

const num = (v: unknown): number => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};
const esBool = (v: unknown): boolean => String(v).trim().toLowerCase() === 'true';
export const redondear = (v: number, d = 2): number => {
  const f = 10 ** d;
  return Math.round((v + Number.EPSILON) * f) / f;
};

// ── tipos ─────────────────────────────────────────────────────────────────
export interface FilaSerie {
  codigo_dane: string; municipio: string; subregion: string; periodo: string;
  ano_inicio: number; ano_fin: number; clase: string;
  hectareas: number; hectareas_anuales: number; fuente: string; estimado: boolean;
}
export interface FeatureCollection { type: string; features: unknown[]; [k: string]: unknown }

// ── carga y caché ───────────────────────────────────────────────────────────
interface Cache {
  serie: FilaSerie[];
  metadata: Record<string, unknown>;
  municipiosFc: FeatureCollection;
  subregionesFc: FeatureCollection;
  capas: Record<string, FeatureCollection>;
  hotspotsDisponibles: string[];
  hotspots: Record<string, FeatureCollection>;
  indiceMunicipios: Record<string, string>;
  nombrePorCodigo: Record<string, string>;
}
let _cache: Cache | null = null;

function leerJson<T = unknown>(rel: string): T {
  return JSON.parse(fs.readFileSync(path.join(DATA_DIR, rel), 'utf-8')) as T;
}

function cargar(): Cache {
  if (_cache) return _cache;

  const serie = parseCsv(fs.readFileSync(path.join(DATA_DIR, 'serie_municipal.csv'), 'utf-8'))
    .map((r): FilaSerie => ({
      codigo_dane: String(r.codigo_dane),
      municipio: r.municipio, subregion: r.subregion, periodo: r.periodo,
      ano_inicio: num(r.ano_inicio), ano_fin: num(r.ano_fin), clase: r.clase,
      hectareas: num(r.hectareas), hectareas_anuales: num(r.hectareas_anuales),
      fuente: r.fuente, estimado: esBool(r.estimado),
    }));

  const municipiosFc = leerJson<FeatureCollection>('municipios.geojson');
  const subregionesFc = leerJson<FeatureCollection>('subregiones.geojson');
  const metadata = leerJson<Record<string, unknown>>('metadata.json');

  // capas de contexto
  const capas: Record<string, FeatureCollection> = {};
  const dirCapas = path.join(DATA_DIR, 'capas');
  if (fs.existsSync(dirCapas)) {
    for (const f of fs.readdirSync(dirCapas).filter((n) => n.endsWith('.geojson')).sort()) {
      capas[f.replace(/\.geojson$/, '')] = leerJson<FeatureCollection>(path.join('capas', f));
    }
  }

  // hotspots disponibles (carga perezosa del contenido)
  const dirHot = path.join(DATA_DIR, 'hotspots');
  const hotspotsDisponibles = fs.existsSync(dirHot)
    ? fs.readdirSync(dirHot).filter((n) => n.endsWith('.geojson')).map((n) => n.replace(/\.geojson$/, '')).sort()
    : [];

  // índices de municipios
  const indiceMunicipios: Record<string, string> = {};
  const nombrePorCodigo: Record<string, string> = {};
  for (const feat of municipiosFc.features as { properties?: Record<string, unknown> }[]) {
    const p = feat.properties ?? {};
    const codigo = String(p.codigo_dane ?? '');
    if (!codigo) continue;
    const nombre = String(p.nombre ?? '');
    nombrePorCodigo[codigo] = nombre;
    indiceMunicipios[codigo] = codigo;
    indiceMunicipios[normalizar(nombre)] = codigo;
    if (p.municipio_key) indiceMunicipios[normalizar(p.municipio_key)] = codigo;
  }

  _cache = {
    serie, metadata, municipiosFc, subregionesFc, capas,
    hotspotsDisponibles, hotspots: {}, indiceMunicipios, nombrePorCodigo,
  };
  return _cache;
}

// ── API del módulo ──────────────────────────────────────────────────────────
export const datos = {
  serie: () => cargar().serie,
  metadata: () => cargar().metadata,
  municipiosFc: () => cargar().municipiosFc,
  subregionesFc: () => cargar().subregionesFc,
  capas: () => cargar().capas,
  hotspotsDisponibles: () => cargar().hotspotsDisponibles,
  nombreMunicipio: (codigo: string) => cargar().nombrePorCodigo[codigo] ?? codigo,

  hotspots(periodo: string): FeatureCollection | null {
    const c = cargar();
    if (!c.hotspotsDisponibles.includes(periodo)) return null;
    if (!c.hotspots[periodo]) {
      c.hotspots[periodo] = leerJson<FeatureCollection>(path.join('hotspots', `${periodo}.geojson`));
    }
    return c.hotspots[periodo];
  },

  idsPeriodos(): string[] {
    const ps = (cargar().metadata.periodos as { id: string }[]) ?? [];
    return ps.map((p) => p.id);
  },

  resolverMunicipio(valor: string): string {
    const c = cargar();
    const codigo = c.indiceMunicipios[String(valor).trim()] ?? c.indiceMunicipios[normalizar(valor)];
    if (!codigo) throw new ErrorDatos(`Municipio desconocido: '${valor}'.`, 404);
    return codigo;
  },

  validarClase(clase: string): string {
    const canon = CLASES_VALIDAS.find((c) => normalizar(c) === normalizar(clase));
    if (!canon) throw new ErrorDatos(`Clase desconocida: '${clase}'.`, 422);
    return canon;
  },
  validarSubregion(sub: string): string {
    const canon = SUBREGIONES_VALIDAS.find((s) => normalizar(s) === normalizar(sub));
    if (!canon) throw new ErrorDatos(`Territorial desconocida: '${sub}'.`, 422);
    return canon;
  },
  validarPeriodo(periodo: string): string {
    if (!this.idsPeriodos().includes(periodo)) {
      throw new ErrorDatos(`Periodo desconocido: '${periodo}'.`, 404);
    }
    return periodo;
  },
};

/** Filtra la serie municipal según los parámetros de /serie. */
export function filtrarSerie(opts: {
  municipios?: string[]; subregion?: string | null; clase?: string;
  desde?: number | null; hasta?: number | null; incluirEstimados?: boolean;
}): FilaSerie[] {
  const claseOk = datos.validarClase(opts.clase ?? CLASE_DEFORESTACION);
  let df = datos.serie().filter((f) => f.clase === claseOk);
  if (opts.municipios?.length) {
    const codigos = new Set(opts.municipios.map((m) => datos.resolverMunicipio(m)));
    df = df.filter((f) => codigos.has(f.codigo_dane));
  }
  if (opts.subregion) {
    const sub = datos.validarSubregion(opts.subregion);
    df = df.filter((f) => f.subregion === sub);
  }
  if (opts.desde != null) df = df.filter((f) => f.ano_inicio >= opts.desde!);
  if (opts.hasta != null) df = df.filter((f) => f.ano_fin <= opts.hasta!);
  if (opts.incluirEstimados === false) df = df.filter((f) => !f.estimado);
  return df.sort((a, b) => a.ano_inicio - b.ano_inicio || a.codigo_dane.localeCompare(b.codigo_dane));
}

/** Serie municipal de un municipio (por defecto Deforestación), ordenada. */
export function serieMunicipio(codigo: string, clase = CLASE_DEFORESTACION): FilaSerie[] {
  const claseOk = datos.validarClase(clase);
  return datos.serie()
    .filter((f) => f.codigo_dane === codigo && f.clase === claseOk)
    .sort((a, b) => a.ano_inicio - b.ano_inicio);
}

/** Serie regional (suma por periodo/clase) filtrada por clase. */
export function serieRegional(clase = CLASE_DEFORESTACION, incluirEstimados = true) {
  const claseOk = datos.validarClase(clase);
  const map = new Map<string, { periodo: string; ano_inicio: number; ano_fin: number; hectareas: number; hectareas_anuales: number; estimado: boolean }>();
  for (const f of datos.serie()) {
    if (f.clase !== claseOk) continue;
    if (!incluirEstimados && f.estimado) continue;
    const e = map.get(f.periodo) ?? { periodo: f.periodo, ano_inicio: f.ano_inicio, ano_fin: f.ano_fin, hectareas: 0, hectareas_anuales: 0, estimado: false };
    e.hectareas += f.hectareas;
    e.hectareas_anuales += f.hectareas_anuales;
    e.estimado = e.estimado || f.estimado;
    map.set(f.periodo, e);
  }
  return [...map.values()].sort((a, b) => a.ano_inicio - b.ano_inicio);
}

/** Periodos con bandera tiene_hotspots (GET /periodos). */
export function periodos() {
  const disp = new Set(datos.hotspotsDisponibles());
  const ps = (datos.metadata().periodos as Record<string, unknown>[]) ?? [];
  return ps.map((p) => ({ ...p, tiene_hotspots: disp.has(String(p.id)) }));
}

/** Respuesta JSON estándar. */
export function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status, headers: { 'content-type': 'application/json; charset=utf-8' },
  });
}
/** Error JSON (traduce ErrorDatos a su código). */
export function errorJson(e: unknown): Response {
  if (e instanceof ErrorDatos) return json({ detail: e.message }, e.codigo);
  console.error(e);
  return json({ detail: 'Error interno del servidor.' }, 500);
}
