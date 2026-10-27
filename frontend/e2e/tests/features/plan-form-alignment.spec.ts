/**
 * E2E — alignement « Rang du plan de gestion » / « Surface totale concernée » (#527).
 *
 * Les deux champs sont côte à côte, mais l'aide du rang tient sur plusieurs
 * lignes et celle de la surface sur une seule : sans grille partagée, les deux
 * champs de saisie ne sont pas à la même hauteur. Même chose pour les
 * années de début et de fin. Vérifié sur la modale « Modifier les données de
 * référence » et sur la page de création d'un plan.
 */
import { Locator } from '@playwright/test';
import { test, expect } from '../../fixtures/auth.fixture';
import { apiGet } from '../../helpers/plan.helper';

async function top(locator: Locator): Promise<number> {
  const box = await locator.boundingBox();
  return box ? box.y : Number.NaN;
}

async function expectSideBySide(scope: Locator, left: string, right: string): Promise<void> {
  const a = scope.locator(`input[formcontrolname="${left}"]`);
  const b = scope.locator(`input[formcontrolname="${right}"]`);
  await expect(a).toBeVisible({ timeout: 15000 });
  await expect(b).toBeVisible();

  const fieldOf = (input: Locator) => input.locator('xpath=ancestor::app-form-field[1]');
  // poll : la page peut encore se recomposer (chargements asynchrones) entre deux mesures.
  const gap = (x: Locator, y: Locator) => async () => Math.abs((await top(x)) - (await top(y)));
  await expect.poll(gap(fieldOf(a).locator('label'), fieldOf(b).locator('label'))).toBeLessThan(1);
  await expect.poll(gap(a, b)).toBeLessThan(1);
}

async function expectRangSurfaceAligned(scope: Locator): Promise<void> {
  await expectSideBySide(scope, 'rang', 'surface');
  await expectSideBySide(scope, 'annee_debut', 'annee_fin');
}

test.describe('Alignement rang / surface (#527)', () => {
  // Largeur où l'aide du rang passe sur deux lignes et pas celle de la surface.
  // Sans grille partagée, le champ de droite était en plus décalé de l'espacement
  // vertical global entre champs successifs (`app-form-field + app-form-field`).
  test.use({ viewport: { width: 1280, height: 900 } });

  test('modale « Modifier les données de référence »', async ({ superAdminPage: page }) => {
    const { data } = await apiGet(page, 'plans/plans/', { statut: 'draft', page_size: '5' });
    const drafts = data.results || data;
    test.skip(drafts.length === 0, 'Aucun plan en brouillon dans le jeu d\'essai');

    await page.goto(`/plans/${drafts[0].slug}`);
    await page.locator('.btn-lifecycle-edit').first().click();
    await expectRangSurfaceAligned(page.locator('mat-dialog-container'));
  });

  test('page de création d\'un plan', async ({ superAdminPage: page }) => {
    await page.goto('/plans/nouveau');
    await expectRangSurfaceAligned(page.locator('body'));
  });
});
