import { TTSSettings } from '@/components/settings/TTSSettings';
import { SettingsSectionPage } from '@/pages/settings/SettingsSectionPage';
import { useSettingsPage } from '@/pages/settings/SettingsPageContext';

export function TTSSettingsPage() {
  const { draft, errors, updateDraft } = useSettingsPage();
  if (!draft) return null;

  return (
    <SettingsSectionPage section="tts_config" titleKey="settings.tts">
      <TTSSettings
        value={draft.tts_config}
        errors={errors.tts_config}
        onChange={(patch) => updateDraft('tts_config', patch)}
      />
    </SettingsSectionPage>
  );
}
