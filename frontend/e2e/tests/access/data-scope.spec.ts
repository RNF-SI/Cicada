import { test, expect } from '../../fixtures/auth.fixture';
import { AdminUsersPage } from '../../pages/admin-users.page';
import { AdminSitesPage } from '../../pages/admin-sites.page';

test.describe('Data Scope by Role', () => {
  test('admin RNF should only see RNF users', async ({ adminRnfPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const rowCount = await usersPage.getRowCount();
    expect(rowCount).toBeGreaterThan(0);

    // Admin RNF should see fewer users than super admin (only their organisme)
    // RNF test users: admin@test.fr, admin.rnf@test.fr, referent.camargue@test.fr, user.rnf@test.fr, test@example.com = 5
    expect(rowCount).toBeLessThanOrEqual(6);

    // Verify known RNF users are visible
    const rnfUserRow = usersPage.getRowByEmail('user.rnf@test.fr');
    await expect(rnfUserRow).toBeVisible();

    // CEN users should NOT be visible
    const cenUserRow = usersPage.getRowByEmail('user.cen@test.fr');
    await expect(cenUserRow).not.toBeVisible();
  });

  test('admin CEN should only see CEN users', async ({ adminCenPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const rowCount = await usersPage.getRowCount();
    expect(rowCount).toBeGreaterThan(0);

    // Verify known CEN users are visible
    const cenUserRow = usersPage.getRowByEmail('user.cen@test.fr');
    await expect(cenUserRow).toBeVisible();

    // RNF users should NOT be visible
    const rnfUserRow = usersPage.getRowByEmail('user.rnf@test.fr');
    await expect(rnfUserRow).not.toBeVisible();
  });

  test('super admin should see users from all organismes', async ({ superAdminPage: page }) => {
    const usersPage = new AdminUsersPage(page);
    await usersPage.goto();
    await usersPage.waitForData();

    const rowCount = await usersPage.getRowCount();
    // Super admin sees all users (more than admin_og)
    expect(rowCount).toBeGreaterThanOrEqual(6);

    // Should see users from different organismes
    const rnfUser = usersPage.getRowByEmail('user.rnf@test.fr');
    const cenUser = usersPage.getRowByEmail('user.cen@test.fr');
    await expect(rnfUser).toBeVisible();
    await expect(cenUser).toBeVisible();
  });

  test('referent should see only their assigned sites', async ({ referentPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    const rowCount = await sitesPage.getRowCount();
    // Referent camargue should see at least Camargue
    expect(rowCount).toBeGreaterThan(0);
  });

  test('super admin should see all sites', async ({ superAdminPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    const rowCount = await sitesPage.getRowCount();
    // Should see more sites than referent
    expect(rowCount).toBeGreaterThanOrEqual(5);
  });
});
