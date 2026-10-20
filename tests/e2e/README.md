# Real browser acceptance

These tests use the running Django API, Vite administration app and Next.js public site. There are no request mocks. Run them only against isolated development/CI data: they create menu records and deactivate a new table.

With the local stack running, execute `python scripts/seed_demo.py` and then `python scripts/test_e2e.py`. The seed creates active restaurants A/B, distinct managers, three categories and five products for A, two categories and three products for B, and Mesa 05. Only the initial platform account is bootstrapped directly; subsequent operations use the real HTTP API, including MFA.

The runner reads generated credentials and records from ignored `.local/` and passes the password, A/B restaurant/product IDs and MFA-authenticated administrator state through the process environment. No default password is committed or printed. Defaults are administration `http://localhost:5173`, public site `http://localhost:3000` and API `http://127.0.0.1:8000`; override with `TAVVO_E2E_ADMIN_URL`, `TAVVO_E2E_PUBLIC_URL` and `TAVVO_E2E_API_URL` if needed. The administration proxy and public site's `API_INTERNAL_URL` must point to the same API/database.

Run `npm run test:e2e`. Windows uses the installed Edge browser. Linux uses Playwright Chromium (`npx playwright install --with-deps chromium`); `TAVVO_E2E_BROWSER` can select another installed Playwright channel. Servers are started outside the test runner so local QA does not start duplicate processes.

The three mandatory tests check login/logout, category creation, draft/published/hidden products, exact decimal display, upload/render/hide/delete of real images through the S3 adapter, public isolation, unauthorized GET/PATCH in both directions A↔B, table creation, QR loading/resolution/revocation, mobile layout and platform creation/deactivation. The platform test requires short-lived MFA state; it cannot silently skip. Rerun the seed if that session expires. The S3 service must be running with its private bucket initialized; the Compose handles this automatically.

For persistence, run `python scripts/verify_persistence.py snapshot`, restart the applications/database while preserving data, and run `python scripts/verify_persistence.py verify` **without rerunning the seed**. The helper compares the full categories/products/settings/tables and public menu responses, checks both public pages and verifies that the runtime role has no superuser or RLS bypass privilege. The CI browser job runs the full Compose with PostgreSQL, MinIO, Gunicorn and the mail worker, and restarts persistent services before this comparison.

Report screenshots are ignored by Git. Tracing and video are disabled; the tests do not save authentication state or credentials into artifacts.
