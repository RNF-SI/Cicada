import { type Page, type Locator } from '@playwright/test';

/**
 * Page Object for the FCR form page (create + edit).
 * Route create: /plans/{slug}/enjeux/fcr/nouveau
 * Route edit:   /plans/{slug}/enjeux/fcr/{fcrId}/modifier
 */
export class FcrFormPage {
  readonly page: Page;

  // Page-level
  readonly heroTitle: Locator;
  readonly loadingSpinner: Locator;
  readonly errorBanner: Locator;

  // Main fields
  readonly libelleTextarea: Locator;
  readonly intituleCourtInput: Locator;
  readonly categorieRadioGroup: Locator;

  // Details accordion
  readonly detailsPanel: Locator;
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

    this.libelleTextarea = page.locator('textarea[formControlName="libelle"]');
    this.intituleCourtInput = page.locator('input[formControlName="intitule_court"]');
    this.categorieRadioGroup = page.locator('mat-radio-group[formControlName="id_categorie_fcr"]');

    this.detailsPanel = page.locator('.details-panel, mat-expansion-panel');
    this.descriptionTextarea = page.locator('textarea[formControlName="description"]');

    this.cancelBtn = page.locator('.btn-action-cancel');
    this.validateBtn = page.locator('.btn-action-validate');

    this.snackbar = page.locator('.mat-mdc-snack-bar-container, mat-snack-bar-container');
  }

  async gotoCreate(planSlug: string) {
    await this.page.goto(`/plans/${planSlug}/enjeux/fcr/nouveau`);
  }

  async gotoEdit(planSlug: string, fcrId: number) {
    await this.page.goto(`/plans/${planSlug}/enjeux/fcr/${fcrId}/modifier`);
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

  async selectFirstCategorie() {
    await this.categorieRadioGroup.locator('mat-radio-button').first().click();
  }

  async selectCategorie(index: number) {
    await this.categorieRadioGroup.locator('mat-radio-button').nth(index).click();
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
}
