/**
 * E2E tests for the « Bilan de la gestion » page (Suivis).
 *
 * Refonte kit UI (Figma 4515-73893 / 74450 / 74948) : onglets Indicateurs /
 * Actions, portée Global / Mi-parcours / Annuel, graphiques (donut, barres,
 * radar) issus de la bibliothèque `shared/components/charts`.
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { findPlan, apiGet } from '../../helpers/plan.helper';

test.describe('Bilan page', () => {
  test('renders hero, tabs and scope selector', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/bilan`);

    // #503 → refonte kit UI : le titre est désormais « Bilan de la gestion ».
    await expect(referentPage.locator('.plan-title')).toContainText(/Bilan de la gestion/i);
    await expect(referentPage.locator('.breadcrumb-current')).toContainText(/Bilan de la gestion/i);

    // Onglets Indicateurs / Actions.
    await expect(referentPage.locator('.big-tab')).toHaveCount(2);
    // Portée Global / Mi-parcours / Annuel.
    await expect(referentPage.locator('.scope-row .pill-btn')).toHaveCount(3);
  });

  test('actions tab shows budget, RH and taux donut when realisations exist', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');

    const { data } = await apiGet(referentPage, `plans/realisations/bilan/${plan.id_pg}/`);
    if (data.taux_realisation.total === 0) {
      test.skip(true, 'No realisations seeded for Camargue plan');
    }

    await referentPage.goto(`/plans/${plan.slug}/bilan`);
    await referentPage.locator('.big-tab', { hasText: 'Actions' }).click();

    // Carte budget (fond vert pâle) avec la ligne Total.
    await expect(referentPage.locator('.budget-table .total-row')).toBeVisible();
    // Synthèse RH (prévisionnelle / réelle).
    await expect(referentPage.locator('.rh-summary')).toBeVisible();
    // Donut « taux de réalisation des actions ».
    await expect(referentPage.locator('app-donut-chart svg').first()).toBeVisible();
  });

  test('actions tab renders stacked bar charts + legend for categories / enjeux', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const { data } = await apiGet(referentPage, `plans/realisations/bilan/${plan.id_pg}/`);
    if (data.taux_realisation.total === 0) {
      test.skip(true, 'No realisations seeded');
    }
    if (data.by_categorie_action.length === 0 && data.by_enjeu.length === 0) {
      test.skip(true, 'No category/enjeu data');
    }

    await referentPage.goto(`/plans/${plan.slug}/bilan`);
    await referentPage.locator('.big-tab', { hasText: 'Actions' }).click();

    // Au moins un graphe en barres (SVG) + sa légende de niveaux.
    await expect(referentPage.locator('app-bar-chart svg.bar-svg').first()).toBeVisible();
    await expect(referentPage.locator('app-chart-legend .legend__item').first()).toBeVisible();
  });

  test('indicateurs tab renders chart tiles and donut when indicateurs exist', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const { data } = await apiGet(referentPage, `plans/realisations/bilan-indicateurs/${plan.id_pg}/`);
    if (!data || data.total_indicateurs === 0) {
      test.skip(true, 'No indicateurs seeded');
    }

    await referentPage.goto(`/plans/${plan.slug}/bilan`);

    // Onglet Indicateurs actif par défaut → tuiles graphiques présentes.
    await expect(referentPage.locator('app-chart-card').first()).toBeVisible();
    // Le donut « évaluation » a toujours au moins une part (fait / pas fait).
    await expect(referentPage.locator('app-donut-chart svg').first()).toBeVisible();
  });

  test('indicateurs tab shows the evolution line chart when a time-series exists', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const { data } = await apiGet(referentPage, `plans/realisations/bilan-series/${plan.id_pg}/`);
    const hasEvolution = data && (data.indicateurs_evolution?.mean ?? []).some((v: number | null) => v !== null);
    if (!hasEvolution) {
      test.skip(true, 'No indicator time-series seeded');
    }

    await referentPage.goto(`/plans/${plan.slug}/bilan`);
    // La courbe d'évolution (globale) est rendue en SVG.
    await expect(referentPage.locator('app-line-chart svg.line-svg')).toBeVisible();
  });
});
