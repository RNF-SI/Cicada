import { Component, inject, computed, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ErrorLogService } from '../../core/services/error-log.service';
import { filter } from 'rxjs/operators';

// Note: 'referent' is an access level (is_referent computed), not a role level
type AccessLevel = 'referent' | 'admin_og' | 'super_admin';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  minRole?: AccessLevel;
  maxRole?: AccessLevel; // Exclusive to this role and below
  exactRole?: 'admin_og' | 'super_admin'; // Only for this exact role (not referent since it's not a role)
  badgeSignal?: string; // Name of signal to use for badge count (e.g., 'errorLogCount')
}

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './admin-layout.component.html',
  styleUrl: './admin-layout.component.scss'
})
export class AdminLayoutComponent implements OnInit, OnDestroy {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly errorLogService = inject(ErrorLogService);

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;

  // Signal pour le badge des logs d'erreur
  readonly errorLogCount = this.errorLogService.unacknowledgedCount;

  // Impersonation state
  readonly isImpersonating = this.authService.isImpersonating;
  readonly impersonationInfo = this.authService.impersonationInfo;

  // Mobile sidebar state
  readonly sidebarOpen = signal(false);

  get userDisplayName(): string {
    return this.authService.getUserDisplayName();
  }

  get originalUserDisplayName(): string {
    return this.authService.getOriginalUserDisplayName();
  }

  ngOnInit(): void {
    // Demarrer le rafraichissement du badge si super_admin
    if (this.isSuperAdmin()) {
      this.errorLogService.startAutoRefresh(60000);
    }

    // Fermer le sidebar mobile lors de la navigation
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd)
    ).subscribe(() => {
      this.closeSidebar();
    });
  }

  toggleSidebar(): void {
    this.sidebarOpen.update(open => !open);
    document.body.style.overflow = this.sidebarOpen() ? 'hidden' : '';
  }

  closeSidebar(): void {
    this.sidebarOpen.set(false);
    document.body.style.overflow = '';
  }

  ngOnDestroy(): void {
    this.errorLogService.stopAutoRefresh();
  }

  stopImpersonation(): void {
    this.authService.stopImpersonation().subscribe({
      next: () => {
        // Force full page reload to reset Angular state and sync all tabs
        window.location.href = '/administration/utilisateurs';
      },
      error: () => {
        window.location.href = '/';
      }
    });
  }

  // Navigation items with role-based visibility
  // referent: sees Validations, Sites (their assigned), Plans (their assigned)
  // admin_og: sees Utilisateurs, Organismes, Sites, Plans, Validations (filtered by their organisme)
  // super_admin: sees everything (dashboard, utilisateurs, organismes, sites, plans, validations)
  // utilisateur: NO access to admin
  readonly navItems: NavItem[] = [
    { label: 'Tableau de bord', icon: 'fi-rr-dashboard', route: '/administration/dashboard', exactRole: 'super_admin' },
    { label: 'Validations', icon: 'fi-rr-check-circle', route: '/administration/validations', minRole: 'referent' },
    { label: 'Utilisateurs', icon: 'fi-rr-users', route: '/administration/utilisateurs', minRole: 'admin_og' },
    { label: 'Organismes', icon: 'fi-rr-building', route: '/administration/organismes', minRole: 'admin_og' },
    { label: 'Sites', icon: 'fi-rr-marker', route: '/administration/sites', minRole: 'referent' },
    { label: 'Plans de gestion', icon: 'fi-rr-document', route: '/administration/plans', minRole: 'referent' },
    { label: 'Rédacteurs généraux', icon: 'fi-rr-pen-nib', route: '/administration/redacteurs-principaux', exactRole: 'super_admin' },
    { label: 'Acces modules', icon: 'fi-rr-apps', route: '/administration/modules', exactRole: 'super_admin' },
    { label: 'Logs erreurs', icon: 'fi-rr-bug', route: '/administration/logs', exactRole: 'super_admin', badgeSignal: 'errorLogCount' },
    { label: 'RGPD', icon: 'fi-rr-shield-check', route: '/administration/rgpd', exactRole: 'super_admin' },
    { label: 'Paramètres', icon: 'fi-rr-settings', route: '/administration/parametres', exactRole: 'super_admin' }
  ];

  visibleNavItems = computed(() => {
    const user = this.currentUser();
    if (!user) return [];

    // Access level hierarchy (referent is computed, not a role)
    const accessHierarchy = ['utilisateur', 'referent', 'admin_og', 'redacteur_principal', 'super_admin'];

    // Get user's effective access level
    const getUserAccessIndex = (): number => {
      if (user.niveau_role === 'super_admin') return 4;
      if (user.niveau_role === 'redacteur_principal') return 3;
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
      'redacteur_principal': 'Rédacteur Général',
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
