'use client';

/**
 * Landing del Observatorio (SPEC §8.1): hero a pantalla completa con SVG
 * topográfico animado, franja de KPIs reales desde /kpis con contadores
 * animados, tarjetas de los 6 módulos y sección de honestidad de datos.
 * El footer institucional lo aporta el layout global.
 */
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion, useReducedMotion } from 'framer-motion';
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CalendarRange,
  Database,
  Flame,
  GraduationCap,
  Layers,
  Map as MapIcon,
  MapPin,
  TreePine,
  TrendingDown,
} from 'lucide-react';
import { getKpis } from '@/lib/api';
import type { Kpis } from '@/lib/types';
import { fmtHa, fmtNum, fmtPct } from '@/lib/format';
import KpiCard from '@/components/ui/KpiCard';
import SectionHeading from '@/components/ui/SectionHeading';
import Badge from '@/components/ui/Badge';
import Loader from '@/components/ui/Loader';
import HeroDosel from '@/components/inicio/HeroDosel';

/* ------------------------------------------------------------------ */
/* Datos estáticos de la página                                        */
/* ------------------------------------------------------------------ */

const MODULOS = [
  {
    href: '/dashboard',
    titulo: 'Dashboard analítico',
    descripcion:
      'Series temporales, ranking de municipios, comparador, heatmap municipio × periodo, predicción y hallazgos de la investigación.',
    Icono: BarChart3,
    acento: 'bg-alerta-50 text-alerta-600 dark:bg-alerta-900/40 dark:text-alerta-300',
  },
  {
    href: '/mapa',
    titulo: 'Mapa interactivo',
    descripcion:
      'Choropleth municipal con línea de tiempo 2000–2024, timelapse, hotspots y capas de contexto (áreas protegidas, resguardos, cuencas).',
    Icono: MapIcon,
    acento: 'bg-bosque-50 text-bosque-600 dark:bg-bosque-900 dark:text-bosque-300',
  },
  {
    href: '/parches',
    titulo: 'Visor de deforestación',
    descripcion:
      'Recorre periodo a periodo los polígonos de deforestación y enciende o apaga las capas de la cartografía oficial sobre el mapa.',
    Icono: Layers,
    acento: 'bg-fuego-500/10 text-fuego-700 dark:bg-fuego-900/30 dark:text-fuego-500',
  },
  {
    href: '/aprende',
    titulo: 'Aprende · PRAES',
    descripcion:
      'Módulo educativo por niveles (primaria, secundaria y media): storytelling, quiz, juego «Salva el Bosque» e historias locales.',
    Icono: GraduationCap,
    acento: 'bg-bosque-100 text-bosque-700 dark:bg-bosque-800 dark:text-bosque-100',
  },
  {
    href: '/datos',
    titulo: 'Centro de descargas',
    descripcion:
      'CSV, XLSX y GeoJSON con generador de extractos, diccionario de datos y metodología completa de fuentes y calibraciones.',
    Icono: Database,
    acento: 'bg-tierra-100 text-tierra-700 dark:bg-tierra-700/30 dark:text-tierra-300',
  },
  {
    href: '/',
    titulo: 'Panorama general',
    descripcion:
      'Este inicio: cifras clave del observatorio de un vistazo y punto de partida para explorar los 24 años de datos de deforestación.',
    Icono: TreePine,
    acento: 'bg-bosque-50 text-bosque-700 dark:bg-bosque-900/60 dark:text-bosque-200',
  },
] as const;

const PUNTOS_HONESTIDAD = [
  {
    Icono: CalendarRange,
    titulo: 'Periodos de distinta duración',
    texto:
      'Los cinco primeros periodos (2000–2010) abarcan dos años cada uno; desde 2012 son anuales. Para comparar en igualdad de condiciones usa siempre las hectáreas por año, no el total del periodo.',
  },
  {
    Icono: AlertTriangle,
    titulo: 'Hay datos estimados',
    texto:
      'Para 2010-2012, 2018-2019 y 2023-2024 no existe medición municipal directa: los valores fueron estimados o calibrados con fuentes auxiliares. Se marcan SIEMPRE con un distintivo visual. (2015-2016 sí se recuperó como dato real desde la tabla municipal oficial.)',
  },
  {
    Icono: Layers,
    titulo: 'Varias fuentes combinadas',
    texto:
      'La serie une shapefiles de monitoreo, hojas de cálculo oficiales y rásteres calibrados. La jerarquía de fuentes por periodo está documentada en el centro de datos, junto al control de calidad.',
  },
] as const;

/* Variantes framer-motion para el reveal al hacer scroll */
const aparecer = {
  oculto: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0 },
};

/* ------------------------------------------------------------------ */
/* Página                                                              */
/* ------------------------------------------------------------------ */

export default function PaginaInicio() {
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [estadoKpis, setEstadoKpis] = useState<'cargando' | 'ok' | 'error'>('cargando');
  const reducirMovimiento = useReducedMotion();

  useEffect(() => {
    let activo = true;
    getKpis()
      .then((k) => {
        if (activo) {
          setKpis(k);
          setEstadoKpis('ok');
        }
      })
      .catch(() => {
        if (activo) setEstadoKpis('error');
      });
    return () => {
      activo = false;
    };
  }, []);

  // Props comunes de reveal (desactivado si el usuario reduce movimiento)
  const propsReveal = reducirMovimiento
    ? {}
    : ({
        variants: aparecer,
        initial: 'oculto',
        whileInView: 'visible',
        viewport: { once: true, margin: '-60px' },
        transition: { duration: 0.55, ease: 'easeOut' },
      } as const);

  return (
    <>
      {/* ============================ HERO ============================ */}
      <HeroDosel />

      {/* ====================== FRANJA DE KPIs ======================= */}
      <section aria-labelledby="titulo-kpis" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-20">
        <SectionHeading
          id="titulo-kpis"
          etiqueta="Los datos en cifras"
          titulo="Lo que dicen 24 años de monitoreo"
          subtitulo="Indicadores calculados en vivo sobre la serie municipal completa (2000–2024), incluyendo los periodos estimados."
        />

        <div className="mt-10">
          {estadoKpis === 'cargando' && <Loader texto="Consultando los indicadores del observatorio…" />}

          {estadoKpis === 'error' && (
            <div
              role="alert"
              className="rounded-2xl border border-dashed border-alerta-500 bg-alerta-50 p-6 text-sm text-alerta-800 dark:bg-alerta-900/30 dark:text-alerta-300"
            >
              <p className="font-semibold">No fue posible conectar con el API del observatorio.</p>
              <p className="mt-1">
                Verifica que el backend esté activo en{' '}
                <code className="rounded bg-alerta-100 px-1.5 py-0.5 text-xs dark:bg-alerta-900/60">
                  {process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}
                </code>{' '}
                y recarga la página. Mientras tanto puedes visitar el módulo educativo.
              </p>
            </div>
          )}

          {estadoKpis === 'ok' && kpis && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KpiCard
                  titulo="Total deforestado"
                  valor={kpis.total_deforestado_ha}
                  formato={fmtHa}
                  detalle="Acumulado 2000–2024 en la jurisdicción"
                  icono={TreePine}
                  retraso={0}
                />
                <KpiCard
                  titulo="Promedio anual"
                  valor={kpis.promedio_anual_ha}
                  formato={fmtHa}
                  detalle="Hectáreas perdidas por año, en promedio"
                  icono={TrendingDown}
                  retraso={0.1}
                />
                <KpiCard
                  titulo="Periodo más crítico"
                  valor={kpis.periodo_mas_critico.hectareas}
                  formato={fmtHa}
                  detalle={kpis.periodo_mas_critico.periodo}
                  estimado={kpis.periodo_mas_critico.estimado}
                  icono={Flame}
                  retraso={0.2}
                />
                <KpiCard
                  titulo="Municipio más afectado"
                  valor={kpis.municipio_mas_afectado.hectareas}
                  formato={fmtHa}
                  detalle={kpis.municipio_mas_afectado.municipio}
                  icono={MapPin}
                  retraso={0.3}
                />
              </div>

              <p className="mt-6 text-sm text-[color:var(--tinta-suave)]">
                Serie de {fmtNum(kpis.n_periodos)} periodos y {fmtNum(kpis.n_municipios)} municipios ·{' '}
                {fmtPct(kpis.pct_datos_estimados)} de los datos de deforestación son estimados ·{' '}
                periodo de menor pérdida: {kpis.periodo_menor.periodo} ({fmtHa(kpis.periodo_menor.hectareas)}
                {kpis.periodo_menor.estimado ? ', estimado' : ''}).
              </p>
            </>
          )}
        </div>
      </section>

      {/* ==================== TARJETAS DE MÓDULOS ===================== */}
      <section
        aria-labelledby="titulo-modulos"
        className="border-y border-[color:var(--borde)] bg-[color:var(--superficie)]"
      >
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-20">
          <SectionHeading
            id="titulo-modulos"
            etiqueta="Seis maneras de explorar"
            titulo="Un observatorio, seis módulos"
            subtitulo="Del vistazo territorial al análisis fino, pasando por el visor de polígonos, el aula y la descarga abierta."
          />

          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {MODULOS.map(({ href, titulo, descripcion, Icono, acento }, i) => (
              <motion.div
                key={href}
                {...propsReveal}
                transition={{
                  duration: 0.5,
                  ease: 'easeOut',
                  delay: reducirMovimiento ? 0 : i * 0.07,
                }}
              >
                <Link
                  href={href}
                  className="group flex h-full flex-col rounded-2xl border border-[color:var(--borde)] bg-[color:var(--fondo)] p-6 transition-all hover:-translate-y-0.5 hover:border-bosque-300 hover:shadow-lg motion-reduce:hover:translate-y-0"
                >
                  <span className={`flex h-11 w-11 items-center justify-center rounded-xl ${acento}`}>
                    <Icono className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <h3 className="mt-4 font-display text-xl font-semibold tracking-tight">{titulo}</h3>
                  <p className="mt-2 flex-1 text-sm leading-relaxed text-[color:var(--tinta-suave)]">
                    {descripcion}
                  </p>
                  <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-bosque-600 group-hover:gap-2.5 dark:text-bosque-300" style={{ transition: 'gap .2s ease' }}>
                    Entrar
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </span>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ================ HONESTIDAD DE LOS DATOS ===================== */}
      <section aria-labelledby="titulo-honestidad" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-20">
        <SectionHeading
          id="titulo-honestidad"
          etiqueta="Transparencia metodológica"
          titulo="¿Cómo leer estos datos?"
          subtitulo="Ningún monitoreo de bosque es perfecto. Antes de sacar conclusiones, ten presentes estas tres cosas."
        />

        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {PUNTOS_HONESTIDAD.map(({ Icono, titulo, texto }, i) => (
            <motion.article
              key={titulo}
              {...propsReveal}
              transition={{
                duration: 0.5,
                ease: 'easeOut',
                delay: reducirMovimiento ? 0 : i * 0.07,
              }}
              className="rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-6"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-tierra-100 text-tierra-700 dark:bg-tierra-700/30 dark:text-tierra-300">
                <Icono className="h-5 w-5" aria-hidden="true" />
              </span>
              <h3 className="mt-4 font-display text-lg font-semibold">{titulo}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[color:var(--tinta-suave)]">{texto}</p>
            </motion.article>
          ))}
        </div>

        <motion.div
          {...propsReveal}
          className="mt-8 flex flex-col items-start gap-4 rounded-2xl border border-dashed border-alerta-500 bg-alerta-50 p-6 dark:bg-alerta-900/20 sm:flex-row sm:items-center"
        >
          <Badge variante="estimado" className="shrink-0">estimado</Badge>
          <p className="text-sm leading-relaxed text-alerta-800 dark:text-alerta-300">
            Cuando veas esta insignia —o un borde discontinuo en el mapa— el dato proviene de una
            estimación o calibración, no de una medición directa. La metodología completa, fuente
            por fuente, está publicada en el centro de datos.
          </p>
          <Link
            href="/datos"
            className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-alerta-500 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-alerta-600"
          >
            Ver metodología
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </motion.div>
      </section>

      {/* ===================== CIERRE / CTA DATOS ===================== */}
      <section className="border-t border-[color:var(--borde)] bg-bosque-50/60 dark:bg-bosque-900/20">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-4 py-14 sm:px-6 md:flex-row md:items-center">
          <div>
            <h2 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
              Datos abiertos para decisiones informadas
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-[color:var(--tinta-suave)]">
              Toda la serie municipal, los límites, los hotspots y las capas de contexto están
              disponibles en CSV, XLSX y GeoJSON, con su diccionario de datos.
            </p>
          </div>
          <Link
            href="/datos"
            className="inline-flex items-center gap-2 rounded-full bg-bosque-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-bosque-700"
          >
            <Database className="h-4 w-4" aria-hidden="true" />
            Ir al centro de descargas
          </Link>
        </div>
      </section>
    </>
  );
}
