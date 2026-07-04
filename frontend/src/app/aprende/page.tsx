import type { Metadata } from 'next';
import ModuloAprende from '@/components/aprende/ModuloAprende';

export const metadata: Metadata = {
  title: 'Aprende (PRAES) · Observatorio de Deforestación de Urabá',
  description:
    'Módulo educativo interactivo sobre la deforestación en Urabá: storytelling por niveles, quiz, el juego «Salva el Bosque» e historias locales con datos reales.',
};

/** Módulo educativo tipo PRAES (SPEC §8.4). */
export default function PaginaAprende() {
  return <ModuloAprende />;
}
