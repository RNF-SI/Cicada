import { type Page, type Locator } from '@playwright/test';

export class AdminDashboardPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly welcomeMessage: Locator;
  readonly statCards: Locator;
  readonly errorBanner: Locator;
  readonly retryButton: Locator;
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1');
    this.welcomeMessage = page.locator('.welcome-message');
    this.statCards = page.locator('.stat-card');
    this.errorBanner = page.locator('.error-banner');
    this.retryButton = page.locator('.retry-btn');
    this.loadingSpinner = page.locator('mat-spinner');
  }

  async goto() {
    await this.page.goto('/administration/dashboard');
  }

  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
  }

  getStatCard(label: string): Locator {
    return this.statCards.filter({ hasText: label });
  }

  async getStatValue(label: string): Promise<string> {
    const card = this.getStatCard(label);
    return card.locator('.stat-value').textContent() ?? '';
  }
}
