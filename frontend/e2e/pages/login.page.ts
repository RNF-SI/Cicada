import { type Page, type Locator } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly errorBanner: Locator;
  readonly registerLink: Locator;
  readonly backToHomeLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.usernameInput = page.locator('input[formcontrolname="username"]');
    this.passwordInput = page.locator('input[formcontrolname="password"]');
    this.submitButton = page.locator('button[type="submit"]');
    this.errorBanner = page.locator('.error-banner');
    this.registerLink = page.locator('a[href="/auth/register"]');
    this.backToHomeLink = page.locator('.back-link');
  }

  async goto() {
    await this.page.goto('/auth/login');
  }

  async login(email: string, password: string) {
    await this.usernameInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }
}
