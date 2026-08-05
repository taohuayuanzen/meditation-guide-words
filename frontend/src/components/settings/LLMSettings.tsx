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
import { testLLM } from '@/services/settingsService';
import type { LLMConfig } from '@/types';

interface LLMSettingsProps {
  value: LLMConfig;
  errors?: Partial<Record<keyof LLMConfig, string>>;
  onChange: (patch: Partial<LLMConfig>) => void;
}

const PROVIDERS = [
  { value: 'deepseek', labelKey: 'settings.providerDeepseek' },
  { value: 'kimi', labelKey: 'settings.providerKimi' },
  { value: 'custom', labelKey: 'settings.providerCustom' },
];

export function LLMSettings({ value, errors, onChange }: LLMSettingsProps) {
  const { t } = useTranslation();
  const [testState, setTestState] = useState<TestState>('idle');
  const [testMessage, setTestMessage] = useState('');

  const handleTest = async () => {
    setTestState('testing');
    try {
      await testLLM(value);
      setTestState('ok');
    } catch (err) {
      setTestState('failed');
      setTestMessage(err instanceof Error ? err.message : String(err));
    }
  };

  const fieldError = (key: keyof LLMConfig) => {
    const code = errors?.[key];
    if (!code) return null;
    return code === 'invalidUrl' ? t('settings.invalidUrl') : t(`settings.${code}`);
  };

  return (
    <div className="space-y-4 py-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="llm-provider">{t('settings.provider')}</Label>
          <Select value={value.provider} onValueChange={(v) => onChange({ provider: v })}>
            <SelectTrigger id="llm-provider">
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
          <Label htmlFor="llm-model">{t('settings.model')}</Label>
          <Input
            id="llm-model"
            value={value.model}
            onChange={(e) => onChange({ model: e.target.value })}
            placeholder="deepseek-chat"
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="llm-base-url">{t('settings.baseUrl')}</Label>
        <Input
          id="llm-base-url"
          value={value.base_url}
          onChange={(e) => onChange({ base_url: e.target.value })}
          placeholder="https://api.deepseek.com/v1"
          aria-invalid={!!errors?.base_url}
        />
        {fieldError('base_url') ? (
          <p className="text-xs text-destructive">{fieldError('base_url')}</p>
        ) : null}
      </div>
      <div className="space-y-2">
        <Label htmlFor="llm-api-key">{t('settings.apiKey')}</Label>
        <PasswordInput
          id="llm-api-key"
          value={value.api_key}
          onChange={(e) => onChange({ api_key: e.target.value })}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="llm-temperature">
            {t('settings.temperature')}（{value.temperature}）
          </Label>
          <Input
            id="llm-temperature"
            type="range"
            min={0}
            max={2}
            step={0.1}
            value={value.temperature}
            onChange={(e) => onChange({ temperature: Number.parseFloat(e.target.value) })}
            aria-invalid={!!errors?.temperature}
          />
          {fieldError('temperature') ? (
            <p className="text-xs text-destructive">{fieldError('temperature')}</p>
          ) : null}
        </div>
        <div className="space-y-2">
          <Label htmlFor="llm-max-tokens">{t('settings.maxTokens')}</Label>
          <Input
            id="llm-max-tokens"
            type="number"
            min={1}
            value={value.max_tokens ?? ''}
            onChange={(e) =>
              onChange({ max_tokens: e.target.value === '' ? null : Number(e.target.value) })
            }
            placeholder={t('common.optional')}
            aria-invalid={!!errors?.max_tokens}
          />
          {fieldError('max_tokens') ? (
            <p className="text-xs text-destructive">{fieldError('max_tokens')}</p>
          ) : null}
        </div>
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
