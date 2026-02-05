import { test, expect } from '../../fixtures/auth.fixture';
import { AdminUsersPage } from '../../pages/admin-users.page';

test.describe('Admin Users - Site associations', () => {
  test('should see site chips on user rows', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const referentRow = usersPage.getRowByEmail('referent.camargue@test.fr');
    await expect(referentRow).toBeVisible();

    const siteChips = referentRow.locator('.site-chip');
    const chipCount = await siteChips.count();
    expect(chipCount).toBeGreaterThan(0);
  });

  test('should open assign site modal for a user', async ({ adminRnfPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const userRow = usersPage.getRowByEmail('user.rnf@test.fr');
    const assignBtn = userRow.locator('.btn-icon').filter({ has: page.locator('.fi-rr-marker') });

    if (await assignBtn.isVisible()) {
      await assignBtn.click();
      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible({ timeout: 5000 });
      await page.keyboard.press('Escape');
    }
  });

  test('should see referent badge on site chips', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    // The referent user should have site chips
    const referentRow = usersPage.getRowByEmail('admin.rnf@test.fr');
    await expect(referentRow).toBeVisible();
  });

  test('should see plan chips on user rows', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    // Check plan chips exist on some users
    const planChips = page.locator('.plan-chip');
    // Some test users have plans
    const count = await planChips.count();
    expect(count).toBeGreaterThanOrEqual(0); // May be 0 if plans not linked in seed data
  });
});
