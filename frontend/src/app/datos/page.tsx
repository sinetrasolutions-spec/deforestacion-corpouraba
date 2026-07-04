import type { Metadata } from 'next';
import CentroDatos from '@/components/datos/CentroDatos';

export const metadata: Metadata = {
  title: 'Datos y descargas · Observatorio de Deforestación de Urabá',
  description:
    'Descargue la serie municipal, capas GeoJSON, hotspots y productos de análisis de la deforestación CORPOURABA 2000–2024. Diccionario y metodología incluidos.',
};

/** Centro de descargas y metodología (SPEC §8.5). */
export default function PaginaDatos() {
  return <CentroDatos />;
}
