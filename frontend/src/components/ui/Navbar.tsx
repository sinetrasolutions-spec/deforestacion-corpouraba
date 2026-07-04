'use client';

/**
 * Barra de navegación principal. Sticky con desenfoque de fondo; colapsa a
 * menú hamburguesa en móvil. Marca el enlace activo según la ruta.
 */
import { useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Menu, X } from 'lucide-react';
import clsx from 'clsx';
import ThemeToggle from './ThemeToggle';

const ENLACES = [
  { href: '/', etiqueta: 'Inicio' },
  { href: '/dashboard', etiqueta: 'Dashboard' },
  { href: '/mapa', etiqueta: 'Mapa' },
  { href: '/parches', etiqueta: 'Visor' },
  { href: '/aprende', etiqueta: 'Aprende' },
  { href: '/datos', etiqueta: 'Datos' },
] as const;

export default function Navbar() {
  const ruta = usePathname();
  const [abierto, setAbierto] = useState(false);

  // Cierra el menú móvil al navegar a otra ruta
  useEffect(() => {
    setAbierto(false);
  }, [ruta]);

  function esActivo(href: string): boolean {
    if (href === '/') return ruta === '/';
    return ruta === href || ruta.startsWith(`${href}/`);
  }

  return (
    <header className="sticky top-0 z-50 border-b border-[color:var(--borde)] bg-white/85 backdrop-blur dark:bg-bosque-950/85">
      <nav aria-label="Navegación principal" className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        {/* Marca */}
        <Link href="/" className="flex items-center gap-2.5" aria-label="Inicio — Observatorio de Deforestación de Urabá">
          {/* El logo institucional va sobre chip blanco para conservar su fondo en modo oscuro */}
          <span className="flex h-10 shrink-0 items-center rounded-lg bg-white px-1.5 shadow-sm ring-1 ring-black/5">
            <Image
              src="/logo-corpouraba.png"
              alt="Logo de CORPOURABA"
              width={87}
              height={35}
              priority
              className="h-[35px] w-auto"
            />
          </span>
          <span className="max-w-[15rem] leading-tight">
            <span className="block font-display text-sm font-semibold leading-tight tracking-tight sm:text-[15px]">
              Observatorio de Deforestación CORPOURABA
            </span>
            <span className="block text-[10px] uppercase tracking-widest text-[color:var(--tinta-suave)]">
              Monitoreo de bosques · 2000–2024
            </span>
          </span>
        </Link>

        {/* Enlaces escritorio */}
        <div className="hidden items-center gap-1 md:flex">
          {ENLACES.map(({ href, etiqueta }) => (
            <Link
              key={href}
              href={href}
              aria-current={esActivo(href) ? 'page' : undefined}
              className={clsx(
                'rounded-full px-4 py-2 text-sm font-medium transition-colors',
                esActivo(href)
                  ? 'bg-bosque-100 text-bosque-800 dark:bg-bosque-800 dark:text-bosque-100'
                  : 'text-[color:var(--tinta-suave)] hover:bg-bosque-50 hover:text-bosque-700 dark:hover:bg-bosque-900 dark:hover:text-bosque-300',
              )}
            >
              {etiqueta}
            </Link>
          ))}
          <ThemeToggle className="ml-2" />
        </div>

        {/* Controles móvil */}
        <div className="flex items-center gap-2 md:hidden">
          <ThemeToggle />
          <button
            type="button"
            onClick={() => setAbierto((v) => !v)}
            aria-expanded={abierto}
            aria-controls="menu-movil"
            aria-label={abierto ? 'Cerrar menú' : 'Abrir menú'}
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-[color:var(--borde)] bg-[color:var(--superficie)] text-[color:var(--tinta-suave)]"
          >
            {abierto ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </nav>

      {/* Menú móvil desplegable */}
      {abierto && (
        <div id="menu-movil" className="border-t border-[color:var(--borde)] bg-[color:var(--superficie)] md:hidden">
          <ul className="mx-auto max-w-7xl space-y-1 px-4 py-3">
            {ENLACES.map(({ href, etiqueta }) => (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={esActivo(href) ? 'page' : undefined}
                  className={clsx(
                    'block rounded-xl px-4 py-2.5 text-sm font-medium',
                    esActivo(href)
                      ? 'bg-bosque-100 text-bosque-800 dark:bg-bosque-800 dark:text-bosque-100'
                      : 'text-[color:var(--tinta-suave)] hover:bg-bosque-50 dark:hover:bg-bosque-900',
                  )}
                >
                  {etiqueta}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </header>
  );
}
