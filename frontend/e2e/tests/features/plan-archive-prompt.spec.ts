/**
 * E2E Tests for the archive-previous-plan prompt (#246).
 *
 * Scénario: lorsqu'un plan brouillon est validé alors qu'un autre plan de la
 * même chaîne de versions (`plan_parent`) est encore au statut `valide`, une
 * pop-up doit proposer d'archiver le plan précédent.
 *
 * Prérequis seed_testdata : 1 plan d'évaluation mi-parcours en brouillon
 * (`plan_parent` = plan "Aiguilles Rouges" en statut `valide`).
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { apiGet, apiPost } from '../../helpers/plan.helper';

interface SeedPlan {
  id_pg: number;
  nom: string;
  slug: string;
  statut: string;
  plan_parent_id?: number | null;
  plan_parent_nom?: string | null;
}

/** Cherche un plan brouillon dont le plan_parent est encore validé. */
async function findDraftWithValidatedParent(
  page: import('@playwright/test').Page,
): Promise<{ child: SeedPlan; parent: SeedPlan } | null> {
  const { data } = await apiGet(page, 'plans/plans/', { statut: 'draft', page_size: '50' });
  const drafts: SeedPlan[] = data.results || data;
  for (const draft of drafts) {
    if (!draft.plan_parent_id) continue;
    const { data: parentData } = await apiGet(page, `plans/plans/${draft.plan_parent_id}/`);
    if (parentData?.statut === 'valide') {
      return { child: draft, parent: parentData };
    }
  }
  return null;
}

test.describe('Plan archive-previous prompt (#246)', () => {
  test('shows the archive dialog when validating a plan whose parent is still valide', async ({ superAdminPage: page }) => {
    const found = await findDraftWithValidatedParent(page);
    test.skip(!found, 'No draft plan with a validated parent in seed data');
    const { child, parent } = found!;

    await page.goto(`/plans/${child.slug}`);
    // Wait for the lifecycle action button to appear (only visible if user can manage lifecycle).
    const validateBtn = page.locator('.btn-lifecycle.btn-lifecycle-success');
    await validateBtn.waitFor({ state: 'visible', timeout: 15000 });

    // confirmValidation() opens a Material ConfirmDialog before triggering the API.
    await validateBtn.click();
    const lifecycleConfirm = page.locator('mat-dialog-container').filter({
      hasText: /Valider le plan/i,
    });
    await lifecycleConfirm.getByRole('button', { name: /Valider le plan/i }).click();

    // #276 — Mi-parcours popup may intercept before the archive prompt when
    // the chain has no mi-parcours yet. Dismiss it as "modification ordinaire".
    const miParcoursDialog = page.locator('mat-dialog-container').filter({
      hasText: /Évaluation à mi-parcours/i,
    });
    if (await miParcoursDialog.isVisible({ timeout: 2000 }).catch(() => false)) {
      await miParcoursDialog.getByRole('button', { name: /modification ordinaire/i }).click();
    }

    // The MatDialog appears once the change-status API responds.
    const dialog = page.locator('app-archive-previous-plan-dialog');
    await expect(dialog).toBeVisible({ timeout: 10000 });

    // It should show the parent's full name.
    await expect(dialog).toContainText(parent.nom);

    // Click "Conserver les deux plans" to dismiss without archiving.
    await dialog.getByRole('button', { name: /Conserver/i }).click();
    await expect(dialog).not.toBeVisible({ timeout: 5000 });

    // Cleanup: revert child plan to draft so the seed remains stable.
    await apiPost(page, `plans/plans/${child.id_pg}/change-status/`, { new_status: 'draft' });
  });

  test('archives the previous plan when user confirms', async ({ superAdminPage: page }) => {
    const found = await findDraftWithValidatedParent(page);
    test.skip(!found, 'No draft plan with a validated parent in seed data');
    const { child, parent } = found!;

    await page.goto(`/plans/${child.slug}`);
    const validateBtn = page.locator('.btn-lifecycle.btn-lifecycle-success');
    await validateBtn.waitFor({ state: 'visible', timeout: 15000 });

    await validateBtn.click();
    // confirmValidation() opens a Material ConfirmDialog
    const lifecycleConfirm = page.locator('mat-dialog-container').filter({
      hasText: /Valider le plan/i,
    });
    await lifecycleConfirm.getByRole('button', { name: /Valider le plan/i }).click();

    // #276 — Dismiss mi-parcours popup if it intercepts.
    const miParcoursDialog = page.locator('mat-dialog-container').filter({
      hasText: /Évaluation à mi-parcours/i,
    });
    if (await miParcoursDialog.isVisible({ timeout: 2000 }).catch(() => false)) {
      await miParcoursDialog.getByRole('button', { name: /modification ordinaire/i }).click();
    }

    const dialog = page.locator('app-archive-previous-plan-dialog');
    await expect(dialog).toBeVisible({ timeout: 10000 });

    // Confirm: archive the previous plan.
    await dialog.getByRole('button', { name: /Archiver le précédent/i }).click();
    await expect(dialog).not.toBeVisible({ timeout: 5000 });

    // Verify the parent was archived via API.
    const { data: refreshedParent } = await apiGet(page, `plans/plans/${parent.id_pg}/`);
    expect(refreshedParent.statut).toBe('archive');

    // Cleanup: restore the seed state (parent → valide, child → draft).
    await apiPost(page, `plans/plans/${parent.id_pg}/change-status/`, { new_status: 'valide' });
    await apiPost(page, `plans/plans/${child.id_pg}/change-status/`, { new_status: 'draft' });
  });
});
