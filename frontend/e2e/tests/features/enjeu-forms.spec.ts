/**
 * E2E Tests for Enjeu and FCR dedicated form pages.
 *
 * Tests:
 * - Enjeu form: create, edit, validation, conditional fields (~18 tests)
 * - FCR form: create, edit, validation (~10 tests)
 *
 * Prerequisite: seed_testdata with enjeux seeder.
 */
import { test, expect } from '../../fixtures/auth.fixture';
import { EnjeuFormPage } from '../../pages/enjeu-form.page';
import { FcrFormPage } from '../../pages/fcr-form.page';
import { findPlan, findFirstFcr, apiGet, apiPatch } from '../../helpers/plan.helper';

// ── Helpers ──────────────────────────────────────────────────────

async function findFirstEnjeu(page: import('@playwright/test').Page, planId: number) {
  const { data } = await apiGet(page, `plans/enjeux/by-plan/${planId}/`);
  const enjeux = data.enjeux || [];
  if (enjeux.length === 0) throw new Error(`No enjeux for plan ${planId}`);
  return enjeux[0];
}

// =========================================================================
// ENJEU FORM — Display & Navigation
// =========================================================================
test.describe('Enjeu Form - Display', () => {
  test('should display create form page with all fields', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await expect(form.heroTitle).toBeVisible();
    await expect(form.libelleTextarea).toBeVisible();
    await expect(form.intituleCourtInput).toBeVisible();
    await expect(form.rangRadioGroup).toBeVisible();
    await expect(form.validateBtn).toBeVisible();
    await expect(form.cancelBtn).toBeVisible();
  });

  test('should display category radio buttons', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await expect(form.categorieEcologiqueRadio).toBeVisible();
    await expect(form.categorieSocioEcoRadio).toBeVisible();
  });

  test('should navigate back on cancel', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.cancel();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });
});

// =========================================================================
// ENJEU FORM — Create
// =========================================================================
test.describe('Enjeu Form - Create', () => {
  test('should create an enjeu with minimal data', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.fillLibelle(`E2E Enjeu Minimal ${Date.now()}`);
    await form.selectRang(1);
    await form.submit();

    await form.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });

  test('should create an ecological enjeu with habitat checkbox', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.fillLibelle(`E2E Enjeu Ecologique ${Date.now()}`);
    await form.fillIntituleCourt('E2E Eco');
    await form.selectRang(2);
    await form.selectEcological();

    // Check habitat checkbox
    await form.habitatCheckbox.click();
    await referentPage.waitForTimeout(300);

    // Habitat reference list should appear
    await expect(form.habitatRefList).toBeVisible();

    await form.submit();
    await form.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });

  test('should create an ecological enjeu with species checkbox', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.fillLibelle(`E2E Enjeu Espece ${Date.now()}`);
    await form.selectRang(1);
    await form.selectEcological();
    await form.especeCheckbox.click();
    await referentPage.waitForTimeout(300);

    await expect(form.taxonRefList).toBeVisible();

    await form.submit();
    await form.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });

  test('should create a socio-economic enjeu', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.fillLibelle(`E2E Enjeu SocioEco ${Date.now()}`);
    await form.selectRang(3);
    await form.selectSocioEconomic();

    // Socio-economic checkboxes should be visible
    await expect(form.valeurPaysagereCheckbox).toBeVisible();
    await expect(form.patrimoineCulturelCheckbox).toBeVisible();

    // Ecological checkboxes should NOT be visible
    await expect(form.habitatCheckbox).not.toBeVisible();
    await expect(form.especeCheckbox).not.toBeVisible();

    await form.valeurPaysagereCheckbox.click();

    await form.submit();
    await form.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });

  test('should create enjeu with description in details accordion', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.fillLibelle(`E2E Enjeu Details ${Date.now()}`);
    await form.selectRang(1);

    // Expand details panel and fill description
    await form.expandDetailsPanel();
    await referentPage.waitForTimeout(300);
    await form.descriptionTextarea.fill('Description E2E test');

    await form.submit();
    await form.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });
});

// =========================================================================
// ENJEU FORM — Conditional Fields
// =========================================================================
test.describe('Enjeu Form - Conditional Fields', () => {
  test('should show ecological checkboxes when ecological is selected', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.selectEcological();

    await expect(form.habitatCheckbox).toBeVisible();
    await expect(form.especeCheckbox).toBeVisible();
    await expect(form.patrimoineGeologiqueCheckbox).toBeVisible();
    await expect(form.fonctionnaliteEcosystemeCheckbox).toBeVisible();
    await expect(form.autreEcologiqueCheckbox).toBeVisible();
  });

  test('should show socio-eco checkboxes when socio-eco is selected', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.selectSocioEconomic();

    await expect(form.valeurPaysagereCheckbox).toBeVisible();
    await expect(form.patrimoineCulturelCheckbox).toBeVisible();
    await expect(form.developpementDurableCheckbox).toBeVisible();
    await expect(form.usagesCheckbox).toBeVisible();
    await expect(form.valeurAjouteeCheckbox).toBeVisible();
    await expect(form.autreSocioEcoCheckbox).toBeVisible();
  });

  test('should hide ecological fields when switching to socio-eco', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    // Start with ecological
    await form.selectEcological();
    await expect(form.habitatCheckbox).toBeVisible();

    // Switch to socio-eco
    await form.selectSocioEconomic();
    await expect(form.habitatCheckbox).not.toBeVisible();
    await expect(form.valeurPaysagereCheckbox).toBeVisible();
  });

  test('should show geology sub-options when patrimoine geologique is checked', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.selectEcological();
    await form.patrimoineGeologiqueCheckbox.click();
    await referentPage.waitForTimeout(300);

    await expect(form.geoExSituCheckbox).toBeVisible();
    await expect(form.geoInSituCheckbox).toBeVisible();
    await expect(form.geologyRefList).toBeVisible();
  });

  test('should show precision input when autre ecologique is checked', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.selectEcological();
    await expect(form.autreEcologiquePrecision).not.toBeVisible();

    await form.autreEcologiqueCheckbox.click();
    await referentPage.waitForTimeout(300);

    await expect(form.autreEcologiquePrecision).toBeVisible();
    await form.autreEcologiquePrecision.fill('Précision E2E test');
  });

  test('should show precision input when autre socio-eco is checked', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.selectSocioEconomic();
    await expect(form.autreSocioEcoPrecision).not.toBeVisible();

    await form.autreSocioEcoCheckbox.click();
    await referentPage.waitForTimeout(300);

    await expect(form.autreSocioEcoPrecision).toBeVisible();
  });

  test('should hide habitat ref list when habitat is unchecked', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.selectEcological();
    await form.habitatCheckbox.click();
    await referentPage.waitForTimeout(300);
    await expect(form.habitatRefList).toBeVisible();

    // Uncheck
    await form.habitatCheckbox.click();
    await referentPage.waitForTimeout(300);
    await expect(form.habitatRefList).not.toBeVisible();
  });
});

// =========================================================================
// ENJEU FORM — Edit
// =========================================================================
test.describe('Enjeu Form - Edit', () => {
  test('should pre-fill form when editing existing enjeu', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const enjeu = await findFirstEnjeu(referentPage, plan.id_pg);
    const form = new EnjeuFormPage(referentPage);
    await form.gotoEdit(plan.slug, enjeu.slug || enjeu.id_enjeu.toString());
    await form.waitForForm();

    const libelleValue = await form.libelleTextarea.inputValue();
    expect(libelleValue).toBe(enjeu.libelle);
  });

  test('should update an enjeu libelle', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const enjeu = await findFirstEnjeu(referentPage, plan.id_pg);
    const form = new EnjeuFormPage(referentPage);
    await form.gotoEdit(plan.slug, enjeu.slug || enjeu.id_enjeu.toString());
    await form.waitForForm();

    const updatedName = `${enjeu.libelle} (E2E modifie)`;
    await form.fillLibelle(updatedName);
    await form.submit();
    await form.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });

    // Restore via API
    await apiPatch(referentPage, `plans/enjeux/${enjeu.id_enjeu}/`, { libelle: enjeu.libelle });
  });
});

// =========================================================================
// ENJEU FORM — Validation
// =========================================================================
test.describe('Enjeu Form - Validation', () => {
  test('should show error when submitting empty libelle', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.submit();
    await referentPage.waitForTimeout(1000);

    expect(referentPage.url()).toContain('/nouveau');
    const matError = referentPage.locator('mat-error, .app-form-field__error, .form-error-msg');
    await expect(matError.first()).toBeVisible();
  });

  test('should enforce max length on intitule court', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new EnjeuFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.fillIntituleCourt('A'.repeat(60));
    const value = await form.intituleCourtInput.inputValue();
    // maxLength should prevent more than 50 characters, or show a counter
    expect(value.length).toBeLessThanOrEqual(50);
  });
});

// =========================================================================
// FCR FORM — Display & Create
// =========================================================================
test.describe('FCR Form - Display', () => {
  test('should display create FCR form page', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new FcrFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await expect(form.heroTitle).toBeVisible();
    await expect(form.libelleTextarea).toBeVisible();
    await expect(form.intituleCourtInput).toBeVisible();
    await expect(form.categorieRadioGroup).toBeVisible();
    await expect(form.validateBtn).toBeVisible();
  });

  test('should display FCR category radio options', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new FcrFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    const options = await form.categorieRadioGroup.locator('mat-radio-button').count();
    expect(options).toBeGreaterThanOrEqual(3); // CONNAISSANCE, ANCRAGE, FONCTIONNEMENT, AUTRE
  });
});

test.describe('FCR Form - Create', () => {
  test('should create a FCR with all fields', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new FcrFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.fillLibelle(`E2E FCR ${Date.now()}`);
    await form.fillIntituleCourt('E2E FCR');
    await form.selectFirstCategorie();
    await referentPage.waitForTimeout(300);

    await form.submit();
    // Wait for either snackbar or navigation (snackbar may dismiss quickly)
    await Promise.race([
      form.waitForSnackbar(),
      referentPage.waitForURL(/\/enjeux/, { timeout: 15000 }),
    ]);
  });

  test('should create FCR with different category', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new FcrFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.fillLibelle(`E2E FCR Cat2 ${Date.now()}`);
    await form.selectCategorie(1); // Second category option
    await referentPage.waitForTimeout(300);

    await form.submit();
    // Wait for either snackbar or navigation (snackbar may dismiss quickly)
    await Promise.race([
      form.waitForSnackbar(),
      referentPage.waitForURL(/\/enjeux/, { timeout: 15000 }),
    ]);
  });

  test('should navigate back on cancel', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new FcrFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.cancel();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });
  });
});

test.describe('FCR Form - Validation', () => {
  test('should show error when submitting empty FCR form', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new FcrFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    await form.submit();
    await referentPage.waitForTimeout(1000);

    expect(referentPage.url()).toContain('/fcr/nouveau');
    const matError = referentPage.locator('mat-error, .app-form-field__error, .form-error-msg');
    await expect(matError.first()).toBeVisible();
  });

  test('should require category selection', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const form = new FcrFormPage(referentPage);
    await form.gotoCreate(plan.slug);
    await form.waitForForm();

    // Fill libelle but don't select category
    await form.fillLibelle(`E2E FCR NoCategory ${Date.now()}`);
    await form.submit();
    await referentPage.waitForTimeout(1000);

    // Should stay on form
    expect(referentPage.url()).toContain('/fcr/nouveau');
  });
});

test.describe('FCR Form - Edit', () => {
  test('should pre-fill form when editing existing FCR', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const fcr = await findFirstFcr(referentPage, plan.id_pg);
    const form = new FcrFormPage(referentPage);
    await form.gotoEdit(plan.slug, fcr.id_enjeu);
    await form.waitForForm();

    const libelleValue = await form.libelleTextarea.inputValue();
    expect(libelleValue).toBe(fcr.libelle);
  });

  test('should update FCR libelle', async ({ referentPage }) => {
    const plan = await findPlan(referentPage, 'Camargue');
    const fcr = await findFirstFcr(referentPage, plan.id_pg);
    const form = new FcrFormPage(referentPage);
    await form.gotoEdit(plan.slug, fcr.id_enjeu);
    await form.waitForForm();

    const updatedName = `${fcr.libelle} (E2E modifie)`;
    await form.fillLibelle(updatedName);
    await form.submit();
    await form.waitForSnackbar();
    await referentPage.waitForURL(/\/enjeux/, { timeout: 10000 });

    // Restore
    await apiPatch(referentPage, `plans/enjeux/${fcr.id_enjeu}/`, { libelle: fcr.libelle });
  });
});
