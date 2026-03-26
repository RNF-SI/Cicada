import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subject } from 'rxjs';
import { debounceTime } from 'rxjs/operators';
import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import { AdminOrganisme } from '../../core/models/admin.model';
import { PaginationComponent } from '../../shared/components/pagination/pagination.component';
import {
  OrganismeFormModalComponent,
  LinkUserOrganismeModalComponent,
  LinkSiteOrganismeModalComponent,
  SiteFormModalComponent
} from '../../shared/components/modals';

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
    TranslateModule,
    PaginationComponent
  ],
  templateUrl: './admin-organismes.component.html',
  styleUrl: './admin-organismes.component.scss'
})
export class AdminOrganismesComponent implements OnInit, OnDestroy {
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;

  searchQuery = '';
  isLoading = signal(false);

  // Pagination state
  currentPage = signal(1);
  totalItems = signal(0);
  readonly pageSize = 20;

  organismes = signal<DisplayOrganisme[]>([]);

  private searchSubject = new Subject<void>();
  private destroy$ = new Subject<void>();

  currentOrganisme = computed(() => {
    const user = this.currentUser();
    if (!user?.organisme) return null;

    const found = this.organismes().find(org => org.id === user.organisme!.id_organisme);
    if (found) return found;

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
    this.searchSubject.pipe(
      debounceTime(300),
    ).subscribe(() => {
      this.currentPage.set(1);
      this.loadOrganismes();
    });

    this.loadOrganismes();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadOrganismes(): void {
    this.isLoading.set(true);
    this.adminService.getOrganismes({
      search: this.searchQuery || undefined,
      page: this.currentPage(),
      page_size: this.pageSize
    }).subscribe({
      next: (response: any) => {
        const mapped = response.results.map((org: AdminOrganisme) => this.mapOrganisme(org));
        this.organismes.set(mapped);
        this.totalItems.set(response.pagination?.count ?? response.count ?? 0);
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, this.translate.instant('common.actions.close'), { duration: 5000 });
        this.isLoading.set(false);
      }
    });
  }

  onSearchChange(): void {
    this.searchSubject.next();
  }

  onPageChange(page: number): void {
    this.currentPage.set(page);
    this.loadOrganismes();
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
      nbPlans: 0,
      isActive: true
    };
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

  openCreateSiteModal(org: DisplayOrganisme): void {
    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '1300px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        organismeId: org.id,
        principal: true
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.site) {
        if (result.validationPending) {
          this.snackBar.open(
            result.message || this.translate.instant('sites.createSite.pendingValidation'),
            this.translate.instant('common.actions.close'),
            { duration: 8000 }
          );
        } else {
          this.snackBar.open(this.translate.instant('admin.organismes.messages.siteCreated'), this.translate.instant('common.actions.close'), { duration: 3000 });
        }
        this.loadOrganismes();
      }
    });
  }

  viewOrganismeDetails(org: DisplayOrganisme): void {
    this.editOrganisme(org);
  }
}
