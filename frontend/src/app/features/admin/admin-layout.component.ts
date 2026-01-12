import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';

// Note: 'referent' is an access level (is_referent computed), not a role level
type AccessLevel = 'referent' | 'admin_og' | 'super_admin';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  minRole?: AccessLevel;
  maxRole?: AccessLevel; // Exclusive to this role and below
  exactRole?: 'admin_og' | 'super_admin'; // Only for this exact role (not referent since it's not a role)
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
  // referent: sees only Plans de gestion and Validations
  // admin_og: sees Utilisateurs, Organismes, Sites, Plans, Validations (filtered by their organisme)
  // super_admin: sees everything (dashboard, utilisateurs, organismes, sites, plans, validations)
  // utilisateur: NO access to admin
  readonly navItems: NavItem[] = [
    { label: 'Tableau de bord', icon: 'fi-rr-dashboard', route: '/administration/dashboard', exactRole: 'super_admin' },
    { label: 'Validations', icon: 'fi-rr-check-circle', route: '/administration/validations', minRole: 'referent' },
    { label: 'Utilisateurs', icon: 'fi-rr-users', route: '/administration/utilisateurs', minRole: 'admin_og' },
    { label: 'Organismes', icon: 'fi-rr-building', route: '/administration/organismes', minRole: 'admin_og' },
    { label: 'Sites', icon: 'fi-rr-marker', route: '/administration/sites', minRole: 'admin_og' },
    { label: 'Plans de gestion', icon: 'fi-rr-document', route: '/administration/plans', minRole: 'referent' }
  ];

  visibleNavItems = computed(() => {
    const user = this.currentUser();
    if (!user) return [];

    // Access level hierarchy (referent is computed, not a role)
    const accessHierarchy = ['utilisateur', 'referent', 'admin_og', 'super_admin'];

    // Get user's effective access level
    const getUserAccessIndex = (): number => {
      if (user.niveau_role === 'super_admin') return 3;
      if (user.niveau_role === 'admin_og') return 2;
      if (user.is_referent) return 1;
      return 0;
    };
    const userAccessIndex = getUserAccessIndex();

    return this.navItems.filter(item => {
      // exactRole: only for this specific role level
      if (item.exactRole) {
        return user.niveau_role === item.exactRole;
      }

      // maxRole: only for access levels up to this level (excludes higher)
      if (item.maxRole) {
        const maxAccessIndex = accessHierarchy.indexOf(item.maxRole);
        if (userAccessIndex > maxAccessIndex) return false;
      }

      // minRole: requires at least this access level
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
      'admin_og': 'Admin Organisme',
      'utilisateur': 'Utilisateur'
    };

    // If user is a referent (via is_referent), show that
    if (user.is_referent && user.niveau_role === 'utilisateur') {
      return 'Referent';
    }

    return labels[user.niveau_role] || user.niveau_role;
  });
}
