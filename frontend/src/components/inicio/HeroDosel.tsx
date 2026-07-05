'use client';

/**
 * Hero del Observatorio: escena 3D "dosel vivo de Urabá" que se deforesta al
 * hacer scroll, con coreografía de entrada (GSAP) y scroll suave (Lenis).
 * El texto y los CTA se conservan íntegros; toda la fuerza visual va a la
 * escena. Respeta prefers-reduced-motion y se adapta a móvil.
 */
import { useEffect, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { CalendarRange, MapPin, TreePine } from 'lucide-react';

const EscenaDosel = dynamic(() => import('./EscenaDosel'), { ssr: false });

const TOTAL_DEFORESTADO = 46846; // ha reales deforestadas 2000–2024 (serie municipal)
const TITULO = ['Observatorio', 'de', 'Deforestación', 'CORPOURABA'];

// Municipios reales (deforestación 2000–2024) como puntos de alerta sobre el dosel.
const ALERTAS = [
  { nombre: 'Turbo', ha: '13.309 ha', left: '64%', top: '37%' },
  { nombre: 'Necoclí', ha: '2.351 ha', left: '80%', top: '29%' },
  { nombre: 'Mutatá', ha: '4.720 ha', left: '58%', top: '56%' },
  { nombre: 'Dabeiba', ha: '5.003 ha', left: '88%', top: '50%' },
  { nombre: 'Chigorodó', ha: '2.111 ha', left: '73%', top: '66%' },
];

const fmt = (n: number) => Math.round(n).toLocaleString('es-CO');

export default function HeroDosel() {
  const progresoRef = useRef(0);
  const punteroRef = useRef({ x: 0, y: 0 });

  const seccionRef = useRef<HTMLElement>(null);
  const escenaRef = useRef<HTMLDivElement>(null);
  const tituloRef = useRef<HTMLHeadingElement>(null);
  const contadorRef = useRef<HTMLSpanElement>(null);
  const contenidoRef = useRef<HTMLDivElement>(null);
  const ctaRef = useRef<HTMLAnchorElement>(null);
  const cursorRef = useRef<HTMLDivElement>(null);
  const marcasRef = useRef<HTMLDivElement>(null);

  const [entorno, setEntorno] = useState<{ reduced: boolean; movil: boolean; listo: boolean }>({
    reduced: false,
    movil: false,
    listo: false,
  });

  // Detección de entorno (solo cliente)
  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const movil = window.matchMedia('(max-width: 767px)').matches;
    setEntorno({ reduced, movil, listo: true });
  }, []);

  // Coreografía: entrada + scroll (GSAP/Lenis). Se rearma según el entorno.
  useEffect(() => {
    if (!entorno.listo) return;
    const { reduced, movil } = entorno;
    let lenis: import('lenis').default | null = null;
    const cleanup: Array<() => void> = [];
    let cancelado = false; // evita la carrera async del doble-montaje (Strict Mode)

    (async () => {
      const gsapMod = await import('gsap');
      const stMod = await import('gsap/ScrollTrigger');
      if (cancelado) return;
      const gsap = gsapMod.default;
      const ScrollTrigger = stMod.ScrollTrigger;
      gsap.registerPlugin(ScrollTrigger);

      const palabras = tituloRef.current?.querySelectorAll<HTMLElement>('.palabra-titulo') ?? [];
      const cifras = contenidoRef.current?.querySelectorAll<HTMLElement>('[data-objetivo]') ?? [];

      // ── prefers-reduced-motion: estado final, sin animación ──────────────
      if (reduced) {
        gsap.set(palabras, { opacity: 1, filter: 'blur(0px)', y: 0 });
        gsap.set(escenaRef.current, { opacity: 1, scale: 1 });
        cifras.forEach((el) => {
          const obj = Number(el.dataset.objetivo);
          const dec = Number(el.dataset.decimales || 0);
          el.textContent = dec ? obj.toLocaleString('es-CO', { minimumFractionDigits: dec }) : fmt(obj);
        });
        if (contadorRef.current) contadorRef.current.textContent = fmt(TOTAL_DEFORESTADO);
        return;
      }

      // ── Entrada: dosel + titular palabra a palabra + conteo de cifras ────
      gsap.set(palabras, { opacity: 0, filter: 'blur(12px)', yPercent: 40 });
      gsap.set(escenaRef.current, { opacity: 0, scale: 1.08 });

      const tl = gsap.timeline({ delay: 0.15 });
      tl.to(escenaRef.current, { opacity: 1, scale: 1, duration: 1.6, ease: 'power2.out' }, 0)
        .to(
          palabras,
          { opacity: 1, filter: 'blur(0px)', yPercent: 0, duration: 0.9, ease: 'power3.out', stagger: 0.06 },
          0.35,
        );
      cifras.forEach((el) => {
        const obj = Number(el.dataset.objetivo);
        const dec = Number(el.dataset.decimales || 0);
        const contador = { v: 0 };
        tl.to(
          contador,
          {
            v: obj,
            duration: 1.4,
            ease: 'power1.out',
            onUpdate: () => {
              el.textContent = dec
                ? contador.v.toLocaleString('es-CO', { minimumFractionDigits: dec, maximumFractionDigits: dec })
                : fmt(contador.v);
            },
          },
          0.6,
        );
      });
      cleanup.push(() => tl.kill());

      // ── Scroll suave (Lenis) + integración con ScrollTrigger ─────────────
      if (!movil) {
        const Lenis = (await import('lenis')).default;
        if (cancelado) return;
        lenis = new Lenis({ duration: 0.85, smoothWheel: true });
        lenis.on('scroll', ScrollTrigger.update);
        const raf = (t: number) => lenis!.raf(t * 1000);
        gsap.ticker.add(raf);
        gsap.ticker.lagSmoothing(0);
        cleanup.push(() => {
          gsap.ticker.remove(raf);
          lenis?.destroy();
        });
      }

      // ── Pin + deforestación al hacer scroll (solo desktop) ───────────────
      if (!movil) {
        const st = ScrollTrigger.create({
          trigger: seccionRef.current,
          start: 'top top',
          end: '+=85%',
          pin: true,
          scrub: 0.6,
          onUpdate: (self) => {
            progresoRef.current = self.progress;
            if (contadorRef.current) {
              contadorRef.current.textContent = fmt(self.progress * TOTAL_DEFORESTADO);
            }
            // el contenido de texto cede protagonismo al bosque que cae
            if (contenidoRef.current) {
              contenidoRef.current.style.opacity = String(1 - Math.max(0, (self.progress - 0.5) / 0.5));
            }
            // los marcadores del bosque intacto se apagan al empezar a talar
            if (marcasRef.current) {
              marcasRef.current.style.opacity = String(Math.max(0, 1 - self.progress / 0.3));
            }
          },
        });
        cleanup.push(() => st.kill());
        ScrollTrigger.refresh();
      }

      // ── Parallax de cursor + cursor custom + botón magnético (desktop) ───
      if (!movil) {
        const onMove = (e: MouseEvent) => {
          punteroRef.current.x = (e.clientX / window.innerWidth) * 2 - 1;
          punteroRef.current.y = -((e.clientY / window.innerHeight) * 2 - 1);
          if (cursorRef.current) {
            cursorRef.current.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
          }
          const cta = ctaRef.current;
          if (cta) {
            const r = cta.getBoundingClientRect();
            const cx = r.left + r.width / 2;
            const cy = r.top + r.height / 2;
            const dx = e.clientX - cx;
            const dy = e.clientY - cy;
            const dist = Math.hypot(dx, dy);
            if (dist < 90) {
              cta.style.transform = `translate(${dx * 0.28}px, ${dy * 0.28}px)`;
            } else {
              cta.style.transform = '';
            }
          }
        };
        window.addEventListener('mousemove', onMove);
        cleanup.push(() => window.removeEventListener('mousemove', onMove));
      }
    })();

    return () => {
      cancelado = true;
      cleanup.forEach((fn) => fn());
    };
  }, [entorno]);

  const treeCount = entorno.movil ? 130 : 430;

  return (
    <section
      ref={seccionRef}
      className="relative flex min-h-[calc(100vh-4rem)] items-center overflow-hidden bg-gradient-to-b from-bosque-950 to-bosque-900 text-white"
      aria-label="Observatorio de Deforestación CORPOURABA"
    >
      {/* Escena 3D (detrás, no captura el puntero salvo los puntos de alerta) */}
      <div ref={escenaRef} className="absolute inset-0 z-0" aria-hidden="true">
        {entorno.listo && (
          <EscenaDosel
            progresoRef={progresoRef}
            punteroRef={punteroRef}
            reduced={entorno.reduced}
            treeCount={treeCount}
          />
        )}
      </div>

      {/* Velos para legibilidad del texto sobre el dosel */}
      <div
        className="pointer-events-none absolute inset-0 z-[1] bg-gradient-to-r from-bosque-950/85 via-bosque-950/40 to-transparent"
        aria-hidden="true"
      />
      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 z-[1] h-40 bg-gradient-to-t from-bosque-950 to-transparent"
        aria-hidden="true"
      />

      {/* Puntos de alerta sobre el dosel (municipios reales) — DOM fiable */}
      {entorno.listo && !entorno.movil && !entorno.reduced && (
        <div ref={marcasRef} className="capa-alertas">
          {ALERTAS.map((a) => (
            <button
              key={a.nombre}
              type="button"
              className="marca-alerta"
              style={{ left: a.left, top: a.top }}
              aria-label={`${a.nombre}: ${a.ha} deforestadas entre 2000 y 2024`}
            >
              <span className="punto-alerta" aria-hidden="true" />
              <span className="tooltip-alerta" role="tooltip">
                <strong>{a.nombre}</strong>
                {a.ha}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Contenido (texto y CTA intactos) */}
      <div ref={contenidoRef} className="relative z-10 mx-auto w-full max-w-6xl px-4 py-24 sm:px-6">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-bosque-300">
          CORPOURABA · Monitoreo de bosques 2000–2024
        </p>

        <h1
          ref={tituloRef}
          className="mt-4 max-w-3xl font-display text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl"
        >
          {TITULO.map((w, i) => (
            <span key={i} className="palabra-titulo inline-block">
              {w}
              {i < TITULO.length - 1 ? ' ' : ''}
            </span>
          ))}
        </h1>

        <p className="mt-6 max-w-2xl text-base leading-relaxed text-bosque-100/90 sm:text-lg">
          Veinticuatro años de datos sobre la pérdida de bosque en los 19 municipios de la
          jurisdicción CORPOURABA, en Urabá y el Occidente antioqueño. Explora el mapa, analiza las
          cifras, aprende con tu colegio y descarga todo en abierto.
        </p>

        <div className="mt-9 flex flex-wrap items-center gap-4">
          <Link
            ref={ctaRef}
            href="/mapa"
            className="brillo-cta relative inline-flex items-center gap-2 overflow-hidden rounded-full bg-alerta-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-alerta-500/25 transition-colors hover:bg-alerta-600"
          >
            <MapPin className="h-4 w-4" aria-hidden="true" />
            Explorar el mapa
          </Link>
          <Link
            href="/aprende"
            className="inline-flex items-center gap-2 rounded-full border border-white/30 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-white/10"
          >
            <TreePine className="h-4 w-4" aria-hidden="true" />
            Aprende con tu colegio
          </Link>
        </div>

        <ul className="mt-12 flex flex-wrap gap-x-8 gap-y-3 text-sm text-bosque-300">
          <li className="flex items-center gap-2">
            <MapPin className="h-4 w-4" aria-hidden="true" />
            <span className="font-display text-base font-semibold tabular-nums text-white" data-objetivo="19">
              0
            </span>{' '}
            municipios · 5 subregiones
          </li>
          <li className="flex items-center gap-2">
            <CalendarRange className="h-4 w-4" aria-hidden="true" />
            <span className="font-display text-base font-semibold tabular-nums text-white" data-objetivo="18">
              0
            </span>{' '}
            periodos de medición
          </li>
          <li className="flex items-center gap-2">
            <TreePine className="h-4 w-4" aria-hidden="true" />≈{' '}
            <span
              className="font-display text-base font-semibold tabular-nums text-white"
              data-objetivo="1.86"
              data-decimales="2"
            >
              0
            </span>{' '}
            millones de hectáreas de jurisdicción
          </li>
        </ul>
      </div>

      {/* Contador de bosque perdido (protagonista de la deforestación al scroll) */}
      <div className="pointer-events-none absolute inset-x-0 bottom-6 z-10 flex justify-center px-4">
        <p className="flex items-baseline gap-2 rounded-full border border-alerta-500/30 bg-bosque-950/60 px-5 py-2 text-sm text-bosque-100/80 backdrop-blur">
          <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-alerta-500" aria-hidden="true" />
          Bosque perdido&nbsp;
          <span ref={contadorRef} className="font-display text-lg font-semibold tabular-nums text-white">
            0
          </span>
          <span>ha (2000–2024)</span>
        </p>
      </div>

      {/* Cursor custom (solo desktop; se activa vía CSS media) */}
      {entorno.listo && !entorno.movil && !entorno.reduced && (
        <div ref={cursorRef} className="cursor-observatorio" aria-hidden="true" />
      )}
    </section>
  );
}
