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
    // #592 — filtres kit UI adressés par data-testid.
    this.statusFilter = page.getByTestId('validations-status');
    this.typeFilter = page.getByTestId('validations-type');
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

  /** @param value valeur de statut (ex. `pending`, `approved`). */
  async selectStatusFilter(value: string) {
    await this.statusFilter.click();
    await this.page.getByTestId(`validations-status-option-${value}`).click();
  }

  /** @param value valeur de type de demande (ex. `site_access`). */
  async selectTypeFilter(value: string) {
    await this.typeFilter.click();
    await this.page.getByTestId(`validations-type-option-${value}`).click();
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
