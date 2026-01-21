/**
 * Composant pour la page d'activite unifiee.
 * Affiche l'historique d'activite dans une timeline avec filtrage par onglets.
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MatTabsModule } from '@angular/material/tabs';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatExpansionModule } from '@angular/material/expansion';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ActivityService } from '../../core/services/activity.service';
import { AuthService } from '../../core/services/auth.service';
import {
  ActivityLogListItem,
  ActivityTab,
  ActivityFilters,
  DEFAULT_TAB_CONFIGS,
  ACTION_ICONS,
  ENTITY_TYPE_ICONS,
  VALIDATION_ACTION_ICONS
} from '../../core/models/activity.model';

@Component({
  selector: 'app-activity',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatTabsModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatPaginatorModule,
    MatBadgeModule,
    MatTooltipModule,
    MatExpansionModule,
    TranslateModule
  ],
  templateUrl: './activity.component.html',
  styleUrl: './activity.component.scss'
})
export class ActivityComponent implements OnInit {
  private readonly activityService = inject(ActivityService);
  private readonly authService = inject(AuthService);
  private readonly translate = inject(TranslateService);

  // Etat
  readonly loading = this.activityService.loading;
  readonly activities = signal<ActivityLogListItem[]>([]);
  readonly totalCount = signal(0);
  readonly currentPage = signal(1);
  readonly pageSize = 20;

  // Onglet actif
  readonly currentTab = this.activityService.currentTab;
  readonly tabsCounts = this.activityService.tabsCounts;

  // User info
  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;

  // Filtres
  searchQuery = '';
  entityTypeFilter = '';
  actionFilter = '';

  // Onglets visibles selon le role
  readonly visibleTabs = computed(() => {
    const user = this.currentUser();
    if (!user) return [];

    return DEFAULT_TAB_CONFIGS.filter(tab => {
      if (tab.superAdminOnly && !this.isSuperAdmin()) return false;
      if (tab.adminOnly && !this.isAdminOrganisme()) return false;
      return true;
    });
  });

  // Index de l'onglet actif pour mat-tab-group
  readonly activeTabIndex = computed(() => {
    const tabs = this.visibleTabs();
    const currentTabId = this.currentTab();
    return tabs.findIndex(t => t.id === currentTabId);
  });

  // Activities groupees par date
  readonly groupedActivities = computed(() => {
    const items = this.activities();
    return this.groupByDate(items);
  });

  ngOnInit(): void {
    this.loadTabsCounts();
    this.loadData();
  }

  /**
   * Charge les compteurs d'onglets.
   */
  loadTabsCounts(): void {
    this.activityService.getTabsCounts().subscribe();
  }

  /**
   * Charge les donnees selon l'onglet actif.
   */
  loadData(): void {
    const tab = this.currentTab();

    const filters: ActivityFilters = {
      page: this.currentPage()
    };

    if (this.searchQuery) {
      filters.search = this.searchQuery;
    }
    if (this.entityTypeFilter) {
      filters.entity_type = this.entityTypeFilter as ActivityFilters['entity_type'];
    }
    if (this.actionFilter) {
      filters.action = this.actionFilter as ActivityFilters['action'];
    }

    this.activityService.getActivitiesByTab(tab, filters).subscribe({
      next: (response) => {
        this.activities.set(response.results);
        this.totalCount.set(response.count);
      },
      error: (error) => {
        console.error('Erreur chargement activites:', error);
      }
    });
  }

  /**
   * Change d'onglet.
   */
  onTabChange(index: number): void {
    const tabs = this.visibleTabs();
    if (index >= 0 && index < tabs.length) {
      this.activityService.setCurrentTab(tabs[index].id);
      this.currentPage.set(1);
      this.resetFilters();
      this.loadData();
    }
  }

  /**
   * Change de page.
   */
  onPageChange(event: PageEvent): void {
    this.currentPage.set(event.pageIndex + 1);
    this.loadData();
  }

  /**
   * Applique les filtres.
   */
  applyFilters(): void {
    this.currentPage.set(1);
    this.loadData();
  }

  /**
   * Reinitialise les filtres.
   */
  resetFilters(): void {
    this.searchQuery = '';
    this.entityTypeFilter = '';
    this.actionFilter = '';
  }

  /**
   * Groupe les activites par date.
   */
  private groupByDate(items: ActivityLogListItem[]): Map<string, ActivityLogListItem[]> {
    const groups = new Map<string, ActivityLogListItem[]>();
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const thisWeekStart = new Date(today);
    thisWeekStart.setDate(thisWeekStart.getDate() - thisWeekStart.getDay());
    const thisMonthStart = new Date(today.getFullYear(), today.getMonth(), 1);

    for (const item of items) {
      const date = new Date(item.created_at);
      let groupKey: string;

      if (this.isSameDay(date, today)) {
        groupKey = this.translate.instant('activity.timeline.today');
      } else if (this.isSameDay(date, yesterday)) {
        groupKey = this.translate.instant('activity.timeline.yesterday');
      } else if (date >= thisWeekStart) {
        groupKey = this.translate.instant('activity.timeline.thisWeek');
      } else if (date >= thisMonthStart) {
        groupKey = this.translate.instant('activity.timeline.thisMonth');
      } else {
        groupKey = date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });
      }

      if (!groups.has(groupKey)) {
        groups.set(groupKey, []);
      }
      groups.get(groupKey)!.push(item);
    }

    return groups;
  }

  /**
   * Verifie si deux dates sont le meme jour.
   */
  private isSameDay(date1: Date, date2: Date): boolean {
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getDate() === date2.getDate();
  }

  /**
   * Obtient l'icone d'une action.
   * Pour les validations, utilise des icones specifiques selon l'etat.
   */
  getActionIcon(action: string, entityType?: string): string {
    // Pour les validations, utiliser les icones specifiques
    if (entityType === 'validation' && VALIDATION_ACTION_ICONS[action]) {
      return VALIDATION_ACTION_ICONS[action];
    }
    return ACTION_ICONS[action as keyof typeof ACTION_ICONS] || 'fi-rr-info';
  }

  /**
   * Obtient l'icone d'un type d'entite.
   */
  getEntityTypeIcon(entityType: string): string {
    return ENTITY_TYPE_ICONS[entityType as keyof typeof ENTITY_TYPE_ICONS] || 'fi-rr-info';
  }

  /**
   * Obtient la classe CSS de l'action.
   * Pour les validations, utilise des classes specifiques selon l'etat.
   */
  getActionClass(action: string, entityType?: string): string {
    // Pour les validations, utiliser des classes specifiques
    if (entityType === 'validation') {
      const validationClasses: Record<string, string> = {
        'create': 'action-validation-pending',
        'validation_approved': 'action-validation-approved',
        'validation_rejected': 'action-validation-rejected',
      };
      return validationClasses[action] || 'action-default';
    }

    const classes: Record<string, string> = {
      'create': 'action-create',
      'update': 'action-update',
      'delete': 'action-delete',
      'add_member': 'action-add',
      'remove_member': 'action-remove',
      'add_referent': 'action-add',
      'remove_referent': 'action-remove',
      'status_change': 'action-status',
      'activate': 'action-activate',
      'deactivate': 'action-deactivate',
      'rgpd_request': 'action-warning',
      'rgpd_cancelled': 'action-info',
      'rgpd_anonymized': 'action-warning',
      'access_granted': 'action-add',
      'access_revoked': 'action-remove',
      'validation_approved': 'action-activate',
      'validation_rejected': 'action-deactivate',
      'file_upload': 'action-add',
      'file_delete': 'action-remove',
    };
    return classes[action] || 'action-default';
  }

  /**
   * Obtient le compteur d'un onglet.
   */
  getTabCount(tabId: ActivityTab): number | null {
    const counts = this.tabsCounts();
    if (!counts) return null;

    const count = counts[tabId as keyof typeof counts];
    return typeof count === 'number' ? count : null;
  }

  /**
   * Formate la date.
   */
  formatTime(dateString: string): string {
    const date = new Date(dateString);
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  /**
   * Construit le lien vers l'entite.
   * Retourne un objet avec path et queryParams pour routerLink.
   */
  getEntityLink(activity: ActivityLogListItem): { path: string; queryParams?: Record<string, string> } | null {
    // Les activites RGPD n'ont pas de page de detail
    if (activity.action.startsWith('rgpd_')) {
      return null;
    }

    switch (activity.entity_type) {
      case 'site':
        return activity.related_site ? { path: `/sites/${activity.related_site}` } : null;
      case 'plan':
        return activity.related_plan ? { path: `/plans/${activity.related_plan}` } : null;
      case 'user':
        // Pour les utilisateurs, on ne peut pas ouvrir directement (pas de support ?id=)
        return null;
      case 'organisme':
        // Pour les organismes, on ne peut pas ouvrir directement (pas de support ?id=)
        return null;
      case 'validation':
        // Les admins et referents peuvent acceder a la page validations
        if (this.isAdminOrganisme() || this.currentUser()?.is_referent) {
          return {
            path: '/administration/validations',
            queryParams: { open: activity.entity_id.toString() }
          };
        }
        return null;
      default:
        return null;
    }
  }

}
