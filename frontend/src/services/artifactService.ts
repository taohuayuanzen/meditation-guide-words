import { readErrorDetail } from '@/services/http';

export interface Artifact {
  id: string;
  type: 'audio' | 'script';
  name: string;
  created_at?: string | null;
  // audio specific
  script_title?: string | null;
  task_id?: number | null;
  // script specific
  title?: string | null;
  script_id?: number | null;
}

export type ArtifactType = 'all' | 'audio' | 'script';

export async function fetchArtifacts(type: ArtifactType = 'all'): Promise<Artifact[]> {
  const url = type === 'all' ? '/api/artifacts' : `/api/artifacts?type=${type}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch artifacts: HTTP ${res.status}`);
  return (await res.json()) as Artifact[];
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
