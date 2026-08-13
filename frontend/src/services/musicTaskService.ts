import { readErrorDetail } from '@/services/http';
import type { MusicCapabilities, MusicDownloadItem, MusicTask } from '@/types';

export interface CreateMusicTaskPayload {
  prompt: string;
  effective_prompt: string;
  preset_params: Record<string, unknown>;
  target_duration_seconds: number;
}

export async function fetchMusicCapabilities(): Promise<MusicCapabilities> {
  const response = await fetch('/api/music-tasks/capabilities');
  if (!response.ok) throw new Error(await readErrorDetail(response));
  return (await response.json()) as MusicCapabilities;
}

export async function fetchMusicTasks(): Promise<MusicTask[]> {
  const response = await fetch('/api/music-tasks');
  if (!response.ok) throw new Error(await readErrorDetail(response));
  return (await response.json()) as MusicTask[];
}

export async function createMusicTask(payload: CreateMusicTaskPayload): Promise<MusicTask> {
  const response = await fetch('/api/music-tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(await readErrorDetail(response));
  return (await response.json()) as MusicTask;
}

export async function retryMusicTask(id: number, confirmRegenerate = false): Promise<MusicTask> {
  const response = await fetch(`/api/music-tasks/${id}/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirm_regenerate: confirmRegenerate }),
  });
  if (!response.ok) throw new Error(await readErrorDetail(response));
  return (await response.json()) as MusicTask;
}

export async function deleteMusicTask(id: number): Promise<void> {
  const response = await fetch(`/api/music-tasks/${id}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(await readErrorDetail(response));
}

export async function fetchMusicDownloads(id: number): Promise<MusicDownloadItem[]> {
  const response = await fetch(`/api/music-tasks/${id}/downloads`);
  if (!response.ok) throw new Error(await readErrorDetail(response));
  const data = (await response.json()) as { items: MusicDownloadItem[] };
  return data.items;
}

export function getMusicDownloadUrl(id: number, kind: 'source' | 'final'): string {
  return `/api/music-tasks/${id}/download/${kind}`;
}
