import { Component, inject, signal, computed, OnInit, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
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
  RemoveUserOrganismeModalResult
} from '../../shared/components/modals';

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
    MatTooltipModule
  ],
  templateUrl: './admin-users.component.html',
  styleUrl: './admin-users.component.scss'
})
export class AdminUsersComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly router = inject(Router);

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
        this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
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
      plans
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
      const isActive = this.filterStatus === 'active';
      result = result.filter(user => user.isActive === isActive);
    }

    // For non-super admin, only show users from their organisme
    if (!this.isSuperAdmin()) {
      const currentOrgId = this.currentUser()?.organisme?.id;
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
    const labels: Record<string, string> = {
      'super_admin': 'Super Admin',
      'admin_og': 'Admin Org.',
      'utilisateur': 'Utilisateur'
    };
    return labels[role] || role;
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
        this.snackBar.open('Organisme mis a jour', 'Fermer', { duration: 3000 });
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
        this.snackBar.open('Sites de l\'utilisateur mis a jour', 'Fermer', { duration: 3000 });
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
      this.snackBar.open('Vous ne pouvez pas modifier cet utilisateur', 'OK', { duration: 3000 });
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
              this.snackBar.open('Utilisateur desactive', 'Fermer', { duration: 3000 });
              this.loadUsers();
            },
            error: (error: Error) => {
              this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
            }
          });
        }
      });
    } else {
      // If activating, proceed directly
      this.adminService.toggleUserStatus(user.id, true).subscribe({
        next: () => {
          this.snackBar.open('Utilisateur active', 'Fermer', { duration: 3000 });
          this.loadUsers();
        },
        error: (error: Error) => {
          this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
        }
      });
    }
  }

  deleteUser(user: DisplayUser): void {
    // User deletion is sensitive - redirect to Django admin
    this.snackBar.open('La suppression d\'utilisateur n\'est pas disponible ici. Utilisez l\'admin Django.', 'OK', { duration: 5000 });
  }

  removeUserFromOrganisme(user: DisplayUser): void {
    if (!this.canManageUser(user)) {
      this.snackBar.open('Vous ne pouvez pas modifier cet utilisateur', 'OK', { duration: 3000 });
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
                this.snackBar.open('Utilisateur retire de l\'organisme et desactive', 'Fermer', { duration: 3000 });
                this.loadUsers();
              },
              error: (error: Error) => {
                // User was removed from organisme but deactivation failed
                this.snackBar.open(`Utilisateur retire mais erreur lors de la desactivation: ${error.message}`, 'Fermer', { duration: 5000 });
                this.loadUsers();
              }
            });
          },
          error: (error: Error) => {
            this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
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
      this.snackBar.open('Vous ne pouvez pas visualiser en tant que cet utilisateur', 'OK', { duration: 3000 });
      return;
    }

    this.snackBar.open(`Demarrage de la session en tant que ${user.prenom} ${user.nom}...`, 'OK', { duration: 2000 });

    this.authService.startImpersonation(user.id).subscribe({
      next: () => {
        this.snackBar.open(`Vous visualisez maintenant en tant que ${user.prenom} ${user.nom}`, 'OK', { duration: 3000 });
        // Navigate to home page as the impersonated user
        this.router.navigate(['/']);
      },
      error: (error: Error) => {
        this.snackBar.open(`Erreur: ${error.message}`, 'Fermer', { duration: 5000 });
      }
    });
  }
}
