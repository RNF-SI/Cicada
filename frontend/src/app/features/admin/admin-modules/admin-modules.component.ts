/**
 * Composant d'administration pour la gestion des acces aux modules.
 * Accessible uniquement au super_admin.
 *
 * NOTE: Cette fonctionnalite est temporaire et constitue un debut de developpement.
 * Elle sera amenee a evoluer significativement dans les prochaines versions.
 * Pour le moment, la gestion des modules est simplifiee et ne couvre pas tous les cas d'usage.
 */
import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';

import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AdminService } from '../../../core/services/admin.service';
import { ValidationService } from '../../../core/services/validation.service';
import { AdminUser } from '../../../core/models/admin.model';
import { ValidationRequestListItem, ApplicationModule, ModuleCode } from '../../../core/models/notification.model';
import { debounceTime, Subject, switchMap, of } from 'rxjs';

interface UserWithModuleAccess {
  user: AdminUser;
  hasAccess: boolean;
  pendingRequest: boolean;
}

@Component({
  selector: 'app-admin-modules',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatTableModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatTooltipModule,
    MatSelectModule,
    MatAutocompleteModule,
    MatDialogModule,
    TranslateModule
  ],
  template: `
    <div class="admin-modules">
      <header class="page-header">
        <div class="header-content">
          <h1>{{ 'admin.modules.title' | translate }}</h1>
          <p class="subtitle">{{ 'admin.modules.subtitle' | translate }}</p>
        </div>
      </header>

      <!-- Avertissement developpement temporaire -->
      <div class="dev-notice">
        <i class="fi fi-rr-info"></i>
        <div class="dev-notice-content">
          <strong>{{ 'admin.modules.devNotice.title' | translate }}</strong>
          <p>{{ 'admin.modules.devNotice.message' | translate }}</p>
        </div>
      </div>

      <!-- Modules disponibles -->
      <section class="modules-overview">
        <h2 class="section-title">{{ 'admin.modules.availableModules' | translate }}</h2>
        <div class="modules-grid">
          @for (module of availableModules; track module.code) {
            <div class="module-card">
              <div class="module-header">
                <div class="module-icon">
                  <i class="fi" [ngClass]="module.icon"></i>
                </div>
                <div class="module-info">
                  <h3>{{ module.name }}</h3>
                  <p>{{ module.description }}</p>
                </div>
              </div>
              <div class="module-stats">
                <span class="stat">
                  <i class="fi fi-rr-users"></i>
                  {{ getModuleUserCount(module.code) }} {{ 'admin.modules.usersWithAccess' | translate }}
                </span>
              </div>
              <div class="module-actions">
                <button
                  mat-stroked-button
                  color="primary"
                  (click)="openGrantAccessSection(module)"
                >
                  <i class="fi fi-rr-user-add"></i>
                  {{ 'admin.modules.grantAccess' | translate }}
                </button>
              </div>
            </div>
          }
        </div>
      </section>

      <!-- Section donner acces (visible quand un module est selectionne) -->
      @if (selectedModule()) {
        <section class="grant-access-section">
          <mat-card class="grant-access-card">
            <mat-card-header>
              <mat-card-title>
                <i class="fi fi-rr-user-add"></i>
                {{ 'admin.modules.grantAccessTo' | translate }} {{ selectedModule()?.name }}
              </mat-card-title>
              <button mat-icon-button (click)="closeGrantAccessSection()" class="close-btn">
                <i class="fi fi-rr-cross"></i>
              </button>
            </mat-card-header>
            <mat-card-content>
              <!-- Recherche utilisateur -->
              <div class="user-search">
                <mat-form-field appearance="outline" class="search-field">
                  <mat-label>{{ 'admin.modules.searchUser' | translate }}</mat-label>
                  <input
                    matInput
                    [(ngModel)]="userSearchQuery"
                    (ngModelChange)="onSearchUsers($event)"
                    [placeholder]="'admin.modules.searchUserPlaceholder' | translate"
                  >
                  <i matPrefix class="fi fi-rr-search"></i>
                </mat-form-field>
              </div>

              <!-- Resultats de recherche -->
              @if (searchingUsers()) {
                <div class="search-loading">
                  <mat-spinner diameter="24"></mat-spinner>
                  <span>{{ 'common.actions.searching' | translate }}...</span>
                </div>
              } @else if (searchResults().length > 0) {
                <div class="search-results">
                  <h4>{{ 'admin.modules.searchResults' | translate }}</h4>
                  <div class="users-list">
                    @for (item of searchResults(); track item.user.id_role) {
                      <div class="user-item">
                        <div class="user-info">
                          <span class="user-name">{{ item.user.prenom_role }} {{ item.user.nom_role }}</span>
                          <span class="user-email">{{ item.user.email }}</span>
                          @if (item.user.organisme?.nom_organisme) {
                            <span class="user-org">{{ item.user.organisme?.nom_organisme }}</span>
                          }
                        </div>
                        <div class="user-action">
                          @if (item.hasAccess) {
                            <mat-chip class="status-success">
                              <i class="fi fi-rr-check"></i>
                              {{ 'admin.modules.hasAccess' | translate }}
                            </mat-chip>
                          } @else if (item.pendingRequest) {
                            <mat-chip class="status-warning">
                              <i class="fi fi-rr-hourglass-end"></i>
                              {{ 'admin.modules.pendingAccess' | translate }}
                            </mat-chip>
                          } @else {
                            <button
                              mat-flat-button
                              color="primary"
                              (click)="grantAccess(item.user)"
                              [disabled]="grantingAccess()"
                            >
                              <i class="fi fi-rr-check"></i>
                              {{ 'admin.modules.grant' | translate }}
                            </button>
                          }
                        </div>
                      </div>
                    }
                  </div>
                </div>
              } @else if (userSearchQuery() && userSearchQuery().length >= 2) {
                <div class="no-results">
                  <i class="fi fi-rr-search"></i>
                  <p>{{ 'admin.modules.noUsersFound' | translate }}</p>
                </div>
              }

              <!-- Utilisateurs avec acces -->
              <div class="users-with-access">
                <h4>
                  {{ 'admin.modules.usersWithAccessList' | translate }}
                  <span class="count">({{ getUsersWithAccess().length }})</span>
                </h4>
                @if (getUsersWithAccess().length === 0) {
                  <p class="empty-message">{{ 'admin.modules.noUsersWithAccess' | translate }}</p>
                } @else {
                  <div class="users-list">
                    @for (item of getUsersWithAccess(); track item.user.id_role) {
                      <div class="user-item">
                        <div class="user-info">
                          <span class="user-name">{{ item.user.prenom_role }} {{ item.user.nom_role }}</span>
                          <span class="user-email">{{ item.user.email }}</span>
                        </div>
                        <div class="user-action">
                          <button
                            mat-icon-button
                            color="warn"
                            (click)="revokeAccess(item.user)"
                            [matTooltip]="'admin.modules.revokeAccess' | translate"
                          >
                            <i class="fi fi-rr-trash"></i>
                          </button>
                        </div>
                      </div>
                    }
                  </div>
                }
              </div>
            </mat-card-content>
          </mat-card>
        </section>
      }

      <!-- Demandes en attente -->
      <section class="pending-requests">
        <h2 class="section-title">
          {{ 'admin.modules.pendingRequests' | translate }}
          @if (pendingModuleRequests().length > 0) {
            <span class="badge">{{ pendingModuleRequests().length }}</span>
          }
        </h2>

        @if (loadingRequests()) {
          <div class="loading-container">
            <mat-spinner diameter="32"></mat-spinner>
          </div>
        } @else if (pendingModuleRequests().length === 0) {
          <div class="empty-state">
            <i class="fi fi-rr-check-circle"></i>
            <p>{{ 'admin.modules.noPendingRequests' | translate }}</p>
          </div>
        } @else {
          <mat-card class="requests-card">
            <mat-card-content>
              <table mat-table [dataSource]="pendingModuleRequests()" class="requests-table">
                <!-- Demandeur -->
                <ng-container matColumnDef="requester">
                  <th mat-header-cell *matHeaderCellDef>{{ 'admin.modules.table.requester' | translate }}</th>
                  <td mat-cell *matCellDef="let request">
                    <span class="requester-name">{{ request.requester_name }}</span>
                  </td>
                </ng-container>

                <!-- Module -->
                <ng-container matColumnDef="module">
                  <th mat-header-cell *matHeaderCellDef>{{ 'admin.modules.table.module' | translate }}</th>
                  <td mat-cell *matCellDef="let request">
                    <span class="module-name">{{ request.target_name }}</span>
                  </td>
                </ng-container>

                <!-- Date -->
                <ng-container matColumnDef="date">
                  <th mat-header-cell *matHeaderCellDef>{{ 'admin.modules.table.date' | translate }}</th>
                  <td mat-cell *matCellDef="let request">
                    {{ formatDate(request.created_at) }}
                  </td>
                </ng-container>

                <!-- Justification -->
                <ng-container matColumnDef="justification">
                  <th mat-header-cell *matHeaderCellDef>{{ 'admin.modules.table.justification' | translate }}</th>
                  <td mat-cell *matCellDef="let request">
                    @if (request.justification) {
                      <span class="justification">{{ request.justification }}</span>
                    } @else {
                      <span class="no-justification">-</span>
                    }
                  </td>
                </ng-container>

                <!-- Actions -->
                <ng-container matColumnDef="actions">
                  <th mat-header-cell *matHeaderCellDef></th>
                  <td mat-cell *matCellDef="let request">
                    <div class="action-buttons">
                      <button
                        mat-flat-button
                        color="primary"
                        (click)="approveRequest(request)"
                        [disabled]="processingRequest() === request.id"
                      >
                        <i class="fi fi-rr-check"></i>
                        {{ 'common.actions.validate' | translate }}
                      </button>
                      <button
                        mat-stroked-button
                        color="warn"
                        (click)="rejectRequest(request)"
                        [disabled]="processingRequest() === request.id"
                      >
                        <i class="fi fi-rr-cross"></i>
                        {{ 'admin.validations.actions.reject' | translate }}
                      </button>
                    </div>
                  </td>
                </ng-container>

                <tr mat-header-row *matHeaderRowDef="requestColumns"></tr>
                <tr mat-row *matRowDef="let row; columns: requestColumns"></tr>
              </table>
            </mat-card-content>
          </mat-card>
        }
      </section>
    </div>
  `,
  styles: [`
    .admin-modules {
      padding: 24px;
    }

    .page-header {
      margin-bottom: 24px;
    }

    .page-header h1 {
      font-family: 'Nunito', sans-serif;
      font-size: 28px;
      font-weight: 700;
      color: #025359;
      margin: 0 0 8px;
    }

    .subtitle {
      font-family: 'Nunito', sans-serif;
      font-size: 16px;
      color: #5C5C5C;
      margin: 0;
    }

    /* Dev notice */
    .dev-notice {
      display: flex;
      gap: 16px;
      padding: 16px 20px;
      background-color: #FFF8E1;
      border: 1px solid #FFE082;
      border-radius: 12px;
      margin-bottom: 32px;

      > i {
        font-size: 24px;
        color: #F57C00;
        flex-shrink: 0;
      }
    }

    .dev-notice-content {
      strong {
        font-family: 'Nunito', sans-serif;
        font-size: 14px;
        font-weight: 700;
        color: #E65100;
        display: block;
        margin-bottom: 4px;
      }

      p {
        font-family: 'Nunito', sans-serif;
        font-size: 13px;
        color: #5C5C5C;
        margin: 0;
        line-height: 1.5;
      }
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 12px;
      font-family: 'Nunito', sans-serif;
      font-size: 20px;
      font-weight: 700;
      color: #343433;
      margin: 0 0 16px;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 24px;
      height: 24px;
      padding: 0 8px;
      background-color: #FA9965;
      color: white;
      font-size: 12px;
      font-weight: 700;
      border-radius: 12px;
    }

    /* Modules grid */
    .modules-overview {
      margin-bottom: 32px;
    }

    .modules-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
    }

    .module-card {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 20px;
      background-color: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }

    .module-header {
      display: flex;
      gap: 16px;
    }

    .module-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background-color: #E8F5F5;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;

      i {
        font-size: 24px;
        color: #025359;
      }
    }

    .module-info {
      flex: 1;

      h3 {
        font-family: 'Nunito', sans-serif;
        font-size: 16px;
        font-weight: 700;
        color: #343433;
        margin: 0 0 4px;
      }

      p {
        font-family: 'Nunito', sans-serif;
        font-size: 13px;
        color: #5C5C5C;
        margin: 0;
        line-height: 1.4;
      }
    }

    .module-stats {
      padding: 12px 0;
      border-top: 1px solid #EFEFEF;
      border-bottom: 1px solid #EFEFEF;

      .stat {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: #5C5C5C;

        i {
          font-size: 14px;
          color: #025359;
        }
      }
    }

    .module-actions {
      button {
        width: 100%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
      }
    }

    /* Grant access section */
    .grant-access-section {
      margin-bottom: 32px;
    }

    .grant-access-card {
      border-radius: 12px;
      border: 2px solid #025359;
    }

    .grant-access-card mat-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 20px;
      background-color: #E8F5F5;
      border-bottom: 1px solid #EFEFEF;

      mat-card-title {
        display: flex;
        align-items: center;
        gap: 12px;
        font-family: 'Nunito', sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: #025359;
        margin: 0;

        i {
          font-size: 20px;
        }
      }
    }

    .close-btn {
      i {
        font-size: 16px;
      }
    }

    .grant-access-card mat-card-content {
      padding: 20px;
    }

    .user-search {
      margin-bottom: 20px;
    }

    .search-field {
      width: 100%;

      i {
        margin-right: 8px;
        color: #949494;
      }
    }

    .search-loading {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      color: #5C5C5C;
      font-size: 14px;
    }

    .search-results, .users-with-access {
      h4 {
        font-family: 'Nunito', sans-serif;
        font-size: 14px;
        font-weight: 700;
        color: #343433;
        margin: 0 0 12px;
        display: flex;
        align-items: center;
        gap: 8px;

        .count {
          font-weight: 400;
          color: #949494;
        }
      }
    }

    .search-results {
      margin-bottom: 24px;
      padding-bottom: 24px;
      border-bottom: 1px solid #EFEFEF;
    }

    .users-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .user-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background-color: #F8F5F1;
      border-radius: 8px;
    }

    .user-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .user-name {
      font-family: 'Nunito', sans-serif;
      font-size: 14px;
      font-weight: 600;
      color: #343433;
    }

    .user-email {
      font-family: 'Nunito', sans-serif;
      font-size: 12px;
      color: #5C5C5C;
    }

    .user-org {
      font-family: 'Nunito', sans-serif;
      font-size: 11px;
      color: #949494;
    }

    .user-action {
      button {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }

      mat-chip {
        font-size: 12px;

        i {
          font-size: 12px;
          margin-right: 4px;
        }
      }
    }

    .no-results {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px;
      color: #949494;

      i {
        font-size: 32px;
        margin-bottom: 8px;
      }

      p {
        font-family: 'Nunito', sans-serif;
        font-size: 14px;
        margin: 0;
      }
    }

    .empty-message {
      font-family: 'Nunito', sans-serif;
      font-size: 13px;
      color: #949494;
      font-style: italic;
      margin: 0;
    }

    /* Pending requests */
    .pending-requests {
      margin-bottom: 32px;
    }

    .loading-container {
      display: flex;
      justify-content: center;
      padding: 32px;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 32px;
      background-color: white;
      border-radius: 12px;
      text-align: center;

      i {
        font-size: 48px;
        color: #04854B;
        margin-bottom: 12px;
      }

      p {
        font-family: 'Nunito', sans-serif;
        font-size: 14px;
        color: #5C5C5C;
        margin: 0;
      }
    }

    .requests-card {
      border-radius: 12px;
      overflow: hidden;
    }

    .requests-table {
      width: 100%;

      th {
        font-family: 'Nunito', sans-serif;
        font-size: 13px;
        font-weight: 700;
        color: #5C5C5C;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        background-color: #F8F5F1;
      }

      td {
        font-family: 'Nunito', sans-serif;
        font-size: 14px;
        color: #343433;
      }
    }

    .requester-name {
      font-weight: 600;
      color: #025359;
    }

    .module-name {
      font-weight: 600;
    }

    .justification {
      font-size: 13px;
      color: #5C5C5C;
      max-width: 300px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .no-justification {
      color: #949494;
    }

    .action-buttons {
      display: flex;
      gap: 8px;

      button {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 13px;
      }
    }
  `]
})
export class AdminModulesComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly validationService = inject(ValidationService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  // Etat
  readonly loadingRequests = signal(false);
  readonly processingRequest = signal<number | null>(null);
  readonly allRequests = signal<ValidationRequestListItem[]>([]);
  readonly allUsers = signal<AdminUser[]>([]);

  // Section donner acces
  readonly selectedModule = signal<ApplicationModule | null>(null);
  readonly userSearchQuery = signal('');
  readonly searchResults = signal<UserWithModuleAccess[]>([]);
  readonly searchingUsers = signal(false);
  readonly grantingAccess = signal(false);

  // Recherche utilisateurs
  private readonly searchSubject = new Subject<string>();

  // Colonnes du tableau
  readonly requestColumns = ['requester', 'module', 'date', 'justification', 'actions'];

  // Modules disponibles
  readonly availableModules: ApplicationModule[] = [
    {
      code: 'zonages',
      name: 'Zonages reglementaires',
      description: 'Acces aux zonages reglementaires et leur gestion',
      icon: 'fi-rr-map',
      route: '/zonages',
      requiresAccess: true
    }
  ];

  // Demandes de module en attente
  readonly pendingModuleRequests = computed(() => {
    return this.allRequests().filter(
      r => r.request_type === 'module_access' && r.status === 'pending'
    );
  });

  ngOnInit(): void {
    this.loadRequests();
    this.loadAllUsers();
    this.setupUserSearch();
  }

  private setupUserSearch(): void {
    this.searchSubject.pipe(
      debounceTime(300),
      switchMap(query => {
        if (!query || query.length < 2) {
          return of([]);
        }
        this.searchingUsers.set(true);
        return this.adminService.getUsers({ search: query, page_size: 20 });
      })
    ).subscribe({
      next: (response: any) => {
        if (response && response.results) {
          this.searchResults.set(
            response.results.map((user: AdminUser) => this.mapUserWithAccess(user))
          );
        } else {
          this.searchResults.set([]);
        }
        this.searchingUsers.set(false);
      },
      error: () => {
        this.searchResults.set([]);
        this.searchingUsers.set(false);
      }
    });
  }

  private mapUserWithAccess(user: AdminUser): UserWithModuleAccess {
    const moduleCode = this.selectedModule()?.code;
    const requests = this.allRequests();

    const userRequests = requests.filter(
      r => r.request_type === 'module_access' &&
           r.requester_id === user.id_role &&
           r.target_name?.toLowerCase().includes(moduleCode || '')
    );

    const hasAccess = userRequests.some(r => r.status === 'approved');
    const pendingRequest = userRequests.some(r => r.status === 'pending');

    return { user, hasAccess, pendingRequest };
  }

  loadRequests(): void {
    this.loadingRequests.set(true);
    this.validationService.getValidationRequests({ request_type: 'module_access' }).subscribe({
      next: (response) => {
        this.allRequests.set(response.results);
        this.loadingRequests.set(false);
      },
      error: (error) => {
        console.error('Erreur chargement demandes modules:', error);
        this.loadingRequests.set(false);
      }
    });
  }

  loadAllUsers(): void {
    this.adminService.getUsers({ page_size: 1000 }).subscribe({
      next: (response) => {
        this.allUsers.set(response.results);
      },
      error: (error) => {
        console.error('Erreur chargement utilisateurs:', error);
      }
    });
  }

  getModuleUserCount(moduleCode: ModuleCode): number {
    return this.allRequests().filter(
      r => r.request_type === 'module_access' &&
           r.status === 'approved' &&
           r.target_name?.toLowerCase().includes(moduleCode)
    ).length;
  }

  getUsersWithAccess(): UserWithModuleAccess[] {
    const moduleCode = this.selectedModule()?.code;
    if (!moduleCode) return [];

    const approvedRequests = this.allRequests().filter(
      r => r.request_type === 'module_access' &&
           r.status === 'approved' &&
           r.target_name?.toLowerCase().includes(moduleCode)
    );

    const userIds = [...new Set(approvedRequests.map(r => r.requester_id))];

    return userIds.map(userId => {
      const user = this.allUsers().find(u => u.id_role === userId);
      if (user) {
        return { user, hasAccess: true, pendingRequest: false };
      }
      // Creer un utilisateur fictif si non trouve
      return {
        user: {
          id_role: userId,
          nom_role: approvedRequests.find(r => r.requester_id === userId)?.requester_name || 'Utilisateur',
          prenom_role: '',
          email: '',
          role_level: 'utilisateur' as const,
          active: true
        } as AdminUser,
        hasAccess: true,
        pendingRequest: false
      };
    }).filter(item => item.user);
  }

  openGrantAccessSection(module: ApplicationModule): void {
    this.selectedModule.set(module);
    this.userSearchQuery.set('');
    this.searchResults.set([]);
  }

  closeGrantAccessSection(): void {
    this.selectedModule.set(null);
    this.userSearchQuery.set('');
    this.searchResults.set([]);
  }

  onSearchUsers(query: string): void {
    this.searchSubject.next(query);
  }

  grantAccess(user: AdminUser): void {
    const module = this.selectedModule();
    if (!module) return;

    this.grantingAccess.set(true);

    // Creer une demande d'acces directement approuvee
    this.validationService.grantModuleAccess({
      user_id: user.id_role,
      module_code: module.code
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('admin.modules.messages.accessGranted', { user: `${user.prenom_role} ${user.nom_role}` }),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadRequests();
        this.grantingAccess.set(false);
        // Mettre a jour les resultats de recherche
        this.onSearchUsers(this.userSearchQuery());
      },
      error: (error) => {
        console.error('Erreur octroi acces:', error);
        this.snackBar.open(
          this.translate.instant('common.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.grantingAccess.set(false);
      }
    });
  }

  revokeAccess(user: AdminUser): void {
    const module = this.selectedModule();
    if (!module) return;

    this.validationService.revokeModuleAccess({
      user_id: user.id_role,
      module_code: module.code
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('admin.modules.messages.accessRevoked', { user: `${user.prenom_role} ${user.nom_role}` }),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadRequests();
      },
      error: (error) => {
        console.error('Erreur revocation acces:', error);
        this.snackBar.open(
          this.translate.instant('common.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  formatDate(dateString: string | null | undefined): string {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  }

  approveRequest(request: ValidationRequestListItem): void {
    this.processingRequest.set(request.id);
    this.validationService.approveRequest(request.id).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('admin.modules.messages.approved'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadRequests();
        this.processingRequest.set(null);
      },
      error: (error) => {
        console.error('Erreur approbation:', error);
        this.snackBar.open(
          this.translate.instant('common.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.processingRequest.set(null);
      }
    });
  }

  rejectRequest(request: ValidationRequestListItem): void {
    this.processingRequest.set(request.id);
    this.validationService.rejectRequest(request.id, { comment: 'Demande refusee' }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('admin.modules.messages.rejected'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadRequests();
        this.processingRequest.set(null);
      },
      error: (error) => {
        console.error('Erreur rejet:', error);
        this.snackBar.open(
          this.translate.instant('common.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.processingRequest.set(null);
      }
    });
  }
}
