import os
import signal
import subprocess
import tempfile
import time


def run_command(argv, root):
    if not argv or len(argv) > 100 or any('\x00' in a for a in argv):
        raise ValueError('Provide a valid argument array')
    # No implicit shell. Commands still execute with the user's OS permissions.
    if os.name == 'nt' and argv[0].lower().endswith(('.bat', '.cmd')):
        raise ValueError('Windows batch files require an explicit shell such as cmd.exe /c')
    env = {k: v for k, v in os.environ.items() if k not in {'ROVNY_API_KEY', 'ROVNY_TOKEN'}}
    with tempfile.TemporaryFile() as output:
        proc = subprocess.Popen(argv, cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                start_new_session=os.name != 'nt', creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
        deadline = time.monotonic() + 30
        reason = None
        while proc.poll() is None:
            if time.monotonic() > deadline or os.fstat(output.fileno()).st_size > 1024 * 1024:
                reason = 'Stopped: 30-second or 1 MiB output limit'
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], capture_output=True)
                else:
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
                break
            time.sleep(0.05)
        output.seek(0)
        text = output.read(1024 * 1024).decode('utf-8', errors='replace')
    return {'exit_code': proc.returncode, 'output': text, 'notice': reason}
