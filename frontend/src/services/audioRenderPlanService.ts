import { readErrorDetail } from '@/services/http';
import type { PauseProfile, PauseProfileId, RenderPlanPreview } from '@/types';

export async function fetchPauseProfiles(): Promise<PauseProfile[]> {
  const response = await fetch('/api/audio-render-plans/pause-profiles');
  if (!response.ok) throw new Error(await readErrorDetail(response));
  const body = (await response.json()) as { items: PauseProfile[] };
  return body.items;
}

export async function previewAudioRenderPlan(
  scriptId: number,
  pauseProfileId: PauseProfileId,
  voicePrompt: string,
): Promise<RenderPlanPreview> {
  const response = await fetch('/api/audio-render-plans/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      script_id: scriptId,
      pause_profile_id: pauseProfileId,
      voice_prompt: voicePrompt,
    }),
  });
  if (!response.ok) throw new Error(await readErrorDetail(response));
  return (await response.json()) as RenderPlanPreview;
}
