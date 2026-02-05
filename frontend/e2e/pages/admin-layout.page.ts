import { type Page, type Locator } from '@playwright/test';

export class AdminLayoutPage {
  readonly page: Page;
  readonly sidebar: Locator;
  readonly navItems: Locator;
  readonly impersonationBanner: Locator;
  readonly stopImpersonationButton: Locator;
  readonly roleBadge: Locator;

  constructor(page: Page) {
    this.page = page;
    this.sidebar = page.locator('.admin-sidebar');
    this.navItems = page.locator('.nav-item');
    this.impersonationBanner = page.locator('.impersonation-banner');
    this.stopImpersonationButton = page.locator('.stop-impersonation-btn');
    this.roleBadge = page.locator('.role-badge');
  }

  async goto() {
    await this.page.goto('/administration');
  }

  async navigateTo(route: string) {
    await this.navItems.filter({ has: this.page.locator(`[href="/administration/${route}"]`) }).click();
  }

  getNavItem(label: string): Locator {
    return this.navItems.filter({ hasText: label });
  }

  async getVisibleNavLabels(): Promise<string[]> {
    return this.navItems.allTextContents();
  }
}
