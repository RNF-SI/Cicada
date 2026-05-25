import { type Page, type Locator } from '@playwright/test';

/**
 * Page Object for the Enjeu form page (create + edit).
 * Route create: /plans/{slug}/enjeux/nouveau
 * Route edit:   /plans/{slug}/enjeux/{enjeuSlug}/modifier
 */
export class EnjeuFormPage {
  readonly page: Page;

  // Page-level
  readonly heroTitle: Locator;
  readonly loadingSpinner: Locator;
  readonly errorBanner: Locator;

  // Main fields
  readonly libelleTextarea: Locator;
  readonly intituleCourtInput: Locator;
  readonly rangRadioGroup: Locator;
  readonly categorieEcologiqueRadio: Locator;
  readonly categorieSocioEcoRadio: Locator;

  // Ecological checkboxes
  readonly habitatCheckbox: Locator;
  readonly especeCheckbox: Locator;
  readonly patrimoineGeologiqueCheckbox: Locator;
  readonly fonctionnaliteEcosystemeCheckbox: Locator;
  readonly autreEcologiqueCheckbox: Locator;
  readonly autreEcologiquePrecision: Locator;
  readonly geoExSituCheckbox: Locator;
  readonly geoInSituCheckbox: Locator;

  // Socio-economic checkboxes
  readonly valeurPaysagereCheckbox: Locator;
  readonly patrimoineCulturelCheckbox: Locator;
  readonly developpementDurableCheckbox: Locator;
  readonly usagesCheckbox: Locator;
  readonly valeurAjouteeCheckbox: Locator;
  readonly autreSocioEcoCheckbox: Locator;
  readonly autreSocioEcoPrecision: Locator;

  // Reference lists
  readonly habitatRefList: Locator;
  readonly taxonRefList: Locator;
  readonly geologyRefList: Locator;

  // Details accordion
  readonly detailsPanel: Locator;
  readonly etatEnjeuTextarea: Locator;
  readonly descriptionTextarea: Locator;

  // Action bar
  readonly cancelBtn: Locator;
  readonly validateBtn: Locator;

  // Snackbar
  readonly snackbar: Locator;

  constructor(page: Page) {
    this.page = page;

    this.heroTitle = page.locator('.hero-title');
    this.loadingSpinner = page.locator('mat-spinner');
    this.errorBanner = page.locator('.error-banner');

    // Main fields
    this.libelleTextarea = page.locator('textarea[formControlName="libelle"]');
    this.intituleCourtInput = page.locator('input[formControlName="intitule_court"]');
    this.rangRadioGroup = page.locator('mat-radio-group[formControlName="rang"]');
    this.categorieEcologiqueRadio = page.locator('mat-radio-group[formControlName="categorie_ecologique"] mat-radio-button').first();
    this.categorieSocioEcoRadio = page.locator('mat-radio-group[formControlName="categorie_ecologique"] mat-radio-button').nth(1);

    // Ecological checkboxes
    this.habitatCheckbox = page.locator('app-checkbox[formControlName="habitat"]');
    this.especeCheckbox = page.locator('app-checkbox[formControlName="espece"]');
    this.patrimoineGeologiqueCheckbox = page.locator('app-checkbox[formControlName="patrimoine_geologique"]');
    this.fonctionnaliteEcosystemeCheckbox = page.locator('app-checkbox[formControlName="fonctionnalite_ecosysteme"]');
    this.autreEcologiqueCheckbox = page.locator('app-checkbox[formControlName="autre_ecologique"]');
    this.autreEcologiquePrecision = page.locator('input[formControlName="autre_ecologique_precision"]');
    this.geoExSituCheckbox = page.locator('app-checkbox[formControlName="geo_ex_situ"]');
    this.geoInSituCheckbox = page.locator('app-checkbox[formControlName="geo_in_situ"]');

    // Socio-economic checkboxes
    this.valeurPaysagereCheckbox = page.locator('app-checkbox[formControlName="valeur_paysagere"]');
    this.patrimoineCulturelCheckbox = page.locator('app-checkbox[formControlName="patrimoine_culturel"]');
    this.developpementDurableCheckbox = page.locator('app-checkbox[formControlName="developpement_durable"]');
    this.usagesCheckbox = page.locator('app-checkbox[formControlName="usages"]');
    this.valeurAjouteeCheckbox = page.locator('app-checkbox[formControlName="valeur_ajoutee"]');
    this.autreSocioEcoCheckbox = page.locator('app-checkbox[formControlName="autre_socioeco"]');
    this.autreSocioEcoPrecision = page.locator('input[formControlName="autre_socioeco_precision"]');

    // Reference lists
    this.habitatRefList = page.locator('app-reference-item-list[type="habitat"]');
    this.taxonRefList = page.locator('app-reference-item-list[type="taxon"]');
    this.geologyRefList = page.locator('app-reference-item-list[type="geology"]');

    // Details accordion
    this.detailsPanel = page.locator('.details-panel, mat-expansion-panel');
    this.etatEnjeuTextarea = page.locator('textarea[formControlName="etat_enjeu"]');
    this.descriptionTextarea = page.locator('textarea[formControlName="description"]');

    // Action bar
    this.cancelBtn = page.locator('.btn-action-cancel');
    this.validateBtn = page.locator('.btn-action-validate');

    this.snackbar = page.locator('.mat-mdc-snack-bar-container, mat-snack-bar-container');
  }

  async gotoCreate(planSlug: string) {
    await this.page.goto(`/plans/${planSlug}/enjeux/nouveau`);
  }

  async gotoEdit(planSlug: string, enjeuSlug: string) {
    await this.page.goto(`/plans/${planSlug}/enjeux/${enjeuSlug}/modifier`);
  }

  async waitForForm() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    await this.libelleTextarea.or(this.errorBanner)
      .first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
  }

  async fillLibelle(text: string) {
    await this.libelleTextarea.click();
    await this.libelleTextarea.fill(text);
  }

  async fillIntituleCourt(text: string) {
    await this.intituleCourtInput.fill(text);
  }

  async selectRang(rang: number) {
    await this.rangRadioGroup.locator('mat-radio-button').nth(rang - 1).click();
  }

  async selectEcological() {
    await this.categorieEcologiqueRadio.click();
    await this.page.waitForTimeout(300);
  }

  async selectSocioEconomic() {
    await this.categorieSocioEcoRadio.click();
    await this.page.waitForTimeout(300);
  }

  async submit() {
    await this.validateBtn.click();
  }

  async cancel() {
    await this.cancelBtn.click();
  }

  async waitForSnackbar() {
    await this.snackbar.waitFor({ state: 'visible', timeout: 10000 });
  }

  async expandDetailsPanel() {
    const panelHeader = this.detailsPanel.locator('mat-expansion-panel-header');
    await panelHeader.click();
    await this.page.waitForTimeout(300);
  }
}
