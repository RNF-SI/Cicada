import { type Page, type Locator } from '@playwright/test';

export class HomePage {
  readonly page: Page;
  readonly navigationTiles: Locator;

  constructor(page: Page) {
    this.page = page;
    this.navigationTiles = page.locator('app-navigation-tile');
  }

  async goto() {
    await this.page.goto('/accueil');
  }

  async getTileByTitle(title: string): Promise<Locator> {
    return this.page.locator('app-navigation-tile').filter({ hasText: title });
  }
}
