import type {BrowserContext} from '@playwright/test';

/** Use a bounded preview share link without disabling deployment protection. */
export async function previewAccess(context: BrowserContext) {
  const token = process.env.TAVVO_E2E_SHARE_TOKEN;
  if (!token) return;
  const origin = new URL(process.env.TAVVO_E2E_ADMIN_URL || 'http://localhost:5173');
  if (origin.protocol !== 'https:' || !origin.hostname.endsWith('.vercel.app')) {
    throw new Error('Preview access requires an explicit Vercel HTTPS origin.');
  }
  origin.searchParams.set('_vercel_share', token);
  const response = await context.request.get(origin.href);
  if (!response.ok()) throw new Error(`Preview access failed: ${response.status()}`);
}
