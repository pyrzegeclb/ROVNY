"""Content-free performance records; Ollama durations are nanoseconds."""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

_lock = threading.Lock()


def measure(packet, wall_seconds, first_token_seconds=None):
    def seconds(key):
        value = packet.get(key)
        return value / 1e9 if isinstance(value, (int, float)) and value >= 0 else None
    def rate(count, duration):
        n, t = packet.get(count), seconds(duration)
        return round(n / t, 3) if isinstance(n, (int, float)) and t and t > 0 else None
    cached = packet.get('prompt_eval_cached_count')
    total = packet.get('prompt_eval_count')
    elapsed = seconds('prompt_eval_duration')
    uncached_rate = round(max(0, total - cached) / elapsed, 3) if isinstance(total, (int, float)) and isinstance(cached, (int, float)) and elapsed else None
    return {'wall_seconds': round(wall_seconds, 4), 'ttft_seconds': round(first_token_seconds, 4) if first_token_seconds is not None else None,
            'load_seconds': seconds('load_duration'), 'prompt_tokens': packet.get('prompt_eval_count'), 'prompt_cached_tokens': packet.get('prompt_eval_cached_count'),
            'prompt_seconds': seconds('prompt_eval_duration'), 'prompt_tokens_per_second': rate('prompt_eval_count', 'prompt_eval_duration'), 'prompt_uncached_tokens_per_second': uncached_rate,
            'generated_tokens': packet.get('eval_count'), 'generation_seconds': seconds('eval_duration'),
            'generation_tokens_per_second': rate('eval_count', 'eval_duration'), 'server_total_seconds': seconds('total_duration')}


def record(model, mode, metrics, status='complete'):
    row = {'time': datetime.now(timezone.utc).isoformat(), 'model': model, 'mode': mode, 'status': status, **metrics}
    folder = Path(os.getenv('ROVNY_STATE_DIR', str(Path(__file__).resolve().parents[1] / '.state')))
    try:
        with _lock:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / 'performance.jsonl'
            if path.exists() and path.stat().st_size > 5 * 1024 * 1024:
                path.replace(folder / 'performance.previous.jsonl')
            with path.open('a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
    except OSError:
        pass  # A full log disk must not break a model response.
    return row
