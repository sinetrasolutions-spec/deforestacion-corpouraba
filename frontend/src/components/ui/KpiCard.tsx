'use client';

/**
 * Tarjeta KPI con contador animado al entrar en el viewport.
 * Respeta prefers-reduced-motion (el valor se pinta directo sin animación).
 * Reutilizada por la landing y por el dashboard (que la recalcula al filtrar).
 */
import { useEffect, useRef } from 'react';
import { animate, useInView, useReducedMotion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import clsx from 'clsx';
import { fmtNum } from '@/lib/format';
import Badge from './Badge';

export interface KpiCardProps {
  /** Rótulo corto del indicador, p. ej. «Total deforestado». */
  titulo: string;
  /** Valor numérico final del contador. */
  valor: number;
  /** Texto secundario bajo el valor (periodo, municipio, aclaración…). */
  detalle?: string;
  /** Icono lucide opcional. */
  icono?: LucideIcon;
  /** Marca el dato como estimado (badge distintivo obligatorio, SPEC §7.2). */
  estimado?: boolean;
  /** Decimales del formateo por defecto (fmtNum es-CO). */
  decimales?: number;
  /** Formateador alternativo del valor (p. ej. fmtHa o fmtPct). */
  formato?: (n: number) => string;
  /** Retraso de la animación en segundos (para escalonar tarjetas). */
  retraso?: number;
  className?: string;
}

export default function KpiCard({
  titulo,
  valor,
  detalle,
  icono: Icono,
  estimado = false,
  decimales = 0,
  formato,
  retraso = 0,
  className,
}: KpiCardProps) {
  const refTarjeta = useRef<HTMLDivElement>(null);
  const refValor = useRef<HTMLSpanElement>(null);
  const valorPrevio = useRef(0);
  const enVista = useInView(refTarjeta, { once: true, margin: '-40px 0px' });
  const reducirMovimiento = useReducedMotion();

  useEffect(() => {
    const nodo = refValor.current;
    if (!nodo || !enVista) return;

    const formatear = formato ?? ((n: number) => fmtNum(n, decimales));

    // Con movimiento reducido pintamos el valor final sin animar
    if (reducirMovimiento) {
      nodo.textContent = formatear(valor);
      valorPrevio.current = valor;
      return;
    }

    const controles = animate(valorPrevio.current, valor, {
      duration: 1.2,
      delay: retraso,
      ease: 'easeOut',
      onUpdate: (v) => {
        nodo.textContent = formatear(v);
      },
    });
    valorPrevio.current = valor;
    return () => controles.stop();
    // `formato` suele declararse inline: lo excluimos a propósito para no reiniciar
    // la animación en cada render del padre.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enVista, valor, reducirMovimiento, decimales, retraso]);

  const formatearFinal = formato ?? ((n: number) => fmtNum(n, decimales));

  return (
    <div
      ref={refTarjeta}
      className={clsx(
        'relative rounded-2xl border border-[color:var(--borde)] bg-[color:var(--superficie)] p-5 shadow-sm',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-[color:var(--tinta-suave)]">
          {titulo}
        </p>
        {Icono && (
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-bosque-50 text-bosque-600 dark:bg-bosque-900 dark:text-bosque-300">
            <Icono className="h-4 w-4" aria-hidden="true" />
          </span>
        )}
      </div>

      <p className="mt-3 font-display text-3xl font-semibold tracking-tight sm:text-4xl">
        {/* El span animado se oculta a lectores de pantalla; el valor final va en sr-only */}
        <span aria-hidden="true" ref={refValor}>
          {formatearFinal(0)}
        </span>
        <span className="sr-only">{formatearFinal(valor)}</span>
      </p>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        {detalle && <p className="text-sm text-[color:var(--tinta-suave)]">{detalle}</p>}
        {estimado && <Badge variante="estimado">estimado</Badge>}
      </div>
    </div>
  );
}
