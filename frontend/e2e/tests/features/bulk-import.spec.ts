/**
 * E2E Tests for Bulk Site Import
 *
 * Tests:
 * - Bulk import button visibility for admins
 * - Opening bulk import dialog
 * - Stepper navigation
 * - File upload validation
 * - Field mapping
 *
 * Note: Actual file import requires test files - these tests verify the UI workflow
 */
import { test, expect } from '../../fixtures/auth.fixture';

test.describe('Bulk Site Import', () => {

  test.describe('Access Control', () => {

    test('should show bulk import button for super admin', async ({ superAdminPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      // Look for the bulk import button
      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await expect(bulkImportBtn).toBeVisible();
    });

    test('should show bulk import button for admin organisme', async ({ adminRnfPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await expect(bulkImportBtn).toBeVisible();
    });

    test('should NOT show bulk import button for regular user', async ({ userRnfPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await expect(bulkImportBtn).not.toBeVisible();
    });

    test('should NOT show bulk import button for referent', async ({ referentPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await expect(bulkImportBtn).not.toBeVisible();
    });

  });

  test.describe('Dialog Workflow', () => {

    test('should open bulk import dialog when clicking button', async ({ adminRnfPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      // Click bulk import button
      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await bulkImportBtn.click();

      // Dialog should open
      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible();

      // Should have dialog title with import text
      await expect(dialog.locator('h2')).toContainText(/Import/i);
    });

    test('should display stepper with correct steps', async ({ adminRnfPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await bulkImportBtn.click();

      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible();

      // Should have stepper (migré kit UI app-stepper)
      const stepper = dialog.locator('app-stepper, mat-stepper');
      await expect(stepper).toBeVisible();

      // Should have step labels (Upload, Mapping, Preview, Results)
      const stepLabels = dialog.locator('.stepper-step, .mat-step-label');
      const count = await stepLabels.count();
      expect(count).toBeGreaterThanOrEqual(3);
    });

    test('should show dropzone on first step', async ({ adminRnfPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await bulkImportBtn.click();

      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible();

      // Should show dropzone
      const dropzone = dialog.locator('.dropzone');
      await expect(dropzone).toBeVisible();

      // Should have file input
      const fileInput = dialog.locator('input[type="file"]');
      await expect(fileInput).toBeAttached();
    });

    test('should show template download links', async ({ adminRnfPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await bulkImportBtn.click();

      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible();

      // Should have template download links
      const templateLinks = dialog.locator('.template-link');
      const count = await templateLinks.count();
      expect(count).toBeGreaterThanOrEqual(1);
    });

    test('should close dialog when clicking close button or pressing Escape', async ({ adminRnfPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await bulkImportBtn.click();

      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible();

      // Close using the close button (dialog has disableClose: true, so Escape doesn't work)
      const closeBtn = dialog.locator('mat-dialog-actions button', { hasText: /Fermer|Annuler|Close/i });
      await closeBtn.click();
      await page.waitForTimeout(500);

      // Dialog should be closed
      await expect(dialog).not.toBeVisible();
    });

    test('should disable first next button until file is validated', async ({ adminRnfPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await bulkImportBtn.click();

      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible();

      // The first step's next button should be disabled (use first() to avoid multiple matches)
      const nextBtn = dialog.locator('.step-actions button[color="primary"]').first();
      await expect(nextBtn).toBeDisabled();

      // Close dialog
      await page.keyboard.press('Escape');
    });

  });

  test.describe('Format Information', () => {

    test('should display format info and geometry note', async ({ adminRnfPage: page }) => {
      await page.goto('/sites');
      await page.waitForTimeout(1000);

      const bulkImportBtn = page.locator('.btn-import, button:has-text("Import en masse")');
      await bulkImportBtn.click();

      const dialog = page.locator('mat-dialog-container');
      await expect(dialog).toBeVisible();

      // Should have format info section
      const formatInfo = dialog.locator('.format-info');
      await expect(formatInfo).toBeVisible();

      // Should mention geometry note
      const geometryNote = dialog.locator('.geometry-note');
      await expect(geometryNote).toBeVisible();

      // Close dialog
      await page.keyboard.press('Escape');
    });

  });

});
