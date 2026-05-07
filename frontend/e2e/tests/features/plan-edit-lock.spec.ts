/**
 * E2E Tests for the edit-lock on non-draft plans (#248).
 *
 * Vérifications :
 *  - Backend : PATCH/POST sur un plan validé est rejeté avec 403.
 *  - Frontend : la bannière "Plan verrouillé en lecture seule" est visible.
 *  - Frontend : le bouton "Modifier les métadonnées" est masqué.
 *
 * Prérequis : seed_testdata fournit au moins un plan en statut `valide`
 * (Camargue, Aiguilles Rouges, etc.) ainsi qu'un plan en `draft`
 * (l'évaluation mi-parcours).
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { findValidatedPlan, apiGet, apiPatch, apiPost } from '../../helpers/plan.helper';

test.describe('Plan edit-lock (#248) — backend permissions', () => {
  test('PATCH on a validated plan returns 403', async ({ superAdminPage: page }) => {
    const plan = await findValidatedPlan(page);
    expect(plan.id_pg).toBeTruthy();

    const { ok, status } = await apiPatch(page, `plans/plans/${plan.id_pg}/`, {
      commentaire: 'tentative de modification (devrait échouer)',
    });

    expect(ok).toBe(false);
    expect(status).toBe(403);
  });

  test('POST to create an enjeu on a validated plan returns 403', async ({ superAdminPage: page }) => {
    const plan = await findValidatedPlan(page);

    // Récupère une nomenclature CATEGORIE_ENJEU pour le payload
    const { data: nomData } = await apiGet(page, 'nomenclatures/', { type: 'CATEGORIE_ENJEU' });
    const categorie = (nomData.results || nomData)[0];
    test.skip(!categorie, 'Pas de nomenclature CATEGORIE_ENJEU disponible');

    const { ok, status } = await apiPost(page, 'plans/enjeux/', {
      id_pg: plan.id_pg,
      libelle: 'E2E lock test enjeu',
      id_categorie: categorie.id_nomenclature,
    });

    expect(ok).toBe(false);
    expect(status).toBe(403);
  });

  test('PATCH on a draft plan succeeds', async ({ superAdminPage: page }) => {
    // Cherche un plan en draft (l'évaluation mi-parcours du seed)
    const { data } = await apiGet(page, 'plans/plans/', { statut: 'draft', page_size: '5' });
    const drafts = data.results || data;
    test.skip(drafts.length === 0, 'No draft plan in seed');

    const draft = drafts[0];
    const before = draft.commentaire || '';
    const probe = `e2e lock test ${Date.now()}`;
    const { ok, status } = await apiPatch(page, `plans/plans/${draft.id_pg}/`, {
      commentaire: probe,
    });

    expect(status).toBe(200);
    expect(ok).toBe(true);

    // Restore
    await apiPatch(page, `plans/plans/${draft.id_pg}/`, { commentaire: before });
  });
});

test.describe('Plan edit-lock (#248) — frontend UI', () => {
  test('lock banner is visible on a validated plan detail page', async ({ superAdminPage: page }) => {
    const plan = await findValidatedPlan(page);
    await page.goto(`/plans/${plan.slug}`);

    // La bannière apparaît dans la page de détail
    const banner = page.locator('.lock-banner');
    await expect(banner).toBeVisible({ timeout: 15000 });
    await expect(banner).toContainText(/lecture seule|verrouillé/i);
  });

  test('the "Modifier les métadonnées" button is hidden on a validated plan', async ({ superAdminPage: page }) => {
    const plan = await findValidatedPlan(page);
    await page.goto(`/plans/${plan.slug}`);
    await page.waitForLoadState('networkidle').catch(() => {});

    const editBtn = page.locator('.btn-lifecycle-edit');
    await expect(editBtn).toHaveCount(0);
  });

  test('lock banner is hidden on a draft plan', async ({ superAdminPage: page }) => {
    const { data } = await apiGet(page, 'plans/plans/', { statut: 'draft', page_size: '5' });
    const drafts = data.results || data;
    test.skip(drafts.length === 0, 'No draft plan in seed');

    const draft = drafts[0];
    await page.goto(`/plans/${draft.slug}`);
    await page.waitForLoadState('networkidle').catch(() => {});

    const banner = page.locator('.lock-banner');
    await expect(banner).toHaveCount(0);
  });
});
