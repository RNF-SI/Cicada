import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule, NavigationEnd } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatMenuModule } from '@angular/material/menu';
import { AuthService } from '../../../core/services/auth.service';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs/operators';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterModule, MatButtonModule, MatDividerModule, MatMenuModule],
  templateUrl: './header.component.html',
  styleUrl: './header.component.scss'
})
export class HeaderComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  // Menu state
  menuOpen = false;

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

  // Impersonation state
  readonly isImpersonating = this.authService.isImpersonating;
  readonly impersonationInfo = this.authService.impersonationInfo;

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
        // Redirect to admin users page after stopping impersonation
        this.router.navigate(['/administration/utilisateurs']);
      },
      error: () => {
        // Even on error, redirect to home
        this.router.navigate(['/']);
      }
    });
  }
}
