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
  findFirstOperation,
  apiGet,
  apiPost,
} from '../../helpers/plan.helper';

// ─── Helpers ────────────────────────────────────────────────────

/** Find an operation that has at least one OperationAnnee. */
async function findOperationWithAnnee(page: any, planId: number) {
  const { data } = await apiGet(page, `plans/operations/by-plan/${planId}/`);
  const allOps: any[] = [];
  for (const group of data.groups || []) {
    if (Array.isArray(group.operations)) allOps.push(...group.operations);
  }
  // Pick first op that has annees
  for (const op of allOps) {
    if (op.operation_annees && op.operation_annees.length > 0) {
      return op;
    }
    // Some serializers omit operation_annees in list - fetch detail
    const { data: detail } = await apiGet(page, `plans/operations/${op.id_operation}/`);
    if (detail.operation_annees && detail.operation_annees.length > 0) {
      return detail;
    }
  }
  throw new Error(`No operation with OperationAnnee found for plan ${planId}`);
}

// ─── Tests ───────────────────────────────────────────────────────

test.describe('Suivi - Saisie page', () => {
  test('renders header, year tabs and form sections', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const op = await findOperationWithAnnee(referentPage, plan.id_pg);
    const oa = op.operation_annees[0];

    await referentPage.goto(
      `/plans/${plan.slug}/suivi-actions/saisie/${op.id_operation}/${oa.annee}`,
    );

    // Title = operation libelle
    await expect(referentPage.locator('.plan-title')).toContainText(op.libelle);

    // Year tabs visible with at least one active
    await expect(referentPage.locator('.year-tab').first()).toBeVisible();
    await expect(referentPage.locator('.year-tab.active')).toContainText(String(oa.annee));

    // Sections
    await expect(referentPage.locator('.saisie-card').first()).toBeVisible();
    await expect(referentPage.getByText(/Réalisation/i)).toBeVisible();
    await expect(referentPage.getByText(/^Détails/i)).toBeVisible();

    // Modify action button in hero
    await expect(referentPage.locator('.btn-hero-primary')).toContainText(/Modifier l'action/);
  });

  test('switches between year tabs and updates active state', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const op = await findOperationWithAnnee(referentPage, plan.id_pg);
    const annees = op.operation_annees.map((oa: any) => oa.annee).sort();
    if (annees.length < 2) test.skip(true, 'Need at least 2 OperationAnnee to test year switching');

    const initial = annees[0];
    const target = annees[1];

    await referentPage.goto(
      `/plans/${plan.slug}/suivi-actions/saisie/${op.id_operation}/${initial}`,
    );

    await expect(referentPage.locator('.year-tab.active')).toContainText(String(initial));
    await referentPage.locator('.year-tab', { hasText: String(target) }).click();
    await expect(referentPage.locator('.year-tab.active')).toContainText(String(target));
  });

  test('submit persists realisation via upsert', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const op = await findOperationWithAnnee(referentPage, plan.id_pg);
    // Pick an OperationAnnee in mode 'none' (cell-level budget input visible)
    const oa = op.operation_annees.find((o: any) => o.id_operation_annee);
    if (!oa) test.skip(true, 'No usable OperationAnnee');

    await referentPage.goto(
      `/plans/${plan.slug}/suivi-actions/saisie/${op.id_operation}/${oa.annee}`,
    );

    // Wait for the form to be ready
    await referentPage.waitForSelector('.realisation-table, .saisie-card');

    // Commentaires : unique marker so we can verify after reload
    const marker = `Test E2E ${Date.now()}`;
    await referentPage.locator('textarea[formcontrolname="commentaires"]').fill(marker);

    // Click Save (Enregistrer)
    await referentPage.getByRole('button', { name: /Enregistrer/i }).click();

    // Snackbar success
    await expect(referentPage.getByText(/Modifications enregistrées/i)).toBeVisible({ timeout: 6000 });

    // Reload + verify the textarea retains the marker
    await referentPage.reload();
    await referentPage.waitForSelector('textarea[formcontrolname="commentaires"]');
    await expect(referentPage.locator('textarea[formcontrolname="commentaires"]')).toHaveValue(marker);
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
