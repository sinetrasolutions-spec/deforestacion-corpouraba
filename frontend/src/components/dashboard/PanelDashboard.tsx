'use client';

/**
 * Panel del dashboard analítico (SPEC §8.3). Descarga la serie municipal
 * completa una vez y deriva en cliente KPIs, series, ranking, comparador,
 * mapa de calor y predicción según los filtros. Añade la sección «Hallazgos
 * de la investigación» conectada a /api/v1/analisis/hallazgos.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { motion, useReducedMotion } from 'framer-motion';
import { Flame, Ruler, TreePine, TrendingDown, X } from 'lucide-react';
import clsx from 'clsx';
import {
  API_URL,
  getComparacion,
  getMetadata,
  getPrediccion,
  getSerie,
} from '@/lib/api';
import type { FilaSerie, Prediccion } from '@/lib/types';
import { colorPara, RAMPA_DEFORESTACION } from '@/lib/colores';
import { fmtHa, fmtNum, fmtPct } from '@/lib/format';
import KpiCard from '@/components/ui/KpiCard';
import SectionHeading from '@/components/ui/SectionHeading';
import BotonExportar from '@/components/ui/BotonExportar';
import Badge from '@/components/ui/Badge';
import Loader from '@/components/ui/Loader';
import DeforestacionPorTerritorio from './DeforestacionPorTerritorio';

const SUBREGIONES = ['Caribe', 'Centro', 'Atrato', 'Nutibara', 'Urrao'] as const;
const PALETA_COMPARADOR = ['#DC2626', '#2563EB', '#16A34A', '#D97706', '#7C3AED', '#0891B2'];

interface Hallazgo {
  id: string;
  tema: string;
  titulo: string;
  cifra: number;
  unidad: string;
  periodo_referencia: string;
  descripcion: string;
  relevancia: number;
}

export default function PanelDashboard() {
  const paramsUrl = useSearchParams();
  const reducir = useReducedMotion();

  const [serie, setSerie] = useState<FilaSerie[]>([]);
  const [cargando, setCargando] = useState(true);
  const [fuentes, setFuentes] = useState<{ id: string; fuente: string }[]>([]);
  const [hallazgos, setHallazgos] = useState<Hallazgo[]>([]);

  // Filtros
  const [subregion, setSubregion] = useState<string>('');
  const [municipiosSel, setMunicipiosSel] = useState<string[]>([]);
  const [incluirEstimados, setIncluirEstimados] = useState(true);
  const [rango, setRango] = useState<[number, number]>([2000, 2024]);

  // Carga de la serie de Deforestación completa (municipal) + metadata + hallazgos
  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const s = await getSerie({ clase: 'Deforestación', incluirEstimados: true });
        if (vivo) setSerie(s.data);
      } catch (e) {
        console.error('Error cargando serie', e);
      } finally {
        if (vivo) setCargando(false);
      }
      try {
        const meta = (await getMetadata()) as { periodos?: { id: string; fuente: string }[] };
        if (vivo && meta.periodos) setFuentes(meta.periodos.map((p) => ({ id: p.id, fuente: p.fuente })));
      } catch {
        /* metadata opcional */
      }
      try {
        const r = await fetch(`${API_URL}/api/v1/analisis/hallazgos`);
        if (r.ok && vivo) {
          const j = (await r.json()) as { hallazgos: Hallazgo[] };
          setHallazgos(j.hallazgos);
        }
      } catch {
        /* la sección se oculta si falla */
      }
    })();
    return () => {
      vivo = false;
    };
  }, []);

  // Lee ?municipio= de la URL al montar
  useEffect(() => {
    const m = paramsUrl.get('municipio');
    if (m) setMunicipiosSel((prev) => (prev.includes(m) ? prev : [...prev, m]));
  }, [paramsUrl]);

  // Catálogo de municipios (de la propia serie)
  const municipios = useMemo(() => {
    const mapa = new Map<string, { codigo: string; nombre: string; subregion: string }>();
    serie.forEach((f) =>
      mapa.set(f.codigo_dane, { codigo: f.codigo_dane, nombre: f.municipio, subregion: f.subregion }),
    );
    return [...mapa.values()].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  }, [serie]);

  const periodosOrden = useMemo(() => {
    const mapa = new Map<string, { id: string; ini: number; fin: number }>();
    serie.forEach((f) => mapa.set(f.periodo, { id: f.periodo, ini: f.ano_inicio, fin: f.ano_fin }));
    return [...mapa.values()].sort((a, b) => a.ini - b.ini);
  }, [serie]);

  // Serie filtrada según los controles
  const filtrada = useMemo(() => {
    return serie.filter((f) => {
      if (!incluirEstimados && f.estimado) return false;
      if (subregion && f.subregion !== subregion) return false;
      if (municipiosSel.length && !municipiosSel.includes(f.codigo_dane)) return false;
      if (f.ano_inicio < rango[0] || f.ano_fin > rango[1]) return false;
      return true;
    });
  }, [serie, incluirEstimados, subregion, municipiosSel, rango]);

  // KPIs derivados
  const kpis = useMemo(() => {
    const total = filtrada.reduce((s, f) => s + f.hectareas, 0);
    const porPeriodo = new Map<string, { ha: number; hay: number; est: boolean }>();
    const porMun = new Map<string, { nombre: string; ha: number }>();
    filtrada.forEach((f) => {
      const p = porPeriodo.get(f.periodo) ?? { ha: 0, hay: 0, est: false };
      p.ha += f.hectareas;
      p.hay += f.hectareas_anuales;
      p.est = p.est || f.estimado;
      porPeriodo.set(f.periodo, p);
      const m = porMun.get(f.codigo_dane) ?? { nombre: f.municipio, ha: 0 };
      m.ha += f.hectareas;
      porMun.set(f.codigo_dane, m);
    });
    let critico = { periodo: '—', hay: -1, est: false };
    porPeriodo.forEach((v, k) => {
      if (v.hay > critico.hay) critico = { periodo: k, hay: v.hay, est: v.est };
    });
    let peor = { nombre: '—', ha: -1 };
    porMun.forEach((v) => {
      if (v.ha > peor.ha) peor = { nombre: v.nombre, ha: v.ha };
    });
    const anios = rango[1] - rango[0] || 1;
    return {
      total,
      promedioAnual: total / anios,
      critico,
      peor,
    };
  }, [filtrada, rango]);

  // Serie temporal regional (ha/año) según filtros
  const serieTemporal = useMemo(() => {
    const mapa = new Map<string, { periodo: string; ini: number; hay: number; estimado: boolean }>();
    filtrada.forEach((f) => {
      const e = mapa.get(f.periodo) ?? { periodo: f.periodo, ini: f.ano_inicio, hay: 0, estimado: false };
      e.hay += f.hectareas_anuales;
      e.estimado = e.estimado || f.estimado;
      mapa.set(f.periodo, e);
    });
    return [...mapa.values()].sort((a, b) => a.ini - b.ini);
  }, [filtrada]);

  // Ranking top-10 acumulado según filtros
  const ranking = useMemo(() => {
    const mapa = new Map<string, { municipio: string; codigo: string; ha: number; est: boolean }>();
    filtrada.forEach((f) => {
      const e = mapa.get(f.codigo_dane) ?? { municipio: f.municipio, codigo: f.codigo_dane, ha: 0, est: false };
      e.ha += f.hectareas;
      e.est = e.est || f.estimado;
      mapa.set(f.codigo_dane, e);
    });
    return [...mapa.values()].sort((a, b) => b.ha - a.ha).slice(0, 10);
  }, [filtrada]);

  // Heatmap municipio × periodo (ha/año), respeta filtros de municipio/subregión
  const heat = useMemo(() => {
    const muns = municipios.filter(
      (m) =>
        (!subregion || m.subregion === subregion) &&
        (!municipiosSel.length || municipiosSel.includes(m.codigo)),
    );
    const celdas = new Map<string, number>();
    let max = 0;
    filtrada.forEach((f) => {
      celdas.set(`${f.codigo_dane}|${f.periodo}`, f.hectareas_anuales);
      if (f.hectareas_anuales > max) max = f.hectareas_anuales;
    });
    const breaks = [max * 0.05, max * 0.15, max * 0.35, max * 0.6, max].map((v) => Math.round(v));
    return { muns, celdas, breaks };
  }, [municipios, filtrada, subregion, municipiosSel]);

  function toggleMunicipio(codigo: string) {
    setMunicipiosSel((prev) =>
      prev.includes(codigo) ? prev.filter((c) => c !== codigo) : [...prev, codigo],
    );
  }
  function limpiar() {
    setSubregion('');
    setMunicipiosSel([]);
    setIncluirEstimados(true);
    setRango([2000, 2024]);
  }

  const refSerie = useRef<HTMLDivElement>(null);
  const refRanking = useRef<HTMLDivElement>(null);
  const refComparador = useRef<HTMLDivElement>(null);
  const pctEstimado = useMemo(() => {
    const est = serie.filter((f) => f.estimado).length;
    return serie.length ? (est / serie.length) * 100 : 0;
  }, [serie]);

  if (cargando) return <Loader texto="Cargando dashboard…" className="min-h-[60vh]" />;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
      <SectionHeading
        etiqueta="Dashboard analítico"
        titulo="Deforestación en cifras"
        subtitulo="Explore los 19 municipios y 18 periodos de monitoreo. Todos los gráficos responden a los filtros y pueden exportarse."
      />

      {/* ── Barra de filtros sticky ─────────────────────────────────────── */}
      <div className="sticky top-16 z-30 mt-6 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/95 p-4 shadow-sm backdrop-blur">
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
              Territorial
            </label>
            <select
              value={subregion}
              onChange={(e) => setSubregion(e.target.value)}
              className="w-full rounded-lg border border-[color:var(--borde)] bg-[color:var(--fondo)] px-3 py-2 text-sm"
            >
              <option value="">Todas</option>
              {SUBREGIONES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
              Rango de años: <span className="text-bosque-700 dark:text-bosque-300">{rango[0]}–{rango[1]}</span>
            </label>
            <SelectorRango min={2000} max={2024} valor={rango} onCambio={setRango} />
            <div className="mt-1 flex justify-between text-[10px] text-[color:var(--tinta-suave)]">
              <span>2000</span>
              <span>2024</span>
            </div>
          </div>

          <div className="flex items-end gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={incluirEstimados}
                onChange={(e) => setIncluirEstimados(e.target.checked)}
                className="accent-bosque-600"
              />
              Incluir estimados
            </label>
          </div>

          <div className="flex items-end">
            <button
              type="button"
              onClick={limpiar}
              className="rounded-full border border-[color:var(--borde)] px-4 py-2 text-sm font-medium transition-colors hover:border-bosque-300"
            >
              Limpiar filtros
            </button>
          </div>
        </div>

        {/* Multiselect de municipios (chips) */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {municipios.map((m) => (
            <button
              key={m.codigo}
              type="button"
              onClick={() => toggleMunicipio(m.codigo)}
              className={clsx(
                'rounded-full px-2.5 py-1 text-xs font-medium transition-colors',
                municipiosSel.includes(m.codigo)
                  ? 'bg-bosque-600 text-white'
                  : 'bg-[color:var(--fondo)] text-[color:var(--tinta-suave)] hover:bg-bosque-50 dark:hover:bg-bosque-900',
              )}
            >
              {m.nombre}
              {municipiosSel.includes(m.codigo) && <X className="ml-1 inline h-3 w-3" />}
            </button>
          ))}
        </div>
      </div>

      {/* ── KPIs ────────────────────────────────────────────────────────── */}
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard titulo="Total deforestado" valor={kpis.total} formato={fmtHa} icono={Flame} />
        <KpiCard
          titulo="Promedio anual"
          valor={kpis.promedioAnual}
          formato={(n) => `${fmtNum(n)} ha/año`}
          icono={TrendingDown}
          retraso={0.05}
        />
        <KpiCard
          titulo="Periodo más crítico"
          valor={kpis.critico.hay > 0 ? kpis.critico.hay : 0}
          formato={() => kpis.critico.periodo}
          detalle={kpis.critico.hay > 0 ? `${fmtNum(kpis.critico.hay)} ha/año` : undefined}
          estimado={kpis.critico.est}
          icono={Ruler}
          retraso={0.1}
        />
        <KpiCard
          titulo="Municipio más afectado"
          valor={kpis.peor.ha > 0 ? kpis.peor.ha : 0}
          formato={() => kpis.peor.nombre}
          detalle={kpis.peor.ha > 0 ? fmtHa(kpis.peor.ha) : undefined}
          icono={TreePine}
          retraso={0.15}
        />
      </div>

      {/* ── Serie temporal ──────────────────────────────────────────────── */}
      <TarjetaGrafico
        titulo="Serie temporal de deforestación"
        subtitulo="Hectáreas por año. Las áreas sombreadas marcan periodos estimados."
        refExport={refSerie}
        nombre="serie_temporal"
        csv={() =>
          'periodo,ha_anuales,estimado\n' +
          serieTemporal.map((s) => `${s.periodo},${s.hay.toFixed(1)},${s.estimado}`).join('\n')
        }
      >
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={serieTemporal} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="gradSerie" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#DC2626" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#DC2626" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--borde)" />
            <XAxis dataKey="periodo" tick={{ fontSize: 11 }} angle={-30} textAnchor="end" height={54} />
            <YAxis tick={{ fontSize: 11 }} width={48} />
            <Tooltip
              formatter={(v: number) => [`${fmtNum(v)} ha/año`, 'Deforestación']}
              contentStyle={{ fontSize: 12 }}
            />
            {serieTemporal.map((s, i) =>
              s.estimado ? (
                <ReferenceArea
                  key={`est-${s.periodo}`}
                  x1={serieTemporal[Math.max(i - 1, 0)].periodo}
                  x2={serieTemporal[Math.min(i + 1, serieTemporal.length - 1)].periodo}
                  fill="#FDBA74"
                  fillOpacity={0.12}
                />
              ) : null,
            )}
            <Area type="monotone" dataKey="hay" stroke="none" fill="url(#gradSerie)" />
            <Line
              type="monotone"
              dataKey="hay"
              stroke="#DC2626"
              strokeWidth={2.5}
              dot={(props) => {
                const { cx, cy, payload, index } = props as unknown as {
                  cx: number;
                  cy: number;
                  payload: { estimado: boolean };
                  index: number;
                };
                return (
                  <circle
                    key={index}
                    cx={cx}
                    cy={cy}
                    r={3.5}
                    fill={payload.estimado ? '#FFFFFF' : '#DC2626'}
                    stroke="#DC2626"
                    strokeWidth={1.5}
                  />
                );
              }}
              isAnimationActive={!reducir}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </TarjetaGrafico>

      {/* ── Ranking + Predicción ────────────────────────────────────────── */}
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <TarjetaGrafico
          titulo="Ranking de municipios"
          subtitulo="Top 10 por deforestación acumulada. Clic en una barra para filtrar."
          refExport={refRanking}
          nombre="ranking"
          csv={() => 'municipio,ha\n' + ranking.map((r) => `${r.municipio},${r.ha.toFixed(1)}`).join('\n')}
        >
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={ranking} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--borde)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="municipio" width={92} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => [fmtHa(v), 'Acumulado']} contentStyle={{ fontSize: 12 }} />
              <Bar
                dataKey="ha"
                radius={[0, 4, 4, 0]}
                isAnimationActive={!reducir}
                onClick={(d: { codigo?: string }) => d.codigo && toggleMunicipio(d.codigo)}
                cursor="pointer"
              >
                {ranking.map((r, i) => {
                  const idx = Math.min(
                    Math.floor((i / Math.max(ranking.length - 1, 1)) * (RAMPA_DEFORESTACION.length - 1)),
                    RAMPA_DEFORESTACION.length - 1,
                  );
                  return (
                    <Cell key={r.codigo} fill={RAMPA_DEFORESTACION[RAMPA_DEFORESTACION.length - 1 - idx]} />
                  );
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </TarjetaGrafico>

        <PrediccionCard municipio={municipiosSel.length === 1 ? municipiosSel[0] : undefined} />
      </div>

      {/* ── Comparador ──────────────────────────────────────────────────── */}
      <ComparadorCard
        municipios={municipiosSel}
        refExport={refComparador}
      />

      {/* ── Heatmap ─────────────────────────────────────────────────────── */}
      <div className="mt-6 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm">
        <h3 className="font-display text-lg font-semibold">Mapa de calor municipio × periodo</h3>
        <p className="mb-3 text-sm text-[color:var(--tinta-suave)]">Deforestación anualizada (ha/año).</p>
        <div className="overflow-x-auto">
          <table className="min-w-full border-separate" style={{ borderSpacing: 2 }}>
            <thead>
              <tr>
                <th className="sticky left-0 z-10 bg-[color:var(--superficie)] px-2 py-1 text-left text-[11px] text-[color:var(--tinta-suave)]">
                  Municipio
                </th>
                {periodosOrden.map((p) => (
                  <th key={p.id} className="px-1 py-1 text-[10px] text-[color:var(--tinta-suave)]">
                    <span className="inline-block -rotate-45 whitespace-nowrap">{p.id}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {heat.muns.map((m) => (
                <tr key={m.codigo}>
                  <td className="sticky left-0 z-10 bg-[color:var(--superficie)] px-2 py-1 text-xs font-medium">
                    {m.nombre}
                  </td>
                  {periodosOrden.map((p) => {
                    const v = heat.celdas.get(`${m.codigo}|${p.id}`);
                    return (
                      <td key={p.id} className="p-0">
                        <div
                          title={v != null ? `${m.nombre} · ${p.id}: ${fmtNum(v)} ha/año` : `${m.nombre} · ${p.id}: sin dato`}
                          className="h-6 w-6 rounded-sm"
                          style={{ backgroundColor: v != null ? colorPara(v, heat.breaks) : 'var(--borde)' }}
                        />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Hallazgos de la investigación ───────────────────────────────── */}
      {hallazgos.length > 0 && (
        <section className="mt-10">
          <SectionHeading
            etiqueta="Investigación"
            titulo="Hallazgos verificados"
            subtitulo="Resultados de la minería temática y del cruce con la cartografía oficial, ordenados por relevancia."
          />
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {hallazgos.map((h, i) => (
              <motion.article
                key={h.id}
                initial={reducir ? false : { opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: Math.min(i * 0.04, 0.3) }}
                className="rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm"
              >
                <div className="flex items-center justify-between gap-2">
                  <Badge variante="neutro">{h.tema.replace(/_/g, ' ')}</Badge>
                  <span className="text-[11px] text-[color:var(--tinta-suave)]">{h.periodo_referencia}</span>
                </div>
                <p className="mt-3 font-display text-3xl font-semibold text-bosque-700 dark:text-bosque-300">
                  {fmtNum(h.cifra, h.cifra % 1 === 0 ? 0 : 1)}
                  <span className="ml-1 text-sm font-normal text-[color:var(--tinta-suave)]">{h.unidad}</span>
                </p>
                <h4 className="mt-2 font-semibold leading-snug">{h.titulo}</h4>
                <p className="mt-1.5 text-sm leading-relaxed text-[color:var(--tinta-suave)]">{h.descripcion}</p>
              </motion.article>
            ))}
          </div>
        </section>
      )}

      {/* ── Deforestación por territorio (AP, POMCAS, resguardos, consejos) ─ */}
      <DeforestacionPorTerritorio />

      {/* ── Nota de fuentes ─────────────────────────────────────────────── */}
      <div className="mt-10 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--fondo)] p-5 text-sm text-[color:var(--tinta-suave)]">
        <p className="font-semibold text-[color:var(--tinta)]">Fuentes y calidad de los datos</p>
        <p className="mt-1">
          {fmtPct(pctEstimado)} de los registros de deforestación son estimados o calibrados
          (2010-2012, 2018-2019, 2023-2024) y se señalan con distintivo visual. 2015-2016 es
          dato real, recuperado de la tabla municipal oficial (dbf).
        </p>
        {fuentes.length > 0 && (
          <p className="mt-2 text-xs">
            Fuente por periodo:{' '}
            {fuentes.map((f, i) => (
              <span key={f.id}>
                {i > 0 && ' · '}
                <span className="font-medium text-[color:var(--tinta)]">{f.id}</span> {f.fuente}
              </span>
            ))}
          </p>
        )}
      </div>
    </div>
  );
}

/** Selector de rango de años con doble manija sobre un solo riel. */
function SelectorRango({
  min,
  max,
  valor,
  onCambio,
}: {
  min: number;
  max: number;
  valor: [number, number];
  onCambio: (r: [number, number]) => void;
}) {
  const [lo, hi] = valor;
  const pctLo = ((lo - min) / (max - min)) * 100;
  const pctHi = ((hi - min) / (max - min)) * 100;
  return (
    <div className="relative h-5 select-none">
      {/* Riel base */}
      <div className="absolute top-1/2 h-1.5 w-full -translate-y-1/2 rounded-full bg-[color:var(--borde)]" />
      {/* Tramo seleccionado */}
      <div
        className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-bosque-600"
        style={{ left: `${pctLo}%`, right: `${100 - pctHi}%` }}
      />
      {/* Manija de año inicial (encima cuando está al tope para poder tomarla) */}
      <input
        type="range"
        min={min}
        max={max}
        value={lo}
        onChange={(e) => onCambio([Math.min(Number(e.target.value), hi), hi])}
        className="rango-dual"
        style={{ zIndex: lo >= max - 1 ? 5 : 3 }}
        aria-label="Año inicial del rango"
      />
      {/* Manija de año final */}
      <input
        type="range"
        min={min}
        max={max}
        value={hi}
        onChange={(e) => onCambio([lo, Math.max(Number(e.target.value), lo)])}
        className="rango-dual"
        style={{ zIndex: 4 }}
        aria-label="Año final del rango"
      />
    </div>
  );
}

/** Envoltorio de gráfico con encabezado y botones de exportación. */
function TarjetaGrafico({
  titulo,
  subtitulo,
  children,
  refExport,
  nombre,
  csv,
}: {
  titulo: string;
  subtitulo?: string;
  children: React.ReactNode;
  refExport: React.RefObject<HTMLDivElement>;
  nombre: string;
  csv?: () => string;
}) {
  return (
    <div className="mt-6 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-display text-lg font-semibold">{titulo}</h3>
          {subtitulo && <p className="text-sm text-[color:var(--tinta-suave)]">{subtitulo}</p>}
        </div>
        <BotonExportar objetivoRef={refExport} nombreArchivo={nombre} obtenerCsv={csv} />
      </div>
      <div ref={refExport}>{children}</div>
    </div>
  );
}

/** Tarjeta de predicción por regresión lineal. */
function PrediccionCard({ municipio }: { municipio?: string }) {
  const [pred, setPred] = useState<Prediccion | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let vivo = true;
    setError(false);
    getPrediccion(municipio, 3)
      .then((p) => vivo && setPred(p))
      .catch(() => vivo && setError(true));
    return () => {
      vivo = false;
    };
  }, [municipio]);

  const datos = useMemo(() => {
    if (!pred) return [];
    const hist = pred.historico.map((h) => ({
      etiqueta: h.periodo,
      historico: h.hectareas_anuales,
      prediccion: null as number | null,
      lo: null as number | null,
      hi: null as number | null,
    }));
    const fut = pred.prediccion.map((p) => ({
      etiqueta: String(p.ano),
      historico: null as number | null,
      prediccion: p.hectareas_anuales_estimadas,
      lo: p.intervalo[0],
      hi: p.intervalo[1],
    }));
    return [...hist, ...fut];
  }, [pred]);

  return (
    <div className="rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm">
      <h3 className="font-display text-lg font-semibold">
        Predicción {municipio ? 'municipal' : 'regional'}
      </h3>
      <p className="mb-3 text-sm text-[color:var(--tinta-suave)]">
        Proyección a 3 años de la tasa anual de deforestación.
      </p>
      {error && <p className="py-8 text-center text-sm text-[color:var(--tinta-suave)]">No disponible.</p>}
      {!error && !pred && <Loader texto="Calculando…" />}
      {pred && (
        <>
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={datos} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--borde)" />
              <XAxis dataKey="etiqueta" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 11 }} width={44} />
              <Tooltip formatter={(v: number) => `${fmtNum(v)} ha/año`} contentStyle={{ fontSize: 12 }} />
              <Area dataKey="hi" stroke="none" fill="#2563EB" fillOpacity={0.1} />
              <Area dataKey="lo" stroke="none" fill="#FFFFFF" fillOpacity={1} />
              <Line dataKey="historico" stroke="#111827" strokeWidth={2} dot={false} connectNulls />
              <Line
                dataKey="prediccion"
                stroke="#2563EB"
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={{ r: 3 }}
                connectNulls
              />
            </ComposedChart>
          </ResponsiveContainer>
          <p className="mt-2 flex items-start gap-1.5 text-xs text-alerta-700 dark:text-alerta-300">
            <span aria-hidden="true">⚠️</span>
            {pred.advertencia}
          </p>
        </>
      )}
    </div>
  );
}

/** Comparador de hasta 6 municipios. */
function ComparadorCard({
  municipios,
  refExport,
}: {
  municipios: string[];
  refExport: React.RefObject<HTMLDivElement>;
}) {
  const [datos, setDatos] = useState<{ periodo: string; [k: string]: number | string }[]>([]);
  const [nombres, setNombres] = useState<string[]>([]);

  useEffect(() => {
    const codigos = municipios.slice(0, 6);
    if (codigos.length < 2) {
      setDatos([]);
      setNombres([]);
      return;
    }
    let vivo = true;
    getComparacion(codigos)
      .then((r) => {
        if (!vivo) return;
        const porPeriodo = new Map<string, { periodo: string; [k: string]: number | string }>();
        r.data.forEach((m) => {
          m.serie.forEach((s) => {
            const fila = porPeriodo.get(s.periodo) ?? { periodo: s.periodo };
            fila[m.municipio] = s.hectareas_anuales;
            porPeriodo.set(s.periodo, fila);
          });
        });
        setNombres(r.data.map((m) => m.municipio));
        setDatos([...porPeriodo.values()].sort((a, b) => String(a.periodo).localeCompare(String(b.periodo))));
      })
      .catch((e) => console.error('Error comparador', e));
    return () => {
      vivo = false;
    };
  }, [municipios]);

  return (
    <div className="mt-6 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-display text-lg font-semibold">Comparador de municipios</h3>
          <p className="text-sm text-[color:var(--tinta-suave)]">
            Seleccione entre 2 y 6 municipios en los filtros para compararlos (ha/año).
          </p>
        </div>
        {datos.length > 0 && <BotonExportar objetivoRef={refExport} nombreArchivo="comparador" />}
      </div>
      <div ref={refExport}>
        {datos.length === 0 ? (
          <p className="py-10 text-center text-sm text-[color:var(--tinta-suave)]">
            Elija al menos 2 municipios en la barra de filtros.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={datos} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--borde)" />
              <XAxis dataKey="periodo" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={54} />
              <YAxis tick={{ fontSize: 11 }} width={44} />
              <Tooltip contentStyle={{ fontSize: 12 }} formatter={(v: number) => `${fmtNum(v)} ha/año`} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {nombres.map((n, i) => (
                <Line
                  key={n}
                  type="monotone"
                  dataKey={n}
                  stroke={PALETA_COMPARADOR[i % PALETA_COMPARADOR.length]}
                  strokeWidth={2}
                  dot={{ r: 2.5 }}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
