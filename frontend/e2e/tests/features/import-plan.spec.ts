/**
 * E2E — Import Excel de l'arborescence d'un plan de gestion (#478).
 *
 * Round-trip complet PAR L'INTERFACE :
 *   1. sur un plan seedé riche, on clique « Exporter le contenu de ce plan »
 *      depuis la page « Exports » (#617) et on capture le .xlsx téléchargé ;
 *   2. on crée un brouillon vide (API) ;
 *   3. sur sa page « Paramètres du plan », on téléverse le fichier, on attend
 *      le rapport de validation, puis on clique « Importer » ;
 *   4. on vérifie que l'arborescence a bien été créée (même nombre d'enjeux),
 *      et que le verrou brouillon masque l'import sur un plan validé.
 *
 * Le fichier n'est pas une fixture committée : il est produit à la volée par
 * l'export, donc toujours au format courant.
 */
import { test, expect } from '../../fixtures/auth.fixture';
import {
  findPlan,
  findValidatedPlan,
  apiGet,
  apiPost,
  apiDelete,
} from '../../helpers/plan.helper';

async function enjeuxCount(page: any, planId: number): Promise<number> {
  const { data } = await apiGet(page, `plans/enjeux/by-plan/${planId}/`);
  return (data.enjeux || []).length;
}

/** Déplie l'accordéon « Options avancées » (contient le mapping). */
async function openAdvanced(page: any): Promise<void> {
  const header = page
    .locator('.app-accordion__header', { hasText: 'Options avancées' })
    .first();
  await header.click();
}

/**
 * #617 — L'export du contenu vit désormais sur la page « Exports » du plan,
 * hors des paramètres (réservée aux référents du plan et gestionnaires).
 */
async function exportArborescence(page: any, slug: string): Promise<string> {
  await page.goto(`/plans/${slug}/exports`);
  const exportBtn = page.getByTestId('arbo-export-prefilled');
  await expect(exportBtn).toBeVisible({ timeout: 15000 });
  const [download] = await Promise.all([
    page.waitForEvent('download'),
    exportBtn.click(),
  ]);
  const filePath = await download.path();
  expect(filePath).toBeTruthy();
  return filePath!;
}

test.describe('Import arborescence via Excel', () => {
  test('round-trip export → import remplit un brouillon vide', async ({ superAdminPage }) => {
    const page = superAdminPage;

    // 1. Plan source riche (brouillon avec arborescence).
    const source = await findPlan(page, 'Lac');
    const sourceCount = await enjeuxCount(page, source.id_pg);
    expect(sourceCount, 'le plan source doit avoir une arborescence').toBeGreaterThan(0);

    // Un site du plan source (la création d'un plan exige au moins un site).
    const { data: sourceDetail } = await apiGet(page, `plans/plans/${source.id_pg}/`);
    const siteId = (sourceDetail.sites || [])[0]?.id_site as number;
    expect(siteId, 'le plan source doit avoir un site').toBeTruthy();

    // 2. Export pré-rempli depuis la page Exports → capture du téléchargement.
    const filePath = await exportArborescence(page, source.slug);

    // 3. Brouillon vide cible (API).
    const created = await apiPost(page, 'plans/plans/', {
      nom: `E2E Import ${Date.now()}`,
      rang: 1,
      annee_debut: 2024,
      annee_fin: 2034,
      sites_ids: [siteId],
    });
    expect(created.ok, `création du plan cible: ${created.status}`).toBeTruthy();
    const target = { id_pg: created.data.id_pg as number, slug: created.data.slug as string };

    try {
      expect(await enjeuxCount(page, target.id_pg)).toBe(0);

      // 4. Page Paramètres du plan cible → upload du fichier exporté.
      await page.goto(`/plans/${target.slug}/parametres`);
      const fileInput = page.getByTestId('arbo-import-file');
      await expect(fileInput).toBeAttached({ timeout: 15000 });
      await fileInput.setInputFiles(filePath);

      // La validation (dry-run) se lance : le bouton Importer apparaît et
      // devient actif si le rapport autorise l'import.
      const importBtn = page.getByTestId('arbo-import-submit');
      await expect(importBtn).toBeEnabled({ timeout: 20000 });

      // 5. Import → succès = navigation vers la page des enjeux.
      await Promise.all([
        page.waitForURL(/\/plans\/.+\/enjeux/, { timeout: 20000 }),
        importBtn.click(),
      ]);

      // 6. L'arborescence a bien été créée dans le plan cible.
      expect(await enjeuxCount(page, target.id_pg)).toBe(sourceCount);
    } finally {
      await apiDelete(page, `plans/plans/${target.id_pg}/`).catch(() => undefined);
    }
  });

  test('verrou brouillon : pas d\'upload sur un plan validé', async ({ superAdminPage }) => {
    const page = superAdminPage;
    const validated = await findValidatedPlan(page);

    await page.goto(`/plans/${validated.slug}/parametres`);
    // …le sélecteur de fichier d'import est masqué hors brouillon (#248).
    await expect(page.getByTestId('arbo-import-file')).toHaveCount(0);
    // L'export reste disponible hors brouillon dans la rubrique « Exports » (#617).
    await page.goto(`/plans/${validated.slug}/exports`);
    await expect(page.getByTestId('arbo-export-prefilled')).toBeVisible({ timeout: 15000 });
  });

  test('les boutons « exemple » téléchargent un classeur (arborescence + actions)', async ({ superAdminPage }) => {
    const page = superAdminPage;
    const plan = await findPlan(page, 'Lac');
    await page.goto(`/plans/${plan.slug}/parametres`);

    // Exemple d'arborescence.
    const exArbo = page.getByTestId('arbo-example');
    await expect(exArbo).toBeVisible({ timeout: 15000 });
    const [dlArbo] = await Promise.all([
      page.waitForEvent('download'),
      exArbo.click(),
    ]);
    expect(await dlArbo.path()).toBeTruthy();

    // Exemple d'actions.
    const exActions = page.getByTestId('actions-example');
    await expect(exActions).toBeVisible();
    const [dlActions] = await Promise.all([
      page.waitForEvent('download'),
      exActions.click(),
    ]);
    expect(await dlActions.path()).toBeTruthy();
  });

  test('correction interactive : ouvrir la grille et importer (#9)', async ({ superAdminPage }) => {
    const page = superAdminPage;
    const source = await findPlan(page, 'Lac');
    const { data: sourceDetail } = await apiGet(page, `plans/plans/${source.id_pg}/`);
    const siteId = (sourceDetail.sites || [])[0]?.id_site as number;
    const sourceCount = await enjeuxCount(page, source.id_pg);

    const filePath = await exportArborescence(page, source.slug);

    const created = await apiPost(page, 'plans/plans/', {
      nom: `E2E Grille ${Date.now()}`,
      rang: 1,
      annee_debut: 2024,
      annee_fin: 2034,
      sites_ids: [siteId],
    });
    const target = { id_pg: created.data.id_pg as number, slug: created.data.slug as string };

    try {
      await page.goto(`/plans/${target.slug}/parametres`);
      await page.getByTestId('arbo-import-file').setInputFiles(filePath);
      // Bouton « Corriger dans un tableau » visible dès que les données sont là.
      const correct = page.getByTestId('arbo-correct');
      await expect(correct).toBeVisible({ timeout: 20000 });
      await correct.click();

      // La grille éditable s'affiche puis on importe directement depuis elle.
      await expect(page.getByTestId('import-grid')).toBeVisible();
      await Promise.all([
        page.waitForURL(/\/plans\/.+\/enjeux/, { timeout: 20000 }),
        page.getByTestId('grid-import').click(),
      ]);
      expect(await enjeuxCount(page, target.id_pg)).toBe(sourceCount);
    } finally {
      await apiDelete(page, `plans/plans/${target.id_pg}/`).catch(() => undefined);
    }
  });

  test('mapping : proposé comme « prochainement disponible » (désactivé)', async ({ superAdminPage }) => {
    const page = superAdminPage;
    const draft = await findPlan(page, 'Lac');
    await page.goto(`/plans/${draft.slug}/parametres`);
    await openAdvanced(page);
    const mappingBtn = page.getByTestId('arbo-mapping-open');
    await expect(mappingBtn).toBeVisible({ timeout: 15000 });
    await expect(mappingBtn).toBeDisabled();
  });

  test('modes : le choix ajouter / remplacer apparaît sur un plan déjà rempli', async ({ superAdminPage }) => {
    // Plan brouillon avec arborescence → l'utilisateur doit choisir ajout/remplacement.
    // (Test non destructif : on vérifie seulement l'affichage du choix.)
    const page = superAdminPage;
    const draft = await findPlan(page, 'Lac');
    await page.goto(`/plans/${draft.slug}/parametres`);
    await expect(page.getByTestId('import-mode-choice')).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId('import-mode-replace')).toBeVisible();
  });
});
