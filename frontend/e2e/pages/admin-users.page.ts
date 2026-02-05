import { type Page, type Locator } from '@playwright/test';

export class AdminUsersPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly searchInput: Locator;
  readonly roleFilter: Locator;
  readonly statusFilter: Locator;
  readonly organismeFilter: Locator;
  readonly tableRows: Locator;
  readonly emptyState: Locator;
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('.page-header h1');
    this.searchInput = page.locator('.filters-bar input[type="text"]');
    this.roleFilter = page.locator('.filters-bar select').first();
    this.statusFilter = page.locator('.filters-bar select').last();
    this.organismeFilter = page.locator('.filters-bar select').nth(1);
    this.tableRows = page.locator('.users-table tbody tr');
    this.emptyState = page.locator('.empty-cell');
    this.loadingSpinner = page.locator('mat-spinner');
  }

  async goto() {
    await this.page.goto('/administration/utilisateurs');
  }

  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    // Wait for either table rows or empty state
    await Promise.race([
      this.tableRows.first().waitFor({ state: 'visible', timeout: 10000 }),
      this.emptyState.waitFor({ state: 'visible', timeout: 10000 }),
    ]).catch(() => {});
  }

  async searchUser(query: string) {
    await this.searchInput.fill(query);
  }

  async filterByRole(role: string) {
    await this.roleFilter.selectOption(role);
  }

  async filterByStatus(status: string) {
    await this.statusFilter.selectOption(status);
  }

  getRowByEmail(email: string): Locator {
    return this.tableRows.filter({ hasText: email });
  }

  getActionButton(row: Locator, iconClass: string): Locator {
    return row.locator(`.btn-icon .fi.${iconClass}`).locator('..');
  }

  async getRowCount(): Promise<number> {
    return this.tableRows.count();
  }
}
