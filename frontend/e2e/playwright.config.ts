import { defineConfig, devices } from '@playwright/test';

const isCI = !!process.env['CI'];

export default defineConfig({
  testDir: '.',
  outputDir: '../test-results',
  globalSetup: require.resolve('./global-setup'),
  globalTeardown: require.resolve('./global-teardown'),
  fullyParallel: false,
  forbidOnly: isCI,
  retries: isCI ? 2 : 3,
  workers: isCI ? 2 : 2,
  timeout: 60000,
  reporter: isCI
    ? [['html', { outputFolder: '../playwright-report' }], ['junit', { outputFile: '../e2e-results.xml' }]]
    : [['html', { outputFolder: '../playwright-report', open: 'never' }]],

  use: {
    baseURL: 'http://localhost:4200',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'on-first-retry',
    locale: 'fr-FR',
    timezoneId: 'Europe/Paris',
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  projects: [
    {
      name: 'auth-setup',
      testMatch: /fixtures\/auth\.setup\.ts/,
    },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['auth-setup'],
      testMatch: /tests\/.*\.spec\.ts/,
    },
  ],

  ...(isCI
    ? {}
    : {
        webServer: {
          command: 'npm start',
          url: 'http://localhost:4200',
          reuseExistingServer: true,
          cwd: '..',
          timeout: 120000,
        },
      }),
});
