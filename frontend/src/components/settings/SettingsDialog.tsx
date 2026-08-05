import { Settings } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { DifySettings } from '@/components/settings/DifySettings';
import { GeneralSettings } from '@/components/settings/GeneralSettings';
import { LLMSettings } from '@/components/settings/LLMSettings';
import { TTSSettings } from '@/components/settings/TTSSettings';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/useToast';
import { useSettingsStore } from '@/stores/settingsStore';
import type { Settings as SettingsData } from '@/types';
import { applyTheme } from '@/utils/theme';
import { hasErrors, validateSettings } from '@/utils/settingsValidation';

const TAB_KEY = 'meditation-settings-tab';

function isEqualSettings(a: SettingsData, b: SettingsData) {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function SettingsDialog() {
  const { t, i18n } = useTranslation();
  const { success, error: showError } = useToast();
  const settings = useSettingsStore((s) => s.settings);
  const loadSettings = useSettingsStore((s) => s.loadSettings);
  const persistSettings = useSettingsStore((s) => s.persistSettings);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<SettingsData | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState(() => localStorage.getItem(TAB_KEY) ?? 'llm');

  useEffect(() => {
    if (!open) return;
    setError('');
    if (!useSettingsStore.getState().settings) {
      void loadSettings().catch((err) => {
        setError(err instanceof Error ? err.message : String(err));
      });
    }
  }, [open, loadSettings]);

  useEffect(() => {
    if (settings && !draft) setDraft(structuredClone(settings));
  }, [settings, draft]);

  const validationErrors = useMemo(() => {
    if (!draft) return {};
    return validateSettings(draft);
  }, [draft]);

  const hasChanges = useMemo(() => {
    if (!settings || !draft) return false;
    return !isEqualSettings(settings, draft);
  }, [settings, draft]);

  const updateBlock = <K extends keyof SettingsData>(key: K, patch: Partial<SettingsData[K]>) => {
    setDraft((prev) => (prev ? { ...prev, [key]: { ...prev[key], ...patch } } : prev));
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen && hasChanges) {
      const confirmed = window.confirm(t('common.unsavedChanges'));
      if (!confirmed) return;
      revertPreview();
    }
    setOpen(nextOpen);
    if (!nextOpen) {
      setDraft(null);
    }
  };

  const revertPreview = () => {
    if (settings) {
      applyTheme(settings.general_config.theme);
      void i18n.changeLanguage(settings.general_config.language);
    }
  };

  const handleSaveAll = async () => {
    if (!draft) return;
    setSaving(true);
    setError('');
    try {
      await persistSettings(draft);
      applyTheme(draft.general_config.theme);
      void i18n.changeLanguage(draft.general_config.language);
      success(t('settings.saved'));
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      showError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleTabChange = (value: string) => {
    setActiveTab(value);
    localStorage.setItem(TAB_KEY, value);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={t('settings.title')}>
          <Settings className="h-5 w-5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="flex max-h-[90vh] max-w-2xl flex-col">
        <DialogHeader>
          <DialogTitle>{t('settings.title')}</DialogTitle>
        </DialogHeader>
        <Tabs
          value={activeTab}
          onValueChange={handleTabChange}
          className="flex flex-1 flex-col overflow-hidden"
        >
          <TabsList className="grid w-full shrink-0 grid-cols-4">
            <TabsTrigger value="llm">{t('settings.llm')}</TabsTrigger>
            <TabsTrigger value="tts">{t('settings.tts')}</TabsTrigger>
            <TabsTrigger value="dify">{t('settings.dify')}</TabsTrigger>
            <TabsTrigger value="general">{t('settings.general')}</TabsTrigger>
          </TabsList>
          <div className="min-h-0 flex-1 overflow-y-auto py-2">
            {draft ? (
              <>
                <TabsContent value="llm" className="mt-0">
                  <LLMSettings
                    value={draft.llm_config}
                    errors={validationErrors.llm_config}
                    onChange={(patch) => updateBlock('llm_config', patch)}
                  />
                </TabsContent>
                <TabsContent value="tts" className="mt-0">
                  <TTSSettings
                    value={draft.tts_config}
                    errors={validationErrors.tts_config}
                    onChange={(patch) => updateBlock('tts_config', patch)}
                  />
                </TabsContent>
                <TabsContent value="dify" className="mt-0">
                  <DifySettings
                    value={draft.dify_config}
                    errors={validationErrors.dify_config}
                    onChange={(patch) => updateBlock('dify_config', patch)}
                  />
                </TabsContent>
                <TabsContent value="general" className="mt-0">
                  <GeneralSettings
                    value={draft.general_config}
                    errors={validationErrors.general_config}
                    onChange={(patch) => updateBlock('general_config', patch)}
                  />
                </TabsContent>
              </>
            ) : (
              <div className="space-y-4 py-4">
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-8 w-2/3" />
              </div>
            )}
          </div>
        </Tabs>

        {error ? (
          <Alert variant="destructive" className="mb-2">
            <AlertTitle>{t('settings.saveFailed')}</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <div className="flex shrink-0 items-center justify-between border-t pt-4">
          <div className="text-sm text-muted-foreground">
            {hasChanges ? t('settings.unsavedHint') : null}
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => handleOpenChange(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={() => void handleSaveAll()}
              disabled={saving || !draft || !hasChanges || hasErrors(validationErrors)}
            >
              {saving ? t('settings.saving') : t('settings.saveAll')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
