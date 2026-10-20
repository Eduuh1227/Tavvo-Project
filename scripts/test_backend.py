"""Isolated test database; application database is never flushed by pytest."""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root / 'apps/api'))
from core.environment import load_local_environment

load_local_environment()
os.environ['DATABASE_URL'] = os.environ.get('MIGRATION_DATABASE_URL', os.environ['DATABASE_URL'])
import pytest

raise SystemExit(pytest.main(sys.argv[1:] or ['-q']))
