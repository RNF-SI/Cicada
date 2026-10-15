import { test, expect } from '../../fixtures/auth.fixture';
import { AdminSitesPage } from '../../pages/admin-sites.page';

test.describe.serial('Admin Sites - CRUD', () => {
  test('super admin should see add site button', async ({ superAdminPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    await expect(sitesPage.addSiteButton).toBeVisible();
  });

  test('should open create site modal', async ({ superAdminPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    await sitesPage.addSiteButton.click();
    const dialog = page.locator('mat-dialog-container');
    await expect(dialog).toBeVisible({ timeout: 5000 });
    await page.keyboard.press('Escape');
  });

  test('should show validation errors on empty submit', async ({ superAdminPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    await sitesPage.addSiteButton.click();
    const dialog = page.locator('mat-dialog-container');
    await expect(dialog).toBeVisible({ timeout: 5000 });

    // Touch required fields to trigger validation (mat-error needs touched + invalid)
    const nameInput = dialog.locator('input[formControlName="nom_site"], input[formcontrolname="nom_site"]').first();
    if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await nameInput.click();
      await nameInput.blur();
    }

    // Try to submit empty form
    const submitBtn = dialog.locator('button').filter({ hasText: /créer|enregistrer|valider/i });
    if (await submitBtn.isVisible()) {
      await submitBtn.click();
      await page.waitForTimeout(500);
      // Should show validation errors (mat-error) or submit button disabled
      const errors = dialog.locator('mat-error, .app-form-field__error, .form-error-msg');
      const errorCount = await errors.count();
      const isDisabled = await submitBtn.isDisabled().catch(() => false);
      expect(errorCount > 0 || isDisabled).toBeTruthy();
    }

    await page.keyboard.press('Escape');
  });

  // #716 : la création d'un site est ouverte à tous les rôles qui accèdent à la page
  test('admin organisme should see add site button (#716)', async ({ adminRnfPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    await expect(sitesPage.addSiteButton).toBeVisible();
    await sitesPage.addSiteButton.click();
    await expect(page.locator('mat-dialog-container')).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('referent should see add site button (#716)', async ({ referentPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    await expect(sitesPage.addSiteButton).toBeVisible();
  });

  test('referent should see their assigned sites', async ({ referentPage: page }) => {
    const sitesPage = new AdminSitesPage(page);
    await sitesPage.goto();
    await sitesPage.waitForData();

    const rowCount = await sitesPage.getRowCount();
    expect(rowCount).toBeGreaterThan(0);
  });
});
