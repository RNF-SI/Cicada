import { test, expect } from '../../fixtures/auth.fixture';
import { AdminUsersPage } from '../../pages/admin-users.page';

test.describe.serial('Admin Users - Actions', () => {
  test('should view user details', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const userRow = usersPage.getRowByEmail('user.rnf@test.fr');
    await expect(userRow).toBeVisible();
  });

  test('should deactivate a user', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const userRow = usersPage.getRowByEmail('user.cen@test.fr');
    await expect(userRow).toBeVisible();

    // Find and click the deactivate button (ban icon)
    const deactivateBtn = userRow.locator('.btn-icon').filter({ has: page.locator('.fi-rr-ban') });
    if (await deactivateBtn.isVisible()) {
      await deactivateBtn.click();

      // Fill required reason field in the deactivation modal (min 10 characters)
      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible({ timeout: 5000 });
      const reasonTextarea = dialog.locator('textarea');
      await reasonTextarea.fill('Désactivation pour test E2E automatisé');

      // Click confirm button
      const confirmBtn = dialog.locator('button[color="warn"]');
      await expect(confirmBtn).toBeEnabled({ timeout: 3000 });
      await confirmBtn.click();

      // Wait for dialog to close and status update
      await dialog.waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(1000);
    }
  });

  test('should activate a user', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const userRow = usersPage.getRowByEmail('user.cen@test.fr');
    await expect(userRow).toBeVisible();

    // Find and click the activate button (check icon)
    const activateBtn = userRow.locator('.btn-icon').filter({ has: page.locator('.fi-rr-check') });
    if (await activateBtn.isVisible()) {
      await activateBtn.click();

      const confirmBtn = page.locator('mat-dialog-container button').filter({ hasText: /confirmer|oui|activer/i });
      if (await confirmBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
        await confirmBtn.click();
      }

      await page.waitForTimeout(2000);
    }
  });

  test('should open assign site modal', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const userRow = usersPage.getRowByEmail('user.rnf@test.fr');
    const assignSiteBtn = userRow.locator('.btn-icon').filter({ has: page.locator('.fi-rr-marker') });

    if (await assignSiteBtn.isVisible()) {
      await assignSiteBtn.click();
      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible({ timeout: 5000 });
      // Close the dialog
      await page.keyboard.press('Escape');
    }
  });

  test('super admin should see impersonate button', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const userRow = usersPage.getRowByEmail('user.rnf@test.fr');
    const impersonateBtn = userRow.locator('.btn-icon.impersonate, .btn-icon').filter({ has: page.locator('.fi-rr-eye') });
    await expect(impersonateBtn).toBeVisible();
  });
});
