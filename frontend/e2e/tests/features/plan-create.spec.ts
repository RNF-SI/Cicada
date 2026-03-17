/**
 * E2E Tests for the Plan de Gestion create page (/plans/nouveau)
 *
 * 8 groups, ~30 tests covering:
 * - Form display & default values
 * - Required field validation
 * - Site selection & search
 * - Optional & hybrid fields (rédacteurs, relecteurs, organisme)
 * - Plan creation with data verification (serial)
 * - Permissions & role-based site visibility
 * - Navigation
 * - Year validation
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { PlanCreatePage } from '../../pages/plan-create.page';
import { PlansListPage } from '../../pages/plans-list.page';
import { ApiHelper } from '../../helpers/api.helper';

// ─── Group 1: Form Display & Default Values ─────────────────────────────────

test.describe('Plan Create - Form Display', () => {

  test('should display all required and optional fields', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    // Required fields
    await expect(createPage.nomInput).toBeVisible();
    await expect(createPage.rangInput).toBeVisible();
    await expect(createPage.anneeDebutInput).toBeVisible();
    await expect(createPage.anneeFinInput).toBeVisible();
    await expect(createPage.ct88RadioGroup).toBeVisible();
    await expect(createPage.sitesSection).toBeVisible();

    // Optional fields
    await expect(createPage.surfaceInput).toBeVisible();
    await expect(createPage.dateValidationCspnInput).toBeVisible();
    await expect(createPage.docGestionInput).toBeVisible();
    await expect(createPage.redacteurTypeSelect).toBeVisible();
    await expect(createPage.organismeSection).toBeVisible();
    await expect(createPage.redacteursInput).toBeVisible();
    await expect(createPage.relecteursInput).toBeVisible();

    // Buttons
    await expect(createPage.submitButton).toBeVisible();
    await expect(createPage.cancelButton).toBeVisible();
  });

  test('should have correct default values', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    const currentYear = new Date().getFullYear();

    await expect(createPage.rangInput).toHaveValue('1');
    await expect(createPage.anneeDebutInput).toHaveValue(String(currentYear));
    await expect(createPage.anneeFinInput).toHaveValue(String(currentYear + 5));
    expect(await createPage.getSiteCountBadgeText()).toBe('0');
  });

  test('should display breadcrumb with correct links', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await expect(createPage.breadcrumb).toBeVisible();
    await expect(createPage.breadcrumbPlansLink).toBeVisible();
    await expect(createPage.breadcrumbCurrent).toBeVisible();
    await expect(createPage.breadcrumbCurrent).toContainText('Saisie des informations');
  });
});

// ─── Group 2: Required Field Validation ──────────────────────────────────────

test.describe('Plan Create - Validation Required', () => {

  test('should show mat-error for empty name', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.nomInput.fill('');
    await createPage.submit();

    const nameError = page.locator('mat-error').filter({ hasText: 'nom est requis' });
    await expect(nameError).toBeVisible();
  });

  test('should show mat-error for empty rang', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.rangInput.fill('');
    await createPage.submit();

    const rangError = page.locator('mat-error').filter({ hasText: /rang/i });
    await expect(rangError).toBeVisible();
  });

  test('should show error banner when no site selected', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    // Fill all required fields except sites
    await createPage.fillForm({
      nom: `Plan No Site ${Date.now()}`,
      rang: 1,
      ct88: false,
    });

    await createPage.submit();

    await expect(createPage.errorBanner).toBeVisible();
    const bannerText = await createPage.getErrorBannerText();
    expect(bannerText).toContain('au moins un site');
  });

  test('should show error for rang below 1', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.rangInput.fill('0');
    await createPage.submit();

    const minError = page.locator('mat-error').filter({ hasText: /minimum 1/i });
    await expect(minError).toBeVisible();
  });
});

// ─── Group 3: Site Selection ─────────────────────────────────────────────────

test.describe('Plan Create - Site Selection', () => {

  test('should display all sites for super admin', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    const siteCount = await createPage.siteItems.count();
    expect(siteCount).toBeGreaterThanOrEqual(7);

    await expect(createPage.siteItems.filter({ hasText: 'Camargue' })).toBeVisible();
    await expect(createPage.siteItems.filter({ hasText: 'Vercors' })).toBeVisible();
  });

  test('should update badge on select/deselect', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    expect(await createPage.getSiteCountBadgeText()).toBe('0');

    // Select
    await createPage.selectSiteByName('Camargue');
    expect(await createPage.getSiteCountBadgeText()).toBe('1');

    // Deselect
    await createPage.deselectSiteByName('Camargue');
    expect(await createPage.getSiteCountBadgeText()).toBe('0');
  });

  test('should support multiple site selection with counter', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.selectSiteByName('Camargue');
    await createPage.selectSiteByName('Vercors');
    await createPage.selectSiteByName('Scandola');

    expect(await createPage.getSiteCountBadgeText()).toBe('3');
  });

  test('should filter sites by search and restore all', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    const initialCount = await createPage.siteItems.count();

    await createPage.siteSearchInput.fill('Camargue');
    await expect(createPage.siteItems.filter({ hasText: 'Camargue' })).toBeVisible();
    const filteredCount = await createPage.siteItems.count();
    expect(filteredCount).toBeLessThan(initialCount);

    // Clear search — all sites return
    await createPage.siteSearchInput.fill('');
    await expect(createPage.siteItems).toHaveCount(initialCount);
  });

  test('should show no-items message for unmatched search', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.siteSearchInput.fill('ZZZNONEXISTENT');
    await expect(createPage.noSiteMessage).toBeVisible();
  });
});

// ─── Group 4: Optional & Hybrid Fields ───────────────────────────────────────

test.describe('Plan Create - Optional and Hybrid Fields', () => {

  test('should fill surface field', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.surfaceInput.fill('150.5');
    await expect(createPage.surfaceInput).toHaveValue('150.5');
  });

  test('should select a redacteur type', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.redacteurTypeSelect.click();
    // Wait for options to appear, pick first non-null option
    const options = page.locator('mat-option');
    await options.first().waitFor({ state: 'visible', timeout: 5000 });
    const optionCount = await options.count();
    // Skip first option which is "Aucun"
    if (optionCount > 1) {
      await options.nth(1).click();
    } else {
      await options.first().click();
    }

    // Verify the select is no longer showing the placeholder
    const selectedText = await createPage.redacteurTypeSelect.textContent();
    expect(selectedText?.trim()).not.toBe('');
  });

  test('should add a free text redacteur and display chip', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.addRedacteurFreeText('Consultant Externe');
    await expect(createPage.redacteursChips.first()).toBeVisible();
    const chips = await createPage.getChipTexts(createPage.redacteursChips);
    expect(chips.some(t => t.includes('Consultant Externe'))).toBe(true);
  });

  test('should remove a redacteur chip', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.addRedacteurFreeText('A Supprimer');
    await expect(createPage.redacteursChips.first()).toBeVisible();

    await createPage.removeChip(createPage.redacteursChips.first());
    await expect(createPage.redacteursChips).toHaveCount(0);
  });

  test('should add a free text relecteur and display chip', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.addRelecteurFreeText('Relecteur Test');
    await expect(createPage.relecteursChips.first()).toBeVisible();
    const chips = await createPage.getChipTexts(createPage.relecteursChips);
    expect(chips.some(t => t.includes('Relecteur Test'))).toBe(true);
  });

  test('should set and clear organisme free text', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.setOrganismeFreeText('Mon Organisme Custom');
    await expect(createPage.organismeChip).toBeVisible();
    const chipText = await createPage.organismeChip.textContent();
    expect(chipText).toContain('Mon Organisme Custom');

    // Remove it
    await createPage.clearOrganisme();
    await expect(createPage.organismeChip).not.toBeVisible();
    // Input should reappear
    await expect(createPage.organismeInput).toBeVisible();
  });
});

// ─── Group 5: Creation & Data Verification (serial) ─────────────────────────

test.describe.serial('Plan Create - Creation and Verification', () => {
  const planNameRequired = `Plan E2E Requis ${Date.now()}`;
  const planNameFull = `Plan E2E Complet ${Date.now()}`;
  const createdSlugs: string[] = [];

  test('should create a plan with required fields only', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.fillForm({
      nom: planNameRequired,
      rang: 1,
      anneeDebut: 2025,
      anneeFin: 2035,
      ct88: false,
    });

    await createPage.selectSiteByName('Camargue');
    await createPage.submit();

    // Should redirect to plan detail page
    await page.waitForURL(/\/plans\/(?!nouveau)/, { timeout: 15000 });
    const url = page.url();
    expect(url).toMatch(/\/plans\/[^/]+$/);
    createdSlugs.push(url.split('/plans/')[1]);

    // Verify on detail page
    const planTitle = page.locator('.plan-title');
    await expect(planTitle).toContainText(planNameRequired);

    const statusValue = page.locator('.meta-value.status');
    await expect(statusValue).toContainText('Brouillon');
  });

  test('should create a plan with optional fields', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.fillForm({
      nom: planNameFull,
      rang: 2,
      anneeDebut: 2024,
      anneeFin: 2034,
      surface: 250.75,
      ct88: true,
    });

    await createPage.selectSiteByName('Camargue');
    await createPage.setOrganismeFreeText('Bureau Etudes Test');
    await createPage.addRedacteurFreeText('Jean Dupont Externe');
    await createPage.submit();

    // Should redirect to plan detail page
    await page.waitForURL(/\/plans\/(?!nouveau)/, { timeout: 15000 });
    const url = page.url();
    createdSlugs.push(url.split('/plans/')[1]);

    // Verify on detail page
    const planTitle = page.locator('.plan-title');
    await expect(planTitle).toContainText(planNameFull);

    // Check surface is displayed
    const surfaceValue = page.locator('.meta-value').filter({ hasText: /ha/ });
    await expect(surfaceValue).toBeVisible();
  });

  test('should show created plan in the list', async ({ superAdminPage: page }) => {
    const plansPage = new PlansListPage(page);
    await plansPage.goto();
    await plansPage.waitForData();

    // Draft plans appear in Actifs tab (statut !== 'archive')
    // Search for the plan created with required fields
    await plansPage.searchPlan(planNameRequired);
    const planRow = plansPage.getRowByName(planNameRequired);
    await expect(planRow).toBeVisible();
  });

  test('cleanup: delete created plans', async () => {
    const api = new ApiHelper();
    await api.login('admin@test.fr', 'Test123!');

    // Get plans to find IDs by searching
    for (const slug of createdSlugs) {
      if (!slug) continue;
      try {
        const plan = await api.get<{ id_pg: number }>(`/plans/plans/by-slug/${slug}/`);
        await api.delete(`/plans/plans/${plan.id_pg}/`);
      } catch {
        // Plan may not exist, ignore
      }
    }
  });
});

// ─── Group 6: Permissions & Role-Based Site Visibility ───────────────────────

test.describe('Plan Create - Permissions', () => {

  test('should show all sites for super admin (>= 7)', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    const count = await createPage.siteItems.count();
    expect(count).toBeGreaterThanOrEqual(7);
  });

  test('should show only RNF sites for admin RNF', async ({ adminRnfPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    // RNF sites should be visible
    await expect(createPage.siteItems.filter({ hasText: 'Camargue' })).toBeVisible();
    await expect(createPage.siteItems.filter({ hasText: 'Aiguilles Rouges' })).toBeVisible();
    await expect(createPage.siteItems.filter({ hasText: 'Lac de Remoray' })).toBeVisible();

    // CEN sites should NOT be visible
    await expect(createPage.siteItems.filter({ hasText: 'Grand-Voyeux' })).not.toBeVisible();
    await expect(createPage.siteItems.filter({ hasText: 'Vercors' })).not.toBeVisible();
  });

  test('should show only CEN sites for admin CEN', async ({ adminCenPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    // CEN sites should be visible
    await expect(createPage.siteItems.filter({ hasText: 'Grand-Voyeux' })).toBeVisible();
    await expect(createPage.siteItems.filter({ hasText: 'Vercors' })).toBeVisible();

    // RNF site should NOT be visible
    await expect(createPage.siteItems.filter({ hasText: 'Camargue' })).not.toBeVisible();
  });

  test('should allow referent to access create form', async ({ referentPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    expect(page.url()).toContain('/plans/nouveau');
    await expect(createPage.formCard).toBeVisible();
  });

  test('should allow regular user to access create form', async ({ userRnfPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    expect(page.url()).toContain('/plans/nouveau');
    await expect(createPage.formCard).toBeVisible();
  });
});

// ─── Group 7: Navigation ─────────────────────────────────────────────────────

test.describe('Plan Create - Navigation', () => {

  test('should navigate back to plans list on cancel', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.cancelButton.click();
    await expect(page).toHaveURL(/\/plans$/);
  });

  test('should navigate to plans list via breadcrumb', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.breadcrumbPlansLink.click();
    await expect(page).toHaveURL(/\/plans$/);
  });
});

// ─── Group 8: Year Validation ────────────────────────────────────────────────

test.describe('Plan Create - Year Validation', () => {

  test('should reject end year before start year', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.fillForm({
      nom: `Plan Bad Years ${Date.now()}`,
      rang: 1,
      anneeDebut: 2030,
      anneeFin: 2020,
      ct88: false,
    });

    await createPage.selectSiteByName('Camargue');
    await createPage.submit();

    // Should stay on the form (no redirect) or show an error
    // The backend may reject it, or the form may catch it
    await page.waitForURL(/\/plans/, { timeout: 5000 });

    const url = page.url();
    const stayedOrError =
      url.includes('/plans/nouveau') ||
      await createPage.errorBanner.isVisible().catch(() => false) ||
      await createPage.snackbar.isVisible().catch(() => false);
    expect(stayedOrError).toBe(true);
  });

  test('should show errors for empty year fields', async ({ superAdminPage: page }) => {
    const createPage = new PlanCreatePage(page);
    await createPage.goto();
    await createPage.waitForForm();

    await createPage.anneeDebutInput.fill('');
    await createPage.anneeFinInput.fill('');
    await createPage.submit();

    // At least one mat-error for years should appear
    const errors = await createPage.getErrors();
    expect(errors.length).toBeGreaterThan(0);
  });
});
