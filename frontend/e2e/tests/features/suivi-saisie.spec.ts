/**
 * E2E tests for the Suivi - Saisie page (Phase 2 - Suivis).
 *
 * Covers:
 * - Page renders from a year cell in the Suivi des actions table
 * - Form sections are visible (operateurs/financeurs read-only, réalisation, détails)
 * - Submit persists values via /api/plans/realisations/upsert/
 * - Year tabs switch between years
 *
 * Prerequisite: seed_testdata creates operations + realisations on Camargue.
 */
import { test, expect } from '../../fixtures/auth.fixture';
import {
  findPlan,
  findFirstMetrique,
  apiGet,
  apiPost,
  apiDelete,
} from '../../helpers/plan.helper';

// ─── Helpers ────────────────────────────────────────────────────

/**
 * Crée une opération DÉDIÉE à ces tests, avec des OperationAnnee explicites et
 * cohérentes (annee_min/max alignés sur les années créées).
 *
 * On NE réutilise PAS une opération seedée partagée : operations.spec.ts édite
 * « la première opération du plan » (findFirstOperation) sur le même plan
 * brouillon Camargue, ce qui corrompt ses années (incohérence annee_min/max vs
 * OperationAnnee) et casse les assertions d'onglets d'années ici. Une opération
 * fraîche par test garantit l'isolation.
 */
async function createSuiviOperation(page: any, planId: number) {
  const met = await findFirstMetrique(page, planId);
  const annees = [2025, 2026, 2027];
  const { ok, status, data } = await apiPost(page, 'plans/operations/', {
    libelle: `E2E Suivi Saisie ${Date.now()}`,
    annee_min: annees[0],
    annee_max: annees[annees.length - 1],
    ventilation_mode: 'none',
    metrique_ids: [met.id_metrique],
    operation_annees: annees.map((a) => ({
      annee: a, periodicite: true, budget: 5000, etp: 10,
    })),
  });
  if (!ok) {
    throw new Error(`Failed to create suivi operation (status ${status}): ${JSON.stringify(data)}`);
  }
  return data; // OperationSerializer : inclut operation_annees (avec id_operation_annee)
}

// ─── Tests ───────────────────────────────────────────────────────

test.describe('Suivi - Saisie page', () => {
  test('renders header, year tabs and form sections', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const op = await createSuiviOperation(referentPage, plan.id_pg);
    const oa = op.operation_annees[0];

    try {
      await referentPage.goto(
        `/plans/${plan.slug}/suivi-actions/saisie/${op.id_operation}/${oa.annee}`,
      );

      // Title = operation libelle
      await expect(referentPage.locator('.plan-title')).toContainText(op.libelle);

      // Year tabs visible with at least one active
      await expect(referentPage.locator('.year-tab').first()).toBeVisible();
      await expect(referentPage.locator('.year-tab.active')).toContainText(String(oa.annee));

      // Sections (titres de cartes — locator précis pour éviter les libellés de
      // champs comme « Niveau de réalisation » qui matchent aussi /Réalisation/).
      await expect(referentPage.locator('.saisie-card').first()).toBeVisible();
      await expect(referentPage.getByRole('heading', { name: 'Réalisation', exact: true })).toBeVisible();
      await expect(referentPage.getByRole('heading', { name: 'Détails', exact: true })).toBeVisible();

      // Modify action button in hero
      await expect(referentPage.locator('.btn-hero-primary')).toContainText(/Modifier l'action/);
    } finally {
      await apiDelete(referentPage, `plans/operations/${op.id_operation}/`);
    }
  });

  test('switches between year tabs and updates active state', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const op = await createSuiviOperation(referentPage, plan.id_pg);
    const annees = op.operation_annees.map((oa: any) => oa.annee).sort((a: number, b: number) => a - b);

    const initial = annees[0];
    const target = annees[1];

    try {
      await referentPage.goto(
        `/plans/${plan.slug}/suivi-actions/saisie/${op.id_operation}/${initial}`,
      );

      await expect(referentPage.locator('.year-tab.active')).toContainText(String(initial));
      await referentPage.locator('.year-tab', { hasText: String(target) }).click();
      await expect(referentPage.locator('.year-tab.active')).toContainText(String(target));
    } finally {
      await apiDelete(referentPage, `plans/operations/${op.id_operation}/`);
    }
  });

  test('submit persists realisation via upsert', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const op = await createSuiviOperation(referentPage, plan.id_pg);
    // OperationAnnee en mode 'none' (cell-level budget input visible)
    const oa = op.operation_annees.find((o: any) => o.id_operation_annee);
    if (!oa) test.skip(true, 'No usable OperationAnnee');

    try {
      await referentPage.goto(
        `/plans/${plan.slug}/suivi-actions/saisie/${op.id_operation}/${oa.annee}`,
      );

      // Wait for the form to be ready
      await referentPage.waitForSelector('.realisation-table, .saisie-card');

      // Commentaires : unique marker so we can verify after reload
      const marker = `Test E2E ${Date.now()}`;
      await referentPage.locator('textarea[formcontrolname="commentaires"]').fill(marker);

      // Click Save (« Enregistrer » exact — distinct de « Enregistrer et quitter »)
      await referentPage.getByRole('button', { name: 'Enregistrer', exact: true }).click();

      // Snackbar success
      await expect(referentPage.getByText(/Modifications enregistrées/i)).toBeVisible({ timeout: 6000 });

      // Reload + verify the textarea retains the marker
      await referentPage.reload();
      await referentPage.waitForSelector('textarea[formcontrolname="commentaires"]');
      await expect(referentPage.locator('textarea[formcontrolname="commentaires"]')).toHaveValue(marker);
    } finally {
      await apiDelete(referentPage, `plans/operations/${op.id_operation}/`);
    }
  });

  test('renders per-organisme sub-tables for by_org_type operations', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    // Trouver une op ventilée par organisme
    const { data } = await apiGet(referentPage, `plans/operations/by-plan/${plan.id_pg}/`);
    let opVentilated: any = null;
    for (const group of data.groups || []) {
      for (const op of group.operations || []) {
        const { data: detail } = await apiGet(referentPage, `plans/operations/${op.id_operation}/`);
        if (detail.ventilation_mode === 'by_org_type' && detail.operation_annees?.some((o: any) => o.organismes?.length)) {
          opVentilated = detail;
          break;
        }
      }
      if (opVentilated) break;
    }
    if (!opVentilated) test.skip(true, 'No by_org_type operation in seed data');

    const oa = opVentilated.operation_annees.find((o: any) => o.organismes?.length);
    await referentPage.goto(
      `/plans/${plan.slug}/suivi-actions/saisie/${opVentilated.id_operation}/${oa.annee}`,
    );

    // Un .org-block par organisme + un total
    const blocks = referentPage.locator('.org-block');
    await blocks.first().waitFor({ state: 'visible' });
    const count = await blocks.count();
    expect(count).toBeGreaterThanOrEqual(oa.organismes.length + 1); // orgs + TOTAL
    await expect(referentPage.locator('.org-block.total-block .org-title.total')).toBeVisible();

    // Investissement présent (mode by_org_type)
    await expect(referentPage.getByText(/Budget investissement/i).first()).toBeVisible();
  });

  test('clicking a year cell in suivi-actions navigates to saisie', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions`);
    // Wait until the table is rendered with at least one year cell
    const firstCell = referentPage.locator('td.col-year.clickable').first();
    await firstCell.waitFor({ state: 'visible', timeout: 8000 });
    await firstCell.click();
    await expect(referentPage).toHaveURL(/\/suivi-actions\/saisie\/\d+\/\d+/);
  });
});
