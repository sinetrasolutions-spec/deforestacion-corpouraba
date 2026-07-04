import type { Config } from 'tailwindcss';

/**
 * Configuración Tailwind del Observatorio de Deforestación CORPOURABA.
 * Tokens de color y tipografía según SPEC §7.1 — NO modificar los valores.
 */
const config: Config = {
  darkMode: 'class',
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        bosque: {
          50: '#ECF8F0',
          100: '#D2EEDC',
          300: '#7BC796',
          500: '#2E8B57',
          600: '#1F7347',
          700: '#175E3A',
          800: '#0F4A2D',
          900: '#0B3D25',
          950: '#062818',
        },
        alerta: {
          50: '#FFF8F1',
          100: '#FEECDC',
          300: '#FDBA74',
          500: '#F97316',
          600: '#EA580C',
          700: '#C2410C',
          800: '#9A3412',
          900: '#7C2D12',
        },
        fuego: {
          500: '#DC2626',
          700: '#B91C1C',
          900: '#7F1D1D',
        },
        tierra: {
          100: '#F5F0E8',
          300: '#D9CDB8',
          500: '#A8927A',
          700: '#6B5744',
        },
      },
      fontFamily: {
        display: ['var(--font-display)'],
        body: ['var(--font-body)'],
      },
    },
  },
  plugins: [],
};

export default config;
