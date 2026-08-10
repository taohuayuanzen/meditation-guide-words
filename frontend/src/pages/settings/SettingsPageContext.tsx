import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { useToast } from '@/hooks/useToast';
import { useSettingsStore } from '@/stores/settingsStore';
import { useTranslation } from 'react-i18next';
import type { Settings } from '@/types';
import { applyTheme } from '@/utils/theme';
import { validateSettings, type SettingsErrors } from '@/utils/settingsValidation';

export type SettingsSection = 'llm_config' | 'tts_config' | 'dify_config' | 'general_config';

interface SettingsPageState {
  settings: Settings | null;
  draft: Settings | null;
  errors: SettingsErrors;
  dirty: Record<SettingsSection, boolean>;
  saving: Record<SettingsSection, boolean>;
  loading: boolean;
  loadError: string;
}

interface SettingsPageContextValue extends SettingsPageState {
  updateDraft: <K extends SettingsSection>(key: K, patch: Partial<Settings[K]>) => void;
  saveSection: (key: SettingsSection) => Promise<void>;
  revertSection: (key: SettingsSection) => void;
  isDirty: boolean;
}

const SettingsPageContext = createContext<SettingsPageContextValue | null>(null);

function isEqualSection<T>(a: T, b: T): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function SettingsPageProvider({ children }: { children: React.ReactNode }) {
  const { t, i18n } = useTranslation();
  const { success, error: showError } = useToast();
  const settings = useSettingsStore((s) => s.settings);
  const loadSettings = useSettingsStore((s) => s.loadSettings);
  const persistSettings = useSettingsStore((s) => s.persistSettings);

  const [draft, setDraft] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [saving, setSaving] = useState<Record<SettingsSection, boolean>>({
    llm_config: false,
    tts_config: false,
    dify_config: false,
    general_config: false,
  });

  useEffect(() => {
    setLoading(true);
    void loadSettings()
      .catch((err) => {
        const message = err instanceof Error ? err.message : String(err);
        setLoadError(message);
        showError(message);
      })
      .finally(() => setLoading(false));
  }, [loadSettings, showError]);

  useEffect(() => {
    if (settings && !draft) {
      setDraft(structuredClone(settings));
    }
  }, [settings, draft]);

  const errors = useMemo<SettingsErrors>(() => {
    if (!draft) return {};
    return validateSettings(draft);
  }, [draft]);

  const dirty = useMemo<Record<SettingsSection, boolean>>(() => {
    if (!settings || !draft) {
      return { llm_config: false, tts_config: false, dify_config: false, general_config: false };
    }
    return {
      llm_config: !isEqualSection(settings.llm_config, draft.llm_config),
      tts_config: !isEqualSection(settings.tts_config, draft.tts_config),
      dify_config: !isEqualSection(settings.dify_config, draft.dify_config),
      general_config: !isEqualSection(settings.general_config, draft.general_config),
    };
  }, [settings, draft]);

  const isDirty = useMemo(() => Object.values(dirty).some(Boolean), [dirty]);

  useEffect(() => {
    if (!isDirty) return;

    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };

    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty]);

  const updateDraft = useCallback(
    <K extends SettingsSection>(key: K, patch: Partial<Settings[K]>) => {
      setDraft((prev) => {
        if (!prev) return prev;
        return { ...prev, [key]: { ...prev[key], ...patch } };
      });
    },
    [],
  );

  const saveSection = useCallback(
    async (key: SettingsSection) => {
      if (!draft || !settings) return;
      const sectionErrors = errors[key];
      if (sectionErrors && Object.keys(sectionErrors).length > 0) return;

      setSaving((prev) => ({ ...prev, [key]: true }));
      try {
        const nextSettings: Settings = { ...settings, [key]: draft[key] };
        await persistSettings(nextSettings);
        success(t('settings.saved'));
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        showError(message);
        throw err;
      } finally {
        setSaving((prev) => ({ ...prev, [key]: false }));
      }
    },
    [draft, settings, errors, persistSettings, success, showError, t],
  );

  const revertSection = useCallback(
    (key: SettingsSection) => {
      if (!settings) return;
      setDraft((prev) => (prev ? { ...prev, [key]: structuredClone(settings[key]) } : prev));
      if (key === 'general_config') {
        applyTheme(settings.general_config.theme);
        void i18n.changeLanguage(settings.general_config.language);
      }
    },
    [settings, i18n],
  );

  const value = useMemo<SettingsPageContextValue>(
    () => ({
      settings,
      draft,
      errors,
      dirty,
      saving,
      loading,
      loadError,
      updateDraft,
      saveSection,
      revertSection,
      isDirty,
    }),
    [
      settings,
      draft,
      errors,
      dirty,
      saving,
      loading,
      loadError,
      updateDraft,
      saveSection,
      revertSection,
      isDirty,
    ],
  );

  return <SettingsPageContext.Provider value={value}>{children}</SettingsPageContext.Provider>;
}

export function useSettingsPage() {
  const context = useContext(SettingsPageContext);
  if (!context) {
    throw new Error('useSettingsPage must be used within SettingsPageProvider');
  }
  return context;
}
