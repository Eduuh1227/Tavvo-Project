"""Management entrypoint: migrations explicitly use the owner connection."""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'apps/api'))
from core.environment import load_local_environment

load_local_environment()
if len(sys.argv) > 1 and sys.argv[1] in ('migrate', 'makemigrations'):
    os.environ['DATABASE_URL'] = os.environ.get('MIGRATION_DATABASE_URL', os.environ['DATABASE_URL'])
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.core.management import execute_from_command_line

execute_from_command_line(sys.argv)
