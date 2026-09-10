"""Run: python benchmark.py --label baseline --ctx 8192 --output results.jsonl"""
import argparse
import ast
import hashlib
import json
import time
from pathlib import Path
import httpx
from rovny.metrics import measure

CASES = [
    ('reasoning', 'Return only JSON with keys sums and unique. Compute prefix sums of [2,-1,4,0] and remove duplicates from [3,1,3,2,1] preserving order. No explanation.'),
    ('code', 'Return only JSON with key code, whose value is complete Python code for def greet(name: str = "ROVNY") -> str returning f"Hello, {name}!". No imports, no extra functions, no explanation.')]


def quality(case, text):
    try:
        obj = json.loads(text.strip().removeprefix('```json').removesuffix('```').strip())
        if case == 'reasoning':
            return obj.get('sums') == [2, 1, 5, 5] and obj.get('unique') == [3, 1, 2]
        tree = ast.parse(obj['code'])
        expected = ast.parse('def greet(name: str = "ROVNY") -> str:\n    return f"Hello, {name}!"')
        return ast.dump(tree, include_attributes=False) == ast.dump(expected, include_attributes=False)
    except (ValueError, TypeError, SyntaxError, KeyError):
        return False


def run(client, model, ctx, prompt, threads=None):
    start = time.perf_counter(); first = None; content = ''; packet = {}
    with client.stream('POST', '/api/chat', json={'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'think': False, 'stream': True,
                     'options': {'num_ctx': ctx, 'num_predict': 160, 'temperature': 0, 'seed': 42, **({'num_thread': threads} if threads else {})}, 'keep_alive': '20m'}) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line: continue
            packet = json.loads(line)
            if packet.get('error'): raise RuntimeError(packet['error'])
            delta = packet.get('message', {}).get('content', '')
            if delta and first is None: first = time.perf_counter() - start
            content += delta
            if packet.get('done'): break
    if not packet.get('done'): raise RuntimeError('Incomplete stream')
    return content, measure(packet, time.perf_counter() - start, first), packet.get('done_reason')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='qwen3:14b'); parser.add_argument('--ctx', type=int, default=4096)
    parser.add_argument('--label', required=True); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=1); parser.add_argument('--endpoint', default='http://127.0.0.1:11434')
    parser.add_argument('--threads', type=int)
    args = parser.parse_args(); args.output.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=args.endpoint, timeout=600, trust_env=False) as client:
        warm, stats, reason = run(client, args.model, args.ctx, 'Reply with the single word Ready.', args.threads)
        with args.output.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'label': args.label, 'phase': 'warmup', 'model': args.model, 'ctx': args.ctx, **stats}) + '\n')
        print(json.dumps({'label': args.label, 'phase': 'warmup', **stats}), flush=True)
        for repeat in range(args.repeats):
            for case, prompt in CASES:
                text, stats, reason = run(client, args.model, args.ctx, prompt, args.threads)
                row = {'label': args.label, 'phase': 'measured', 'repeat': repeat, 'case': case, 'model': args.model, 'ctx': args.ctx, 'threads': args.threads,
                       'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest(), 'quality_pass': quality(case, text), 'response': text,
                       'done_reason': reason, 'running_models': client.get('/api/ps').json(), **stats}
                with args.output.open('a', encoding='utf-8') as f: f.write(json.dumps(row, ensure_ascii=False) + '\n')
                print(json.dumps({k: v for k, v in row.items() if k not in ('response', 'running_models')}), flush=True)


if __name__ == '__main__': main()
