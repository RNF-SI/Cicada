import { type Page, type Locator } from '@playwright/test';

export class RegisterPage {
  readonly page: Page;
  readonly firstNameInput: Locator;
  readonly lastNameInput: Locator;
  readonly emailInput: Locator;
  readonly identifiantInput: Locator;
  readonly organismeInput: Locator;
  readonly passwordInput: Locator;
  readonly confirmPasswordInput: Locator;
  readonly justificationInput: Locator;
  readonly submitButton: Locator;
  readonly errorBanner: Locator;
  readonly loginLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.firstNameInput = page.locator('input[formcontrolname="prenom"]');
    this.lastNameInput = page.locator('input[formcontrolname="nom"]');
    this.emailInput = page.locator('input[formcontrolname="email"]');
    this.identifiantInput = page.locator('input[formcontrolname="identifiant"]');
    this.organismeInput = page.locator('input[formcontrolname="organisme"]');
    this.passwordInput = page.locator('input[formcontrolname="password"]');
    this.confirmPasswordInput = page.locator('input[formcontrolname="confirmPassword"]');
    this.justificationInput = page.locator('textarea[formcontrolname="justification"]');
    this.submitButton = page.locator('button[type="submit"]');
    this.errorBanner = page.locator('.error-banner');
    this.loginLink = page.locator('a[href="/auth/login"]');
  }

  async goto() {
    await this.page.goto('/auth/register');
  }

  async fillForm(data: {
    firstName: string;
    lastName: string;
    email: string;
    identifiant?: string;
    organisme?: string;
    password: string;
    confirmPassword: string;
    justification?: string;
  }) {
    await this.firstNameInput.fill(data.firstName);
    await this.lastNameInput.fill(data.lastName);
    await this.emailInput.fill(data.email);

    if (data.identifiant) {
      await this.identifiantInput.fill(data.identifiant);
    }

    if (data.organisme) {
      await this.organismeInput.fill(data.organisme);
      // Wait for autocomplete and select first option
      const option = this.page.locator('mat-option').first();
      await option.waitFor({ state: 'visible', timeout: 5000 });
      await option.click();
      // Wait for autocomplete overlay to close before filling next fields
      await this.page.locator('.cdk-overlay-backdrop').waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
      await this.page.waitForTimeout(300);
    }

    // Click password field first to ensure focus, then fill
    await this.passwordInput.click();
    await this.passwordInput.fill(data.password);
    await this.confirmPasswordInput.click();
    await this.confirmPasswordInput.fill(data.confirmPassword);

    if (data.justification) {
      await this.justificationInput.fill(data.justification);
    }
  }

  async submit() {
    await this.submitButton.click();
  }
}
