import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { TestButton, type TestState } from '@/components/settings/TestButton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { PasswordInput } from '@/components/ui/password-input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { normalizeMusicConfig, testMusicConfig } from '@/services/settingsService';
import type { MusicConfig, TTSConfig } from '@/types';

interface MusicSettingsProps {
  value: MusicConfig;
  ttsConfig: TTSConfig;
  errors?: Partial<Record<keyof MusicConfig, string>>;
  onChange: (patch: Partial<MusicConfig>) => void;
}

export function MusicSettings({ value, ttsConfig, errors, onChange }: MusicSettingsProps) {
  const { t } = useTranslation();
  const [testState, setTestState] = useState<TestState>('idle');
  const [testMessage, setTestMessage] = useState('');
  const normalizedValue = normalizeMusicConfig(value);
  const active = normalizedValue[normalizedValue.provider];

  const updateActive = (patch: Partial<typeof active>) => {
    onChange({ [normalizedValue.provider]: { ...active, ...patch } });
  };

  const copyTtsKey = () => {
    if (ttsConfig.provider === 'aliyun' && ttsConfig.api_key) {
      onChange({ aliyun: { ...normalizedValue.aliyun, api_key: ttsConfig.api_key } });
    }
  };

  const handleTest = async () => {
    setTestState('testing');
    try {
      await testMusicConfig(value);
      setTestState('ok');
      setTestMessage(t('settings.musicPermissionDeferred'));
    } catch (error) {
      setTestState('failed');
      setTestMessage(error instanceof Error ? error.message : String(error));
    }
  };

  return (
    <div className="space-y-5 py-4">
      <div className="space-y-2">
        <Label>{t('settings.musicProvider')}</Label>
        <Select
          value={normalizedValue.provider}
          onValueChange={(provider: 'minimax' | 'aliyun') => onChange({ provider })}
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="minimax">MiniMax</SelectItem>
            <SelectItem value="aliyun">{t('settings.aliyunBailian')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {normalizedValue.provider === 'aliyun' ? (
          <div className="space-y-2">
            <Label htmlFor="music-workspace">{t('settings.workspaceId')}</Label>
            <Input
              id="music-workspace"
              value={normalizedValue.aliyun.workspace_id}
              onChange={(event) => updateActive({ workspace_id: event.target.value })}
            />
          </div>
        ) : null}
        <div className="space-y-2">
          <Label htmlFor="music-api-key">{t('settings.apiKey')}</Label>
          <PasswordInput
            id="music-api-key"
            value={active.api_key}
            onChange={(event) => updateActive({ api_key: event.target.value })}
          />
          {normalizedValue.provider === 'aliyun' ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={ttsConfig.provider !== 'aliyun' || !ttsConfig.api_key}
              onClick={copyTtsKey}
            >
              {t('settings.copyAliyunTtsKey')}
            </Button>
          ) : null}
        </div>
      </div>

      <details className="rounded-xl border p-4">
        <summary className="cursor-pointer font-medium">{t('settings.advanced')}</summary>
        <div className="mt-4 space-y-2">
          <Label htmlFor="music-base-url">{t('settings.baseUrl')}</Label>
          <Input
            id="music-base-url"
            value={active.base_url}
            onChange={(event) => updateActive({ base_url: event.target.value })}
            placeholder={normalizedValue.provider === 'minimax' ? 'https://api.minimaxi.com/v1' : 'https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api/v1'}
            aria-invalid={Boolean(errors?.[normalizedValue.provider])}
          />
          <p className="text-xs text-muted-foreground">
            {normalizedValue.provider === 'minimax'
              ? t('settings.minimaxBaseUrlHint')
              : t('settings.musicBaseUrlHint')}
          </p>
        </div>
      </details>

      <div className="grid gap-4 sm:grid-cols-3">
        <ReadOnlyField label={t('settings.model')} value={active.model} />
        <ReadOnlyField label={t('settings.sourceFormat')} value={active.source_format.toUpperCase()} />
        <ReadOnlyField label={t('settings.finalFormat')} value="MP3" />
      </div>
      {normalizedValue.provider === 'minimax' ? (
        <ReadOnlyField label={t('settings.instrumental')} value={t('settings.enabled')} />
      ) : null}
      <ReadOnlyField label={t('settings.aigcWatermark')} value={t('settings.disabled')} />

      <TestButton
        state={testState}
        message={testMessage}
        onTest={handleTest}
        label={t('settings.checkMusicConfig')}
      />
    </div>
  );
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Input value={value} readOnly disabled />
    </div>
  );
}
