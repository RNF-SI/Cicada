import { test, expect } from '@playwright/test';
import { RegisterPage } from '../../pages/register.page';

test.describe('Registration', () => {
  let registerPage: RegisterPage;

  test.beforeEach(async ({ page }) => {
    registerPage = new RegisterPage(page);
    await registerPage.goto();
  });

  test('should display the registration form', async () => {
    await expect(registerPage.firstNameInput).toBeVisible();
    await expect(registerPage.lastNameInput).toBeVisible();
    await expect(registerPage.emailInput).toBeVisible();
    await expect(registerPage.organismeInput).toBeVisible();
    await expect(registerPage.passwordInput).toBeVisible();
    await expect(registerPage.confirmPasswordInput).toBeVisible();
    await expect(registerPage.submitButton).toBeVisible();
  });

  test('should register and redirect to pending page', async ({ page }) => {
    const uniqueEmail = `e2e-${Date.now()}@test.fr`;
    await registerPage.fillForm({
      firstName: 'E2E',
      lastName: 'TestUser',
      email: uniqueEmail,
      organisme: 'Naturelles',
      password: 'Test123!e2e',
      confirmPassword: 'Test123!e2e',
      justification: 'Test E2E registration',
    });
    await registerPage.submit();
    await expect(page).toHaveURL(/\/auth\/registration-pending/, { timeout: 15000 });
  });

  test('should show validation errors for empty required fields', async ({ page }) => {
    // Le bouton de soumission est toujours actif : la validation s'affiche au submit.
    await registerPage.submit();

    // Un bandeau d'erreur apparaît et on reste sur la page d'inscription.
    await expect(page.locator('.error-banner')).toBeVisible();
    await expect(page).toHaveURL(/\/auth\/register/);
  });

  test('should show error for password mismatch', async ({ page }) => {
    // Fill required fields first so form-level validation can run
    await registerPage.firstNameInput.fill('Test');
    await registerPage.lastNameInput.fill('User');
    await registerPage.emailInput.fill('mismatch@test.fr');

    await registerPage.passwordInput.fill('Test123!abc');
    await registerPage.confirmPasswordInput.fill('DifferentPassword');

    // Le bouton est toujours actif : soumettre déclenche la validation (markAllAsTouched).
    await registerPage.submit();

    // L'erreur de concordance des mots de passe s'affiche et on reste sur la page.
    const mismatchError = page.locator('.app-form-field__error, mat-error, .form-error-msg').filter({ hasText: /correspondent|match/i });
    await expect(mismatchError.first()).toBeVisible();
    await expect(page).toHaveURL(/\/auth\/register/);
  });

  test('should show error for duplicate email', async ({ page }) => {
    await registerPage.fillForm({
      firstName: 'Duplicate',
      lastName: 'User',
      email: 'admin@test.fr', // Already exists
      organisme: 'Naturelles',
      password: 'Test123!dup',
      confirmPassword: 'Test123!dup',
      justification: 'Test E2E duplicate email',
    });
    await registerPage.submit();
    // Backend should return error for duplicate email
    const errorBanner = page.locator('.error-banner, mat-error').first();
    await expect(errorBanner).toBeVisible({ timeout: 10000 });
  });
});
