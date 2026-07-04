'use client';

/**
 * Contenedor del módulo de mapa (SPEC §8.2). Carga el lienzo Leaflet de forma
 * dinámica (ssr:false, obligatorio con react-leaflet) y orquesta panel lateral,
 * controles de tiempo y capas mediante el store global.
 */
import dynamic from 'next/dynamic';
import Loader from '@/components/ui/Loader';

const LienzoMapa = dynamic(() => import('./LienzoMapa'), {
  ssr: false,
  loading: () => (
    <div className="flex h-[calc(100vh-4rem)] items-center justify-center bg-[color:var(--fondo)]">
      <Loader texto="Cargando mapa…" />
    </div>
  ),
});

export default function MapaObservatorio() {
  return <LienzoMapa />;
}
