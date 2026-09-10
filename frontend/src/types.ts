export type Project = { id: string; name: string; path: string };
export type FileItem = { path: string; size: number };
export type OpenFile = { path: string; content: string; hash: string | null };
export type Settings = { provider: 'ollama' | 'openai-compatible' | 'demo'; endpoint: string; model: string; allow_remote: boolean; context_length?: number };
export type Plan = { metrics?: import('./api').PerformanceMetrics; id: string; summary: string; status: string; changes: { path: string; content: string | null; action: string; diff: string }[] };
export type Snapshot = { id: string; label: string; created: string };
export type SearchResult = { path: string; line: number; text: string };
