import { type Page, type Locator } from '@playwright/test';

/**
 * Page Object for the Operation (Action) form — create and edit modes.
 * Route create: /plans/{slug}/enjeux/operations/nouveau
 * Route edit:   /plans/{slug}/enjeux/operations/{operationId}/modifier
 */
export class OperationFormPage {
  readonly page: Page;

  // Page-level
  readonly heroTitle: Locator;
  readonly loadingSpinner: Locator;
  readonly errorBanner: Locator;

  // Main card
  readonly libelleInput: Locator;
  readonly typeActionInput: Locator;
  readonly typeActionClearBtn: Locator;
  readonly metriqueSelect: Locator;
  readonly prioriteRadioGroup: Locator;

  // Suivi existant toggle
  readonly estSuiviOui: Locator;
  readonly estSuiviNon: Locator;

  // Intitulé du suivi (visible quand CS + nouveau suivi)
  readonly intituleSuiviInput: Locator;

  // Section headers (for toggling)
  readonly sectionDetailsSuivi: Locator;
  readonly sectionProtocole: Locator;
  readonly sectionBancarisation: Locator;
  readonly sectionProgrammation: Locator;
  readonly sectionDetails: Locator;
  readonly sectionEmprise: Locator;

  // Détails de l'inventaire ou du suivi
  readonly objectifPrincipalSelect: Locator;
  readonly ciblesPrincipalesSelect: Locator;

  // Protocole section
  readonly protocoleCampanuleOui: Locator;
  readonly protocoleCampanuleNon: Locator;
  readonly nomProtocoleInput: Locator;
  readonly nbEtpCycleInput: Locator;
  readonly respectProtocoleOui: Locator;
  readonly respectProtocoleNon: Locator;
  readonly justificationNonRespect: Locator;
  readonly descriptionProtocole: Locator;
  readonly objectifProtocole: Locator;
  readonly periodeEchantillonnage: Locator;

  // Fréquence
  readonly frequenceInput: Locator;
  readonly frequenceDecrementBtn: Locator;
  readonly frequenceIncrementBtn: Locator;
  readonly frequenceUniteSelect: Locator;

  // Bancarisation
  readonly bancarisationSelect: Locator;
  readonly outilSaisieSelect: Locator;
  readonly transmissionDonneeOui: Locator;
  readonly transmissionDonneeNon: Locator;

  // Programmation
  readonly sitesCheckboxes: Locator;
  readonly programmationTable: Locator;
  readonly duplicateBtn: Locator;

  // Détails (description)
  readonly descriptionTextarea: Locator;

  // Finances
  readonly addFinanceBtn: Locator;
  readonly financeRows: Locator;

  // Action bar
  readonly cancelBtn: Locator;
  readonly validateBtn: Locator;

  // Snackbar
  readonly snackbar: Locator;

  constructor(page: Page) {
    this.page = page;

    // Page-level
    this.heroTitle = page.locator('.hero-title');
    this.loadingSpinner = page.locator('mat-spinner');
    this.errorBanner = page.locator('.error-banner');

    // Main card — formControlName selectors
    this.libelleInput = page.locator('input[formControlName="libelle"]');
    this.typeActionInput = page.locator('input[placeholder*="Rechercher par code"]');
    this.typeActionClearBtn = page.locator('mat-form-field').filter({ hasText: /type d'action/i }).locator('button[matSuffix]');
    this.metriqueSelect = page.locator('mat-select[formControlName="metrique_ids"]');
    this.prioriteRadioGroup = page.locator('mat-radio-group[formControlName="id_priorite"]');

    // Suivi existant toggle (radio buttons in .radio-field-row)
    this.estSuiviOui = page.locator('.radio-field-row').filter({ hasText: /suivi existant/i }).locator('mat-radio-button').first();
    this.estSuiviNon = page.locator('.radio-field-row').filter({ hasText: /suivi existant/i }).locator('mat-radio-button').nth(1);

    // Intitulé du suivi (input texte, visible quand CS + nouveau suivi)
    this.intituleSuiviInput = page.locator('input[formControlName="intitule_suivi"]');

    // Section headers
    this.sectionDetailsSuivi = page.locator('.section-header').filter({ hasText: /inventaire|suivi/i }).first();
    this.sectionProtocole = page.locator('.section-header').filter({ hasText: /protocole/i }).first();
    this.sectionBancarisation = page.locator('.section-header').filter({ hasText: /bancarisation/i });
    this.sectionProgrammation = page.locator('.section-header').filter({ hasText: /programmation/i });
    this.sectionDetails = page.locator('.section-header').filter({ hasText: /détail/i }).first();
    this.sectionEmprise = page.locator('.section-header').filter({ hasText: /emprise/i });

    // Détails suivi section
    this.objectifPrincipalSelect = page.locator('mat-select[formControlName="objectif_principal"]');
    this.ciblesPrincipalesSelect = page.locator('mat-select[formControlName="cibles_principales"]');

    // Protocole section
    this.protocoleCampanuleOui = page.locator('mat-radio-group[formControlName="protocole_dans_campanule"] mat-radio-button').first();
    this.protocoleCampanuleNon = page.locator('mat-radio-group[formControlName="protocole_dans_campanule"] mat-radio-button').nth(1);
    this.nomProtocoleInput = page.locator('input[formControlName="nom_protocole"]');
    this.nbEtpCycleInput = page.locator('input[formControlName="nb_etp_cycle"]');
    this.respectProtocoleOui = page.locator('mat-radio-group[formControlName="respect_protocole"] mat-radio-button').first();
    this.respectProtocoleNon = page.locator('mat-radio-group[formControlName="respect_protocole"] mat-radio-button').nth(1);
    this.justificationNonRespect = page.locator('textarea[formControlName="justification_non_respect"]');
    this.descriptionProtocole = page.locator('textarea[formControlName="description_protocole"]');
    this.objectifProtocole = page.locator('textarea[formControlName="objectif_protocole"]');
    this.periodeEchantillonnage = page.locator('input[formControlName="periode_echantillonnage"]');

    // Fréquence
    this.frequenceInput = page.locator('input[formControlName="frequence_nombre"]');
    this.frequenceDecrementBtn = page.locator('.frequence-number .freq-btn').first();
    this.frequenceIncrementBtn = page.locator('.frequence-number .freq-btn').nth(1);
    this.frequenceUniteSelect = page.locator('mat-select[formControlName="frequence_unite"]');

    // Bancarisation
    this.bancarisationSelect = page.locator('mat-select[formControlName="outil_bancarisation"]');
    this.outilSaisieSelect = page.locator('mat-select[formControlName="outil_saisie"]');
    this.transmissionDonneeOui = page.locator('mat-radio-group[formControlName="transmission_donnee"] mat-radio-button').first();
    this.transmissionDonneeNon = page.locator('mat-radio-group[formControlName="transmission_donnee"] mat-radio-button').nth(1);

    // Programmation
    this.sitesCheckboxes = page.locator('.sites-checkboxes mat-checkbox');
    this.programmationTable = page.locator('.programmation-table');
    this.duplicateBtn = page.locator('.duplicate-btn');

    // Détails
    this.descriptionTextarea = page.locator('textarea[formControlName="description"]');

    // Finances
    this.addFinanceBtn = page.locator('.finances-section .add-link-btn');
    this.financeRows = page.locator('.finance-row');

    // Action bar
    this.cancelBtn = page.locator('.btn-action-cancel');
    this.validateBtn = page.locator('.btn-action-validate');

    // Snackbar
    this.snackbar = page.locator('.mat-mdc-snack-bar-container, mat-snack-bar-container');
  }

  /** Navigate to create operation form for a plan. */
  async gotoCreate(planSlug: string, metriqueId?: number) {
    const url = metriqueId
      ? `/plans/${planSlug}/enjeux/operations/nouveau?metriqueId=${metriqueId}`
      : `/plans/${planSlug}/enjeux/operations/nouveau`;
    await this.page.goto(url);
  }

  /** Navigate to edit operation form. */
  async gotoEdit(planSlug: string, operationId: number) {
    await this.page.goto(`/plans/${planSlug}/enjeux/operations/${operationId}/modifier`);
  }

  /** Wait for form to be loaded (spinner gone, form visible, sections rendered). */
  async waitForForm() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 20000 }).catch(() => {});
    await this.libelleInput.or(this.errorBanner)
      .first().waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
    // Wait for Programmation section (always visible) to confirm full form is ready
    await this.sectionProgrammation.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
  }

  /** Select a CS-type action to reveal Protocole/Bancarisation sections. */
  async selectCSAction() {
    await this.typeActionInput.click();
    await this.typeActionInput.fill('CS');
    await this.page.waitForTimeout(300);
    const csOption = this.page.locator('.type-action-autocomplete mat-option').first();
    await csOption.waitFor({ state: 'visible', timeout: 5000 });
    await csOption.click();
    await this.page.waitForTimeout(500);
  }

  /** Fill the libelle field. */
  async fillLibelle(text: string) {
    await this.libelleInput.click();
    await this.libelleInput.fill(text);
  }

  /**
   * Fill the intitulé du suivi (visible only after selecting a CS-type action
   * with mode "nouveau suivi"). Required for CS actions to pass validation.
   */
  async fillIntituleSuivi(text: string) {
    await this.intituleSuiviInput.fill(text);
  }

  /** Select the first available type d'action option from the autocomplete. */
  async selectFirstTypeAction() {
    await this.typeActionInput.click();
    await this.typeActionInput.fill('');
    await this.page.waitForTimeout(300);
    await this.page.locator('.type-action-autocomplete mat-option').first().waitFor({ state: 'visible', timeout: 5000 });
    await this.page.locator('.type-action-autocomplete mat-option').first().click();
  }

  /** Search and select a type d'action by text. */
  async selectTypeAction(searchText: string) {
    await this.typeActionInput.click();
    await this.typeActionInput.fill(searchText);
    await this.page.waitForTimeout(300);
    await this.page.locator('.type-action-autocomplete mat-option').first().waitFor({ state: 'visible', timeout: 5000 });
    await this.page.locator('.type-action-autocomplete mat-option').first().click();
  }

  /** Select a priority radio button by index (0-based). */
  async selectPriority(index: number) {
    await this.prioriteRadioGroup.locator('mat-radio-button').nth(index).click();
  }

  /** Set protocole mode to non-campanule and fill basic protocol fields. */
  async fillProtocoleNonCampanule(nom: string, opts?: { description?: string; objectif?: string; periode?: string }) {
    await this.protocoleCampanuleNon.click();
    await this.page.waitForTimeout(300);
    await this.nomProtocoleInput.fill(nom);
    await this.nbEtpCycleInput.fill('1');
    if (opts?.description) {
      await this.descriptionProtocole.fill(opts.description);
    }
    if (opts?.objectif) {
      await this.objectifProtocole.fill(opts.objectif);
    }
    if (opts?.periode) {
      await this.periodeEchantillonnage.fill(opts.periode);
    }
  }

  /** Set respect protocole to Yes. */
  async setRespectProtocoleOui() {
    await this.respectProtocoleOui.click();
  }

  /** Set respect protocole to No. */
  async setRespectProtocoleNon() {
    await this.respectProtocoleNon.click();
  }

  /** Set frequency (number + unit). */
  async setFrequence(nombre: number, unite: string) {
    await this.frequenceInput.fill(nombre.toString());
    await this.frequenceUniteSelect.click();
    await this.page.locator('mat-option').filter({ hasText: new RegExp(unite, 'i') }).first().click();
  }

  /** Select the first available site checkbox. */
  async selectFirstSite() {
    await this.sitesCheckboxes.first().click();
  }

  /** Add a finance row. */
  async addFinance(libelle: string) {
    await this.addFinanceBtn.click();
    await this.page.waitForTimeout(200);
    const lastRow = this.financeRows.last();
    await lastRow.locator('input[matInput]').fill(libelle);
  }

  /** Click Validate to submit the form. */
  async submit() {
    await this.validateBtn.click();
  }

  /** Click Cancel to go back. */
  async cancel() {
    await this.cancelBtn.click();
  }

  /** Wait for the snackbar to appear with expected text. */
  async waitForSnackbar(textPattern?: RegExp) {
    await this.snackbar.waitFor({ state: 'visible', timeout: 10000 });
    if (textPattern) {
      await this.page.locator('.mat-mdc-snack-bar-label, .mdc-snackbar__label')
        .filter({ hasText: textPattern })
        .waitFor({ state: 'visible', timeout: 5000 });
    }
  }

  /** Fill description in the Détails section. */
  async fillDescription(text: string) {
    await this.descriptionTextarea.fill(text);
  }

  /** Check if the form contains a validation error for required libelle. */
  async hasLibelleError(): Promise<boolean> {
    return this.page.locator('mat-error').isVisible().catch(() => false);
  }
}
