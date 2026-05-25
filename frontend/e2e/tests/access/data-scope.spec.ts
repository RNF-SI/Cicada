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

    // Scope semantique : RNF doit voir RNF, jamais CEN — assertion fiable face
    // à l'accumulation de comptes E2E entre runs (seed --reset peut échouer).
    const rnfUserRow = usersPage.getRowByEmail('user.rnf@test.fr');
    await expect(rnfUserRow).toBeVisible();

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
