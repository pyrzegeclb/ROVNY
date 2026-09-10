import sys
from rovny.terminal import run_command


def test_output_is_bounded(tmp_path):
    result = run_command([sys.executable, '-c', 'import sys; sys.stdout.write("x" * 1500000)'], tmp_path)
    assert len(result['output']) <= 1024 * 1024


def test_private_tokens_not_in_child_environment(tmp_path, monkeypatch):
    monkeypatch.setenv('ROVNY_TOKEN', 'private-session')
    monkeypatch.setenv('ROVNY_API_KEY', 'private-provider-key')
    result = run_command([sys.executable, '-c', 'import os; print(os.getenv("ROVNY_TOKEN")); print(os.getenv("ROVNY_API_KEY"))'], tmp_path)
    assert result['output'].splitlines() == ['None', 'None']
