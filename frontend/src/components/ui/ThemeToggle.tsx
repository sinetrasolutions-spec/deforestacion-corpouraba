'use client';

/**
 * Alternador de tema claro/oscuro. La clase `dark` vive en <html> y se
 * persiste en localStorage bajo la clave 'tema' ('claro' | 'oscuro').
 * El valor inicial lo aplica el script inline del layout (default: sistema).
 */
import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import clsx from 'clsx';

export default function ThemeToggle({ className }: { className?: string }) {
  // null = aún no montado (evita desajustes de hidratación)
  const [oscuro, setOscuro] = useState<boolean | null>(null);

  useEffect(() => {
    setOscuro(document.documentElement.classList.contains('dark'));
  }, []);

  function alternar() {
    const nuevo = !(oscuro ?? false);
    setOscuro(nuevo);
    document.documentElement.classList.toggle('dark', nuevo);
    try {
      localStorage.setItem('tema', nuevo ? 'oscuro' : 'claro');
    } catch {
      // localStorage no disponible: el cambio aplica solo a esta vista
    }
  }

  return (
    <button
      type="button"
      onClick={alternar}
      aria-label={oscuro ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
      title={oscuro ? 'Tema claro' : 'Tema oscuro'}
      className={clsx(
        'inline-flex h-9 w-9 items-center justify-center rounded-full border',
        'border-[color:var(--borde)] bg-[color:var(--superficie)] text-[color:var(--tinta-suave)]',
        'transition-colors hover:text-bosque-600 dark:hover:text-bosque-300',
        className,
      )}
    >
      {/* Antes de montar se muestra el sol para no romper la hidratación */}
      {oscuro ? <Sun className="h-4 w-4" aria-hidden="true" /> : <Moon className="h-4 w-4" aria-hidden="true" />}
    </button>
  );
}
