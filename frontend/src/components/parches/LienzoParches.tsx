'use client';

/**
 * Lienzo del explorador de parches de deforestación (hotspots ≥1 ha) dentro de
 * la jurisdicción CORPOURABA. Componente cliente puro (ssr:false).
 *
 *  - Vista ACUMULADA (todos los periodos) o POR PERIODO (uno, con línea de tiempo).
 *  - Línea de tiempo visual: mini-gráfica de barras por año (altura = deforestación),
 *    barras clicables + barra deslizante + reproducción automática (timelapse).
 *  - Filtro por municipio y capas de contexto de la cartografía oficial.
 *  - Panel de estadísticas de fragmentación (conteo, área, tamaños, por periodo).
 *  - Renderizado en canvas para manejar con fluidez miles de polígonos.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import type * as GeoJSONNS from 'geojson';
import L from 'leaflet';
import { GeoJSON as CapaGeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet';
import { BarChart3, Layers, Maximize2, Pause, Play } from 'lucide-react';
import clsx from 'clsx';
import {
  getCapa,
  getCapas,
  getMunicipios,
  getParches,
  getParchesResumen,
  getPeriodos,
  urlDescarga,
  type ParchesMeta,
  type ResumenPeriodo,
} from '@/lib/api';
import type { Periodo } from '@/lib/types';
import { fmtHa, fmtNum } from '@/lib/format';
import Loader from '@/components/ui/Loader';

const TESELA_CLARO = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
const TESELA_OSCURO = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const ATRIBUCION = '© OpenStreetMap · © CARTO';
const CENTRO: [number, number] = [7.5, -76.4];

// Estilos por capa de contexto de la cartografía oficial (colores distinguibles).
const ESTILO_CAPAS: Record<string, L.PathOptions> = {
  areas_protegidas: { color: '#15803D', weight: 1, fillColor: '#22C55E', fillOpacity: 0.18 },
  areas_protegidas_oficial: { color: '#15803D', weight: 1.2, fillColor: '#22C55E', fillOpacity: 0.14 },
  ley_segunda: { color: '#0F766E', weight: 1, fillColor: '#14B8A6', fillOpacity: 0.14 },
  ecosistemas_estrategicos: { color: '#0891B2', weight: 1, fillColor: '#22D3EE', fillOpacity: 0.16 },
  zonificacion_conflicto: { color: '#9333EA', weight: 1, fillColor: '#C084FC', fillOpacity: 0.16 },
  resguardos: { color: '#7C3AED', weight: 1, fillColor: '#A78BFA', fillOpacity: 0.16 },
  resguardos_oficial: { color: '#7C3AED', weight: 1.2, fillColor: '#A78BFA', fillOpacity: 0.14 },
  consejos: { color: '#B45309', weight: 1, fillColor: '#F59E0B', fillOpacity: 0.16 },
  comunidades_negras_oficial: { color: '#B45309', weight: 1.2, fillColor: '#F59E0B', fillOpacity: 0.14 },
  cuencas: { color: '#1D4ED8', weight: 1, fillColor: '#60A5FA', fillOpacity: 0.12 },
  pomcas: { color: '#1E40AF', weight: 1, fillColor: '#3B82F6', fillOpacity: 0.12 },
  titulos_mineros: { color: '#78350F', weight: 1, fillColor: '#B45309', fillOpacity: 0.18 },
  pdet: { color: '#9333EA', weight: 1, fillColor: '#C084FC', fillOpacity: 0.1 },
};
const ESTILO_CAPA_DEFECTO: L.PathOptions = {
  color: '#4B5563',
  weight: 1,
  fillColor: '#9CA3AF',
  fillOpacity: 0.14,
};

// Rampa temporal (12 periodos): teal antiguo → magenta/rojo reciente.
// Se usa en el modo "Ver todo" para distinguir el año de cada polígono.
const RAMPA_TEMPORAL = [
  '#0D9488', '#0EA5A0', '#22C55E', '#84CC16', '#EAB308', '#F59E0B',
  '#F97316', '#EF4444', '#DC2626', '#B91C1C', '#9F1239', '#831843',
];
// Rojo de deforestación para el modo "Por periodo" (un solo año a la vez).
const COLOR_DEFORESTACION = '#DC2626';

function useTemaOscuro(): boolean {
  const [oscuro, setOscuro] = useState(false);
  useEffect(() => {
    const el = document.documentElement;
    const leer = () => setOscuro(el.classList.contains('dark'));
    leer();
    const obs = new MutationObserver(leer);
    obs.observe(el, { attributes: true, attributeFilter: ['class'] });
    return () => obs.disconnect();
  }, []);
  return oscuro;
}

function ControlAjuste({ bounds, senal }: { bounds: L.LatLngBoundsExpression | null; senal: number }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [20, 20] });
  }, [senal, bounds, map]);
  return null;
}

type Vista = 'acumulado' | 'periodo';

export default function LienzoParches() {
  const oscuro = useTemaOscuro();
  const mapaRef = useRef<L.Map | null>(null);

  const [periodos, setPeriodos] = useState<Periodo[]>([]);
  const [municipiosFc, setMunicipiosFc] = useState<GeoJSONNS.FeatureCollection | null>(null);
  const [municipios, setMunicipios] = useState<{ codigo: string; nombre: string }[]>([]);

  const [vista, setVista] = useState<Vista>('periodo');
  const [periodoSel, setPeriodoSel] = useState('2002-2004');
  const [municipioSel, setMunicipioSel] = useState('');
  // Resumen ligero (conteo y ha por periodo) para la línea de tiempo visual.
  const [resumenPeriodos, setResumenPeriodos] = useState<ResumenPeriodo[]>([]);
  const [reproduciendo, setReproduciendo] = useState(false);
  const [panelStats, setPanelStats] = useState(true);
  const [ajusteSenal, setAjusteSenal] = useState(0);

  // Capas de contexto de la cartografía oficial (prender/apagar en el visor)
  const [capasCatalogo, setCapasCatalogo] = useState<{ id: string; nombre: string; unidades: number }[]>([]);
  const [capasActivas, setCapasActivas] = useState<string[]>([]);
  const [capasGeo, setCapasGeo] = useState<Record<string, GeoJSONNS.FeatureCollection>>({});
  const [panelCapas, setPanelCapas] = useState(false);

  function toggleCapa(id: string) {
    setCapasActivas((prev) => (prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]));
  }

  const [parches, setParches] = useState<(GeoJSONNS.FeatureCollection & { metadata: ParchesMeta }) | null>(null);
  const [cargando, setCargando] = useState(true);

  // Índice de ano_inicio por periodo, para el gradiente temporal.
  const anoIndex = useMemo(() => {
    const conHotspots = periodos.filter((p) => p.tiene_hotspots).sort((a, b) => a.ano_inicio - b.ano_inicio);
    const m = new Map<string, number>();
    conHotspots.forEach((p, i) => m.set(p.id, i));
    return m;
  }, [periodos]);
  const totalPeriodos = anoIndex.size || 1;

  // Carga inicial
  useEffect(() => {
    (async () => {
      try {
        const [ps, mun, cat] = await Promise.all([getPeriodos(), getMunicipios(), getCapas()]);
        setPeriodos(ps);
        setMunicipiosFc(mun);
        // Se muestran solo las capas oficiales de áreas protegidas, resguardos
        // y consejos; se ocultan las derivadas del paquete de monitoreo
        // ('areas_protegidas', 'resguardos', 'consejos') por ser redundantes
        // con las de la cartografía oficial.
        const OCULTAS = new Set(['areas_protegidas', 'resguardos', 'consejos']);
        setCapasCatalogo(cat.capas.filter((c) => !OCULTAS.has(c.id)));
        setMunicipios(
          (mun.features ?? [])
            .map((f) => ({
              codigo: String(f.properties?.codigo_dane ?? ''),
              nombre: String(f.properties?.nombre ?? ''),
            }))
            .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')),
        );
      } catch (e) {
        console.error('Error base del visor', e);
      }
    })();
  }, []);

  // Descarga perezosa del GeoJSON de cada capa al activarla
  useEffect(() => {
    capasActivas
      .filter((id) => !capasGeo[id])
      .forEach((id) => {
        getCapa(id)
          .then((fc) => setCapasGeo((prev) => ({ ...prev, [id]: fc })))
          .catch((e) => console.error(`Error capa ${id}`, e));
      });
  }, [capasActivas, capasGeo]);

  // Carga de parches según filtros
  useEffect(() => {
    let vivo = true;
    setCargando(true);
    getParches({
      periodo: vista === 'periodo' ? periodoSel : undefined,
      municipio: municipioSel || undefined,
    })
      .then((fc) => {
        if (vivo) setParches(fc);
      })
      .catch((e) => console.error('Error /parches', e))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, [vista, periodoSel, municipioSel]);

  // Resumen por periodo para la línea de tiempo (se reajusta al municipio).
  useEffect(() => {
    let vivo = true;
    getParchesResumen(municipioSel || undefined)
      .then((r) => vivo && setResumenPeriodos(r.por_periodo))
      .catch((e) => console.error('Error /parches/resumen', e));
    return () => {
      vivo = false;
    };
  }, [municipioSel]);

  // Timelapse en vista por periodo
  useEffect(() => {
    if (!reproduciendo || vista !== 'periodo') return;
    const ids = periodos.filter((p) => p.tiene_hotspots).map((p) => p.id);
    const t = setInterval(() => {
      setPeriodoSel((actual) => {
        const i = ids.indexOf(actual);
        return ids[(i + 1) % ids.length];
      });
    }, 1500);
    return () => clearInterval(t);
  }, [reproduciendo, vista, periodos]);

  const boundsMunicipios = useMemo<L.LatLngBoundsExpression | null>(() => {
    if (!municipiosFc) return null;
    try {
      return L.geoJSON(municipiosFc).getBounds();
    } catch {
      return null;
    }
  }, [municipiosFc]);

  // Estadísticas de tamaño derivadas de los parches cargados
  const stats = useMemo(() => {
    if (!parches) return null;
    const has = parches.features
      .map((f) => Number(f.properties?.ha ?? 0))
      .sort((a, b) => a - b);
    const n = has.length;
    const total = has.reduce((s, v) => s + v, 0);
    const mediana = n ? has[Math.floor(n / 2)] : 0;
    const max = n ? has[n - 1] : 0;
    const clases = [
      { etiqueta: '1–2 ha', n: has.filter((h) => h < 2).length },
      { etiqueta: '2–5 ha', n: has.filter((h) => h >= 2 && h < 5).length },
      { etiqueta: '5–10 ha', n: has.filter((h) => h >= 5 && h < 10).length },
      { etiqueta: '10–20 ha', n: has.filter((h) => h >= 10 && h < 20).length },
      { etiqueta: '>20 ha', n: has.filter((h) => h >= 20).length },
    ];
    return { n, total, media: n ? total / n : 0, mediana, max, clases };
  }, [parches]);

  const claveParches = `${vista}-${periodoSel}-${municipioSel}`;

  const periodosConHotspots = periodos.filter((p) => p.tiene_hotspots);

  // Derivados para la línea de tiempo visual (barras por año).
  const haPorPeriodo = useMemo(
    () => new Map(resumenPeriodos.map((p) => [p.periodo, p.ha])),
    [resumenPeriodos],
  );
  const nPorPeriodo = useMemo(
    () => new Map(resumenPeriodos.map((p) => [p.periodo, p.n])),
    [resumenPeriodos],
  );
  const maxHaLinea = useMemo(
    () => Math.max(...resumenPeriodos.map((p) => p.ha), 1),
    [resumenPeriodos],
  );

  return (
    <div className="relative h-[calc(100vh-4rem)] w-full overflow-hidden">
      <MapContainer
        center={CENTRO}
        zoom={8}
        className="h-full w-full"
        preferCanvas
        ref={(m) => {
          if (m) mapaRef.current = m;
        }}
      >
        <TileLayer url={oscuro ? TESELA_OSCURO : TESELA_CLARO} attribution={ATRIBUCION} subdomains="abcd" />
        <ControlAjuste bounds={boundsMunicipios} senal={ajusteSenal} />

        {/* Contorno de la jurisdicción (referencia) */}
        {municipiosFc && (
          <CapaGeoJSON
            data={municipiosFc}
            style={() => ({ color: oscuro ? '#7BC796' : '#175E3A', weight: 1, fill: false, opacity: 0.5 })}
            interactive={false}
          />
        )}

        {/* Capas de contexto de la cartografía oficial (bajo la deforestación) */}
        {capasActivas
          .filter((id) => capasGeo[id])
          .map((id) => (
            <CapaGeoJSON
              key={`capa-${id}`}
              data={capasGeo[id]}
              style={() => ESTILO_CAPAS[id] ?? ESTILO_CAPA_DEFECTO}
              onEachFeature={(f, layer) => {
                const props = f.properties ?? {};
                const nombre = props.nombre ?? props.nomb_cuenc ?? props.categoria ?? 'Unidad';
                const defo = props.deforestacion_ha_total ?? props.deforestacion_ha_ultimo_periodo;
                layer.bindPopup(
                  `<strong>${nombre}</strong>` +
                    (props.categoria ? `<br/>${props.categoria}` : '') +
                    (props.tipo ? `<br/>${props.tipo}` : '') +
                    (props.pueblo ? `<br/>Pueblo: ${props.pueblo}` : '') +
                    (defo != null ? `<br/>Deforestación: ${fmtHa(Number(defo))}` : ''),
                );
              }}
            />
          ))}

        {/* Polígonos de deforestación */}
        {parches && (
          <CapaGeoJSON
            key={claveParches}
            data={parches}
            style={(f) => {
              const pid = String(f?.properties?.periodo ?? '');
              // "Ver todo": cada parche se colorea por su año (gradiente temporal).
              // "Por periodo": todos son del mismo año → rojo de deforestación.
              const color =
                vista === 'acumulado'
                  ? RAMPA_TEMPORAL[Math.round(((anoIndex.get(pid) ?? 0) / (totalPeriodos - 1 || 1)) * (RAMPA_TEMPORAL.length - 1))]
                  : COLOR_DEFORESTACION;
              return { color, weight: 0.3, fillColor: color, fillOpacity: 0.8 };
            }}
            onEachFeature={(f, layer) => {
              const p = f.properties ?? {};
              layer.bindTooltip(
                `<strong>${p.municipio ?? 'Polígono'}</strong><br/>${p.periodo}<br/>${fmtHa(Number(p.ha ?? 0))}`,
                { sticky: true },
              );
            }}
          />
        )}
      </MapContainer>

      {/* ── Controles superiores ────────────────────────────────────────── */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-[500] flex flex-wrap items-start justify-between gap-2 p-3">
        <div className="pointer-events-auto w-64 rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/95 p-3 shadow-lg backdrop-blur">
          <p className="font-display text-sm font-semibold">Visor de deforestación</p>
          <div className="mt-2">
            <GrupoBotones
              valor={vista}
              onCambio={(v) => setVista(v as Vista)}
              opciones={[
                { valor: 'periodo', etiqueta: 'Un año a la vez' },
                { valor: 'acumulado', etiqueta: 'Ver todo' },
              ]}
            />
          </div>
          <p className="mt-1.5 text-[11px] leading-snug text-[color:var(--tinta-suave)]">
            {vista === 'periodo'
              ? 'Desliza la línea de tiempo de abajo o toca una barra para ver ese año.'
              : 'Todos los años a la vez, coloreados según la fecha.'}
          </p>

          <label className="mt-3 block text-[11px] font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
            Municipio
          </label>
          <select
            value={municipioSel}
            onChange={(e) => setMunicipioSel(e.target.value)}
            className="mt-1 w-full rounded-lg border border-[color:var(--borde)] bg-[color:var(--fondo)] px-2 py-1.5 text-xs"
          >
            <option value="">Toda la jurisdicción</option>
            {municipios.map((m) => (
              <option key={m.codigo} value={m.nombre}>
                {m.nombre}
              </option>
            ))}
          </select>
        </div>

        <div className="pointer-events-auto flex gap-2">
          <button
            type="button"
            onClick={() => setAjusteSenal((s) => s + 1)}
            className="flex items-center gap-1.5 rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/90 px-3 py-2 text-xs font-medium shadow-lg backdrop-blur hover:border-bosque-300"
            aria-label="Ajustar a la jurisdicción"
          >
            <Maximize2 className="h-4 w-4" />
            <span className="hidden sm:inline">Ajustar</span>
          </button>
          <button
            type="button"
            onClick={() => setPanelCapas((v) => !v)}
            aria-expanded={panelCapas}
            className={clsx(
              'flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-medium shadow-lg backdrop-blur',
              panelCapas ? 'border-bosque-400 bg-bosque-600 text-white' : 'border-[color:var(--borde)] bg-[color:var(--superficie)]/90 hover:border-bosque-300',
            )}
          >
            <Layers className="h-4 w-4" />
            <span className="hidden sm:inline">Capas</span>
            {capasActivas.length > 0 && (
              <span className="ml-0.5 rounded-full bg-alerta-500 px-1.5 text-[10px] font-semibold text-white">
                {capasActivas.length}
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => setPanelStats((v) => !v)}
            className={clsx(
              'flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-medium shadow-lg backdrop-blur',
              panelStats ? 'border-bosque-400 bg-bosque-600 text-white' : 'border-[color:var(--borde)] bg-[color:var(--superficie)]/90 hover:border-bosque-300',
            )}
          >
            <BarChart3 className="h-4 w-4" />
            <span className="hidden sm:inline">Datos</span>
          </button>
        </div>
      </div>

      {/* ── Panel de capas de la cartografía oficial ────────────────────── */}
      {panelCapas && (
        <div className="pointer-events-auto absolute right-3 top-[4.5rem] z-[600] max-h-[70vh] w-64 overflow-y-auto rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/95 p-3 shadow-2xl backdrop-blur">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
            Capas de la cartografía
          </p>
          {capasCatalogo.length === 0 && (
            <p className="text-[11px] italic text-[color:var(--tinta-suave)]">Cargando catálogo…</p>
          )}
          {capasCatalogo.map((c) => (
            <label key={c.id} className="mb-1.5 flex cursor-pointer items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={capasActivas.includes(c.id)}
                onChange={() => toggleCapa(c.id)}
                className="accent-bosque-600"
              />
              <span
                className="h-3 w-3 shrink-0 rounded-sm border border-black/10"
                style={{ backgroundColor: (ESTILO_CAPAS[c.id]?.fillColor as string) ?? '#9CA3AF' }}
                aria-hidden="true"
              />
              <span className="flex-1">{c.nombre}</span>
              <span className="text-[10px] text-[color:var(--tinta-suave)]">{c.unidades}</span>
            </label>
          ))}
          {capasActivas.length > 0 && (
            <button
              type="button"
              onClick={() => setCapasActivas([])}
              className="mt-1 w-full rounded-full border border-[color:var(--borde)] py-1 text-[11px] font-medium hover:border-bosque-300"
            >
              Apagar todas
            </button>
          )}
          <p className="mt-2 border-t border-[color:var(--borde)] pt-2 text-[10px] leading-snug text-[color:var(--tinta-suave)]">
            Active una o varias capas para verlas bajo la deforestación. Haga clic en una unidad para su detalle.
          </p>
        </div>
      )}

      {/* ── Leyenda (se adapta al modo) ─────────────────────────────────── */}
      <div className="pointer-events-auto absolute bottom-24 left-3 z-[500] w-56 rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/92 p-3 text-xs shadow-lg backdrop-blur">
        {vista === 'acumulado' ? (
          <>
            <p className="mb-1.5 font-semibold">Año de la deforestación</p>
            <div className="flex h-3 w-full overflow-hidden rounded-sm">
              {RAMPA_TEMPORAL.map((c) => (
                <span key={c} className="flex-1" style={{ backgroundColor: c }} />
              ))}
            </div>
            <div className="mt-1 flex justify-between text-[10px] text-[color:var(--tinta-suave)]">
              <span>2000</span>
              <span>2024</span>
            </div>
          </>
        ) : (
          <div className="flex items-center gap-2">
            <span className="h-3.5 w-5 shrink-0 rounded-sm" style={{ backgroundColor: COLOR_DEFORESTACION }} />
            <span className="text-[color:var(--tinta-suave)]">Deforestación en {periodoSel}</span>
          </div>
        )}
      </div>

      {/* ── Línea de tiempo visual (solo vista por periodo) ─────────────── */}
      {vista === 'periodo' && (
        <div className="pointer-events-auto absolute inset-x-3 bottom-3 z-[500] rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/95 px-3 py-2.5 shadow-lg backdrop-blur">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setReproduciendo((v) => !v)}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-bosque-600 text-white hover:bg-bosque-700"
              aria-label={reproduciendo ? 'Pausar' : 'Reproducir la evolución año a año'}
              title={reproduciendo ? 'Pausar' : 'Reproducir'}
            >
              {reproduciendo ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
            </button>
            <div className="min-w-0 flex-1">
              {/* Año seleccionado + su cifra */}
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-display text-lg font-semibold leading-none">{periodoSel}</span>
                <span className="text-[11px] tabular-nums text-[color:var(--tinta-suave)]">
                  {nPorPeriodo.has(periodoSel)
                    ? `${fmtNum(nPorPeriodo.get(periodoSel) ?? 0)} focos · ${fmtHa(haPorPeriodo.get(periodoSel) ?? 0)}`
                    : '—'}
                </span>
              </div>
              {/* Mini-gráfica de barras por año: altura = deforestación; toca para saltar */}
              <div className="mt-1.5 flex h-9 items-end gap-[3px]">
                {periodosConHotspots.map((p) => {
                  const activo = p.id === periodoSel;
                  const ha = haPorPeriodo.get(p.id) ?? 0;
                  const alto = Math.max((ha / maxHaLinea) * 100, 8);
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setPeriodoSel(p.id)}
                      title={`${p.id}: ${fmtNum(nPorPeriodo.get(p.id) ?? 0)} focos, ${fmtHa(ha)}`}
                      aria-label={`Ver ${p.id}`}
                      className="flex h-full flex-1 items-end"
                    >
                      <span
                        className="w-full rounded-t-sm transition-all"
                        style={{
                          height: `${alto}%`,
                          backgroundColor: activo
                            ? COLOR_DEFORESTACION
                            : oscuro
                              ? '#4B5563'
                              : '#D1D5DB',
                        }}
                      />
                    </button>
                  );
                })}
              </div>
              {/* Barra deslizante por año + extremos temporales */}
              <input
                type="range"
                min={0}
                max={Math.max(periodosConHotspots.length - 1, 0)}
                value={Math.max(periodosConHotspots.findIndex((p) => p.id === periodoSel), 0)}
                onChange={(e) => {
                  const p = periodosConHotspots[Number(e.target.value)];
                  if (p) setPeriodoSel(p.id);
                }}
                className="mt-1 w-full accent-bosque-600"
                aria-label="Año de la deforestación"
              />
              <div className="flex justify-between text-[10px] text-[color:var(--tinta-suave)]">
                <span>{periodosConHotspots[0]?.ano_inicio ?? ''}</span>
                <span>{periodosConHotspots[periodosConHotspots.length - 1]?.ano_inicio ?? ''}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Panel de estadísticas ───────────────────────────────────────── */}
      {panelStats && stats && (
        <aside className="pointer-events-auto absolute right-3 top-24 z-[500] w-64 rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/95 p-4 shadow-2xl backdrop-blur">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
            {vista === 'acumulado' ? 'Acumulado 2000–2024' : `Periodo ${periodoSel}`}
            {municipioSel ? ` · ${municipioSel}` : ''}
          </p>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <Metrica etiqueta="Polígonos" valor={fmtNum(stats.n)} />
            <Metrica etiqueta="Área total" valor={fmtHa(stats.total)} />
            <Metrica etiqueta="Tamaño medio" valor={`${fmtNum(stats.media, 1)} ha`} />
            <Metrica etiqueta="Mayor polígono" valor={fmtHa(stats.max)} />
          </div>

          <p className="mt-3 text-[11px] font-semibold text-[color:var(--tinta-suave)]">Distribución por tamaño</p>
          <div className="mt-1 space-y-1">
            {stats.clases.map((c) => {
              const pct = stats.n ? (c.n / stats.n) * 100 : 0;
              return (
                <div key={c.etiqueta} className="flex items-center gap-2 text-[11px]">
                  <span className="w-14 shrink-0 text-[color:var(--tinta-suave)]">{c.etiqueta}</span>
                  <span className="h-2.5 flex-1 overflow-hidden rounded-full bg-[color:var(--borde)]">
                    <span className="block h-full rounded-full bg-alerta-500" style={{ width: `${pct}%` }} />
                  </span>
                  <span className="w-9 shrink-0 text-right tabular-nums">{fmtNum(c.n)}</span>
                </div>
              );
            })}
          </div>

          {vista === 'acumulado' && parches?.metadata.por_periodo && (
            <>
              <p className="mt-3 text-[11px] font-semibold text-[color:var(--tinta-suave)]">Polígonos por periodo</p>
              <div className="mt-1 space-y-0.5">
                {parches.metadata.por_periodo.map((p) => {
                  const maxN = Math.max(...parches.metadata.por_periodo.map((x) => x.n), 1);
                  return (
                    <button
                      key={p.periodo}
                      type="button"
                      onClick={() => {
                        setVista('periodo');
                        setPeriodoSel(p.periodo);
                      }}
                      className="flex w-full items-center gap-2 text-[10px] hover:opacity-80"
                      title={`Ver ${p.periodo}`}
                    >
                      <span className="w-14 shrink-0 text-left text-[color:var(--tinta-suave)]">{p.periodo}</span>
                      <span className="h-2 flex-1 overflow-hidden rounded-full bg-[color:var(--borde)]">
                        <span
                          className="block h-full rounded-full"
                          style={{
                            width: `${(p.n / maxN) * 100}%`,
                            backgroundColor: RAMPA_TEMPORAL[Math.round(((anoIndex.get(p.periodo) ?? 0) / (totalPeriodos - 1 || 1)) * (RAMPA_TEMPORAL.length - 1))],
                          }}
                        />
                      </span>
                      <span className="w-8 shrink-0 text-right tabular-nums">{p.n}</span>
                    </button>
                  );
                })}
              </div>
            </>
          )}

          <a
            href={
              vista === 'periodo'
                ? urlDescarga(`hotspots/${periodoSel}.geojson`)
                : `${''}`
            }
            className={clsx(
              'mt-3 block rounded-full px-3 py-1.5 text-center text-xs font-medium',
              vista === 'periodo'
                ? 'border border-[color:var(--borde)] hover:border-bosque-300'
                : 'hidden',
            )}
          >
            Descargar GeoJSON del periodo
          </a>
          <p className="mt-3 text-[10px] leading-snug text-[color:var(--tinta-suave)]">
            Polígonos ≥1 ha de 12 de los 18 periodos (aprox. 65 % de la deforestación total; faltan el pico 2015-2016 y otros 5 periodos sin geometría).
          </p>
        </aside>
      )}

      {cargando && (
        <div className="pointer-events-none absolute inset-0 z-[600] flex items-center justify-center">
          <div className="rounded-full bg-[color:var(--superficie)]/90 px-4 py-2 shadow-lg backdrop-blur">
            <Loader texto="Cargando polígonos…" className="py-0" />
          </div>
        </div>
      )}
    </div>
  );
}

function GrupoBotones({
  valor,
  onCambio,
  opciones,
}: {
  valor: string;
  onCambio: (v: string) => void;
  opciones: { valor: string; etiqueta: string }[];
}) {
  return (
    <div className="flex overflow-hidden rounded-full border border-[color:var(--borde)]">
      {opciones.map((o) => (
        <button
          key={o.valor}
          type="button"
          onClick={() => onCambio(o.valor)}
          className={clsx(
            'px-2.5 py-1 text-[11px] font-medium transition-colors',
            valor === o.valor
              ? 'bg-bosque-600 text-white'
              : 'text-[color:var(--tinta-suave)] hover:bg-bosque-50 dark:hover:bg-bosque-900',
          )}
        >
          {o.etiqueta}
        </button>
      ))}
    </div>
  );
}

function Metrica({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div className="rounded-lg bg-[color:var(--fondo)] p-2">
      <p className="text-[10px] text-[color:var(--tinta-suave)]">{etiqueta}</p>
      <p className="font-display text-base font-semibold">{valor}</p>
    </div>
  );
}
