/**
 * #692 — En exploration **locale**, chaque donnée affichée nomme sa structure
 * d'origine. Avant, la pastille de provenance n'apparaissait qu'en
 * exploration fédérée : l'utilisateur ne savait pas toujours dans quel mode il
 * cherchait, et une URL partagée s'ouvre d'une instance à l'autre.
 *
 * L'exploration fédérée a ses propres tests (`federation/`, opt-in, banc à
 * trois briques). Ceux-ci visent l'instance de développement, en mode local.
 *
 * Prérequis : seed_testdata (plans validés) et index de recherche construit.
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { apiGet } from '../../helpers/plan.helper';

test.describe('Exploration locale — provenance (#692)', () => {
  test('chaque tuile de plan et chaque ligne de contenu nomme la structure', async ({ referentPage: page }) => {
    const { data } = await apiGet(page, 'exploration/instances/');
    const structure: string = data.instances[0].libelle;
    expect(structure).toBeTruthy();

    await page.goto('/exploration/plans');
    const tuiles = page.getByTestId('exploration-plans-resultats').locator('.exploration-tuile');
    await expect(tuiles.first()).toBeVisible({ timeout: 20000 });
    const nbTuiles = await tuiles.count();
    await expect(
      page.getByTestId('exploration-plans-resultats').getByTestId('exploration-source'),
    ).toHaveCount(nbTuiles);
    await expect(tuiles.first().getByTestId('exploration-source')).toContainText(structure);

    await page.goto('/exploration/contenus');
    const lignes = page.getByTestId('exploration-contenus-resultats').locator('.exploration-tuile');
    await expect(lignes.first()).toBeVisible({ timeout: 20000 });
    const nbLignes = await lignes.count();
    await expect(
      page.getByTestId('exploration-contenus-resultats').getByTestId('exploration-source'),
    ).toHaveCount(nbLignes);
  });

  test('le filtre « Structure d\'origine » reste visible, en lecture seule', async ({ referentPage: page }) => {
    const { data } = await apiGet(page, 'exploration/instances/');
    test.skip(data.instances.length > 1, 'Instance relayée vers le hub : plusieurs structures.');

    await page.goto('/exploration/contenus');
    await expect(page.getByTestId('exploration-instances-seule'))
      .toContainText(data.instances[0].libelle, { timeout: 20000 });
  });

  test('la fiche annonce sa provenance en tête et dans le fil d\'Ariane', async ({ referentPage: page }) => {
    const { data } = await apiGet(page, 'exploration/plans/', { page_size: '1' });
    const plan = data.results[0];
    test.skip(!plan, 'Aucun plan validé indexé.');

    await page.goto(`/exploration/plans/${plan.slug}`);
    await expect(page.getByTestId('fiche-provenance')).toContainText(plan.instance_libelle, { timeout: 20000 });
    await expect(page.getByTestId('fiche-fil-structure')).toHaveText(plan.instance_libelle);
  });
});
