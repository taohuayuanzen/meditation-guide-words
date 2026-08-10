import { useTranslation } from 'react-i18next';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useSettingsPage, type SettingsSection } from '@/pages/settings/SettingsPageContext';

interface SettingsSectionPageProps {
  section: SettingsSection;
  titleKey: string;
  children: React.ReactNode;
}

export function SettingsSectionPage({ section, titleKey, children }: SettingsSectionPageProps) {
  const { t } = useTranslation();
  const { errors, dirty, saving, saveSection } = useSettingsPage();

  const sectionErrors = errors[section];
  const isDirty = dirty[section];
  const isSaving = saving[section];
  const hasSectionErrors = sectionErrors !== undefined && Object.keys(sectionErrors).length > 0;

  const handleSave = async () => {
    try {
      await saveSection(section);
    } catch {
      // error already shown by context
    }
  };

  return (
    <div className="mx-auto max-w-3xl pb-24">
      <h2 className="mb-6 text-2xl font-bold">{t(titleKey)}</h2>

      {hasSectionErrors ? (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>{t('settings.validationError')}</AlertTitle>
          <AlertDescription>{t('settings.fixBeforeSave')}</AlertDescription>
        </Alert>
      ) : null}

      <div className="space-y-6">{children}</div>

      <div className="fixed bottom-0 right-0 left-56 flex items-center justify-end gap-4 border-t bg-background/95 px-6 py-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <span className="text-sm text-muted-foreground">
          {isDirty ? t('settings.unsavedHint') : t('settings.allSaved')}
        </span>
        <Button
          onClick={() => void handleSave()}
          disabled={isSaving || !isDirty || hasSectionErrors}
        >
          {isSaving ? t('settings.saving') : t('settings.save')}
        </Button>
      </div>
    </div>
  );
}
