import { readErrorDetail } from '@/services/http';

export interface Artifact {
  id: string;
  type: 'audio' | 'music' | 'script';
  name: string;
  created_at?: string | null;
  // audio specific
  script_title?: string | null;
  task_id?: number | null;
  // script specific
  title?: string | null;
  script_id?: number | null;
  // music specific
  preset_params?: Record<string, unknown> | null;
  target_duration_seconds?: number | null;
  source_duration_seconds?: number | null;
  provider?: 'minimax' | 'aliyun' | null;
  model?: string | null;
  source_format?: 'wav' | 'mp3' | null;
  is_ai_generated?: boolean;
}

export type ArtifactType = 'all' | 'audio' | 'music' | 'script';

export interface ArtifactListResponse {
  items: Artifact[];
  total: number;
}

export async function fetchArtifacts(
  type: ArtifactType = 'all',
  page = 1,
  pageSize = 20,
): Promise<ArtifactListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (type !== 'all') params.set('type', type);
  const url = `/api/artifacts?${params.toString()}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch artifacts: HTTP ${res.status}`);
  return (await res.json()) as ArtifactListResponse;
}

export function getArtifactDownloadUrl(id: string): string {
  return `/api/artifacts/${encodeURIComponent(id)}/download`;
}

export async function renameArtifact(id: string, newName: string): Promise<{ name: string }> {
  const res = await fetch(`/api/artifacts/${encodeURIComponent(id)}/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_name: newName }),
  });
  if (!res.ok) {
    const detail = await readErrorDetail(res);
    throw new Error(detail || `Rename failed: HTTP ${res.status}`);
  }
  return (await res.json()) as { name: string };
}

export async function deleteArtifact(id: string): Promise<void> {
  const res = await fetch(`/api/artifacts/${encodeURIComponent(id)}`, { method: 'DELETE' });
  if (!res.ok) {
    const detail = await readErrorDetail(res);
    throw new Error(detail || `Delete failed: HTTP ${res.status}`);
  }
}
