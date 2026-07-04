/**
 * Generación de descargas del lado servidor (réplica de downloads.py):
 * CSV con BOM + cabecera de metadatos, XLSX (SheetJS) y ZIP (JSZip).
 */
import fs from 'node:fs';
import path from 'node:path';
import * as XLSX from 'xlsx';
import JSZip from 'jszip';
import { DATA_DIR } from './datos';

const BOM = '﻿';
const TITULO = 'Observatorio de Deforestación CORPOURABA (2000–2024)';
const ATRIBUCION =
  'Fuente: CORPOURABA — monitoreo de bosque de la jurisdicción; datos procesados por el ETL del Observatorio.';
const NOTA_ESTIMADOS =
  'Los periodos 2010-2012, 2015-2016, 2018-2019 y 2023-2024 contienen valores estimados ' +
  '(columna estimado=True); úselos solo como referencia.';

function describirFiltros(filtros: Record<string, unknown>): string {
  const partes = Object.entries(filtros)
    .filter(([, v]) => v != null && v !== '' && !(Array.isArray(v) && v.length === 0))
    .map(([k, v]) => `${k}=${v}`);
  return partes.length ? partes.join('; ') : 'sin filtros (serie completa)';
}

function celda(v: unknown): string {
  if (typeof v === 'boolean') return v ? 'True' : 'False';
  const s = String(v ?? '');
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** CSV con BOM UTF-8 y cabecera de metadatos comentada con '#'. */
export function csvSerie(filas: Record<string, unknown>[], filtros: Record<string, unknown>): string {
  const meta = [
    TITULO,
    `Generado: ${new Date().toISOString().replace(/\.\d+Z$/, 'Z')}`,
    `Filtros: ${describirFiltros(filtros)}`,
    `Nota: ${NOTA_ESTIMADOS}`,
    ATRIBUCION,
  ];
  const encabezado = meta.map((l) => `# ${l}\n`).join('');
  if (!filas.length) return BOM + encabezado;
  const cols = Object.keys(filas[0]);
  const cuerpo = [cols.join(','), ...filas.map((f) => cols.map((c) => celda(f[c])).join(','))].join('\n');
  return BOM + encabezado + cuerpo + '\n';
}

/** XLSX con hojas `datos` y `metadatos`. */
export function xlsxSerie(filas: Record<string, unknown>[], filtros: Record<string, unknown>): Uint8Array {
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(filas), 'datos');
  const meta = [
    { campo: 'titulo', valor: TITULO },
    { campo: 'generado', valor: new Date().toISOString() },
    { campo: 'filtros', valor: describirFiltros(filtros) },
    { campo: 'filas', valor: String(filas.length) },
    { campo: 'nota_estimados', valor: NOTA_ESTIMADOS },
    { campo: 'atribucion', valor: ATRIBUCION },
  ];
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(meta), 'metadatos');
  return XLSX.write(wb, { type: 'array', bookType: 'xlsx' }) as Uint8Array;
}

/** ZIP en memoria con todo data/processed. */
export async function zipPaquete(): Promise<Uint8Array> {
  const zip = new JSZip();
  const agregar = (dir: string, base = ''): void => {
    for (const nombre of fs.readdirSync(dir).sort()) {
      const abs = path.join(dir, nombre);
      const rel = base ? `${base}/${nombre}` : nombre;
      if (fs.statSync(abs).isDirectory()) agregar(abs, rel);
      else zip.file(rel, fs.readFileSync(abs));
    }
  };
  agregar(DATA_DIR);
  return zip.generateAsync({ type: 'uint8array', compression: 'DEFLATE' });
}

export function archivoDatos(rel: string): Buffer {
  return fs.readFileSync(path.join(DATA_DIR, rel));
}
