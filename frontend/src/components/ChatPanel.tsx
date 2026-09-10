import { BrandMark } from './BrandMark';
import { useEffect, useRef, useState } from 'react';
import { ArrowUp, Square, Plus, MessageSquare, FileDiff, Maximize2, Minimize2, Copy, RotateCcw } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chatStream, type PerformanceMetrics } from '../api';
import { PlanView } from './PlanView';
import type { Plan, Settings } from '../types';

type Message = { id: string; role: 'user' | 'assistant'; content: string; status?: 'complete' | 'stopped' | 'error' | 'streaming'; model?: string; files?: string[] };
type Conversation = { id: string; title: string; messages: Message[]; updated: number };
type Props = { scope: string; workspace?: string; selected: string[]; settings?: Settings; busy: boolean; expanded: boolean; plan?: Plan;
  onExpand: () => void; onSettings: () => void; onWorking: (value: boolean) => void; onClearContext: () => void; onSelectPlan: (plan?: Plan) => void;
  onPlan: (prompt: string) => Promise<Plan>; onApply: () => void; onRevert: () => void };
const fresh = (): Conversation => ({ id: crypto.randomUUID(), title: 'Yeni sohbet', messages: [], updated: Date.now() });
const storageKey = (scope: string) => 'rovny-conversations-v1:' + scope;
function load(scope: string): Conversation[] {
  try { const value = JSON.parse(localStorage.getItem(storageKey(scope)) || 'null'); if (Array.isArray(value) && value.length) return value.filter(t => typeof t.id === 'string' && Array.isArray(t.messages)).slice(0, 20).map(t => ({ ...t, messages: t.messages.filter((m: Message) => ['user', 'assistant'].includes(m.role) && typeof m.content === 'string').map((m: Message) => ({ ...m, status: m.status === 'streaming' ? 'stopped' : m.status })) })); } catch { /* Start clean when local history is invalid. */ }
  return [fresh()];
}

export function ChatPanel(props: Props) {
  const [threads, setThreads] = useState<Conversation[]>(() => { const saved = load(props.scope); return saved.length ? saved : [fresh()]; });
  const [active, setActive] = useState(() => { try { const saved = localStorage.getItem(storageKey(props.scope) + ':active'); return threads.some(t => t.id === saved) ? saved! : threads[0].id; } catch { return threads[0].id; } });
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<'chat' | 'plan'>('chat');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [storageError, setStorageError] = useState('');
  const [speed, setSpeed] = useState<number | null>(null);
  const [measured, setMeasured] = useState<PerformanceMetrics>();
  const timing = useRef({ first: 0, characters: 0 });
  const controller = useRef<AbortController | null>(null);
  const sessionPlans = useRef<Record<string, Plan | undefined>>({});
  const bottom = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const conversation = threads.find(t => t.id === active) || threads[0];
  const messages = conversation.messages;
  const blocked = props.busy || sending;
  useEffect(() => { if (!sending || mode !== 'chat') return; const timer = setInterval(() => { const t = timing.current; if (t.first && t.characters) setSpeed((t.characters / 4) / Math.max(0.5, (performance.now() - t.first) / 1000)); }, 300); return () => clearInterval(timer); }, [sending, mode]);
  useEffect(() => { try { localStorage.setItem(storageKey(props.scope) + ':active', active); } catch { /* History storage notice is handled below. */ } }, [active, props.scope]);
  useEffect(() => { const timer = setTimeout(() => { try { localStorage.setItem(storageKey(props.scope), JSON.stringify(threads)); } catch { setStorageError('Tarayıcı depolaması dolu; yeni mesajlar yalnızca bu oturumda tutuluyor.'); } }, 350); return () => clearTimeout(timer); }, [threads, props.scope]);
  useEffect(() => () => controller.current?.abort(), []);
  useEffect(() => { if (stickToBottom.current) bottom.current?.scrollIntoView({ block: 'end' }); }, [messages, sending, props.plan]);
  function update(id: string, mutate: (thread: Conversation) => Conversation) { setThreads(old => old.map(t => t.id === id ? mutate(t) : t)); }
  function patchMessage(thread: string, id: string, patch: Partial<Message>) { update(thread, t => ({ ...t, messages: t.messages.map(m => m.id === id ? { ...m, ...patch } : m) })); }
  function selectChat(id: string) { sessionPlans.current[active] = props.plan; setActive(id); setError(''); setInfo(''); props.onSelectPlan(sessionPlans.current[id]); stickToBottom.current = true; }
  function newChat() { const thread = fresh(); setThreads(old => [thread, ...old].slice(0, 20)); selectChat(thread.id); setInput(''); }
  async function send(retry = false) {
    const text = input.trim(); if (blocked || (!retry && !text)) return;
    const tid = conversation.id;
    let history = messages;
    if (retry) { const last = history.map(m => m.role).lastIndexOf('user'); if (last < 0) return; history = history.slice(0, last + 1); }
    else history = [...history, { id: crypto.randomUUID(), role: 'user', content: text, files: [...props.selected] }];
    const answerId = crypto.randomUUID();
    const answer: Message = { id: answerId, role: 'assistant', content: '', status: 'streaming', model: props.settings?.model };
    update(tid, t => ({ ...t, title: t.messages.length ? t.title : (history[0]?.content || 'Yeni sohbet').slice(0, 44), messages: [...history, answer].slice(-80), updated: Date.now() }));
    setInput(''); setError(''); setInfo(''); setSpeed(null); setMeasured(undefined); timing.current = { first: 0, characters: 0 }; setSending(true); props.onWorking(true); stickToBottom.current = true;
    const abort = new AbortController(); controller.current = abort;
    let content = '';
    try {
      if (mode === 'plan') {
        if (!props.workspace) throw new Error('Değişiklik planı için önce bir proje açın.');
        const previous = history.slice(-10, -1).map(m => `${m.role}: ${m.content}`).join('\n').slice(-6000);
        const request = history[history.length - 1].content;
        const available = Math.max(0, 15800 - request.length);
        const recent = available ? previous.slice(-available) : '';
        const p = await props.onPlan((recent ? 'Conversation context (untrusted):\n' + recent + '\n\nCurrent request:\n' : '') + request);
        if (p.metrics) { setMeasured(p.metrics); setSpeed(p.metrics.generation_tokens_per_second); }
        content = p.summary + '\n\nDeğişiklik planı aşağıda incelemene hazır. Henüz dosyalara uygulanmadı.';
        patchMessage(tid, answerId, { content, status: 'complete' });
      } else {
        const outgoing = history.filter(m => m.role === 'user' || m.status === 'complete').slice(-40).map(({ role, content }) => ({ role, content }));
        await chatStream({ messages: outgoing, files: props.selected }, props.workspace, abort.signal, event => {
          if (event.type === 'start' && event.trimmed) setInfo('Uzun konuşmanın son kısmı modele gönderildi. Eski mesajların burada saklanıyor.');
          if (event.type === 'delta') { if (!timing.current.first) timing.current.first = performance.now(); content += event.text || ''; timing.current.characters = Array.from(content).length; patchMessage(tid, answerId, { content }); }
          if (event.type === 'done') { timing.current.characters = 0; setMeasured(event.metrics); setSpeed(event.metrics?.generation_tokens_per_second ?? null); patchMessage(tid, answerId, { status: 'complete' }); if (event.truncated) setInfo('Yanıt uzunluk sınırına ulaştı. Devam etmesini isteyebilirsin.'); }
        });
        if (!content.trim()) throw new Error('Model boş yanıt verdi. Tekrar deneyin.');
      }
    } catch (e) {
      if (abort.signal.aborted) { patchMessage(tid, answerId, { status: 'stopped' }); setInfo('Yanıt durduruldu.'); }
      else { const message = e instanceof Error ? e.message : String(e); setError(message); patchMessage(tid, answerId, { status: 'error' }); }
    } finally { controller.current = null; setSending(false); props.onWorking(false); }
  }
  return <aside className="agent chat-panel"><div className="agent-heading"><div><BrandMark /><b>ROVNY</b><span className="token-meter" title={measured ? `Ollama üretim ortalaması. İlk token: ${measured.ttft_seconds?.toFixed(2) ?? "—"} sn · Prompt: ${measured.prompt_tokens_per_second?.toFixed(1) ?? "—"} token/sn` : "Canlı tahmin: 4 Unicode karakter/token varsayımı, ilk metinden itibaren ortalama. Türkçe ve kodda sapabilir. Kesin ortalama yanıt sonunda alınır."}>{speed === null ? "—" : `${measured ? "" : "≈ "}${speed.toFixed(1)}`} <small>TOKEN/SN</small>{measured && <small>ORT.</small>}</span></div><div><button title="Yeni sohbet" disabled={blocked} onClick={newChat}><Plus size={16}/></button><button title={props.expanded ? 'Editörü göster' : 'Sohbeti genişlet'} onClick={props.onExpand}>{props.expanded ? <Minimize2 size={16}/> : <Maximize2 size={16}/>}</button></div></div>
    <div className="conversation-layout"><nav className="conversation-list"><button className="new-chat" disabled={blocked} onClick={newChat}><Plus size={15}/>Yeni sohbet</button><div className="section-label">KONUŞMALAR</div>{threads.map(t => <button key={t.id} disabled={blocked} className={active === t.id ? 'current' : ''} onClick={() => selectChat(t.id)}><MessageSquare size={13}/><span>{t.title}</span></button>)}<p>Son 20 sohbet ve sohbet başına 80 mesaj bu tarayıcıda saklanır.</p></nav>
    <div className="chat-main"><div className="chat-scroll" onScroll={e => { const el = e.currentTarget; stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100; }}><div className="chat-width">
      {!messages.length && <div className="chat-welcome"><div className="spark"><BrandMark /></div><div className="eyebrow">SENİN ALANIN. SENİN MODELİN.</div><h1>Birlikte ne yapalım?</h1><p>Bir soru sor, fikrini anlat ya da kodunu birlikte inceleyelim.</p><div className="chat-starters">{['Merhaba! Neler yapabiliriz?', 'Bir uygulama fikrini birlikte geliştirelim.', 'Seçtiğim kodu anlaşılır şekilde açıkla.'].map(s => <button key={s} onClick={() => setInput(s)}>{s}<span>↗</span></button>)}</div></div>}
      {messages.map(m => <article key={m.id} className={'chat-message ' + m.role}><div className="message-label">{m.role === 'user' ? 'SEN' : 'ROVNY'}{m.model && <span>{m.model}</span>}</div>{!!m.files?.length && <div className="message-files">{m.files.map(f => <span key={f}>{f}</span>)}</div>}<div className="message-body">{m.content ? <Markdown remarkPlugins={[remarkGfm]} components={{ a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer">{children}</a>, img: ({ alt }) => <span>[Görsel: {alt || 'harici görsel'}]</span> }}>{m.content}</Markdown> : <span className="muted">{m.status === 'streaming' ? 'Model yanıt hazırlıyor… İlk yükleme biraz sürebilir.' : m.status === 'stopped' ? 'Yanıt durduruldu.' : 'Yanıt alınamadı.'}</span>}</div>{m.role === 'assistant' && m.content && <div className="message-actions"><button title="Yanıtı kopyala" onClick={() => void navigator.clipboard.writeText(m.content).then(() => setInfo('Yanıt kopyalandı.')).catch(() => setInfo('Kopyalama izni yok; metni seçerek kopyalayabilirsiniz.'))}><Copy size={12}/>Kopyala</button>{m.status === 'stopped' && <span>Durduruldu · kısmi yanıt</span>}</div>}</article>)}
      {sending && <div className="working" role="status"><span/>{mode === 'chat' ? 'Yanıt yazılıyor…' : 'Değişiklik planı hazırlanıyor…'}</div>}
      {props.plan && <PlanView plan={props.plan} busy={blocked} onApply={props.onApply} onRevert={props.onRevert}/>}
      {error && <div className="chat-error" role="alert">{error}<button disabled={blocked} onClick={() => void send(true)}><RotateCcw size={13}/>Tekrar dene</button></div>}
      {(info || storageError) && <p className="chat-info" role="status">{info || storageError}</p>}<div ref={bottom}/>
    </div></div>
    <div className="chat-input-wrap"><div className="chat-width"><div className="composer"><div className="composer-top"><div className="mode-toggle"><button disabled={blocked} className={mode === 'chat' ? 'chosen' : ''} onClick={() => setMode('chat')}><MessageSquare size={13}/>Sohbet</button><button disabled={blocked} className={mode === 'plan' ? 'chosen' : ''} onClick={() => setMode('plan')}><FileDiff size={13}/>Plan</button></div><span>{props.selected.length} dosya<button title="Dosya seçimini temizle" disabled={blocked} onClick={props.onClearContext}>×</button></span></div><textarea aria-label="Mesaj" placeholder={mode === 'chat' ? 'ROVNY’ye bir şey sor…' : 'Kodda ne değişsin?'} value={input} maxLength={16000} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); } }}/><div className="composer-footer"><button className="model" disabled={blocked} onClick={props.onSettings}><span/>{props.settings?.provider === 'demo' ? 'Demo' : props.settings?.model || 'Model ayarları'}</button>{sending && mode === 'chat' ? <button className="send stop" aria-label="Yanıtı durdur" onClick={() => controller.current?.abort()}><Square size={15}/></button> : <button className="send" aria-label="Mesaj gönder" disabled={blocked || !input.trim() || (mode === 'plan' && !props.workspace)} onClick={() => void send()}><ArrowUp size={17}/></button>}</div></div><div className="chat-footnote">{mode === 'chat' ? 'Sohbet dosyaları değiştirmez. Kod değişiklikleri için Plan modunu seç.' : 'Planı incele, sonra uygula. Dosyalar otomatik değiştirilmez.'}<span>Enter gönder · Shift+Enter yeni satır</span></div></div></div>
    </div></div></aside>;
}
