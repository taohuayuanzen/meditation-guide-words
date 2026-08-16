import type { Script, ScriptListResponse, ScriptPlan } from '@/types';

export interface CreateScriptPayload {
  title: string;
  content?: string;
  script_plan?: ScriptPlan;
  session_id?: string | null;
}

export async function fetchScripts(): Promise<Script[]> {
  const res = await fetch('/api/scripts');
  if (!res.ok) throw new Error(`Failed to fetch scripts: HTTP ${res.status}`);
  const data = (await res.json()) as ScriptListResponse;
  return data.items;
}

export async function fetchScript(id: number): Promise<Script> {
  const res = await fetch(`/api/scripts/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch script: HTTP ${res.status}`);
  return (await res.json()) as Script;
}

export async function createScript(payload: CreateScriptPayload): Promise<Script> {
  const res = await fetch('/api/scripts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Failed to save script: HTTP ${res.status}`);
  return (await res.json()) as Script;
}
