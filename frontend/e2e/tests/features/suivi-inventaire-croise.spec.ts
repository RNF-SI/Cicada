/**
 * #715 — Un même suivi/inventaire se saisit à deux endroits : le module
 * Inventaires et la fiche d'une action de suivi (CS). On passe d'un écran à
 * l'autre et on vérifie, par l'API, que ni l'un ni l'autre ne perd ce que
 * l'autre a saisi.
 *
 * Les données sont posées par l'API (2 protocoles, habitats structurés) puis
 * chaque écran est ouvert et enregistré SANS modification : tout écart entre
 * l'avant et l'après est une perte causée par le formulaire.
 *
 * Prérequis : seed_testdata (plan brouillon Camargue avec au moins une métrique).
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { InventaireFormPage } from '../../pages/inventaire-form.page';
import { OperationFormPage } from '../../pages/operation-form.page';
import { apiGet, apiPost, apiDelete, findPlan, findFirstMetrique } from '../../helpers/plan.helper';

type Page = import('@playwright/test').Page;

async function typeActionCS(page: Page): Promise<number> {
  const { data } = await apiGet(page, 'nomenclatures/', { type: 'TYPE_ACTION', prefix: 'CS' });
  const list = data?.results ?? data ?? [];
  const cs8 = list.find((n: any) => n.cd_nomenclature === 'CS8') ?? list[0];
  return cs8.id_nomenclature;
}

/** Suivi complet, tel qu'on le saisit dans le module Inventaires. */
function suiviComplet(intitule: string, idTypeAction: number) {
  return {
    intitule,
    id_type_action: idTypeAction,
    objectif_principal: 'OBJ_ETAT_CONSERVATION',
    objectif_secondaire: 'OBJ_INVENTAIRE_INITIAL',
    cibles_principales: 'HABITATS_VEGETATIONS',
    habitat_ref: 'Prairies humides',
    habitats: [{ cd_hab: '1234', lb_hab_fr: 'Prairies humides', lb_code: 'E3.4', lb_typo: 'EUNIS' }],
    protocoles: [
      {
        protocole_dans_campanule: false, nom_protocole: 'Transect local',
        periode_suivi: 'AVRIL,MAI', documentation_disponible: true,
        url_documentation: 'https://example.org/transect',
      },
      { protocole_dans_campanule: false, nom_protocole: 'Points d\'écoute' },
    ],
  };
}

function attendreLaSauvegarde(page: Page, form: { waitForSnackbar: () => Promise<void> }) {
  return Promise.race([
    form.waitForSnackbar().catch(() => {}),
    page.waitForTimeout(5000),
  ]).then(() => page.waitForTimeout(800));
}

function expectSuiviIntact(apres: any, avant: any) {
  expect(apres.intitule).toBe(avant.intitule);
  expect(apres.id_type_action).toBe(avant.id_type_action);
  expect(apres.objectif_principal).toBe(avant.objectif_principal);
  expect(apres.objectif_secondaire).toBe(avant.objectif_secondaire);
  expect(apres.cibles_principales).toBe(avant.cibles_principales);
  expect(apres.habitat_ref).toBe(avant.habitat_ref);
  expect(apres.habitats.map((h: any) => h.cd_hab)).toEqual(avant.habitats.map((h: any) => h.cd_hab));
  expect(apres.protocoles.map((p: any) => p.nom_protocole)).toEqual(['Transect local', 'Points d\'écoute']);
  expect(apres.protocoles[0].periode_suivi).toBe('AVRIL,MAI');
  expect(apres.protocoles[0].documentation_disponible).toBe(true);
  expect(apres.protocoles[0].url_documentation).toBe('https://example.org/transect');
}

test.describe('Suivi partagé entre le module Inventaires et la fiche action (#715)', () => {
  test('inventaire → action rattachée → inventaire : rien n\'est perdu', async ({ referentPage }) => {
    const page = referentPage;
    const idType = await typeActionCS(page);
    const created = await apiPost(page, 'inventaires/suivis/', suiviComplet(`E2E #715 ${Date.now()}`, idType));
    expect(created.ok).toBeTruthy();
    const suiviId = created.data.id_suivi_inventaire as number;
    let opId: number | null = null;

    try {
      const avant = (await apiGet(page, `inventaires/suivis/${suiviId}/`)).data;

      // 1. Module Inventaires : ouvrir et enregistrer sans rien changer.
      const inv = new InventaireFormPage(page);
      await inv.gotoEdit(suiviId);
      await inv.waitForForm();
      await inv.submit();
      await page.waitForURL(new RegExp(`/inventaires/${suiviId}$`), { timeout: 10000 });
      expectSuiviIntact((await apiGet(page, `inventaires/suivis/${suiviId}/`)).data, avant);

      // 2. Fiche action : une action CS rattachée à ce suivi existant.
      const plan = await findPlan(page, 'Camargue');
      const metrique = await findFirstMetrique(page, plan.id_pg);
      const op = await apiPost(page, 'plans/operations/', {
        libelle: avant.intitule, id_type_action: idType, metrique_ids: [metrique.id_metrique],
        est_suivi_existant: true, id_suivi: suiviId,
      });
      expect(op.ok).toBeTruthy();
      opId = op.data.id_operation as number;

      const action = new OperationFormPage(page);
      await action.gotoEdit(plan.slug, opId);
      await action.waitForForm();
      await action.saveDraft();
      await attendreLaSauvegarde(page, action);
      expectSuiviIntact((await apiGet(page, `inventaires/suivis/${suiviId}/`)).data, avant);

      // 3. Le suivi est bien proposé aux autres actions de son type.
      const proposes = (await apiGet(page, 'inventaires/suivis/', { type_action_prefix: 'CS8', page_size: '200' })).data;
      expect((proposes.results ?? []).map((s: any) => s.id_suivi_inventaire)).toContain(suiviId);
    } finally {
      if (opId) await apiDelete(page, `plans/operations/${opId}/`).catch(() => {});
      await apiDelete(page, `inventaires/suivis/${suiviId}/`).catch(() => {});
    }
  });

  test('action avec son propre suivi à 2 protocoles : l\'enregistrer garde le second', async ({ referentPage }) => {
    const page = referentPage;
    const idType = await typeActionCS(page);
    const plan = await findPlan(page, 'Camargue');
    const metrique = await findFirstMetrique(page, plan.id_pg);
    const suivi = suiviComplet(`E2E #715 propre ${Date.now()}`, idType);
    const op = await apiPost(page, 'plans/operations/', {
      libelle: suivi.intitule, id_type_action: idType, metrique_ids: [metrique.id_metrique],
      est_suivi_existant: false, suivi_inventaire: suivi,
    });
    expect(op.ok).toBeTruthy();
    const opId = op.data.id_operation as number;
    const suiviId = op.data.id_suivi as number;

    try {
      const avant = (await apiGet(page, `inventaires/suivis/${suiviId}/`)).data;
      expect(avant.protocoles).toHaveLength(2);

      const action = new OperationFormPage(page);
      await action.gotoEdit(plan.slug, opId);
      await action.waitForForm();
      await action.saveDraft();
      await attendreLaSauvegarde(page, action);

      const apres = (await apiGet(page, `inventaires/suivis/${suiviId}/`)).data;
      expectSuiviIntact(apres, avant);
      // Et la fiche du module Inventaires affiche des libellés, pas des codes.
      expect(apres.objectif_principal_label).not.toBe('OBJ_ETAT_CONSERVATION');
      expect(apres.cibles_principales_label).toBe('Habitats et végétations');
    } finally {
      await apiDelete(page, `plans/operations/${opId}/`).catch(() => {});
      await apiDelete(page, `inventaires/suivis/${suiviId}/`).catch(() => {});
    }
  });
});
