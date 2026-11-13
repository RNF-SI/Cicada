/**
 * #794 — Planification annuelle ajustée : du tableau de l'année au suivi.
 *
 * Jeu d'essai (seeder `ventilation_plans`) : dans les plans « Ventilation
 * validée — … », l'année en cours est ajustée — CS1 revue à +10 % (7 600 →
 * 8 360 €, septembre-octobre), IP1 reportée à l'année suivante, PA1 à revoir.
 * Ce qu'un test ajuste (PA1) est remis au plan de gestion à la fin.
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { apiDelete, apiGet } from '../../helpers/plan.helper';

const ANNEE = new Date().getFullYear();
const NOMBRE = (texte: string) => texte.replace(/\s/g, '');

async function planValide(page: any, libelleMode: string) {
  const nom = `Ventilation validée — ${libelleMode}`;
  const { data } = await apiGet(page, 'plans/plans/', { search: 'Ventilation validée', page_size: '50' });
  const plan = (data.results || data).find((p: any) => p.nom === nom);
  expect(plan, `plan « ${nom} » absent : relancer seed_testdata`).toBeTruthy();
  return plan;
}

async function action(page: any, planId: number, code: string) {
  const { data } = await apiGet(page, `plans/planification-annuelle/plan/${planId}/`, { annee: String(ANNEE) });
  const ligne = data.actions.find((a: any) => a.code === code);
  expect(ligne, `action ${code} absente du tableau`).toBeTruthy();
  return ligne;
}

test.describe('#794 — Ajustement de la planification annuelle', () => {
  test('le tableau de l\'année distingue le plan de gestion de l\'ajusté', async ({ referentPage }) => {
    const plan = await planValide(referentPage, 'aucune ventilation');
    await referentPage.goto(`/plans/${plan.slug}/planification-annuelle?annee=${ANNEE}`);

    await expect(referentPage.getByTestId('planification-revue'))
      .toContainText(`2 / 3 actions revues pour ${ANNEE}`, { timeout: 15000 });
    const cs1 = referentPage.locator('tr', { hasText: 'Suivi annuel des habitats humides' });
    await expect(cs1).toContainText('Planifiée');
    expect(NOMBRE(await cs1.textContent() ?? '')).toContain('7600€');
    expect(NOMBRE(await cs1.textContent() ?? '')).toContain('8360€');
    const ip1 = referentPage.locator('tr', { hasText: 'Restauration hydraulique' });
    await expect(ip1).toContainText(`Reportée en ${ANNEE + 1}`);

    // Filtre « À revoir » : seule PA1 reste.
    await referentPage.getByRole('button', { name: /À revoir/ }).click();
    await expect(referentPage.locator('[data-testid^="planification-ligne-"]')).toHaveCount(1);
  });

  test('ajuster une action la marque revue, sans toucher au plan de gestion', async ({ referentPage }) => {
    const plan = await planValide(referentPage, 'aucune ventilation');
    const pa1 = await action(referentPage, plan.id_pg, 'PA1');
    try {
      await referentPage.goto(`/plans/${plan.slug}/planification-annuelle/${pa1.id_operation}/${ANNEE}`);
      const budget = referentPage.getByTestId('champ-budget');
      await expect(budget).toHaveValue(/5300/, { timeout: 15000 });
      await budget.fill('6100');
      await expect(referentPage.getByTestId('ajustement-total')).toContainText('6');
      await referentPage.getByTestId('ajustement-enregistrer').click();
      await expect(referentPage.getByText('Ajustement enregistré')).toBeVisible();
      // Retour 13/11 — enregistrée, la saisie se fige ; « Modifier » la rouvre.
      await expect(budget).toBeDisabled();
      await referentPage.getByTestId('ajustement-modifier').click();
      await expect(budget).toBeEnabled();

      const apres = await action(referentPage, plan.id_pg, 'PA1');
      expect([Number(apres.pg.budget), Number(apres.ajuste.budget), apres.revue]).toEqual([5300, 6100, true]);
      await referentPage.goto(`/plans/${plan.slug}/planification-annuelle?annee=${ANNEE}`);
      await expect(referentPage.getByTestId('planification-revue'))
        .toContainText(`3 / 3 actions revues pour ${ANNEE}`, { timeout: 15000 });
    } finally {
      await apiDelete(referentPage, `plans/planification-annuelle/operation/${pa1.id_operation}/${ANNEE}/`);
    }
  });

  test('l\'année se détaille par type de coût sans changer son total', async ({ referentPage }) => {
    const plan = await planValide(referentPage, 'aucune ventilation');
    const pa1 = await action(referentPage, plan.id_pg, 'PA1');
    await referentPage.goto(`/plans/${plan.slug}/planification-annuelle/${pa1.id_operation}/${ANNEE}`);
    await expect(referentPage.getByTestId('champ-budget')).toHaveValue(/5300/, { timeout: 15000 });
    await expect(referentPage.getByTestId('budget-total')).toContainText('5');
    await referentPage.getByTestId('ajustement-reglages-budget')
      .getByText('Déclinaison par type de coût').click();
    // Le montant saisi passe en « autres coûts », le total ne bouge pas.
    await expect(referentPage.getByTestId('champ-autre_cout')).toHaveValue(/5300/);
    await expect(referentPage.getByTestId('champ-budget')).toHaveCount(0);
    expect(NOMBRE(await referentPage.getByTestId('budget-total').textContent() ?? '')).toContain('5300€5300€');
    // Rien n'est enregistré tant qu'on n'enregistre pas.
    const apres = await action(referentPage, plan.id_pg, 'PA1');
    expect(apres.ajustee).toBe(false);
  });

  test('le report montre son aperçu avant d\'écrire quoi que ce soit', async ({ referentPage }) => {
    const plan = await planValide(referentPage, 'aucune ventilation');
    const pa1 = await action(referentPage, plan.id_pg, 'PA1');
    await referentPage.goto(`/plans/${plan.slug}/planification-annuelle/${pa1.id_operation}/${ANNEE}`);
    await referentPage.getByTestId('ajustement-reporter').click({ timeout: 15000 });
    await referentPage.getByTestId('report-voir-apercu').click();
    const apercu = referentPage.getByTestId('report-apercu');
    await expect(apercu).toContainText(`Reportée en ${ANNEE + 1}`);
    await expect(referentPage.getByTestId('report-confirmer')).toBeVisible();
    await referentPage.getByRole('button', { name: 'Annuler' }).click();
    // Rien n'a été écrit.
    const apres = await action(referentPage, plan.id_pg, 'PA1');
    expect(apres.ajustee).toBe(false);
  });

  test('le suivi des actions lit le prévu ajusté, en regard du plan', async ({ referentPage }) => {
    const plan = await planValide(referentPage, 'aucune ventilation');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions?tab=budget`);
    const table = referentPage.locator('.agg-table');
    await expect(table.locator('tr.sous-colonnes th').first()).toHaveText('Prévu PG', { timeout: 15000 });
    await expect(table.locator('tr.sous-colonnes th').nth(1)).toHaveText('Prévu ajusté');
    const cs1 = table.locator('tr', { hasText: 'Suivi annuel des habitats humides' });
    const cellules = cs1.locator('td.col-agg');
    expect(NOMBRE(await cellules.nth(0).textContent() ?? '')).toBe('7600€');
    expect(NOMBRE(await cellules.nth(1).textContent() ?? '')).toBe('8360€');
  });

  test('la saisie du suivi propose « Reportée » pour une année reportée', async ({ referentPage }) => {
    const plan = await planValide(referentPage, 'aucune ventilation');
    const ip1 = await action(referentPage, plan.id_pg, 'IP1');
    await referentPage.goto(`/plans/${plan.slug}/suivi-actions/saisie/${ip1.id_operation}/${ANNEE}`);
    await expect(referentPage.getByTestId('suivi-ajustement'))
      .toContainText(`reportée en ${ANNEE + 1}`, { timeout: 15000 });
    await expect(referentPage.getByTestId('suivi-reporte-propose')).toBeVisible();
    await expect(referentPage.locator('select[formcontrolname="id_niveau_realisation"] option:checked'))
      .toHaveText('Reportée');
  });

  test('un utilisateur lié au plan consulte sans ajuster', async ({ userRnfPage }) => {
    const plan = await planValide(userRnfPage, 'aucune ventilation');
    await userRnfPage.goto(`/plans/${plan.slug}/planification-annuelle?annee=${ANNEE}`);
    await expect(userRnfPage.getByTestId('planification-lecture-seule')).toBeVisible({ timeout: 15000 });
    await expect(userRnfPage.getByTestId('planification-exporter')).toHaveCount(0);
  });
});
