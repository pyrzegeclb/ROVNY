import json
from rovny.metrics import measure, record


def test_ns_conversion_and_missing_values():
    m = measure({'eval_count': 24, 'eval_duration': 2_000_000_000, 'prompt_eval_count': 60, 'prompt_eval_duration': 500_000_000}, 3.5, 1.2)
    assert m['generation_tokens_per_second'] == 12
    assert m['prompt_tokens_per_second'] == 120
    assert m['ttft_seconds'] == 1.2
    assert measure({}, 1)['generation_tokens_per_second'] is None
    assert measure({'eval_duration': 0, 'eval_count': 2}, 1)['generation_tokens_per_second'] is None


def test_logs_contain_only_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv('ROVNY_STATE_DIR', str(tmp_path))
    record('test-model', 'chat', measure({'eval_count': 10, 'eval_duration': 1e9}, 2, 0.5))
    row = json.loads((tmp_path / 'performance.jsonl').read_text())
    assert row['generation_tokens_per_second'] == 10
    assert 'prompt' not in row and 'response' not in row and 'token' not in row
