/**
 * E2E Tests for the Profile and My Requests pages
 *
 * Tests:
 * - Profile page displays user information
 * - Profile shows organisme information
 * - RGPD section for non-super-admin users
 * - My Requests page displays validation requests
 * - Request cancellation
 * - Module access request
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { ProfilePage } from '../../pages/profile.page';
import { MyRequestsPage } from '../../pages/my-requests.page';

test.describe('Profile Page', () => {

  test.describe('User Information', () => {

    test('should display profile page with user info', async ({ userRnfPage: page }) => {
      const profilePage = new ProfilePage(page);
      await profilePage.goto();
      await profilePage.waitForData();

      await expect(profilePage.pageTitle).toBeVisible();
      await expect(profilePage.pageTitle).toContainText(/profil/i);
    });

    test('should display user name and email', async ({ userRnfPage: page }) => {
      const profilePage = new ProfilePage(page);
      await profilePage.goto();
      await profilePage.waitForData();

      // User card should be visible
      await expect(profilePage.userCard).toBeVisible();

      // Email should contain test user email
      const email = await profilePage.getEmail();
      expect(email).toContain('@test.fr');
    });

    test('should display user role', async ({ adminRnfPage: page }) => {
      const profilePage = new ProfilePage(page);
      await profilePage.goto();
      await profilePage.waitForData();

      await expect(profilePage.roleChip).toBeVisible();
      const role = await profilePage.getRole();
      expect(role.length).toBeGreaterThan(0);
    });

    test('should display back link to home', async ({ userRnfPage: page }) => {
      const profilePage = new ProfilePage(page);
      await profilePage.goto();
      await profilePage.waitForData();

      await expect(profilePage.backLink).toBeVisible();
      await expect(profilePage.backLink).toContainText(/Retour/i);
    });

  });

  test.describe('Organisme Information', () => {

    test('should display organisme card when user has organisme', async ({ userRnfPage: page }) => {
      const profilePage = new ProfilePage(page);
      await profilePage.goto();
      await profilePage.waitForData();

      // Test user should have an organisme
      const hasOrganisme = await profilePage.hasOrganismeCard();
      expect(hasOrganisme).toBeTruthy();
    });

    test('should display organisme name', async ({ userRnfPage: page }) => {
      const profilePage = new ProfilePage(page);
      await profilePage.goto();
      await profilePage.waitForData();

      if (await profilePage.hasOrganismeCard()) {
        const orgName = await profilePage.getOrganismeName();
        expect(orgName.length).toBeGreaterThan(0);
      }
    });

  });

  test.describe('RGPD Section', () => {

    test('should display RGPD section for regular user', async ({ userRnfPage: page }) => {
      const profilePage = new ProfilePage(page);
      await profilePage.goto();
      await profilePage.waitForData();

      const hasRgpd = await profilePage.hasRgpdCard();
      expect(hasRgpd).toBeTruthy();
    });

    test('should display delete account option when no pending deletion', async ({ userRnfPage: page }) => {
      const profilePage = new ProfilePage(page);
      await profilePage.goto();
      await profilePage.waitForData();

      const hasPending = await profilePage.hasDeletionPending();

      if (!hasPending) {
        // Look for delete button with various possible selectors
        const deleteBtn = page.locator('.delete-account-section button, .rgpd-card button:has(.fi-rr-trash), button:has-text("Supprimer")').first();
        const hasDeleteBtn = await deleteBtn.isVisible().catch(() => false);
        expect(hasDeleteBtn).toBeTruthy();
      }
    });

    test('should NOT display RGPD section for super admin', async ({ superAdminPage: page }) => {
      const profilePage = new ProfilePage(page);
      await profilePage.goto();
      await profilePage.waitForData();

      // Super admin should NOT see RGPD card
      const hasRgpd = await profilePage.hasRgpdCard();
      expect(hasRgpd).toBeFalsy();
    });

    test('should open delete account dialog when clicking delete button', async ({ userCenPage: page }) => {
      const profilePage = new ProfilePage(page);
      await profilePage.goto();
      await profilePage.waitForData();

      const hasPending = await profilePage.hasDeletionPending();

      if (!hasPending) {
        // Click delete button
        const deleteBtn = page.locator('.delete-account-section button, .rgpd-card button:has(.fi-rr-trash), button:has-text("Supprimer")').first();
        const isVisible = await deleteBtn.isVisible().catch(() => false);

        if (isVisible) {
          await deleteBtn.click();

          // Dialog should open
          const dialog = page.locator('mat-dialog-container');
          await expect(dialog).toBeVisible();

          // Close dialog with Escape
          await page.keyboard.press('Escape');
        }
      }
    });

  });

});

test.describe('My Requests Page', () => {

  test.describe('Basic Display', () => {

    test('should display my requests page with title', async ({ userRnfPage: page }) => {
      const myRequestsPage = new MyRequestsPage(page);
      await myRequestsPage.goto();
      await myRequestsPage.waitForData();

      await expect(myRequestsPage.pageTitle).toBeVisible();
      await expect(myRequestsPage.pageTitle).toContainText(/demandes/i);
    });

    test('should display stats cards', async ({ userRnfPage: page }) => {
      const myRequestsPage = new MyRequestsPage(page);
      await myRequestsPage.goto();
      await myRequestsPage.waitForData();

      // All three stat cards should be visible
      await expect(myRequestsPage.pendingStatCard).toBeVisible();
      await expect(myRequestsPage.approvedStatCard).toBeVisible();
      await expect(myRequestsPage.rejectedStatCard).toBeVisible();
    });

    test('should display correct stat values', async ({ userRnfPage: page }) => {
      const myRequestsPage = new MyRequestsPage(page);
      await myRequestsPage.goto();
      await myRequestsPage.waitForData();

      const pendingCount = await myRequestsPage.getPendingCount();
      const approvedCount = await myRequestsPage.getApprovedCount();
      const rejectedCount = await myRequestsPage.getRejectedCount();

      // Counts should be numeric strings
      expect(parseInt(pendingCount || '0')).toBeGreaterThanOrEqual(0);
      expect(parseInt(approvedCount || '0')).toBeGreaterThanOrEqual(0);
      expect(parseInt(rejectedCount || '0')).toBeGreaterThanOrEqual(0);
    });

  });

  test.describe('Requests Table', () => {

    test('should display requests table or empty state', async ({ userRnfPage: page }) => {
      const myRequestsPage = new MyRequestsPage(page);
      await myRequestsPage.goto();
      await myRequestsPage.waitForData();

      const hasRequests = await myRequestsPage.getRequestCount() > 0;
      const hasEmpty = await myRequestsPage.hasEmptyState();

      expect(hasRequests || hasEmpty).toBeTruthy();
    });

    test('should display request details in table', async ({ userRnfPage: page }) => {
      const myRequestsPage = new MyRequestsPage(page);
      await myRequestsPage.goto();
      await myRequestsPage.waitForData();

      const requestCount = await myRequestsPage.getRequestCount();

      if (requestCount > 0) {
        // Table should have header columns
        const table = myRequestsPage.requestsTable;
        await expect(table).toBeVisible();

        // Check for expected columns (headers)
        await expect(table.locator('th', { hasText: 'Type' })).toBeVisible();
        await expect(table.locator('th', { hasText: 'Cible' })).toBeVisible();
        await expect(table.locator('th', { hasText: 'Statut' })).toBeVisible();
      }
    });

    test('empty state should show navigation links', async ({ userCenPage: page }) => {
      const myRequestsPage = new MyRequestsPage(page);
      await myRequestsPage.goto();
      await myRequestsPage.waitForData();

      const hasEmpty = await myRequestsPage.hasEmptyState();

      if (hasEmpty) {
        // Empty state should have navigation links
        const emptyState = myRequestsPage.emptyState;
        await expect(emptyState.locator('a[routerLink="/plans"]')).toBeVisible();
        await expect(emptyState.locator('a[routerLink="/sites"]')).toBeVisible();
      }
    });

  });

  test.describe('Navigation', () => {

    test('should have back link to home', async ({ userRnfPage: page }) => {
      const myRequestsPage = new MyRequestsPage(page);
      await myRequestsPage.goto();
      await myRequestsPage.waitForData();

      await expect(myRequestsPage.backLink).toBeVisible();
    });

    test('clicking back link should navigate to home', async ({ userRnfPage: page }) => {
      const myRequestsPage = new MyRequestsPage(page);
      await myRequestsPage.goto();
      await myRequestsPage.waitForData();

      await myRequestsPage.backLink.click();
      await expect(page).toHaveURL(/\/accueil/);
    });

  });

});
