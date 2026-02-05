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
    const restrictedPages = [
      '/administration/utilisateurs',
      '/administration/organismes',
      '/administration/dashboard',
    ];

    for (const url of restrictedPages) {
      await page.goto(url);
      await page.waitForTimeout(3000);
      const currentUrl = page.url();
      // Should be redirected away - either to another admin page, accueil, or login
      const lastSegment = url.split('/').pop()!;
      const isRedirected = !currentUrl.includes(lastSegment) ||
        currentUrl.includes('/auth/login') ||
        currentUrl.includes('/accueil');
      expect(isRedirected).toBeTruthy();
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
