import { type Page, type Locator } from '@playwright/test';

/**
 * Page Object for the Suivi/Inventaire form — create and edit modes.
 * Route create: /inventaires/nouveau
 * Route edit:   /inventaires/{suiviId}/modifier
 */
export class InventaireFormPage {
  readonly page: Page;

  // Page-level
  readonly heroTitle: Locator;
  readonly loadingSpinner: Locator;
  readonly errorBanner: Locator;
  readonly infoBlock: Locator;

  // Main card fields
  readonly intituleInput: Locator;
  readonly typeActionInput: Locator;
  readonly integrePgOui: Locator;
  readonly integrePgNon: Locator;
  readonly objectifPrincipalSelect: Locator;
  readonly ciblesPrincipalesSelect: Locator;
  readonly dateLancementInput: Locator;
  readonly statutSelect: Locator;
  readonly anneeFinInput: Locator;

  // Section headers
  readonly sectionProtocole: Locator;
  readonly sectionBancarisation: Locator;
  readonly sectionDetails: Locator;

  // Protocole section
  readonly protocoleCampanuleOui: Locator;
  readonly protocoleCampanuleNon: Locator;
  readonly nomProtocoleInput: Locator;
  readonly respectProtocoleOui: Locator;
  readonly respectProtocoleNon: Locator;
  readonly nbEtpCycleInput: Locator;
  readonly descriptionProtocole: Locator;
  readonly objectifProtocole: Locator;
  readonly periodeEchantillonnage: Locator;
  readonly frequenceInput: Locator;
  readonly frequenceDecrementBtn: Locator;
  readonly frequenceIncrementBtn: Locator;

  // Bancarisation
  readonly bancarisationSelect: Locator;
  readonly outilSaisieSelect: Locator;
  readonly transmissionDonneeOui: Locator;
  readonly transmissionDonneeNon: Locator;

  // Détails
  readonly commentairesTextarea: Locator;

  // Action bar
  readonly cancelBtn: Locator;
  readonly saveBtn: Locator;

  // Snackbar
  readonly snackbar: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heroTitle = page.locator('.hero-title');
    this.loadingSpinner = page.locator('mat-spinner');
    this.errorBanner = page.locator('.error-banner');
    this.infoBlock = page.locator('.info-block');

    // Main card
    this.intituleInput = page.locator('input[formControlName="intitule"]');
    this.typeActionInput = page.locator('mat-form-field').filter({ hasText: /type/i }).locator('input[matInput]').first();
    this.integrePgOui = page.locator('mat-radio-group[formControlName="integre_plan_gestion"] mat-radio-button').first();
    this.integrePgNon = page.locator('mat-radio-group[formControlName="integre_plan_gestion"] mat-radio-button').nth(1);
    this.objectifPrincipalSelect = page.locator('mat-select[formControlName="objectif_principal"]');
    this.ciblesPrincipalesSelect = page.locator('mat-select[formControlName="cibles_principales"]');
    this.dateLancementInput = page.locator('input[formControlName="date_lancement_suivi"]');
    this.statutSelect = page.locator('mat-select[formControlName="id_statut"]');
    this.anneeFinInput = page.locator('input[formControlName="annee_fin_suivi"]');

    // Section headers
    this.sectionProtocole = page.locator('.section-header').filter({ hasText: /protocole/i });
    this.sectionBancarisation = page.locator('.section-header').filter({ hasText: /bancarisation/i });
    this.sectionDetails = page.locator('.section-header').filter({ hasText: /détail/i });

    // Protocole
    this.protocoleCampanuleOui = page.locator('mat-radio-group[formControlName="protocole_dans_campanule"] mat-radio-button').first();
    this.protocoleCampanuleNon = page.locator('mat-radio-group[formControlName="protocole_dans_campanule"] mat-radio-button').nth(1);
    this.nomProtocoleInput = page.locator('input[formControlName="nom_protocole"]');
    this.respectProtocoleOui = page.locator('mat-radio-group[formControlName="respect_protocole"] mat-radio-button').first();
    this.respectProtocoleNon = page.locator('mat-radio-group[formControlName="respect_protocole"] mat-radio-button').nth(1);
    this.nbEtpCycleInput = page.locator('input[formControlName="nb_etp_cycle"]');
    this.descriptionProtocole = page.locator('textarea[formControlName="description_protocole"]');
    this.objectifProtocole = page.locator('textarea[formControlName="objectif_protocole"]');
    this.periodeEchantillonnage = page.locator('input[formControlName="periode_echantillonnage"]');
    this.frequenceInput = page.locator('input[formControlName="frequence_nombre"]');
    this.frequenceDecrementBtn = page.locator('.frequence-number .freq-btn').first();
    this.frequenceIncrementBtn = page.locator('.frequence-number .freq-btn').nth(1);

    // Bancarisation
    this.bancarisationSelect = page.locator('mat-select[formControlName="outil_bancarisation"]');
    this.outilSaisieSelect = page.locator('mat-select[formControlName="outil_saisie"]');
    this.transmissionDonneeOui = page.locator('mat-radio-group[formControlName="transmission_donnee"] mat-radio-button').first();
    this.transmissionDonneeNon = page.locator('mat-radio-group[formControlName="transmission_donnee"] mat-radio-button').nth(1);

    // Détails
    this.commentairesTextarea = page.locator('textarea[formControlName="commentaires"]');

    // Action bar
    this.cancelBtn = page.locator('.btn-action-cancel');
    this.saveBtn = page.locator('.btn-action-validate');

    // Snackbar
    this.snackbar = page.locator('.mat-mdc-snack-bar-container, mat-snack-bar-container');
  }

  async gotoCreate() {
    await this.page.goto('/inventaires/nouveau');
  }

  async gotoEdit(suiviId: number) {
    await this.page.goto(`/inventaires/${suiviId}/modifier`);
  }

  async gotoList() {
    await this.page.goto('/inventaires');
  }

  async waitForForm() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    await this.page.locator('form').or(this.intituleInput).or(this.errorBanner)
      .first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
  }

  async fillIntitule(text: string) {
    await this.intituleInput.click();
    await this.intituleInput.fill(text);
  }

  async selectFirstTypeSuivi() {
    await this.typeActionInput.click();
    await this.typeActionInput.fill('');
    await this.page.waitForTimeout(300);
    await this.page.locator('.type-action-autocomplete mat-option').first().waitFor({ state: 'visible', timeout: 5000 });
    await this.page.locator('.type-action-autocomplete mat-option').first().click();
  }

  async selectFirstObjectifPrincipal() {
    await this.objectifPrincipalSelect.click();
    await this.page.locator('mat-option').filter({ hasNotText: '—' }).first().click();
  }

  async selectFirstCiblePrincipale() {
    await this.ciblesPrincipalesSelect.click();
    await this.page.locator('mat-option').filter({ hasNotText: '—' }).first().click();
  }

  async fillDateLancement(date: string) {
    await this.dateLancementInput.fill(date);
  }

  async fillProtocoleNonCampanule(nom: string) {
    await this.protocoleCampanuleNon.click();
    await this.page.waitForTimeout(300);
    await this.nomProtocoleInput.fill(nom);
    await this.nbEtpCycleInput.fill('1');
  }

  /**
   * Fill all fields required by the conditional validators :
   * intitule, integre_plan_gestion=Non, objectif_principal, cibles_principales,
   * date_lancement_suivi, protocole_dans_campanule=Non, nom_protocole,
   * respect_protocole=Oui, documentation_disponible=Non, nb_etp_cycle, frequence.
   * After this call, the form is in a state that should pass validation.
   */
  async fillAllRequiredFields(intitule: string) {
    await this.fillIntitule(intitule);
    // integre_plan_gestion=Non (évite d'avoir à choisir suit_indicateur)
    await this.integrePgNon.click();
    await this.page.waitForTimeout(200);
    await this.selectFirstObjectifPrincipal();
    await this.selectFirstCiblePrincipale();
    await this.fillDateLancement('01/06/2024');
    // Protocole hors-CAMPanule (mode le plus simple)
    await this.protocoleCampanuleNon.click();
    await this.page.waitForTimeout(300);
    await this.nomProtocoleInput.fill('Protocole E2E');
    await this.nbEtpCycleInput.fill('1');
    await this.respectProtocoleOui.click();
    // documentation_disponible=Non
    await this.page.locator('mat-radio-group[formControlName="documentation_disponible"] mat-radio-button').nth(1).click();
    // Fréquence : 1 fois par AN
    await this.frequenceInput.fill('1');
    await this.page.locator('mat-select[formControlName="frequence_unite"]').click();
    // Nomenclature `AN` is labelled "Ans" (cf. seed FREQUENCE_EMBOITEMENT)
    await this.page.locator('mat-option').filter({ hasText: /^Ans?$/i }).first().click();
  }

  async submit() {
    await this.saveBtn.click();
  }

  async cancel() {
    await this.cancelBtn.click();
  }

  async waitForSnackbar(textPattern?: RegExp) {
    await this.snackbar.waitFor({ state: 'visible', timeout: 10000 });
    if (textPattern) {
      await this.page.locator('.mat-mdc-snack-bar-label, .mdc-snackbar__label')
        .filter({ hasText: textPattern })
        .waitFor({ state: 'visible', timeout: 5000 });
    }
  }

  async hasIntituleError(): Promise<boolean> {
    // Soit un mat-error inline (ancien comportement), soit la nouvelle bannière
    // qui liste les champs manquants après un submit invalide (#197 / a0c6ddc).
    const matError = await this.page.locator('mat-error').first().isVisible().catch(() => false);
    if (matError) return true;
    const banner = await this.page.locator('.error-banner').first().isVisible().catch(() => false);
    return banner;
  }
}
