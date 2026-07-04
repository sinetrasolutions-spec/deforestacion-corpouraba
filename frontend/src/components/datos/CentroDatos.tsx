'use client';

/**
 * Centro de descargas y metodología (SPEC §8.5). Reúne datasets descargables,
 * un generador de extractos filtrados, el catálogo de productos de análisis,
 * el diccionario de datos, la metodología (desde /metadata) y una vista previa.
 */
import { useEffect, useMemo, useState } from 'react';
import {
  Database,
  Download,
  FileJson,
  FileSpreadsheet,
  Layers,
  Map as MapIcon,
  Package,
  Table2,
} from 'lucide-react';
import {
  API_URL,
  getCapas,
  getMetadata,
  getMunicipios,
  getPeriodos,
  getSerie,
  urlDescarga,
} from '@/lib/api';
import type { FilaSerie, Periodo } from '@/lib/types';
import { fmtNum, fmtPct } from '@/lib/format';
import SectionHeading from '@/components/ui/SectionHeading';
import Badge from '@/components/ui/Badge';
import Loader from '@/components/ui/Loader';

const CLASES = ['Deforestación', 'Bosque Estable', 'No Bosque Estable', 'Regeneración', 'Sin Información'];

interface MetaPeriodo {
  id: string;
  ano_inicio: number;
  ano_fin: number;
  fuente: string;
}
interface Metadata {
  periodos?: MetaPeriodo[];
  nota_estimados?: string;
  nota_2015_2016?: string;
  qa_calculos?: { periodo: string; diferencia_pct: number }[];
  crs_salida?: string;
  crs_origen?: string;
}

export default function CentroDatos() {
  const [periodos, setPeriodos] = useState<Periodo[]>([]);
  const [capas, setCapas] = useState<{ id: string; nombre: string; unidades: number }[]>([]);
  const [municipios, setMunicipios] = useState<{ codigo: string; nombre: string }[]>([]);
  const [meta, setMeta] = useState<Metadata | null>(null);
  const [analisis, setAnalisis] = useState<{ tablas: { id: string }[]; capas: { id: string }[] } | null>(null);

  // Estado del generador de extracto
  const [munSel, setMunSel] = useState('');
  const [perSel, setPerSel] = useState('');
  const [claseSel, setClaseSel] = useState('Deforestación');

  // Vista previa
  const [preview, setPreview] = useState<FilaSerie[]>([]);
  const [cargandoPrev, setCargandoPrev] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [ps, cs, mun, m] = await Promise.all([
          getPeriodos(),
          getCapas(),
          getMunicipios(),
          getMetadata(),
        ]);
        setPeriodos(ps);
        setCapas(cs.capas);
        setMunicipios(
          (mun.features ?? [])
            .map((f) => ({
              codigo: String(f.properties?.codigo_dane ?? ''),
              nombre: String(f.properties?.nombre ?? ''),
            }))
            .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')),
        );
        setMeta(m as Metadata);
      } catch (e) {
        console.error('Error cargando catálogo de datos', e);
      }
      try {
        const r = await fetch(`${API_URL}/api/v1/analisis`);
        if (r.ok) setAnalisis(await r.json());
      } catch {
        /* opcional */
      }
    })();
  }, []);

  const paramsExtracto = useMemo(() => {
    const p: Record<string, string> = {};
    if (munSel) p.municipio = munSel;
    if (perSel) {
      const per = periodos.find((x) => x.id === perSel);
      if (per) {
        p.desde = String(per.ano_inicio);
        p.hasta = String(per.ano_fin);
      }
    }
    if (claseSel) p.clase = claseSel;
    return p;
  }, [munSel, perSel, claseSel, periodos]);

  async function verPrevia() {
    setCargandoPrev(true);
    try {
      const per = periodos.find((x) => x.id === perSel);
      const r = await getSerie({
        municipio: munSel ? [munSel] : undefined,
        clase: claseSel || undefined,
        desde: per?.ano_inicio,
        hasta: per?.ano_fin,
      });
      setPreview(r.data.slice(0, 50));
    } catch (e) {
      console.error(e);
    } finally {
      setCargandoPrev(false);
    }
  }

  const periodosConHotspots = periodos.filter((p) => p.tiene_hotspots);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <SectionHeading
        etiqueta="Datos abiertos"
        titulo="Centro de descargas"
        subtitulo="Todos los datos del observatorio, listos para análisis. Formatos CSV, Excel y GeoJSON con metadatos incluidos."
      />

      {/* ── Datasets principales ────────────────────────────────────────── */}
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <TarjetaDataset
          icono={FileSpreadsheet}
          titulo="Serie municipal"
          descripcion="Municipio × periodo × clase (1.123 filas). CSV o Excel con metadatos."
          acciones={[
            { etiqueta: 'CSV', href: urlDescarga('serie.csv') },
            { etiqueta: 'Excel', href: urlDescarga('serie.xlsx') },
          ]}
        />
        <TarjetaDataset
          icono={FileSpreadsheet}
          titulo="Serie regional"
          descripcion="Agregado de la jurisdicción por periodo y clase."
          acciones={[{ etiqueta: 'CSV', href: urlDescarga('serie.csv', { agregado: 'regional' }) }]}
        />
        <TarjetaDataset
          icono={MapIcon}
          titulo="Límites municipales"
          descripcion="Los 19 municipios en GeoJSON (WGS84) con códigos DANE y subregión."
          acciones={[{ etiqueta: 'GeoJSON', href: urlDescarga('municipios.geojson') }]}
        />
        <TarjetaDataset
          icono={Layers}
          titulo="Hotspots por periodo"
          descripcion="Polígonos de deforestación ≥1 ha. 12 periodos disponibles."
          selector={{
            opciones: periodosConHotspots.map((p) => ({ valor: p.id, etiqueta: p.id })),
            plantillaHref: (v) => urlDescarga(`hotspots/${v}.geojson`),
            etiquetaBoton: 'GeoJSON',
          }}
        />
        <TarjetaDataset
          icono={FileJson}
          titulo="Capas de contexto"
          descripcion="Áreas protegidas, resguardos, consejos, cuencas y capas oficiales."
          selector={{
            opciones: capas.map((c) => ({ valor: c.id, etiqueta: `${c.nombre} (${c.unidades})` })),
            plantillaHref: (v) => `${API_URL}/api/v1/capas/${v}`,
            etiquetaBoton: 'GeoJSON',
          }}
        />
        <TarjetaDataset
          icono={Package}
          titulo="Paquete completo"
          descripcion="Todos los datos procesados en un único archivo ZIP."
          acciones={[{ etiqueta: 'Descargar ZIP', href: urlDescarga('paquete.zip') }]}
        />
      </div>

      {/* ── Datos de la investigación ───────────────────────────────────── */}
      {analisis && (analisis.tablas.length > 0 || analisis.capas.length > 0) && (
        <div className="mt-4 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--fondo)] p-5">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-bosque-600" aria-hidden="true" />
            <h3 className="font-display text-lg font-semibold">Datos de la investigación temática</h3>
          </div>
          <p className="mt-1 text-sm text-[color:var(--tinta-suave)]">
            Tablas y capas generadas por la minería temática y el cruce con la cartografía oficial.
            También incluidas en el paquete ZIP.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {analisis.tablas.map((t) => (
              <a
                key={t.id}
                href={`${API_URL}/api/v1/analisis/tabla/${t.id}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--borde)] bg-[color:var(--superficie)] px-3 py-1.5 text-xs font-medium hover:border-bosque-300"
              >
                <Table2 className="h-3.5 w-3.5" /> {t.id}
              </a>
            ))}
            {analisis.capas.map((c) => (
              <a
                key={c.id}
                href={`${API_URL}/api/v1/analisis/geo/${c.id}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--borde)] bg-[color:var(--superficie)] px-3 py-1.5 text-xs font-medium hover:border-bosque-300"
              >
                <FileJson className="h-3.5 w-3.5" /> {c.id}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* ── Generador de extracto ───────────────────────────────────────── */}
      <div className="mt-8 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm">
        <h3 className="font-display text-lg font-semibold">Generador de extractos</h3>
        <p className="mb-4 text-sm text-[color:var(--tinta-suave)]">
          Filtre por municipio, periodo y clase; descargue solo lo que necesita.
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          <label className="text-sm">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
              Municipio
            </span>
            <select
              value={munSel}
              onChange={(e) => setMunSel(e.target.value)}
              className="w-full rounded-lg border border-[color:var(--borde)] bg-[color:var(--fondo)] px-3 py-2 text-sm"
            >
              <option value="">Todos</option>
              {municipios.map((m) => (
                <option key={m.codigo} value={m.codigo}>
                  {m.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
              Periodo
            </span>
            <select
              value={perSel}
              onChange={(e) => setPerSel(e.target.value)}
              className="w-full rounded-lg border border-[color:var(--borde)] bg-[color:var(--fondo)] px-3 py-2 text-sm"
            >
              <option value="">Todos</option>
              {periodos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-xs font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
              Clase
            </span>
            <select
              value={claseSel}
              onChange={(e) => setClaseSel(e.target.value)}
              className="w-full rounded-lg border border-[color:var(--borde)] bg-[color:var(--fondo)] px-3 py-2 text-sm"
            >
              {CLASES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <a
            href={urlDescarga('serie.csv', paramsExtracto)}
            className="inline-flex items-center gap-1.5 rounded-full bg-bosque-600 px-4 py-2 text-sm font-medium text-white hover:bg-bosque-700"
          >
            <Download className="h-4 w-4" /> CSV
          </a>
          <a
            href={urlDescarga('serie.xlsx', paramsExtracto)}
            className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--borde)] px-4 py-2 text-sm font-medium hover:border-bosque-300"
          >
            <Download className="h-4 w-4" /> Excel
          </a>
          <button
            type="button"
            onClick={verPrevia}
            className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--borde)] px-4 py-2 text-sm font-medium hover:border-bosque-300"
          >
            <Table2 className="h-4 w-4" /> Vista previa
          </button>
        </div>

        {cargandoPrev && <Loader texto="Cargando vista previa…" />}
        {preview.length > 0 && !cargandoPrev && (
          <div className="mt-4 max-h-80 overflow-auto rounded-lg border border-[color:var(--borde)]">
            <table className="min-w-full text-xs">
              <thead className="sticky top-0 bg-bosque-600 text-white">
                <tr>
                  {['Municipio', 'Subregión', 'Periodo', 'Clase', 'Ha', 'Ha/año', 'Fuente', 'Est.'].map((h) => (
                    <th key={h} className="px-2 py-1.5 text-left font-semibold">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.map((f, i) => (
                  <tr key={i} className={i % 2 ? 'bg-[color:var(--fondo)]' : ''}>
                    <td className="px-2 py-1">{f.municipio}</td>
                    <td className="px-2 py-1">{f.subregion}</td>
                    <td className="px-2 py-1">{f.periodo}</td>
                    <td className="px-2 py-1">{f.clase}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{fmtNum(f.hectareas, 1)}</td>
                    <td className="px-2 py-1 text-right tabular-nums">{fmtNum(f.hectareas_anuales, 1)}</td>
                    <td className="px-2 py-1">{f.fuente}</td>
                    <td className="px-2 py-1">{f.estimado ? 'Sí' : 'No'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Diccionario de datos ────────────────────────────────────────── */}
      <div className="mt-8 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm">
        <h3 className="font-display text-lg font-semibold">Diccionario de datos (serie municipal)</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-[color:var(--borde)] text-left text-[color:var(--tinta-suave)]">
                <th className="py-2 pr-4 font-semibold">Columna</th>
                <th className="py-2 font-semibold">Descripción</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['codigo_dane', 'Código DANE del municipio (5 dígitos, con cero inicial).'],
                ['municipio', 'Nombre oficial del municipio.'],
                ['subregion', 'Subregión CORPOURABA: Caribe, Centro, Atrato, Nutibara, Urrao.'],
                ['periodo', 'Periodo de monitoreo (p. ej. 2016-2017).'],
                ['ano_inicio / ano_fin', 'Años extremos del periodo (los 5 primeros duran 2 años).'],
                ['clase', 'Bosque Estable · Deforestación · No Bosque Estable · Regeneración · Sin Información.'],
                ['hectareas', 'Hectáreas de la clase en el municipio y periodo.'],
                ['hectareas_anuales', 'hectareas / años del periodo — usar para comparar.'],
                ['fuente', 'shapefile · excel · cuencas-calibrado · raster · estimado · estimado-calibrado-rat.'],
                ['estimado', 'True = sin medición municipal directa (referencia).'],
              ].map(([col, desc]) => (
                <tr key={col} className="border-b border-[color:var(--borde)]/60">
                  <td className="py-1.5 pr-4 font-mono text-xs">{col}</td>
                  <td className="py-1.5 text-[color:var(--tinta-suave)]">{desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Metodología ─────────────────────────────────────────────────── */}
      {meta && (
        <div className="mt-8 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--fondo)] p-5">
          <h3 className="font-display text-lg font-semibold">Metodología y fuentes</h3>
          {meta.periodos && (
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="text-left text-[color:var(--tinta-suave)]">
                    <th className="py-1 pr-4 font-semibold">Periodo</th>
                    <th className="py-1 pr-4 font-semibold">Fuente</th>
                    <th className="py-1 font-semibold">Diferencia vs. Cálculos oficiales</th>
                  </tr>
                </thead>
                <tbody>
                  {meta.periodos.map((p) => {
                    const qa = meta.qa_calculos?.find((q) => q.periodo === p.id);
                    return (
                      <tr key={p.id} className="border-t border-[color:var(--borde)]/50">
                        <td className="py-1 pr-4 font-medium">{p.id}</td>
                        <td className="py-1 pr-4">{p.fuente}</td>
                        <td className="py-1">
                          {qa ? `${fmtNum(qa.diferencia_pct, 2)} %` : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {meta.nota_estimados && (
            <p className="mt-3 text-sm text-[color:var(--tinta-suave)]">
              <Badge variante="estimado">estimados</Badge> {meta.nota_estimados}
            </p>
          )}
          {meta.nota_2015_2016 && (
            <p className="mt-2 text-sm text-[color:var(--tinta-suave)]">{meta.nota_2015_2016}</p>
          )}
          <p className="mt-3 text-xs text-[color:var(--tinta-suave)]">
            CRS de origen: {meta.crs_origen ?? 'EPSG:3115'} · CRS de salida: {meta.crs_salida ?? 'EPSG:4326'}.
            Atribución sugerida: «CORPOURABA — Observatorio de Deforestación de Urabá (2000–2024)».
          </p>
        </div>
      )}
      {!meta && <Loader texto="Cargando metodología…" />}

      <p className="mt-8 text-center text-xs text-[color:var(--tinta-suave)]">
        Los datos estimados representan {meta ? '' : '≈23 % '}de los registros y se marcan siempre con
        distintivo visual. Úselos como referencia, no como cifra oficial.
      </p>
    </div>
  );
}

/** Tarjeta de un dataset con botones directos o un selector desplegable. */
function TarjetaDataset({
  icono: Icono,
  titulo,
  descripcion,
  acciones,
  selector,
}: {
  icono: typeof FileSpreadsheet;
  titulo: string;
  descripcion: string;
  acciones?: { etiqueta: string; href: string }[];
  selector?: {
    opciones: { valor: string; etiqueta: string }[];
    plantillaHref: (v: string) => string;
    etiquetaBoton: string;
  };
}) {
  const [sel, setSel] = useState(selector?.opciones[0]?.valor ?? '');
  useEffect(() => {
    if (selector && !sel && selector.opciones[0]) setSel(selector.opciones[0].valor);
  }, [selector, sel]);

  return (
    <div className="flex flex-col rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-bosque-50 text-bosque-600 dark:bg-bosque-900 dark:text-bosque-300">
        <Icono className="h-5 w-5" aria-hidden="true" />
      </span>
      <h3 className="mt-3 font-semibold">{titulo}</h3>
      <p className="mt-1 flex-1 text-sm text-[color:var(--tinta-suave)]">{descripcion}</p>
      {acciones && (
        <div className="mt-4 flex flex-wrap gap-2">
          {acciones.map((a) => (
            <a
              key={a.etiqueta}
              href={a.href}
              className="inline-flex items-center gap-1.5 rounded-full bg-bosque-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-bosque-700"
            >
              <Download className="h-3.5 w-3.5" /> {a.etiqueta}
            </a>
          ))}
        </div>
      )}
      {selector && (
        <div className="mt-4 flex gap-2">
          <select
            value={sel}
            onChange={(e) => setSel(e.target.value)}
            className="min-w-0 flex-1 rounded-lg border border-[color:var(--borde)] bg-[color:var(--fondo)] px-2 py-1.5 text-xs"
          >
            {selector.opciones.map((o) => (
              <option key={o.valor} value={o.valor}>
                {o.etiqueta}
              </option>
            ))}
          </select>
          <a
            href={selector.plantillaHref(sel)}
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-bosque-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-bosque-700"
          >
            <Download className="h-3.5 w-3.5" /> {selector.etiquetaBoton}
          </a>
        </div>
      )}
    </div>
  );
}
