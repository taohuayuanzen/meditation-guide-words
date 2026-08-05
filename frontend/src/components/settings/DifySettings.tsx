import { useTranslation } from 'react-i18next';

import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { PasswordInput } from '@/components/ui/password-input';
import type { DifyConfig } from '@/types';

interface DifySettingsProps {
  value: DifyConfig;
  errors?: Partial<Record<keyof DifyConfig, string>>;
  onChange: (patch: Partial<DifyConfig>) => void;
}

export function DifySettings({ value, errors, onChange }: DifySettingsProps) {
  const { t } = useTranslation();

  const fieldError = (key: keyof DifyConfig) => {
    const code = errors?.[key];
    if (!code) return null;
    return code === 'invalidUrl' ? t('settings.invalidUrl') : t(`settings.${code}`);
  };

  return (
    <div className="space-y-4 py-4">
      <div className="space-y-2">
        <Label htmlFor="dify-base-url">{t('settings.difyBaseUrl')}</Label>
        <Input
          id="dify-base-url"
          value={value.base_url}
          onChange={(e) => onChange({ base_url: e.target.value })}
          placeholder="http://localhost/v1"
          aria-invalid={!!errors?.base_url}
        />
        {fieldError('base_url') ? (
          <p className="text-xs text-destructive">{fieldError('base_url')}</p>
        ) : null}
      </div>
      <div className="space-y-2">
        <Label htmlFor="dify-script-key">{t('settings.scriptAppKey')}</Label>
        <PasswordInput
          id="dify-script-key"
          value={value.script_app_key}
          onChange={(e) => onChange({ script_app_key: e.target.value })}
          placeholder="app-xxxxxxxxxxxxxxxx"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="dify-audio-key">{t('settings.audioAppKey')}</Label>
        <PasswordInput
          id="dify-audio-key"
          value={value.audio_app_key}
          onChange={(e) => onChange({ audio_app_key: e.target.value })}
          placeholder="app-xxxxxxxxxxxxxxxx"
        />
      </div>
      <p className="text-sm text-muted-foreground">{t('settings.difyHint')}</p>
    </div>
  );
}
