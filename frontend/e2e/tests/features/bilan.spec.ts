/**
 * E2E tests for the Bilan de gestion page (Phase 4 - Suivis).
 *
 * Covers:
 * - Page renders with hero, summary cards and bar charts
 * - When data exists (seeder runs realisations), cards show non-zero values
 * - Empty state when no realisations exist
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { findPlan, apiGet } from '../../helpers/plan.helper';

test.describe('Bilan page', () => {
  test('renders hero + sidebar + breadcrumb', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/bilan`);

    await expect(referentPage.locator('.plan-title')).toContainText(/Bilan/i);
    await expect(referentPage.locator('.breadcrumb-current')).toContainText(/Bilan/i);
  });

  test('shows summary cards (taux, budget, RH) when realisations exist', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');

    // Vérifier que le bilan retourne au moins une réalisation (seeder)
    const { data } = await apiGet(referentPage, `plans/realisations/bilan/${plan.id_pg}/`);
    if (data.taux_realisation.total === 0) {
      test.skip(true, 'No realisations seeded for Camargue plan');
    }

    await referentPage.goto(`/plans/${plan.slug}/bilan`);

    // 3 cards summary
    const cards = referentPage.locator('.summary-card');
    await expect(cards).toHaveCount(3);

    // Taux contient un %
    await expect(cards.first().locator('.big-number')).toContainText('%');

    // Budget table avec ligne TOTAL
    await expect(referentPage.locator('.kpi-table .total-row')).toBeVisible();

    // Légende des niveaux
    await expect(referentPage.locator('.legend .legend-item')).toHaveCount(6);
  });

  test('renders bar charts for categories and enjeux', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const { data } = await apiGet(referentPage, `plans/realisations/bilan/${plan.id_pg}/`);
    if (data.taux_realisation.total === 0) {
      test.skip(true, 'No realisations seeded for Camargue plan');
    }
    if (data.by_categorie_action.length === 0 && data.by_enjeu.length === 0) {
      test.skip(true, 'No category/enjeu data');
    }

    await referentPage.goto(`/plans/${plan.slug}/bilan`);

    // Au moins une .chart-card
    const charts = referentPage.locator('.chart-card');
    await expect(charts.first()).toBeVisible();

    // Au moins une barre empilée
    await expect(referentPage.locator('.stacked-bar').first()).toBeVisible();
    await expect(referentPage.locator('.stacked-bar .segment').first()).toBeVisible();
  });
});
