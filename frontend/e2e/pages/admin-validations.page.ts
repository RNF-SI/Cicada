import { type Page, type Locator } from '@playwright/test';

export class AdminValidationsPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly statusFilter: Locator;
  readonly typeFilter: Locator;
  readonly tableRows: Locator;
  readonly emptyState: Locator;
  readonly loadingSpinner: Locator;
  readonly paginator: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('.page-header h1');
    this.statusFilter = page.locator('mat-select').first();
    this.typeFilter = page.locator('mat-select').nth(1);
    this.tableRows = page.locator('tr[mat-row]');
    this.emptyState = page.locator('.empty-state');
    this.loadingSpinner = page.locator('mat-spinner');
    this.paginator = page.locator('mat-paginator');
  }

  async goto() {
    await this.page.goto('/administration/validations');
  }

  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    await Promise.race([
      this.tableRows.first().waitFor({ state: 'visible', timeout: 10000 }),
      this.emptyState.waitFor({ state: 'visible', timeout: 10000 }),
    ]).catch(() => {});
  }

  async selectStatusFilter(label: string) {
    await this.statusFilter.click();
    await this.page.locator('mat-option').filter({ hasText: label }).click();
  }

  async selectTypeFilter(label: string) {
    await this.typeFilter.click();
    await this.page.locator('mat-option').filter({ hasText: label }).click();
  }

  getApproveButton(row: Locator): Locator {
    return row.locator('button[color="primary"]');
  }

  getDetailButton(row: Locator): Locator {
    return row.locator('button').filter({ has: row.page().locator('.fi-rr-eye') });
  }

  async getRowCount(): Promise<number> {
    return this.tableRows.count();
  }
}
