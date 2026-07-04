/**
 * Estado global compartido (zustand) — contrato EXACTO del SPEC §6.4.
 * Lo usan el mapa (periodo/timelapse/capas) y el dashboard (filtros).
 */
import { create } from 'zustand';

export interface AppState {
  periodoActivo: string;             // default '2022-2023'
  metrica: 'hectareas'|'hectareas_anuales';
  reproduciendo: boolean;            // timelapse
  capasActivas: string[];            // ids de overlays + 'hotspots'
  municipioSeleccionado: string|null;// codigo_dane
  incluirEstimados: boolean;         // default true
  setPeriodo(p: string): void; setMetrica(m: AppState['metrica']): void;
  toggleReproduccion(): void; toggleCapa(id: string): void;
  setMunicipio(c: string|null): void; setIncluirEstimados(v: boolean): void;
}

export const useAppStore = create<AppState>((set) => ({
  periodoActivo: '2022-2023',
  metrica: 'hectareas',
  reproduciendo: false,
  capasActivas: [],
  municipioSeleccionado: null,
  incluirEstimados: true,

  setPeriodo: (p) => set({ periodoActivo: p }),
  setMetrica: (m) => set({ metrica: m }),
  toggleReproduccion: () => set((s) => ({ reproduciendo: !s.reproduciendo })),
  toggleCapa: (id) =>
    set((s) => ({
      capasActivas: s.capasActivas.includes(id)
        ? s.capasActivas.filter((c) => c !== id)
        : [...s.capasActivas, id],
    })),
  setMunicipio: (c) => set({ municipioSeleccionado: c }),
  setIncluirEstimados: (v) => set({ incluirEstimados: v }),
}));

export default useAppStore;
