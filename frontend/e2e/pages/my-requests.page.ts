import { type Page, type Locator } from '@playwright/test';

export class MyRequestsPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly subtitle: Locator;

  // Stats cards
  readonly pendingStatCard: Locator;
  readonly approvedStatCard: Locator;
  readonly rejectedStatCard: Locator;

  // Modules section
  readonly modulesSection: Locator;
  readonly moduleCards: Locator;

  // Requests table
  readonly requestsTable: Locator;
  readonly requestRows: Locator;
  readonly emptyState: Locator;
  readonly loadingSpinner: Locator;
  readonly backLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('.page-header h1');
    this.subtitle = page.locator('.page-header .subtitle');

    // Stats cards
    this.pendingStatCard = page.locator('.stat-card--pending');
    this.approvedStatCard = page.locator('.stat-card--approved');
    this.rejectedStatCard = page.locator('.stat-card--rejected');

    // Modules section
    this.modulesSection = page.locator('.modules-section');
    this.moduleCards = page.locator('.module-card');

    // Requests table
    this.requestsTable = page.locator('.requests-table');
    this.requestRows = page.locator('.requests-table tr[mat-row]');
    this.emptyState = page.locator('.empty-state');
    this.loadingSpinner = page.locator('mat-spinner');
    this.backLink = page.locator('.back-link');
  }

  async goto() {
    await this.page.goto('/mes-demandes');
  }

  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    // Wait for either table or empty state
    await Promise.race([
      this.requestRows.first().waitFor({ state: 'visible', timeout: 10000 }),
      this.emptyState.waitFor({ state: 'visible', timeout: 10000 }),
    ]).catch(() => {});
  }

  async getPendingCount(): Promise<string> {
    return this.pendingStatCard.locator('.stat-value').textContent() || '0';
  }

  async getApprovedCount(): Promise<string> {
    return this.approvedStatCard.locator('.stat-value').textContent() || '0';
  }

  async getRejectedCount(): Promise<string> {
    return this.rejectedStatCard.locator('.stat-value').textContent() || '0';
  }

  async getRequestCount(): Promise<number> {
    return this.requestRows.count();
  }

  getRequestByTarget(target: string): Locator {
    return this.requestRows.filter({ hasText: target });
  }

  async cancelRequest(target: string) {
    const row = this.getRequestByTarget(target);
    const cancelButton = row.locator('button[color="warn"]');
    await cancelButton.click();
  }

  async requestModuleAccess(moduleName: string) {
    const moduleCard = this.moduleCards.filter({ hasText: moduleName });
    const requestButton = moduleCard.locator('button', { hasText: 'Demander' });
    await requestButton.click();
  }

  async hasEmptyState(): Promise<boolean> {
    return this.emptyState.isVisible().catch(() => false);
  }

  async hasModulesSection(): Promise<boolean> {
    return this.modulesSection.isVisible().catch(() => false);
  }
}
