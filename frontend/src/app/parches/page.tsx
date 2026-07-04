import type { Metadata } from 'next';
import ExploradorParches from '@/components/parches/ExploradorParches';

export const metadata: Metadata = {
  title: 'Visor de deforestación · Observatorio de Deforestación de Urabá',
  description:
    'Visor interactivo de la deforestación en la jurisdicción de CORPOURABA, 2000–2024: recorra los periodos con la barra de tiempo y active las capas de la cartografía oficial (áreas protegidas, resguardos, cuencas, títulos mineros y más).',
};

/** Explorador de parches de deforestación (vista dedicada). */
export default function PaginaParches() {
  return <ExploradorParches />;
}
