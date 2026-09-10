const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has('token')) { sessionStorage.setItem('rovny-token', fragment.get('token')!); history.replaceState(null, '', location.pathname); }
export async function api<T>(path: string, method = 'GET', body?: unknown, workspace?: string): Promise<T> {
  const response = await fetch('/api' + path, { method, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (sessionStorage.getItem('rovny-token') || ''), ...(workspace ? { 'X-Workspace': workspace } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) });
  const text = await response.text();
  let data; try { data = JSON.parse(text); } catch { throw new Error('Backend unavailable. Start the Python server and use its session URL.'); }
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data as T;
}

export type PerformanceMetrics = { generation_tokens_per_second: number | null; ttft_seconds: number | null; prompt_tokens_per_second: number | null; generated_tokens?: number; wall_seconds?: number };
export type ChatEvent = { type: 'start' | 'delta' | 'done' | 'error'; text?: string; trimmed?: boolean; truncated?: boolean; model?: string; metrics?: PerformanceMetrics };
export async function chatStream(body: unknown, workspace: string | undefined, signal: AbortSignal, onEvent: (event: ChatEvent) => void) {
  const response = await fetch('/api/chat', { method: 'POST', signal, headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (sessionStorage.getItem('rovny-token') || ''), ...(workspace ? { 'X-Workspace': workspace } : {}) }, body: JSON.stringify(body) });
  if (!response.ok) { const error = await response.json(); throw new Error(typeof error.detail === 'string' ? error.detail : 'Sohbet isteği geçersiz.'); }
  if (!response.body) throw new Error('Tarayıcı akışlı yanıtı desteklemiyor.');
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = ''; let completed = false;
  const parse = (line: string) => { if (!line.trim()) return; const event = JSON.parse(line) as ChatEvent; if (event.type === 'error') throw new Error(event.text); if (event.type === 'done') completed = true; onEvent(event); };
  try { while (true) { const { done, value } = await reader.read(); buffer += decoder.decode(value, { stream: !done }); const lines = buffer.split('\n'); buffer = lines.pop()!; lines.forEach(parse); if (done) break; } if (buffer.trim()) parse(buffer); if (!completed) throw new Error('Bağlantı yanıt tamamlanmadan kesildi.'); }
  finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
