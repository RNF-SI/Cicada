import { test as setup, expect } from '@playwright/test';
import path from 'path';

const AUTH_DIR = path.join(__dirname, '..', '.auth');

const TEST_USERS = [
  { email: 'admin@test.fr', file: 'super-admin.json' },
  { email: 'admin.rnf@test.fr', file: 'admin-rnf.json' },
  { email: 'admin.cen@test.fr', file: 'admin-cen.json' },
  { email: 'referent.camargue@test.fr', file: 'referent.json' },
  { email: 'user.rnf@test.fr', file: 'user-rnf.json' },
  { email: 'user.cen@test.fr', file: 'user-cen.json' },
];

const PASSWORD = 'Test123!';

for (const user of TEST_USERS) {
  setup(`authenticate as ${user.email}`, async ({ page }) => {
    await page.goto('/auth/login');

    // Use formcontrolname selectors (reliable with Angular Material)
    await page.locator('input[formcontrolname="username"]').fill(user.email);
    await page.locator('input[formcontrolname="password"]').fill(PASSWORD);
    await page.locator('button[type="submit"]').click();

    // Wait for redirect to home page after login
    await expect(page).toHaveURL(/\/accueil/, { timeout: 15000 });

    // Verify JWT tokens are stored
    // The app stores tokens under 'auth_tokens' as JSON: { access: "...", refresh: "..." }
    const authTokens = await page.evaluate(() => {
      const raw = window.localStorage.getItem('auth_tokens');
      return raw ? JSON.parse(raw) : null;
    });
    expect(authTokens).toBeTruthy();
    expect(authTokens.access).toBeTruthy();

    // Save storage state
    await page.context().storageState({ path: path.join(AUTH_DIR, user.file) });
  });
}
