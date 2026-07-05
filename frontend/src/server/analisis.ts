/**
 * Lógica de la investigación temática (réplica de routers/analisis.py):
 * catálogo, hallazgos, tablas, resúmenes, capas geo, parches y territorios.
 */
import fs from 'node:fs';
import path from 'node:path';
import { DATA_DIR, datos, ErrorDatos, normalizar, parseCsv, type FeatureCollection } from './datos';

const DIR_ANALISIS = path.join(DATA_DIR, 'analisis');
const ID_SEGURO = /^[a-z0-9_]+(\/[a-z0-9_]+)?$/;

function existeDirAnalisis(): string {
  if (!fs.existsSync(DIR_ANALISIS)) throw new ErrorDatos('No hay resultados de análisis generados todavía.', 404);
  return DIR_ANALISIS;
}

function resolver(dataset: string, ext: string): string {
  if (!ID_SEGURO.test(dataset)) throw new ErrorDatos(`Identificador de dataset inválido: '${dataset}'.`, 422);
  const ruta = path.join(existeDirAnalisis(), dataset + ext);
  if (!fs.existsSync(ruta)) throw new ErrorDatos(`No existe el dataset '${dataset}${ext}'.`, 404);
  return ruta;
}

export function catalogoAnalisis() {
  const carpeta = existeDirAnalisis();
  const tablas: { id: string; archivo: string }[] = [];
  const resumenes: { id: string; archivo: string }[] = [];
  const capas: { id: string; archivo: string }[] = [];
  const walk = (dir: string, base = ''): void => {
    for (const nombre of fs.readdirSync(dir).sort()) {
      const abs = path.join(dir, nombre);
      const rel = base ? `${base}/${nombre}` : nombre;
      if (fs.statSync(abs).isDirectory()) { walk(abs, rel); continue; }
      const id = rel.replace(/\.[^.]+$/, '');
      if (nombre.endsWith('.csv')) tablas.push({ id, archivo: rel });
      else if (nombre.endsWith('.geojson')) capas.push({ id, archivo: rel });
      else if (nombre.endsWith('.json') && !nombre.startsWith('hallazgos')) resumenes.push({ id, archivo: rel });
    }
  };
  walk(carpeta);
  return { tablas, resumenes, capas };
}

export function hallazgos() {
  const carpeta = existeDirAnalisis();
  const todos: Record<string, unknown>[] = [];
  for (const nombre of ['hallazgos.json', 'hallazgos_cartografia.json']) {
    const ruta = path.join(carpeta, nombre);
    if (fs.existsSync(ruta)) {
      todos.push(...(JSON.parse(fs.readFileSync(ruta, 'utf-8')) as Record<string, unknown>[]));
    }
  }
  if (!todos.length) throw new ErrorDatos('Aún no hay hallazgos publicados.', 404);
  todos.sort((a, b) => Number(b.relevancia ?? 0) - Number(a.relevancia ?? 0));
  return { hallazgos: todos, total: todos.length };
}

export function tablaAnalisis(dataset: string, opts: { municipio?: string | null; periodo?: string | null; limite?: number }) {
  const ruta = resolver(dataset, '.csv');
  let filas = parseCsv(fs.readFileSync(ruta, 'utf-8'));
  const columnas = filas.length ? Object.keys(filas[0]) : [];
  if (opts.municipio && columnas.includes('municipio')) {
    const obj = opts.municipio.trim().toLowerCase();
    filas = filas.filter((f) => String(f.municipio).toLowerCase() === obj);
  }
  if (opts.periodo && columnas.includes('periodo')) {
    filas = filas.filter((f) => String(f.periodo) === opts.periodo);
  }
  const total = filas.length;
  const limite = opts.limite ?? 5000;
  const recortadas = filas.slice(0, limite).map((f) => {
    const o: Record<string, unknown> = {};
    for (const c of columnas) {
      const v = f[c];
      const n = Number(v);
      o[c] = v === '' ? null : (v !== '' && Number.isFinite(n) && /^-?\d/.test(v) ? n : v);
    }
    return o;
  });
  return { dataset, columnas, filas: recortadas, total_filas: total, truncado: total > limite };
}

export function resumenAnalisis(dataset: string): unknown {
  return JSON.parse(fs.readFileSync(resolver(dataset, '.json'), 'utf-8'));
}
export function geoAnalisis(dataset: string): unknown {
  return JSON.parse(fs.readFileSync(resolver(dataset, '.geojson'), 'utf-8'));
}

// ── parches (réplica de repository.parches) ─────────────────────────────────
export function parches(periodo: string | null, minHa: number, municipio: string | null): FeatureCollection {
  const meta = (datos.metadata().periodos as { id: string; ano_inicio?: number }[]) ?? [];
  const anoPor = new Map(meta.map((p) => [p.id, p.ano_inicio]));
  let periodos: string[];
  if (periodo != null) {
    datos.validarPeriodo(periodo);
    periodos = datos.hotspotsDisponibles().includes(periodo) ? [periodo] : [];
  } else {
    periodos = datos.hotspotsDisponibles();
  }
  let objetivoMun: string | null = null;
  if (municipio) {
    try { objetivoMun = normalizar(datos.nombreMunicipio(datos.resolverMunicipio(municipio))); }
    catch { objetivoMun = normalizar(municipio); }
  }
  const features: unknown[] = [];
  let totalHa = 0;
  const porPeriodo = new Map<string, { periodo: string; ano_inicio: number | undefined; n: number; ha: number }>();
  for (const pid of periodos) {
    const fc = datos.hotspots(pid);
    if (!fc) continue;
    const ano = anoPor.get(pid);
    for (const feat of fc.features as { geometry?: unknown; properties?: Record<string, unknown> }[]) {
      const props = feat.properties ?? {};
      const ha = Number(props.ha) || 0;
      if (ha < minHa) continue;
      const mun = props.municipio ?? null;
      if (objetivoMun != null && (mun == null || normalizar(String(mun)) !== objetivoMun)) continue;
      features.push({ type: 'Feature', geometry: feat.geometry, properties: { periodo: pid, ano_inicio: ano, municipio: mun, ha: Math.round(ha * 100) / 100 } });
      totalHa += ha;
      const agg = porPeriodo.get(pid) ?? { periodo: pid, ano_inicio: ano, n: 0, ha: 0 };
      agg.n += 1; agg.ha += ha;
      porPeriodo.set(pid, agg);
    }
  }
  const porPeriodoArr = [...porPeriodo.values()].map((a) => ({ ...a, ha: Math.round(a.ha * 10) / 10 }))
    .sort((a, b) => (a.ano_inicio ?? 0) - (b.ano_inicio ?? 0));
  return {
    type: 'FeatureCollection', features,
    metadata: { n_parches: features.length, ha_total: Math.round(totalHa * 10) / 10, periodos, min_ha: minHa, por_periodo: porPeriodoArr },
  };
}

/**
 * Resumen ligero (sin geometría) de los polígonos de deforestación por periodo,
 * para dibujar la línea de tiempo del visor. Devuelve conteo y área de cada
 * periodo con hotspots, opcionalmente acotado a un municipio.
 */
export function parchesResumen(municipio: string | null): {
  por_periodo: { periodo: string; ano_inicio: number | undefined; n: number; ha: number }[];
} {
  const meta = (datos.metadata().periodos as { id: string; ano_inicio?: number }[]) ?? [];
  const anoPor = new Map(meta.map((p) => [p.id, p.ano_inicio]));
  let objetivoMun: string | null = null;
  if (municipio) {
    try { objetivoMun = normalizar(datos.nombreMunicipio(datos.resolverMunicipio(municipio))); }
    catch { objetivoMun = normalizar(municipio); }
  }
  const filas: { periodo: string; ano_inicio: number | undefined; n: number; ha: number }[] = [];
  for (const pid of datos.hotspotsDisponibles()) {
    const fc = datos.hotspots(pid);
    if (!fc) continue;
    let n = 0;
    let ha = 0;
    for (const feat of fc.features as { properties?: Record<string, unknown> }[]) {
      const props = feat.properties ?? {};
      if (objetivoMun != null) {
        const mun = props.municipio ?? null;
        if (mun == null || normalizar(String(mun)) !== objetivoMun) continue;
      }
      n += 1;
      ha += Number(props.ha) || 0;
    }
    filas.push({ periodo: pid, ano_inicio: anoPor.get(pid), n, ha: Math.round(ha * 10) / 10 });
  }
  filas.sort((a, b) => (a.ano_inicio ?? 0) - (b.ano_inicio ?? 0));
  return { por_periodo: filas };
}

// ── territorios (réplica de /analisis/territorios) ──────────────────────────
interface CfgTerritorio {
  titulo: string; archivo: string; col_nombre: string; col_sec?: string | null;
  filtro?: [string, string]; por_clase?: boolean; col_defo?: string; col_area?: string | null;
}
export const TERRITORIOS: Record<string, CfgTerritorio> = {
  areas_protegidas: { titulo: 'Áreas protegidas', archivo: 'areas_protegidas_serie.csv', col_nombre: 'nombre', col_sec: 'categoria', por_clase: true, col_area: null },
  resguardos: { titulo: 'Resguardos indígenas', archivo: 'cartografia/territorios_oficiales.csv', filtro: ['tipo', 'resguardo'], col_nombre: 'nombre', col_sec: 'pueblo', col_defo: 'deforestacion_ha', col_area: 'area_oficial_ha' },
  consejos: { titulo: 'Consejos comunitarios', archivo: 'cartografia/territorios_oficiales.csv', filtro: ['tipo', 'consejo_comunitario'], col_nombre: 'nombre', col_sec: 'municipios', col_defo: 'deforestacion_ha', col_area: 'area_oficial_ha' },
  pomcas: { titulo: 'POMCAS (cuencas ordenadas)', archivo: 'cartografia/pomcas_serie.csv', col_nombre: 'pomca', col_sec: null, col_defo: 'deforestacion_ha', col_area: null },
  cuencas: { titulo: 'Cuencas hidrográficas', archivo: 'cuencas_serie.csv', col_nombre: 'cuenca', col_sec: null, por_clase: true, col_area: null },
};

export function catalogoTerritorios() {
  const carpeta = existeDirAnalisis();
  return {
    tipos: Object.entries(TERRITORIOS).map(([id, cfg]) => ({
      id, titulo: cfg.titulo, disponible: fs.existsSync(path.join(carpeta, cfg.archivo)),
    })),
  };
}

export function territorios(tipo: string, periodo: string | null) {
  const cfg = TERRITORIOS[tipo];
  if (!cfg) throw new ErrorDatos(`Tipo desconocido: '${tipo}'. Disponibles: ${Object.keys(TERRITORIOS).join(', ')}.`, 422);
  const ruta = path.join(existeDirAnalisis(), cfg.archivo);
  if (!fs.existsSync(ruta)) throw new ErrorDatos(`Aún no hay datos de '${tipo}' (${cfg.archivo}).`, 404);
  let filas = parseCsv(fs.readFileSync(ruta, 'utf-8'));

  if (cfg.filtro) {
    const [col, val] = cfg.filtro;
    filas = filas.filter((f) => String(f[col]).trim().toLowerCase() === val.toLowerCase());
  }
  filas = filas.filter((f) => f[cfg.col_nombre] != null && f[cfg.col_nombre] !== '');
  if (cfg.por_clase) filas = filas.filter((f) => f.clase === 'Deforestación');

  const periodosDisp = [...new Set(filas.map((f) => f.periodo).filter(Boolean))].sort();
  if (periodo) filas = filas.filter((f) => String(f.periodo) === periodo);

  const grupos = new Map<string, Record<string, string>[]>();
  for (const f of filas) {
    const clave = String(f[cfg.col_nombre]);
    (grupos.get(clave) ?? grupos.set(clave, []).get(clave)!).push(f);
  }
  const defoCol = cfg.por_clase ? 'hectareas' : (cfg.col_defo as string);
  const unidades = [...grupos.entries()].map(([nombre, grp]) => {
    const total = grp.reduce((s, r) => s + (Number(r[defoCol]) || 0), 0);
    let detalle: string | null = null;
    if (cfg.col_sec && grp[0][cfg.col_sec] != null) {
      const vals = grp.map((r) => r[cfg.col_sec!]).filter((v) => v && v !== 'nan' && v !== '');
      detalle = vals.length ? String(vals[0]) : null;
    }
    let area: number | null = null;
    let pct: number | null = null;
    if (cfg.col_area && grp[0][cfg.col_area] != null && grp[0][cfg.col_area] !== '') {
      area = Math.round(Number(grp[0][cfg.col_area]) * 10) / 10;
      if (area) pct = Math.round((100 * total / area) * 1000) / 1000;
    }
    const nPeriodos = new Set(grp.map((r) => r.periodo).filter(Boolean)).size || null;
    return { nombre, detalle, deforestacion_ha: Math.round(total * 100) / 100, n_periodos: nPeriodos, area_ha: area, pct_del_territorio: pct };
  }).sort((a, b) => b.deforestacion_ha - a.deforestacion_ha);

  return {
    tipo, titulo: cfg.titulo, periodo, periodos_disponibles: periodosDisp,
    n_unidades: unidades.length,
    deforestacion_total_ha: Math.round(unidades.reduce((s, u) => s + u.deforestacion_ha, 0) * 10) / 10,
    nota: 'Deforestación mapeada dentro de cada unidad. Ver metodología en /datos.',
    unidades,
  };
}
