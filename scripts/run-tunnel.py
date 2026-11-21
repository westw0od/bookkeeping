"""Supervise a temporary outbound tunnel and keep its logs bounded."""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from runtime_logging import tunnel_logger

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', choices=['http2', 'quic'], default='http2')
    args = parser.parse_args()
    logger = tunnel_logger()
    state_path = ROOT / '.local' / 'tunnel.json'
    binary = ROOT / '.local' / 'cloudflared.exe'
    if not binary.is_file():
        raise SystemExit('Install the verified official cloudflared binary in .local first.')
    state = {'active': False, 'url': None, 'supervisor_pid': os.getpid(), 'started_at': datetime.now(timezone.utc).isoformat()}
    def save():
        temporary = state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, indent=2), encoding='utf-8')
        temporary.replace(state_path)
    save()
    # Each child reconnects internally; retry a crashed child with a bounded delay.
    for attempt in range(5):
        command = [str(binary), 'tunnel', '--url', 'http://127.0.0.1:8000', '--no-autoupdate',
                   '--protocol', args.protocol, '--metrics', '127.0.0.1:20241']
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding='utf-8', errors='replace',
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        state.update(active=False, pid=child.pid, attempt=attempt + 1)
        save()
        for line in child.stdout:
            logger.info(line.rstrip())
            found = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
            if found:
                state['url'] = found.group(); save()
            if 'Registered tunnel connection' in line:
                state['active'] = True; save()
        child.wait()
        state.update(active=False, exit_code=child.returncode); save()
        logger.warning('Tunnel exited with code %s; attempt %s/5', child.returncode, attempt + 1)
        if attempt < 4:
            time.sleep(min(5 * (attempt + 1), 20))

if __name__ == '__main__':
    main()
