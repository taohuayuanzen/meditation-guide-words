import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { TestButton } from '@/components/settings/TestButton';
import type { TestState } from '@/components/settings/TestButton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { PasswordInput } from '@/components/ui/password-input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { testTTS } from '@/services/settingsService';
import type { TTSConfig } from '@/types';

interface TTSSettingsProps {
  value: TTSConfig;
  errors?: Partial<Record<keyof TTSConfig, string>>;
  onChange: (patch: Partial<TTSConfig>) => void;
}

const PROVIDERS = [
  { value: 'volcano', labelKey: 'settings.providerVolcano' },
  { value: 'aliyun', labelKey: 'settings.providerAliyun' },
];

export function TTSSettings({ value, errors, onChange }: TTSSettingsProps) {
  const { t } = useTranslation();
  const [testState, setTestState] = useState<TestState>('idle');
  const [testMessage, setTestMessage] = useState('');

  const handleTest = async () => {
    setTestState('testing');
    try {
      await testTTS(value);
      setTestState('ok');
    } catch (err) {
      setTestState('failed');
      setTestMessage(err instanceof Error ? err.message : String(err));
    }
  };

  const fieldError = (key: keyof TTSConfig) => {
    const code = errors?.[key];
    if (!code) return null;
    if (code === 'required') return t('settings.required');
    if (code === 'invalidRange') return t('settings.invalidRange');
    return t(`settings.${code}`);
  };

  return (
    <div className="space-y-4 py-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="tts-provider">{t('settings.provider')}</Label>
          <Select value={value.provider} onValueChange={(v) => onChange({ provider: v })}>
            <SelectTrigger id="tts-provider">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PROVIDERS.map((p) => (
                <SelectItem key={p.value} value={p.value}>
                  {t(p.labelKey)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="tts-voice-id">{t('settings.voiceId')}</Label>
          <Input
            id="tts-voice-id"
            value={value.voice_id}
            onChange={(e) => onChange({ voice_id: e.target.value })}
            placeholder="BV001_streaming / sambert-zhichu-v1"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="tts-api-key">{t('settings.apiKey')}</Label>
          <PasswordInput
            id="tts-api-key"
            value={value.api_key}
            onChange={(e) => onChange({ api_key: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="tts-secret-key">{t('settings.secretKey')}</Label>
          <PasswordInput
            id="tts-secret-key"
            value={value.secret_key}
            onChange={(e) => onChange({ secret_key: e.target.value })}
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="tts-appid">{t('settings.appid')}</Label>
          <Input
            id="tts-appid"
            value={value.appid}
            onChange={(e) => onChange({ appid: e.target.value })}
            aria-invalid={!!errors?.appid}
          />
          {fieldError('appid') ? (
            <p className="text-xs text-destructive">{fieldError('appid')}</p>
          ) : null}
        </div>
        <div className="space-y-2">
          <Label htmlFor="tts-cluster">{t('settings.cluster')}</Label>
          <Input
            id="tts-cluster"
            value={value.cluster}
            onChange={(e) => onChange({ cluster: e.target.value })}
            placeholder="volcano_tts"
            aria-invalid={!!errors?.cluster}
          />
          {fieldError('cluster') ? (
            <p className="text-xs text-destructive">{fieldError('cluster')}</p>
          ) : null}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="tts-speed">
            {t('settings.speed')}（{value.speed}）
          </Label>
          <Input
            id="tts-speed"
            type="range"
            min={0.5}
            max={2}
            step={0.1}
            value={value.speed}
            onChange={(e) => onChange({ speed: Number.parseFloat(e.target.value) })}
            aria-invalid={!!errors?.speed}
          />
          {fieldError('speed') ? (
            <p className="text-xs text-destructive">{fieldError('speed')}</p>
          ) : null}
        </div>
        <div className="space-y-2">
          <Label htmlFor="tts-volume">
            {t('settings.volume')}（{value.volume}）
          </Label>
          <Input
            id="tts-volume"
            type="range"
            min={0}
            max={2}
            step={0.1}
            value={value.volume}
            onChange={(e) => onChange({ volume: Number.parseFloat(e.target.value) })}
            aria-invalid={!!errors?.volume}
          />
          {fieldError('volume') ? (
            <p className="text-xs text-destructive">{fieldError('volume')}</p>
          ) : null}
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="tts-format">{t('settings.outputFormat')}</Label>
        <Select value={value.output_format} onValueChange={(v) => onChange({ output_format: v })}>
          <SelectTrigger id="tts-format">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="mp3">mp3</SelectItem>
            <SelectItem value="wav">wav</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <TestButton
        state={testState}
        message={testMessage}
        onTest={handleTest}
        label={t('settings.test')}
      />
    </div>
  );
}
