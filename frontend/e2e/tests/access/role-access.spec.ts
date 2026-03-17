import { test, expect } from '../../fixtures/auth.fixture';

test.describe('Role-based Access Control', () => {
  test('super admin should access all admin pages', async ({ superAdminPage: page }) => {
    const pages = [
      '/administration/dashboard',
      '/administration/utilisateurs',
      '/administration/organismes',
      '/administration/sites',
      '/administration/plans',
      '/administration/validations',
      '/administration/modules',
      '/administration/logs',
      '/administration/rgpd',
    ];

    for (const url of pages) {
      await page.goto(url);
      // Should not be redirected to login
      await expect(page).not.toHaveURL(/\/auth\/login/, { timeout: 5000 });
    }
  });

  test('admin organisme should access users, sites, validations, organismes, plans', async ({ adminRnfPage: page }) => {
    const allowedPages = [
      '/administration/utilisateurs',
      '/administration/organismes',
      '/administration/sites',
      '/administration/plans',
      '/administration/validations',
    ];

    for (const url of allowedPages) {
      await page.goto(url);
      await expect(page).not.toHaveURL(/\/auth\/login/, { timeout: 5000 });
    }
  });

  test('admin organisme should not access dashboard, modules, logs, rgpd', async ({ adminRnfPage: page }) => {
    const restrictedPages = [
      '/administration/dashboard',
      '/administration/modules',
      '/administration/logs',
      '/administration/rgpd',
    ];

    for (const url of restrictedPages) {
      await page.goto(url);
      // Should be redirected away from the restricted page
      await page.waitForTimeout(2000);
      const currentUrl = page.url();
      expect(currentUrl).not.toContain(url.split('/').pop());
    }
  });

  test('referent should access validations, sites, plans', async ({ referentPage: page }) => {
    const allowedPages = [
      '/administration/validations',
      '/administration/sites',
      '/administration/plans',
    ];

    for (const url of allowedPages) {
      await page.goto(url);
      await expect(page).not.toHaveURL(/\/auth\/login/, { timeout: 5000 });
    }
  });

  test('referent should not access users, organismes, dashboard', async ({ referentPage: page }) => {
    // Navigate to accueil first to ensure Angular is bootstrapped
    await page.goto('/accueil');
    await page.waitForTimeout(1000);

    const restrictedPages = [
      { url: '/administration/utilisateurs', marker: '.users-table, .users-list' },
      { url: '/administration/organismes', marker: '.organismes-grid, .organisme-detail' },
      { url: '/administration/dashboard', marker: '.dashboard-stats, .admin-dashboard' },
    ];

    for (const { url, marker } of restrictedPages) {
      await page.goto(url);
      await page.waitForTimeout(3000);

      // Either the URL changed (redirect) or the restricted content is not visible
      const currentUrl = page.url();
      const lastSegment = url.split('/').pop()!;
      const wasRedirected = !currentUrl.includes(lastSegment) ||
        currentUrl.includes('/accueil') ||
        currentUrl.includes('/validations') ||
        currentUrl.includes('/auth/login');
      const contentVisible = await page.locator(marker).first().isVisible().catch(() => false);

      // Test passes if redirected OR if restricted content is not shown
      expect(wasRedirected || !contentVisible).toBeTruthy();
    }
  });

  test('regular user should be redirected when accessing admin', async ({ userRnfPage: page }) => {
    await page.goto('/administration/utilisateurs');
    await page.waitForTimeout(3000);

    // Should be redirected away from admin
    const currentUrl = page.url();
    expect(currentUrl).not.toContain('/administration/utilisateurs');
  });

  test('unauthenticated user should be redirected to login', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('http://localhost:4200/administration/dashboard');
    await expect(page).toHaveURL(/\/auth\/login/, { timeout: 10000 });

    await context.close();
  });

  test('login page should be accessible without authentication', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('http://localhost:4200/auth/login');
    await expect(page).toHaveURL(/\/auth\/login/);
    await expect(page.locator('input[formcontrolname="username"]')).toBeVisible();

    await context.close();
  });
});
