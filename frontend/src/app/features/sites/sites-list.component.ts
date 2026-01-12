/**
 * Composant pour la page "Mes sites".
 * Affiche les sites auxquels l'utilisateur a acces et permet de demander l'acces a d'autres sites.
 */
import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AdminService } from '../../core/services/admin.service';
import { ValidationService } from '../../core/services/validation.service';
import { AuthService } from '../../core/services/auth.service';
import { AdminSite } from '../../core/models/admin.model';
import { ValidationRequestListItem } from '../../core/models/notification.model';
import { AccessRequestDialogComponent, AccessRequestDialogData } from '../../shared/components/access-request-dialog/access-request-dialog.component';

interface SiteUserRelation {
  id_role: number;
  email?: string;
  nom_role?: string;
  prenom_role?: string;
  referent?: boolean;
}

// Utiliser Omit pour exclure 'users' de AdminSite et le redéfinir avec notre type
interface SiteWithUsers extends Omit<AdminSite, 'users'> {
  users?: SiteUserRelation[];
}

interface SiteWithAccess extends SiteWithUsers {
  accessStatus: 'granted' | 'pending' | 'rejected' | 'none';
  isReferent: boolean;
}

@Component({
  selector: 'app-sites-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatTableModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatTooltipModule,
    MatDialogModule,
    TranslateModule
  ],
  templateUrl: './sites-list.component.html',
  styleUrl: './sites-list.component.scss'
})
export class SitesListComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly validationService = inject(ValidationService);
  private readonly authService = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly dialog = inject(MatDialog);

  // Donnees
  readonly allSites = signal<SiteWithAccess[]>([]);
  readonly myRequests = signal<ValidationRequestListItem[]>([]);
  readonly loading = signal(false);
  readonly searchTerm = signal('');

  // Colonnes du tableau
  readonly mySitesColumns = ['name', 'type', 'surface', 'organisme', 'status'];
  readonly otherSitesColumns = ['name', 'type', 'surface', 'organisme', 'actions'];

  // Sites filtres
  readonly mySites = computed(() => {
    return this.allSites().filter(s => s.accessStatus === 'granted');
  });

  readonly otherSites = computed(() => {
    const search = this.searchTerm().toLowerCase();
    return this.allSites()
      .filter(s => s.accessStatus !== 'granted')
      .filter(s => !search || s.nom_site.toLowerCase().includes(search));
  });

  ngOnInit(): void {
    this.loadData();
  }

  /**
   * Charge les donnees (sites et demandes en cours).
   */
  loadData(): void {
    this.loading.set(true);

    // Charger les sites
    this.adminService.getSites({ page_size: 100 }).subscribe({
      next: (response) => {
        // Charger aussi les demandes de l'utilisateur
        this.validationService.getMyRequests().subscribe({
          next: (requests) => {
            this.myRequests.set(requests.filter(r => r.request_type === 'site_access'));

            // Enrichir les sites avec le statut d'acces
            const sitesWithAccess = this.enrichSitesWithAccess(response.results as SiteWithUsers[], requests);
            this.allSites.set(sitesWithAccess);
            this.loading.set(false);
          },
          error: () => {
            // Si erreur sur les demandes, afficher quand meme les sites
            const sitesWithAccess = this.enrichSitesWithAccess(response.results as SiteWithUsers[], []);
            this.allSites.set(sitesWithAccess);
            this.loading.set(false);
          }
        });
      },
      error: (error) => {
        console.error('Erreur chargement sites:', error);
        this.snackBar.open(
          this.translate.instant('common.messages.error'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loading.set(false);
      }
    });
  }

  /**
   * Enrichit les sites avec les informations d'acces.
   * Note: Pour l'instant, on determine l'acces via les demandes approuvees
   * et les informations de l'utilisateur retournees par l'API.
   */
  private enrichSitesWithAccess(sites: SiteWithUsers[], requests: ValidationRequestListItem[]): SiteWithAccess[] {
    // Recuperer les sites auxquels l'utilisateur a acces via les demandes approuvees
    const approvedSiteNames = requests
      .filter(r => r.request_type === 'site_access' && r.status === 'approved')
      .map(r => r.target_name);

    return sites.map(site => {
      // Verifier s'il y a une demande en cours pour ce site
      const pendingRequest = requests.find(
        r => r.request_type === 'site_access' &&
             r.status === 'pending' &&
             r.target_name === site.nom_site
      );
      const rejectedRequest = requests.find(
        r => r.request_type === 'site_access' &&
             r.status === 'rejected' &&
             r.target_name === site.nom_site
      );
      const approvedRequest = requests.find(
        r => r.request_type === 'site_access' &&
             r.status === 'approved' &&
             r.target_name === site.nom_site
      );

      // Verifier si l'utilisateur est lie au site via les users du site
      const currentUser = this.authService.currentUser();
      const isUserLinked = site.users?.some(u => u.id_role === currentUser?.id);
      const userLink = site.users?.find(u => u.id_role === currentUser?.id);

      let accessStatus: 'granted' | 'pending' | 'rejected' | 'none' = 'none';
      if (isUserLinked || approvedRequest) {
        accessStatus = 'granted';
      } else if (pendingRequest) {
        accessStatus = 'pending';
      } else if (rejectedRequest) {
        accessStatus = 'rejected';
      }

      return {
        ...site,
        accessStatus,
        isReferent: userLink?.referent || false
      };
    });
  }

  /**
   * Ouvre le dialog de demande d'acces.
   */
  openAccessRequestDialog(site: SiteWithAccess): void {
    const dialogRef = this.dialog.open(AccessRequestDialogComponent, {
      width: '500px',
      data: {
        type: 'site',
        targetId: site.id_site,
        targetName: site.nom_site
      } as AccessRequestDialogData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.loadData();
      }
    });
  }

  /**
   * Recherche de sites.
   */
  onSearch(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchTerm.set(input.value);
  }

  /**
   * Obtient la classe CSS du statut.
   */
  getStatusClass(status: string): string {
    const classes: Record<string, string> = {
      'granted': 'status-success',
      'pending': 'status-warning',
      'rejected': 'status-error',
      'none': 'status-neutre'
    };
    return classes[status] || 'status-neutre';
  }

  /**
   * Formate la surface.
   */
  formatSurface(surface: number | null | undefined): string {
    if (!surface) return '-';
    return `${surface.toLocaleString('fr-FR')} ha`;
  }
}
