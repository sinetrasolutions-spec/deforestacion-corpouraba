'use client';

/**
 * Sección del dashboard: deforestación por unidad territorial. Permite elegir
 * un tipo (áreas protegidas, POMCAS, resguardos indígenas, consejos
 * comunitarios, cuencas) y ver el ranking de cuánta deforestación mapeada
 * ocurre en cada unidad, con barra, área y % del territorio, y descarga CSV.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { getTerritorios, getTerritoriosCatalogo, type UnidadTerritorio } from '@/lib/api';
import { fmtHa, fmtNum, fmtPct } from '@/lib/format';
import SectionHeading from '@/components/ui/SectionHeading';
import BotonExportar from '@/components/ui/BotonExportar';
import Loader from '@/components/ui/Loader';

const ORDEN_PREFERIDO = ['areas_protegidas', 'pomcas', 'resguardos', 'consejos'];
// 'cuencas' se omite: es redundante con POMCAS (los POMCAS ordenan esas cuencas).
const EXCLUIR = new Set(['cuencas']);

export default function DeforestacionPorTerritorio() {
  const reducir = useReducedMotion();
  const [tipos, setTipos] = useState<{ id: string; titulo: string; disponible: boolean }[]>([]);
  const [tipoSel, setTipoSel] = useState<string>('areas_protegidas');
  const [periodoSel, setPeriodoSel] = useState<string | null>(null); // null = acumulado
  const [datos, setDatos] = useState<{
    titulo: string;
    n_unidades: number;
    deforestacion_total_ha: number;
    periodos_disponibles: string[];
    unidades: UnidadTerritorio[];
  } | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  const refTabla = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getTerritoriosCatalogo()
      .then((c) => {
        const disp = c.tipos.filter((t) => t.disponible && !EXCLUIR.has(t.id));
        disp.sort((a, b) => ORDEN_PREFERIDO.indexOf(a.id) - ORDEN_PREFERIDO.indexOf(b.id));
        setTipos(disp);
        if (disp.length && !disp.some((t) => t.id === 'areas_protegidas')) {
          setTipoSel(disp[0].id);
        }
      })
      .catch(() => setError(true));
  }, []);

  useEffect(() => {
    let vivo = true;
    setCargando(true);
    setError(false);
    getTerritorios(tipoSel, periodoSel ?? undefined)
      .then((d) => vivo && setDatos(d))
      .catch(() => vivo && setError(true))
      .finally(() => vivo && setCargando(false));
    return () => {
      vivo = false;
    };
  }, [tipoSel, periodoSel]);

  // Al cambiar de tipo se vuelve al acumulado (los periodos pueden diferir)
  function cambiarTipo(id: string) {
    setPeriodoSel(null);
    setTipoSel(id);
  }

  // Lista de posiciones de la barra: [Acumulado, ...periodos]
  const periodos = datos?.periodos_disponibles ?? [];
  const posiciones = [null, ...periodos];
  const idxActual = Math.max(posiciones.findIndex((p) => p === periodoSel), 0);

  const maxHa = useMemo(
    () => (datos ? Math.max(...datos.unidades.map((u) => u.deforestacion_ha), 1) : 1),
    [datos],
  );

  function csv(): string {
    if (!datos) return '';
    const cab = 'unidad,detalle,deforestacion_ha,n_periodos,area_ha,pct_del_territorio\n';
    return (
      cab +
      datos.unidades
        .map((u) =>
          [
            `"${u.nombre}"`,
            `"${u.detalle ?? ''}"`,
            u.deforestacion_ha,
            u.n_periodos ?? '',
            u.area_ha ?? '',
            u.pct_del_territorio ?? '',
          ].join(','),
        )
        .join('\n')
    );
  }

  if (error && !datos) return null; // sin datos de territorios: se oculta la sección

  return (
    <section className="mt-10">
      <SectionHeading
        etiqueta="Territorios"
        titulo="Deforestación por área protegida, POMCA y territorio"
        subtitulo="Cuánta deforestación mapeada ocurre dentro de cada unidad. Elige el tipo de territorio."
      />

      {/* Selector de tipo */}
      <div className="mt-5 flex flex-wrap gap-2">
        {tipos.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => cambiarTipo(t.id)}
            className={
              'rounded-full px-4 py-2 text-sm font-medium transition-colors ' +
              (tipoSel === t.id
                ? 'bg-bosque-600 text-white'
                : 'border border-[color:var(--borde)] text-[color:var(--tinta-suave)] hover:border-bosque-300')
            }
          >
            {t.titulo}
          </button>
        ))}
      </div>

      {/* Barra de tiempo: Acumulado + cada periodo con hotspots */}
      {periodos.length > 0 && (
        <div className="mt-4 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--fondo)] px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
              Periodo
            </span>
            <span className="font-display text-sm font-semibold text-bosque-700 dark:text-bosque-300">
              {periodoSel ?? 'Acumulado 2000–2024'}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={posiciones.length - 1}
            value={idxActual}
            onChange={(e) => setPeriodoSel(posiciones[Number(e.target.value)])}
            className="mt-1 w-full accent-bosque-600"
            aria-label="Periodo del ranking de territorios"
          />
          <div className="flex justify-between text-[10px] text-[color:var(--tinta-suave)]">
            <span>Acumulado</span>
            <span>{periodos[periodos.length - 1]}</span>
          </div>
        </div>
      )}

      <div className="mt-4 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm">
        {cargando && <Loader texto="Cargando territorios…" />}
        {!cargando && datos && (
          <>
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="font-display text-lg font-semibold">
                  {datos.titulo}
                  <span className="ml-2 text-sm font-normal text-[color:var(--tinta-suave)]">
                    · {periodoSel ?? 'acumulado 2000–2024'}
                  </span>
                </p>
                <p className="text-sm text-[color:var(--tinta-suave)]">
                  {datos.n_unidades} unidades · {fmtHa(datos.deforestacion_total_ha)} deforestadas (mapeado)
                </p>
              </div>
              <BotonExportar
                nombreArchivo={`deforestacion_${tipoSel}${periodoSel ? `_${periodoSel}` : '_acumulado'}`}
                obtenerCsv={csv}
              />
            </div>

            <div ref={refTabla} className="space-y-1.5">
              {datos.unidades.map((u, i) => (
                <motion.div
                  key={u.nombre}
                  initial={reducir ? false : { opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: Math.min(i * 0.02, 0.4) }}
                  className="flex items-center gap-3"
                >
                  <span className="w-6 shrink-0 text-right text-xs tabular-nums text-[color:var(--tinta-suave)]">
                    {i + 1}
                  </span>
                  <span className="w-40 shrink-0 truncate text-sm sm:w-56" title={u.nombre}>
                    {u.nombre}
                    {u.detalle && (
                      <span className="ml-1 text-[11px] text-[color:var(--tinta-suave)]">· {u.detalle}</span>
                    )}
                  </span>
                  <span className="h-4 flex-1 overflow-hidden rounded-full bg-[color:var(--borde)]">
                    <span
                      className="block h-full rounded-full bg-gradient-to-r from-alerta-500 to-fuego-500"
                      style={{ width: `${Math.max((u.deforestacion_ha / maxHa) * 100, 1.5)}%` }}
                    />
                  </span>
                  <span className="w-20 shrink-0 text-right text-sm font-medium tabular-nums">
                    {fmtNum(u.deforestacion_ha)} ha
                  </span>
                  <span className="hidden w-16 shrink-0 text-right text-xs tabular-nums text-[color:var(--tinta-suave)] sm:inline">
                    {u.pct_del_territorio != null ? fmtPct(u.pct_del_territorio) : '—'}
                  </span>
                </motion.div>
              ))}
            </div>

            <p className="mt-4 text-xs text-[color:var(--tinta-suave)]">
              «Deforestación mapeada»: polígonos ≥1 ha de los 12 periodos con detección espacial
              (aprox. 65 % de la deforestación total; los otros 6 periodos —incluido el pico
              2015-2016— no tienen geometría). El % es sobre el área de cada unidad cuando se
              conoce. Fuentes y método en el centro de datos.
            </p>
          </>
        )}
      </div>
    </section>
  );
}
