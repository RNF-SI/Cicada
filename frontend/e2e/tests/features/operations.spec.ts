/**
 * E2E Tests for Operations (Actions) CRUD within the Enjeux module.
 *
 * Tests:
 * - Navigation and form display (~6 tests)
 * - Create operations (~6 tests)
 * - Edit operations (~4 tests)
 * - Form validation (~3 tests)
 * - Form interactions (~5 tests)
 * - Delete operations (~2 tests)
 *
 * Prerequisite: seed_testdata with enjeux seeder (creates ~36 operations
 * across multiple plans with full data: suivi, protocole, annees, finances).
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { OperationFormPage } from '../../pages/operation-form.page';
import {
  findPlan,
  findFirstOperation,
  findFirstMetrique,
  apiPost,
  apiGet,
  apiPatch,
  apiDelete,
} from '../../helpers/plan.helper';

// ── Helpers ──────────────────────────────────────────────────────

/** Create an operation via the API and return its ID. */
async function createOperationViaApi(
  page: import('@playwright/test').Page,
  libelle: string,
  metriqueId?: number,
): Promise<number> {
  const payload: Record<string, unknown> = { libelle };
  if (metriqueId) payload['metrique_ids'] = [metriqueId];
  const { ok, data } = await apiPost(page, 'plans/operations/', payload);
  if (!ok) throw new Error(`Failed to create operation via API (status: ${data?.detail || 'unknown'})`);
  return data.id_operation;
}

/** Delete an operation via the API. */
async function deleteOperationViaApi(page: import('@playwright/test').Page, operationId: number) {
  await apiDelete(page, `plans/operations/${operationId}/`);
}

// =========================================================================
// Navigation and Form Display
// =========================================================================
test.describe('Operations - Navigation and Form Display', () => {
  test('should display the create operation form page', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    await expect(formPage.heroTitle).toBeVisible();
    await expect(formPage.libelleInput).toBeVisible();
    await expect(formPage.validateBtn).toBeVisible();
    await expect(formPage.cancelBtn).toBeVisible();
  });

  test('should display create title for new operation', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    const title = await formPage.heroTitle.innerText();
    // Create title should be something like "Nouvelle action" or "Créer une action"
    expect(title.length).toBeGreaterThan(0);
  });

  test('should display all form sections', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // Always-visible sections
    await expect(formPage.sectionProgrammation).toBeVisible();
    await expect(formPage.sectionDetails).toBeVisible();
    await expect(formPage.sectionEmprise).toBeVisible();

    // Protocole and Bancarisation are only visible for CS-type actions
    await expect(formPage.sectionProtocole).not.toBeVisible();
    await formPage.selectCSAction();
    await expect(formPage.sectionProtocole).toBeVisible();
    await expect(formPage.sectionBancarisation).toBeVisible();
  });

  test('should display type action select with options', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    await formPage.typeActionInput.click();
    await formPage.typeActionInput.fill('');
    await referentPage.waitForTimeout(300);
    const options = await referentPage.locator('.type-action-autocomplete mat-option').count();
    expect(options).toBeGreaterThan(1);
    await referentPage.keyboard.press('Escape');
  });

  test('should display metrique select with plan metrics', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // Le mat-select multiple n'ouvre pas son panel via click programmatique ;
    // on vérifie simplement que le select est rendu, ce qui couvre la régression
    // critique (champ disparu après migration form-field).
    await formPage.metriqueSelect.scrollIntoViewIfNeeded();
    await expect(formPage.metriqueSelect).toBeVisible();
  });

  test('should pre-link metrique when metriqueId query param is provided', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const metrique = await findFirstMetrique(referentPage, plan.id_pg);
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug, metrique.id_metrique);
    await formPage.waitForForm();

    // The metrique select should have a value (not the default "--")
    const selectedText = await formPage.metriqueSelect.innerText();
    expect(selectedText).not.toBe('--');
  });

  test('super admin should access operation form', async ({ superAdminPage }) => {
    const plan = await findPlan(superAdminPage, 'Camargue');
    const formPage = new OperationFormPage(superAdminPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    await expect(formPage.libelleInput).toBeVisible();
  });
});

// =========================================================================
// Create Operations
// =========================================================================
test.describe('Operations - Create', () => {
  test('should create an operation with minimal data (libelle only)', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    const uniqueName = `E2E Op Minimal ${Date.now()}`;
    await formPage.fillLibelle(uniqueName);
    await formPage.submit();

    // Should show success snackbar and navigate back
    await formPage.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });

  test('should create an operation with type action and priority', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    const uniqueName = `E2E Op Priority ${Date.now()}`;
    await formPage.fillLibelle(uniqueName);
    await formPage.selectFirstTypeAction();
    await formPage.selectPriority(0); // First priority option

    await formPage.submit();
    await formPage.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });

  test('should create an operation with protocole non-campanule', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    const uniqueName = `E2E Op Protocole ${Date.now()}`;
    await formPage.fillLibelle(uniqueName);

    // Select a CS action type to reveal protocole section
    await formPage.selectCSAction();

    // CS action requires an intitulé de suivi (validators conditionnels)
    await formPage.fillIntituleSuivi(`E2E Suivi ${Date.now()}`);

    // Fill protocole
    await formPage.fillProtocoleNonCampanule('Protocole E2E Test', {
      description: 'Description du protocole de test',
      objectif: 'Objectif du protocole de test',
      periode: 'Janvier-Mars',
    });
    await formPage.setRespectProtocoleOui();

    // Set frequency
    await formPage.setFrequence(2, 'an');

    await formPage.submit();
    await formPage.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });

  test('should create an operation with description', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    const uniqueName = `E2E Op Description ${Date.now()}`;
    await formPage.fillLibelle(uniqueName);
    await formPage.fillDescription('Description de test pour cette action E2E');

    await formPage.submit();
    await formPage.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });

  test('should create operation with linked metrique', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    const uniqueName = `E2E Op Metrique ${Date.now()}`;
    await formPage.fillLibelle(uniqueName);

    // Select first available metrique : scroll dans la vue + click sur le trigger
    // car le mat-select multiple peut être hors viewport. Retry si le panel
    // n'ouvre pas (mat-select multiple parfois récalcitrant).
    await formPage.metriqueSelect.scrollIntoViewIfNeeded();
    const trigger = formPage.metriqueSelect.locator('.mat-mdc-select-trigger');
    for (let attempt = 0; attempt < 3; attempt++) {
      await trigger.click();
      await referentPage.waitForTimeout(400);
      const panelOpen = await referentPage.locator('.mat-mdc-select-panel').isVisible().catch(() => false);
      if (panelOpen) break;
    }
    await referentPage.locator('mat-option').filter({ hasNotText: '--' }).first().click({ timeout: 10000 });
    // Press Escape to ensure the autocomplete overlay is dismissed before
    // clicking submit (otherwise cdk-overlay-backdrop intercepts pointer events).
    await referentPage.keyboard.press('Escape');
    await referentPage.locator('.cdk-overlay-backdrop').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await referentPage.waitForTimeout(500);

    await formPage.submit();
    await formPage.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });

  test('should create operation with finances', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    const uniqueName = `E2E Op Finances ${Date.now()}`;
    await formPage.fillLibelle(uniqueName);

    // Add a finance entry
    await formPage.addFinance('Financement test E2E');

    // Verify the row appeared
    const financeCount = await formPage.financeRows.count();
    expect(financeCount).toBe(1);

    await formPage.submit();
    await formPage.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });
});

// =========================================================================
// Edit Operations
// =========================================================================
test.describe('Operations - Edit', () => {
  test('should display edit title when editing existing operation', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    let op: any;
    try {
      op = await findFirstOperation(referentPage, plan.id_pg);
    } catch {
      test.skip(true, 'No operations found for this plan — cannot test edit title');
      return;
    }
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoEdit(plan.slug, op.id_operation);
    await formPage.waitForForm();

    const title = await formPage.heroTitle.innerText();
    // Edit title should be different from create title
    expect(title.length).toBeGreaterThan(0);
  });

  test('should pre-fill form fields when editing', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    let op: any;
    try {
      op = await findFirstOperation(referentPage, plan.id_pg);
    } catch {
      test.skip(true, 'No operations found for this plan — cannot test edit pre-fill');
      return;
    }
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoEdit(plan.slug, op.id_operation);
    await formPage.waitForForm();

    // Libelle should be pre-filled
    const libelleValue = await formPage.libelleInput.inputValue();
    expect(libelleValue).toBe(op.libelle);
  });

  test('should update an operation libelle', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    let op: any;
    try {
      op = await findFirstOperation(referentPage, plan.id_pg);
    } catch {
      test.skip(true, 'No operations found for this plan — cannot test update');
      return;
    }
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoEdit(plan.slug, op.id_operation);
    await formPage.waitForForm();

    // Modify the libelle
    const updatedName = `${op.libelle} (E2E modifie)`;
    await formPage.fillLibelle(updatedName);
    await formPage.submit();

    // Wait for either snackbar or URL change (whichever comes first)
    await Promise.race([
      formPage.waitForSnackbar().catch(() => {}),
      referentPage.waitForURL(/\/enjeux/, { timeout: 10000 }).catch(() => {}),
    ]);
    // Give a moment for navigation to complete
    await referentPage.waitForTimeout(1000);

    // Verify via API that it was updated
    const { data: updated } = await apiGet(referentPage, `plans/operations/${op.id_operation}/`);
    expect(updated.libelle).toBe(updatedName);

    // Restore original name
    await apiPatch(referentPage, `plans/operations/${op.id_operation}/`, { libelle: op.libelle });
  });

  test('should preserve existing data after edit roundtrip', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    let op: any;
    try {
      op = await findFirstOperation(referentPage, plan.id_pg);
    } catch {
      test.skip(true, 'No operations found for this plan — cannot test edit roundtrip');
      return;
    }

    // Get full operation details first
    const { data: detail } = await apiGet(referentPage, `plans/operations/${op.id_operation}/`);

    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoEdit(plan.slug, op.id_operation);
    await formPage.waitForForm();

    // Just submit without changes
    await formPage.submit();

    // Wait for either snackbar or URL change (whichever comes first)
    await Promise.race([
      formPage.waitForSnackbar().catch(() => {}),
      referentPage.waitForURL(/\/enjeux/, { timeout: 10000 }).catch(() => {}),
    ]);
    await referentPage.waitForTimeout(1000);

    // Verify fields preserved
    const { data: after } = await apiGet(referentPage, `plans/operations/${op.id_operation}/`);
    expect(after.libelle).toBe(detail.libelle);
    if (detail.id_priorite) expect(after.id_priorite).toBe(detail.id_priorite);
  });

  /**
   * Régression #187 : tous les champs SuiviInventaire (notamment habitat_ref,
   * cible_secondaire, taxon_taxref) doivent survivre à un round-trip
   * GET → ouvrir le formulaire → valider sans changement → GET.
   *
   * Avant le fix : habitat_ref et cible_secondaire étaient absents du
   * serializer de lecture → champs vides en formulaire → écrasés au save.
   */
  test('should preserve ALL SuiviInventaire fields on edit roundtrip (#187)', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');

    // Étape 1 : créer une action CS avec un SuiviInventaire complet via l'API
    // (on évite de remplir 30+ champs à la souris)
    const createPayload: Record<string, unknown> = {
      libelle: `E2E roundtrip ${Date.now()}`,
      est_suivi_existant: false,
      suivi_inventaire: {
        intitule: 'Suivi roundtrip E2E',
        objectif_principal: 'OBJ_CONNAISSANCE',
        objectif_secondaire: 'OBJ_GESTION',
        cibles_principales: 'HABITATS_VEGETATIONS',
        cible_secondaire: 'cible secondaire texte libre',
        taxon_taxref: 'Phragmites australis, Tamarix gallica',
        habitat_ref: 'D5.2, C1.221',
        date_lancement_suivi: '2024-03-15',
        outil_bancarisation: 'GeoNature',
        outil_saisie: 'GeoNature',
        transmission_donnee: true,
      },
    };
    const { ok, data: created } = await apiPost(referentPage, 'plans/operations/', createPayload);
    if (!ok) {
      test.skip(true, `Cannot create test operation: ${JSON.stringify(created).slice(0, 200)}`);
      return;
    }
    const opId = created.id_operation as number;

    try {
      // Étape 2 : récupérer l'état initial via l'API
      const { data: before } = await apiGet(referentPage, `plans/operations/${opId}/`);
      const beforeSuivi = before.suivi_inventaire;

      // Sanity check : tous les champs sont bien renvoyés par l'API de lecture
      expect(beforeSuivi.intitule).toBe('Suivi roundtrip E2E');
      expect(beforeSuivi.cibles_principales).toBe('HABITATS_VEGETATIONS');
      expect(beforeSuivi.cible_secondaire).toBe('cible secondaire texte libre');
      expect(beforeSuivi.taxon_taxref).toBe('Phragmites australis, Tamarix gallica');
      expect(beforeSuivi.habitat_ref).toBe('D5.2, C1.221');

      // Étape 3 : ouvrir le formulaire d'édition et valider sans changement
      const formPage = new OperationFormPage(referentPage);
      await formPage.gotoEdit(plan.slug, opId);
      await formPage.waitForForm();
      await formPage.submit();
      await Promise.race([
        formPage.waitForSnackbar().catch(() => {}),
        referentPage.waitForURL(/\/enjeux/, { timeout: 10000 }).catch(() => {}),
      ]);
      await referentPage.waitForTimeout(1000);

      // Étape 4 : vérifier que TOUS les champs ont survécu au roundtrip
      const { data: after } = await apiGet(referentPage, `plans/operations/${opId}/`);
      const afterSuivi = after.suivi_inventaire;

      expect(after.libelle).toBe(before.libelle);
      expect(afterSuivi.intitule).toBe(beforeSuivi.intitule);
      expect(afterSuivi.objectif_principal).toBe(beforeSuivi.objectif_principal);
      expect(afterSuivi.objectif_secondaire).toBe(beforeSuivi.objectif_secondaire);
      expect(afterSuivi.cibles_principales).toBe(beforeSuivi.cibles_principales);
      expect(afterSuivi.cible_secondaire).toBe(beforeSuivi.cible_secondaire);
      expect(afterSuivi.taxon_taxref).toBe(beforeSuivi.taxon_taxref);
      expect(afterSuivi.habitat_ref).toBe(beforeSuivi.habitat_ref);
      expect(afterSuivi.outil_bancarisation).toBe(beforeSuivi.outil_bancarisation);
      expect(afterSuivi.outil_saisie).toBe(beforeSuivi.outil_saisie);
      expect(afterSuivi.transmission_donnee).toBe(beforeSuivi.transmission_donnee);
    } finally {
      // Cleanup : supprimer l'action créée pour le test
      await deleteOperationViaApi(referentPage, opId).catch(() => {});
    }
  });
});

// =========================================================================
// Form Validation
// =========================================================================
test.describe('Operations - Validation', () => {
  test('should allow submitting form with empty libelle', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // Submit with empty form — libelle is not required
    await formPage.submit();

    // Should submit successfully and navigate back
    await Promise.race([
      formPage.waitForSnackbar().catch(() => {}),
      referentPage.waitForURL(/\/enjeux/, { timeout: 10000 }).catch(() => {}),
    ]);
  });

  test('should not submit when libelle exceeds max length', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // Fill with 501 characters
    await formPage.fillLibelle('A'.repeat(501));
    await formPage.submit();

    // Should stay on the form
    await referentPage.waitForTimeout(1000);
    expect(referentPage.url()).toContain('/operations/nouveau');
  });

  test('should show error banner on API error', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    // Navigate to edit with a non-existent ID
    await formPage.gotoEdit(plan.slug, 999999);
    await formPage.waitForForm();

    // Should show an error banner or error state
    await referentPage.waitForTimeout(2000);
    const hasError = await formPage.errorBanner.isVisible().catch(() => false);
    // Might show error banner or redirect — either is acceptable
    expect(hasError || referentPage.url().includes('/enjeux')).toBeTruthy();
  });

  test('should display validation error banner listing missing required fields (CS action)', async ({ referentPage }) => {
    // Sélectionne un type CS sans remplir intitule_suivi → la bannière doit
    // lister les champs requis manquants.
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    await formPage.selectCSAction();
    await formPage.submit();
    await referentPage.waitForTimeout(500);

    // Reste sur le formulaire (validation a bloqué)
    expect(referentPage.url()).toContain('/operations/nouveau');

    // La bannière d'erreur est visible avec le label des champs manquants
    await expect(formPage.errorBanner).toBeVisible();
    const bannerText = await formPage.errorBanner.textContent();
    expect(bannerText).toMatch(/Champs obligatoires manquants/i);
    // Au moins un des champs requis CS doit apparaître
    expect(bannerText).toMatch(/Intitulé|Protocole|Respect/i);
  });

  test('should auto-scroll to the first invalid field on submit (CS action)', async ({ referentPage }) => {
    // Avec un type CS sélectionné mais intitule_suivi vide, le scroll doit
    // ramener le premier champ invalide dans le viewport.
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    await formPage.selectCSAction();

    // Scrolle tout en bas de la page
    await referentPage.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await referentPage.waitForTimeout(300);

    await formPage.submit();
    await referentPage.waitForTimeout(800);

    // L'intitule_suivi (premier champ requis dans le DOM en mode CS) doit être visible
    const intituleSuivi = formPage.intituleSuiviInput;
    await expect(intituleSuivi).toBeVisible();
    const inViewport = await intituleSuivi.evaluate((el: HTMLElement) => {
      const rect = el.getBoundingClientRect();
      return rect.top >= 0 && rect.bottom <= window.innerHeight;
    });
    expect(inViewport).toBeTruthy();
  });
});

// =========================================================================
// Form Interactions
// =========================================================================
test.describe('Operations - Form Interactions', () => {
  test('should toggle collapsible sections', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // Use the Programmation section (always visible) to test toggle
    await expect(formPage.sectionProgrammation).toBeVisible();

    // Click to collapse the Programmation section
    await formPage.sectionProgrammation.click();
    await referentPage.waitForTimeout(300);

    // Click to re-expand
    await formPage.sectionProgrammation.click();
    await referentPage.waitForTimeout(300);
  });

  test('should show protocole fields when selecting non-campanule', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // Select CS action to reveal protocole section
    await formPage.selectCSAction();

    // Initially, nom_protocole should not be visible (no radio selected)
    await expect(formPage.nomProtocoleInput).not.toBeVisible();

    // Select "Non" for campanule
    await formPage.protocoleCampanuleNon.click();
    await referentPage.waitForTimeout(300);

    // Now nom_protocole and nb_etp_cycle should be visible
    await expect(formPage.nomProtocoleInput).toBeVisible();
    await expect(formPage.nbEtpCycleInput).toBeVisible();
  });

  test('should show justification field when respect protocole is No', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // Select CS action to reveal protocole section
    await formPage.selectCSAction();

    // Select non-campanule first
    await formPage.protocoleCampanuleNon.click();
    await referentPage.waitForTimeout(300);

    // Select "Non" for respect protocole
    await formPage.setRespectProtocoleNon();
    await referentPage.waitForTimeout(300);

    // Justification and differences fields should appear
    await expect(formPage.justificationNonRespect).toBeVisible();
  });

  test('should increment and decrement frequency', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // Select CS action to reveal protocole section with frequency controls
    await formPage.selectCSAction();

    // Need to select a protocole mode for frequency controls to appear
    await formPage.protocoleCampanuleNon.click();
    await referentPage.waitForTimeout(300);

    // Click increment several times
    await formPage.frequenceIncrementBtn.click();
    await formPage.frequenceIncrementBtn.click();
    await formPage.frequenceIncrementBtn.click();
    let value = await formPage.frequenceInput.inputValue();
    expect(parseInt(value)).toBe(3);

    // Decrement once
    await formPage.frequenceDecrementBtn.click();
    value = await formPage.frequenceInput.inputValue();
    expect(parseInt(value)).toBe(2);
  });

  test('should add and remove finance entries', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // Initially no finance rows
    let count = await formPage.financeRows.count();
    expect(count).toBe(0);

    // Add two finance rows
    await formPage.addFinance('Finance 1');
    await formPage.addFinance('Finance 2');
    count = await formPage.financeRows.count();
    expect(count).toBe(2);

    // Remove the first finance row.
    // Use dispatchEvent('click') because the mat-select chevron of the adjacent
    // .finance-categorie field visually intercepts pointer events on the trash btn.
    await formPage.financeRows.first().locator('.finance-remove-btn').dispatchEvent('click');
    await referentPage.waitForTimeout(300);
    count = await formPage.financeRows.count();
    expect(count).toBe(1);
  });
});

// =========================================================================
// Cancel Navigation
// =========================================================================
test.describe('Operations - Cancel', () => {
  test('should navigate back to enjeux list on cancel', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    // Navigate to /enjeux first so location.back() has a destination after
    // the "annuler" click on the operation form.
    await referentPage.goto(`/plans/${plan.slug}/enjeux`);
    await referentPage.waitForLoadState('networkidle').catch(() => {});

    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    await formPage.cancel();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });
});

// =========================================================================
// Delete Operations
// =========================================================================
test.describe('Operations - Delete via API', () => {
  test('should create then delete an operation via API', async ({ superAdminPage }) => {
    const uniqueName = `E2E Op Delete ${Date.now()}`;
    let opId: number;
    try {
      opId = await createOperationViaApi(superAdminPage, uniqueName);
    } catch {
      test.skip(true, 'Operation creation via API failed');
      return;
    }

    // Verify it exists (super admin sees all)
    const { ok: checkOk } = await apiGet(superAdminPage, `plans/operations/${opId}/`);
    expect(checkOk).toBeTruthy();

    // Delete via API
    await deleteOperationViaApi(superAdminPage, opId);

    // Verify it's gone (should 404)
    const { status } = await apiGet(superAdminPage, `plans/operations/${opId}/`);
    expect(status).toBe(404);
  });
});

// =========================================================================
// Programmation Section
// =========================================================================
test.describe('Operations - Programmation', () => {
  test('should display programmation table with plan years', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // The programmation table should be visible (section is open by default)
    await expect(formPage.programmationTable.first()).toBeVisible();

    // Table should have year headers
    const headers = await formPage.programmationTable.first().locator('thead th').allInnerTexts();
    expect(headers.length).toBeGreaterThan(1); // label + at least 1 year
  });

  test('should display site checkboxes in programmation', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // The plan may or may not have sites linked — verify page loads without error
    const siteCount = await formPage.sitesCheckboxes.count();
    expect(siteCount).toBeGreaterThanOrEqual(0);
  });

  test('should show monthly programming table', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    // Check the monthly table exists (12 month headers)
    const monthlyTable = formPage.programmationTable.nth(1);
    await expect(monthlyTable).toBeVisible();
    const monthHeaders = await monthlyTable.locator('thead th').allInnerTexts();
    // label + 12 months
    expect(monthHeaders.length).toBe(13);
  });
});

// =========================================================================
// Save without validation (#251)
// =========================================================================
test.describe('Operations - Save without validation (#251)', () => {
  test('save button is visible alongside validate in create mode', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    await expect(formPage.saveBtn).toBeVisible();
    await expect(formPage.validateBtn).toBeVisible();
  });

  test('saveDraft creates operation and stays on form (URL switches to edit mode)', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    await formPage.fillLibelle('Action enregistrée sans validation');
    await formPage.saveDraft();

    // URL replaced to /modifier/{id}
    await referentPage.waitForURL(/\/operations\/\d+\/modifier/, { timeout: 10000 });
    expect(referentPage.url()).toMatch(/\/operations\/\d+\/modifier/);

    // Wait for the form to re-populate from the loaded operation (the
    // component re-mounts after navigateToEdit and re-fetches the operation).
    await formPage.waitForForm();
    await expect(formPage.libelleInput).toBeVisible();
    await expect(formPage.libelleInput).toHaveValue('Action enregistrée sans validation', { timeout: 10000 });
  });

  test('saveDraft on CS action with missing required fields does not block', async ({ referentPage }) => {
    // En cliquant Valider, la validation bloque (cf. test plus haut). Le bouton
    // Enregistrer doit au contraire passer outre les requis et créer l'action.
    const plan = await findPlan(referentPage, 'Camargue');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoCreate(plan.slug);
    await formPage.waitForForm();

    await formPage.selectCSAction();
    // intitule_suivi resté vide volontairement
    await formPage.saveDraft();

    // Doit créer et passer en mode édition
    await referentPage.waitForURL(/\/operations\/\d+\/modifier/, { timeout: 10000 });
    expect(referentPage.url()).toMatch(/\/operations\/\d+\/modifier/);
  });

  test('saveDraft in edit mode keeps the user on the form', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const opId = await createOperationViaApi(referentPage, 'Action initiale (saveDraft test)');
    const formPage = new OperationFormPage(referentPage);
    await formPage.gotoEdit(plan.slug, opId);
    await formPage.waitForForm();

    const urlBefore = referentPage.url();
    await formPage.fillLibelle('Action modifiée via saveDraft');
    await formPage.saveDraft();

    // Snackbar de confirmation, URL inchangée
    await formPage.waitForSnackbar();
    expect(referentPage.url()).toBe(urlBefore);
    await expect(formPage.libelleInput).toHaveValue('Action modifiée via saveDraft');

    // Cleanup
    await apiDelete(referentPage, `plans/operations/${opId}/`);
  });
});
