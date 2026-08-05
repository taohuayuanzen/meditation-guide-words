import { readErrorDetail } from '@/services/http';
import type { Script } from '@/types';

export async function parseVoicePrompt(
  script: Script,
  query: string,
): Promise<Record<string, unknown>> {
  const res = await fetch('/api/dify/audio/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      inputs: { script_content: script.content },
      query,
      response_mode: 'blocking',
      conversation_id: '',
      user: 'local-user',
    }),
  });
  if (!res.ok) throw new Error(await readErrorDetail(res));
  const data = (await res.json()) as { answer?: string };
  return parseTtsParams(data.answer ?? '');
}

export function parseTtsParams(answer: string): Record<string, unknown> {
  const cleaned = answer
    .trim()
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/```\s*$/, '');
  const parsed: unknown = JSON.parse(cleaned);
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error('TTS params must be a JSON object');
  }
  return parsed as Record<string, unknown>;
}
