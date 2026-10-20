"""Load literal KEY=value local configuration; process environment always wins."""
import os
from pathlib import Path


def load_local_environment():
    path = Path(__file__).resolve().parents[3] / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())
