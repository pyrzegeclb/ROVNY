import base64
import difflib
import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

EXCLUDED = {'.git', '.rovny', 'node_modules', '.venv', '__pycache__', 'dist', 'build'}
LIMIT = 1024 * 1024


def unified_diff(before, after, name):
    lines = difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile='a/' + name, tofile='b/' + name)
    return ''.join(line if line.endswith('\n') else line + '\n\\ No newline at end of file\n' for line in lines)


class Workspace:
    def __init__(self, root: str):
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError('Project must be a directory')
        self.lock = threading.RLock()
        self.plans = {}

    def path(self, name: str) -> Path:
        if not name or '\\' in name or ':' in name:
            raise ValueError('Use a relative forward-slash file path')
        rel = PurePosixPath(name)
        if rel.is_absolute() or any(p in {'.', '..'} | EXCLUDED for p in rel.parts):
            raise ValueError('Protected or invalid path')
        if any(p.startswith('.env') or p.lower().endswith(('.pem', '.key')) for p in rel.parts):
            raise ValueError('Secret files are protected')
        target = self.root.joinpath(*rel.parts)
        cursor = self.root
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink() or (hasattr(cursor, 'is_junction') and cursor.is_junction()):
                raise ValueError('Symlinks and junctions are not supported')
        if not target.resolve().is_relative_to(self.root):
            raise ValueError('Path escapes project')
        if target.exists() and not target.is_file():
            raise ValueError('Expected a regular file')
        return target

    def files(self):
        result = []
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not (Path(directory)/d).is_symlink() and not (hasattr(Path(directory)/d, 'is_junction') and (Path(directory)/d).is_junction()))
            for name in sorted(files):
                rel = (Path(directory) / name).relative_to(self.root).as_posix()
                try:
                    p = self.path(rel)
                    result.append({'path': rel, 'size': p.stat().st_size})
                except (ValueError, OSError):
                    continue
                if len(result) > 10000:
                    raise ValueError('Project exceeds 10,000 eligible files; open a smaller folder')
        return result

    def read(self, name):
        p = self.path(name)
        if p.stat().st_size > LIMIT:
            raise ValueError('Text file limit is 1 MiB')
        raw = p.read_bytes()
        if b'\0' in raw:
            raise ValueError('Binary file cannot be edited')
        return raw.decode('utf-8')

    def hash(self, name):
        p = self.path(name)
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

    def storage(self):
        p = self.root / '.rovny'
        if p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
            raise ValueError('Unsafe snapshot directory')
        p.mkdir(exist_ok=True)
        return p

    def snapshot(self, names=None, label='Manual snapshot'):
        with self.lock:
            full = names is None
            names = names if names is not None else [f['path'] for f in self.files()]
            data = {}
            total = 0
            for name in names:
                p = self.path(name)
                if p.exists():
                    size = p.stat().st_size
                    total += size
                    if total > 50 * LIMIT:
                        raise ValueError('Snapshot exceeds 50 MiB limit')
                    data[name] = base64.b64encode(p.read_bytes()).decode()
                else:
                    data[name] = None
            record = {'id': uuid.uuid4().hex, 'label': label, 'created': datetime.now(timezone.utc).isoformat(), 'files': data, 'full': full}
            dest = self.storage() / (record['id'] + '.json')
            if dest.is_symlink():
                raise ValueError('Unsafe snapshot')
            dest.write_text(json.dumps(record), encoding='utf-8')
            return record['id']

    def snapshots(self):
        result = []
        for p in self.storage().glob('*.json'):
            if p.is_symlink():
                continue
            try:
                r = json.loads(p.read_text(encoding='utf-8'))
                result.append({k: r[k] for k in ('id', 'label', 'created')})
            except (ValueError, KeyError):
                continue
        return sorted(result, key=lambda r: r['created'], reverse=True)

    def restore(self, sid):
        with self.lock:
            if len(sid) != 32 or any(c not in '0123456789abcdef' for c in sid):
                raise ValueError('Invalid snapshot ID')
            source = self.storage() / (sid + '.json')
            if source.is_symlink():
                raise ValueError('Unsafe snapshot')
            r = json.loads(source.read_text(encoding='utf-8'))
            names = set(r['files'])
            if r.get('full'):
                names.update(f['path'] for f in self.files())
            values = {n: base64.b64decode(r['files'][n], validate=True) if r['files'].get(n) is not None else None for n in names}
            for n in values:
                self.path(n)
            backup = self.snapshot(sorted(names), 'Before restore')
            self.write_batch(values)
            return backup

    def write_batch(self, values):
        originals = {n: self.path(n).read_bytes() if self.path(n).exists() else None for n in values}
        try:
            for n, raw in values.items():
                self.write_raw(n, raw)
        except Exception:
            for n, raw in originals.items():
                self.write_raw(n, raw)
            raise

    def write_raw(self, name, raw):
        p = self.path(name)
        if raw is None:
            p.unlink(missing_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            temp = p.with_name('.' + p.name + '.' + uuid.uuid4().hex + '.tmp')
            try:
                temp.write_bytes(raw)
                if p.exists():
                    temp.chmod(p.stat().st_mode)
                os.replace(temp, p)
            finally:
                temp.unlink(missing_ok=True)

    def preview(self, changes, summary='Manual edit', expected=None):
        with self.lock:
            if not changes or len(changes) > 30:
                raise ValueError('A plan must contain 1–30 file changes')
            seen, output = set(), []
            for change in changes:
                name, content = change['path'], change.get('content')
                if name in seen:
                    raise ValueError('Duplicate file path')
                seen.add(name)
                p = self.path(name)
                before = self.read(name) if p.exists() else ''
                if content is not None and (not isinstance(content, str) or len(content.encode()) > LIMIT):
                    raise ValueError('Invalid or oversized content')
                digest = self.hash(name)
                if expected is not None and digest != expected.get(name):
                    raise ValueError('File changed while the plan was generated; regenerate it')
                output.append({'path': name, 'content': content, 'before_hash': digest, 'diff': unified_diff(before, content or '', name), 'action': 'delete' if content is None else ('create' if not p.exists() else 'modify')})
            plan = {'id': uuid.uuid4().hex, 'summary': summary, 'changes': output, 'status': 'pending'}
            self.plans[plan['id']] = plan
            return plan

    def apply(self, pid):
        with self.lock:
            plan = self.plans[pid]
            if plan['status'] != 'pending':
                raise ValueError('Plan already applied')
            for c in plan['changes']:
                if self.hash(c['path']) != c['before_hash']:
                    raise ValueError('File changed since preview: ' + c['path'])
            plan['snapshot'] = self.snapshot([c['path'] for c in plan['changes']], 'Before apply: ' + plan['summary'][:80])
            self.write_batch({c['path']: c['content'].encode('utf-8') if c['content'] is not None else None for c in plan['changes']})
            plan['after_hashes'] = {c['path']: self.hash(c['path']) for c in plan['changes']}
            plan['status'] = 'applied'
            return plan

    def revert(self, pid):
        with self.lock:
            plan = self.plans[pid]
            if plan['status'] != 'applied':
                raise ValueError('Only applied plans can be reverted')
            for name, digest in plan['after_hashes'].items():
                if self.hash(name) != digest:
                    raise ValueError('File changed after apply; use snapshots to review recovery')
            self.restore(plan['snapshot'])
            plan['status'] = 'reverted'
            return plan
