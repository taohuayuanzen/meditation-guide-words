import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';

import { GeneralSettings } from '@/components/settings/GeneralSettings';
import { SettingsSectionPage } from '@/pages/settings/SettingsSectionPage';
import { useSettingsPage } from '@/pages/settings/SettingsPageContext';
import { applyTheme } from '@/utils/theme';

export function GeneralSettingsPage() {
  const { i18n } = useTranslation();
  const { draft, settings, errors, dirty, updateDraft } = useSettingsPage();

  const draftRef = useRef(draft);
  const settingsRef = useRef(settings);
  const dirtyRef = useRef(dirty);

  draftRef.current = draft;
  settingsRef.current = settings;
  dirtyRef.current = dirty;

  useEffect(() => {
    const currentDraft = draftRef.current;
    if (currentDraft) {
      applyTheme(currentDraft.general_config.theme);
      void i18n.changeLanguage(currentDraft.general_config.language);
    }

    return () => {
      const wasDirty = dirtyRef.current.general_config;
      const savedSettings = settingsRef.current;
      if (wasDirty && savedSettings) {
        applyTheme(savedSettings.general_config.theme);
        void i18n.changeLanguage(savedSettings.general_config.language);
      }
    };
  }, [i18n]);

  if (!draft) return null;

  return (
    <SettingsSectionPage section="general_config" titleKey="settings.general">
      <GeneralSettings
        value={draft.general_config}
        errors={errors.general_config}
        onChange={(patch) => updateDraft('general_config', patch)}
      />
    </SettingsSectionPage>
  );
}
