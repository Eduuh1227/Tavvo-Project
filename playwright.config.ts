import {defineConfig, devices} from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: {timeout: 15_000},
  reporter: [['list'], ['html', {open: 'never'}]],
  use: {
    baseURL: process.env.TAVVO_E2E_ADMIN_URL || 'http://localhost:5173',
    ...devices['Desktop Chrome'],
    // Edge is already installed on Windows; CI can use the Playwright Chromium build.
    channel: process.env.TAVVO_E2E_BROWSER || (process.platform === 'win32' ? 'msedge' : undefined),
    headless: true,
    // Authentication is exercised with real secrets. Never persist a trace or storage state.
    trace: 'off',
    video: 'off',
    screenshot: 'only-on-failure',
  },
});
