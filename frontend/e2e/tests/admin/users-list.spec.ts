import { test, expect } from '../../fixtures/auth.fixture';
import { AdminUsersPage } from '../../pages/admin-users.page';

test.describe('Admin Users - List', () => {
  test('super admin should see all users', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const rowCount = await usersPage.getRowCount();
    expect(rowCount).toBeGreaterThan(0);
  });

  test('admin organisme should see only users from their organisme', async ({ adminRnfPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const rowCount = await usersPage.getRowCount();
    expect(rowCount).toBeGreaterThan(0);

    // Admin RNF should see RNF users but not CEN users
    const rnfUser = usersPage.getRowByEmail('user.rnf@test.fr');
    await expect(rnfUser).toBeVisible();

    const cenUser = usersPage.getRowByEmail('user.cen@test.fr');
    await expect(cenUser).not.toBeVisible();
  });

  test('should search users by name or email', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    await usersPage.searchUser('admin');
    // Wait for filter to apply
    await page.waitForTimeout(500);

    const rowCount = await usersPage.getRowCount();
    expect(rowCount).toBeGreaterThan(0);
  });

  test('should filter users by role', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    await usersPage.filterByRole('admin_og');
    await page.waitForTimeout(500);

    const rowCount = await usersPage.getRowCount();
    expect(rowCount).toBeGreaterThan(0);
  });

  test('should filter users by status', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    await usersPage.filterByStatus('active');
    await page.waitForTimeout(500);

    const rowCount = await usersPage.getRowCount();
    expect(rowCount).toBeGreaterThan(0);
  });

  test('should display page title', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    await expect(usersPage.pageTitle).toBeVisible();
  });
});
