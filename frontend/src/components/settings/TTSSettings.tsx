import { useMemo, useState, useEffect } from 'react';
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

const ALIYUN_MODELS = [
  { value: 'qwen-audio-3.0-tts-plus', labelKey: 'settings.modelQwenAudioPlus' },
  { value: 'qwen-audio-3.0-tts-flash', labelKey: 'settings.modelQwenAudioFlash' },
  { value: 'cosyvoice-v3-flash', labelKey: 'settings.modelCosyVoiceFlash' },
];

const DEFAULT_ALIYUN_BASE_URL = 'https://dashscope.aliyuncs.com/api/v1';

const ALIYUN_VOICES: Record<string, { value: string; labelKey: string }[]> = {
  'qwen-audio-3.0-tts-plus': [
    { value: 'longanlingxin', labelKey: 'settings.voiceLonganlingxin' },
    { value: 'longanlufeng', labelKey: 'settings.voiceLonganlufeng' },
  ],
  'qwen-audio-3.0-tts-flash': [
    { value: 'longanfengyue', labelKey: 'settings.voiceLonganfengyue' },
    { value: 'longanyuanfei', labelKey: 'settings.voiceLonganyuanfei' },
    { value: 'longanlingxi', labelKey: 'settings.voiceLonganlingxi' },
    { value: 'longanxiaoxin', labelKey: 'settings.voiceLonganxiaoxin' },
    { value: 'longanhuan_v3.6', labelKey: 'settings.voiceLonganhuan' },
    { value: 'longjielidou_v3.6', labelKey: 'settings.voiceLongjielidou' },
    { value: 'longpaopao_v3.6', labelKey: 'settings.voiceLongpaopao' },
    { value: 'longhuohuo_v3.6', labelKey: 'settings.voiceLonghuohuo' },
    { value: 'longchuanshu_v3.6', labelKey: 'settings.voiceLongchuanshu' },
    { value: 'loongmary', labelKey: 'settings.voiceLoongmary' },
    { value: 'loongeva_v3.6', labelKey: 'settings.voiceLoongeva' },
    { value: 'loongjohn', labelKey: 'settings.voiceLoongjohn' },
  ],
  'cosyvoice-v3-flash': [
    { value: 'longanyang', labelKey: 'settings.voiceLonganyang' },
    { value: 'longanhuan_v3', labelKey: 'settings.voiceLonganhuanV3' },
  ],
};

const CUSTOM_VOICE = 'custom';

export function TTSSettings({ value, errors, onChange }: TTSSettingsProps) {
  const { t } = useTranslation();

  const isAliyun = value.provider === 'aliyun';

  const currentVoices = useMemo(() => {
    return ALIYUN_VOICES[value.model] ?? [];
  }, [value.model]);

  const isPresetVoice = currentVoices.some((v) => v.value === value.voice_id);
  const isCustomVoice = !isPresetVoice && isAliyun;
  const [customVoice, setCustomVoice] = useState(isPresetVoice || !isAliyun ? '' : value.voice_id);

  useEffect(() => {
    if (!isAliyun) {
      setCustomVoice('');
      return;
    }
    if (!isPresetVoice && value.voice_id !== CUSTOM_VOICE) {
      setCustomVoice(value.voice_id);
    }
  }, [isAliyun, isPresetVoice, value.voice_id]);

  const handleProviderChange = (provider: string) => {
    const patch: Partial<TTSConfig> = { provider };
    if (provider === 'aliyun') {
      patch.model = value.model || 'qwen-audio-3.0-tts-plus';
      patch.base_url = value.base_url || DEFAULT_ALIYUN_BASE_URL;
      patch.voice_id = value.voice_id || ALIYUN_VOICES['qwen-audio-3.0-tts-plus'][0].value;
      patch.secret_key = '';
      patch.appid = '';
      patch.cluster = 'volcano_tts';
    }
    onChange(patch);
  };

  const handleModelChange = (model: string) => {
    const voices = ALIYUN_VOICES[model] ?? [];
    const firstVoice = voices[0]?.value ?? '';
    const newVoice = voices.some((v) => v.value === value.voice_id) ? value.voice_id : firstVoice;
    onChange({ model, voice_id: newVoice });
  };

  const handleVoiceChange = (voice: string) => {
    if (voice === CUSTOM_VOICE) {
      onChange({ voice_id: customVoice || CUSTOM_VOICE });
    } else {
      onChange({ voice_id: voice });
    }
  };

  const handleCustomVoiceChange = (text: string) => {
    setCustomVoice(text);
    onChange({ voice_id: text });
  };

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
          <Select value={value.provider} onValueChange={handleProviderChange}>
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
        {isAliyun ? (
          <div className="space-y-2">
            <Label htmlFor="tts-model">{t('settings.model')}</Label>
            <Select value={value.model} onValueChange={handleModelChange}>
              <SelectTrigger id="tts-model">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ALIYUN_MODELS.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {t(m.labelKey)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ) : null}
        {!isAliyun ? (
          <div className="space-y-2">
            <Label htmlFor="tts-voice-id">{t('settings.voiceId')}</Label>
            <Input
              id="tts-voice-id"
              value={value.voice_id}
              onChange={(e) => onChange({ voice_id: e.target.value })}
              placeholder="BV001_streaming"
            />
          </div>
        ) : null}
      </div>
      {isAliyun ? (
        <div className="space-y-2">
          <Label htmlFor="tts-voice-id">{t('settings.voiceId')}</Label>
          <Select
            value={isCustomVoice ? CUSTOM_VOICE : value.voice_id}
            onValueChange={handleVoiceChange}
          >
            <SelectTrigger id="tts-voice-id">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {currentVoices.map((v) => (
                <SelectItem key={v.value} value={v.value}>
                  {t(v.labelKey)}
                </SelectItem>
              ))}
              <SelectItem value={CUSTOM_VOICE}>{t('settings.voiceCustom')}</SelectItem>
            </SelectContent>
          </Select>
          {isCustomVoice ? (
            <Input
              value={customVoice}
              onChange={(e) => handleCustomVoiceChange(e.target.value)}
              placeholder={t('settings.voiceCustomPlaceholder')}
            />
          ) : null}
        </div>
      ) : null}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="tts-api-key">{t('settings.apiKey')}</Label>
          <PasswordInput
            id="tts-api-key"
            value={value.api_key}
            onChange={(e) => onChange({ api_key: e.target.value })}
          />
        </div>
        {!isAliyun ? (
          <div className="space-y-2">
            <Label htmlFor="tts-secret-key">{t('settings.secretKey')}</Label>
            <PasswordInput
              id="tts-secret-key"
              value={value.secret_key}
              onChange={(e) => onChange({ secret_key: e.target.value })}
            />
          </div>
        ) : null}
      </div>
      {!isAliyun ? (
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
      ) : null}
      {isAliyun ? (
        <div className="space-y-2">
          <Label htmlFor="tts-base-url">{t('settings.baseUrl')}</Label>
          <Input
            id="tts-base-url"
            value={value.base_url || DEFAULT_ALIYUN_BASE_URL}
            disabled
            readOnly
          />
          <p className="text-xs text-muted-foreground">{t('settings.baseUrlReadonlyHint')}</p>
        </div>
      ) : null}
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
