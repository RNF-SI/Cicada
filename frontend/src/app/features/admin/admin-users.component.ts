import { Component, inject, signal, computed, OnInit, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import { AdminUser as ApiUser, AdminOrganisme, UserSiteRelation } from '../../core/models/admin.model';
import { UserRole } from '../../core/models/user.model';
import {
  LinkUserOrganismeModalComponent,
  LinkUserSiteModalComponent,
  DeactivateUserModalComponent,
  DeactivateUserModalResult,
  RemoveUserOrganismeModalComponent,
  RemoveUserOrganismeModalResult,
  AdminRoleChangeModalComponent,
  AdminRoleChangeModalResult
} from '../../shared/components/modals';
import { ValidationService } from '../../core/services/validation.service';

// Interface for display site
interface DisplaySite {
  id: number;
  nom: string;
  isReferent: boolean;
}

// Interface for display plan
interface DisplayPlan {
  id: number;
  nom: string;
  statut: string;
}

// Interface for display
interface DisplayUser {
  id: number;
  email: string;
  nom: string;
  prenom: string;
  organisme: string;
  organismeId: number;
  organismeUuid?: string;
  role: UserRole;
  isActive: boolean;
  lastLogin?: string;
  sites: DisplaySite[];
  plans: DisplayPlan[];
  // RGPD fields
  deletionRequestedAt?: string | null;
  isAnonymized: boolean;
  daysUntilDeletion?: number;
}

interface DisplayOrganisme {
  id: number;
  nom: string;
}

@Component({
  selector: 'app-admin-users',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslateModule
  ],
  templateUrl: './admin-users.component.html',
  styleUrl: './admin-users.component.scss'
})
export class AdminUsersComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);
  private readonly validationService = inject(ValidationService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly router = inject(Router);
  private readonly translate = inject(TranslateService);

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isImpersonating = this.authService.isImpersonating;

  // Filter state
  searchQuery = '';
  filterRole = '';
  filterOrganisme = '';
  filterStatus = '';
  isLoading = signal(false);

  users = signal<DisplayUser[]>([]);
  organismes = signal<DisplayOrganisme[]>([]);
  filteredUsers = signal<DisplayUser[]>([]);

  // Track previous user ID to detect user changes (e.g., after stopping impersonation)
  private previousUserId: number | null = null;
  private initialized = false;

  currentOrganismeName = computed(() => {
    return this.currentUser()?.organisme?.nom_organisme || '';
  });

  constructor() {
    // Effect to reload data when user changes (e.g., after stopping impersonation)
    effect(() => {
      const user = this.currentUser();
      const currentUserId = user?.id ?? null;

      // Skip first execution during ngOnInit
      if (!this.initialized) {
        this.previousUserId = currentUserId;
        return;
      }

      // Reload data if user ID changed
      if (currentUserId !== this.previousUserId) {
        this.previousUserId = currentUserId;
        // Reset filters and reload data
        this.searchQuery = '';
        this.filterRole = '';
        this.filterOrganisme = '';
        this.filterStatus = '';
        this.loadData();
      }
    });
  }

  ngOnInit(): void {
    this.initialized = true;
    this.loadData();
  }

  loadData(): void {
    this.isLoading.set(true);

    // Load organismes for filter dropdown
    this.adminService.getOrganismes().subscribe({
      next: (response) => {
        this.organismes.set(response.results.map(org => ({
          id: org.id_organisme,
          nom: org.nom_organisme
        })));
      }
    });

    // Load users
    this.loadUsers();
  }

  loadUsers(): void {
    this.isLoading.set(true);
    this.adminService.getUsers({ search: this.searchQuery || undefined }).subscribe({
      next: (response) => {
        const mapped = response.results.map(user => this.mapUser(user));
        this.users.set(mapped);
        this.applyFilters();
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
        this.isLoading.set(false);
      }
    });
  }

  private mapUser(user: ApiUser): DisplayUser {
    const sites: DisplaySite[] = (user.sites_lies || []).map(relation => ({
      id: relation.site.id_site,
      nom: relation.site.nom_site,
      isReferent: relation.referent
    }));

    const plans: DisplayPlan[] = (user.plans_referent || []).map(plan => ({
      id: plan.id_pg,
      nom: plan.nom,
      statut: plan.statut
    }));

    // Calculate days until deletion (30 days grace period)
    let daysUntilDeletion: number | undefined;
    if (user.deletion_requested_at) {
      const requestDate = new Date(user.deletion_requested_at);
      const deletionDate = new Date(requestDate.getTime() + 30 * 24 * 60 * 60 * 1000);
      const now = new Date();
      daysUntilDeletion = Math.ceil((deletionDate.getTime() - now.getTime()) / (24 * 60 * 60 * 1000));
      if (daysUntilDeletion < 0) daysUntilDeletion = 0;
    }

    return {
      id: user.id_role,
      email: user.email,
      nom: user.nom_role || '',
      prenom: user.prenom_role || '',
      organisme: user.organisme?.nom_organisme || 'Non assigne',
      organismeId: user.organisme?.id_organisme || 0,
      organismeUuid: user.organisme?.uuid_organisme,
      role: user.role_level,
      isActive: user.active,
      lastLogin: user.last_login ? new Date(user.last_login).toLocaleDateString('fr-FR') : undefined,
      sites,
      plans,
      deletionRequestedAt: user.deletion_requested_at,
      isAnonymized: user.is_anonymized || false,
      daysUntilDeletion
    };
  }

  getSiteRoles(site: DisplaySite): string {
    return site.isReferent ? 'Referent' : 'Associe';
  }

  getOtherSitesNames(sites: DisplaySite[]): string {
    return sites.slice(2).map(s => s.nom).join(', ');
  }

  getOtherPlansNames(plans: DisplayPlan[]): string {
    return plans.slice(2).map(p => p.nom).join(', ');
  }

  filterUsers(): void {
    this.applyFilters();
  }

  private applyFilters(): void {
    let result = this.users();

    // Filter by search query
    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      result = result.filter(user =>
        user.nom.toLowerCase().includes(query) ||
        user.prenom.toLowerCase().includes(query) ||
        user.email.toLowerCase().includes(query)
      );
    }

    // Filter by role
    if (this.filterRole) {
      result = result.filter(user => user.role === this.filterRole);
    }

    // Filter by organisme (super admin only)
    if (this.filterOrganisme) {
      result = result.filter(user => user.organismeId === parseInt(this.filterOrganisme));
    }

    // Filter by status
    if (this.filterStatus) {
      if (this.filterStatus === 'deletion_pending') {
        result = result.filter(user => user.deletionRequestedAt != null);
      } else {
        const isActive = this.filterStatus === 'active';
        result = result.filter(user => user.isActive === isActive && !user.deletionRequestedAt);
      }
    }

    // For non-super admin, only show users from their organisme
    if (!this.isSuperAdmin()) {
      const currentOrgId = this.currentUser()?.organisme?.id_organisme;
      if (currentOrgId) {
        result = result.filter(user => user.organismeId === currentOrgId);
      }
    }

    this.filteredUsers.set(result);
  }

  getInitials(user: DisplayUser): string {
    const first = user.prenom?.charAt(0) || '';
    const last = user.nom?.charAt(0) || '';
    return `${first}${last}`.toUpperCase() || user.email.charAt(0).toUpperCase();
  }

  getRoleLabel(role: UserRole): string {
    return this.translate.instant('admin.users.roles.' + role);
  }

  canManageUser(user: DisplayUser): boolean {
    // Cannot manage super admin unless you are super admin
    if (user.role === 'super_admin' && !this.isSuperAdmin()) {
      return false;
    }
    // Cannot manage yourself
    if (user.id === this.currentUser()?.id) {
      return false;
    }
    return true;
  }

  openAssignOrganismeModal(user: DisplayUser): void {
    const dialogRef = this.dialog.open(LinkUserOrganismeModalComponent, {
      width: '500px',
      data: {
        user: {
          id_role: user.id,
          email: user.email,
          nom_role: user.nom,
          prenom_role: user.prenom,
          id_organisme: user.organismeId || null,
          organisme: user.organismeUuid ? {
            id_organisme: user.organismeId,
            uuid_organisme: user.organismeUuid,
            nom_organisme: user.organisme
          } : null
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        this.snackBar.open(this.translate.instant('admin.users.messages.organismeUpdated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadUsers();
      }
    });
  }

  openAssignSiteModal(user: DisplayUser): void {
    // Build sites_lies from DisplaySite array
    const sitesLies = user.sites.map(s => ({
      site: {
        id_site: s.id,
        nom_site: s.nom,
        active: true
      },
      referent: s.isReferent
    }));

    const dialogRef = this.dialog.open(LinkUserSiteModalComponent, {
      width: '650px',
      maxHeight: '85vh',
      data: {
        user: {
          id_role: user.id,
          email: user.email,
          nom_role: user.nom,
          prenom_role: user.prenom,
          sites_lies: sitesLies
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success && result?.changed) {
        this.snackBar.open(this.translate.instant('admin.users.messages.sitesUpdated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadUsers();
      }
    });
  }

  editUser(user: DisplayUser): void {
    // For now, show organisme assignment modal
    this.openAssignOrganismeModal(user);
  }

  toggleUserStatus(user: DisplayUser): void {
    if (!this.canManageUser(user)) {
      this.snackBar.open(this.translate.instant('admin.users.messages.cannotModify'), 'OK', { duration: 3000 });
      return;
    }

    // If deactivating, show confirmation modal with reason
    if (user.isActive) {
      const dialogRef = this.dialog.open(DeactivateUserModalComponent, {
        width: '500px',
        data: {
          userName: `${user.prenom} ${user.nom}`.trim() || user.email,
          userEmail: user.email
        }
      });

      dialogRef.afterClosed().subscribe((result: DeactivateUserModalResult) => {
        if (result?.confirmed) {
          this.adminService.toggleUserStatus(user.id, false).subscribe({
            next: () => {
              this.snackBar.open(this.translate.instant('admin.users.messages.userDeactivated'), this.translate.instant('common.actions.close'), { duration: 3000 });
              this.loadUsers();
            },
            error: (error: Error) => {
              this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
            }
          });
        }
      });
    } else {
      // If activating, proceed directly
      this.adminService.toggleUserStatus(user.id, true).subscribe({
        next: () => {
          this.snackBar.open(this.translate.instant('admin.users.messages.userActivated'), this.translate.instant('common.actions.close'), { duration: 3000 });
          this.loadUsers();
        },
        error: (error: Error) => {
          this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
        }
      });
    }
  }

  deleteUser(user: DisplayUser): void {
    // User deletion is sensitive - redirect to Django admin
    this.snackBar.open(this.translate.instant('admin.users.messages.deletionNotAvailable'), 'OK', { duration: 5000 });
  }

  removeUserFromOrganisme(user: DisplayUser): void {
    if (!this.canManageUser(user)) {
      this.snackBar.open(this.translate.instant('admin.users.messages.cannotModify'), 'OK', { duration: 3000 });
      return;
    }

    // Show confirmation modal with reason
    const dialogRef = this.dialog.open(RemoveUserOrganismeModalComponent, {
      width: '500px',
      data: {
        userName: `${user.prenom} ${user.nom}`.trim() || user.email,
        userEmail: user.email,
        organismeName: user.organisme
      }
    });

    dialogRef.afterClosed().subscribe((result: RemoveUserOrganismeModalResult) => {
      if (result?.confirmed) {
        // First remove from organisme, then deactivate
        this.adminService.assignOrganismeToUser(user.id, null).subscribe({
          next: () => {
            // Now deactivate the user
            this.adminService.toggleUserStatus(user.id, false).subscribe({
              next: () => {
                this.snackBar.open(this.translate.instant('admin.users.messages.removedFromOrganisme'), this.translate.instant('common.actions.close'), { duration: 3000 });
                this.loadUsers();
              },
              error: (error: Error) => {
                // User was removed from organisme but deactivation failed
                this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
                this.loadUsers();
              }
            });
          },
          error: (error: Error) => {
            this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
          }
        });
      }
    });
  }

  /**
   * Check if current user can impersonate the target user
   * Only super_admin can impersonate, and cannot impersonate other super_admins
   */
  canImpersonateUser(user: DisplayUser): boolean {
    // Must be super admin to impersonate
    if (!this.isSuperAdmin()) {
      return false;
    }
    // Cannot impersonate yourself
    if (user.id === this.currentUser()?.id) {
      return false;
    }
    // Cannot impersonate other super admins
    if (user.role === 'super_admin') {
      return false;
    }
    // Cannot impersonate inactive users
    if (!user.isActive) {
      return false;
    }
    return true;
  }

  /**
   * Start impersonation session for the specified user
   */
  startImpersonation(user: DisplayUser): void {
    if (!this.canImpersonateUser(user)) {
      this.snackBar.open(this.translate.instant('admin.users.messages.cannotModify'), 'OK', { duration: 3000 });
      return;
    }

    const userName = `${user.prenom} ${user.nom}`.trim();
    this.snackBar.open(this.translate.instant('admin.users.messages.impersonationStarting', { name: userName }), 'OK', { duration: 2000 });

    this.authService.startImpersonation(user.id).subscribe({
      next: () => {
        this.snackBar.open(this.translate.instant('admin.users.messages.impersonationStarted', { name: userName }), 'OK', { duration: 3000 });
        // Navigate to home page as the impersonated user
        this.router.navigate(['/']);
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
      }
    });
  }

  /**
   * Check if current admin can request promotion for the user
   * Admin_og can only promote users from their own organisme
   */
  canRequestPromotion(user: DisplayUser): boolean {
    // Cannot promote yourself
    if (user.id === this.currentUser()?.id) {
      return false;
    }
    // User must be a simple utilisateur
    if (user.role !== 'utilisateur') {
      return false;
    }
    // User must be active
    if (!user.isActive) {
      return false;
    }
    // For admin_og, must be same organisme
    if (!this.isSuperAdmin()) {
      const currentOrgId = this.currentUser()?.organisme?.id_organisme;
      if (user.organismeId !== currentOrgId) {
        return false;
      }
    }
    return true;
  }

  /**
   * Check if current admin can request demotion for the user
   * Admin_og can only demote admin_og from their own organisme
   */
  canRequestDemotion(user: DisplayUser): boolean {
    // Cannot demote yourself
    if (user.id === this.currentUser()?.id) {
      return false;
    }
    // User must be an admin_og
    if (user.role !== 'admin_og') {
      return false;
    }
    // User must be active
    if (!user.isActive) {
      return false;
    }
    // For admin_og, must be same organisme
    if (!this.isSuperAdmin()) {
      const currentOrgId = this.currentUser()?.organisme?.id_organisme;
      if (user.organismeId !== currentOrgId) {
        return false;
      }
    }
    return true;
  }

  /**
   * Open modal to request admin promotion
   */
  requestAdminPromotion(user: DisplayUser): void {
    const dialogRef = this.dialog.open(AdminRoleChangeModalComponent, {
      width: '500px',
      data: {
        type: 'promotion',
        userName: `${user.prenom} ${user.nom}`.trim() || user.email,
        userEmail: user.email
      }
    });

    dialogRef.afterClosed().subscribe((result: AdminRoleChangeModalResult) => {
      if (result?.confirmed && result.justification) {
        this.validationService.requestAdminPromotion(user.id, result.justification).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('modals.adminRoleChange.messages.promotionSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
          },
          error: (error: { error?: { error?: string } }) => {
            this.snackBar.open(
              error.error?.error || this.translate.instant('modals.adminRoleChange.messages.error'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
          }
        });
      }
    });
  }

  /**
   * Open modal to request admin demotion
   */
  requestAdminDemotion(user: DisplayUser): void {
    const dialogRef = this.dialog.open(AdminRoleChangeModalComponent, {
      width: '500px',
      data: {
        type: 'demotion',
        userName: `${user.prenom} ${user.nom}`.trim() || user.email,
        userEmail: user.email
      }
    });

    dialogRef.afterClosed().subscribe((result: AdminRoleChangeModalResult) => {
      if (result?.confirmed && result.justification) {
        this.validationService.requestAdminDemotion(user.id, result.justification).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('modals.adminRoleChange.messages.demotionSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
          },
          error: (error: { error?: { error?: string } }) => {
            this.snackBar.open(
              error.error?.error || this.translate.instant('modals.adminRoleChange.messages.error'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
          }
        });
      }
    });
  }
}
