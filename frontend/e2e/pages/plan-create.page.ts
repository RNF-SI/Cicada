import { type Page, type Locator } from '@playwright/test';

export class PlanCreatePage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly loadingSpinner: Locator;
  readonly breadcrumb: Locator;
  readonly formCard: Locator;
  readonly errorBanner: Locator;
  readonly requiredNote: Locator;

  // Form fields
  readonly nomInput: Locator;
  readonly rangInput: Locator;
  readonly surfaceInput: Locator;
  readonly anneeDebutInput: Locator;
  readonly anneeFinInput: Locator;

  // Sites selection
  readonly sitesSection: Locator;
  readonly siteSearchInput: Locator;
  readonly siteItems: Locator;
  readonly siteCheckboxes: Locator;

  // CT88 radio buttons
  readonly ct88RadioGroup: Locator;
  readonly ct88Yes: Locator;
  readonly ct88No: Locator;

  // Action buttons
  readonly submitButton: Locator;
  readonly cancelButton: Locator;

  // Validation errors
  readonly errorMessages: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1').first();
    this.loadingSpinner = page.locator('mat-spinner');
    this.breadcrumb = page.locator('nav.breadcrumb');
    this.formCard = page.locator('.form-card');
    this.errorBanner = page.locator('.error-banner');
    this.requiredNote = page.locator('.required-note');

    // Form fields (Angular reactive forms use formControlName)
    this.nomInput = page.locator('input[formControlName="nom"]');
    this.rangInput = page.locator('input[formControlName="rang"]');
    this.surfaceInput = page.locator('input[formControlName="surface"]');
    this.anneeDebutInput = page.locator('input[formControlName="annee_debut"]');
    this.anneeFinInput = page.locator('input[formControlName="annee_fin"]');

    // Sites selection
    this.sitesSection = page.locator('.sites-section');
    this.siteSearchInput = page.locator('.search-box input');
    this.siteItems = page.locator('.selection-item');
    this.siteCheckboxes = page.locator('.selection-item mat-checkbox');

    // CT88 radio
    this.ct88RadioGroup = page.locator('mat-radio-group[formControlName="ct88"]');
    this.ct88Yes = page.locator('mat-radio-button').filter({ hasText: 'Oui' });
    this.ct88No = page.locator('mat-radio-button').filter({ hasText: 'Non' });

    // Action bar buttons
    this.submitButton = page.locator('.action-bar button[color="primary"]');
    this.cancelButton = page.locator('.action-bar button[mat-stroked-button]');

    // Error messages
    this.errorMessages = page.locator('mat-error');
  }

  async goto() {
    await this.page.goto('/plans/nouveau');
  }

  async waitForForm() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    await this.formCard.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
  }

  async fillForm(data: {
    nom?: string;
    rang?: number;
    anneeDebut?: number;
    anneeFin?: number;
    surface?: number;
    ct88?: boolean;
  }) {
    if (data.nom !== undefined) {
      await this.nomInput.fill(data.nom);
    }
    if (data.rang !== undefined) {
      await this.rangInput.fill(String(data.rang));
    }
    if (data.anneeDebut !== undefined) {
      await this.anneeDebutInput.fill(String(data.anneeDebut));
    }
    if (data.anneeFin !== undefined) {
      await this.anneeFinInput.fill(String(data.anneeFin));
    }
    if (data.surface !== undefined) {
      await this.surfaceInput.fill(String(data.surface));
    }
    if (data.ct88 !== undefined) {
      if (data.ct88) {
        await this.ct88Yes.click();
      } else {
        await this.ct88No.click();
      }
    }
  }

  async selectSite(name: string) {
    // Search for the site
    const searchVisible = await this.siteSearchInput.isVisible().catch(() => false);
    if (searchVisible) {
      await this.siteSearchInput.fill(name);
      await this.page.waitForTimeout(300);
    }
    // Click the matching site item
    const siteItem = this.siteItems.filter({ hasText: name }).first();
    const isVisible = await siteItem.isVisible().catch(() => false);
    if (isVisible) {
      await siteItem.click();
    }
  }

  async submit() {
    await this.submitButton.click();
  }

  async getErrors(): Promise<string[]> {
    const errors: string[] = [];
    const count = await this.errorMessages.count();
    for (let i = 0; i < count; i++) {
      const text = await this.errorMessages.nth(i).textContent();
      if (text) errors.push(text.trim());
    }
    return errors;
  }
}
