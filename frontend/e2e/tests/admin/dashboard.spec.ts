import { test, expect } from '../../fixtures/auth.fixture';
import { AdminDashboardPage } from '../../pages/admin-dashboard.page';

test.describe('Admin Dashboard', () => {
  test('super admin should access dashboard', async ({ superAdminPage: page }) => {
    const dashboardPage = new AdminDashboardPage(page);
    await dashboardPage.goto();
    await dashboardPage.waitForData();

    await expect(dashboardPage.pageTitle).toBeVisible();
  });

  test('should display statistics cards', async ({ superAdminPage: page }) => {
    const dashboardPage = new AdminDashboardPage(page);
    await dashboardPage.goto();
    await dashboardPage.waitForData();

    // Wait for stat cards to render (stats loaded async)
    await dashboardPage.statCards.first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});

    const cardCount = await dashboardPage.statCards.count();
    // Dashboard has stat cards for: plans, active plans, users, sites, organismes (super admin)
    expect(cardCount).toBeGreaterThanOrEqual(3);
  });

  test('should show welcome message with user name', async ({ superAdminPage: page }) => {
    const dashboardPage = new AdminDashboardPage(page);
    await dashboardPage.goto();
    await dashboardPage.waitForData();

    await expect(dashboardPage.welcomeMessage).toBeVisible();
    const text = await dashboardPage.welcomeMessage.textContent();
    expect(text).toBeTruthy();
  });
});
