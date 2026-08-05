import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

import { useSettingsStore } from '@/stores/settingsStore';
import { applyTheme } from '@/utils/theme';

export function useAppBootstrap() {
  const { i18n } = useTranslation();
  const loadSettings = useSettingsStore((s) => s.loadSettings);

  useEffect(() => {
    void loadSettings()
      .then(() => {
        const settings = useSettingsStore.getState().settings;
        if (!settings) return;
        if (settings.general_config.language) {
          void i18n.changeLanguage(settings.general_config.language);
        }
        applyTheme(settings.general_config.theme);
      })
      .catch(() => undefined);
  }, [i18n, loadSettings]);
}
