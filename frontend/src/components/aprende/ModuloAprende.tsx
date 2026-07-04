'use client';

/**
 * Módulo educativo PRAES (SPEC §8.4): niveles adaptativos, secciones de
 * storytelling, quiz por nivel, juego «Salva el Bosque», historias locales
 * con sparkline y glosario. Contenido y cifras reales en ./contenido.ts.
 */
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { motion, useReducedMotion } from 'framer-motion';
import { BookOpen, ChevronDown, GraduationCap } from 'lucide-react';
import clsx from 'clsx';
import SectionHeading from '@/components/ui/SectionHeading';
import SalvaBosque from './SalvaBosque';
import {
  GLOSARIO,
  HISTORIAS,
  NIVELES,
  type Nivel,
  type Pregunta,
  QUIZ,
  SECCIONES,
} from './contenido';

export default function ModuloAprende() {
  const [nivel, setNivel] = useState<Nivel>('guardian');
  const reducir = useReducedMotion();

  // Nivel persistente en localStorage
  useEffect(() => {
    const guardado = localStorage.getItem('praes-nivel') as Nivel | null;
    if (guardado && NIVELES.some((n) => n.id === guardado)) setNivel(guardado);
  }, []);
  useEffect(() => {
    localStorage.setItem('praes-nivel', nivel);
  }, [nivel]);

  const anim = (i = 0) =>
    reducir
      ? {}
      : {
          initial: { opacity: 0, y: 24 },
          whileInView: { opacity: 1, y: 0 },
          viewport: { once: true, margin: '-60px' },
          transition: { delay: Math.min(i * 0.05, 0.3) },
        };

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
      {/* Portada */}
      <div className="rounded-3xl bg-gradient-to-br from-bosque-800 to-bosque-950 p-8 text-white sm:p-12">
        <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-widest text-bosque-200">
          <GraduationCap className="h-4 w-4" /> Módulo educativo · PRAES
        </p>
        <h1 className="mt-3 font-display text-4xl font-semibold sm:text-5xl">
          Aprende sobre el bosque de Urabá
        </h1>
        <p className="mt-3 max-w-2xl text-bosque-100">
          Una historia contada con datos reales del observatorio. Elige tu nivel y descubre por qué
          el bosque importa, qué lo amenaza y cómo cuidarlo.
        </p>
      </div>

      {/* Selector de nivel */}
      <div className="sticky top-16 z-30 mt-6 flex flex-wrap gap-2 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)]/95 p-2 backdrop-blur">
        {NIVELES.map((n) => (
          <button
            key={n.id}
            type="button"
            onClick={() => setNivel(n.id)}
            className={clsx(
              'flex flex-1 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors',
              nivel === n.id
                ? 'bg-bosque-600 text-white'
                : 'text-[color:var(--tinta-suave)] hover:bg-bosque-50 dark:hover:bg-bosque-900',
            )}
            aria-pressed={nivel === n.id}
          >
            <span className="text-lg" aria-hidden="true">
              {n.emoji}
            </span>
            <span>
              {n.nombre}
              <span className="ml-1 hidden text-xs opacity-70 sm:inline">· {n.grado}</span>
            </span>
          </button>
        ))}
      </div>

      {/* Secciones de storytelling */}
      <div className="mt-10 space-y-10">
        {SECCIONES.map((s, i) => (
          <motion.section key={s.id} {...anim(i)} className="grid gap-4 sm:grid-cols-[auto_1fr] sm:gap-6">
            <IlustracionSeccion id={s.id} />
            <div>
              <h2 className="font-display text-2xl font-semibold">{s.titulo}</h2>
              <p className="mt-2 leading-relaxed text-[color:var(--tinta-suave)]">{s.texto[nivel]}</p>
            </div>
          </motion.section>
        ))}
      </div>

      {/* Quiz */}
      <div className="mt-14">
        <SectionHeading
          etiqueta="Pon a prueba lo aprendido"
          titulo="¿Cuánto sabes del bosque de Urabá?"
          subtitulo={`8 preguntas del nivel ${NIVELES.find((n) => n.id === nivel)?.nombre}.`}
        />
        <Quiz preguntas={QUIZ[nivel]} key={nivel} />
      </div>

      {/* Juego */}
      <div className="mt-14">
        <SectionHeading etiqueta="Juega y aprende" titulo="El reto del guardabosques" />
        <div className="mt-6">
          <SalvaBosque />
        </div>
      </div>

      {/* Historias locales */}
      <div className="mt-14">
        <SectionHeading
          etiqueta="Historias del territorio"
          titulo="Cuatro municipios, cuatro historias"
          subtitulo="Cada gráfico muestra la deforestación real (ha/año) del municipio."
        />
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {HISTORIAS.map((h, i) => (
            <motion.article
              key={h.id}
              {...anim(i)}
              className="rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm"
            >
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-semibold">{h.titulo}</h3>
                <Sparkline datos={h.serie} />
              </div>
              <p className="mt-2 text-sm leading-relaxed text-[color:var(--tinta-suave)]">{h.texto}</p>
            </motion.article>
          ))}
        </div>
      </div>

      {/* Glosario */}
      <div className="mt-14">
        <SectionHeading etiqueta="Vocabulario" titulo="Glosario del bosque" />
        <div className="mt-6 divide-y divide-[color:var(--borde)] rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)]">
          {GLOSARIO.map((g) => (
            <Acordeon key={g.termino} termino={g.termino} definicion={g.definicion} />
          ))}
        </div>
      </div>

      {/* Guía docente */}
      <div className="mt-10 flex flex-col items-start gap-3 rounded-2xl border border-bosque-300 bg-bosque-50 p-6 dark:border-bosque-700 dark:bg-bosque-900/50 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <BookOpen className="mt-0.5 h-6 w-6 shrink-0 text-bosque-600 dark:text-bosque-300" />
          <div>
            <p className="font-semibold">Guía docente y datos para el aula</p>
            <p className="text-sm text-[color:var(--tinta-suave)]">
              Descarga las series y capas para trabajar el PRAES con datos reales del territorio.
            </p>
          </div>
        </div>
        <Link
          href="/datos"
          className="shrink-0 rounded-full bg-bosque-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-bosque-700"
        >
          Ir al centro de datos
        </Link>
      </div>
    </div>
  );
}

/** Ilustración SVG propia por sección (sin dependencias externas). */
function IlustracionSeccion({ id }: { id: string }) {
  const comun = 'h-24 w-24 shrink-0 rounded-2xl';
  if (id === 'que-es')
    return (
      <svg viewBox="0 0 100 100" className={`${comun} bg-bosque-50 dark:bg-bosque-900/50`} aria-hidden="true">
        <path d="M50 20 L64 46 H36 Z M50 34 L70 66 H30 Z" fill="#2E8B57" />
        <rect x="46" y="66" width="8" height="14" fill="#6B5744" />
        <line x1="74" y1="30" x2="86" y2="18" stroke="#DC2626" strokeWidth="3" />
        <line x1="86" y1="30" x2="74" y2="18" stroke="#DC2626" strokeWidth="3" />
      </svg>
    );
  if (id === 'por-que')
    return (
      <svg viewBox="0 0 100 100" className={`${comun} bg-alerta-50 dark:bg-alerta-900/40`} aria-hidden="true">
        <rect x="10" y="60" width="80" height="30" fill="#D9CDB8" />
        <path d="M25 60 L33 44 H17 Z" fill="#2E8B57" />
        <path d="M50 60 L58 44 H42 Z" fill="#7BC796" />
        <circle cx="72" cy="70" r="6" fill="#6B5744" />
        <path d="M66 70 q6 -10 12 0" stroke="#6B5744" fill="none" strokeWidth="2" />
      </svg>
    );
  if (id === 'impactos')
    return (
      <svg viewBox="0 0 100 100" className={`${comun} bg-tierra-100 dark:bg-tierra-700/30`} aria-hidden="true">
        <circle cx="40" cy="45" r="16" fill="#F59E0B" />
        <circle cx="35" cy="42" r="2.5" fill="#111" />
        <circle cx="45" cy="42" r="2.5" fill="#111" />
        <path d="M34 52 q6 5 12 0" stroke="#111" fill="none" strokeWidth="2" />
        <path d="M20 78 q30 -14 60 0" stroke="#1D4ED8" fill="none" strokeWidth="3" />
      </svg>
    );
  if (id === 'clima')
    return (
      <svg viewBox="0 0 100 100" className={`${comun} bg-bosque-50 dark:bg-bosque-900/50`} aria-hidden="true">
        <circle cx="50" cy="42" r="20" fill="#7BC796" />
        <text x="50" y="48" textAnchor="middle" fontSize="14" fill="#0B3D25" fontWeight="bold">
          CO₂
        </text>
        <path d="M30 74 h40 M36 82 h28" stroke="#2E8B57" strokeWidth="3" strokeLinecap="round" />
      </svg>
    );
  return (
    <svg viewBox="0 0 100 100" className={`${comun} bg-bosque-50 dark:bg-bosque-900/50`} aria-hidden="true">
      <path d="M50 78 V40" stroke="#6B5744" strokeWidth="4" />
      <circle cx="50" cy="34" r="16" fill="#2E8B57" />
      <path d="M50 52 q-14 -4 -20 6 M50 60 q14 -4 20 6" stroke="#7BC796" strokeWidth="3" fill="none" />
      <path d="M38 82 q12 8 24 0" stroke="#2E8B57" strokeWidth="3" fill="none" />
    </svg>
  );
}

/** Quiz interactivo con feedback inmediato y confeti CSS al terminar. */
function Quiz({ preguntas }: { preguntas: Pregunta[] }) {
  const [actual, setActual] = useState(0);
  const [elegida, setElegida] = useState<number | null>(null);
  const [aciertos, setAciertos] = useState(0);
  const [terminado, setTerminado] = useState(false);

  const p = preguntas[actual];

  function responder(i: number) {
    if (elegida !== null) return;
    setElegida(i);
    if (i === p.correcta) setAciertos((a) => a + 1);
  }
  function siguiente() {
    if (actual + 1 >= preguntas.length) {
      setTerminado(true);
    } else {
      setActual((a) => a + 1);
      setElegida(null);
    }
  }
  function reiniciar() {
    setActual(0);
    setElegida(null);
    setAciertos(0);
    setTerminado(false);
  }

  const mensaje = useMemo(() => {
    const pct = aciertos / preguntas.length;
    if (pct === 1) return '¡Perfecto! Eres un verdadero guardián del bosque. 🌳';
    if (pct >= 0.6) return '¡Muy bien! Sabes bastante sobre el bosque de Urabá. 🌿';
    return 'Buen intento. Vuelve a leer las secciones y prueba otra vez. 🌱';
  }, [aciertos, preguntas.length]);

  if (terminado) {
    return (
      <div className="relative mt-6 overflow-hidden rounded-2xl border border-bosque-300 bg-bosque-50 p-8 text-center dark:border-bosque-700 dark:bg-bosque-900/50">
        <div className="pointer-events-none absolute inset-0 motion-reduce:hidden" aria-hidden="true">
          {Array.from({ length: 18 }).map((_, i) => (
            <span
              key={i}
              className="absolute block h-2 w-2 rounded-sm"
              style={{
                left: `${(i * 53) % 100}%`,
                top: '-10px',
                backgroundColor: ['#2E8B57', '#F97316', '#FDBA74', '#7BC796'][i % 4],
                animation: `caer 2.4s ${(i % 6) * 0.2}s ease-in infinite`,
              }}
            />
          ))}
        </div>
        <p className="font-display text-2xl font-semibold">
          {aciertos} / {preguntas.length} correctas
        </p>
        <p className="mt-2 text-[color:var(--tinta-suave)]">{mensaje}</p>
        <button
          type="button"
          onClick={reiniciar}
          className="mt-4 rounded-full bg-bosque-600 px-5 py-2 text-sm font-medium text-white hover:bg-bosque-700"
        >
          Reintentar
        </button>
        <style>{`@keyframes caer{to{transform:translateY(320px) rotate(360deg);opacity:0}}`}</style>
      </div>
    );
  }

  return (
    <div className="mt-6 rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-6 shadow-sm">
      <div className="mb-3 flex items-center justify-between text-xs text-[color:var(--tinta-suave)]">
        <span>
          Pregunta {actual + 1} de {preguntas.length}
        </span>
        <span>Aciertos: {aciertos}</span>
      </div>
      <p className="font-display text-lg font-semibold">{p.pregunta}</p>
      <div className="mt-4 space-y-2">
        {p.opciones.map((o, i) => {
          const esCorrecta = i === p.correcta;
          const revelar = elegida !== null;
          return (
            <button
              key={i}
              type="button"
              onClick={() => responder(i)}
              disabled={revelar}
              className={clsx(
                'flex w-full items-center gap-3 rounded-xl border px-4 py-3 text-left text-sm transition-colors',
                !revelar && 'border-[color:var(--borde)] hover:border-bosque-400 hover:bg-bosque-50 dark:hover:bg-bosque-900',
                revelar && esCorrecta && 'border-bosque-500 bg-bosque-50 dark:bg-bosque-900/60',
                revelar && !esCorrecta && elegida === i && 'border-fuego-500 bg-fuego-500/10',
                revelar && !esCorrecta && elegida !== i && 'border-[color:var(--borde)] opacity-60',
              )}
            >
              <span
                className={clsx(
                  'flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold',
                  revelar && esCorrecta
                    ? 'bg-bosque-600 text-white'
                    : revelar && elegida === i
                    ? 'bg-fuego-500 text-white'
                    : 'bg-[color:var(--fondo)]',
                )}
              >
                {String.fromCharCode(65 + i)}
              </span>
              {o}
            </button>
          );
        })}
      </div>
      {elegida !== null && (
        <div className="mt-4 rounded-xl bg-[color:var(--fondo)] p-3 text-sm">
          <p className={elegida === p.correcta ? 'font-semibold text-bosque-700 dark:text-bosque-300' : 'font-semibold text-fuego-700'}>
            {elegida === p.correcta ? '¡Correcto!' : 'No exactamente.'}
          </p>
          <p className="mt-1 text-[color:var(--tinta-suave)]">{p.explicacion}</p>
          <button
            type="button"
            onClick={siguiente}
            className="mt-3 rounded-full bg-bosque-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-bosque-700"
          >
            {actual + 1 >= preguntas.length ? 'Ver resultado' : 'Siguiente'}
          </button>
        </div>
      )}
    </div>
  );
}

/** Mini gráfico de línea SVG (sparkline) sin dependencias. */
function Sparkline({ datos }: { datos: number[] }) {
  const w = 90;
  const h = 32;
  const max = Math.max(...datos, 1);
  const min = Math.min(...datos);
  const puntos = datos
    .map((v, i) => {
      const x = (i / (datos.length - 1)) * w;
      const y = h - ((v - min) / (max - min || 1)) * (h - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg width={w} height={h} className="shrink-0" aria-hidden="true">
      <polyline points={puntos} fill="none" stroke="#DC2626" strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

/** Ítem de glosario tipo acordeón. */
function Acordeon({ termino, definicion }: { termino: string; definicion: string }) {
  const [abierto, setAbierto] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        aria-expanded={abierto}
        className="flex w-full items-center justify-between px-5 py-3 text-left text-sm font-medium hover:bg-bosque-50 dark:hover:bg-bosque-900/40"
      >
        {termino}
        <ChevronDown className={clsx('h-4 w-4 transition-transform', abierto && 'rotate-180')} />
      </button>
      {abierto && <p className="px-5 pb-3 text-sm text-[color:var(--tinta-suave)]">{definicion}</p>}
    </div>
  );
}
