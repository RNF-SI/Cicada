import { type Page, type Locator, expect } from '@playwright/test';

export class PlanCreatePage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly loadingSpinner: Locator;
  readonly breadcrumb: Locator;
  readonly breadcrumbPlansLink: Locator;
  readonly breadcrumbCurrent: Locator;
  readonly formCard: Locator;
  readonly errorBanner: Locator;
  readonly requiredNote: Locator;

  // Form fields — required
  readonly nomInput: Locator;
  readonly rangInput: Locator;
  readonly anneeDebutInput: Locator;
  readonly anneeFinInput: Locator;

  // Form fields — optional
  readonly surfaceInput: Locator;
  readonly dateValidationCspnInput: Locator;
  readonly docGestionInput: Locator;
  readonly redacteurTypeSelect: Locator;

  // Sites selection
  readonly sitesSection: Locator;
  readonly siteSearchInput: Locator;
  readonly siteItems: Locator;
  readonly siteCheckboxes: Locator;
  readonly siteCountBadge: Locator;
  readonly noSiteMessage: Locator;
  readonly createSiteLink: Locator;

  // CT88 radio buttons
  readonly ct88RadioGroup: Locator;
  readonly ct88Yes: Locator;
  readonly ct88No: Locator;

  // Organisme rédacteur
  readonly organismeSection: Locator;
  readonly organismeInput: Locator;
  readonly organismeChip: Locator;
  readonly organismeRemoveBtn: Locator;

  // Rédacteurs (chips hybrides)
  readonly redacteursChips: Locator;
  readonly redacteursInput: Locator;

  // Relecteurs (chips hybrides)
  readonly relecteursChips: Locator;
  readonly relecteursInput: Locator;

  // Autocomplete
  readonly autocompletePanel: Locator;
  readonly autocompleteOptions: Locator;

  // Action buttons
  readonly submitButton: Locator;
  readonly cancelButton: Locator;

  // Validation errors
  readonly errorMessages: Locator;

  // Snackbar
  readonly snackbar: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1').first();
    this.loadingSpinner = page.locator('mat-spinner');
    this.breadcrumb = page.locator('nav.breadcrumb');
    this.breadcrumbPlansLink = page.locator('nav.breadcrumb .breadcrumb-link');
    this.breadcrumbCurrent = page.locator('nav.breadcrumb .breadcrumb-current');
    this.formCard = page.locator('.form-card');
    this.errorBanner = page.locator('.error-banner');
    this.requiredNote = page.locator('.required-note');

    // Required fields
    this.nomInput = page.locator('input[formControlName="nom"]');
    this.rangInput = page.locator('input[formControlName="rang"]');
    this.anneeDebutInput = page.locator('input[formControlName="annee_debut"]');
    this.anneeFinInput = page.locator('input[formControlName="annee_fin"]');

    // Optional fields
    this.surfaceInput = page.locator('input[formControlName="surface"]');
    this.dateValidationCspnInput = page.locator('input[formControlName="date_validation_cspn"]');
    this.docGestionInput = page.locator('input[formControlName="id_docgestion_fcen"]');
    this.redacteurTypeSelect = page.locator('mat-select[formControlName="id_redacteur_type"]');

    // Sites selection
    this.sitesSection = page.locator('.sites-section');
    this.siteSearchInput = page.locator('.search-box input');
    this.siteItems = page.locator('.selection-item');
    this.siteCheckboxes = page.locator('.selection-item mat-checkbox');
    this.siteCountBadge = page.locator('.sites-section .count-badge');
    this.noSiteMessage = page.locator('.no-items');
    this.createSiteLink = page.locator('.sites-hint a');

    // CT88 radio
    this.ct88RadioGroup = page.locator('mat-radio-group[formControlName="ct88"]');
    this.ct88Yes = page.locator('mat-radio-button').filter({ hasText: 'Oui' });
    this.ct88No = page.locator('mat-radio-button').filter({ hasText: 'Non' });

    // Organisme rédacteur
    this.organismeSection = page.locator('.organisme-section');
    this.organismeInput = page.locator('.organisme-section input[matInput]');
    this.organismeChip = page.locator('.selected-organisme mat-chip-row');
    this.organismeRemoveBtn = page.locator('.selected-organisme button[matChipRemove]');

    // Rédacteurs
    this.redacteursChips = page.locator('[data-testid="redacteurs-input"]').locator('..').locator('mat-chip-row');
    this.redacteursInput = page.locator('[data-testid="redacteurs-input"]');

    // Relecteurs
    this.relecteursChips = page.locator('[data-testid="relecteurs-input"]').locator('..').locator('mat-chip-row');
    this.relecteursInput = page.locator('[data-testid="relecteurs-input"]');

    // Autocomplete panel (shared, only one visible at a time)
    this.autocompletePanel = page.locator('.mat-mdc-autocomplete-panel');
    this.autocompleteOptions = page.locator('mat-option');

    // Action bar buttons
    this.submitButton = page.locator('.action-bar button[color="primary"]');
    this.cancelButton = page.locator('.action-bar button[mat-stroked-button]');

    // Error messages
    this.errorMessages = page.locator('mat-error');

    // Snackbar
    this.snackbar = page.locator('mat-snack-bar-container');
  }

  async goto() {
    await this.page.goto('/plans/nouveau');
  }

  async waitForForm() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    await this.formCard.waitFor({ state: 'visible', timeout: 10000 });
  }

  async fillForm(data: {
    nom?: string;
    rang?: number;
    anneeDebut?: number;
    anneeFin?: number;
    surface?: number;
    ct88?: boolean;
    docGestion?: string;
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
    if (data.docGestion !== undefined) {
      await this.docGestionInput.fill(data.docGestion);
    }
  }

  /** Select a site by clicking its row (searches first then clicks) */
  async selectSiteByName(name: string) {
    await this.siteSearchInput.fill(name);
    const siteItem = this.siteItems.filter({ hasText: name }).first();
    await siteItem.waitFor({ state: 'visible', timeout: 5000 });
    await siteItem.click();
    // Wait for the selection to be visually confirmed (selected class) before clearing search
    await expect(siteItem).toHaveClass(/selected/, { timeout: 3000 });
    // Clear search to show all sites again
    await this.siteSearchInput.fill('');
  }

  /** Deselect a site by name (searches first then clicks the selected site) */
  async deselectSiteByName(name: string) {
    await this.siteSearchInput.fill(name);
    const siteItem = this.siteItems.filter({ hasText: name }).first();
    await siteItem.waitFor({ state: 'visible', timeout: 5000 });
    await siteItem.click();
    await this.siteSearchInput.fill('');
  }

  /** Get the text of the sites count badge */
  async getSiteCountBadgeText(): Promise<string> {
    return (await this.siteCountBadge.textContent() ?? '').trim();
  }

  /** Get the error banner text */
  async getErrorBannerText(): Promise<string> {
    return (await this.errorBanner.textContent() ?? '').trim();
  }

  /** Select a redacteur type from the dropdown */
  async selectRedacteurType(label: string) {
    await this.redacteurTypeSelect.click();
    const option = this.page.locator('mat-option').filter({ hasText: label });
    await option.waitFor({ state: 'visible', timeout: 5000 });
    await option.click();
  }

  /** Add a free text redacteur (type + Enter) */
  async addRedacteurFreeText(text: string) {
    await this.redacteursInput.focus();
    await this.redacteursInput.fill(text);
    await this.redacteursInput.press('Enter');
  }

  /** Add a free text relecteur (type + Enter) */
  async addRelecteurFreeText(text: string) {
    await this.relecteursInput.focus();
    await this.relecteursInput.fill(text);
    await this.relecteursInput.press('Enter');
  }

  /** Get all chip texts from a chip locator */
  async getChipTexts(chipsLocator: Locator): Promise<string[]> {
    const texts: string[] = [];
    const count = await chipsLocator.count();
    for (let i = 0; i < count; i++) {
      const text = await chipsLocator.nth(i).textContent();
      if (text) texts.push(text.trim());
    }
    return texts;
  }

  /** Set an organisme as free text (type + Enter) */
  async setOrganismeFreeText(text: string) {
    await this.organismeInput.focus();
    await this.organismeInput.fill(text);
    await this.organismeInput.press('Enter');
  }

  /** Clear the selected organisme */
  async clearOrganisme() {
    await this.organismeRemoveBtn.click();
  }

  /** Remove a chip via its remove button */
  async removeChip(chipLocator: Locator) {
    const removeBtn = chipLocator.locator('button[matChipRemove]');
    await removeBtn.click();
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
