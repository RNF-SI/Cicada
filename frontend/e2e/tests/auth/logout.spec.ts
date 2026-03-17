import { test, expect } from '../../fixtures/auth.fixture';

test.describe('Logout', () => {
  test('should clear tokens from localStorage on logout', async ({ superAdminPage: page }) => {
    await page.goto('/accueil');
    await expect(page).toHaveURL(/\/accueil/);

    // Open user menu and click logout
    const menuTrigger = page.locator('button.user-menu-trigger');
    await menuTrigger.waitFor({ state: 'visible', timeout: 10000 });
    await menuTrigger.click();
    // Wait for menu to open (Material animation)
    const logoutBtn = page.locator('.logout-item, [class*="logout"]');
    await logoutBtn.waitFor({ state: 'visible', timeout: 5000 });
    await logoutBtn.click();

    // Wait for logout to process
    await page.waitForTimeout(2000);

    // Tokens should be cleared
    const authTokens = await page.evaluate(() => window.localStorage.getItem('auth_tokens'));
    expect(authTokens).toBeFalsy();
  });

  test('should redirect to login when accessing protected route after logout', async ({ superAdminPage: page }) => {
    await page.goto('/accueil');

    // Manually clear tokens to simulate logout
    await page.evaluate(() => {
      window.localStorage.removeItem('auth_tokens');
      window.localStorage.removeItem('current_user');
      window.localStorage.removeItem('auth_token_timestamp');
    });

    await page.goto('/administration/dashboard');
    await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10000 });
  });

  test('should show logout button in user menu', async ({ superAdminPage: page }) => {
    await page.goto('/accueil');
    await page.locator('button.user-menu-trigger').click();

    const logoutItem = page.locator('button.logout-item');
    await expect(logoutItem).toBeVisible();
  });
});
