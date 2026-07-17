/**
 * E2E — Import Excel de l'arborescence d'un plan de gestion (#478).
 *
 * Round-trip complet PAR L'INTERFACE :
 *   1. sur un plan seedé riche, on clique « Exporter (pré-rempli) » et on
 *      capture le fichier .xlsx téléchargé ;
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

    // 2. Export pré-rempli depuis la page Paramètres → capture du téléchargement.
    await page.goto(`/plans/${source.slug}/parametres`);
    const exportBtn = page.getByTestId('arbo-export-prefilled');
    await expect(exportBtn).toBeVisible({ timeout: 15000 });
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      exportBtn.click(),
    ]);
    const filePath = await download.path();
    expect(filePath).toBeTruthy();

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
      await fileInput.setInputFiles(filePath!);

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
    // L'export (lecture) reste disponible…
    await expect(page.getByTestId('arbo-export-prefilled')).toBeVisible({ timeout: 15000 });
    // …mais le sélecteur de fichier d'import est masqué hors brouillon (#248).
    await expect(page.getByTestId('arbo-import-file')).toHaveCount(0);
  });
});
