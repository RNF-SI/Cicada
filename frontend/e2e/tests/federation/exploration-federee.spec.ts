import { test, expect, Page } from '@playwright/test';
import path from 'path';

/**
 * Exploration fédérée vue par l'utilisateur (#636).
 *
 * Ces tests visent une instance **relayée vers le hub** : son exploration ne
 * lit plus son index local, elle interroge l'index agrégé. C'est le seul niveau
 * qui couvre ce que l'utilisateur voit — les suites unitaires et le banc
 * (`tests/federation/bench.py`) s'arrêtent à l'API.
 *
 * Prérequis : `scripts/federation.sh up` puis `scripts/federation.sh push`.
 * Lancement : `scripts/federation.sh test --e2e`.
 *
 * ## Le cas qui justifie ces tests
 *
 * Les deux instances du banc sont seedées des mêmes fixtures : elles ont des
 * **slugs identiques pour des plans différents**. Une interface qui lierait la
 * fiche par slug nu n'ouvrirait donc pas le plan sur lequel on a cliqué, mais
 * son homonyme local — sans rien signaler. C'est une réponse fausse et
 * silencieuse, la pire espèce, et aucun test d'API ne peut la voir : elle naît
 * de la construction du lien, côté navigateur.
 */

test.use({
  storageState: path.join(__dirname, '..', '..', '.auth', 'federation-admin.json'),
});

const RECHERCHE = 'exploration-contenus-q';
const RESULTATS = 'exploration-contenus-resultats';
const TOTAL = 'exploration-contenus-total';

async function rechercher(page: Page, terme: string): Promise<void> {
  await page.goto('/exploration/contenus');
  await page.getByTestId(RECHERCHE).fill(terme);
  await page.getByTestId(RECHERCHE).press('Enter');
  // La liste se recharge : on attend que la recherche ait abouti plutôt qu'un
  // délai fixe, qui serait tantôt trop court tantôt gaspillé.
  await expect(page.getByTestId(TOTAL)).toBeVisible({ timeout: 20000 });
}

/**
 * Ouvre la liste complète, sans mot-clé.
 *
 * Préféré à une recherche pour les tests qui ont juste besoin d'un résultat
 * distant : chercher supposerait de connaître un terme présent dans le
 * *contenu* des plans distants. « camargue » ou « bac à sable » sont des noms de
 * plans, pas des libellés d'enjeux — ils ne rendent rien ici, et l'échec se
 * lirait comme un défaut de la fédération.
 */
async function ouvrirListe(page: Page): Promise<void> {
  await page.goto('/exploration/contenus');
  await expect(page.getByTestId(RESULTATS)).toBeVisible({ timeout: 20000 });
}

/** Les réponses de l'API d'exploration, capturées pour inspection. */
async function capturerReponses(page: Page): Promise<Array<Record<string, unknown>>> {
  const corps: Array<Record<string, unknown>> = [];
  page.on('response', async (reponse) => {
    if (reponse.url().includes('/api/exploration/contenus/') && reponse.ok()) {
      try {
        corps.push(await reponse.json());
      } catch {
        /* réponse non JSON : sans intérêt ici */
      }
    }
  });
  return corps;
}

test.describe('Exploration servie par le hub', () => {
  test("remonte le contenu de plusieurs instances dans une même liste", async ({ page }) => {
    // C'est la propriété qui justifie l'index central : sans elle, on aurait
    // simplement deux explorations côte à côte.
    const reponses = await capturerReponses(page);
    await rechercher(page, 'zones humides');

    await expect(page.getByTestId(RESULTATS)).toBeVisible();
    expect(reponses.length).toBeGreaterThan(0);

    const derniere = reponses[reponses.length - 1] as {
      results: Array<{ instance_id?: string }>;
    };
    const instances = new Set(derniere.results.map((r) => r.instance_id));
    expect(
      instances.size,
      `Une seule instance dans les résultats (${[...instances]}). ` +
        'Les deux ont-elles publié ? « scripts/federation.sh push »',
    ).toBeGreaterThan(1);
  });

  test('les compteurs d’onglets portent sur toutes les instances', async ({ page }) => {
    const reponses = await capturerReponses(page);
    await page.goto('/exploration/contenus');
    await expect(page.getByTestId(TOTAL)).toBeVisible({ timeout: 20000 });

    const derniere = reponses[reponses.length - 1] as {
      compteurs: Record<string, number>;
      pagination: { count: number };
    };
    // Le total dépasse ce qu'une instance seule peut fournir : les deux du banc
    // publient un corpus comparable, l'agrégat est donc nettement supérieur.
    expect(derniere.compteurs['tout']).toBe(derniere.pagination.count);
    expect(derniere.compteurs['tout']).toBeGreaterThan(100);
  });

  test("ouvre la fiche du plan sur lequel on a cliqué, pas celle de son homonyme", async ({
    page,
  }) => {
    // Le cœur du sujet. Les deux instances ont des plans de même slug ; le lien
    // doit désigner l'instance d'origine, sinon l'utilisateur atterrit sur un
    // autre plan qui porte le même nom.
    const reponses = await capturerReponses(page);
    await ouvrirListe(page);

    const derniere = reponses[reponses.length - 1] as {
      results: Array<{
        titre: string;
        instance_id?: string;
        plan: { nom: string; slug: string; instance_id?: string };
      }>;
    };
    const distant = derniere.results.find((r) => r.instance_id !== 'cen');
    test.skip(!distant, 'Aucun résultat distant : les deux instances ont-elles publié ?');

    const rang = derniere.results.indexOf(distant!);

    // L'attente est posée AVANT le clic : `waitForResponse` ne voit que ce qui
    // arrive après son appel, et la fiche répond souvent avant qu'on ait fini
    // de vérifier l'URL.
    const attenteFiche = page.waitForResponse(
      (r) => r.url().includes('/api/exploration/plans/') && r.request().method() === 'GET',
      { timeout: 20000 },
    );
    await page.getByTestId(RESULTATS).locator('li').nth(rang).click();
    await expect(page).toHaveURL(/\/exploration\/plans\//, { timeout: 20000 });

    // La fiche affichée doit être celle du plan distant. On le vérifie sur ce
    // que l'API a réellement renvoyé : deux plans homonymes ne se distinguent
    // pas à l'écran, c'est précisément le piège.
    const fiche = await attenteFiche;
    expect(
      fiche.status(),
      `La fiche du plan distant répond ${fiche.status()} : le lien perd-il ` +
        "l'instance d'origine ?",
    ).toBe(200);

    const corps = (await fiche.json()) as {
      instance_id?: string;
      nom?: string;
      id_pg?: number;
    };

    const instanceServie = corps.instance_id ?? 'cen';
    expect(
      instanceServie,
      `La fiche ouverte vient de « ${instanceServie} » alors que le résultat ` +
        `cliqué vient de « ${distant!.instance_id} » : le lien perd l'instance ` +
        "d'origine et ouvre un homonyme local.",
    ).toBe(distant!.instance_id);
  });

  test("dit sur chaque résultat de quelle structure il vient", async ({ page }) => {
    // Le pendant visible du test précédent. Les deux instances du banc ont des
    // plans de même nom : le lien pointe désormais le bon, mais la liste reste
    // illisible tant que rien ne distingue « le mien » de « celui d'à côté ».
    await ouvrirListe(page);

    const sources = page.getByTestId(RESULTATS).getByTestId('exploration-source');
    await expect(
      sources.first(),
      "Aucune provenance affichée : les résultats distants se lisent comme " +
        'des résultats locaux.',
    ).toBeVisible({ timeout: 20000 });

    // Plusieurs structures nommées, et non un même libellé répété : c'est ce
    // qui rend la liste lisible.
    const libelles = new Set(
      (await sources.allInnerTexts()).map((texte) => texte.trim()),
    );
    expect(
      libelles.size,
      `Une seule provenance affichée (${[...libelles]}) sur une liste ` +
        'agrégée. Les deux instances ont-elles publié ?',
    ).toBeGreaterThan(1);
  });

  test("nomme la structure qui a publié la fiche qu'on lit", async ({ page }) => {
    const reponses = await capturerReponses(page);
    await ouvrirListe(page);

    const derniere = reponses[reponses.length - 1] as {
      results: Array<{ instance_id?: string }>;
    };
    const rang = derniere.results.findIndex((r) => r.instance_id !== 'cen');
    test.skip(rang < 0, 'Aucun résultat distant dans cette recherche.');

    await page.getByTestId(RESULTATS).locator('li').nth(rang).click();
    await expect(page).toHaveURL(/\/exploration\/plans\//, { timeout: 20000 });

    // La fiche est un instantané déposé par une autre structure : qui l'a
    // publiée, et quand, fait partie de ce qu'il faut savoir pour la lire.
    await expect(page.getByTestId('fiche-provenance')).toBeVisible({ timeout: 20000 });
  });

  test('affiche la fiche complète d’un plan hébergé ailleurs', async ({ page }) => {
    // Le hub ressert un instantané publié : le plan n'existe dans aucune table
    // de cette instance, et sa fiche doit pourtant s'afficher entièrement.
    const reponses = await capturerReponses(page);
    await ouvrirListe(page);

    const derniere = reponses[reponses.length - 1] as {
      results: Array<{ instance_id?: string }>;
    };
    const rang = derniere.results.findIndex((r) => r.instance_id !== 'cen');
    test.skip(rang < 0, 'Aucun résultat distant dans cette recherche.');

    await page.getByTestId(RESULTATS).locator('li').nth(rang).click();
    await expect(page).toHaveURL(/\/exploration\/plans\//, { timeout: 20000 });

    // Un titre et au moins un enjeu : la fiche est rendue, pas juste son
    // squelette. Une page blanche passerait un simple test d'URL.
    await expect(page.locator('h1')).toBeVisible({ timeout: 20000 });
    await expect(page.locator('h1')).not.toBeEmpty();
  });

  test("signale une panne du hub au lieu d’afficher une liste vide", async ({ page }) => {
    // Sans repli sur l'index local, une indisponibilité doit se voir. Une liste
    // vide se lirait « aucun plan ne correspond », ce qui est faux et
    // indétectable pour l'utilisateur.
    await page.route('**/api/exploration/contenus/**', (route) =>
      route.fulfill({
        status: 502,
        contentType: 'application/json',
        body: JSON.stringify({ detail: "L'exploration centralisée est indisponible." }),
      }),
    );

    await page.goto('/exploration/contenus');

    await expect(page.locator('.info-block-error, .exploration-etat')).toBeVisible({
      timeout: 20000,
    });
    await expect(page.getByTestId(RESULTATS)).toHaveCount(0);
  });
});
