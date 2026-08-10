import { LLMSettings } from '@/components/settings/LLMSettings';
import { SettingsSectionPage } from '@/pages/settings/SettingsSectionPage';
import { useSettingsPage } from '@/pages/settings/SettingsPageContext';

export function LLMSettingsPage() {
  const { draft, errors, updateDraft } = useSettingsPage();
  if (!draft) return null;

  return (
    <SettingsSectionPage section="llm_config" titleKey="settings.llm">
      <LLMSettings
        value={draft.llm_config}
        errors={errors.llm_config}
        onChange={(patch) => updateDraft('llm_config', patch)}
      />
    </SettingsSectionPage>
  );
}
