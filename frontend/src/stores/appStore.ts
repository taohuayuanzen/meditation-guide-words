import { create } from 'zustand';

export type Workspace = 'script' | 'audio' | 'artifact';

interface AppState {
  currentWorkspace: Workspace;
  sidebarCollapsed: boolean;
  mobileMenuOpen: boolean;
  setWorkspace: (workspace: Workspace) => void;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setMobileMenuOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentWorkspace: 'script',
  sidebarCollapsed: false,
  mobileMenuOpen: false,
  setWorkspace: (workspace) => set({ currentWorkspace: workspace }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
  setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
}));
