'use client';

/**
 * Juego «Salva el Bosque» (SPEC §8.4). Tablero 8×8: aparecen brotes y amenazas
 * (🔥🪓) que se propagan a celdas vecinas cada turno (900 ms). El jugador
 * apaga amenazas y siembra en celdas vacías. 90 s de partida. Accesible por
 * teclado (cada celda es un button) y respeta prefers-reduced-motion.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Pause, Play, RotateCcw } from 'lucide-react';
import { fmtNum } from '@/lib/format';

type Celda = 'vacia' | 'brote' | 'arbol' | 'amenaza';
const LADO = 8;
const TOTAL = LADO * LADO;
const DURACION = 90; // segundos
const TICK = 900; // ms

function tableroInicial(): Celda[] {
  const t: Celda[] = Array(TOTAL).fill('vacia');
  // Siembra inicial de árboles y algún brote
  for (let i = 0; i < 10; i += 1) t[Math.floor((i * 6.1) % TOTAL)] = 'arbol';
  t[27] = 'amenaza';
  t[36] = 'amenaza';
  return t;
}

function vecinos(idx: number): number[] {
  const fila = Math.floor(idx / LADO);
  const col = idx % LADO;
  const res: number[] = [];
  [-1, 0, 1].forEach((df) =>
    [-1, 0, 1].forEach((dc) => {
      if (df === 0 && dc === 0) return;
      const f = fila + df;
      const c = col + dc;
      if (f >= 0 && f < LADO && c >= 0 && c < LADO) res.push(f * LADO + c);
    }),
  );
  return res;
}

export default function SalvaBosque() {
  const [tablero, setTablero] = useState<Celda[]>(tableroInicial);
  const [jugando, setJugando] = useState(false);
  const [tiempo, setTiempo] = useState(DURACION);
  const [salvadas, setSalvadas] = useState(0);
  const [perdidas, setPerdidas] = useState(0);
  const [fin, setFin] = useState(false);
  // pseudoaleatorio determinista (evita Math.random en SSR/hydration mismatch)
  const semilla = useRef(12345);
  const rnd = useCallback(() => {
    semilla.current = (semilla.current * 1103515245 + 12345) & 0x7fffffff;
    return semilla.current / 0x7fffffff;
  }, []);

  // Cuenta regresiva
  useEffect(() => {
    if (!jugando) return;
    const t = setInterval(() => {
      setTiempo((s) => {
        if (s <= 1) {
          setJugando(false);
          setFin(true);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [jugando]);

  // Turno del bosque: amenazas se propagan, brotes crecen a árbol
  useEffect(() => {
    if (!jugando) return;
    const t = setInterval(() => {
      setTablero((prev) => {
        const next = [...prev];
        let nuevasPerdidas = 0;
        prev.forEach((c, i) => {
          if (c === 'amenaza' && rnd() < 0.35) {
            const vs = vecinos(i).filter((v) => next[v] === 'arbol' || next[v] === 'brote');
            if (vs.length) {
              const objetivo = vs[Math.floor(rnd() * vs.length)];
              next[objetivo] = 'amenaza';
              nuevasPerdidas += 1;
            }
          } else if (c === 'brote' && rnd() < 0.5) {
            next[i] = 'arbol';
          }
        });
        // aparición ocasional de un brote y una amenaza nueva
        if (rnd() < 0.6) {
          const libres = next.map((c, i) => (c === 'vacia' ? i : -1)).filter((i) => i >= 0);
          if (libres.length) next[libres[Math.floor(rnd() * libres.length)]] = 'brote';
        }
        if (rnd() < 0.25) {
          const arboles = next.map((c, i) => (c === 'arbol' ? i : -1)).filter((i) => i >= 0);
          if (arboles.length) next[arboles[Math.floor(rnd() * arboles.length)]] = 'amenaza';
        }
        if (nuevasPerdidas) setPerdidas((p) => p + nuevasPerdidas);
        return next;
      });
    }, TICK);
    return () => clearInterval(t);
  }, [jugando, rnd]);

  function tocar(i: number) {
    if (!jugando) return;
    setTablero((prev) => {
      const next = [...prev];
      if (next[i] === 'amenaza') {
        next[i] = 'vacia';
        setSalvadas((s) => s + 1);
      } else if (next[i] === 'vacia') {
        next[i] = 'brote';
      }
      return next;
    });
  }

  function iniciar() {
    setTablero(tableroInicial());
    setTiempo(DURACION);
    setSalvadas(0);
    setPerdidas(0);
    setFin(false);
    semilla.current = 12345 + Math.floor(tiempo);
    setJugando(true);
  }

  const arbolesVivos = tablero.filter((c) => c === 'arbol' || c === 'brote').length;
  // 1 acción de rescate ≈ 5 ha (referencia lúdica). Mutatá pierde ~160 ha/año.
  const haSalvadas = salvadas * 5;
  const pctMutata = Math.min(Math.round((haSalvadas / 160) * 100), 999);

  return (
    <div className="rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-display text-xl font-semibold">🌳 Salva el Bosque</h3>
          <p className="text-sm text-[color:var(--tinta-suave)]">
            Apaga las amenazas 🔥🪓 y siembra 🌱 en las casillas vacías. ¡Tienes 90 segundos!
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!jugando && (
            <button
              type="button"
              onClick={iniciar}
              className="inline-flex items-center gap-1.5 rounded-full bg-bosque-600 px-4 py-2 text-sm font-medium text-white hover:bg-bosque-700"
            >
              {fin ? <RotateCcw className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              {fin ? 'Jugar otra vez' : 'Empezar'}
            </button>
          )}
          {jugando && (
            <button
              type="button"
              onClick={() => setJugando(false)}
              className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--borde)] px-4 py-2 text-sm font-medium"
            >
              <Pause className="h-4 w-4" /> Pausa
            </button>
          )}
        </div>
      </div>

      <div className="mb-3 grid grid-cols-3 gap-2 text-center text-sm">
        <div className="rounded-lg bg-[color:var(--fondo)] py-2">
          <p className="text-[11px] text-[color:var(--tinta-suave)]">Tiempo</p>
          <p className="font-display text-xl font-semibold">{tiempo}s</p>
        </div>
        <div className="rounded-lg bg-bosque-50 py-2 dark:bg-bosque-900/50">
          <p className="text-[11px] text-[color:var(--tinta-suave)]">Bosque vivo</p>
          <p className="font-display text-xl font-semibold text-bosque-700 dark:text-bosque-300">{arbolesVivos}</p>
        </div>
        <div className="rounded-lg bg-alerta-50 py-2 dark:bg-alerta-900/40">
          <p className="text-[11px] text-[color:var(--tinta-suave)]">Amenazas apagadas</p>
          <p className="font-display text-xl font-semibold text-alerta-700 dark:text-alerta-300">{salvadas}</p>
        </div>
      </div>

      <div
        className="mx-auto grid max-w-md gap-1"
        style={{ gridTemplateColumns: `repeat(${LADO}, minmax(0, 1fr))` }}
        role="grid"
        aria-label="Tablero del juego Salva el Bosque"
      >
        {tablero.map((c, i) => {
          const icono = c === 'arbol' ? '🌳' : c === 'brote' ? '🌱' : c === 'amenaza' ? (i % 2 ? '🔥' : '🪓') : '';
          const fondo =
            c === 'amenaza'
              ? 'bg-fuego-500/20 hover:bg-fuego-500/30'
              : c === 'arbol'
              ? 'bg-bosque-100 dark:bg-bosque-900/60'
              : c === 'brote'
              ? 'bg-bosque-50 dark:bg-bosque-900/40'
              : 'bg-[color:var(--fondo)] hover:bg-bosque-50 dark:hover:bg-bosque-900/40';
          return (
            <button
              key={i}
              type="button"
              onClick={() => tocar(i)}
              disabled={!jugando}
              aria-label={`Casilla ${i + 1}: ${c}`}
              className={`flex aspect-square items-center justify-center rounded-md border border-[color:var(--borde)] text-lg transition-colors disabled:cursor-default ${fondo}`}
            >
              <span aria-hidden="true">{icono}</span>
            </button>
          );
        })}
      </div>

      {/* Barra de hectáreas salvadas */}
      <div className="mt-4">
        <div className="mb-1 flex justify-between text-xs text-[color:var(--tinta-suave)]">
          <span>Hectáreas rescatadas (equivalente lúdico)</span>
          <span>{fmtNum(haSalvadas)} ha</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-[color:var(--borde)]">
          <div
            className="h-full rounded-full bg-bosque-600 transition-all"
            style={{ width: `${Math.min((haSalvadas / 160) * 100, 100)}%` }}
          />
        </div>
      </div>

      {fin && (
        <div className="mt-4 rounded-xl border border-bosque-300 bg-bosque-50 p-4 text-center dark:border-bosque-700 dark:bg-bosque-900/50">
          <p className="font-display text-lg font-semibold">¡Fin del juego!</p>
          <p className="mt-1 text-sm text-[color:var(--tinta-suave)]">
            Apagaste <strong>{salvadas}</strong> amenazas y dejaste que se propagaran{' '}
            <strong>{perdidas}</strong>. Rescataste el equivalente a{' '}
            <strong>{fmtNum(haSalvadas)} ha</strong>: cerca del <strong>{pctMutata}%</strong> de lo
            que Mutatá pierde en un año (~160 ha/año). ¡Cada acción cuenta en el bosque real!
          </p>
        </div>
      )}
    </div>
  );
}
