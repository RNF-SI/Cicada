/**
 * E2E — Import Excel des actions d'un plan de gestion (#478, #600).
 *
 * Aller-retour complet PAR L'INTERFACE, sur un plan construit pour le test :
 *   1. brouillon sur le site de Camargue (2 organismes gestionnaires) ;
 *      arborescence importée depuis un plan « Ventilation — … » seedé ;
 *   2. postes (un salarié avec coût jour, un bénévole) et trois actions
 *      saisies comme le fait la fiche action, dans trois modes de ventilation :
 *      ventilation maximale (détail des coûts par organisme, temps par poste),
 *      « par type de budget » sans détail, « par organisme » ;
 *   3. export du classeur d'actions du plan ;
 *   4. téléversé tel quel sur la page « Paramètres » : refusé tant que le plan
 *      contient ses actions (rapport d'erreur affiché, import désactivé) ;
 *   5. actions supprimées, nouveau téléversement : rapport valide, import ;
 *   6. les actions recréées sont identiques aux originales — paramétrage
 *      budgétaire, montants par année / organisme, lignes de temps de travail.
 *
 * Le classeur n'est pas une fixture committée : il est produit par l'export,
 * donc toujours au format courant.
 */
import * as fs from 'fs';
import { test, expect } from '../../fixtures/auth.fixture';
import {
  findPlan,
  apiGet,
  apiGetBuffer,
  apiPost,
  apiPostFile,
  apiDelete,
} from '../../helpers/plan.helper';

type Api = Awaited<ReturnType<typeof apiGet>>;

function results(res: Api): any[] {
  return Array.isArray(res.data) ? res.data : res.data?.results ?? [];
}

/** Premier indicateur (branche état) d'un plan. */
async function firstIndicateurId(page: any, planId: number): Promise<number> {
  const { data } = await apiGet(page, `plans/enjeux/by-plan/${planId}/`);
  for (const enjeu of [...(data.enjeux || []), ...(data.fcr || [])]) {
    for (const olt of enjeu.objectifs_long_terme || []) {
      for (const ne of olt.niveaux_exigence || []) {
        for (const ind of ne.indicateurs || []) return ind.id_indicateur as number;
      }
    }
  }
  throw new Error(`Aucun indicateur dans le plan ${planId}`);
}

async function planOperations(page: any, indicateurId: number): Promise<any[]> {
  // Rattachement direct ou par métrique (#367) ; le filtre `?id_indicateur=`
  // de la liste ne suit que les métriques.
  const { data } = await apiGet(page, `plans/operations/by-indicateur/${indicateurId}/`);
  const details = [];
  for (const op of data.operations || []) {
    details.push((await apiGet(page, `plans/operations/${op.id_operation}/`)).data);
  }
  return details;
}

const AMOUNT_FIELDS = [
  'budget_fonctionnement', 'budget_investissement', 'cout_salarial', 'cout_salarial_invest',
  'cout_stage', 'cout_prestataire', 'autre_cout', 'autre_cout_commentaire',
  'cout_prestataire_invest', 'autre_cout_invest', 'autre_cout_invest_commentaire', 'etp',
];

const num = (v: unknown) => (v == null || v === '' ? null : Number(v));
const pick = (o: any) =>
  AMOUNT_FIELDS.map((f) => (f.endsWith('commentaire') ? o[f] || '' : num(o[f])));

/** Ce que l'import doit restituer, sans les identifiants techniques. */
function normalize(ops: any[]) {
  return ops
    .map((op) => ({
      code: op.code_operation,
      libelle: op.libelle,
      mode: op.ventilation_mode,
      parPoste: op.declinaison_par_poste,
      typeCout: op.declinaison_par_type_cout,
      salaireAuto: op.cout_salarial_auto,
      sites: [...(op.site_ids || [])].sort(),
      annees: (op.operation_annees || [])
        .map((oa: any) => ({
          annee: oa.annee,
          programmee: oa.periodicite,
          budget: num(oa.budget),
          montants: pick(oa),
          organismes: (oa.organismes || [])
            .map((o: any) => JSON.stringify([o.id_organisme, ...pick(o)]))
            .sort(),
          rh: (oa.rh_lignes || [])
            .map((l: any) =>
              JSON.stringify([l.id_poste, l.id_organisme, num(l.jours), l.categorie_depense, l.finance]),
            )
            .sort(),
        }))
        .sort((a: any, b: any) => a.annee - b.annee),
    }))
    .sort((a, b) => a.code.localeCompare(b.code));
}

interface Fixture {
  plan: { id_pg: number; slug: string };
  indicateurId: number;
}

/** Brouillon + arborescence + postes + 3 actions (une par famille de mode). */
async function buildPlan(page: any): Promise<Fixture> {
  const source = await findPlan(page, 'Ventilation');
  const { data: sourceDetail } = await apiGet(page, `plans/plans/${source.id_pg}/`);
  const site = (sourceDetail.sites || [])[0];
  expect(site?.id_site, 'le plan source doit avoir un site').toBeTruthy();
  const orgIds: number[] = (site.organismes || []).map((o: any) => o.id_organisme);
  expect(orgIds.length, 'le site doit avoir 2 organismes gestionnaires').toBeGreaterThanOrEqual(2);

  const created = await apiPost(page, 'plans/plans/', {
    nom: `E2E Import actions ${Date.now()}`,
    rang: 1,
    annee_debut: 2024,
    annee_fin: 2028,
    sites_ids: [site.id_site],
  });
  expect(created.ok, `création du plan : ${created.status}`).toBeTruthy();
  const plan = { id_pg: created.data.id_pg as number, slug: created.data.slug as string };

  // Arborescence : export du plan source, import dans le brouillon.
  const arbo = await apiGetBuffer(page, `plans/plans/${source.id_pg}/export-arborescence-xlsx/`);
  expect(arbo.ok).toBeTruthy();
  const imported = await apiPostFile(page, `plans/plans/${plan.id_pg}/import-arborescence/`, 'arbo.xlsx', arbo.body);
  expect(imported.ok, `import arborescence : ${JSON.stringify(imported.data)}`).toBeTruthy();
  const indicateurId = await firstIndicateurId(page, plan.id_pg);

  // Postes : un salarié (coût jour) et un bénévole (non financé).
  const fonctions = results(await apiGet(page, 'plans/fonctions/'));
  const salarie = fonctions.find((f: any) => f.type_poste === 'salarie');
  const benevole = fonctions.find((f: any) => f.type_poste === 'benevole') ??
    fonctions.find((f: any) => f.finance_par_defaut === false);
  expect(salarie && benevole, 'fonctions du socle').toBeTruthy();
  const posteSal = await apiPost(page, 'plans/postes/', {
    id_pg: plan.id_pg, id_organisme: orgIds[0], nombre: 1, cout_jour: '300',
    fonctions: [{ id_fonction: salarie.id_fonction }],
  });
  const posteBen = await apiPost(page, 'plans/postes/', {
    id_pg: plan.id_pg, id_organisme: orgIds[0], nombre: 3, cout_jour: '0',
    fonctions: [{ id_fonction: benevole.id_fonction }],
  });
  expect(posteSal.ok && posteBen.ok, 'création des postes').toBeTruthy();
  const qSal = posteSal.data.id_poste as number;
  const qBen = posteBen.data.id_poste as number;

  const empty = { annee: 2025, periodicite: false, organismes: [], rh_lignes: [] };
  const common = { id_indicateur: indicateurId, annee_min: 2024, annee_max: 2025 };
  const actions = [
    {
      // Ventilation maximale : détail des coûts par organisme, temps par poste,
      // coût salarial calculé (6 j × 300 € + 2 j invest × 300 €).
      ...common,
      libelle: 'E2E ventilation maximale',
      code_operation: 'E2E-MAX',
      ventilation_mode: 'by_org_type_poste',
      declinaison_par_poste: true,
      declinaison_par_type_cout: true,
      cout_salarial_auto: true,
      site_ids: [site.id_site],
      operation_annees: [
        {
          annee: 2024, periodicite: true, budget: 4970, etp: 18,
          organismes: [
            { id_organisme: orgIds[0], cout_prestataire: 1500, autre_cout: 250,
              autre_cout_commentaire: 'Location', cout_stage: 400 },
            { id_organisme: orgIds[1], cout_prestataire_invest: 420 },
          ],
          rh_lignes: [
            { id_poste: qSal, jours: 6, categorie_depense: 'fonctionnement', finance: true },
            { id_poste: qSal, jours: 2, categorie_depense: 'investissement', finance: true },
            { id_poste: qBen, jours: 10, categorie_depense: 'benevolat_partenariat', finance: false },
          ],
        },
        empty,
      ],
    },
    {
      ...common,
      libelle: 'E2E par type de budget',
      code_operation: 'E2E-TYPE',
      ventilation_mode: 'by_type',
      declinaison_par_poste: false,
      declinaison_par_type_cout: false,
      cout_salarial_auto: true,
      operation_annees: [
        {
          annee: 2024, periodicite: true, budget: 2000, etp: 5,
          budget_fonctionnement: 800, budget_investissement: 1200,
          organismes: [],
          rh_lignes: [{ jours: 5, categorie_depense: 'investissement', finance: true }],
        },
        empty,
      ],
    },
    {
      ...common,
      libelle: 'E2E par organisme',
      code_operation: 'E2E-ORG',
      ventilation_mode: 'by_org',
      declinaison_par_poste: false,
      declinaison_par_type_cout: true,
      cout_salarial_auto: true,
      site_ids: [site.id_site],
      operation_annees: [
        {
          annee: 2024, periodicite: true, budget: 3000, etp: 11,
          organismes: [
            { id_organisme: orgIds[0], budget_fonctionnement: 2000, etp: 8 },
            { id_organisme: orgIds[1], budget_fonctionnement: 1000, etp: 3 },
          ],
          rh_lignes: [
            { id_organisme: orgIds[0], jours: 8, categorie_depense: 'fonctionnement', finance: true },
            { id_organisme: orgIds[1], jours: 3, categorie_depense: 'benevolat_partenariat', finance: false },
          ],
        },
        empty,
      ],
    },
  ];
  for (const payload of actions) {
    const res = await apiPost(page, 'plans/operations/', payload);
    expect(res.ok, `création ${payload.code_operation} : ${JSON.stringify(res.data)}`).toBeTruthy();
  }
  return { plan, indicateurId };
}

async function uploadActions(page: any, slug: string, filePath: string): Promise<void> {
  await page.goto(`/plans/${slug}/parametres`);
  const input = page.getByTestId('actions-import-file');
  await expect(input).toBeAttached({ timeout: 15000 });
  await input.setInputFiles(filePath);
}

test.describe('Import des actions via Excel', () => {
  test('aller-retour export → import restitue budgets, RH et paramétrage (#600)', async ({ superAdminPage }, testInfo) => {
    const page = superAdminPage;
    const { plan, indicateurId } = await buildPlan(page);

    try {
      const before = normalize(await planOperations(page, indicateurId));
      expect(before.map((o) => o.mode)).toEqual(['by_org_type_poste', 'by_org', 'by_type']);

      // Export du classeur d'actions pré-rempli.
      const exported = await apiGetBuffer(page, `plans/plans/${plan.id_pg}/export-actions-xlsx/`);
      expect(exported.ok).toBeTruthy();
      const filePath = testInfo.outputPath('actions.xlsx');
      fs.writeFileSync(filePath, exported.body);

      // Plan encore rempli : le rapport refuse l'import et l'explique.
      await uploadActions(page, plan.slug, filePath);
      await expect(page.getByTestId('actions-report-error')).toBeVisible({ timeout: 20000 });
      await expect(page.getByTestId('actions-issues-error')).toContainText('déjà des actions');
      await expect(page.getByTestId('actions-import-submit')).toBeDisabled();

      // Plan vidé de ses actions : le même fichier passe.
      for (const op of await planOperations(page, indicateurId)) {
        const del = await apiDelete(page, `plans/operations/${op.id_operation}/`);
        expect(del.ok, `suppression ${op.code_operation}`).toBeTruthy();
      }
      expect(await planOperations(page, indicateurId)).toHaveLength(0);

      await uploadActions(page, plan.slug, filePath);
      const ok = page.getByTestId('actions-report-ok');
      await expect(ok).toBeVisible({ timeout: 20000 });
      await expect(ok).toContainText('3 action(s)');
      await expect(page.getByTestId('actions-issues-error')).toHaveCount(0);
      await expect(page.getByTestId('actions-issues-warning')).toHaveCount(0);

      const submit = page.getByTestId('actions-import-submit');
      await expect(submit).toBeEnabled();
      await Promise.all([
        page.waitForURL(/\/plans\/.+\/enjeux/, { timeout: 20000 }),
        submit.click(),
      ]);

      // Les actions recréées sont identiques aux originales.
      const after = normalize(await planOperations(page, indicateurId));
      expect(after).toEqual(before);
    } finally {
      await apiDelete(page, `plans/plans/${plan.id_pg}/`).catch(() => undefined);
    }
  });

  test('le modèle d\'actions du plan se télécharge depuis les paramètres', async ({ superAdminPage }) => {
    const page = superAdminPage;
    const plan = await findPlan(page, 'Ventilation');
    await page.goto(`/plans/${plan.slug}/parametres`);
    const btn = page.getByTestId('actions-template');
    await expect(btn).toBeVisible({ timeout: 15000 });
    const [download] = await Promise.all([page.waitForEvent('download'), btn.click()]);
    expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
    expect(await download.path()).toBeTruthy();
  });
});
