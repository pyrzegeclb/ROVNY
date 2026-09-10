import json
from pathlib import Path
import pytest
from rovny.workspace import Workspace


@pytest.fixture
def ws(tmp_path):
    (tmp_path / 'a.txt').write_bytes(b'old\r\n')
    return Workspace(str(tmp_path))


@pytest.mark.parametrize('name', ['../escape', '/etc/passwd', '.git/config', '.env', 'a/.env.local', 'secret.pem', 'C:/Windows/test', 'a\\b'])
def test_protected_paths(ws, name):
    with pytest.raises(ValueError):
        ws.path(name)


def test_multi_apply_revert_preserves_bytes(ws):
    plan = ws.preview([{'path': 'a.txt', 'content': 'new\n'}, {'path': 'nested/new.txt', 'content': 'hello'}])
    assert ws.read('a.txt') == 'old\r\n'
    assert '-old' in plan['changes'][0]['diff']
    ws.apply(plan['id'])
    assert ws.read('nested/new.txt') == 'hello'
    ws.revert(plan['id'])
    assert ws.path('a.txt').read_bytes() == b'old\r\n'
    assert not ws.path('nested/new.txt').exists()


def test_stale_preview_rejected(ws):
    plan = ws.preview([{'path': 'a.txt', 'content': 'new'}])
    ws.path('a.txt').write_text('external change')
    with pytest.raises(ValueError, match='changed'):
        ws.apply(plan['id'])
    assert ws.read('a.txt') == 'external change'


def test_stale_revert_rejected(ws):
    p = ws.preview([{'path': 'a.txt', 'content': 'new'}])
    ws.apply(p['id'])
    ws.path('a.txt').write_text('later')
    with pytest.raises(ValueError, match='changed'):
        ws.revert(p['id'])


def test_full_restore_and_recovery(ws):
    sid = ws.snapshot()
    ws.path('a.txt').unlink()
    ws.path('new.txt').write_text('new')
    backup = ws.restore(sid)
    assert ws.read('a.txt') == 'old\r\n'
    assert not ws.path('new.txt').exists()
    ws.restore(backup)
    assert not ws.path('a.txt').exists()
    assert ws.read('new.txt') == 'new'


def test_delete(ws):
    p = ws.preview([{'path': 'a.txt', 'content': None}])
    ws.apply(p['id'])
    assert not ws.path('a.txt').exists()
    ws.revert(p['id'])
    assert ws.path('a.txt').exists()


def test_diff_without_trailing_newline(ws):
    ws.path('a.txt').write_text('old')
    p = ws.preview([{'path': 'a.txt', 'content': 'new'}])
    diff = p['changes'][0]['diff']
    assert '-old\n\\ No newline at end of file\n+new\n' in diff


def test_symlink_rejected(ws, tmp_path):
    link = tmp_path / 'link.txt'
    try:
        link.symlink_to(tmp_path / 'a.txt')
    except OSError:
        pytest.skip('OS requires symlink privileges')
    with pytest.raises(ValueError):
        ws.read('link.txt')


def test_snapshot_tampering_cannot_escape(ws):
    sid = ws.snapshot()
    p = ws.storage() / (sid + '.json')
    r = json.loads(p.read_text())
    r['files']['../escape.txt'] = 'aGk='
    p.write_text(json.dumps(r))
    with pytest.raises(ValueError):
        ws.restore(sid)


def test_rollback_on_mid_batch_failure(ws, monkeypatch):
    original = ws.write_raw
    failed = False
    def failing(name, raw):
        nonlocal failed
        if name == 'b.txt' and not failed:
            failed = True
            raise OSError('simulated disk error')
        return original(name, raw)
    monkeypatch.setattr(ws, 'write_raw', failing)
    p = ws.preview([{'path': 'a.txt', 'content': 'new'}, {'path': 'b.txt', 'content': 'hello'}])
    with pytest.raises(OSError):
        ws.apply(p['id'])
    assert ws.read('a.txt') == 'old\r\n'
    assert not ws.path('b.txt').exists()
