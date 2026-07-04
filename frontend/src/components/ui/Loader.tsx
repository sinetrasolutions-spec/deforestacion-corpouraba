/**
 * Indicador de carga accesible. Se usa mientras llegan datos del API.
 */
import clsx from 'clsx';

export interface LoaderProps {
  texto?: string;
  className?: string;
}

export default function Loader({ texto = 'Cargando datos…', className }: LoaderProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={clsx(
        'flex items-center justify-center gap-3 py-8 text-sm text-[color:var(--tinta-suave)]',
        className,
      )}
    >
      <span
        aria-hidden="true"
        className="h-5 w-5 animate-spin rounded-full border-2 border-bosque-300 border-t-bosque-600 motion-reduce:animate-none"
      />
      <span>{texto}</span>
    </div>
  );
}
