/**
 * Insignia compacta para estados y distinciones. La variante 'estimado'
 * (borde discontinuo ámbar) es la señal visual obligatoria del SPEC §7.2
 * para datos estimados en tooltips, leyendas y tarjetas.
 */
import clsx from 'clsx';

export type VarianteBadge = 'estimado' | 'neutro' | 'exito' | 'alerta' | 'info';

const ESTILOS: Record<VarianteBadge, string> = {
  estimado:
    'border border-dashed border-alerta-500 bg-alerta-50 text-alerta-700 dark:bg-alerta-900/40 dark:text-alerta-300',
  neutro:
    'border border-[color:var(--borde)] bg-[color:var(--superficie)] text-[color:var(--tinta-suave)]',
  exito:
    'border border-bosque-300 bg-bosque-50 text-bosque-700 dark:border-bosque-700 dark:bg-bosque-900/60 dark:text-bosque-300',
  alerta:
    'border border-alerta-300 bg-alerta-100 text-alerta-800 dark:border-alerta-700 dark:bg-alerta-900/40 dark:text-alerta-300',
  info:
    'border border-tierra-300 bg-tierra-100 text-tierra-700 dark:border-tierra-700 dark:bg-tierra-700/30 dark:text-tierra-300',
};

export interface BadgeProps {
  children: React.ReactNode;
  variante?: VarianteBadge;
  className?: string;
  title?: string;
}

export default function Badge({ children, variante = 'neutro', className, title }: BadgeProps) {
  return (
    <span
      title={title}
      className={clsx(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium leading-4',
        ESTILOS[variante],
        className,
      )}
    >
      {children}
    </span>
  );
}
