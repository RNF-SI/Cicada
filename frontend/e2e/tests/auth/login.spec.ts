import { test, expect } from '@playwright/test';
import { LoginPage } from '../../pages/login.page';

test.describe('Login', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test('should display the login form', async ({ page }) => {
    await expect(loginPage.usernameInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.submitButton).toBeVisible();
    await expect(loginPage.registerLink).toBeVisible();
  });

  test('should login with valid credentials and redirect to /accueil', async ({ page }) => {
    await loginPage.login('admin@test.fr', 'Test123!');
    await expect(page).toHaveURL(/\/accueil/, { timeout: 15000 });
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await loginPage.login('admin@test.fr', 'WrongPassword');
    await expect(loginPage.errorBanner).toBeVisible({ timeout: 10000 });
  });

  test('should disable submit button when fields are empty', async () => {
    await expect(loginPage.submitButton).toBeDisabled();
  });

  test('should redirect to returnUrl after login', async ({ page }) => {
    await page.goto('/auth/login?returnUrl=/profile');
    loginPage = new LoginPage(page);
    await loginPage.login('admin@test.fr', 'Test123!');
    await expect(page).toHaveURL(/\/profile/, { timeout: 15000 });
  });
});
