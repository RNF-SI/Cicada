import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
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
  LinkUserSiteModalComponent
} from '../../shared/components/modals';

// Interface for display site
interface DisplaySite {
  id: number;
  nom: string;
  isReferent: boolean;
  isConservateur: boolean;
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

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;

  // Filter state
  searchQuery = '';
  filterRole = '';
  filterOrganisme = '';
  filterStatus = '';
  isLoading = signal(false);

  users = signal<DisplayUser[]>([]);
  organismes = signal<DisplayOrganisme[]>([]);
  filteredUsers = signal<DisplayUser[]>([]);

  currentOrganismeName = computed(() => {
    return this.currentUser()?.organisme?.nom_organisme || '';
  });

  ngOnInit(): void {
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
      isReferent: relation.referent,
      isConservateur: relation.conservateur
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
      sites
    };
  }

  getSiteRoles(site: DisplaySite): string {
    const roles: string[] = [];
    if (site.isReferent) roles.push('Referent');
    if (site.isConservateur) roles.push('Conservateur');
    return roles.length > 0 ? roles.join(', ') : 'Associe';
  }

  getOtherSitesNames(sites: DisplaySite[]): string {
    return sites.slice(2).map(s => s.nom).join(', ');
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
      'referent': 'Referent',
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
      referent: s.isReferent,
      conservateur: s.isConservateur
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

    this.adminService.toggleUserStatus(user.id, !user.isActive).subscribe({
      next: () => {
        this.snackBar.open(
          user.isActive ? 'Utilisateur desactive' : 'Utilisateur active',
          'Fermer',
          { duration: 3000 }
        );
        this.loadUsers();
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
      }
    });
  }

  deleteUser(user: DisplayUser): void {
    // User deletion is sensitive - redirect to Django admin
    this.snackBar.open('La suppression d\'utilisateur n\'est pas disponible ici. Utilisez l\'admin Django.', 'OK', { duration: 5000 });
  }
}
