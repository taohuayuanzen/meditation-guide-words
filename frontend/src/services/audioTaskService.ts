import type { AudioCapabilities, AudioRenderPlan, AudioTask } from '@/types';
import { readErrorDetail } from '@/services/http';

export async function createAudioTask(
  scriptId: number,
  voicePrompt: string,
  ttsParams?: Record<string, unknown>,
  renderPlan?: AudioRenderPlan,
  renderPlanDigest?: string,
  previewDigest?: string,
): Promise<AudioTask> {
  const res = await fetch('/api/audio-tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      script_id: scriptId,
      voice_prompt: voicePrompt,
      tts_params: ttsParams,
      render_plan: renderPlan,
      render_plan_digest: renderPlanDigest,
      preview_digest: previewDigest,
    }),
  });
  if (!res.ok) throw new Error(await readErrorDetail(res));
  return (await res.json()) as AudioTask;
}

export async function fetchAudioCapabilities(): Promise<AudioCapabilities> {
  const res = await fetch('/api/audio-tasks/capabilities');
  if (!res.ok) throw new Error(await readErrorDetail(res));
  return (await res.json()) as AudioCapabilities;
}

export async function fetchAudioTasks(): Promise<AudioTask[]> {
  const res = await fetch('/api/audio-tasks');
  if (!res.ok) throw new Error(`Failed to fetch audio tasks: HTTP ${res.status}`);
  return (await res.json()) as AudioTask[];
}

export async function retryAudioTask(id: number): Promise<AudioTask> {
  const res = await fetch(`/api/audio-tasks/${id}/retry`, { method: 'POST' });
  if (!res.ok) throw new Error(await readErrorDetail(res));
  return (await res.json()) as AudioTask;
}

export function getAudioDownloadUrl(id: number): string {
  return `/api/audio-tasks/${id}/download`;
}
