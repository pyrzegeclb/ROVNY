import asyncio
import json
import httpx
import pytest
from rovny.providers import Settings, propose


@pytest.mark.parametrize('provider', ['ollama', 'openai-compatible'])
def test_provider_wire_contract(provider, monkeypatch):
    proposal = {'summary': 'Change greeting', 'changes': [{'path': 'hello.py', 'content': 'print("hello")\n'}]}
    requests = []
    def handler(request):
        requests.append(request)
        content = json.dumps(proposal)
        return httpx.Response(200, json={'message': {'content': content}, 'done': True} if provider == 'ollama' else {'choices': [{'message': {'content': content}}]})
    real_client = httpx.AsyncClient
    monkeypatch.setattr('rovny.providers.httpx.AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    monkeypatch.delenv('ROVNY_API_KEY', raising=False)
    settings = Settings(provider=provider, endpoint='http://127.0.0.1:1234' + ('/v1' if provider == 'openai-compatible' else ''))
    result = asyncio.run(propose(settings, 'Improve greeting', {'hello.py': 'print("hi")'}))
    assert result.summary == 'Change greeting'
    assert len(requests) == 1
    req = requests[0]
    assert req.url.path == ('/api/chat' if provider == 'ollama' else '/v1/chat/completions')
    assert 'authorization' not in req.headers
    payload = json.loads(req.content)
    assert payload['stream'] is (provider == 'ollama')
    if provider == 'ollama':
        assert payload['options']['num_ctx'] == 4096
        assert payload['think'] is False
    assert 'hello.py' in payload['messages'][1]['content']


def test_provider_rejects_invalid_schema(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={'message': {'content': '{"summary":"bad","changes":[]}'}})
    real_client = httpx.AsyncClient
    monkeypatch.setattr('rovny.providers.httpx.AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    with pytest.raises(ValueError):
        asyncio.run(propose(Settings(), 'test', {}))
