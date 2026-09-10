import { useState } from 'react';
import { Play } from 'lucide-react';
import { api } from '../api';
export function Terminal({ workspace, onChanged }: { workspace: string; onChanged: () => void }) {
  const [command, setCommand] = useState('["git", "status", "--short"]');
  const [output, setOutput] = useState('Ready. Commands run in the open project.');
  const [busy, setBusy] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  async function run() { setBusy(true); try { const argv: unknown = JSON.parse(command); if (!Array.isArray(argv) || !argv.every(a => typeof a === 'string')) throw new Error('Enter a JSON array of command arguments.'); const r = await api<{ output: string; exit_code: number; notice?: string }>('/terminal', 'POST', { argv, confirmed }, workspace); setOutput(r.output + '\n' + (r.notice || '') + '\nExit code: ' + r.exit_code); onChanged(); } catch (e) { setOutput(String(e)); } finally { setBusy(false); setConfirmed(false); } }
  return <section className="terminal"><div className="section-label">TERMINAL <span className="muted">30s limit · 1 MiB output</span></div><p className="muted">Commands have your system permissions and can change files outside this project. Review every command.</p><div className="command"><input aria-label="Command argument array" value={command} onChange={e => { setCommand(e.target.value); setConfirmed(false); }}/><button disabled={busy || !confirmed} onClick={run}><Play size={13}/>{busy ? 'Running…' : 'Run'}</button></div><label className="check-label"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)}/>I approve this exact command</label><pre>{output}</pre></section>;
}
