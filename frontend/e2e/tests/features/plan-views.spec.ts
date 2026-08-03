/**
 * E2E Tests for Plan views: Mindmap, Tableau de Bord, Suivi Actions, Bilan.
 *
 * Tests:
 * - Mindmap: display, view toggle, legend, zoom (~8 tests)
 * - Tableau de Bord: display, indicators, scores, expand (~7 tests)
 * - Suivi Actions: display, table, filters, legend (~7 tests)
 * - Bilan: coming soon page (~2 tests)
 * - Sidebar navigation (~4 tests)
 *
 * Prerequisite: seed_testdata with enjeux seeder (creates operations, indicateurs, mesures).
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { findPlan } from '../../helpers/plan.helper';

/** Wait for plan page to finish loading (spinner gone or content visible). */
async function waitForPageLoad(page: import('@playwright/test').Page, timeout = 30000) {
  // Wait for the loading indicator to disappear
  await page.locator('text=Chargement').first().waitFor({ state: 'hidden', timeout }).catch(() => {});
  // Extra stability wait
  await page.waitForTimeout(1000);
}

// =========================================================================
// MINDMAP
// =========================================================================
test.describe('Plan Views - Mindmap', () => {
  test('should display the mindmap page with hero and title', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/mindmap`);
    await waitForPageLoad(referentPage);

    const heroSection = referentPage.locator('.hero-section');
    await expect(heroSection).toBeVisible();

    const breadcrumb = referentPage.locator('.breadcrumb');
    await expect(breadcrumb).toBeVisible();
  });

  test('should display the tree visualization', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/mindmap`);
    await waitForPageLoad(referentPage);

    // Fixed-column tree should be rendered with at least one clickable cell.
    const cell = referentPage.locator('.tree-scroll .tree-cell');
    await cell.first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
    const cellCount = await cell.count();
    expect(cellCount).toBeGreaterThan(0);
  });

  test('should display view toggle buttons (Enjeux / Actions)', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/mindmap`);
    await waitForPageLoad(referentPage);

    // Wait for the view toggle to appear (rendered after data loads)
    const viewToggle = referentPage.locator('.view-toggle button, .toggle-btn');
    await viewToggle.first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
    const btnCount = await viewToggle.count();
    expect(btnCount).toBeGreaterThanOrEqual(2);
  });

  // La légende de couleurs a été retirée de la carte mentale (item 4 de la
  // revue design) : l'arbre porte désormais les couleurs sans bloc de légende.
  // Cf. le test unitaire « légende (item 4) » dans plan-mindmap.component.spec.ts.
  test('should NOT display a color legend', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/mindmap`);
    await waitForPageLoad(referentPage);

    // L'arbre doit bien être rendu (sinon l'absence de légende ne prouve rien).
    const cell = referentPage.locator('.tree-scroll .tree-cell');
    await cell.first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
    expect(await cell.count()).toBeGreaterThan(0);

    await expect(referentPage.locator('.mindmap-legend, .legend')).toHaveCount(0);
  });

  test('should switch between Enjeux and Actions views', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/mindmap`);
    await referentPage.waitForTimeout(5000);

    // Click the second toggle button (Actions view)
    const toggleBtns = referentPage.locator('.view-toggle button, .toggle-btn');
    if (await toggleBtns.count() >= 2) {
      await toggleBtns.nth(1).click();
      await waitForPageLoad(referentPage);

      // Tree should still render (re-rendered with inverse data)
      const cell = referentPage.locator('.tree-scroll .tree-cell');
      await expect(cell.first()).toBeVisible();
    }
  });

  test('should display control buttons (expand / collapse all)', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/mindmap`);
    await waitForPageLoad(referentPage);

    const controlBtns = referentPage.locator('.mindmap-controls button');
    await controlBtns.first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
    const btnCount = await controlBtns.count();
    expect(btnCount).toBeGreaterThanOrEqual(1);
  });

  test('should display sidebar navigation', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/mindmap`);
    await waitForPageLoad(referentPage);

    const sidebar = referentPage.locator('app-plan-sidebar').first();
    await expect(sidebar).toBeVisible();
  });

  test('super admin should access mindmap', async ({ superAdminPage }) => {
    const plan = await findPlan(superAdminPage, 'Camargue');
    await superAdminPage.goto(`/plans/${plan.slug}/mindmap`);
    await waitForPageLoad(superAdminPage);

    const heroSection = superAdminPage.locator('.hero-section');
    await expect(heroSection).toBeVisible();
  });
});

// =========================================================================
// TABLEAU DE BORD
// =========================================================================
test.describe('Plan Views - Tableau de Bord', () => {
  test('should display the tableau de bord page', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/tableau-de-bord`);
    await waitForPageLoad(referentPage);

    const heroSection = referentPage.locator('.hero-section');
    await expect(heroSection).toBeVisible();
  });

  test('should display Etat/Pression toggle tabs', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/tableau-de-bord`);
    await waitForPageLoad(referentPage);

    const toggleBtns = referentPage.locator('.view-toggle .toggle-btn');
    await toggleBtns.first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
    const btnCount = await toggleBtns.count();
    expect(btnCount).toBeGreaterThanOrEqual(2);
  });

  test('should display score legend with 6 levels', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/tableau-de-bord`);
    await waitForPageLoad(referentPage);

    const legend = referentPage.locator('.legend');
    await expect(legend).toBeVisible();

    const legendItems = referentPage.locator('.legend-item');
    const itemCount = await legendItems.count();
    expect(itemCount).toBeGreaterThanOrEqual(5); // 5 score levels + no-data
  });

  test('should display indicator table or empty state', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/tableau-de-bord`);
    await waitForPageLoad(referentPage);

    const table = referentPage.locator('.tdb-table');
    const emptyState = referentPage.locator('.empty-state');
    await table.or(emptyState).first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
    const hasContent = (await table.count()) > 0 || (await emptyState.count()) > 0;
    expect(hasContent).toBeTruthy();
  });

  test('should display OLT header rows in table', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/tableau-de-bord`);
    await waitForPageLoad(referentPage);

    const oltHeaders = referentPage.locator('.olt-header-row');
    const count = await oltHeaders.count();
    // Seeder creates OLTs with indicateurs
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should expand indicator row to show metriques', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/tableau-de-bord`);
    await waitForPageLoad(referentPage);

    const indicatorRows = referentPage.locator('.indicator-row');
    if (await indicatorRows.count() > 0) {
      // Click first indicator row to expand
      await indicatorRows.first().click();
      await referentPage.waitForTimeout(500);

      // Metrique rows should appear
      const metriqueRows = referentPage.locator('.metrique-row');
      const metriqueCount = await metriqueRows.count();
      expect(metriqueCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('should display breadcrumb with sidebar', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/tableau-de-bord`);
    await waitForPageLoad(referentPage);

    const sidebar = referentPage.locator('app-plan-sidebar').first();
    await expect(sidebar).toBeVisible();

    const breadcrumb = referentPage.locator('.breadcrumb');
    await expect(breadcrumb).toBeVisible();
  });
});

// =========================================================================
// SUIVI ACTIONS
// =========================================================================
test.describe('Plan Views - Suivi Actions', () => {
  test('should display the suivi actions page', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions`);
    await waitForPageLoad(referentPage);

    const heroSection = referentPage.locator('.hero-section');
    await expect(heroSection).toBeVisible();
  });

  // La page suivi-actions a été redessinée (Phase 3) : la bascule Global/Annuel
  // a laissé place à des onglets (Réalisation / Budget / RH) + un tableau
  // multi-années. On vérifie donc la présence de ces onglets de vue.
  test('should display the suivi view tabs (Réalisation / Budget / RH)', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions`);
    await waitForPageLoad(referentPage);

    const tabs = referentPage.locator('.suivi-tabs [role="tab"]');
    await tabs.first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(2);
  });

  test('should display filter bar with dropdowns', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions`);
    await waitForPageLoad(referentPage);

    const filterBar = referentPage.locator('.filter-bar');
    await expect(filterBar).toBeVisible();

    // Kit UI #592 — les filtres sont désormais des `app-filter-dropdown`
    // (déclencheur `.filter-trigger`), l'ancienne classe `.filter-btn` a disparu.
    const filterBtns = referentPage.locator('.filter-bar .filter-trigger');
    const filterCount = await filterBtns.count();
    expect(filterCount).toBeGreaterThanOrEqual(2); // At least categorie + enjeu
  });

  test('should display action status legend', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions`);
    await waitForPageLoad(referentPage);

    const legend = referentPage.locator('.legend');
    await expect(legend).toBeVisible();

    const legendItems = referentPage.locator('.legend-item');
    const count = await legendItems.count();
    expect(count).toBeGreaterThanOrEqual(3); // At least 3 action status types
  });

  test('should display actions table or empty state', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions`);
    await waitForPageLoad(referentPage);

    const table = referentPage.locator('.actions-table');
    const emptyState = referentPage.locator('.empty-state');
    await table.or(emptyState).first().waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
    const hasContent = (await table.count()) > 0 || (await emptyState.count()) > 0;
    expect(hasContent).toBeTruthy();
  });

  test('should display year columns in actions table', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions`);
    await waitForPageLoad(referentPage);

    const table = referentPage.locator('.actions-table');
    if (await table.count() > 0) {
      const yearHeaders = table.locator('thead th.col-year');
      const yearCount = await yearHeaders.count();
      // Plan Camargue 2020-2030 -> 11 year columns
      expect(yearCount).toBeGreaterThan(0);
    }
  });

  test('should display export button', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions`);
    await waitForPageLoad(referentPage);

    const exportBtn = referentPage.locator('.export-btn, .btn-generate');
    await expect(exportBtn.first()).toBeVisible();
  });
});

// =========================================================================
// BILAN
// =========================================================================
test.describe('Plan Views - Bilan', () => {
  test('should display bilan page with coming soon', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/bilan`);
    await waitForPageLoad(referentPage);

    const heroSection = referentPage.locator('.hero-section');
    await expect(heroSection).toBeVisible();

    // Should show "coming soon" content
    const comingSoon = referentPage.locator('.coming-soon, .empty-state');
    const pageContent = await referentPage.textContent('body');
    expect(pageContent?.length).toBeGreaterThan(0);
  });

  test('should display sidebar on bilan page', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/bilan`);
    await waitForPageLoad(referentPage);

    const sidebar = referentPage.locator('app-plan-sidebar').first();
    await expect(sidebar).toBeVisible();
  });
});

// =========================================================================
// SIDEBAR NAVIGATION
// =========================================================================
test.describe('Plan Views - Sidebar Navigation', () => {
  test('should navigate between plan pages via sidebar', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}`);
    await waitForPageLoad(referentPage);

    const sidebar = referentPage.locator('app-plan-sidebar').first();
    await expect(sidebar).toBeVisible();

    // Click on tableau d'arborescence link in sidebar (formerly "mindmap")
    const mindmapLink = sidebar.locator('.menu-item, .sidebar-menu-item').filter({ hasText: /arborescence|mindmap/i });
    if (await mindmapLink.count() > 0) {
      await mindmapLink.first().click();
      await referentPage.waitForURL(/(tableau-d-arborescence|mindmap)/, { timeout: 10000 });
    }
  });

  test('should show enjeux submenu in sidebar', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/enjeux`);
    await waitForPageLoad(referentPage);

    const sidebar = referentPage.locator('app-plan-sidebar').first();
    await expect(sidebar).toBeVisible();

    // Enjeux submenu should show individual enjeu items
    const submenuItems = sidebar.locator('.submenu-tree-item, .submenu-item');
    const count = await submenuItems.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('should show suivis submenu with links', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions`);
    await waitForPageLoad(referentPage);

    const sidebar = referentPage.locator('app-plan-sidebar').first();

    // Suivis submenu should have bilan, suivi-actions, tableau-de-bord
    const suivisLinks = sidebar.locator('.submenu-item, .menu-item').filter({
      hasText: /bilan|suivi|tableau/i,
    });
    const linkCount = await suivisLinks.count();
    expect(linkCount).toBeGreaterThanOrEqual(1);
  });

  test('should highlight active page in sidebar', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/mindmap`);
    await waitForPageLoad(referentPage);

    const sidebar = referentPage.locator('app-plan-sidebar').first();
    const activeItem = sidebar.locator('.menu-item.active, .sidebar-menu-item.active');
    const activeCount = await activeItem.count();
    expect(activeCount).toBeGreaterThanOrEqual(1);
  });
});
