import { create } from 'zustand';

export const useStore = create((set) => ({
  zoneDesenate: [],
  reguliActive: [],

  adaugaZona: (nouaZona) => set((state) => ({
    zoneDesenate: [...state.zoneDesenate, nouaZona]
  })),

  stergeZona: (idZona) => set((state) => ({
    zoneDesenate: state.zoneDesenate.filter((z) => z.id !== idZona),
    // Ștergem automat și regulile asociate acestei zone
    reguliActive: state.reguliActive.filter((r) => r.zonaId.toString() !== idZona.toString())
  })),

  adaugaRegula: (nouaRegula) => set((state) => ({
    reguliActive: [...state.reguliActive, nouaRegula]
  })),

  stergeRegula: (idRegula) => set((state) => ({
    reguliActive: state.reguliActive.filter((r) => r.id !== idRegula)
  })),

  stergeToateZonele: () => set({ zoneDesenate: [], reguliActive: [] })
}));