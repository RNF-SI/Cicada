import { type Page, type Locator } from '@playwright/test';

export class EnjeuxPage {
  readonly page: Page;

  // Page-level elements
  readonly pageTitle: Locator;
  readonly loadingSpinner: Locator;
  readonly errorContainer: Locator;

  // Breadcrumb
  readonly breadcrumb: Locator;
  readonly breadcrumbHome: Locator;
  readonly breadcrumbLinks: Locator;
  readonly breadcrumbCurrent: Locator;

  // List view
  readonly emptyState: Locator;
  readonly emptyText: Locator;
  readonly countText: Locator;
  readonly enjeuAccordions: Locator;
  readonly fcrAccordions: Locator;
  readonly addButton: Locator;
  readonly addMenuEnjeu: Locator;
  readonly addMenuFcr: Locator;

  // Detail view
  readonly enjeuMainTitle: Locator;
  readonly enjeuDetailCard: Locator;
  readonly cardSectionName: Locator;
  readonly cardDetailBody: Locator;
  readonly propertyLines: Locator;
  readonly tabs: Locator;
  readonly tabDetail: Locator;
  readonly tabOlt: Locator;
  readonly tabOperations: Locator;

  // Facteurs d'influence (detail view)
  readonly facteurCards: Locator;
  readonly addFacteurButton: Locator;
  readonly facteurInlineForm: Locator;

  // Pressions (detail view)
  readonly pressionCards: Locator;

  // Inline forms
  readonly inlineForms: Locator;
  readonly inlineFormLibelleInput: Locator;
  readonly inlineFormDescriptionInput: Locator;
  readonly inlineFormSaveButton: Locator;
  readonly inlineFormCancelButton: Locator;

  // Confirm dialog
  readonly confirmDialog: Locator;
  readonly confirmButton: Locator;
  readonly cancelButton: Locator;

  // Sidebar
  readonly sidebar: Locator;

  constructor(page: Page) {
    this.page = page;

    // Page-level elements
    this.pageTitle = page.locator('.plan-title');
    this.loadingSpinner = page.locator('mat-spinner');
    this.errorContainer = page.locator('.error-container');

    // Breadcrumb
    this.breadcrumb = page.locator('.breadcrumb');
    this.breadcrumbHome = page.locator('.breadcrumb-home');
    this.breadcrumbLinks = page.locator('.breadcrumb-link');
    this.breadcrumbCurrent = page.locator('.breadcrumb-current');

    // List view
    this.emptyState = page.locator('.empty-state');
    this.emptyText = page.locator('.empty-text');
    this.countText = page.locator('.count-text');
    this.enjeuAccordions = page.locator('app-enjeu-accordion:not([isfcr="true"]) .accordion:not(.fcr)');
    this.fcrAccordions = page.locator('app-enjeu-accordion .accordion.fcr');
    this.addButton = page.locator('.list-top-bar button[mat-stroked-button]');
    this.addMenuEnjeu = page.locator('mat-menu-item', { hasText: 'Enjeu' }).first();
    this.addMenuFcr = page.locator('mat-menu-item', { hasText: 'FCR' }).first();

    // Detail view
    this.enjeuMainTitle = page.locator('.enjeu-main-title');
    this.enjeuDetailCard = page.locator('.enjeu-detail-card');
    this.cardSectionName = page.locator('.card-section-name');
    this.cardDetailBody = page.locator('.card-detail-body');
    this.propertyLines = page.locator('.card-detail-body .property-line');
    this.tabs = page.locator('.tab-item');
    this.tabDetail = page.locator('.tab-item', { hasText: /Détail|Detail/ });
    this.tabOlt = page.locator('.tab-item', { hasText: /Vision.*long.*terme|OLT/ });
    this.tabOperations = page.locator('.tab-item', { hasText: /opération/i });

    // Facteurs d'influence
    this.facteurCards = page.locator('.facteur-influence-card');
    this.addFacteurButton = page.locator('.add-item-btn').first();
    this.facteurInlineForm = page.locator('.inline-form').filter({ has: page.locator('.facteur-bullet') });

    // Pressions
    this.pressionCards = page.locator('.pression-card');

    // Inline forms (general)
    this.inlineForms = page.locator('.inline-form');
    this.inlineFormLibelleInput = page.locator('.inline-form-body mat-form-field input[matInput]').first();
    this.inlineFormDescriptionInput = page.locator('.inline-form-body mat-form-field textarea[matInput]').first();
    this.inlineFormSaveButton = page.locator('.inline-form-actions button[mat-flat-button]');
    this.inlineFormCancelButton = page.locator('.inline-form-actions button[mat-stroked-button]');

    // Confirm dialog
    this.confirmDialog = page.locator('mat-dialog-container');
    this.confirmButton = page.locator('mat-dialog-container button[mat-flat-button]');
    this.cancelButton = page.locator('mat-dialog-container button[mat-stroked-button]');

    // Sidebar
    this.sidebar = page.locator('app-plan-sidebar');
  }

  /**
   * Navigate to the enjeux list for a given plan.
   * @param planSlugOrId - Plan slug (preferred) or numeric ID
   */
  async goto(planSlugOrId: string | number) {
    await this.page.goto(`/plans/${planSlugOrId}/enjeux`);
  }

  /**
   * Navigate to enjeu detail view.
   * @param planSlugOrId - Plan slug (preferred) or numeric ID
   * @param enjeuSlugOrId - Enjeu slug (preferred) or numeric ID
   */
  async gotoDetail(planSlugOrId: string | number, enjeuSlugOrId: string | number) {
    await this.page.goto(`/plans/${planSlugOrId}/enjeux/${enjeuSlugOrId}`);
  }

  /**
   * Wait for loading to complete and data to appear.
   */
  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 30000 }).catch(() => {});
    // Wait for either content or empty state or error
    await Promise.race([
      this.countText.waitFor({ state: 'visible', timeout: 15000 }),
      this.emptyState.waitFor({ state: 'visible', timeout: 15000 }),
      this.enjeuMainTitle.waitFor({ state: 'visible', timeout: 15000 }),
      this.errorContainer.waitFor({ state: 'visible', timeout: 15000 }),
    ]).catch(() => {});
  }

  /**
   * Get the number of enjeu accordion items (non-FCR).
   */
  async getEnjeuAccordionCount(): Promise<number> {
    return this.page.locator('[id^="enjeu-"]').count();
  }

  /**
   * Get the number of FCR accordion items.
   */
  async getFcrAccordionCount(): Promise<number> {
    return this.page.locator('[id^="fcr-"]').count();
  }

  /**
   * Get total accordion count (enjeux + FCR).
   */
  async getTotalAccordionCount(): Promise<number> {
    return this.page.locator('app-enjeu-accordion').count();
  }

  /**
   * Expand an accordion by its index (0-based, in DOM order).
   */
  async expandAccordion(index: number) {
    const accordion = this.page.locator('app-enjeu-accordion').nth(index);
    const header = accordion.locator('.accordion-header');
    const isExpanded = await accordion.locator('.accordion.expanded').isVisible().catch(() => false);
    if (!isExpanded) {
      await header.click();
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Collapse an accordion by its index.
   */
  async collapseAccordion(index: number) {
    const accordion = this.page.locator('app-enjeu-accordion').nth(index);
    const header = accordion.locator('.accordion-header');
    const isExpanded = await accordion.locator('.accordion.expanded').isVisible().catch(() => false);
    if (isExpanded) {
      await header.click();
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Click the "Ajouter" button to open the add menu.
   */
  async clickAddButton() {
    await this.addButton.click();
    await this.page.waitForTimeout(200);
  }

  /**
   * Click the add enjeu menu item.
   */
  async clickAddEnjeu() {
    await this.clickAddButton();
    await this.page.locator('.mat-mdc-menu-panel button', { hasText: 'Enjeu' }).first().click();
  }

  /**
   * Click the add FCR menu item.
   */
  async clickAddFcr() {
    await this.clickAddButton();
    await this.page.locator('.mat-mdc-menu-panel button', { hasText: 'FCR' }).first().click();
  }

  /**
   * Get accordion title text by index.
   */
  async getAccordionTitle(index: number): Promise<string> {
    return this.page.locator('app-enjeu-accordion').nth(index).locator('.accordion-title').innerText();
  }

  /**
   * Click "Voir les facteurs" button in an expanded accordion.
   */
  async clickViewFacteurs(accordionIndex: number) {
    const accordion = this.page.locator('app-enjeu-accordion').nth(accordionIndex);
    const viewBtn = accordion.locator('.btn-sm', { hasText: /facteur/i });
    await viewBtn.click();
  }

  /**
   * Get the count of facteur cards in the detail view.
   */
  async getFacteurCount(): Promise<number> {
    return this.facteurCards.count();
  }

  /**
   * Expand a facteur card by index.
   */
  async expandFacteur(index: number) {
    const facteur = this.facteurCards.nth(index);
    const isExpanded = await facteur.locator('.facteur-card-body').isVisible().catch(() => false);
    if (!isExpanded) {
      await facteur.locator('.facteur-card-header').click();
      await this.page.waitForTimeout(300);
    }
  }

  /**
   * Click the add facteur button to show the inline form.
   */
  async clickAddFacteur() {
    await this.addFacteurButton.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Fill the facteur inline form and save.
   */
  async addFacteur(libelle: string, description?: string) {
    const countBefore = await this.facteurCards.count();
    await this.clickAddFacteur();
    const form = this.page.locator('.inline-form').filter({ has: this.page.locator('.facteur-bullet') });
    await form.locator('input[matInput]').fill(libelle);
    if (description) {
      await form.locator('textarea[matInput]').fill(description);
    }
    await form.locator('.inline-form-actions button[mat-flat-button]').click();
    // Wait for the new card to appear instead of a fixed timeout
    await this.facteurCards.nth(countBefore).waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
  }

  /**
   * Click the edit button on a facteur card (pencil icon).
   */
  async clickEditFacteur(index: number) {
    const facteur = this.facteurCards.nth(index);
    await facteur.locator('.facteur-card-actions button .fi-rr-pencil').first().locator('..').click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Edit a facteur inline: click edit, fill fields, save.
   */
  async editFacteur(index: number, libelle: string, description?: string) {
    await this.clickEditFacteur(index);
    const form = this.facteurCards.nth(index).locator('.inline-form, .edit-inline-form').first();
    await form.locator('input[matInput]').fill(libelle);
    if (description !== undefined) {
      await form.locator('textarea[matInput]').fill(description);
    }
    await form.locator('button[mat-flat-button]').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Delete a facteur by index (clicks delete then confirms).
   */
  async deleteFacteur(index: number) {
    const facteur = this.facteurCards.nth(index);
    await facteur.locator('.facteur-card-actions button:has(i.fi-rr-trash)').click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Click the add pression button inside a facteur card.
   */
  async clickAddPression(facteurIndex: number) {
    const facteur = this.facteurCards.nth(facteurIndex);
    await facteur.locator('.add-item-btn').click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Fill the pression inline form and save.
   */
  async addPression(facteurIndex: number, libelle: string, description?: string) {
    const facteur = this.facteurCards.nth(facteurIndex);
    const countBefore = await facteur.locator('.pression-card').count();
    await this.clickAddPression(facteurIndex);
    const form = this.page.locator('.inline-form').filter({ has: this.page.locator('.pression-bullet') });
    await form.locator('input[matInput]').first().fill(libelle);
    if (description) {
      await form.locator('textarea[matInput]').fill(description);
    }
    await form.locator('.inline-form-actions button[mat-flat-button]').click();
    // Wait for the new pression card to appear
    await facteur.locator('.pression-card').nth(countBefore).waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
  }

  /**
   * Click the edit button on a pression card (pencil icon).
   */
  async clickEditPression(facteurIndex: number, pressionIndex: number) {
    const facteur = this.facteurCards.nth(facteurIndex);
    const pression = facteur.locator('.pression-card').nth(pressionIndex);
    await pression.locator('.pression-card-actions button .fi-rr-pencil').first().locator('..').click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Edit a pression inline: click edit, fill fields, save.
   */
  async editPression(facteurIndex: number, pressionIndex: number, libelle: string, description?: string) {
    await this.clickEditPression(facteurIndex, pressionIndex);
    const facteur = this.facteurCards.nth(facteurIndex);
    const form = facteur.locator('.pression-card').nth(pressionIndex).locator('.inline-form, .edit-inline-form').first();
    await form.locator('input[matInput]').first().fill(libelle);
    if (description !== undefined) {
      await form.locator('textarea[matInput]').fill(description);
    }
    await form.locator('button[mat-flat-button]').click();
    await this.page.waitForTimeout(500);
  }

  /**
   * Get the count of pression cards inside a facteur.
   */
  async getPressionCount(facteurIndex: number): Promise<number> {
    const facteur = this.facteurCards.nth(facteurIndex);
    return facteur.locator('.pression-card').count();
  }

  /**
   * Switch to a detail tab.
   */
  async switchTab(tab: 'detail' | 'olt' | 'operations') {
    const tabLocator = tab === 'detail' ? this.tabDetail
      : tab === 'olt' ? this.tabOlt
      : this.tabOperations;
    await tabLocator.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Confirm the delete dialog.
   */
  async confirmDelete() {
    await this.confirmButton.click();
    // Wait for the dialog to close
    await this.confirmButton.waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {});
    await this.page.waitForTimeout(300);
  }

  /**
   * Cancel the delete dialog.
   */
  async cancelDelete() {
    await this.cancelButton.click();
    await this.page.waitForTimeout(300);
  }

  /**
   * Check if empty state is shown.
   */
  async hasEmptyState(): Promise<boolean> {
    return this.emptyState.isVisible().catch(() => false);
  }

  /**
   * Get the facteurs summary count text from an expanded accordion.
   */
  async getFacteursSummaryCount(accordionIndex: number): Promise<string> {
    const accordion = this.page.locator('app-enjeu-accordion').nth(accordionIndex);
    return accordion.locator('.facteurs-count').innerText().catch(() => '');
  }

  /**
   * Navigate to enjeu detail by clicking on an accordion's "Voir les facteurs" button.
   */
  async navigateToDetail(accordionIndex: number) {
    const accordion = this.page.locator('app-enjeu-accordion').nth(accordionIndex);
    const detailBtn = accordion.locator('button', { hasText: /facteur|détail/i });
    await detailBtn.click();
    await this.waitForData();
  }
}
