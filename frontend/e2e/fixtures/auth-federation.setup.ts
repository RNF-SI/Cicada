import { test as setup, expect } from '@playwright/test';
import path from 'path';

/**
 * Session sur la SECONDE instance du banc de fédération (#636).
 *
 * Elle ne peut pas réutiliser `.auth/super-admin.json` : un `storageState` est
 * lié à son origine, et les deux instances sont sur des ports différents. C'est
 * d'ailleurs ce qui permet d'être connecté aux deux à la fois, sous des comptes
 * différents — mais impose une authentification par origine.
 */

const AUTH_DIR = path.join(__dirname, '..', '.auth');

setup('authenticate on federated instance', async ({ page }) => {
  await page.goto('/auth/login');

  await page.locator('input[formcontrolname="username"]').fill('admin@test.fr');
  await page.locator('input[formcontrolname="password"]').fill('Test123!');
  await page.locator('button[type="submit"]').click();

  await expect(page).toHaveURL(/\/accueil/, { timeout: 15000 });

  const authTokens = await page.evaluate(() => {
    const raw = window.localStorage.getItem('auth_tokens');
    return raw ? JSON.parse(raw) : null;
  });
  expect(authTokens?.access).toBeTruthy();

  await page.context().storageState({
    path: path.join(AUTH_DIR, 'federation-admin.json'),
  });
});
