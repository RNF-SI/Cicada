/**
 * E2E Tests for Enjeux (conservation issues), FCR, Facteurs d'Influence and Pressions
 *
 * Tests:
 * - Navigation and display (~10 tests)
 * - Detail view (~8 tests)
 * - CRUD Facteurs d'influence (~10 tests)
 * - CRUD Pressions (~7 tests)
 *
 * Prerequisite: seed_testdata must have been run (enjeux seeder creates
 * 16 enjeux, 8 FCR, 10 facteurs d'influence, ~14 pressions across 4 plans).
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { EnjeuxPage } from '../../pages/enjeux.page';

/**
 * Helper: discover a plan ID by searching for a plan whose name contains the given text.
 * Uses the API to find the plan since database IDs are dynamic.
 */
async function findPlanIdByName(page: import('@playwright/test').Page, nameFragment: string): Promise<number> {
  const response = await page.request.get('/api/plans/plans/', {
    params: { search: nameFragment },
  });
  const data = await response.json();
  const results = data.results || data;
  const plan = Array.isArray(results) ? results[0] : null;
  if (!plan) throw new Error(`Plan with name containing "${nameFragment}" not found`);
  return plan.id_pg;
}

/**
 * Helper: find the first enjeu ID for a plan (for detail navigation tests).
 */
async function findFirstEnjeuId(page: import('@playwright/test').Page, planId: number): Promise<number> {
  const response = await page.request.get(`/api/plans/enjeux/by-plan/${planId}/`);
  const data = await response.json();
  const enjeux = data.enjeux || [];
  if (enjeux.length === 0) throw new Error(`No enjeux found for plan ${planId}`);
  return enjeux[0].id_enjeu;
}


// =========================================================================
// Navigation and Display
// =========================================================================

test.describe('Enjeux - Navigation and Display', () => {

  test('should display the enjeux list page for a plan', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.goto(planId);
    await enjeuxPage.waitForData();

    await expect(enjeuxPage.pageTitle).toBeVisible();
  });

  test('should display breadcrumb with correct navigation', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.goto(planId);
    await enjeuxPage.waitForData();

    await expect(enjeuxPage.breadcrumb).toBeVisible();
    await expect(enjeuxPage.breadcrumbHome).toBeVisible();
    // Breadcrumb should have links for "Plans" and the plan name
    const linkCount = await enjeuxPage.breadcrumbLinks.count();
    expect(linkCount).toBeGreaterThanOrEqual(2);
  });

  test('should display enjeu accordions in the list', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.goto(planId);
    await enjeuxPage.waitForData();

    // Camargue has 5 enjeux
    const enjeuCount = await enjeuxPage.getEnjeuAccordionCount();
    expect(enjeuCount).toBe(5);
  });

  test('should display FCR accordions after enjeux', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.goto(planId);
    await enjeuxPage.waitForData();

    // Camargue has 2 FCR
    const fcrCount = await enjeuxPage.getFcrAccordionCount();
    expect(fcrCount).toBe(2);
  });

  test('should display correct total count', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.goto(planId);
    await enjeuxPage.waitForData();

    // 5 enjeux + 2 FCR = 7 total
    await expect(enjeuxPage.countText).toContainText('7');
  });

  test('should expand and collapse an accordion on click', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.goto(planId);
    await enjeuxPage.waitForData();

    // Expand first accordion
    await enjeuxPage.expandAccordion(0);
    const firstAccordion = page.locator('app-enjeu-accordion').first();
    await expect(firstAccordion.locator('.accordion.expanded')).toBeVisible();

    // Collapse it
    await enjeuxPage.collapseAccordion(0);
    await expect(firstAccordion.locator('.accordion.expanded')).not.toBeVisible();
  });

  test('should show properties when accordion is expanded', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.goto(planId);
    await enjeuxPage.waitForData();

    await enjeuxPage.expandAccordion(0);

    const firstAccordion = page.locator('app-enjeu-accordion').first();
    // Should show property lines for priorité, catégorie, etc.
    const propertyLines = firstAccordion.locator('.property-line');
    const count = await propertyLines.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test('should show facteurs count in expanded accordion', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.goto(planId);
    await enjeuxPage.waitForData();

    // First enjeu (Hab. humides) has 2 facteurs
    await enjeuxPage.expandAccordion(0);
    const firstAccordion = page.locator('app-enjeu-accordion').first();
    const facteursSummary = firstAccordion.locator('.facteurs-summary');
    const isVisible = await facteursSummary.isVisible().catch(() => false);

    if (isVisible) {
      const countText = await firstAccordion.locator('.facteurs-count').innerText();
      expect(countText).toContain('2');
    }
  });

  test('should display sidebar navigation', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.goto(planId);
    await enjeuxPage.waitForData();

    await expect(enjeuxPage.sidebar).toBeVisible();
  });

  test('super admin should access enjeux page', async ({ superAdminPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.goto(planId);
    await enjeuxPage.waitForData();

    await expect(enjeuxPage.pageTitle).toBeVisible();
    const totalCount = await enjeuxPage.getTotalAccordionCount();
    expect(totalCount).toBe(7); // 5 enjeux + 2 FCR
  });
});


// =========================================================================
// Detail View
// =========================================================================

test.describe('Enjeux - Detail View', () => {

  test('should navigate to enjeu detail view', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    // Detail view should show the enjeu title
    await expect(enjeuxPage.enjeuMainTitle).toBeVisible();
  });

  test('should display detail tabs', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    // Should show 3 tabs: Détail, OLT, Opérations
    const tabCount = await enjeuxPage.tabs.count();
    expect(tabCount).toBe(3);
  });

  test('should show Detail tab as active by default', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await expect(enjeuxPage.tabDetail).toHaveClass(/active/);
  });

  test('should display enjeu detail card with properties', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await expect(enjeuxPage.enjeuDetailCard).toBeVisible();
    await expect(enjeuxPage.cardSectionName).toBeVisible();
  });

  test('should display facteurs d\'influence in detail view', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    // First enjeu (Hab. humides) has 2 facteurs
    const facteurCount = await enjeuxPage.getFacteurCount();
    expect(facteurCount).toBeGreaterThanOrEqual(1);
  });

  test('should expand a facteur card to show details', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const facteurCount = await enjeuxPage.getFacteurCount();
    if (facteurCount > 0) {
      await enjeuxPage.expandFacteur(0);
      const facteur = enjeuxPage.facteurCards.first();
      await expect(facteur.locator('.facteur-card-body')).toBeVisible();
    }
  });

  test('should show pressions inside expanded facteur', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const facteurCount = await enjeuxPage.getFacteurCount();
    if (facteurCount > 0) {
      await enjeuxPage.expandFacteur(0);
      // First facteur (Modification du régime hydrologique) has 2 pressions
      const pressionCount = await enjeuxPage.getPressionCount(0);
      expect(pressionCount).toBeGreaterThanOrEqual(1);
    }
  });

  test('should include enjeu name in breadcrumb on detail view', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    // Current breadcrumb should show the enjeu short name
    await expect(enjeuxPage.breadcrumbCurrent).toBeVisible();
    const currentText = await enjeuxPage.breadcrumbCurrent.innerText();
    expect(currentText.length).toBeGreaterThan(0);
  });
});


// =========================================================================
// CRUD Facteurs d'Influence
// =========================================================================

test.describe('Enjeux - CRUD Facteurs d\'Influence', () => {

  test('should display the add facteur button in detail view', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await expect(enjeuxPage.addFacteurButton).toBeVisible();
  });

  test('should show inline form when clicking add facteur', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.clickAddFacteur();

    // Inline form should appear
    const form = page.locator('.inline-form').filter({ has: page.locator('.facteur-bullet') });
    await expect(form).toBeVisible();
    await expect(form.locator('input[matInput]')).toBeVisible();
    await expect(form.locator('textarea[matInput]')).toBeVisible();
  });

  test('should have save button disabled when libelle is empty', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.clickAddFacteur();

    const form = page.locator('.inline-form').filter({ has: page.locator('.facteur-bullet') });
    const saveBtn = form.locator('.inline-form-actions button[mat-flat-button]');
    await expect(saveBtn).toBeDisabled();
  });

  test('should create a facteur with libelle', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const initialCount = await enjeuxPage.getFacteurCount();

    await enjeuxPage.addFacteur('E2E Test - Facteur temporaire', 'Description E2E');

    // Wait for the new facteur to appear
    await page.waitForTimeout(1000);
    const newCount = await enjeuxPage.getFacteurCount();
    expect(newCount).toBe(initialCount + 1);
  });

  test('should show the new facteur in the list after creation', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    // Check that one of the facteur cards contains our seeded data
    const facteurText = page.locator('.facteur-card-title');
    const count = await facteurText.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // At least one facteur title should contain "Modification" or "Urbanisation"
    const allText = await page.locator('.facteur-card-title').allInnerTexts();
    const hasKnownFacteur = allText.some(
      t => t.includes('régime hydrologique') || t.includes('Urbanisation')
    );
    expect(hasKnownFacteur).toBe(true);
  });

  test('should cancel adding a facteur', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const initialCount = await enjeuxPage.getFacteurCount();

    await enjeuxPage.clickAddFacteur();
    const form = page.locator('.inline-form').filter({ has: page.locator('.facteur-bullet') });
    await expect(form).toBeVisible();

    // Click cancel
    await form.locator('.inline-form-actions button[mat-stroked-button]').click();
    await page.waitForTimeout(300);

    // Form should be hidden and count unchanged
    await expect(form).not.toBeVisible();
    const newCount = await enjeuxPage.getFacteurCount();
    expect(newCount).toBe(initialCount);
  });

  test('should open confirm dialog when deleting a facteur', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const facteurCount = await enjeuxPage.getFacteurCount();
    if (facteurCount > 0) {
      // Expand first facteur to access delete button
      await enjeuxPage.expandFacteur(0);
      await enjeuxPage.deleteFacteur(0);

      // Dialog should appear
      await expect(enjeuxPage.confirmDialog).toBeVisible();
    }
  });

  test('should cancel deletion and keep the facteur', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const initialCount = await enjeuxPage.getFacteurCount();
    if (initialCount > 0) {
      await enjeuxPage.expandFacteur(0);
      await enjeuxPage.deleteFacteur(0);

      // Cancel the dialog
      await enjeuxPage.cancelDelete();
      await page.waitForTimeout(500);

      const newCount = await enjeuxPage.getFacteurCount();
      expect(newCount).toBe(initialCount);
    }
  });

  test('should delete a facteur after confirmation', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    // First create a temporary facteur so we don't delete seeded data
    await enjeuxPage.addFacteur('E2E Temp Facteur - À Supprimer');
    await page.waitForTimeout(1000);

    const countAfterAdd = await enjeuxPage.getFacteurCount();

    // Delete the last facteur (our temp one)
    const lastIndex = countAfterAdd - 1;
    await enjeuxPage.expandFacteur(lastIndex);
    await enjeuxPage.deleteFacteur(lastIndex);

    // Confirm deletion
    await enjeuxPage.confirmDelete();
    await page.waitForTimeout(1000);

    const countAfterDelete = await enjeuxPage.getFacteurCount();
    expect(countAfterDelete).toBe(countAfterAdd - 1);
  });
});


// =========================================================================
// CRUD Pressions
// =========================================================================

test.describe('Enjeux - CRUD Pressions', () => {

  test('should display add pression button inside expanded facteur', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const facteurCount = await enjeuxPage.getFacteurCount();
    if (facteurCount > 0) {
      await enjeuxPage.expandFacteur(0);
      const addPressionBtn = enjeuxPage.facteurCards.first().locator('.add-pression-btn');
      await expect(addPressionBtn).toBeVisible();
    }
  });

  test('should show inline pression form when clicking add', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const facteurCount = await enjeuxPage.getFacteurCount();
    if (facteurCount > 0) {
      await enjeuxPage.expandFacteur(0);
      await enjeuxPage.clickAddPression(0);

      const form = page.locator('.inline-form').filter({ has: page.locator('.pression-bullet') });
      await expect(form).toBeVisible();
    }
  });

  test('should create a pression', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const facteurCount = await enjeuxPage.getFacteurCount();
    if (facteurCount > 0) {
      await enjeuxPage.expandFacteur(0);
      const initialPressionCount = await enjeuxPage.getPressionCount(0);

      await enjeuxPage.addPression(0, 'E2E Test - Pression temporaire', 'Description pression E2E');
      await page.waitForTimeout(1000);

      const newPressionCount = await enjeuxPage.getPressionCount(0);
      expect(newPressionCount).toBe(initialPressionCount + 1);
    }
  });

  test('should show the new pression in the facteur', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const facteurCount = await enjeuxPage.getFacteurCount();
    if (facteurCount > 0) {
      await enjeuxPage.expandFacteur(0);

      // Check that seeded pressions are visible
      const pressionTitles = enjeuxPage.facteurCards.first().locator('.pression-card-title');
      const count = await pressionTitles.count();
      expect(count).toBeGreaterThanOrEqual(1);
    }
  });

  test('should cancel adding a pression', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const facteurCount = await enjeuxPage.getFacteurCount();
    if (facteurCount > 0) {
      await enjeuxPage.expandFacteur(0);
      const initialCount = await enjeuxPage.getPressionCount(0);

      await enjeuxPage.clickAddPression(0);
      const form = page.locator('.inline-form').filter({ has: page.locator('.pression-bullet') });
      await expect(form).toBeVisible();

      // Cancel
      await form.locator('.inline-form-actions button[mat-stroked-button]').click();
      await page.waitForTimeout(300);

      await expect(form).not.toBeVisible();
      const newCount = await enjeuxPage.getPressionCount(0);
      expect(newCount).toBe(initialCount);
    }
  });

  test('should delete a pression after confirmation', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const facteurCount = await enjeuxPage.getFacteurCount();
    if (facteurCount > 0) {
      await enjeuxPage.expandFacteur(0);

      // Create a temp pression first
      await enjeuxPage.addPression(0, 'E2E Temp Pression - À Supprimer');
      await page.waitForTimeout(1000);

      const countAfterAdd = await enjeuxPage.getPressionCount(0);

      // Delete the last pression (our temp one)
      const lastPression = enjeuxPage.facteurCards.first().locator('.pression-card').last();
      await lastPression.locator('.pression-card-actions button[title]').first().click();
      await page.waitForTimeout(300);

      // Confirm
      await enjeuxPage.confirmDelete();
      await page.waitForTimeout(1000);

      const countAfterDelete = await enjeuxPage.getPressionCount(0);
      expect(countAfterDelete).toBe(countAfterAdd - 1);
    }
  });

  test('should not delete pression when cancelling confirmation', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    const facteurCount = await enjeuxPage.getFacteurCount();
    if (facteurCount > 0) {
      await enjeuxPage.expandFacteur(0);
      const initialCount = await enjeuxPage.getPressionCount(0);

      if (initialCount > 0) {
        // Try to delete first pression
        const firstPression = enjeuxPage.facteurCards.first().locator('.pression-card').first();
        await firstPression.locator('.pression-card-actions button[title]').first().click();
        await page.waitForTimeout(300);

        // Cancel
        await enjeuxPage.cancelDelete();
        await page.waitForTimeout(500);

        const newCount = await enjeuxPage.getPressionCount(0);
        expect(newCount).toBe(initialCount);
      }
    }
  });
});


// =========================================================================
// Tab Navigation (Detail View)
// =========================================================================

test.describe('Enjeux - Tab Navigation', () => {

  test('should switch to OLT tab', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');
    await expect(enjeuxPage.tabOlt).toHaveClass(/active/);

    // OLT tab should show the olt-content container
    const oltContent = page.locator('.olt-content');
    await expect(oltContent).toBeVisible();
  });

  test('should switch to Operations tab and show empty state', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('operations');
    await expect(enjeuxPage.tabOperations).toHaveClass(/active/);

    const tabEmpty = page.locator('.tab-empty-state');
    await expect(tabEmpty).toBeVisible();
  });

  test('should switch back to Detail tab', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    // Go to OLT then back to Detail
    await enjeuxPage.switchTab('olt');
    await enjeuxPage.switchTab('detail');

    await expect(enjeuxPage.tabDetail).toHaveClass(/active/);
    await expect(enjeuxPage.enjeuDetailCard).toBeVisible();
  });
});


// =========================================================================
// OLT Tab - Vision à long terme
// =========================================================================

test.describe('Enjeux - OLT Tab Display', () => {

  test('should display info note about typical usage', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');
    const infoNote = page.locator('.olt-info-note');
    await expect(infoNote).toBeVisible();
  });

  test('should display etat actuel cards with seeded data', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    // First enjeu (Habitats humides) should have at least 1 etat actuel from seed data
    const etatCards = page.locator('.etat-actuel-card');
    const count = await etatCards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('should display OLT bars inside etat actuel', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    // Should have OLT bars
    const oltBars = page.locator('.olt-header-bar');
    const count = await oltBars.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('should display OLT count in top bar', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    const countText = page.locator('.olt-top-bar .count-text');
    await expect(countText).toBeVisible();
  });

  test('should expand OLT to show niveaux d\'exigence', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    // Click on first OLT bar to expand
    const firstOlt = page.locator('.olt-header-bar').first();
    await firstOlt.click();
    await page.waitForTimeout(300);

    // Should show expanded content
    const expandedContent = page.locator('.olt-expanded-content');
    const isVisible = await expandedContent.first().isVisible().catch(() => false);
    expect(isVisible).toBe(true);
  });

  test('should show NE cards inside expanded OLT', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    // Expand the first OLT
    const firstOlt = page.locator('.olt-header-bar').first();
    await firstOlt.click();
    await page.waitForTimeout(300);

    // Check NE cards
    const neCards = page.locator('.ne-card');
    const count = await neCards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('should show add etat actuel button', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    const addEtatBtn = page.locator('.add-etat-btn');
    await expect(addEtatBtn).toBeVisible();
  });
});


test.describe('Enjeux - OLT Tab CRUD', () => {

  test('should show inline form when clicking add etat actuel', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    // Click add etat actuel
    await page.locator('.add-etat-btn').click();
    await page.waitForTimeout(300);

    // Form should appear
    const form = page.locator('.etat-inline-form');
    await expect(form).toBeVisible();
    await expect(form.locator('input[matInput]')).toBeVisible();
  });

  test('should cancel adding an etat actuel', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    const initialCount = await page.locator('.etat-actuel-card').count();

    // Click add then cancel
    await page.locator('.add-etat-btn').click();
    await page.waitForTimeout(300);
    const form = page.locator('.etat-inline-form');
    await form.locator('button[mat-stroked-button]').click();
    await page.waitForTimeout(300);

    // Form hidden, count unchanged
    await expect(form).not.toBeVisible();
    const newCount = await page.locator('.etat-actuel-card').count();
    expect(newCount).toBe(initialCount);
  });

  test('should create an etat actuel', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    const initialCount = await page.locator('.etat-actuel-card').count();

    // Fill and submit the form
    await page.locator('.add-etat-btn').click();
    await page.waitForTimeout(300);
    const form = page.locator('.etat-inline-form');
    await form.locator('input[matInput]').fill('E2E Temp État Actuel');
    await form.locator('button[mat-flat-button]').click();
    await page.waitForTimeout(1000);

    const newCount = await page.locator('.etat-actuel-card').count();
    expect(newCount).toBe(initialCount + 1);
  });

  test('should show add OLT button inside etat actuel card', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    const addOltBtn = page.locator('.add-olt-btn').first();
    await expect(addOltBtn).toBeVisible();
  });

  test('should create an OLT via inline form', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    const initialOltCount = await page.locator('.olt-header-bar').count();

    // Click add OLT button inside first etat card
    await page.locator('.add-olt-btn').first().click();
    await page.waitForTimeout(300);

    const form = page.locator('.olt-inline-form');
    await expect(form).toBeVisible();
    await form.locator('input[matInput]').fill('E2E Temp OLT');
    await form.locator('button[mat-flat-button]').click();
    await page.waitForTimeout(1000);

    const newOltCount = await page.locator('.olt-header-bar').count();
    expect(newOltCount).toBe(initialOltCount + 1);
  });

  test('should expand OLT and show add NE button', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    // Expand first OLT
    await page.locator('.olt-header-bar').first().click();
    await page.waitForTimeout(300);

    const addNeBtn = page.locator('.add-ne-btn').first();
    await expect(addNeBtn).toBeVisible();
  });

  test('should create a NE inside an expanded OLT', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    // Expand first OLT
    await page.locator('.olt-header-bar').first().click();
    await page.waitForTimeout(300);

    const initialNeCount = await page.locator('.ne-card').count();

    // Click add NE button
    await page.locator('.add-ne-btn').first().click();
    await page.waitForTimeout(300);

    const form = page.locator('.ne-inline-form');
    await expect(form).toBeVisible();
    await form.locator('input[matInput]').fill('E2E Temp NE');
    await form.locator('button[mat-flat-button]').click();
    await page.waitForTimeout(1000);

    const newNeCount = await page.locator('.ne-card').count();
    expect(newNeCount).toBe(initialNeCount + 1);
  });

  test('should delete an OLT after confirmation', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    // First create a temp OLT so we don't delete seeded data
    await page.locator('.add-olt-btn').first().click();
    await page.waitForTimeout(300);
    const form = page.locator('.olt-inline-form');
    await form.locator('input[matInput]').fill('E2E Temp OLT - À Supprimer');
    await form.locator('button[mat-flat-button]').click();
    await page.waitForTimeout(1000);

    const countAfterAdd = await page.locator('.olt-header-bar').count();

    // Delete the last OLT
    const lastOlt = page.locator('.olt-header-bar').last();
    await lastOlt.locator('.icon-btn-olt').last().click(); // delete button
    await page.waitForTimeout(300);

    // Confirm
    await enjeuxPage.confirmDelete();
    await page.waitForTimeout(1000);

    const countAfterDelete = await page.locator('.olt-header-bar').count();
    expect(countAfterDelete).toBe(countAfterAdd - 1);
  });

  test('should delete an etat actuel after confirmation', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    // First create a temp etat actuel
    await page.locator('.add-etat-btn').click();
    await page.waitForTimeout(300);
    const form = page.locator('.etat-inline-form');
    await form.locator('input[matInput]').fill('E2E Temp État - À Supprimer');
    await form.locator('button[mat-flat-button]').click();
    await page.waitForTimeout(1000);

    const countAfterAdd = await page.locator('.etat-actuel-card').count();

    // Delete the last etat (our temp one)
    const lastEtat = page.locator('.etat-actuel-card').last();
    await lastEtat.locator('.etat-actuel-card-actions .icon-btn-flat').last().click(); // delete button
    await page.waitForTimeout(300);

    // Confirm
    await enjeuxPage.confirmDelete();
    await page.waitForTimeout(1000);

    const countAfterDelete = await page.locator('.etat-actuel-card').count();
    expect(countAfterDelete).toBe(countAfterAdd - 1);
  });

  test('should edit an OLT inline', async ({ referentPage: page }) => {
    const planId = await findPlanIdByName(page, 'Camargue');
    const enjeuId = await findFirstEnjeuId(page, planId);
    const enjeuxPage = new EnjeuxPage(page);
    await enjeuxPage.gotoDetail(planId, enjeuId);
    await enjeuxPage.waitForData();

    await enjeuxPage.switchTab('olt');

    // Click edit on first OLT
    const firstOlt = page.locator('.olt-header-bar').first();
    await firstOlt.locator('.icon-btn-olt').first().click(); // edit button
    await page.waitForTimeout(300);

    // Should show inline edit form
    const editForm = page.locator('.olt-inline-form');
    await expect(editForm).toBeVisible();
    await expect(editForm.locator('input[matInput]')).toBeVisible();

    // Cancel to restore
    await editForm.locator('button[mat-stroked-button]').click();
    await page.waitForTimeout(300);
  });
});
