import { type Page, type Locator } from '@playwright/test';

export class AdminOrganismesPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly searchInput: Locator;
  readonly addOrganismeButton: Locator;
  readonly organismeCards: Locator;
  readonly organismeDetail: Locator;
  readonly emptyState: Locator;
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('.page-header h1');
    this.searchInput = page.locator('.search-box input[type="text"]');
    this.addOrganismeButton = page.locator('button.btn-primary');
    this.organismeCards = page.locator('.organisme-card');
    this.organismeDetail = page.locator('.organisme-detail');
    this.emptyState = page.locator('.empty-state');
    this.loadingSpinner = page.locator('mat-spinner');
  }

  async goto() {
    await this.page.goto('/administration/organismes');
  }

  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    await Promise.race([
      this.organismeCards.first().waitFor({ state: 'visible', timeout: 10000 }),
      this.organismeDetail.waitFor({ state: 'visible', timeout: 10000 }),
      this.emptyState.waitFor({ state: 'visible', timeout: 10000 }),
    ]).catch(() => {});
  }

  async searchOrganisme(query: string) {
    await this.searchInput.fill(query);
  }

  getCardByName(name: string): Locator {
    return this.organismeCards.filter({ hasText: name });
  }

  getEditButton(card: Locator): Locator {
    return card.locator('button.btn-secondary');
  }
}
