import { test, expect } from '../../fixtures/auth.fixture';

test.describe('Navigation', () => {
  test('header should show correct links for authenticated user', async ({ superAdminPage: page }) => {
    await page.goto('/accueil');

    // Header should be visible
    const header = page.locator('.header');
    await expect(header).toBeVisible();

    // Admin button should be visible for admin users
    const adminBtn = page.locator('.admin-btn, .nav-link').filter({ has: page.locator('.fi-rr-settings-sliders') });
    await expect(adminBtn).toBeVisible();

    // Notification bell should be visible
    const notifBell = page.locator('app-notification-bell');
    await expect(notifBell).toBeVisible();
  });

  test('admin sidebar should show role-appropriate items', async ({ superAdminPage: page }) => {
    await page.goto('/administration/dashboard');

    const sidebar = page.locator('.admin-sidebar');
    await expect(sidebar).toBeVisible();

    // Super admin should see dashboard, users, sites, etc.
    await expect(sidebar.locator('.nav-item').filter({ hasText: /tableau de bord/i })).toBeVisible();
    await expect(sidebar.locator('.nav-item').filter({ hasText: /utilisateurs/i })).toBeVisible();
    await expect(sidebar.locator('.nav-item').filter({ hasText: /sites/i })).toBeVisible();
  });

  test('admin sidebar should hide restricted items for admin organisme', async ({ adminRnfPage: page }) => {
    await page.goto('/administration/utilisateurs');

    const sidebar = page.locator('.admin-sidebar');
    await expect(sidebar).toBeVisible();

    // Admin org should NOT see dashboard
    const dashboardItem = sidebar.locator('.nav-item').filter({ hasText: /tableau de bord/i });
    await expect(dashboardItem).toBeHidden();

    // But should see users, sites, validations
    await expect(sidebar.locator('.nav-item').filter({ hasText: /utilisateurs/i })).toBeVisible();
    await expect(sidebar.locator('.nav-item').filter({ hasText: /validations/i })).toBeVisible();
  });

  test('should navigate between pages without errors', async ({ superAdminPage: page }) => {
    // Start at home
    await page.goto('/accueil');
    await expect(page).toHaveURL(/\/accueil/);

    // Go to profile
    await page.goto('/profile');
    await expect(page).toHaveURL(/\/profile/);

    // Go to admin
    await page.goto('/administration/dashboard');
    await expect(page).toHaveURL(/\/administration\/dashboard/);

    // Go to sites
    await page.goto('/sites');
    await expect(page).toHaveURL(/\/sites/);

    // No console errors indicating crashes
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/accueil');
    await page.waitForTimeout(1000);
    // Filter out non-critical errors
    const criticalErrors = errors.filter(e => !e.includes('ChunkLoadError'));
    expect(criticalErrors.length).toBe(0);
  });
});
