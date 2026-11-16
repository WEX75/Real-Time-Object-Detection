import { create } from 'zustand';
import { apiService } from './api';

export const useStore = create((set) => ({
  zoneDesenate: [],
  reguliActive: [],
  alerteLive: [],
  statistici: {}, // Stochează contoarele sub forma: { "obiect_zona": { obiect, zona, total } }

  adaugaZona: async (nouaZona) => {
    await apiService.salveazaZona(nouaZona);
    set((state) => ({
      zoneDesenate: [...state.zoneDesenate, nouaZona]
    }));
  },

  stergeZona: async (idZona) => {
    await apiService.stergeZona(idZona);
    set((state) => ({
      zoneDesenate: state.zoneDesenate.filter((z) => z.id !== idZona),
      reguliActive: state.reguliActive.filter((r) => r.zonaId.toString() !== idZona.toString())
    }));
  },

  adaugaRegula: async (nouaRegula) => {
    await apiService.salveazaRegula(nouaRegula);
    set((state) => ({
      reguliActive: [...state.reguliActive, nouaRegula]
    }));
  },

  stergeRegula: async (idRegula) => {
    await apiService.stergeRegula(idRegula);
    set((state) => ({
      reguliActive: state.reguliActive.filter((r) => r.id !== idRegula)
    }));
  },

  adaugaAlerta: (alerta) => set((state) => {
    const cheie = `${alerta.obiect.trim().toLowerCase()}_${alerta.zona.trim().toLowerCase()}`;
    const intrareExistenta = state.statistici[cheie];

    return {
      alerteLive: [alerta, ...state.alerteLive].slice(0, 20),
      statistici: {
        ...state.statistici,
        [cheie]: {
          obiect: alerta.obiect,
          zona: alerta.zona,
          total: (intrareExistenta ? intrareExistenta.total : 0) + 1
        }
      }
    };
  }),

  golesteAlerte: () => set({ alerteLive: [] }),

  reseteazaStatistici: () => set({ statistici: {} })
}));