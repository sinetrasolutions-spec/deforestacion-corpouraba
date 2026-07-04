/**
 * Encabezado de sección con estilo editorial: etiqueta pequeña (eyebrow),
 * titular Fraunces y subtítulo opcional.
 */
import clsx from 'clsx';

export interface SectionHeadingProps {
  titulo: string;
  subtitulo?: string;
  etiqueta?: string;
  centrado?: boolean;
  id?: string;
  className?: string;
}

export default function SectionHeading({
  titulo,
  subtitulo,
  etiqueta,
  centrado = false,
  id,
  className,
}: SectionHeadingProps) {
  return (
    <div className={clsx('max-w-3xl', centrado && 'mx-auto text-center', className)}>
      {etiqueta && (
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bosque-600 dark:text-bosque-300">
          {etiqueta}
        </p>
      )}
      <h2
        id={id}
        className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl"
      >
        {titulo}
      </h2>
      {subtitulo && (
        <p className="mt-3 text-base leading-relaxed text-[color:var(--tinta-suave)]">
          {subtitulo}
        </p>
      )}
    </div>
  );
}
