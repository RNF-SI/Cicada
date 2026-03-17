import { type Page, type Locator } from '@playwright/test';

export class NotificationsPage {
  readonly page: Page;
  readonly pageTitle: Locator;
  readonly notificationCards: Locator;
  readonly unreadNotifications: Locator;
  readonly emptyState: Locator;
  readonly loadingSpinner: Locator;
  readonly markAllReadButton: Locator;
  readonly loadMoreButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageTitle = page.locator('.page-header h1');
    this.notificationCards = page.locator('.notification-card');
    this.unreadNotifications = page.locator('.notification-card.unread');
    this.emptyState = page.locator('.empty-state');
    this.loadingSpinner = page.locator('mat-spinner');
    this.markAllReadButton = page.locator('button', { hasText: 'Tout marquer comme lu' });
    this.loadMoreButton = page.locator('.load-more button');
  }

  async goto() {
    await this.page.goto('/notifications');
  }

  async waitForData() {
    await this.loadingSpinner.waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
    // Wait for either notifications or empty state
    await Promise.race([
      this.notificationCards.first().waitFor({ state: 'visible', timeout: 10000 }),
      this.emptyState.waitFor({ state: 'visible', timeout: 10000 }),
    ]).catch(() => {});
  }

  async markAllAsRead() {
    await this.markAllReadButton.click();
  }

  async markAsRead(index: number) {
    const markReadButton = this.notificationCards.nth(index).locator('button[title="Marquer comme lu"]');
    await markReadButton.click();
  }

  async loadMore() {
    await this.loadMoreButton.click();
  }

  async getNotificationCount(): Promise<number> {
    return this.notificationCards.count();
  }

  async getUnreadCount(): Promise<number> {
    return this.unreadNotifications.count();
  }

  getNotificationByText(text: string): Locator {
    return this.notificationCards.filter({ hasText: text });
  }

  async hasEmptyState(): Promise<boolean> {
    return this.emptyState.isVisible().catch(() => false);
  }

  async hasMoreToLoad(): Promise<boolean> {
    return this.loadMoreButton.isVisible().catch(() => false);
  }
}
