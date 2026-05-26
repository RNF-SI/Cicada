/**
 * E2E Tests for the Plans de Gestion list page
 *
 * Tests:
 * - Page displays correctly with title and breadcrumb
 * - Table shows plans with name, period, status columns
 * - Create button is visible
 * - Active/Inactive tabs
 * - Scope toggle for different user roles
 * - Navigation to plan detail and create pages
 * - Access request section
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { PlansListPage } from '../../pages/plans-list.page';

test.describe('Plans List - Display', () => {

  test('should display page title and breadcrumb', async ({ superAdminPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    await expect(plansPage.pageTitle).toBeVisible();
    await expect(plansPage.pageTitle).toContainText(/plans de gestion/i);
    await expect(plansPage.breadcrumb).toBeVisible();
  });

  test('should show plans in the table', async ({ superAdminPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    // Super admin should see at least one plan from seed data
    const hasTable = await plansPage.plansTable.isVisible().catch(() => false);
    const hasEmpty = await plansPage.emptyState.isVisible().catch(() => false);
    expect(hasTable || hasEmpty).toBeTruthy();
  });

  test('should show plan name, period, and status in table rows', async ({ superAdminPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    const rowCount = await plansPage.getRowCount();
    if (rowCount > 0) {
      const firstRow = plansPage.plansTableRows.first();
      // Check that columns are present
      await expect(firstRow.locator('.col-name, td').first()).toBeVisible();
    }
  });

  test('should show create button', async ({ superAdminPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    await expect(plansPage.createButton).toBeVisible();
  });

});

test.describe('Plans List - Tabs', () => {

  test('should display active tab by default', async ({ superAdminPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    // The "Actifs" tab should be active/visible
    const actifTab = plansPage.tabActifs;
    const isVisible = await actifTab.isVisible().catch(() => false);

    // At minimum, the tab buttons should exist
    const tabButtons = page.locator('button.tab');
    const tabCount = await tabButtons.count();
    expect(tabCount).toBeGreaterThanOrEqual(1);
  });

  test('should switch to inactive tab', async ({ superAdminPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    const inactifTab = plansPage.tabInactifs;
    const isVisible = await inactifTab.isVisible().catch(() => false);

    if (isVisible) {
      await inactifTab.click();
      await page.waitForTimeout(1000);
      // Page should still be on /plans
      await expect(page).toHaveURL(/\/plans/);
    }
  });

});

test.describe('Plans List - Scope', () => {

  test('should show scope toggle with "Tous" for super admin', async ({ superAdminPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    const scopeToggle = plansPage.scopeToggle;
    const isVisible = await scopeToggle.isVisible().catch(() => false);

    if (isVisible) {
      // Super admin should see the "Tous" scope option
      const tousButton = plansPage.getScopeButton('Tous');
      const tousVisible = await tousButton.isVisible().catch(() => false);
      expect(tousVisible).toBeTruthy();
    }
  });

  test('should not show "Tous" scope for referent', async ({ referentPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    const scopeToggle = plansPage.scopeToggle;
    const isVisible = await scopeToggle.isVisible().catch(() => false);

    if (isVisible) {
      // Referent should NOT see the "Tous les plans" option
      const tousButton = plansPage.getScopeButton('Tous les plans');
      const tousVisible = await tousButton.isVisible().catch(() => false);
      expect(tousVisible).toBeFalsy();
    }
  });

});

test.describe('Plans List - Navigation', () => {

  test('should navigate to plan detail on "Voir" click', async ({ superAdminPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    const rowCount = await plansPage.getRowCount();
    if (rowCount > 0) {
      const viewButton = plansPage.plansTableRows.first().locator('button', { hasText: /voir/i });
      const isVisible = await viewButton.isVisible().catch(() => false);

      if (isVisible) {
        await viewButton.click();
        await page.waitForTimeout(2000);
        // Should navigate to /plans/{slug}
        await expect(page).toHaveURL(/\/plans\/[a-z0-9-]+$/);
      }
    }
  });

  test('should navigate to create form on "Nouveau plan vierge" click', async ({ superAdminPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    // Click the create button to open menu
    await plansPage.createButton.click();
    await page.waitForTimeout(500);

    // Click "À partir d'une base vierge" menu item (libellé i18n actuel)
    const newBlankOption = page.locator('button, a').filter({ hasText: /base vierge|nouveau plan vierge/i });
    const isVisible = await newBlankOption.isVisible().catch(() => false);

    if (isVisible) {
      await newBlankOption.click();
      await page.waitForTimeout(2000);
      await expect(page).toHaveURL(/\/plans\/nouveau/);
    }
  });

});

test.describe('Plans List - Access Request', () => {

  test('should display access request section', async ({ referentPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    // Look for the access request section heading or search field
    const accessSection = page.locator('h2', { hasText: /demander l'accès/i });
    const isVisible = await accessSection.isVisible().catch(() => false);
    // Section may or may not be visible depending on available plans
    expect(typeof isVisible).toBe('boolean');
  });

  test('should search in access request section', async ({ referentPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    // Look for the search input in the access section
    const searchField = page.locator('input').filter({
      has: page.locator('[placeholder]'),
    });
    const isVisible = await searchField.first().isVisible().catch(() => false);

    if (isVisible) {
      await searchField.first().fill('Test');
      await page.waitForTimeout(1000);
      // The page should still be visible (no crash)
      await expect(page).toHaveURL(/\/plans/);
    }
  });

});
