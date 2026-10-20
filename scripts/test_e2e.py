"""Run live browser tests against locally provisioned demonstration data."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
local = root / '.local'
credentials = json.loads((local / 'demo-credentials.json').read_text())
records = json.loads((local / 'demo-records.json').read_text())
environment = os.environ.copy()
environment.update({
    'TAVVO_E2E_PASSWORD': credentials['password'],
    'TAVVO_E2E_RESTAURANT_A': records['a']['restaurant']['id'],
    'TAVVO_E2E_PRODUCT_A': records['a']['products'][0]['id'],
    'TAVVO_E2E_RESTAURANT_B': records['b']['restaurant']['id'],
    'TAVVO_E2E_PRODUCT_B': records['b']['products'][0]['id'],
    'TAVVO_E2E_ADMIN_STATE': str(local / 'admin-storage-state.json'),
})
command = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
raise SystemExit(subprocess.call([command, 'run', 'test:e2e', '--', *sys.argv[1:]], cwd=root, env=environment))
