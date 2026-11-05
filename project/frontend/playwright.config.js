import { defineConfig } from '@playwright/test';

export default defineConfig({
    testDir: './tests/browser',
    timeout: 120000,
    expect: { timeout: 15000 },
    workers: 1,
    fullyParallel: false,
    reporter: 'list',
    use: {
        baseURL: process.env.APP_TEST_URL || 'http://127.0.0.1:8000',
        channel: process.env.PLAYWRIGHT_CHANNEL || (process.platform === 'win32' ? 'msedge' : 'chromium'),
        headless: true,
        actionTimeout: 15000,
        viewport: { width: 1440, height: 1000 },
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
    },
});
