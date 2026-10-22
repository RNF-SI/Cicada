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

/**
 * #720 — plan « Ventilation validée — <mode> » du jeu d'essai (seeder
 * `ventilation_plans`) : validé, donc saisie du suivi ouverte, et programmé de
 * façon identique dans chaque mode. Cibler ce plan par son nom rend les tests
 * indépendants de « dernier plan validé modifié », qui change avec le seed.
 */
async function findVentilationValidee(page: any, libelleMode: string) {
  const nom = `Ventilation validée — ${libelleMode}`;
  const { data } = await apiGet(page, 'plans/plans/', { search: 'Ventilation validée', page_size: '50' });
  const plan = (data.results || data).find((p: any) => p.nom === nom);
  expect(plan, `plan « ${nom} » absent : relancer seed_testdata`).toBeTruthy();
  expect(plan.statut).toBe('valide');
  return plan;
}

/** Détail d'une action du plan, retrouvée par la fin de son code (« -CS1 »…). */
async function findOperationByCode(page: any, planId: number, codeSuffix: string) {
  const { data } = await apiGet(page, `plans/operations/by-plan/${planId}/`);
  for (const group of data.groups || []) {
    for (const o of group.operations || []) {
      if (o.code_operation?.endsWith(codeSuffix)) {
        const { data: detail } = await apiGet(page, `plans/operations/${o.id_operation}/`);
        return detail;
      }
    }
  }
  throw new Error(`Action *${codeSuffix} introuvable sur le plan ${planId}`);
}

/** Cellule de l'année affichée (colonne active) d'une ligne du tableau, par libellé. */
function activeCell(page: any, scope: any, libelle: string) {
  return scope.locator('tr', { has: page.locator('td.col-field', { hasText: libelle }) })
    .locator('td.active');
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

      // #589 — plus de bouton « Modifier l'action » depuis le suivi : on
      // consulte l'action via sa fiche, on ne l'édite pas d'ici.
      await expect(referentPage.locator('.hero-actions')).not.toContainText(/Modifier l'action/);
      await expect(referentPage.locator('.hero-actions')).toContainText(/Voir la fiche action/);
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
    // #379 — la saisie de réalisation n'est éditable que sur un plan VALIDÉ
    // (le formulaire est verrouillé en lecture seule sur un brouillon). On cible
    // donc une opération seedée d'un plan validé (pas de création possible non
    // plus sur un plan validé, #248).
    const plan = await findVentilationValidee(referentPage, 'aucune ventilation');
    const op = await findOperationByCode(referentPage, plan.id_pg, '-CS1');
    expect(op.ventilation_mode).toBe('none');
    const oa = op.operation_annees[0];

    const commentaires = 'textarea[formcontrolname="commentaires"]';
    await referentPage.goto(
      `/plans/${plan.slug}/suivi-actions/saisie/${op.id_operation}/${oa.annee}`,
    );

    // Wait for the form to be ready
    await referentPage.waitForSelector('.realisation-table, .saisie-card');

    // Capture la valeur d'origine pour restaurer la donnée seedée après le test.
    const original = await referentPage.locator(commentaires).inputValue();

    // #762 — l'année seedée est déjà enregistrée : elle s'ouvre en lecture.
    const modifier = referentPage.locator('.saisie-toolbar').getByRole('button', { name: 'Modifier' });
    await modifier.click();

    // Commentaires : unique marker so we can verify after reload
    const marker = `Test E2E ${Date.now()}`;
    await referentPage.locator(commentaires).fill(marker);

    // Click Save (« Enregistrer » exact — distinct de « Enregistrer et quitter »)
    await referentPage.getByRole('button', { name: 'Enregistrer', exact: true }).click();

    // Snackbar success
    await expect(referentPage.getByText(/Modifications enregistrées/i)).toBeVisible({ timeout: 6000 });

    // Reload + verify the textarea retains the marker
    await referentPage.reload();
    await referentPage.waitForSelector(commentaires);
    await expect(referentPage.locator(commentaires)).toHaveValue(marker);

    // Restaure la valeur d'origine pour ne pas polluer la donnée seedée.
    await modifier.click();
    await referentPage.locator(commentaires).fill(original);
    await referentPage.getByRole('button', { name: 'Enregistrer', exact: true }).click();
    await expect(referentPage.getByText(/Modifications enregistrées/i)).toBeVisible({ timeout: 6000 });
  });

  test('renders per-organisme sub-tables for by_org_type operations', async ({ referentPage }) => {
    const plan = await findVentilationValidee(referentPage, 'par organisme et type de budget');
    const opVentilated = await findOperationByCode(referentPage, plan.id_pg, '-CS1');
    expect(opVentilated.ventilation_mode).toBe('by_org_type');

    const oa = opVentilated.operation_annees.find((o: any) => o.organismes?.length);
    await referentPage.goto(
      `/plans/${plan.slug}/suivi-actions/saisie/${opVentilated.id_operation}/${oa.annee}`,
    );

    // Une ligne d'en-tête par organisme + une ligne TOTAL (tableau de réalisation).
    // Ce test visait l'ancien gabarit `.org-block` et passait inaperçu : il
    // était toujours ignoré faute d'action « by_org_type » sur le plan Camargue.
    const total = referentPage.locator('tr.total-header-row');
    await expect(total).toBeVisible({ timeout: 15000 });
    await expect(referentPage.locator('tr.org-header-row:not(.total-header-row)'))
      .toHaveCount(oa.organismes.length);

    // Investissement présent (mode by_org_type)
    await expect(referentPage.getByText(/Budget investissement/i).first()).toBeVisible();
  });

  test('#720 — ventilation maximale : la saisie reprend la programmation de la fiche action', async ({ referentPage }) => {
    // Action CS du plan validé « par organisme, type de budget et type de
    // poste », coût salarial SAISI (#600). Programmation par an (seeder) :
    //   organisme principal : salarial 1 500 (5 j × 300) + prestataire 2 500 + autres 800 = 4 800
    //   organisme secondaire : salarial 1 600 (20 j × 80) + stage 1 200            = 2 800
    // Suivi de l'année − 1 saisi à 55 % : jours et coûts réalisés × 0,55
    //   principal 825 + 1 375 + 440 = 2 640 ; secondaire 880 + 660 = 1 540.
    const plan = await findVentilationValidee(referentPage, 'par organisme, type de budget et type de poste');
    const op = await findOperationByCode(referentPage, plan.id_pg, '-CS1');
    expect(op.ventilation_mode).toBe('by_org_type_poste');
    expect(op.cout_salarial_auto).toBe(false);

    const annee = new Date().getFullYear() - 1;
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions/saisie/${op.id_operation}/${annee}`);
    const prevu = activeCell(referentPage, referentPage, 'Budget total prévu (€)');
    await expect(prevu).toHaveText(/^7\s600\s€$/, { timeout: 15000 });
    await expect(activeCell(referentPage, referentPage, 'Budget total réalisé (€)')).toHaveText(/^4\s180\s€$/);

    // Même chose organisme par organisme (ordre des organismes indifférent).
    const ogPrev = (await activeCell(referentPage, referentPage, 'Budget total OG prévu (€)').allTextContents())
      .map((t: string) => t.replace(/\s/g, ''));
    expect(ogPrev.sort()).toEqual(['2800€', '4800€']);
    const ogReal = (await activeCell(referentPage, referentPage, 'Budget total OG réalisé (€)').allTextContents())
      .map((t: string) => t.replace(/\s/g, ''));
    expect(ogReal.sort()).toEqual(['1540€', '2640€']);
  });

  test('#762 — changer d\'année ne reporte pas la saisie d\'une autre année', async ({ referentPage }) => {
    // Action CS du plan validé « par type de budget et type de poste » : temps de
    // travail décliné par poste, programmé chaque année. Année − 2 : suivi saisi ;
    // année + 1 : jamais saisie. Les lignes de temps réalisé de l'année + 1
    // doivent être vides, et non reprendre les jours de l'année − 2.
    const plan = await findVentilationValidee(referentPage, 'par type de budget et type de poste');
    const op = await findOperationByCode(referentPage, plan.id_pg, '-CS1');
    const y = new Date().getFullYear();
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions/saisie/${op.id_operation}/${y - 2}`);

    const jours = referentPage.locator('.rh-table input[formcontrolname="jours"]');
    await expect(jours.first()).not.toHaveValue('', { timeout: 15000 });

    await referentPage.locator('.year-tab', { hasText: String(y + 1) }).click();
    await expect(referentPage.locator('.year-tab.active')).toContainText(String(y + 1));
    expect(await jours.count()).toBeGreaterThan(0);
    for (const v of await jours.evaluateAll((els: HTMLInputElement[]) => els.map(e => e.value))) {
      expect(v).toBe('');
    }
  });

  test('#762 — année enregistrée en lecture, « Modifier » et « Effacer » en haut à droite', async ({ referentPage }) => {
    const plan = await findVentilationValidee(referentPage, 'aucune ventilation');
    const op = await findOperationByCode(referentPage, plan.id_pg, '-CS1');
    const y = new Date().getFullYear();
    const niveau = referentPage.locator('select[formcontrolname="id_niveau_realisation"]');
    const toolbar = referentPage.locator('.saisie-toolbar');
    const enregistrer = referentPage.getByRole('button', { name: 'Enregistrer', exact: true });

    // Année − 2 : saisie enregistrée → lecture.
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions/saisie/${op.id_operation}/${y - 2}`);
    await expect(toolbar.getByRole('button', { name: 'Modifier' })).toBeVisible({ timeout: 15000 });
    await expect(toolbar.getByRole('button', { name: `Effacer la saisie de ${y - 2}` })).toBeVisible();
    await expect(niveau).toBeDisabled();
    await expect(enregistrer).toHaveCount(0);

    // « Modifier » repasse en saisie.
    await toolbar.getByRole('button', { name: 'Modifier' }).click();
    await expect(niveau).toBeEnabled();
    await expect(enregistrer).toBeVisible();
    await expect(toolbar.getByRole('button', { name: 'Modifier' })).toHaveCount(0);

    // Année + 1, jamais saisie : directement en saisie, sans « Modifier » ni « Effacer ».
    await referentPage.locator('.year-tab', { hasText: String(y + 1) }).click();
    await expect(niveau).toBeEnabled();
    await expect(niveau).toHaveValue(/^(0: null|)$/);
    await expect(toolbar).toHaveCount(0);

    // Retour sur l'année − 2 : de nouveau en lecture.
    await referentPage.locator('.year-tab', { hasText: String(y - 2) }).click();
    await expect(niveau).toBeDisabled();
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
