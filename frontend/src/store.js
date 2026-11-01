import { create } from 'zustand';

export const useStore = create((set) => ({
  zoneDesenate: [],
  reguliActive: [],

  adaugaZona: (nouaZona) => set((state) => ({
    zoneDesenate: [...state.zoneDesenate, nouaZona]
  })),

  // Funcția nouă care salvează regula creată
  adaugaRegula: (nouaRegula) => set((state) => ({
    reguliActive: [...state.reguliActive, nouaRegula]
  })),

  stergeToateZonele: () => set({ zoneDesenate: [] })
}));