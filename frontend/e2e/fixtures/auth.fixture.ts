import { test as base, type Page } from '@playwright/test';
import path from 'path';

const AUTH_DIR = path.join(__dirname, '..', '.auth');

type AuthFixtures = {
  superAdminPage: Page;
  adminRnfPage: Page;
  adminCenPage: Page;
  referentPage: Page;
  userRnfPage: Page;
  userCenPage: Page;
};

/**
 * Custom test fixture providing pre-authenticated pages for each user role.
 *
 * Usage:
 *   test('my test', async ({ superAdminPage }) => {
 *     await superAdminPage.goto('/administration/dashboard');
 *   });
 */
export const test = base.extend<AuthFixtures>({
  superAdminPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: path.join(AUTH_DIR, 'super-admin.json'),
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  adminRnfPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: path.join(AUTH_DIR, 'admin-rnf.json'),
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  adminCenPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: path.join(AUTH_DIR, 'admin-cen.json'),
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  referentPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: path.join(AUTH_DIR, 'referent.json'),
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  userRnfPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: path.join(AUTH_DIR, 'user-rnf.json'),
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },

  userCenPage: async ({ browser }, use) => {
    const context = await browser.newContext({
      storageState: path.join(AUTH_DIR, 'user-cen.json'),
    });
    const page = await context.newPage();
    await use(page);
    await context.close();
  },
});

export { expect } from '@playwright/test';
