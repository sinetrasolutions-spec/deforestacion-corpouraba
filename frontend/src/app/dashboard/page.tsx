import type { Metadata } from 'next';
import { Suspense } from 'react';
import Loader from '@/components/ui/Loader';
import PanelDashboard from '@/components/dashboard/PanelDashboard';

export const metadata: Metadata = {
  title: 'Dashboard analítico · Observatorio de Deforestación de Urabá',
  description:
    'Indicadores, series temporales, ranking, comparador, mapa de calor, predicción y hallazgos de la deforestación en CORPOURABA 2000–2024.',
};

/** Página del dashboard analítico (SPEC §8.3). */
export default function PaginaDashboard() {
  return (
    <Suspense fallback={<Loader texto="Cargando dashboard…" className="min-h-[60vh]" />}>
      <PanelDashboard />
    </Suspense>
  );
}
