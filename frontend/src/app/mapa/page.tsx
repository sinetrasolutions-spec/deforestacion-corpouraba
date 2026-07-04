import type { Metadata } from 'next';
import MapaObservatorio from '@/components/mapa/MapaObservatorio';

export const metadata: Metadata = {
  title: 'Mapa interactivo · Observatorio de Deforestación de Urabá',
  description:
    'Mapa dinámico de la deforestación en los 19 municipios de CORPOURABA (2000–2024): coropletas por periodo, línea de tiempo, hotspots y capas de contexto.',
};

/**
 * Página del mapa interactivo (SPEC §8.2). El mapa Leaflet vive en un
 * componente cliente cargado dinámicamente (ssr:false) desde MapaObservatorio.
 */
export default function PaginaMapa() {
  return <MapaObservatorio />;
}
