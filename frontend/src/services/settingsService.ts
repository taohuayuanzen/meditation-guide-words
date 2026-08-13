import { readErrorDetail } from '@/services/http';
import { fetchMusicCapabilities } from '@/services/musicTaskService';
import type {
  AliyunMusicConfig,
  LLMConfig,
  MiniMaxMusicConfig,
  MusicConfig,
  Settings,
  TTSConfig,
} from '@/types';

const DEFAULT_ALIYUN_MUSIC_CONFIG: AliyunMusicConfig = {
  api_key: '',
  workspace_id: '',
  base_url: '',
  model: 'fun-music-v1',
  source_format: 'wav',
};

const DEFAULT_MINIMAX_MUSIC_CONFIG: MiniMaxMusicConfig = {
  api_key: '',
  base_url: 'https://api.minimaxi.com/v1',
  model: 'music-3.0',
  source_format: 'mp3',
};

function asRecord(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

export function normalizeMusicConfig(value: unknown): MusicConfig {
  const raw = asRecord(value);
  const hasNestedConfig = raw.aliyun !== undefined || raw.minimax !== undefined;
  const rawAliyun = asRecord(hasNestedConfig ? raw.aliyun : raw);
  const rawMiniMax = asRecord(raw.minimax);
  const provider = hasNestedConfig && raw.provider === 'aliyun' ? 'aliyun' : 'minimax';

  return {
    provider,
    output_format: 'mp3',
    enable_aigc_watermark: false,
    worker_concurrency:
      typeof raw.worker_concurrency === 'number' &&
      raw.worker_concurrency >= 1 &&
      raw.worker_concurrency <= 8
        ? raw.worker_concurrency
        : 1,
    aliyun: {
      ...DEFAULT_ALIYUN_MUSIC_CONFIG,
      api_key: stringValue(rawAliyun.api_key),
      workspace_id: stringValue(rawAliyun.workspace_id),
      base_url: stringValue(rawAliyun.base_url),
    },
    minimax: {
      ...DEFAULT_MINIMAX_MUSIC_CONFIG,
      api_key: stringValue(rawMiniMax.api_key),
      base_url: stringValue(rawMiniMax.base_url, DEFAULT_MINIMAX_MUSIC_CONFIG.base_url),
    },
  };
}

function normalizeSettings(value: unknown): Settings {
  const raw = asRecord(value) as unknown as Settings;
  return { ...raw, music_config: normalizeMusicConfig(raw.music_config) };
}

export async function fetchSettings(): Promise<Settings> {
  const res = await fetch('/api/settings');
  if (!res.ok) throw new Error(await readErrorDetail(res));
  return normalizeSettings(await res.json());
}

export async function saveSettings(settings: Settings): Promise<Settings> {
  const res = await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error(await readErrorDetail(res));
  return normalizeSettings(await res.json());
}

export async function testLLM(config: LLMConfig): Promise<void> {
  const res = await fetch('/api/settings/test-llm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(await readErrorDetail(res));
}

export async function testTTS(config: TTSConfig): Promise<void> {
  const res = await fetch('/api/settings/test-tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(await readErrorDetail(res));
}

export async function testMusicConfig(config: MusicConfig): Promise<void> {
  const normalizedConfig = normalizeMusicConfig(config);
  const provider = normalizedConfig[normalizedConfig.provider];
  if (!provider.api_key) {
    throw new Error('Music API Key is required');
  }
  if (normalizedConfig.provider === 'aliyun' && !normalizedConfig.aliyun.workspace_id) {
    throw new Error('Workspace ID is required for Aliyun');
  }
  if (provider.base_url) {
    let url: URL;
    try {
      url = new URL(provider.base_url);
    } catch {
      throw new Error('Music Base URL must be a valid HTTP(S) URL');
    }
    if (
      !['http:', 'https:'].includes(url.protocol) ||
      url.username ||
      url.password ||
      url.search ||
      url.hash
    ) {
      throw new Error('Music Base URL cannot contain credentials, a query, or a fragment');
    }
  }
  const capabilities = await fetchMusicCapabilities();
  if (!capabilities.music_processing_available) {
    throw new Error('FFmpeg or FFprobe is unavailable');
  }
}
