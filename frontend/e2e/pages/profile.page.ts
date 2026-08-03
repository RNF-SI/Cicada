import { type Page, type Locator } from '@playwright/test';

export class ProfilePage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly subtitle: Locator;
  readonly backLink: Locator;

  // User info card
  readonly userCard: Locator;
  readonly fullName: Locator;
  readonly email: Locator;
  readonly roleChip: Locator;
  readonly memberSince: Locator;
  readonly lastLogin: Locator;

  // Organisation card
  readonly organismeCard: Locator;
  readonly organismeName: Locator;
  readonly organismeAddress: Locator;

  // RGPD card
  readonly rgpdCard: Locator;
  readonly deleteAccountButton: Locator;
  readonly cancelDeletionButton: Locator;
  readonly deletionPendingWarning: Locator;

  // Loading
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('.page-header h1');
    this.subtitle = page.locator('.page-header .subtitle');
    this.backLink = page.locator('.back-link');

    // User info card
    this.userCard = page.locator('.profile-card').first();
    this.fullName = page.locator('mat-card-title').first();
    this.email = page.locator('mat-card-subtitle').first();
    // #296 — le rôle est rendu par le composant unifié `app-tag`
    // (l'ancienne classe `.role-chip` n'existe plus).
    this.roleChip = page.locator('.info-item').filter({ hasText: 'Rôle' }).locator('app-tag .app-tag');
    this.memberSince = page.locator('.info-item').filter({ hasText: 'Membre depuis' }).locator('.info-value');
    this.lastLogin = page.locator('.info-item').filter({ hasText: 'Dernière connexion' }).locator('.info-value');

    // Organisation card
    this.organismeCard = page.locator('.profile-card', { hasText: 'Organisme' });
    this.organismeName = page.locator('.org-name');
    this.organismeAddress = this.organismeCard.locator('.info-item', { hasText: 'Adresse' }).locator('.info-value');

    // RGPD card
    this.rgpdCard = page.locator('.rgpd-card');
    this.deleteAccountButton = page.locator('.delete-button', { hasText: 'Supprimer mon compte' });
    this.cancelDeletionButton = page.locator('button', { hasText: 'Annuler la demande' });
    this.deletionPendingWarning = page.locator('.deletion-pending');

    // Loading
    this.loadingSpinner = page.locator('mat-spinner');
  }

  async goto() {
    await this.page.goto('/profile');
  }

  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    await this.userCard.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
  }

  async getFullName(): Promise<string> {
    return (await this.fullName.textContent()) || '';
  }

  async getEmail(): Promise<string> {
    return (await this.email.textContent()) || '';
  }

  async getRole(): Promise<string> {
    return (await this.roleChip.textContent()) || '';
  }

  async getOrganismeName(): Promise<string> {
    return (await this.organismeName.textContent()) || '';
  }

  async openDeleteAccountDialog() {
    await this.deleteAccountButton.click();
  }

  async hasRgpdCard(): Promise<boolean> {
    return this.rgpdCard.isVisible().catch(() => false);
  }

  async hasDeletionPending(): Promise<boolean> {
    return this.deletionPendingWarning.isVisible().catch(() => false);
  }

  async hasOrganismeCard(): Promise<boolean> {
    return this.organismeCard.isVisible().catch(() => false);
  }
}
