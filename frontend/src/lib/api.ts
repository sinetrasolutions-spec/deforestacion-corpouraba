/**
 * Cliente HTTP tipado del API del Observatorio (contrato SPEC §5 y §6.2).
 * Todas las rutas cuelgan de `/api/v1`. Las firmas exportadas son EXACTAS
 * según el SPEC; los demás módulos dependen de ellas.
 */
import type * as GeoJSON from 'geojson';
import type {
  Choropleth,
  FilaSerie,
  ItemRanking,
  Kpis,
  Periodo,
  Prediccion,
} from './types';

/**
 * URL base del API (sin barra final). Por defecto vacío = mismo origen: las
 * rutas /api/v1/* las sirve el propio Next.js (route handlers) en Vercel.
 * Se puede apuntar a un backend externo con NEXT_PUBLIC_API_URL.
 */
export const API_URL: string = process.env.NEXT_PUBLIC_API_URL ?? '';

const BASE = `${API_URL}/api/v1`;

/** Error tipado del API con el código HTTP y el `detail` de FastAPI. */
export class ErrorApi extends Error {
  constructor(
    public readonly estado: number,
    mensaje: string,
  ) {
    super(mensaje);
    this.name = 'ErrorApi';
  }
}

/** GET genérico con manejo de errores FastAPI ({"detail": "..."}). */
async function pedir<T>(ruta: string, params?: URLSearchParams): Promise<T> {
  const qs = params?.toString();
  const url = qs ? `${BASE}${ruta}?${qs}` : `${BASE}${ruta}`;
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!res.ok) {
    let detalle = `Error ${res.status} en ${ruta}`;
    try {
      const cuerpo = (await res.json()) as { detail?: unknown };
      if (typeof cuerpo.detail === 'string') detalle = cuerpo.detail;
    } catch {
      // sin cuerpo JSON: conservamos el mensaje por defecto
    }
    throw new ErrorApi(res.status, detalle);
  }
  return (await res.json()) as T;
}

/** Lista de los 18 periodos con su fuente y disponibilidad de hotspots. */
export async function getPeriodos(): Promise<Periodo[]> {
  return pedir<Periodo[]>('/periodos');
}

/** Límites municipales (19 features, WGS84) con propiedades del §4.2. */
export async function getMunicipios(): Promise<GeoJSON.FeatureCollection> {
  return pedir<GeoJSON.FeatureCollection>('/municipios');
}

/** Límites de las 5 subregiones (FeatureCollection). */
export async function getSubregiones(): Promise<GeoJSON.FeatureCollection> {
  return pedir<GeoJSON.FeatureCollection>('/subregiones');
}

/** Valores de choropleth por municipio para un periodo, con breaks p20..p100. */
export async function getChoropleth(
  periodo: string,
  metrica?: 'hectareas' | 'hectareas_anuales',
): Promise<Choropleth> {
  const q = new URLSearchParams({ periodo });
  if (metrica) q.set('metrica', metrica);
  return pedir<Choropleth>('/choropleth', q);
}

/** Serie municipal filtrada. `municipio` acepta códigos DANE o nombres (repetible). */
export async function getSerie(params?: {
  municipio?: string[];
  subregion?: string;
  clase?: string;
  desde?: number;
  hasta?: number;
  incluirEstimados?: boolean;
}): Promise<{ data: FilaSerie[]; total_ha: number; nota: string | null }> {
  const q = new URLSearchParams();
  params?.municipio?.forEach((m) => q.append('municipio', m));
  if (params?.subregion) q.set('subregion', params.subregion);
  if (params?.clase) q.set('clase', params.clase);
  if (params?.desde !== undefined) q.set('desde', String(params.desde));
  if (params?.hasta !== undefined) q.set('hasta', String(params.hasta));
  if (params?.incluirEstimados !== undefined) {
    q.set('incluir_estimados', String(params.incluirEstimados));
  }
  return pedir('/serie', q);
}

/** Serie agregada regional (jurisdicción completa) por periodo. */
export async function getSerieRegional(
  clase?: string,
  incluirEstimados?: boolean,
): Promise<{
  data: {
    periodo: string;
    ano_inicio: number;
    ano_fin: number;
    hectareas: number;
    hectareas_anuales: number;
    estimado: boolean;
  }[];
}> {
  const q = new URLSearchParams();
  if (clase) q.set('clase', clase);
  if (incluirEstimados !== undefined) q.set('incluir_estimados', String(incluirEstimados));
  return pedir('/serie/regional', q);
}

/** Ranking de municipios (top-n) por periodo o acumulado si no se indica. */
export async function getRanking(
  periodo?: string,
  n?: number,
  metrica?: string,
): Promise<{ data: ItemRanking[] }> {
  const q = new URLSearchParams();
  if (periodo) q.set('periodo', periodo);
  if (n !== undefined) q.set('n', String(n));
  if (metrica) q.set('metrica', metrica);
  return pedir('/ranking', q);
}

/** KPIs regionales (total, promedio anual, periodo crítico, etc.). */
export async function getKpis(incluirEstimados?: boolean): Promise<Kpis> {
  const q = new URLSearchParams();
  if (incluirEstimados !== undefined) q.set('incluir_estimados', String(incluirEstimados));
  return pedir<Kpis>('/kpis', q);
}

/** Comparación de series (ha/año) entre 2 y 6 municipios por código DANE. */
export async function getComparacion(codigos: string[]): Promise<{
  data: {
    municipio: string;
    codigo_dane: string;
    serie: { periodo: string; hectareas_anuales: number; estimado: boolean }[];
  }[];
}> {
  const q = new URLSearchParams({ municipios: codigos.join(',') });
  return pedir('/comparacion', q);
}

/**
 * Polígonos de hotspots de un periodo. Solo 12 periodos los tienen (§4.3):
 * devuelve `null` cuando el API responde 404 para degradar con elegancia.
 */
export async function getHotspots(periodo: string): Promise<GeoJSON.FeatureCollection | null> {
  const res = await fetch(`${BASE}/hotspots/${encodeURIComponent(periodo)}`, {
    headers: { Accept: 'application/json' },
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new ErrorApi(res.status, `Error ${res.status} al pedir hotspots de ${periodo}`);
  return (await res.json()) as GeoJSON.FeatureCollection;
}

/** Metadatos del explorador de parches (conteos y agregados por periodo). */
export interface ParchesMeta {
  n_parches: number;
  ha_total: number;
  periodos: string[];
  min_ha: number;
  por_periodo: { periodo: string; ano_inicio: number; n: number; ha: number }[];
}

/**
 * Parches de deforestación (hotspots ≥1 ha) de uno o TODOS los periodos.
 * Cada feature trae periodo, ano_inicio, municipio y ha en sus properties.
 */
export async function getParches(params?: {
  periodo?: string;
  minHa?: number;
  municipio?: string;
}): Promise<GeoJSON.FeatureCollection & { metadata: ParchesMeta }> {
  const q = new URLSearchParams();
  if (params?.periodo) q.set('periodo', params.periodo);
  if (params?.minHa) q.set('min_ha', String(params.minHa));
  if (params?.municipio) q.set('municipio', params.municipio);
  return pedir('/parches', q);
}

/** Resumen ligero (sin geometría) de polígonos por periodo, para la línea de tiempo. */
export interface ResumenPeriodo { periodo: string; ano_inicio: number; n: number; ha: number }
export async function getParchesResumen(
  municipio?: string,
): Promise<{ por_periodo: ResumenPeriodo[] }> {
  const q = new URLSearchParams();
  if (municipio) q.set('municipio', municipio);
  return pedir('/parches/resumen', q);
}

/** Catálogo de capas de contexto disponibles (id, nombre, unidades). */
export async function getCapas(): Promise<{
  capas: { id: string; nombre: string; unidades: number }[];
}> {
  return pedir('/capas');
}

/** Unidad territorial con su deforestación (área protegida, POMCA, resguardo…). */
export interface UnidadTerritorio {
  nombre: string;
  detalle: string | null;
  deforestacion_ha: number;
  n_periodos: number | null;
  area_ha: number | null;
  pct_del_territorio: number | null;
}

/** Tipos de territorio disponibles para el ranking de deforestación por unidad. */
export async function getTerritoriosCatalogo(): Promise<{
  tipos: { id: string; titulo: string; disponible: boolean }[];
}> {
  return pedir('/analisis/territorios');
}

/** Ranking de deforestación por unidad para un tipo (areas_protegidas, pomcas…). */
export async function getTerritorios(
  tipo: string,
  periodo?: string,
): Promise<{
  tipo: string;
  titulo: string;
  periodo: string | null;
  periodos_disponibles: string[];
  n_unidades: number;
  deforestacion_total_ha: number;
  nota: string;
  unidades: UnidadTerritorio[];
}> {
  const q = new URLSearchParams();
  if (periodo) q.set('periodo', periodo);
  return pedir(`/analisis/territorios/${encodeURIComponent(tipo)}`, q);
}

/** Una capa de contexto por id: areas_protegidas | resguardos | consejos | cuencas. */
export async function getCapa(id: string): Promise<GeoJSON.FeatureCollection> {
  return pedir<GeoJSON.FeatureCollection>(`/capas/${encodeURIComponent(id)}`);
}

/** Predicción por regresión lineal (regional si no se pasa municipio). */
export async function getPrediccion(municipio?: string, horizonte?: number): Promise<Prediccion> {
  const q = new URLSearchParams();
  if (municipio) q.set('municipio', municipio);
  if (horizonte !== undefined) q.set('horizonte', String(horizonte));
  return pedir<Prediccion>('/prediccion', q);
}

/** Metadatos completos del ETL (periodos, fuentes, notas metodológicas, QA). */
export async function getMetadata(): Promise<Record<string, unknown>> {
  return pedir<Record<string, unknown>>('/metadata');
}

/**
 * Construye la URL de un recurso de descarga, p. ej.:
 * `urlDescarga('serie.csv', { subregion: 'Caribe' })`
 * → `http://localhost:8000/api/v1/descargas/serie.csv?subregion=Caribe`
 */
export function urlDescarga(ruta: string, params?: Record<string, string>): string {
  const limpia = ruta.replace(/^\/+/, '');
  const qs = params ? new URLSearchParams(params).toString() : '';
  return `${BASE}/descargas/${limpia}${qs ? `?${qs}` : ''}`;
}
