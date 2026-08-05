import { useTranslation } from 'react-i18next';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { GeneralConfig } from '@/types';
import { applyTheme } from '@/utils/theme';

interface GeneralSettingsProps {
  value: GeneralConfig;
  errors?: Partial<Record<keyof GeneralConfig, string>>;
  onChange: (patch: Partial<GeneralConfig>) => void;
}

export function GeneralSettings({ value, errors, onChange }: GeneralSettingsProps) {
  const { t, i18n } = useTranslation();

  const handleLanguage = (lang: string) => {
    onChange({ language: lang });
    void i18n.changeLanguage(lang);
  };

  const handleTheme = (theme: string) => {
    onChange({ theme });
    applyTheme(theme);
  };

  const fieldError = (key: keyof GeneralConfig) => {
    const code = errors?.[key];
    if (!code) return null;
    return code === 'required' ? t('settings.required') : t(`settings.${code}`);
  };

  return (
    <div className="space-y-4 py-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="gen-language">{t('settings.language')}</Label>
          <Select value={value.language} onValueChange={handleLanguage}>
            <SelectTrigger id="gen-language">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="zh">{t('settings.langZh')}</SelectItem>
              <SelectItem value="en">{t('settings.langEn')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="gen-theme">{t('settings.theme')}</Label>
          <Select value={value.theme} onValueChange={handleTheme}>
            <SelectTrigger id="gen-theme">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="light">{t('settings.themeLight')}</SelectItem>
              <SelectItem value="dark">{t('settings.themeDark')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="gen-output-dir">{t('settings.audioOutputDir')}</Label>
        <Input
          id="gen-output-dir"
          value={value.audio_output_dir}
          onChange={(e) => onChange({ audio_output_dir: e.target.value })}
          placeholder="./data/audio"
          aria-invalid={!!errors?.audio_output_dir}
        />
        {fieldError('audio_output_dir') ? (
          <p className="text-xs text-destructive">{fieldError('audio_output_dir')}</p>
        ) : null}
      </div>
    </div>
  );
}
