import json
import os
import secrets
import threading
from pathlib import Path
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .workspace import Workspace
from .providers import Settings, endpoint, propose, ChatMessage, chat_messages, stream_chat
from .terminal import run_command

TOKEN = os.getenv('ROVNY_TOKEN') or secrets.token_urlsafe(32)
app = FastAPI(title='ROVNY Harness', version='0.2.0', docs_url=None, redoc_url=None, openapi_url=None)
workspaces = {}
state_dir = Path(os.getenv('ROVNY_STATE_DIR', str(Path(__file__).resolve().parents[1] / '.state')))
settings_file = state_dir / 'settings.json'
settings = Settings.model_validate_json(settings_file.read_text()) if settings_file.exists() else Settings()
terminal_lock = threading.Lock()


@app.middleware('http')
async def guard(request: Request, call_next):
    host = request.headers.get('host', '').split(':')[0]
    if host not in {'127.0.0.1', 'localhost', 'testserver'}:
        return JSONResponse({'detail': 'Invalid Host'}, status_code=403)
    origin = request.headers.get('origin')
    if origin and origin not in {'http://127.0.0.1:8765', 'http://localhost:8765', 'http://127.0.0.1:5173', 'http://localhost:5173'}:
        return JSONResponse({'detail': 'Invalid Origin'}, status_code=403)
    if request.headers.get('content-length', '0').isdigit() and int(request.headers.get('content-length', '0')) > 35 * 1024 * 1024:
        return JSONResponse({'detail': 'Request too large'}, status_code=413)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(ValueError)
async def bad_value(request, exc):
    return JSONResponse({'detail': str(exc)}, status_code=400)


@app.exception_handler(OSError)
async def os_error(request, exc):
    return JSONResponse({'detail': 'Filesystem or process error: ' + str(exc)}, status_code=400)


@app.exception_handler(KeyError)
async def missing(request, exc):
    return JSONResponse({'detail': 'Resource not found or invalid provider response'}, status_code=404)


def auth(authorization: str = Header(default='')):
    if not secrets.compare_digest(authorization, 'Bearer ' + TOKEN):
        raise HTTPException(401, 'Enter the session token printed by the backend')


def project(x_workspace: str = Header(default=''), _=Depends(auth)):
    if x_workspace not in workspaces:
        raise HTTPException(400, 'Open a project first')
    return workspaces[x_workspace]


class OpenProject(BaseModel):
    path: str


@app.post('/api/projects', dependencies=[Depends(auth)])
def open_project(body: OpenProject):
    ws = Workspace(body.path)
    key = str(ws.root)
    for wid, existing in workspaces.items():
        if str(existing.root) == key:
            return {'id': wid, 'path': key, 'name': ws.root.name}
    wid = secrets.token_hex(16)
    workspaces[wid] = ws
    return {'id': wid, 'path': key, 'name': ws.root.name}


@app.get('/api/tree')
def tree(ws=Depends(project)):
    return ws.files()


@app.get('/api/file')
def read_file(path: str, ws=Depends(project)):
    with ws.lock:
        return {'path': path, 'content': ws.read(path), 'hash': ws.hash(path)}


class Edit(BaseModel):
    path: str
    content: str | None
    hash: str | None


@app.post('/api/edit')
def edit(body: Edit, ws=Depends(project)):
    return ws.preview([body.model_dump()], 'Edit ' + body.path, {body.path: body.hash})


@app.get('/api/search')
def search(q: str, ws=Depends(project)):
    if not q or len(q) > 200:
        raise ValueError('Search must be 1–200 characters')
    results = []
    for item in ws.files():
        try:
            for number, line in enumerate(ws.read(item['path']).splitlines(), 1):
                if q.casefold() in line.casefold():
                    results.append({'path': item['path'], 'line': number, 'text': line[:300]})
                    if len(results) >= 200:
                        return results
        except (ValueError, OSError):
            continue
    return results


@app.get('/api/settings', dependencies=[Depends(auth)])
def get_settings():
    return settings


@app.put('/api/settings', dependencies=[Depends(auth)])
def set_settings(body: Settings):
    global settings
    endpoint(body)
    state_dir.mkdir(parents=True, exist_ok=True)
    temp = settings_file.with_suffix('.tmp')
    temp.write_text(body.model_dump_json(), encoding='utf-8')
    temp.replace(settings_file)
    settings = body
    return settings


class AgentRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=16000)
    files: list[str] = Field(default_factory=list, max_length=30)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    files: list[str] = Field(default_factory=list, max_length=30)


@app.post('/api/chat', dependencies=[Depends(auth)])
async def chat(body: ChatRequest, request: Request, x_workspace: str = Header(default='')):
    context = {}
    if body.files:
        if x_workspace not in workspaces:
            raise HTTPException(400, 'Dosya eklemek için bir proje açın.')
        ws = workspaces[x_workspace]
        with ws.lock:
            context = {name: ws.read(name) for name in body.files}
    config = settings.model_copy()
    messages, trimmed = chat_messages(body.messages, context, config.context_length)
    endpoint(config)
    async def events():
        yield json.dumps({'type': 'start', 'trimmed': trimmed, 'model': config.model}) + '\n'
        try:
            async for event in stream_chat(config, messages):
                if await request.is_disconnected():
                    return
                yield json.dumps(event, ensure_ascii=False) + '\n'
        except ValueError as exc:
            yield json.dumps({'type': 'error', 'text': str(exc)}, ensure_ascii=False) + '\n'
        except Exception:
            yield json.dumps({'type': 'error', 'text': 'Modele bağlanılamadı veya zaman aşımı oluştu. Sunucu ve model ayarlarını kontrol edin.'}, ensure_ascii=False) + '\n'
    return StreamingResponse(events(), media_type='application/x-ndjson', headers={'X-Accel-Buffering': 'no'})


@app.post('/api/agent')
async def agent(body: AgentRequest, ws=Depends(project)):
    with ws.lock:
        context = {name: ws.read(name) for name in body.files}
        if sum(len(s.encode()) for s in context.values()) > 120000:
            raise ValueError('Selected context exceeds 120 KB; select fewer files')
        hashes = {name: ws.hash(name) for name in body.files}
        known = {f['path'] for f in ws.files()}
    try:
        proposal = await propose(settings.model_copy(), body.prompt, context)
    except ValueError:
        raise
    except Exception:
        raise HTTPException(502, 'Provider unavailable or response invalid. Check that the server and model are running.')
    for change in proposal.changes:
        if change.path in known and change.path not in context:
            raise ValueError('Model tried to edit an unselected file: ' + change.path)
    plan = ws.preview([c.model_dump() for c in proposal.changes], proposal.summary, hashes)
    plan['metrics'] = proposal._metrics
    return plan


@app.post('/api/plans/{pid}/apply')
def apply(pid: str, ws=Depends(project)):
    return ws.apply(pid)


@app.post('/api/plans/{pid}/revert')
def revert(pid: str, ws=Depends(project)):
    return ws.revert(pid)


@app.get('/api/snapshots')
def snapshots(ws=Depends(project)):
    return ws.snapshots()


@app.post('/api/snapshots')
def snapshot(ws=Depends(project)):
    return {'id': ws.snapshot()}


@app.post('/api/snapshots/{sid}/restore')
def restore(sid: str, ws=Depends(project)):
    return {'backup': ws.restore(sid)}


class Command(BaseModel):
    argv: list[str] = Field(min_length=1, max_length=100)
    confirmed: bool = False


@app.post('/api/terminal')
def terminal(body: Command, ws=Depends(project)):
    if not body.confirmed:
        raise HTTPException(403, 'Explicit command confirmation required')
    if not terminal_lock.acquire(blocking=False):
        raise HTTPException(409, 'Another command is running')
    try:
        with ws.lock:
            return run_command(body.argv, ws.root)
    finally:
        terminal_lock.release()


dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
if dist.exists():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
