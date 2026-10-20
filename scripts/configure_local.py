"""Generate local-only secrets without printing them or overwriting an existing file."""
import base64
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / '.env'
if target.exists():
    raise SystemExit('.env already exists; no changes made.')
password = secrets.token_urlsafe(32)
app_password = secrets.token_urlsafe(32)
target.write_text('\n'.join([
    'TAVVO_ENV=development',
    f'DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}',
    f'TAVVO_MFA_ENCRYPTION_KEY={base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()}',
    f'POSTGRES_PASSWORD={password}',
    f'TAVVO_DB_PASSWORD={app_password}',
    f'DATABASE_URL=postgresql://tavvo_app:{app_password}@127.0.0.1:55432/tavvo',
    f'MIGRATION_DATABASE_URL=postgresql://postgres:{password}@127.0.0.1:55432/tavvo',
    'DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver',
    'CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173',
    'TAVVO_ADMIN_ORIGIN=http://localhost:5173',
    'TAVVO_PUBLIC_ORIGIN=http://localhost:3000',
    'S3_ENDPOINT_URL=http://127.0.0.1:9000',
    'S3_BUCKET=tavvo-images',
    'S3_REGION=us-east-1',
    'S3_ACCESS_KEY=local-development',
    f'S3_SECRET_KEY={secrets.token_urlsafe(32)}',
    'EMAIL_HOST=localhost', 'EMAIL_PORT=1025',
]) + '\n', encoding='utf-8')
print('Created .env with local-only secrets. Do not commit it.')
