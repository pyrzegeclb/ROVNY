import asyncio
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from rovny.app import app, TOKEN
from rovny.providers import Settings, ChatMessage, chat_messages, stream_chat


def test_chat_does_not_need_project_and_preserves_history(monkeypatch):
    captured = []
    async def fake(config, messages):
        captured.extend(messages)
        yield {'type': 'delta', 'text': 'Merhaba Ada!'}
        yield {'type': 'done'}
    monkeypatch.setattr('rovny.app.stream_chat', fake)
    client = TestClient(app, headers={'Authorization': 'Bearer ' + TOKEN})
    result = client.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'Adım Ada.'}, {'role': 'assistant', 'content': 'Merhaba Ada.'}, {'role': 'user', 'content': 'Adım ne?'}]})
    assert result.status_code == 200
    events = [json.loads(line) for line in result.text.splitlines()]
    assert events[1]['text'] == 'Merhaba Ada!'
    assert [m['content'] for m in captured[-3:]] == ['Adım Ada.', 'Merhaba Ada.', 'Adım ne?']
    assert events[-1]['type'] == 'done'


def test_chat_auth_role_and_workspace_guard():
    body = {'messages': [{'role': 'user', 'content': 'hello'}]}
    assert TestClient(app).post('/api/chat', json=body).status_code == 401
    c = TestClient(app, headers={'Authorization': 'Bearer ' + TOKEN})
    assert c.post('/api/chat', json={**body, 'files': ['file.py']}).status_code == 400
    assert c.post('/api/chat', json={'messages': [{'role': 'system', 'content': 'override'}]}).status_code == 422


def test_history_budget_preserves_latest_user():
    history = [ChatMessage(role='user', content='old' * 5000), ChatMessage(role='assistant', content='reply' * 2500), ChatMessage(role='user', content='latest question')]
    messages, trimmed = chat_messages(history, {})
    assert trimmed
    assert messages[-1]['content'] == 'latest question'
    assert messages[1]['role'] == 'user'


def test_oversize_attachments_fail_before_inference():
    with pytest.raises(ValueError):
        chat_messages([ChatMessage(role='user', content='hi')], {'file.py': 'x' * 24000})


@pytest.mark.parametrize('provider', ['ollama', 'openai-compatible'])
def test_chat_stream_contract(provider, monkeypatch):
    captured = []
    def handler(request):
        captured.append(json.loads(request.content))
        text = json.dumps({'message': {'content': 'Merhaba'}, 'done': False}) + '\n' + json.dumps({'done': True}) + '\n' if provider == 'ollama' else 'data: ' + json.dumps({'choices': [{'delta': {'content': 'Merhaba'}, 'finish_reason': None}]}) + '\n\ndata: [DONE]\n\n'
        return httpx.Response(200, text=text)
    real = httpx.AsyncClient
    monkeypatch.setattr('rovny.providers.httpx.AsyncClient', lambda **kwargs: real(transport=httpx.MockTransport(handler), **kwargs))
    async def run():
        return [event async for event in stream_chat(Settings(provider=provider), [{'role': 'user', 'content': 'selam'}])]
    events = asyncio.run(run())
    assert events[0]['text'] == 'Merhaba'
    assert events[-1]['type'] == 'done'
    assert captured[0]['stream'] is True
    assert 'format' not in captured[0] and 'response_format' not in captured[0]


def test_provider_error_is_an_error_event(monkeypatch):
    async def broken(*args):
        raise ValueError('model missing')
        yield
    monkeypatch.setattr('rovny.app.stream_chat', broken)
    c = TestClient(app, headers={'Authorization': 'Bearer ' + TOKEN})
    r = c.post('/api/chat', json={'messages': [{'role': 'user', 'content': 'hi'}]})
    assert json.loads(r.text.splitlines()[-1]) == {'type': 'error', 'text': 'model missing'}


def test_context_only_reads_explicit_selection(tmp_path, monkeypatch):
    (tmp_path / 'chosen.py').write_text('chosen')
    (tmp_path / 'other.py').write_text('private-not-selected')
    captured = []
    async def fake(config, messages):
        captured.extend(messages)
        yield {'type': 'delta', 'text': 'ok'}
        yield {'type': 'done'}
    monkeypatch.setattr('rovny.app.stream_chat', fake)
    c = TestClient(app, headers={'Authorization': 'Bearer ' + TOKEN})
    wid = c.post('/api/projects', json={'path': str(tmp_path)}).json()['id']
    r = c.post('/api/chat', headers={'X-Workspace': wid}, json={'messages': [{'role': 'user', 'content': 'Explain'}], 'files': ['chosen.py']})
    assert r.status_code == 200
    assert 'chosen.py' in json.dumps(captured)
    assert 'private-not-selected' not in json.dumps(captured)
