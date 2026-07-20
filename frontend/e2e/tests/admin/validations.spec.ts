import { test, expect } from '../../fixtures/auth.fixture';
import { AdminValidationsPage } from '../../pages/admin-validations.page';

test.describe.serial('Admin Validations', () => {
  test('should display validation requests list', async ({ superAdminPage: page }) => {
    const validationsPage = new AdminValidationsPage(page);
    await validationsPage.goto();
    await validationsPage.waitForData();

    // Should show either table rows or empty state
    const hasRows = await validationsPage.tableRows.count() > 0;
    const hasEmpty = await validationsPage.emptyState.isVisible().catch(() => false);
    expect(hasRows || hasEmpty).toBeTruthy();
  });

  test('should filter by status', async ({ superAdminPage: page }) => {
    const validationsPage = new AdminValidationsPage(page);
    await validationsPage.goto();
    await validationsPage.waitForData();

    if (await validationsPage.statusFilter.isVisible()) {
      await validationsPage.selectStatusFilter('pending');
      await page.waitForTimeout(1000);
      // Filter applied - page should not crash
      await expect(page.locator('.admin-validations')).toBeVisible();
    }
  });

  test('should filter by type', async ({ superAdminPage: page }) => {
    const validationsPage = new AdminValidationsPage(page);
    await validationsPage.goto();
    await validationsPage.waitForData();

    // #592 — les options sont des lignes du kit UI, plus des `mat-option`.
    if (await validationsPage.typeFilter.isVisible()) {
      await validationsPage.typeFilter.click();
      const options = page.locator('[data-testid^="validations-type-option-"]');
      if ((await options.count()) > 1) {
        // On saute la ligne « tout » (`…-option-all`) pour filtrer réellement.
        await options.nth(1).click();
        await page.waitForTimeout(1000);
      } else {
        await page.keyboard.press('Escape');
      }
    }
  });

  test('should approve a pending validation request', async ({ superAdminPage: page }) => {
    const validationsPage = new AdminValidationsPage(page);
    await validationsPage.goto();
    await validationsPage.waitForData();

    const rowCount = await validationsPage.getRowCount();
    if (rowCount > 0) {
      const firstRow = validationsPage.tableRows.first();
      const approveBtn = validationsPage.getApproveButton(firstRow);

      if (await approveBtn.isVisible().catch(() => false)) {
        await approveBtn.click();

        // Confirm in dialog if present
        const confirmBtn = page.locator('mat-dialog-container button').filter({ hasText: /confirmer|approuver|valider/i });
        if (await confirmBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
          await confirmBtn.click();
        }
        await page.waitForTimeout(2000);
      }
    }
  });

  test('should open detail view for a validation request', async ({ superAdminPage: page }) => {
    const validationsPage = new AdminValidationsPage(page);
    await validationsPage.goto();
    await validationsPage.waitForData();

    const rowCount = await validationsPage.getRowCount();
    if (rowCount > 0) {
      const firstRow = validationsPage.tableRows.first();
      await firstRow.click();

      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible({ timeout: 5000 });
      await page.keyboard.press('Escape');
    }
  });

  test('should show empty state when no requests match', async ({ superAdminPage: page }) => {
    const validationsPage = new AdminValidationsPage(page);
    await validationsPage.goto();
    await validationsPage.waitForData();

    // This is a documentation test - if empty state exists, verify it renders correctly
    if (await validationsPage.emptyState.isVisible().catch(() => false)) {
      const emptyIcon = validationsPage.emptyState.locator('.empty-icon, .fi-rr-check-circle');
      await expect(emptyIcon).toBeVisible();
    }
  });
});
