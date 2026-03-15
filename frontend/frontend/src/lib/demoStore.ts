import { create } from 'zustand';

interface DemoState {
  isActive: boolean;
  spotlightTarget: string | null;
  speed: number;
  toggleDemo: () => void;
  setSpotlight: (target: string | null) => void;
  setSpeed: (speed: number) => void;
  resetDemo: () => void;
}

export const useDemoStore = create<DemoState>((set) => ({
  isActive: false,
  spotlightTarget: null,
  speed: 1,
  toggleDemo: () => set((state) => ({ isActive: !state.isActive })),
  setSpotlight: (target) => set({ spotlightTarget: target }),
  setSpeed: (speed) => set({ speed }),
  resetDemo: () => set({ isActive: false, spotlightTarget: null, speed: 1 }),
}));
