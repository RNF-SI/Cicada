import { type Page, type Locator } from '@playwright/test';

export class AdminSitesPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly searchInput: Locator;
  readonly typeFilter: Locator;
  readonly organismeFilter: Locator;
  readonly addSiteButton: Locator;
  readonly tableRows: Locator;
  readonly emptyState: Locator;
  readonly loadingSpinner: Locator;
  readonly summaryText: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('.page-header h1');
    this.searchInput = page.locator('.filters-bar input[type="text"]');
    // #592 — filtres kit UI adressés par data-testid (cf. admin-users.page.ts).
    this.typeFilter = page.getByTestId('sites-type');
    this.organismeFilter = page.getByTestId('sites-organisme');
    this.addSiteButton = page.locator('button.btn-primary');
    this.tableRows = page.locator('.sites-table tbody tr');
    this.emptyState = page.locator('.empty-cell');
    this.loadingSpinner = page.locator('mat-spinner');
    this.summaryText = page.locator('.summary-text');
  }

  async goto() {
    await this.page.goto('/administration/sites');
  }

  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    await Promise.race([
      this.tableRows.first().waitFor({ state: 'visible', timeout: 10000 }),
      this.emptyState.waitFor({ state: 'visible', timeout: 10000 }),
    ]).catch(() => {});
  }

  async searchSite(query: string) {
    await this.searchInput.fill(query);
  }

  async filterByType(type: string) {
    await this.typeFilter.click();
    await this.page.getByTestId(`sites-type-option-${type}`).click();
  }

  async filterByOrganisme(organismeId: number | string) {
    await this.organismeFilter.click();
    await this.page.getByTestId(`sites-organisme-option-${organismeId}`).click();
  }

  getRowByName(name: string): Locator {
    return this.tableRows.filter({ hasText: name });
  }

  async getRowCount(): Promise<number> {
    return this.tableRows.count();
  }
}
