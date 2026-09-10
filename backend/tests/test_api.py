import sys
import pytest
from fastapi.testclient import TestClient
from rovny.app import app, TOKEN
from rovny.providers import Settings, endpoint


@pytest.fixture
def client(tmp_path):
    c = TestClient(app, headers={'Authorization': 'Bearer ' + TOKEN})
    p = c.post('/api/projects', json={'path': str(tmp_path)}).json()
    c.headers['X-Workspace'] = p['id']
    return c


def test_auth_and_origin(client):
    assert TestClient(app).get('/api/settings').status_code == 401
    assert client.get('/api/settings', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert client.get('/api/settings', headers={'Host': 'evil.example'}).status_code == 403


def test_edit_apply_search_restore(client):
    p = client.post('/api/edit', json={'path': 'test.txt', 'content': 'hello world', 'hash': None}).json()
    assert client.post('/api/plans/' + p['id'] + '/apply').status_code == 200
    assert client.get('/api/search?q=world').json()[0]['line'] == 1
    assert client.get('/api/file?path=test.txt').json()['content'] == 'hello world'
    assert client.post('/api/plans/' + p['id'] + '/revert').status_code == 200
    assert client.get('/api/tree').json() == []


def test_terminal_confirmation(client):
    body = {'argv': [sys.executable, '-c', 'print("rovny-ok")']}
    assert client.post('/api/terminal', json=body).status_code == 403
    r = client.post('/api/terminal', json={**body, 'confirmed': True}).json()
    assert r['exit_code'] == 0
    assert 'rovny-ok' in r['output']


def test_demo_agent(client, monkeypatch):
    monkeypatch.setattr('rovny.app.settings', Settings(provider='demo'))
    r = client.post('/api/agent', json={'prompt': 'demo', 'files': []})
    assert r.status_code == 200
    p = r.json()
    assert p['status'] == 'pending'
    assert client.get('/api/tree').json() == []
    assert client.post('/api/plans/' + p['id'] + '/apply').status_code == 200


def test_remote_requires_opt_in():
    with pytest.raises(ValueError):
        endpoint(Settings(endpoint='https://example.com/v1'))
    with pytest.raises(ValueError):
        endpoint(Settings(endpoint='http://example.com/v1', allow_remote=True))
    assert endpoint(Settings(endpoint='https://example.com/v1', allow_remote=True)) == 'https://example.com/v1'


def test_agent_cannot_overwrite_unselected_file(client, monkeypatch):
    from rovny.providers import Proposal, Change
    p = client.post('/api/edit', json={'path': 'private.txt', 'content': 'keep', 'hash': None}).json()
    client.post('/api/plans/' + p['id'] + '/apply')
    async def malicious(*args):
        return Proposal(summary='Overwrite', changes=[Change(path='private.txt', content='lost')])
    monkeypatch.setattr('rovny.app.propose', malicious)
    r = client.post('/api/agent', json={'prompt': 'test', 'files': []})
    assert r.status_code == 400
    assert client.get('/api/file?path=private.txt').json()['content'] == 'keep'


def test_agent_stale_context_rejected(client, monkeypatch):
    from rovny.providers import Proposal, Change
    from rovny.app import workspaces
    ws = workspaces[client.headers['X-Workspace']]
    ws.path('a.txt').write_text('before')
    async def delayed(*args):
        ws.path('a.txt').write_text('external edit')
        return Proposal(summary='Update', changes=[Change(path='a.txt', content='model edit')])
    monkeypatch.setattr('rovny.app.propose', delayed)
    assert client.post('/api/agent', json={'prompt': 'test', 'files': ['a.txt']}).status_code == 400
    assert ws.read('a.txt') == 'external edit'
