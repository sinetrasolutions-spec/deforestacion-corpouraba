'use client';

/**
 * Lienzo Leaflet del Observatorio (SPEC §8.2). Componente cliente puro
 * (se importa con ssr:false). Integra:
 *  - Coropletas de los 19 municipios por periodo y métrica (/choropleth).
 *  - Línea de tiempo de 18 periodos con timelapse (store zustand).
 *  - Tooltips + panel lateral de municipio con minigráfico de su serie.
 *  - Capas de contexto (/capas) + hotspots del periodo + frentes persistentes.
 *  - Leyenda dinámica, zoom inteligente y controles flotantes responsive.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type * as GeoJSONNS from 'geojson';
import type { Layer, LeafletMouseEvent, Map as LeafletMap, PathOptions } from 'leaflet';
import L from 'leaflet';
import {
  GeoJSON as CapaGeoJSON,
  MapContainer,
  TileLayer,
  useMap,
} from 'react-leaflet';
import {
  ChevronLeft,
  Layers,
  Maximize2,
  Pause,
  Play,
  X,
} from 'lucide-react';
import clsx from 'clsx';
import {
  API_URL,
  getCapa,
  getCapas,
  getChoropleth,
  getMunicipios,
  getPeriodos,
  getRanking,
  getSerie,
  urlDescarga,
} from '@/lib/api';
import type { Choropleth, ItemRanking, Periodo } from '@/lib/types';
import { COLOR_SIN_DATOS, colorPara, RAMPA_DEFORESTACION } from '@/lib/colores';
import { fmtHa, fmtNum } from '@/lib/format';
import useAppStore from '@/store/useAppStore';
import Badge from '@/components/ui/Badge';
import Loader from '@/components/ui/Loader';

// Teselas CARTO (sin API key) — claro/oscuro según el tema activo.
const TESELA_CLARO = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
const TESELA_OSCURO = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const ATRIBUCION = '© OpenStreetMap · © CARTO';
const CENTRO_URABA: [number, number] = [7.5, -76.4];

// Estilos por capa de contexto (colores distinguibles y tenues).
const ESTILO_CAPAS: Record<string, PathOptions> = {
  areas_protegidas: { color: '#15803D', weight: 1, fillColor: '#22C55E', fillOpacity: 0.18 },
  areas_protegidas_oficial: { color: '#15803D', weight: 1.2, fillColor: '#22C55E', fillOpacity: 0.14 },
  pomcas: { color: '#1E40AF', weight: 1, fillColor: '#3B82F6', fillOpacity: 0.12 },
  ley_segunda: { color: '#0F766E', weight: 1, fillColor: '#14B8A6', fillOpacity: 0.14 },
  ecosistemas_estrategicos: { color: '#0891B2', weight: 1, fillColor: '#22D3EE', fillOpacity: 0.16 },
  resguardos: { color: '#7C3AED', weight: 1, fillColor: '#A78BFA', fillOpacity: 0.16 },
  resguardos_oficial: { color: '#7C3AED', weight: 1.2, fillColor: '#A78BFA', fillOpacity: 0.14 },
  consejos: { color: '#B45309', weight: 1, fillColor: '#F59E0B', fillOpacity: 0.16 },
  comunidades_negras_oficial: { color: '#B45309', weight: 1.2, fillColor: '#F59E0B', fillOpacity: 0.14 },
  cuencas: { color: '#1D4ED8', weight: 1, fillColor: '#60A5FA', fillOpacity: 0.12 },
  pdet: { color: '#9333EA', weight: 1, fillColor: '#C084FC', fillOpacity: 0.1 },
};
const ESTILO_CAPA_DEFECTO: PathOptions = {
  color: '#4B5563',
  weight: 1,
  fillColor: '#9CA3AF',
  fillOpacity: 0.14,
};

interface PropsMunicipio {
  codigo_dane: string;
  nombre: string;
  subregion: string;
  area_municipio_ha: number;
}

/** Detecta el tema oscuro observando la clase del <html>. */
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

/** Ajusta el mapa a los límites de la jurisdicción cuando se solicita. */
function ControlAjuste({
  bounds,
  senal,
}: {
  bounds: L.LatLngBoundsExpression | null;
  senal: number;
}) {
  const map = useMap();
  useEffect(() => {
    if (bounds) map.fitBounds(bounds, { padding: [24, 24] });
  }, [senal, bounds, map]);
  return null;
}

export default function LienzoMapa() {
  const {
    periodoActivo,
    metrica,
    reproduciendo,
    capasActivas,
    municipioSeleccionado,
    incluirEstimados,
    setPeriodo,
    setMetrica,
    toggleReproduccion,
    toggleCapa,
    setMunicipio,
    setIncluirEstimados,
  } = useAppStore();

  const oscuro = useTemaOscuro();
  const mapaRef = useRef<LeafletMap | null>(null);

  const [periodos, setPeriodos] = useState<Periodo[]>([]);
  const [municipios, setMunicipios] = useState<GeoJSONNS.FeatureCollection | null>(null);
  const [choropleth, setChoropleth] = useState<Choropleth | null>(null);
  const [capasCatalogo, setCapasCatalogo] = useState<{ id: string; nombre: string; unidades: number }[]>([]);
  const [capasGeo, setCapasGeo] = useState<Record<string, GeoJSONNS.FeatureCollection>>({});
  const [hotspots, setHotspots] = useState<GeoJSONNS.FeatureCollection | null>(null);
  const [hotspotsVacio, setHotspotsVacio] = useState(false);
  const [recurrencia, setRecurrencia] = useState<GeoJSONNS.FeatureCollection | null>(null);

  const [panelCapas, setPanelCapas] = useState(false);
  const [ajusteSenal, setAjusteSenal] = useState(0);
  const [cargando, setCargando] = useState(true);

  // ── Carga inicial: periodos, municipios y catálogo de capas ──────────────
  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const [ps, mun, cat] = await Promise.all([getPeriodos(), getMunicipios(), getCapas()]);
        if (!vivo) return;
        setPeriodos(ps);
        setMunicipios(mun);
        // Solo capas oficiales: se ocultan las derivadas del paquete de
        // monitoreo, redundantes con la cartografía oficial.
        const OCULTAS = new Set(['areas_protegidas', 'resguardos', 'consejos']);
        setCapasCatalogo(cat.capas.filter((c) => !OCULTAS.has(c.id)));
      } catch (e) {
        console.error('Error cargando datos base del mapa', e);
      } finally {
        if (vivo) setCargando(false);
      }
    })();
    return () => {
      vivo = false;
    };
  }, []);

  // ── Coropletas del periodo/métrica activos ───────────────────────────────
  useEffect(() => {
    let vivo = true;
    getChoropleth(periodoActivo, metrica)
      .then((c) => vivo && setChoropleth(c))
      .catch((e) => console.error('Error /choropleth', e));
    return () => {
      vivo = false;
    };
  }, [periodoActivo, metrica]);

  // ── Hotspots del periodo (si la capa está activa) ────────────────────────
  useEffect(() => {
    if (!capasActivas.includes('hotspots')) {
      setHotspots(null);
      setHotspotsVacio(false);
      return;
    }
    let vivo = true;
    setHotspotsVacio(false);
    fetch(`${API_URL}/api/v1/hotspots/${encodeURIComponent(periodoActivo)}`)
      .then((r) => (r.status === 404 ? null : r.json()))
      .then((fc) => {
        if (!vivo) return;
        if (!fc) {
          setHotspots(null);
          setHotspotsVacio(true);
        } else {
          setHotspots(fc as GeoJSONNS.FeatureCollection);
        }
      })
      .catch(() => vivo && setHotspots(null));
    return () => {
      vivo = false;
    };
  }, [capasActivas, periodoActivo]);

  // ── Frentes persistentes (capa de análisis, se pide una sola vez) ────────
  useEffect(() => {
    if (!capasActivas.includes('recurrencia') || recurrencia) return;
    fetch(`${API_URL}/api/v1/analisis/geo/recurrencia`)
      .then((r) => (r.ok ? r.json() : null))
      .then((fc) => fc && setRecurrencia(fc as GeoJSONNS.FeatureCollection))
      .catch(() => undefined);
  }, [capasActivas, recurrencia]);

  // ── Descarga perezosa de overlays de contexto al activarlos ──────────────
  useEffect(() => {
    const especiales = new Set(['hotspots', 'recurrencia']);
    capasActivas
      .filter((id) => !especiales.has(id) && !capasGeo[id])
      .forEach((id) => {
        getCapa(id)
          .then((fc) => setCapasGeo((prev) => ({ ...prev, [id]: fc })))
          .catch((e) => console.error(`Error capa ${id}`, e));
      });
  }, [capasActivas, capasGeo]);

  // ── Timelapse: avanza cada 1,4 s en bucle ────────────────────────────────
  useEffect(() => {
    if (!reproduciendo || periodos.length === 0) return;
    const t = setInterval(() => {
      const ids = periodos.map((p) => p.id);
      const i = ids.indexOf(useAppStore.getState().periodoActivo);
      setPeriodo(ids[(i + 1) % ids.length]);
    }, 1400);
    return () => clearInterval(t);
  }, [reproduciendo, periodos, setPeriodo]);

  const boundsMunicipios = useMemo<L.LatLngBoundsExpression | null>(() => {
    if (!municipios) return null;
    try {
      return L.geoJSON(municipios).getBounds();
    } catch {
      return null;
    }
  }, [municipios]);

  const periodoActual = periodos.find((p) => p.id === periodoActivo);
  const esEstimadoPeriodo = useMemo(() => {
    if (!choropleth) return false;
    return Object.values(choropleth.valores).some((v) => v.estimado);
  }, [choropleth]);

  // ── Estilo de cada municipio según su valor en el periodo ────────────────
  const estiloMunicipio = useCallback(
    (feature?: GeoJSONNS.Feature): PathOptions => {
      const dane = String(feature?.properties?.codigo_dane ?? '');
      const valorObj = choropleth?.valores[dane];
      const valor = valorObj
        ? metrica === 'hectareas'
          ? valorObj.hectareas
          : valorObj.hectareas_anuales
        : undefined;
      const color = choropleth ? colorPara(valor, choropleth.breaks) : COLOR_SIN_DATOS;
      const seleccionado = dane === municipioSeleccionado;
      const estimado = Boolean(valorObj?.estimado);
      return {
        color: seleccionado ? '#111827' : '#ffffff',
        weight: seleccionado ? 2.5 : 1,
        fillColor: color,
        fillOpacity: valorObj ? (estimado ? 0.62 : 0.85) : 0.45,
        dashArray: estimado ? '4 3' : undefined,
      };
    },
    [choropleth, metrica, municipioSeleccionado],
  );

  // ── Interacción por municipio: tooltip, selección y zoom ─────────────────
  const alCrearMunicipio = useCallback(
    (feature: GeoJSONNS.Feature, layer: Layer) => {
      const p = feature.properties as unknown as PropsMunicipio;
      const valorObj = choropleth?.valores[p.codigo_dane];
      const ha = valorObj?.hectareas ?? 0;
      const hay = valorObj?.hectareas_anuales ?? 0;
      const est = valorObj?.estimado
        ? ' <span style="color:#b45309">(estimado)</span>'
        : '';
      layer.bindTooltip(
        `<strong>${p.nombre}</strong><br/>${periodoActivo}${est}<br/>` +
          `${fmtHa(ha)} · ${fmtNum(hay)} ha/año`,
        { sticky: true, direction: 'top' },
      );
      layer.on({
        click: () => setMunicipio(p.codigo_dane),
        dblclick: (e: LeafletMouseEvent) => {
          const capa = e.target as L.GeoJSON;
          if (mapaRef.current && 'getBounds' in capa) {
            mapaRef.current.fitBounds(capa.getBounds(), { padding: [40, 40] });
          }
        },
      });
    },
    [choropleth, periodoActivo, setMunicipio],
  );

  // Clave para forzar re-render del GeoJSON de municipios al cambiar estilos.
  const claveMunicipios = `${periodoActivo}-${metrica}-${municipioSeleccionado}-${choropleth?.periodo ?? ''}`;

  return (
    <div className="relative h-[calc(100vh-4rem)] w-full overflow-hidden">
      <MapContainer
        center={CENTRO_URABA}
        zoom={8}
        className="h-full w-full"
        zoomControl
        doubleClickZoom={false}
        ref={(m) => {
          if (m) mapaRef.current = m;
        }}
      >
        <TileLayer
          url={oscuro ? TESELA_OSCURO : TESELA_CLARO}
          attribution={ATRIBUCION}
          subdomains="abcd"
        />

        <ControlAjuste bounds={boundsMunicipios} senal={ajusteSenal} />

        {/* Overlays de contexto (debajo de los municipios) */}
        {capasActivas
          .filter((id) => capasGeo[id])
          .map((id) => (
            <CapaGeoJSON
              key={`capa-${id}`}
              data={capasGeo[id]}
              style={() => ESTILO_CAPAS[id] ?? ESTILO_CAPA_DEFECTO}
              onEachFeature={(f, layer) => {
                const props = f.properties ?? {};
                const nombre =
                  props.nombre ?? props.nomb_cuenc ?? props.categoria ?? 'Unidad';
                const defo = props.deforestacion_ha_total ?? props.deforestacion_ha_ultimo_periodo;
                layer.bindPopup(
                  `<strong>${nombre}</strong>` +
                    (props.categoria ? `<br/>${props.categoria}` : '') +
                    (props.pueblo ? `<br/>Pueblo: ${props.pueblo}` : '') +
                    (defo != null ? `<br/>Deforestación: ${fmtHa(Number(defo))}` : ''),
                );
              }}
            />
          ))}

        {/* Frentes persistentes de deforestación (celdas recurrentes) */}
        {capasActivas.includes('recurrencia') && recurrencia && (
          <CapaGeoJSON
            key="recurrencia"
            data={recurrencia}
            style={(f) => {
              const conteo = Number(f?.properties?.conteo_periodos ?? 0);
              const t = Math.min(conteo / 10, 1);
              return {
                color: '#7F1D1D',
                weight: 0.4,
                fillColor: '#DC2626',
                fillOpacity: 0.15 + t * 0.55,
              };
            }}
            onEachFeature={(f, layer) => {
              const p = f.properties ?? {};
              layer.bindPopup(
                `<strong>Frente persistente</strong><br/>` +
                  `${p.conteo_periodos} periodos con deforestación<br/>` +
                  `${fmtHa(Number(p.ha_acumuladas ?? 0))} acumuladas` +
                  (p.municipio ? `<br/>${p.municipio}` : ''),
              );
            }}
          />
        )}

        {/* Hotspots del periodo activo (polígonos de deforestación ≥1 ha) */}
        {capasActivas.includes('hotspots') && hotspots && (
          <CapaGeoJSON
            key={`hotspots-${periodoActivo}`}
            data={hotspots}
            style={() => ({ color: '#7F1D1D', weight: 0.6, fillColor: '#DC2626', fillOpacity: 0.6 })}
            onEachFeature={(f, layer) => {
              const p = f.properties ?? {};
              layer.bindTooltip(
                `Deforestación ${periodoActivo}<br/>${fmtHa(Number(p.ha ?? 0))}` +
                  (p.municipio ? `<br/>${p.municipio}` : ''),
                { sticky: true },
              );
            }}
          />
        )}

        {/* Municipios (coropletas) — encima de todo lo demás */}
        {municipios && (
          <CapaGeoJSON
            key={claveMunicipios}
            data={municipios}
            style={estiloMunicipio as (f?: GeoJSONNS.Feature) => PathOptions}
            onEachFeature={alCrearMunicipio}
          />
        )}
      </MapContainer>

      {/* ── Controles superiores: métrica + capas + ajustar ─────────────── */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-[500] flex flex-wrap items-start justify-between gap-2 p-3">
        <div className="pointer-events-auto rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/90 px-3 py-2 shadow-lg backdrop-blur">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
            Métrica
          </p>
          <div className="mt-1 flex gap-1">
            {(['hectareas', 'hectareas_anuales'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMetrica(m)}
                className={clsx(
                  'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                  metrica === m
                    ? 'bg-bosque-600 text-white'
                    : 'text-[color:var(--tinta-suave)] hover:bg-bosque-50 dark:hover:bg-bosque-900',
                )}
              >
                {m === 'hectareas' ? 'Hectáreas' : 'Ha/año'}
              </button>
            ))}
          </div>
        </div>

        <div className="pointer-events-auto flex gap-2">
          <button
            type="button"
            onClick={() => setAjusteSenal((s) => s + 1)}
            className="flex items-center gap-1.5 rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/90 px-3 py-2 text-xs font-medium shadow-lg backdrop-blur hover:border-bosque-300"
            aria-label="Ajustar el mapa a la jurisdicción"
          >
            <Maximize2 className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">Ajustar</span>
          </button>
          <button
            type="button"
            onClick={() => setPanelCapas((v) => !v)}
            aria-expanded={panelCapas}
            className={clsx(
              'flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-medium shadow-lg backdrop-blur',
              panelCapas
                ? 'border-bosque-400 bg-bosque-600 text-white'
                : 'border-[color:var(--borde)] bg-[color:var(--superficie)]/90 hover:border-bosque-300',
            )}
          >
            <Layers className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">Capas</span>
          </button>
        </div>
      </div>

      {/* ── Panel de capas ──────────────────────────────────────────────── */}
      {panelCapas && (
        <div className="pointer-events-auto absolute right-3 top-20 z-[600] w-64 rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/95 p-3 shadow-2xl backdrop-blur">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
            Capas del mapa
          </p>
          <ToggleCapa
            id="hotspots"
            etiqueta={`Deforestación (hotspots)${
              periodoActual && !periodoActual.tiene_hotspots ? ' — sin datos' : ''
            }`}
            activo={capasActivas.includes('hotspots')}
            onToggle={toggleCapa}
            color="#DC2626"
          />
          {hotspotsVacio && (
            <p className="mb-2 ml-6 text-[11px] italic text-[color:var(--tinta-suave)]">
              Sin polígonos para {periodoActivo}.
            </p>
          )}
          <ToggleCapa
            id="recurrencia"
            etiqueta="Frentes persistentes (≥3 periodos)"
            activo={capasActivas.includes('recurrencia')}
            onToggle={toggleCapa}
            color="#B91C1C"
          />
          <div className="my-2 border-t border-[color:var(--borde)]" />
          {capasCatalogo.map((c) => (
            <ToggleCapa
              key={c.id}
              id={c.id}
              etiqueta={`${c.nombre} (${c.unidades})`}
              activo={capasActivas.includes(c.id)}
              onToggle={toggleCapa}
              color={(ESTILO_CAPAS[c.id]?.fillColor as string) ?? '#9CA3AF'}
            />
          ))}
        </div>
      )}

      {/* ── Leyenda dinámica ────────────────────────────────────────────── */}
      {choropleth && (
        <div className="pointer-events-auto absolute bottom-24 left-3 z-[500] max-w-[15rem] rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/90 p-3 text-xs shadow-lg backdrop-blur sm:bottom-28">
          <p className="mb-1.5 font-semibold">
            {metrica === 'hectareas' ? 'Deforestación (ha)' : 'Deforestación (ha/año)'}
          </p>
          <div className="space-y-1">
            {RAMPA_DEFORESTACION.map((color, i) => {
              const desde = i === 0 ? 0 : choropleth.breaks[i - 1];
              const hasta = choropleth.breaks[i];
              return (
                <div key={color} className="flex items-center gap-2">
                  <span
                    className="h-3 w-5 shrink-0 rounded-sm"
                    style={{ backgroundColor: color }}
                    aria-hidden="true"
                  />
                  <span className="text-[color:var(--tinta-suave)]">
                    {fmtNum(desde)}–{hasta != null ? fmtNum(hasta) : '+'}
                  </span>
                </div>
              );
            })}
            <div className="flex items-center gap-2">
              <span
                className="h-3 w-5 shrink-0 rounded-sm"
                style={{ backgroundColor: COLOR_SIN_DATOS }}
                aria-hidden="true"
              />
              <span className="text-[color:var(--tinta-suave)]">Sin dato</span>
            </div>
          </div>
          {esEstimadoPeriodo && (
            <p className="mt-2 border-t border-[color:var(--borde)] pt-1.5">
              <Badge variante="estimado">periodo estimado</Badge>
            </p>
          )}
        </div>
      )}

      {/* ── Línea de tiempo + timelapse ─────────────────────────────────── */}
      <div className="pointer-events-auto absolute inset-x-3 bottom-3 z-[500] rounded-xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/92 px-3 py-2.5 shadow-lg backdrop-blur">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={toggleReproduccion}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-bosque-600 text-white transition-colors hover:bg-bosque-700"
            aria-label={reproduciendo ? 'Pausar animación' : 'Reproducir animación temporal'}
          >
            {reproduciendo ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-display text-lg font-semibold">{periodoActivo}</span>
              <span className="text-xs text-[color:var(--tinta-suave)]">
                {periodos.length > 0
                  ? `${periodos.findIndex((p) => p.id === periodoActivo) + 1} / ${periodos.length}`
                  : ''}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={Math.max(periodos.length - 1, 0)}
              value={Math.max(periodos.findIndex((p) => p.id === periodoActivo), 0)}
              onChange={(e) => {
                const p = periodos[Number(e.target.value)];
                if (p) setPeriodo(p.id);
              }}
              className="mt-1 w-full accent-bosque-600"
              aria-label="Seleccionar periodo"
            />
          </div>
          <label className="hidden shrink-0 items-center gap-1.5 text-xs text-[color:var(--tinta-suave)] sm:flex">
            <input
              type="checkbox"
              checked={incluirEstimados}
              onChange={(e) => setIncluirEstimados(e.target.checked)}
              className="accent-bosque-600"
            />
            estimados
          </label>
        </div>
      </div>

      {/* ── Panel lateral de municipio ──────────────────────────────────── */}
      {municipioSeleccionado && (
        <PanelMunicipio
          codigo={municipioSeleccionado}
          periodo={periodoActivo}
          incluirEstimados={incluirEstimados}
          alCerrar={() => setMunicipio(null)}
        />
      )}

      {cargando && (
        <div className="absolute inset-0 z-[700] flex items-center justify-center bg-[color:var(--fondo)]/70">
          <Loader texto="Cargando mapa…" />
        </div>
      )}
    </div>
  );
}

function ToggleCapa({
  id,
  etiqueta,
  activo,
  onToggle,
  color,
}: {
  id: string;
  etiqueta: string;
  activo: boolean;
  onToggle: (id: string) => void;
  color: string;
}) {
  return (
    <label className="mb-1.5 flex cursor-pointer items-center gap-2 text-xs">
      <input
        type="checkbox"
        checked={activo}
        onChange={() => onToggle(id)}
        className="accent-bosque-600"
      />
      <span
        className="h-3 w-3 shrink-0 rounded-sm border border-black/10"
        style={{ backgroundColor: color }}
        aria-hidden="true"
      />
      <span>{etiqueta}</span>
    </label>
  );
}

/** Panel lateral con la ficha del municipio seleccionado. */
function PanelMunicipio({
  codigo,
  periodo,
  incluirEstimados,
  alCerrar,
}: {
  codigo: string;
  periodo: string;
  incluirEstimados: boolean;
  alCerrar: () => void;
}) {
  const [serie, setSerie] = useState<{ periodo: string; ha: number; estimado: boolean }[]>([]);
  const [ficha, setFicha] = useState<{ municipio: string; subregion: string } | null>(null);
  const [ranking, setRanking] = useState<ItemRanking | null>(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    let vivo = true;
    setCargando(true);
    Promise.all([
      getSerie({ municipio: [codigo], clase: 'Deforestación', incluirEstimados: true }),
      getRanking(undefined, 19),
    ])
      .then(([s, r]) => {
        if (!vivo) return;
        const filas = s.data
          .slice()
          .sort((a, b) => a.ano_inicio - b.ano_inicio)
          .map((f) => ({ periodo: f.periodo, ha: f.hectareas_anuales, estimado: f.estimado }));
        setSerie(filas);
        if (s.data[0]) setFicha({ municipio: s.data[0].municipio, subregion: s.data[0].subregion });
        setRanking(r.data.find((it) => it.codigo_dane === codigo) ?? null);
      })
      .catch((e) => console.error('Error panel municipio', e))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, [codigo]);

  const maxHa = Math.max(...serie.map((s) => s.ha), 1);

  return (
    <aside className="pointer-events-auto absolute right-0 top-0 z-[650] flex h-full w-[22rem] max-w-[88vw] flex-col border-l border-[color:var(--borde)] bg-[color:var(--superficie)] shadow-2xl">
      <div className="flex items-center justify-between border-b border-[color:var(--borde)] p-4">
        <div>
          <p className="text-[11px] uppercase tracking-wider text-[color:var(--tinta-suave)]">
            Municipio
          </p>
          <h2 className="font-display text-xl font-semibold">{ficha?.municipio ?? codigo}</h2>
          {ficha && (
            <p className="text-sm text-[color:var(--tinta-suave)]">Subregión {ficha.subregion}</p>
          )}
        </div>
        <button
          type="button"
          onClick={alCerrar}
          className="flex h-8 w-8 items-center justify-center rounded-full border border-[color:var(--borde)] hover:bg-bosque-50 dark:hover:bg-bosque-900"
          aria-label="Cerrar panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {cargando ? (
          <Loader texto="Cargando ficha…" />
        ) : (
          <>
            {ranking && (
              <div className="mb-4 grid grid-cols-2 gap-2">
                <div className="rounded-xl bg-bosque-50 p-3 dark:bg-bosque-900/50">
                  <p className="text-[11px] text-[color:var(--tinta-suave)]">Posición regional</p>
                  <p className="font-display text-2xl font-semibold">#{ranking.posicion}</p>
                  <p className="text-[11px] text-[color:var(--tinta-suave)]">de 19 · acumulado</p>
                </div>
                <div className="rounded-xl bg-alerta-50 p-3 dark:bg-alerta-900/40">
                  <p className="text-[11px] text-[color:var(--tinta-suave)]">Total 2000–2024</p>
                  <p className="font-display text-2xl font-semibold">{fmtNum(ranking.hectareas)}</p>
                  <p className="text-[11px] text-[color:var(--tinta-suave)]">ha deforestadas</p>
                </div>
              </div>
            )}

            <p className="mb-2 text-sm font-semibold">Deforestación por periodo (ha/año)</p>
            <div className="space-y-1">
              {serie.map((s) => (
                <div key={s.periodo} className="flex items-center gap-2">
                  <span
                    className={clsx(
                      'w-16 shrink-0 text-[11px]',
                      s.periodo === periodo
                        ? 'font-semibold text-bosque-700 dark:text-bosque-300'
                        : 'text-[color:var(--tinta-suave)]',
                    )}
                  >
                    {s.periodo}
                  </span>
                  <span className="h-3 flex-1 overflow-hidden rounded-full bg-[color:var(--borde)]">
                    <span
                      className="block h-full rounded-full"
                      style={{
                        width: `${(s.ha / maxHa) * 100}%`,
                        backgroundColor: s.estimado ? '#FDBA74' : '#DC2626',
                      }}
                    />
                  </span>
                  <span className="w-12 shrink-0 text-right text-[11px] tabular-nums">
                    {fmtNum(s.ha)}
                  </span>
                </div>
              ))}
            </div>

            <div className="mt-5 flex flex-col gap-2">
              <a
                href={`/dashboard?municipio=${codigo}`}
                className="rounded-full bg-bosque-600 px-4 py-2 text-center text-sm font-medium text-white transition-colors hover:bg-bosque-700"
              >
                Ver en el dashboard
              </a>
              <a
                href={urlDescarga('serie.csv', { municipio: codigo })}
                className="rounded-full border border-[color:var(--borde)] px-4 py-2 text-center text-sm font-medium transition-colors hover:border-bosque-300"
              >
                Descargar CSV del municipio
              </a>
            </div>
            {!incluirEstimados && serie.some((s) => s.estimado) && (
              <p className="mt-3 text-[11px] italic text-[color:var(--tinta-suave)]">
                Las barras ámbar corresponden a periodos estimados.
              </p>
            )}
          </>
        )}
      </div>

      <button
        type="button"
        onClick={alCerrar}
        className="flex items-center justify-center gap-1 border-t border-[color:var(--borde)] py-2 text-xs text-[color:var(--tinta-suave)] hover:bg-bosque-50 dark:hover:bg-bosque-900 sm:hidden"
      >
        <ChevronLeft className="h-4 w-4" /> Volver al mapa
      </button>
    </aside>
  );
}
