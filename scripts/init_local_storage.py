"""Initialize the local private S3 bucket using the generated development environment."""
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'apps/api'))
sys.path.insert(0, str(root))
from core.environment import load_local_environment
from infra.init_storage import main

load_local_environment()
host = urlsplit(os.environ['S3_ENDPOINT_URL']).hostname
if os.getenv('TAVVO_ENV', 'development') != 'development' or host not in ('localhost', '127.0.0.1', 'storage'):
    raise SystemExit('This helper initializes local development storage only.')
main()
