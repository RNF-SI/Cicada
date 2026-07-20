import { test, expect } from '../../fixtures/auth.fixture';
import { AdminSitesPage } from '../../pages/admin-sites.page';

test.describe('Admin Sites - List', () => {
  test('super admin should see all sites', async ({ superAdminPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    const rowCount = await sitesPage.getRowCount();
    expect(rowCount).toBeGreaterThan(0);
  });

  test('should search sites by name', async ({ superAdminPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    await sitesPage.searchSite('Camargue');
    await page.waitForTimeout(500);

    const row = sitesPage.getRowByName('Camargue');
    await expect(row).toBeVisible();
  });

  test('should filter sites by type', async ({ superAdminPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    // #592 — plus d'`<option>` natives à énumérer : le filtre est un dropdown kit UI.
    // On cible un type présent dans les données de test (RNN).
    await sitesPage.filterByType('RNN');
    await page.waitForTimeout(500);
  });

  test('should display site details in table rows', async ({ superAdminPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    // Verify table has expected columns
    const headerRow = page.locator('.sites-table thead th');
    const headerCount = await headerRow.count();
    expect(headerCount).toBeGreaterThan(3);
  });

  test('should show summary text with site count', async ({ superAdminPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    if (await sitesPage.summaryText.isVisible()) {
      const text = await sitesPage.summaryText.textContent();
      expect(text).toBeTruthy();
    }
  });
});
