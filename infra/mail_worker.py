"""Run the durable PostgreSQL mail queue in bounded batches; no addresses/tokens logged."""
import signal
import subprocess
import sys
from pathlib import Path
from threading import Event


def main():
    stopped = Event()
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    manage = Path(__file__).resolve().parents[1] / 'scripts/manage.py'
    while not stopped.is_set():
        result = subprocess.run([sys.executable, str(manage), 'process_auth_mail', '--limit', '100'], check=False)
        if result.returncode:
            print('Mail batch failed; retrying after interval.', flush=True)
        stopped.wait(10)


if __name__ == '__main__':
    main()
