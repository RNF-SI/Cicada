import { type Page, type Locator } from '@playwright/test';

export class ActivityPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly subtitle: Locator;
  readonly tabs: Locator;
  readonly searchInput: Locator;
  readonly entityTypeFilter: Locator;
  readonly resetButton: Locator;
  readonly timelineGroups: Locator;
  readonly timelineItems: Locator;
  readonly emptyState: Locator;
  readonly loadingSpinner: Locator;
  readonly paginator: Locator;
  readonly backLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('.page-header h1');
    this.subtitle = page.locator('.page-header .subtitle');
    this.tabs = page.locator('mat-tab-group .mat-mdc-tab');
    this.searchInput = page.locator('.filters-bar input');
    this.entityTypeFilter = page.locator('.filter-field mat-select');
    this.resetButton = page.locator('.filters-bar button', { hasText: 'Réinitialiser' });
    this.timelineGroups = page.locator('.timeline-group');
    this.timelineItems = page.locator('.timeline-item');
    this.emptyState = page.locator('.empty-state');
    this.loadingSpinner = page.locator('mat-spinner');
    this.paginator = page.locator('mat-paginator');
    this.backLink = page.locator('.back-link');
  }

  async goto() {
    await this.page.goto('/activite');
  }

  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    // Wait for either timeline or empty state
    await Promise.race([
      this.timelineItems.first().waitFor({ state: 'visible', timeout: 10000 }),
      this.emptyState.waitFor({ state: 'visible', timeout: 10000 }),
    ]).catch(() => {});
  }

  async selectTab(index: number) {
    await this.tabs.nth(index).click();
    await this.page.waitForTimeout(500);
  }

  async getTabByLabel(label: string): Promise<Locator> {
    return this.tabs.filter({ hasText: label });
  }

  async searchActivity(query: string) {
    await this.searchInput.fill(query);
    await this.searchInput.press('Enter');
  }

  async filterByEntityType(type: string) {
    await this.entityTypeFilter.click();
    await this.page.locator('mat-option', { hasText: type }).click();
  }

  async resetFilters() {
    await this.resetButton.click();
  }

  async getTabCount(): Promise<number> {
    return this.tabs.count();
  }

  async getTimelineItemCount(): Promise<number> {
    return this.timelineItems.count();
  }

  async getGroupCount(): Promise<number> {
    return this.timelineGroups.count();
  }

  getActivityByDescription(description: string): Locator {
    return this.timelineItems.filter({ hasText: description });
  }

  async hasEmptyState(): Promise<boolean> {
    return this.emptyState.isVisible().catch(() => false);
  }

  async hasPagination(): Promise<boolean> {
    return this.paginator.isVisible().catch(() => false);
  }

  async goToNextPage() {
    await this.paginator.locator('button.mat-mdc-paginator-navigation-next').click();
  }

  async goToPreviousPage() {
    await this.paginator.locator('button.mat-mdc-paginator-navigation-previous').click();
  }
}
