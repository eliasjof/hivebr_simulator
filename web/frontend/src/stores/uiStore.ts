import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'

interface UIState {
  theme: 'dark' | 'light'
  setTheme: (theme: 'dark' | 'light') => void
  toggleTheme: () => void

  panels: Record<string, boolean>
  togglePanel: (name: string) => void
  openPanel: (name: string) => void
  closePanel: (name: string) => void
  isPanelOpen: (name: string) => boolean

  simulatorView: '2d' | '3d'
  setSimulatorView: (view: '2d' | '3d') => void

  showGrid: boolean
  toggleGrid: () => void

  showLidar: boolean
  toggleLidar: () => void

  showPaths: boolean
  togglePaths: () => void

  showWaypoints: boolean
  toggleWaypoints: () => void

  cameraLocked: boolean
  setCameraLocked: (locked: boolean) => void
}

export const useUIStore = create<UIState>()(
  subscribeWithSelector((set, get) => ({
    theme: 'dark',
    setTheme: (theme) => set({ theme }),
    toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),

    panels: {
      logs: true,
      plots: false,
      config: false,
      trackEditor: false,
    },
    togglePanel: (name) => set((state) => ({ panels: { ...state.panels, [name]: !state.panels[name] } })),
    openPanel: (name) => set((state) => ({ panels: { ...state.panels, [name]: true } })),
    closePanel: (name) => set((state) => ({ panels: { ...state.panels, [name]: false } })),
    isPanelOpen: (name) => get().panels[name] ?? false,

    simulatorView: '2d',
    setSimulatorView: (view) => set({ simulatorView: view }),

    showGrid: true,
    toggleGrid: () => set((state) => ({ showGrid: !state.showGrid })),

    showLidar: false,
    toggleLidar: () => set((state) => ({ showLidar: !state.showLidar })),

    showPaths: true,
    togglePaths: () => set((state) => ({ showPaths: !state.showPaths })),

    showWaypoints: true,
    toggleWaypoints: () => set((state) => ({ showWaypoints: !state.showWaypoints })),

    cameraLocked: false,
    setCameraLocked: (locked) => set({ cameraLocked: locked }),
  }))
)