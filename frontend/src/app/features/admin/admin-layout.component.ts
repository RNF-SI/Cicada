import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  minRole?: 'referent' | 'admin_og' | 'super_admin';
  maxRole?: 'referent' | 'admin_og' | 'super_admin'; // Exclusive to this role and below
  exactRole?: 'referent' | 'admin_og' | 'super_admin'; // Only for this exact role
}

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './admin-layout.component.html',
  styleUrl: './admin-layout.component.scss'
})
export class AdminLayoutComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;

  // Impersonation state
  readonly isImpersonating = this.authService.isImpersonating;
  readonly impersonationInfo = this.authService.impersonationInfo;

  get userDisplayName(): string {
    return this.authService.getUserDisplayName();
  }

  get originalUserDisplayName(): string {
    return this.authService.getOriginalUserDisplayName();
  }

  stopImpersonation(): void {
    this.authService.stopImpersonation().subscribe({
      next: () => {
        this.router.navigate(['/administration/utilisateurs']);
      },
      error: () => {
        this.router.navigate(['/']);
      }
    });
  }

  // Navigation items with role-based visibility
  // admin_og: sees Utilisateurs, Organismes, Sites, Plans (filtered by their organisme)
  // super_admin: sees everything (dashboard, utilisateurs, organismes, sites, plans)
  // referent & utilisateur: NO access to admin
  readonly navItems: NavItem[] = [
    { label: 'Tableau de bord', icon: 'fi-rr-dashboard', route: '/administration/dashboard', exactRole: 'super_admin' },
    { label: 'Utilisateurs', icon: 'fi-rr-users', route: '/administration/utilisateurs', minRole: 'admin_og' },
    { label: 'Organismes', icon: 'fi-rr-building', route: '/administration/organismes', minRole: 'admin_og' },
    { label: 'Sites', icon: 'fi-rr-marker', route: '/administration/sites', minRole: 'admin_og' },
    { label: 'Plans de gestion', icon: 'fi-rr-document', route: '/administration/plans', minRole: 'admin_og' }
  ];

  visibleNavItems = computed(() => {
    const user = this.currentUser();
    if (!user) return [];

    const roleHierarchy = ['utilisateur', 'referent', 'admin_og', 'super_admin'];
    const userRoleIndex = roleHierarchy.indexOf(user.niveau_role);

    return this.navItems.filter(item => {
      // exactRole: only for this specific role
      if (item.exactRole) {
        return user.niveau_role === item.exactRole;
      }

      // maxRole: only for roles up to this level (excludes higher roles)
      if (item.maxRole) {
        const maxRoleIndex = roleHierarchy.indexOf(item.maxRole);
        if (userRoleIndex > maxRoleIndex) return false;
      }

      // minRole: requires at least this role
      if (item.minRole) {
        return this.authService.hasRole(item.minRole);
      }

      return true;
    });
  });

  roleLabel = computed(() => {
    const user = this.currentUser();
    if (!user) return '';

    const labels: Record<string, string> = {
      'super_admin': 'Super Administrateur',
      'admin_og': 'Admin Organisme'
    };
    return labels[user.niveau_role] || user.niveau_role;
  });
}
