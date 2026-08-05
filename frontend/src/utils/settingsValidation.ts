import type { DifyConfig, GeneralConfig, LLMConfig, Settings, TTSConfig } from '@/types';

export interface SettingsErrors {
  llm_config?: Partial<Record<keyof LLMConfig, string>>;
  tts_config?: Partial<Record<keyof TTSConfig, string>>;
  dify_config?: Partial<Record<keyof DifyConfig, string>>;
  general_config?: Partial<Record<keyof GeneralConfig, string>>;
}

function isValidUrl(url: string) {
  return /^https?:\/\//i.test(url);
}

export function validateSettings(settings: Settings): SettingsErrors {
  const errors: SettingsErrors = {};

  const llm = settings.llm_config;
  const llmErrors: Partial<Record<keyof LLMConfig, string>> = {};
  if (!isValidUrl(llm.base_url)) llmErrors.base_url = 'invalidUrl';
  if (llm.temperature < 0 || llm.temperature > 2) llmErrors.temperature = 'invalidRange';
  if (llm.max_tokens !== null && llm.max_tokens !== undefined && llm.max_tokens < 1) {
    llmErrors.max_tokens = 'invalidPositive';
  }
  if (Object.keys(llmErrors).length > 0) errors.llm_config = llmErrors;

  const tts = settings.tts_config;
  const ttsErrors: Partial<Record<keyof TTSConfig, string>> = {};
  if (tts.speed < 0.5 || tts.speed > 2) ttsErrors.speed = 'invalidRange';
  if (tts.volume < 0 || tts.volume > 2) ttsErrors.volume = 'invalidRange';
  if (tts.provider === 'volcano') {
    if (!tts.appid) ttsErrors.appid = 'required';
    if (!tts.cluster) ttsErrors.cluster = 'required';
  }
  if (Object.keys(ttsErrors).length > 0) errors.tts_config = ttsErrors;

  const dify = settings.dify_config;
  const difyErrors: Partial<Record<keyof DifyConfig, string>> = {};
  if (!isValidUrl(dify.base_url)) difyErrors.base_url = 'invalidUrl';
  if (Object.keys(difyErrors).length > 0) errors.dify_config = difyErrors;

  const general = settings.general_config;
  const generalErrors: Partial<Record<keyof GeneralConfig, string>> = {};
  if (!general.audio_output_dir) generalErrors.audio_output_dir = 'required';
  if (Object.keys(generalErrors).length > 0) errors.general_config = generalErrors;

  return errors;
}

export function hasErrors(errors: SettingsErrors): boolean {
  return Object.values(errors).some((block) => Object.keys(block ?? {}).length > 0);
}
