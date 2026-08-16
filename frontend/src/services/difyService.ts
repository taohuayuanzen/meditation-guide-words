import { readErrorDetail } from '@/services/http';
import type { GeneratedScript, RenderPlanPreview, Script } from '@/types';

const PAUSE_KINDS = new Set([
  'short', 'paragraph', 'breath', 'observe', 'practice', 'transition', 'ending', 'none',
]);

function cleanJson(answer: string): string {
  let cleaned = answer.trim();

  while (/^<think>\s*/i.test(cleaned)) {
    const closingTag = cleaned.toLowerCase().indexOf('</think>');
    if (closingTag === -1) {
      throw new Error('模型思考内容未完整结束，请重新生成');
    }
    cleaned = cleaned.slice(closingTag + '</think>'.length).trimStart();
  }

  return cleaned.replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/, '').trim();
}

export function parseGeneratedScript(answer: string): GeneratedScript {
  const parsed: unknown = JSON.parse(cleanJson(answer));
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error('引导词必须是 JSON 对象');
  }
  const value = parsed as Partial<GeneratedScript>;
  if (
    typeof value.title !== 'string' || value.title.trim() === '' || value.version !== 1 ||
    !Number.isInteger(value.target_duration_seconds) || !Array.isArray(value.blocks) ||
    value.blocks.length === 0
  ) {
    throw new Error('引导词 JSON 缺少必要字段');
  }
  for (const block of value.blocks) {
    if (typeof block?.text !== 'string' || block.text.trim() === '' ||
        !block.pause_after || !PAUSE_KINDS.has(block.pause_after.kind)) {
      throw new Error('引导词 block 或语义停顿无效');
    }
  }
  return value as GeneratedScript;
}

export async function previewRenderPlan(
  scriptId: number,
  pauseProfileId: string,
  voicePrompt: string,
): Promise<RenderPlanPreview> {
  const res = await fetch('/api/audio-render-plans/preview', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ script_id: scriptId, pause_profile_id: pauseProfileId, voice_prompt: voicePrompt }),
  });
  if (!res.ok) throw new Error(await readErrorDetail(res));
  return (await res.json()) as RenderPlanPreview;
}

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
  const cleaned = cleanJson(answer);
  const parsed: unknown = JSON.parse(cleaned);
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
    throw new Error('TTS params must be a JSON object');
  }
  return parsed as Record<string, unknown>;
}
