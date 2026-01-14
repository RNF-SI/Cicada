import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import { AdminOrganisme } from '../../core/models/admin.model';
import {
  OrganismeFormModalComponent,
  LinkUserOrganismeModalComponent,
  LinkSiteOrganismeModalComponent,
  SiteFormModalComponent
} from '../../shared/components/modals';

// Interface for display (mapping from API model)
interface DisplayOrganisme {
  id: number;
  uuid?: string;
  nom: string;
  adresse?: string;
  codePostal?: string;
  ville?: string;
  telephone?: string;
  email?: string;
  url?: string;
  parentId?: number;
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
    MatProgressSpinnerModule,
    MatTooltipModule,
    TranslateModule
  ],
  templateUrl: './admin-organismes.component.html',
  styleUrl: './admin-organismes.component.scss'
})
export class AdminOrganismesComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

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
    const found = this.organismes().find(org => org.id === user.organisme!.id_organisme);
    if (found) return found;

    // Fallback: create from user data
    return {
      id: user.organisme.id_organisme,
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
        this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
        this.isLoading.set(false);
      }
    });
  }

  private mapOrganisme(org: AdminOrganisme): DisplayOrganisme {
    return {
      id: org.id_organisme,
      uuid: org.uuid_organisme,
      nom: org.nom_organisme,
      adresse: org.adresse_organisme,
      codePostal: org.cp_organisme,
      ville: org.ville_organisme,
      telephone: org.tel_organisme,
      email: org.email_organisme,
      url: org.url_organisme,
      parentId: org.id_parent,
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
          id_organisme: o.id,
          nom_organisme: o.nom
        }))
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.snackBar.open(this.translate.instant('admin.organismes.messages.created'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadOrganismes();
      }
    });
  }

  editOrganisme(org: DisplayOrganisme): void {
    const dialogRef = this.dialog.open(OrganismeFormModalComponent, {
      width: '600px',
      data: {
        organisme: {
          id_organisme: org.id,
          nom_organisme: org.nom,
          adresse_organisme: org.adresse,
          cp_organisme: org.codePostal,
          ville_organisme: org.ville,
          tel_organisme: org.telephone,
          email_organisme: org.email,
          url_organisme: org.url,
          id_parent: org.parentId
        },
        parentOrganismes: this.organismes().map(o => ({
          id_organisme: o.id,
          nom_organisme: o.nom
        }))
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.snackBar.open(this.translate.instant('admin.organismes.messages.updated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadOrganismes();
      }
    });
  }

  openAddUserModal(org: DisplayOrganisme): void {
    const dialogRef = this.dialog.open(LinkUserOrganismeModalComponent, {
      width: '600px',
      data: {
        organisme: {
          id_organisme: org.id,
          uuid_organisme: org.uuid,
          nom_organisme: org.nom,
          ville_organisme: org.ville
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        this.snackBar.open(this.translate.instant('admin.organismes.messages.userLinked'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadOrganismes();
      }
    });
  }

  openAddSiteModal(org: DisplayOrganisme): void {
    const dialogRef = this.dialog.open(LinkSiteOrganismeModalComponent, {
      width: '600px',
      data: {
        organisme: {
          id_organisme: org.id,
          nom_organisme: org.nom,
          ville_organisme: org.ville
        }
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        this.snackBar.open(this.translate.instant('admin.organismes.messages.siteLinked'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadOrganismes();
      }
    });
  }

  /**
   * Open site creation modal (for admin_og)
   * The site will be automatically linked to their organisme
   */
  openCreateSiteModal(org: DisplayOrganisme): void {
    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '600px',
      data: {
        organismeId: org.id,
        principal: true // New site is principal by default for admin_og
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.snackBar.open(this.translate.instant('admin.organismes.messages.siteCreated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        this.loadOrganismes();
      }
    });
  }

  viewOrganismeDetails(org: DisplayOrganisme): void {
    // For now, just show edit modal - detail page to be implemented later
    this.editOrganisme(org);
  }
}
