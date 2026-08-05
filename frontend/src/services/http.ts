export async function readErrorDetail(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: string };
    return data.detail || `HTTP ${res.status}`;
  } catch {
    return `HTTP ${res.status}`;
  }
}
