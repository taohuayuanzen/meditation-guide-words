import { readErrorDetail } from '@/services/http';
import type { LLMConfig, Settings, TTSConfig } from '@/types';

export async function fetchSettings(): Promise<Settings> {
  const res = await fetch('/api/settings');
  if (!res.ok) throw new Error(await readErrorDetail(res));
  return (await res.json()) as Settings;
}

export async function saveSettings(settings: Settings): Promise<Settings> {
  const res = await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error(await readErrorDetail(res));
  return (await res.json()) as Settings;
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
