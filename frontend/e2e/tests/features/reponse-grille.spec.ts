/**
 * E2E — Indicateurs de réponse en format GRILLE (#452 / #464 / #465).
 *
 * Stratégie : la DÉFINITION de la grille est pilotée par API (l'endpoint
 * `create-indicator` accepte désormais `format_metrique` + les champs de grille),
 * ce qui est déterministe ; on vérifie ensuite dans l'UI :
 *  - l'exposition backend de la grille sur l'opération,
 *  - la SAISIE type-aware (le vrai correctif) : un <select> des libellés pour
 *    une grille TEXTE (#464), un <select> des valeurs pour une grille CHIFFRE,
 *  - la DÉFINITION : à l'ouverture du formulaire d'action, la case « grille »
 *    est cochée et l'éditeur de grille (app-metrique-form) est affiché.
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { OperationFormPage } from '../../pages/operation-form.page';
import {
  findPlan,
  findFirstMetrique,
  apiGet,
  apiPost,
  apiDelete,
} from '../../helpers/plan.helper';
import type { Page } from '@playwright/test';

/** Résout l'id d'une nomenclature par type + mnémonique. */
async function nomenclatureId(page: Page, type: string, mnemonique: string): Promise<number | null> {
  const res = await apiGet(page, 'nomenclatures/', { type });
  const list = (res.data?.results || res.data || []) as Array<{ id_nomenclature: number; mnemonique: string }>;
  return list.find(n => n.mnemonique === mnemonique)?.id_nomenclature ?? null;
}

/** Crée une opération brouillon liée à une métrique (prérequis create-indicator). */
async function createOperation(page: Page, planId: number): Promise<any> {
  const met = await findFirstMetrique(page, planId);
  const res = await apiPost(page, 'plans/operations/', {
    libelle: `E2E Réponse grille ${Date.now()}`,
    annee_min: 2025,
    annee_max: 2025,
    ventilation_mode: 'none',
    metrique_ids: [met.id_metrique],
    operation_annees: [{ annee: 2025, periodicite: true, budget: 1000, etp: 1 }],
  });
  return res.data;
}

test.describe('Indicateurs de réponse — format grille (#452/#464/#465)', () => {
  test('saisie TEXTE en grille : menu déroulant des libellés (#464)', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const grilleId = await nomenclatureId(referentPage, 'FORMAT_METRIQUE', 'GRILLE');
    const texteId = await nomenclatureId(referentPage, 'TYPE_METRIQUE', 'TEXTE');
    test.skip(!grilleId || !texteId, 'Nomenclatures FORMAT_METRIQUE/TYPE_METRIQUE absentes');

    const op = await createOperation(referentPage, plan.id_pg);
    const opId = op.id_operation as number;
    const annee = op.operation_annees[0].annee as number;
    const labels = ['Très mauvais', 'Mauvais', 'Moyen', 'Bon', 'Très bon'];

    try {
      // Définition de la grille TEXTE via API (déterministe).
      const created = await apiPost(referentPage, `plans/operations/${opId}/create-indicator/`, {
        nom_indicateur: 'Satisfaction usagers',
        nom_metrique: 'Niveau de satisfaction',
        type_metrique_id: texteId,
        format_metrique: grilleId,
        score_1_label: labels[0],
        score_2_label: labels[1],
        score_3_label: labels[2],
        score_4_label: labels[3],
        score_5_label: labels[4],
      });
      expect(created.ok, JSON.stringify(created.data)).toBeTruthy();

      // Exposition backend : la métrique de réponse porte le format + la grille.
      const opRes = await apiGet(referentPage, `plans/operations/${opId}/`);
      const repMet = (opRes.data.metriques || []).find(
        (m: any) => m.indicateur_type === 'REPONSE',
      );
      expect(repMet).toBeTruthy();
      expect(repMet.format_metrique_mnemonique).toBe('GRILLE');
      expect(repMet.type_metrique_mnemonique).toBe('TEXTE');
      expect(repMet.score_3_label).toBe('Moyen');

      // Saisie type-aware : un <select> des libellés est rendu (et non un input texte).
      await referentPage.goto(`/plans/${plan.slug}/suivi-actions/saisie/${opId}/${annee}`);
      const section = referentPage.locator('#indicateurs-reponse');
      await expect(section).toBeVisible({ timeout: 15000 });

      const select = section.locator('select');
      await expect(select.first()).toBeVisible({ timeout: 10000 });

      // Les 5 libellés de la grille figurent parmi les options.
      const optionTexts = (await section.locator('select option').allInnerTexts())
        .map(t => t.trim());
      for (const lbl of labels) {
        expect(optionTexts).toContain(lbl);
      }
    } finally {
      await apiDelete(referentPage, `plans/operations/${opId}/`);
    }
  });

  test('saisie CHIFFRE en grille : menu déroulant des valeurs (#465)', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const grilleId = await nomenclatureId(referentPage, 'FORMAT_METRIQUE', 'GRILLE');
    const chiffreId = await nomenclatureId(referentPage, 'TYPE_METRIQUE', 'CHIFFRE');
    test.skip(!grilleId || !chiffreId, 'Nomenclatures absentes');

    const op = await createOperation(referentPage, plan.id_pg);
    const opId = op.id_operation as number;
    const annee = op.operation_annees[0].annee as number;

    try {
      const created = await apiPost(referentPage, `plans/operations/${opId}/create-indicator/`, {
        nom_indicateur: 'Effectifs',
        nom_metrique: 'Nombre de couples',
        type_metrique_id: chiffreId,
        format_metrique: grilleId,
        score_1_val: 10,
        score_2_val: 20,
        score_3_val: 30,
        score_4_val: 40,
        score_5_val: 50,
      });
      expect(created.ok, JSON.stringify(created.data)).toBeTruthy();

      await referentPage.goto(`/plans/${plan.slug}/suivi-actions/saisie/${opId}/${annee}`);
      const section = referentPage.locator('#indicateurs-reponse');
      await expect(section).toBeVisible({ timeout: 15000 });
      await expect(section.locator('select').first()).toBeVisible({ timeout: 10000 });

      const optionTexts = (await section.locator('select option').allInnerTexts())
        .map(t => t.trim());
      for (const v of ['10', '30', '50']) {
        expect(optionTexts).toContain(v);
      }
    } finally {
      await apiDelete(referentPage, `plans/operations/${opId}/`);
    }
  });

  test('définition : la case « grille » est cochée et l’éditeur de grille s’affiche', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const grilleId = await nomenclatureId(referentPage, 'FORMAT_METRIQUE', 'GRILLE');
    const texteId = await nomenclatureId(referentPage, 'TYPE_METRIQUE', 'TEXTE');
    test.skip(!grilleId || !texteId, 'Nomenclatures absentes');

    const op = await createOperation(referentPage, plan.id_pg);
    const opId = op.id_operation as number;

    try {
      await apiPost(referentPage, `plans/operations/${opId}/create-indicator/`, {
        nom_indicateur: 'Indicateur grille',
        nom_metrique: 'Métrique grille',
        type_metrique_id: texteId,
        format_metrique: grilleId,
        score_1_label: 'Bas',
        score_5_label: 'Haut',
      });

      const formPage = new OperationFormPage(referentPage);
      await formPage.gotoEdit(plan.slug, opId);
      await formPage.waitForForm();

      // La section « Indicateur(s) de réponse » est dépliée par défaut : on
      // amène la case en vue sans la (re)basculer.
      const checkbox = referentPage.locator('app-checkbox')
        .filter({ hasText: /grille de scoring/i }).first();
      await checkbox.scrollIntoViewIfNeeded();

      // La case « Utiliser une grille de scoring » est cochée (format GRILLE).
      await expect(checkbox).toBeVisible({ timeout: 10000 });
      await expect(checkbox.locator('input[type="checkbox"]')).toBeChecked();

      // L'éditeur de grille (app-metrique-form) est affiché.
      await expect(referentPage.locator('app-metrique-form').first()).toBeVisible({ timeout: 10000 });
    } finally {
      await apiDelete(referentPage, `plans/operations/${opId}/`);
    }
  });
});
