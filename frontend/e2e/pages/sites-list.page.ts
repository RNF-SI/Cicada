import { type Page, type Locator } from '@playwright/test';

export class SitesListPage {
  readonly page: Page;
  readonly pageTitle: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('h1').first();
  }

  async goto() {
    await this.page.goto('/sites');
  }
}
