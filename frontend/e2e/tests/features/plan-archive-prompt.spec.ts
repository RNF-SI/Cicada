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
  /** #277 — Étape CSRPN en cours (null = pas dans le workflow). */
  validation_step?: string | null;
  plan_parent_id?: number | null;
  plan_parent_nom?: string | null;
}

/** Cherche un plan brouillon (hors workflow CSRPN) dont le plan_parent est
 *  encore validé. Les drafts en workflow CSRPN n'exposent PAS le bouton
 *  "Valider le plan" — ils utilisent les actions dédiées au workflow. */
async function findDraftWithValidatedParent(
  page: import('@playwright/test').Page,
): Promise<{ child: SeedPlan; parent: SeedPlan } | null> {
  const { data } = await apiGet(page, 'plans/plans/', { statut: 'draft', page_size: '50' });
  const drafts: SeedPlan[] = data.results || data;
  for (const draft of drafts) {
    if (!draft.plan_parent_id) continue;
    if (draft.validation_step) continue;  // exclure les drafts en workflow CSRPN
    // Exclure le brouillon Camargue : c'est la cible partagée de findPlan('Camargue')
    // pour les tests operations/enjeux/suivi. Le valider ici (et un flake éventuel
    // avant le cleanup) le laisserait en `modifie`, cassant ces tests en aval.
    if (/brouillon E2E/i.test(draft.nom)) continue;
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

    try {
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
      // the chain has no mi-parcours yet. Wait for whichever dialog opens first
      // and dismiss the mi-parcours one as "modification ordinaire" if applicable.
      const miParcoursDialog = page.locator('mat-dialog-container').filter({
        hasText: /Évaluation à mi-parcours/i,
      });
      const archiveDialogEarly = page.locator('app-archive-previous-plan-dialog');
      await Promise.race([
        miParcoursDialog.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {}),
        archiveDialogEarly.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {}),
      ]);
      if (await miParcoursDialog.isVisible().catch(() => false)) {
        // Click "Non — modification ordinaire" — the middle button.
        // Use locator with hasText for robust matching (em-dash + accents).
        await miParcoursDialog.locator('button').filter({ hasText: /modification ordinaire/i }).click();
        await miParcoursDialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
      }

      // The MatDialog appears once the change-status API responds.
      const dialog = page.locator('app-archive-previous-plan-dialog');
      await expect(dialog).toBeVisible({ timeout: 10000 });

      // It should show the parent's full name.
      await expect(dialog).toContainText(parent.nom);

      // Click "Conserver les deux plans" to dismiss without archiving.
      await dialog.getByRole('button', { name: /Conserver/i }).click();
      await expect(dialog).not.toBeVisible({ timeout: 5000 });
    } finally {
      // Cleanup (toujours exécuté, même sur échec en cours de test) : restaurer
      // l'état du seed pour ne pas casser les tests en aval qui partagent ce plan.
      await apiPost(page, `plans/plans/${child.id_pg}/change-status/`, { new_status: 'draft' });
    }
  });

  test('archives the previous plan when user confirms', async ({ superAdminPage: page }) => {
    const found = await findDraftWithValidatedParent(page);
    test.skip(!found, 'No draft plan with a validated parent in seed data');
    const { child, parent } = found!;

    try {
      await page.goto(`/plans/${child.slug}`);
      const validateBtn = page.locator('.btn-lifecycle.btn-lifecycle-success');
      await validateBtn.waitFor({ state: 'visible', timeout: 15000 });

      await validateBtn.click();
      // confirmValidation() opens a Material ConfirmDialog
      const lifecycleConfirm = page.locator('mat-dialog-container').filter({
        hasText: /Valider le plan/i,
      });
      await lifecycleConfirm.getByRole('button', { name: /Valider le plan/i }).click();

      // #276 — Mi-parcours popup may intercept; race to detect it.
      const miParcoursDialog = page.locator('mat-dialog-container').filter({
        hasText: /Évaluation à mi-parcours/i,
      });
      const archiveDialogEarly = page.locator('app-archive-previous-plan-dialog');
      await Promise.race([
        miParcoursDialog.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {}),
        archiveDialogEarly.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {}),
      ]);
      if (await miParcoursDialog.isVisible().catch(() => false)) {
        // Click "Non — modification ordinaire" — the middle button.
        // Use locator with hasText for robust matching (em-dash + accents).
        await miParcoursDialog.locator('button').filter({ hasText: /modification ordinaire/i }).click();
        await miParcoursDialog.waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
      }

      const dialog = page.locator('app-archive-previous-plan-dialog');
      await expect(dialog).toBeVisible({ timeout: 10000 });

      // Confirm: archive the previous plan.
      await dialog.getByRole('button', { name: /Archiver le précédent/i }).click();
      await expect(dialog).not.toBeVisible({ timeout: 5000 });

      // Verify the parent was archived via API. L'archivage du précédent est un
      // second appel change-status asynchrone déclenché après la fermeture de la
      // modale : on attend qu'il aboutisse plutôt que de lire l'état trop tôt.
      await expect.poll(
        async () => {
          const { data } = await apiGet(page, `plans/plans/${parent.id_pg}/`);
          return data.statut;
        },
        { timeout: 10000, message: 'parent plan should become archived' },
      ).toBe('archive');
    } finally {
      // Cleanup (toujours exécuté, même sur échec) : restaurer l'état du seed
      // (parent → valide, child → draft) pour ne pas casser les tests en aval.
      await apiPost(page, `plans/plans/${parent.id_pg}/change-status/`, { new_status: 'valide' });
      await apiPost(page, `plans/plans/${child.id_pg}/change-status/`, { new_status: 'draft' });
    }
  });
});
