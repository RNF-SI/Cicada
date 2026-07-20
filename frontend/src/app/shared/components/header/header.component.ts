import { Component, inject, signal, computed, OnInit, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenuModule } from '@angular/material/menu';
import { TranslateModule } from '@ngx-translate/core';
import { trigger, state, style, transition, animate } from '@angular/animations';
import { AuthService } from '../../../core/services/auth.service';
import { ImpersonationGuardService } from '../../../core/services/impersonation-guard.service';
import { ModuleService } from '../../../core/services/module.service';
import { SettingsService } from '../../../core/services/settings.service';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs/operators';
import { NotificationBellComponent } from '../notification-bell/notification-bell.component';

/**
 * Interface for sidebar module definition
 */
interface SidebarModule {
  code: string;
  name: string;
  icon: string;
  route: string;
  requiresAccess: boolean;
  isDeveloped: boolean;
}

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterModule, MatButtonModule, MatDividerModule, MatMenuModule, NotificationBellComponent, TranslateModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss',
  animations: [
    trigger('slideAnimation', [
      state('closed', style({
        transform: 'translateX(-100%)'
      })),
      state('open', style({
        transform: 'translateX(0)'
      })),
      transition('closed <=> open', [
        animate('300ms ease-in-out')
      ])
    ]),
    trigger('fadeAnimation', [
      transition(':enter', [
        style({ opacity: 0 }),
        animate('200ms ease-in', style({ opacity: 1 }))
      ]),
      transition(':leave', [
        animate('200ms ease-out', style({ opacity: 0 }))
      ])
    ])
  ]
})
export class HeaderComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly impersonationGuard = inject(ImpersonationGuardService);
  private readonly moduleService = inject(ModuleService);
  private readonly settings = inject(SettingsService);

  // #448 — Personnalisation du bandeau (couleur + logo structure).
  readonly headerColor = computed(() => this.settings.config()?.header_color || this.settings.defaultHeaderColor);
  readonly structureLogoUrl = computed(() => this.settings.config()?.structure_logo_url || null);
  /** Vrai si la couleur du bandeau est foncée → contenu en blanc (lisibilité). */
  readonly headerOnDark = computed(() => this.isDarkColor(this.headerColor()));

  /**
   * #448 — Couleur de premier plan du bandeau (texte, icônes, cloche), exposée
   * comme variable CSS `--header-fg`. Calculée à partir de la luminance de la
   * couleur du bandeau pour garantir un contraste suffisant quelle que soit la
   * couleur choisie : la cloche de notifications notamment ne se fond plus dans
   * le bandeau (ex. fond bleu primary = cloche blanche, et non plus invisible).
   */
  readonly headerForeground = computed(() => this.headerOnDark() ? '#FFFFFF' : '#025359');

  /** Luminance relative approchée : sombre si < 0.5 (texte blanc requis). */
  private isDarkColor(hex: string): boolean {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex || '');
    if (!m) return true;
    const n = parseInt(m[1], 16);
    const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    // Luminance perçue (sRGB simplifiée).
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance < 0.6;
  }

  // Menu state
  menuOpen = false;

  // Static sidebar modules definition
  // These are always shown regardless of API availability
  readonly sidebarModules: SidebarModule[] = [
    { code: 'plans', name: 'Plans de gestion', icon: 'fi-rr-document', route: '/plans', requiresAccess: false, isDeveloped: true },
    { code: 'sites', name: 'Sites', icon: 'fi-rr-marker', route: '/sites', requiresAccess: false, isDeveloped: true },
    { code: 'inventaires', name: 'Mes inventaires et suivis', icon: 'fi-rr-test-tube', route: '/inventaires', requiresAccess: false, isDeveloped: true },
    { code: 'zonages', name: 'Zonages réglementaires', icon: 'fi-rr-layers', route: '/zonages', requiresAccess: true, isDeveloped: false },
    { code: 'exploration', name: 'Exploration des données', icon: 'fi-rr-search', route: '/exploration', requiresAccess: false, isDeveloped: true },
  ];

  // Modules the user has access to (from API)
  private readonly _accessibleModuleCodes = signal<Set<string>>(new Set());

  // Track current route to detect home page
  private readonly currentUrl = toSignal(
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      map(event => event.urlAfterRedirects)
    ),
    { initialValue: this.router.url }
  );

  // Detect if we're on the home page
  readonly isHomePage = computed(() => {
    const url = this.currentUrl();
    return url === '/' || url === '/accueil' || url.startsWith('/accueil?');
  });

  // Expose auth state to template
  readonly isAuthenticated = this.authService.isAuthenticated;
  readonly currentUser = this.authService.currentUser;
  readonly canAccessAdmin = this.authService.canAccessAdmin;

  constructor() {
    // Load accessible modules when authentication state changes
    effect(() => {
      if (this.isAuthenticated()) {
        this.loadAccessibleModules();
      } else {
        this._accessibleModuleCodes.set(new Set());
      }
    });
  }

  ngOnInit(): void {
    // #448 — s'assurer que le thème (couleur bandeau + logo) est chargé pour
    // l'afficher sur toutes les pages (idempotent : seulement si pas déjà chargé).
    if (!this.settings.config()) {
      this.settings.loadSettings().subscribe();
    }
  }

  private loadAccessibleModules(): void {
    // Load modules the user has explicit access to (for modules requiring access like zonages)
    this.moduleService.getMyAccessibleModules().subscribe({
      next: (modules) => {
        const codes = new Set(modules.map(m => m.code));
        this._accessibleModuleCodes.set(codes);
      },
      error: () => this._accessibleModuleCodes.set(new Set())
    });
  }

  /**
   * Check if the user has access to a module
   */
  hasModuleAccess(module: SidebarModule): boolean {
    // Modules that don't require access are accessible to everyone
    if (!module.requiresAccess) {
      return true;
    }
    // Otherwise check if user has been granted access via API
    return this._accessibleModuleCodes().has(module.code);
  }

  /**
   * Check if a module should be visible in the sidebar
   * A module is visible if the user has access to it
   */
  shouldShowModule(module: SidebarModule): boolean {
    return this.hasModuleAccess(module);
  }

  // Impersonation state
  readonly isImpersonating = this.authService.isImpersonating;
  readonly impersonationInfo = this.authService.impersonationInfo;
  readonly isReadOnly = this.impersonationGuard.isReadOnly;

  get userDisplayName(): string {
    return this.authService.getUserDisplayName();
  }

  get originalUserDisplayName(): string {
    return this.authService.getOriginalUserDisplayName();
  }

  get userInitials(): string {
    const user = this.currentUser();
    if (!user) return '';

    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role.charAt(0)}${user.nom_role.charAt(0)}`.toUpperCase();
    }
    return user.email.charAt(0).toUpperCase();
  }

  /**
   * Check if the current route matches or starts with the given path
   */
  isActiveRoute(path: string): boolean {
    const currentUrl = this.currentUrl();
    if (path === '/accueil') {
      return currentUrl === '/' || currentUrl === '/accueil' || currentUrl.startsWith('/accueil?');
    }
    return currentUrl.startsWith(path);
  }

  toggleMenu(): void {
    this.menuOpen = !this.menuOpen;
    // Prevent body scroll when menu is open
    document.body.style.overflow = this.menuOpen ? 'hidden' : '';
  }

  logout(): void {
    this.authService.logout().subscribe();
  }

  openAdmin(): void {
    if (this.isImpersonating()) {
      // En mode impersonation, naviguer sur la même page pour garder le contexte
      this.router.navigate(['/administration']);
    } else {
      // En mode normal, ouvrir dans une nouvelle fenêtre
      window.open('/administration', '_blank');
    }
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
}
