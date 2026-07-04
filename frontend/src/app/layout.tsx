import type { Metadata } from 'next';
import { Fraunces, Inter } from 'next/font/google';
import 'leaflet/dist/leaflet.css';
import './globals.css';
import Navbar from '@/components/ui/Navbar';
import Footer from '@/components/ui/Footer';

/*
 * Fuentes autoalojadas vía next/font (sin CDN en runtime, SPEC §3 y §7.1):
 * Fraunces para titulares (aire editorial-cartográfico) e Inter para cuerpo.
 */
const fraunces = Fraunces({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-body',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'Observatorio de Deforestación de Urabá · CORPOURABA',
    template: '%s · Observatorio de Deforestación de Urabá',
  },
  description:
    'Plataforma para explorar, analizar, aprender y descargar los datos de deforestación ' +
    'de los 19 municipios de la jurisdicción CORPOURABA (Urabá y Occidente antioqueño), 2000–2024.',
  keywords: ['deforestación', 'Urabá', 'CORPOURABA', 'bosque', 'Antioquia', 'datos abiertos'],
};

/*
 * Script mínimo ejecutado ANTES de pintar el contenido: aplica la clase
 * `dark` según localStorage ('tema') o la preferencia del sistema, para
 * evitar el destello de tema incorrecto (FOUC).
 */
const SCRIPT_TEMA = `
(function () {
  try {
    var guardado = localStorage.getItem('tema');
    var oscuro = guardado ? guardado === 'oscuro'
      : window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.classList.toggle('dark', oscuro);
  } catch (e) { /* sin acceso a localStorage: se queda el tema claro */ }
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="es"
      suppressHydrationWarning
      className={`${fraunces.variable} ${inter.variable}`}
    >
      <body className="flex min-h-screen flex-col font-body antialiased">
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
        <Navbar />
        <main id="contenido" className="flex-1">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
