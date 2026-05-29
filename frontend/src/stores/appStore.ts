import { create } from 'zustand'

interface AppStore {
  demoMode: boolean
  setDemoMode: (v: boolean) => void
}

export const useAppStore = create<AppStore>((set) => ({
  demoMode: true,
  setDemoMode: (demoMode) => set({ demoMode }),
}))
