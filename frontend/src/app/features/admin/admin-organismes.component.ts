import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import { AdminOrganisme } from '../../core/models/admin.model';
import {
  OrganismeFormModalComponent,
  LinkUserOrganismeModalComponent,
  LinkSiteOrganismeModalComponent
} from '../../shared/components/modals';

// Interface for display (mapping from API model)
interface DisplayOrganisme {
  id: number;
  nom: string;
  adresse?: string;
  codePostal?: string;
  ville?: string;
  telephone?: string;
  email?: string;
  nbUtilisateurs: number;
  nbSites: number;
  nbPlans: number;
  isActive: boolean;
}

@Component({
  selector: 'app-admin-organismes',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './admin-organismes.component.html',
  styleUrl: './admin-organismes.component.scss'
})
export class AdminOrganismesComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;

  searchQuery = '';
  isLoading = signal(false);

  organismes = signal<DisplayOrganisme[]>([]);
  filteredOrganismes = signal<DisplayOrganisme[]>([]);

  currentOrganisme = computed(() => {
    const user = this.currentUser();
    if (!user?.organisme) return null;

    // Find organisme in list or create from user data
    const found = this.organismes().find(org => org.id === user.organisme!.id);
    if (found) return found;

    // Fallback: create from user data
    return {
      id: user.organisme.id,
      nom: user.organisme.nom_organisme,
      adresse: user.organisme.adresse_organisme,
      codePostal: user.organisme.cp_organisme,
      ville: user.organisme.ville_organisme,
      telephone: user.organisme.tel_organisme,
      email: user.organisme.email_organisme,
      nbUtilisateurs: 0,
      nbSites: 0,
      nbPlans: 0,
      isActive: true
    } as DisplayOrganisme;
  });

  ngOnInit(): void {
    this.loadOrganismes();
  }

  loadOrganismes(): void {
    this.isLoading.set(true);
    this.adminService.getOrganismes({ search: this.searchQuery || undefined }).subscribe({
      next: (response) => {
        const mapped = response.results.map(org => this.mapOrganisme(org));
        this.organismes.set(mapped);
        this.filteredOrganismes.set(mapped);
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
        this.isLoading.set(false);
      }
    });
  }

  private mapOrganisme(org: AdminOrganisme): DisplayOrganisme {
    return {
      id: org.id_organisme,
      nom: org.nom_organisme,
      adresse: org.adresse_organisme,
      codePostal: org.cp_organisme,
      ville: org.ville_organisme,
      telephone: org.tel_organisme,
      email: org.email_organisme,
      nbUtilisateurs: org.users_count || 0,
      nbSites: org.sites_count || 0,
      nbPlans: 0, // Will be added later
      isActive: true
    };
  }

  filterOrganismes(): void {
    if (!this.searchQuery) {
      this.filteredOrganismes.set(this.organismes());
      return;
    }

    const query = this.searchQuery.toLowerCase();
    const result = this.organismes().filter(org =>
      org.nom.toLowerCase().includes(query) ||
      org.ville?.toLowerCase().includes(query)
    );
    this.filteredOrganismes.set(result);
  }

  openAddOrganismeModal(): void {
    const dialogRef = this.dialog.open(OrganismeFormModalComponent, {
      width: '600px',
      data: {
        parentOrganismes: this.organismes().map(o => ({
          id: o.id,
          nom_organisme: o.nom
        }))
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.snackBar.open('Organisme cree avec succes', 'Fermer', { duration: 3000 });
        this.loadOrganismes();
      }
    });
  }

  editOrganisme(org: DisplayOrganisme): void {
    const dialogRef = this.dialog.open(OrganismeFormModalComponent, {
      width: '600px',
      data: {
        organisme: {
          id: org.id,
          nom_organisme: org.nom,
          adresse_organisme: org.adresse,
          cp_organisme: org.codePostal,
          ville_organisme: org.ville,
          tel_organisme: org.telephone,
          email_organisme: org.email
        },
        parentOrganismes: this.organismes().map(o => ({
          id: o.id,
          nom_organisme: o.nom
        }))
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.snackBar.open('Organisme modifie avec succes', 'Fermer', { duration: 3000 });
        this.loadOrganismes();
      }
    });
  }

  openAddUserModal(org: DisplayOrganisme): void {
    const dialogRef = this.dialog.open(LinkUserOrganismeModalComponent, {
      width: '500px',
      data: {
        organisme: {
          id: org.id,
          nom_organisme: org.nom
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        this.snackBar.open('Utilisateur associe a l\'organisme', 'Fermer', { duration: 3000 });
        this.loadOrganismes();
      }
    });
  }

  openAddSiteModal(org: DisplayOrganisme): void {
    const dialogRef = this.dialog.open(LinkSiteOrganismeModalComponent, {
      width: '550px',
      data: {
        organisme: {
          id: org.id,
          nom_organisme: org.nom,
          ville_organisme: org.ville
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        this.snackBar.open('Site associe a l\'organisme', 'Fermer', { duration: 3000 });
        this.loadOrganismes();
      }
    });
  }

  viewOrganismeDetails(org: DisplayOrganisme): void {
    // For now, just show edit modal - detail page to be implemented later
    this.editOrganisme(org);
  }
}
