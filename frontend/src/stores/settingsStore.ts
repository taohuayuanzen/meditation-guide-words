import { create } from 'zustand';

import { fetchSettings, saveSettings } from '@/services/settingsService';
import type { Settings } from '@/types';

interface SettingsState {
  settings: Settings | null;
  loadSettings: () => Promise<void>;
  persistSettings: (settings: Settings) => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: null,
  loadSettings: async () => {
    const settings = await fetchSettings();
    set({ settings });
  },
  persistSettings: async (settings) => {
    await saveSettings(settings);
    set({ settings });
  },
}));
