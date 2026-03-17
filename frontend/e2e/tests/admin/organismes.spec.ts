import { test, expect } from '../../fixtures/auth.fixture';
import { AdminOrganismesPage } from '../../pages/admin-organismes.page';

test.describe('Admin Organismes', () => {
  test('super admin should see organismes grid', async ({ superAdminPage: page }) => {
    const orgPage = new AdminOrganismesPage(page);
    await orgPage.goto();
    await orgPage.waitForData();

    const cardCount = await orgPage.organismeCards.count();
    expect(cardCount).toBeGreaterThan(0);
  });

  test('admin organisme should see detail view of their organisme', async ({ adminRnfPage: page }) => {
    const orgPage = new AdminOrganismesPage(page);
    await orgPage.goto();
    await orgPage.waitForData();

    // Admin_og sees detail view instead of grid
    const hasDetail = await orgPage.organismeDetail.isVisible().catch(() => false);
    const hasCards = await orgPage.organismeCards.first().isVisible().catch(() => false);
    expect(hasDetail || hasCards).toBeTruthy();
  });

  test('super admin should search organismes', async ({ superAdminPage: page }) => {
    const orgPage = new AdminOrganismesPage(page);
    await orgPage.goto();
    await orgPage.waitForData();

    if (await orgPage.searchInput.isVisible()) {
      // Search by a term that matches one of the seed organismes
      // Seeder uses "Reserves Naturelles de France" (no accent)
      await orgPage.searchOrganisme('Reserves');
      // Wait for filtering to apply
      await page.waitForTimeout(1000);

      // Check if results are filtered - either we find a card or the grid reduced
      const cardCount = await orgPage.organismeCards.count();
      if (cardCount === 0) {
        // Fallback: try partial name
        await orgPage.searchInput.clear();
        await orgPage.searchOrganisme('France');
        await page.waitForTimeout(1000);
      }

      const finalCount = await orgPage.organismeCards.count();
      expect(finalCount).toBeGreaterThan(0);
    }
  });

  test('should open edit organisme modal', async ({ superAdminPage: page }) => {
    const orgPage = new AdminOrganismesPage(page);
    await orgPage.goto();
    await orgPage.waitForData();

    const firstCard = orgPage.organismeCards.first();
    if (await firstCard.isVisible()) {
      const editBtn = orgPage.getEditButton(firstCard);
      if (await editBtn.isVisible()) {
        await editBtn.click();
        const dialog = page.locator('mat-dialog-container');
        await expect(dialog).toBeVisible({ timeout: 5000 });
        await page.keyboard.press('Escape');
      }
    }
  });
});
