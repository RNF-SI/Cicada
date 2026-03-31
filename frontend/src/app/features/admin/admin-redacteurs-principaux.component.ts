import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';

interface RedacteurPrincipal {
  id: number;
  nom: string;
  email: string;
  organisme: string;
}

interface SearchUser {
  id_role: number;
  email: string;
  nom_role: string;
  prenom_role: string;
  nom_complet: string;
  role_level: string;
  organisme?: { nom_organisme: string };
}

@Component({
  selector: 'app-admin-redacteurs-principaux',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatProgressSpinnerModule, MatSnackBarModule, TranslateModule
  ],
  templateUrl: './admin-redacteurs-principaux.component.html',
  styleUrls: ['./admin-redacteurs-principaux.component.scss']
})
export class AdminRedacteursPrincipauxComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  isLoading = signal(true);
  redacteurs = signal<RedacteurPrincipal[]>([]);

  // Search state for adding new redacteur
  showAddDialog = signal(false);
  searchQuery = signal('');
  searchResults = signal<SearchUser[]>([]);
  isSearching = signal(false);

  // Confirm remove
  confirmRemoveUser = signal<RedacteurPrincipal | null>(null);

  ngOnInit(): void {
    this.loadRedacteurs();
  }

  loadRedacteurs(): void {
    this.isLoading.set(true);
    this.adminService.getUsers({ role: 'redacteur_principal' }).subscribe({
      next: (response: any) => {
        const users = response.results || response;
        this.redacteurs.set(
          users.map((u: any) => ({
            id: u.id_role || u.id,
            nom: u.nom_complet || `${u.prenom_role || ''} ${u.nom_role || ''}`.trim(),
            email: u.email,
            organisme: u.organisme?.nom_organisme || '-',
          }))
        );
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      }
    });
  }

  openAddDialog(): void {
    this.showAddDialog.set(true);
    this.searchQuery.set('');
    this.searchResults.set([]);
  }

  closeAddDialog(): void {
    this.showAddDialog.set(false);
  }

  onSearch(): void {
    const query = this.searchQuery();
    if (query.length < 2) {
      this.searchResults.set([]);
      return;
    }
    this.isSearching.set(true);
    this.adminService.getUsers({ search: query }).subscribe({
      next: (response: any) => {
        const users = response.results || response;
        // Exclude already redacteur_principal and super_admin
        this.searchResults.set(
          users.filter((u: any) => u.role_level !== 'redacteur_principal' && u.role_level !== 'super_admin')
        );
        this.isSearching.set(false);
      },
      error: () => {
        this.isSearching.set(false);
      }
    });
  }

  promoteUser(user: SearchUser): void {
    this.adminService.setRedacteurPrincipal(user.id_role).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('admin.redacteursPrincipaux.messages.added', { name: user.nom_complet }),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.closeAddDialog();
        this.loadRedacteurs();
      },
      error: (err) => {
        this.snackBar.open(
          err.error?.error || 'Erreur',
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  askRemove(user: RedacteurPrincipal): void {
    this.confirmRemoveUser.set(user);
  }

  cancelRemove(): void {
    this.confirmRemoveUser.set(null);
  }

  confirmRemove(): void {
    const user = this.confirmRemoveUser();
    if (!user) return;

    this.adminService.removeRedacteurPrincipal(user.id).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('admin.redacteursPrincipaux.messages.removed', { name: user.nom }),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.confirmRemoveUser.set(null);
        this.loadRedacteurs();
      },
      error: (err) => {
        this.snackBar.open(
          err.error?.error || 'Erreur',
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }
}
