import { MusicSettings } from '@/components/settings/MusicSettings';
import { SettingsSectionPage } from '@/pages/settings/SettingsSectionPage';
import { useSettingsPage } from '@/pages/settings/SettingsPageContext';

export function MusicSettingsPage() {
  const { draft, errors, updateDraft } = useSettingsPage();
  if (!draft) return null;

  return (
    <SettingsSectionPage section="music_config" titleKey="settings.music">
      <MusicSettings
        value={draft.music_config}
        ttsConfig={draft.tts_config}
        errors={errors.music_config}
        onChange={(patch) => updateDraft('music_config', patch)}
      />
    </SettingsSectionPage>
  );
}
