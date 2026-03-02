import { type Page, type Locator } from '@playwright/test';

export class PlansListPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly loadingSpinner: Locator;
  readonly plansTable: Locator;
  readonly plansTableRows: Locator;
  readonly tabActifs: Locator;
  readonly tabInactifs: Locator;
  readonly scopeToggle: Locator;
  readonly createButton: Locator;
  readonly createMenuNewBlank: Locator;
  readonly emptyState: Locator;
  readonly pagination: Locator;
  readonly searchInput: Locator;
  readonly pendingSection: Locator;
  readonly requestAccessSection: Locator;
  readonly breadcrumb: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1').first();
    this.loadingSpinner = page.locator('mat-spinner');
    this.plansTable = page.locator('table.plans-table').first();
    this.plansTableRows = page.locator('table.plans-table tbody tr');
    this.tabActifs = page.locator('button.tab', { hasText: 'Actifs' });
    this.tabInactifs = page.locator('button.tab', { hasText: 'Inactifs' });
    this.scopeToggle = page.locator('app-view-scope-toggle');
    this.createButton = page.locator('.btn-create');
    this.createMenuNewBlank = page.locator('button', { hasText: 'Nouveau plan vierge' });
    this.emptyState = page.locator('.empty-icon').first();
    this.pagination = page.locator('.pagination');
    this.searchInput = page.locator('.search-field input[matInput]');
    this.pendingSection = page.locator('table.plans-table-pending');
    this.requestAccessSection = page.locator('.search-field');
    this.breadcrumb = page.locator('nav.breadcrumb');
  }

  async goto() {
    await this.page.goto('/plans');
  }

  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    // Wait for either table data or empty state
    await Promise.race([
      this.plansTable.waitFor({ state: 'visible', timeout: 10000 }),
      this.emptyState.waitFor({ state: 'visible', timeout: 10000 }),
    ]).catch(() => {});
  }

  async getRowCount(): Promise<number> {
    return this.plansTableRows.count();
  }

  getRowByName(name: string): Locator {
    return this.plansTableRows.filter({ hasText: name });
  }

  async setTab(tab: 'actifs' | 'inactifs') {
    if (tab === 'actifs') {
      await this.tabActifs.click();
    } else {
      await this.tabInactifs.click();
    }
    await this.page.waitForTimeout(500);
  }

  async searchPlan(query: string) {
    await this.searchInput.fill(query);
    await this.page.waitForTimeout(500);
  }

  getScopeButton(label: string): Locator {
    return this.scopeToggle.locator('button', { hasText: label });
  }
}
