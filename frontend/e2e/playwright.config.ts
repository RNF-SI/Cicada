import { defineConfig, devices } from '@playwright/test';

const isCI = !!process.env['CI'];

// Optional native Chromium binary (Alpine container side-runs use the
// system chromium installed via apk, since Playwright's bundled Ubuntu
// build is not glibc-compatible with Alpine).
const nativeChromium = process.env['PLAYWRIGHT_CHROMIUM_EXECUTABLE'];

// Exploration fédérée (#636). Ces tests visent une SECONDE instance CICADA,
// relayée vers le hub — une autre origine, donc un autre `storageState` : une
// session est liée à son origine, celle de l'instance principale n'y vaut rien.
//
// Opt-in : ils demandent le banc à trois briques (`scripts/federation.sh up`),
// que ni la CI ni un lancement ordinaire de la suite n'ont.
const federationEnabled = process.env['E2E_FEDERATION'] === '1';
const federationURL = process.env['E2E_CEN_URL'] ?? 'http://localhost:8081';

const chromiumLaunch = nativeChromium
  ? { launchOptions: { executablePath: nativeChromium } }
  : {};

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
      use: nativeChromium ? { launchOptions: { executablePath: nativeChromium } } : {},
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        ...(nativeChromium ? { launchOptions: { executablePath: nativeChromium } } : {}),
      },
      dependencies: ['auth-setup'],
      testMatch: /tests\/.*\.spec\.ts/,
      // La fédération a ses propres projets, sur une autre origine.
      testIgnore: /tests\/federation\/.*/,
    },
    ...(federationEnabled
      ? [
          {
            name: 'federation-auth',
            testMatch: /fixtures\/auth-federation\.setup\.ts/,
            use: { baseURL: federationURL, ...chromiumLaunch },
          },
          {
            name: 'federation',
            use: {
              ...devices['Desktop Chrome'],
              baseURL: federationURL,
              ...chromiumLaunch,
            },
            dependencies: ['federation-auth'],
            testMatch: /tests\/federation\/.*\.spec\.ts/,
          },
        ]
      : []),
  ],

  // Les tests de fédération visent des instances déjà lancées par
  // `scripts/federation.sh up` : démarrer un serveur de développement en plus
  // ferait tourner une troisième interface qui ne sert à rien.
  ...(isCI || federationEnabled
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
