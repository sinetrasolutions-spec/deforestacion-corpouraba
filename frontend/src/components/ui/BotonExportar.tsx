'use client';

/**
 * Botón de exportación reutilizable para los gráficos del dashboard:
 * - PNG: captura el nodo referenciado con html-to-image (fondo según tema).
 * - CSV: descarga contenido generado en cliente (con BOM UTF-8) o una URL
 *   directa del API (urlDescarga).
 * Renderiza solo las opciones para las que recibió props.
 */
import { useState } from 'react';
import { toPng } from 'html-to-image';
import { FileImage, FileSpreadsheet } from 'lucide-react';
import clsx from 'clsx';

export interface BotonExportarProps {
  /** Nodo a capturar como PNG (ref del contenedor del gráfico). */
  objetivoRef?: React.RefObject<HTMLElement>;
  /** Nombre base del archivo, sin extensión. */
  nombreArchivo: string;
  /** Genera el contenido CSV en cliente (se antepone BOM UTF-8). */
  obtenerCsv?: () => string;
  /** Alternativa: URL de descarga directa del API (p. ej. urlDescarga(...)). */
  urlCsv?: string;
  className?: string;
}

/** Dispara la descarga de un href como archivo. */
function descargar(href: string, nombre: string) {
  const ancla = document.createElement('a');
  ancla.href = href;
  ancla.download = nombre;
  document.body.appendChild(ancla);
  ancla.click();
  ancla.remove();
}

export default function BotonExportar({
  objetivoRef,
  nombreArchivo,
  obtenerCsv,
  urlCsv,
  className,
}: BotonExportarProps) {
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function exportarPng() {
    const nodo = objetivoRef?.current;
    if (!nodo || ocupado) return;
    setOcupado(true);
    setError(null);
    try {
      const esOscuro = document.documentElement.classList.contains('dark');
      const dataUrl = await toPng(nodo, {
        pixelRatio: 2,
        cacheBust: true,
        backgroundColor: esOscuro ? '#0A1410' : '#FFFFFF',
      });
      descargar(dataUrl, `${nombreArchivo}.png`);
    } catch {
      setError('No se pudo generar el PNG');
    } finally {
      setOcupado(false);
    }
  }

  function exportarCsv() {
    setError(null);
    if (urlCsv) {
      descargar(urlCsv, `${nombreArchivo}.csv`);
      return;
    }
    if (!obtenerCsv) return;
    try {
      // BOM UTF-8 (U+FEFF) para que Excel abra bien las tildes
      const bom = String.fromCharCode(0xfeff);
      const blob = new Blob([bom + obtenerCsv()], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      descargar(url, `${nombreArchivo}.csv`);
      URL.revokeObjectURL(url);
    } catch {
      setError('No se pudo generar el CSV');
    }
  }

  const hayPng = Boolean(objetivoRef);
  const hayCsv = Boolean(obtenerCsv || urlCsv);
  if (!hayPng && !hayCsv) return null;

  const estiloBoton =
    'inline-flex items-center gap-1.5 rounded-full border border-[color:var(--borde)] ' +
    'bg-[color:var(--superficie)] px-3 py-1.5 text-xs font-medium text-[color:var(--tinta-suave)] ' +
    'transition-colors hover:border-bosque-300 hover:text-bosque-700 ' +
    'dark:hover:text-bosque-300 disabled:cursor-not-allowed disabled:opacity-50';

  return (
    <div className={clsx('flex items-center gap-2', className)}>
      {hayPng && (
        <button
          type="button"
          onClick={exportarPng}
          disabled={ocupado}
          className={estiloBoton}
          aria-label={`Exportar ${nombreArchivo} como imagen PNG`}
        >
          <FileImage className="h-3.5 w-3.5" aria-hidden="true" />
          {ocupado ? 'Generando…' : 'PNG'}
        </button>
      )}
      {hayCsv && (
        <button
          type="button"
          onClick={exportarCsv}
          className={estiloBoton}
          aria-label={`Descargar ${nombreArchivo} como CSV`}
        >
          <FileSpreadsheet className="h-3.5 w-3.5" aria-hidden="true" />
          CSV
        </button>
      )}
      {error && (
        <span role="alert" className="text-xs text-fuego-500">
          {error}
        </span>
      )}
    </div>
  );
}
