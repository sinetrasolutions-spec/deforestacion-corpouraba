/**
 * Pie de página institucional. Componente de servidor (sin interactividad).
 */
import Image from 'next/image';
import Link from 'next/link';

const MODULOS = [
  { href: '/dashboard', etiqueta: 'Dashboard analítico' },
  { href: '/mapa', etiqueta: 'Mapa interactivo' },
  { href: '/parches', etiqueta: 'Visor de deforestación' },
  { href: '/aprende', etiqueta: 'Aprende (PRAES)' },
  { href: '/datos', etiqueta: 'Centro de descargas' },
];

const RECURSOS = [
  { href: '/datos', etiqueta: 'Diccionario de datos' },
  { href: '/datos', etiqueta: 'Metodología y fuentes' },
  { href: '/aprende', etiqueta: 'Guía docente' },
];

export default function Footer() {
  const ano = new Date().getFullYear();

  return (
    <footer className="border-t border-[color:var(--borde)] bg-bosque-950 text-bosque-100">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        <div className="grid gap-10 md:grid-cols-[2fr_1fr_1fr]">
          {/* Identidad institucional */}
          <div>
            <div className="flex items-center gap-3">
              <span className="flex h-11 shrink-0 items-center rounded-lg bg-white px-2">
                <Image
                  src="/logo-corpouraba.png"
                  alt="Logo de CORPOURABA"
                  width={97}
                  height={39}
                  className="h-[39px] w-auto"
                />
              </span>
              <p className="font-display text-lg font-semibold text-white">
                Observatorio de Deforestación de Urabá
              </p>
            </div>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-bosque-300">
              CORPOURABA — Corporación para el Desarrollo Sostenible del Urabá.
              Datos procesados del monitoreo de bosque en los 19 municipios de la
              jurisdicción (Urabá y Occidente antioqueño), periodo 2000–2024.
            </p>
            <p className="mt-3 text-xs text-bosque-300/80">
              Cartografía base: © OpenStreetMap · © CARTO. Coordenadas en WGS84 (EPSG:4326).
            </p>
          </div>

          {/* Módulos */}
          <nav aria-label="Módulos del observatorio">
            <p className="text-xs font-semibold uppercase tracking-widest text-bosque-300">Módulos</p>
            <ul className="mt-4 space-y-2">
              {MODULOS.map(({ href, etiqueta }) => (
                <li key={etiqueta}>
                  <Link href={href} className="text-sm text-bosque-100 transition-colors hover:text-white hover:underline">
                    {etiqueta}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          {/* Recursos */}
          <nav aria-label="Recursos y documentación">
            <p className="text-xs font-semibold uppercase tracking-widest text-bosque-300">Recursos</p>
            <ul className="mt-4 space-y-2">
              {RECURSOS.map(({ href, etiqueta }) => (
                <li key={etiqueta}>
                  <Link href={href} className="text-sm text-bosque-100 transition-colors hover:text-white hover:underline">
                    {etiqueta}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>

        <div className="mt-10 border-t border-bosque-800 pt-6 text-xs text-bosque-300">
          <p>
            © {ano} CORPOURABA · Observatorio de Deforestación. Datos abiertos con fines
            de gestión ambiental y educación.
          </p>
          <p className="mt-2">
            Nota de honestidad: los periodos 2010-2012, 2015-2016, 2018-2019 y 2023-2024
            contienen valores estimados o calibrados y se señalan siempre con un distintivo visual.
          </p>
          <p className="mt-2 text-[11px] text-bosque-300/70">
            Esta plataforma fue creada por Alberto Vivas y Carlos Zuluaga.
          </p>
        </div>
      </div>
    </footer>
  );
}
