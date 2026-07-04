'use client';

/**
 * Explorador de parches de deforestación. Carga el lienzo Leaflet de forma
 * dinámica (ssr:false) — react-leaflet no puede renderizarse en el servidor.
 */
import dynamic from 'next/dynamic';
import Loader from '@/components/ui/Loader';

const LienzoParches = dynamic(() => import('./LienzoParches'), {
  ssr: false,
  loading: () => (
    <div className="flex h-[calc(100vh-4rem)] items-center justify-center bg-[color:var(--fondo)]">
      <Loader texto="Cargando polígonos…" />
    </div>
  ),
});

export default function ExploradorParches() {
  return <LienzoParches />;
}
