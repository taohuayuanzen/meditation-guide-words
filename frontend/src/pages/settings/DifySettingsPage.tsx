import { DifySettings } from '@/components/settings/DifySettings';
import { SettingsSectionPage } from '@/pages/settings/SettingsSectionPage';
import { useSettingsPage } from '@/pages/settings/SettingsPageContext';

export function DifySettingsPage() {
  const { draft, errors, updateDraft } = useSettingsPage();
  if (!draft) return null;

  return (
    <SettingsSectionPage section="dify_config" titleKey="settings.dify">
      <DifySettings
        value={draft.dify_config}
        errors={errors.dify_config}
        onChange={(patch) => updateDraft('dify_config', patch)}
      />
    </SettingsSectionPage>
  );
}
