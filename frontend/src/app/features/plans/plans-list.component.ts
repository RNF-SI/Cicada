/**
 * Composant pour la liste des plans de gestion.
 * Affiche les plans auxquels l'utilisateur a accès et permet de demander l'accès à d'autres plans.
 */
import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatMenuModule } from '@angular/material/menu';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { PlanGaugeComponent, GaugeStatus } from '../../shared/components/plan-gauge/plan-gauge.component';
import { AdminService } from '../../core/services/admin.service';
import { ValidationService } from '../../core/services/validation.service';
import { AuthService } from '../../core/services/auth.service';
import { AdminPlan } from '../../core/models/admin.model';
import { ValidationRequestListItem } from '../../core/models/notification.model';
import { AccessRequestDialogComponent, AccessRequestDialogData } from '../../shared/components/access-request-dialog/access-request-dialog.component';

interface PlanWithAccess extends AdminPlan {
  accessStatus: 'granted' | 'pending' | 'rejected' | 'none';
  isReferent: boolean;
  gaugeStatus: GaugeStatus;
}

@Component({
  selector: 'app-plans-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatMenuModule,
    MatButtonModule,
    MatCardModule,
    MatTableModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatDialogModule,
    TranslateModule,
    HeaderComponent,
    PlanGaugeComponent
  ],
  templateUrl: './plans-list.component.html',
  styleUrl: './plans-list.component.scss'
})
export class PlansListComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly translate = inject(TranslateService);
  private readonly adminService = inject(AdminService);
  private readonly validationService = inject(ValidationService);
  private readonly authService = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);

  // Données
  readonly allPlans = signal<PlanWithAccess[]>([]);
  readonly myRequests = signal<ValidationRequestListItem[]>([]);
  readonly loading = signal(false);

  // Tab state pour "Mes plans"
  activeTab = signal<'actifs' | 'inactifs'>('actifs');

  // Search pour "Demander l'accès"
  searchQuery = signal('');

  // Colonnes des tableaux
  readonly myPlansColumns = ['name', 'period', 'status', 'actions'];
  readonly otherPlansColumns = ['name', 'period', 'organisme', 'actions'];

  // Plans filtrés
  readonly myPlans = computed(() => {
    const tab = this.activeTab();
    return this.allPlans()
      .filter(p => p.accessStatus === 'granted')
      .filter(p => {
        if (tab === 'actifs') {
          return p.statut !== 'archive';
        } else {
          return p.statut === 'archive';
        }
      });
  });

  readonly otherPlans = computed(() => {
    const search = this.searchQuery().toLowerCase();
    return this.allPlans()
      .filter(p => p.accessStatus !== 'granted')
      .filter(p => !search || p.nom.toLowerCase().includes(search));
  });

  // Pagination pour "Mes plans"
  currentPage = signal(1);
  totalPages = signal(1);
  itemsPerPage = 10;
  showPagination = computed(() => this.totalPages() > 1);

  paginationPages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: (number | string)[] = [];

    if (total <= 7) {
      for (let i = 1; i <= total; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);
      if (current > 3) {
        pages.push('...');
      }
      for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
        if (!pages.includes(i)) {
          pages.push(i);
        }
      }
      if (current < total - 2) {
        pages.push('...');
      }
      if (!pages.includes(total)) {
        pages.push(total);
      }
    }

    return pages;
  });

  ngOnInit(): void {
    this.loadData();
  }

  /**
   * Charge les données (plans et demandes en cours).
   */
  loadData(): void {
    this.loading.set(true);

    // Charger les plans
    this.adminService.getPlans().subscribe({
      next: (response) => {
        // Charger aussi les demandes de l'utilisateur
        this.validationService.getMyRequests().subscribe({
          next: (requests) => {
            this.myRequests.set(requests.filter(r => r.request_type === 'plan_access'));

            // Enrichir les plans avec le statut d'accès
            const plansWithAccess = this.enrichPlansWithAccess(response.results, requests);
            this.allPlans.set(plansWithAccess);
            this.loading.set(false);
          },
          error: () => {
            // Si erreur sur les demandes, afficher quand même les plans
            const plansWithAccess = this.enrichPlansWithAccess(response.results, []);
            this.allPlans.set(plansWithAccess);
            this.loading.set(false);
          }
        });
      },
      error: (error) => {
        console.error('Erreur chargement plans:', error);
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
   * Enrichit les plans avec les informations d'accès.
   */
  private enrichPlansWithAccess(plans: AdminPlan[], requests: ValidationRequestListItem[]): PlanWithAccess[] {
    const currentUser = this.authService.currentUser();

    return plans.map(plan => {
      // Vérifier s'il y a une demande en cours pour ce plan
      const pendingRequest = requests.find(
        r => r.request_type === 'plan_access' &&
             r.status === 'pending' &&
             r.target_name === plan.nom
      );
      const rejectedRequest = requests.find(
        r => r.request_type === 'plan_access' &&
             r.status === 'rejected' &&
             r.target_name === plan.nom
      );
      const approvedRequest = requests.find(
        r => r.request_type === 'plan_access' &&
             r.status === 'approved' &&
             r.target_name === plan.nom
      );

      // Vérifier si l'utilisateur est référent du plan
      const isReferent = plan.referents?.some(r => r.id_role === currentUser?.id) || false;

      let accessStatus: 'granted' | 'pending' | 'rejected' | 'none' = 'none';
      if (isReferent || approvedRequest) {
        accessStatus = 'granted';
      } else if (pendingRequest) {
        accessStatus = 'pending';
      } else if (rejectedRequest) {
        accessStatus = 'rejected';
      }

      // Calculer le statut de la jauge
      const gaugeStatus = this.calculateGaugeStatus(plan);

      return {
        ...plan,
        accessStatus,
        isReferent,
        gaugeStatus
      };
    });
  }

  /**
   * Calcule le statut de la jauge en fonction des dates du plan.
   */
  private calculateGaugeStatus(plan: AdminPlan): GaugeStatus {
    if (!plan.annee_debut || !plan.annee_fin) {
      return 'not-started';
    }

    const currentYear = new Date().getFullYear();
    const startYear = plan.annee_debut;
    const endYear = plan.annee_fin;

    if (currentYear < startYear) {
      return 'not-started';
    } else if (currentYear > endYear) {
      return 'exceeded';
    } else {
      const progress = (currentYear - startYear) / (endYear - startYear);
      if (progress < 0.5) {
        return 'in-progress';
      } else {
        return 'completed';
      }
    }
  }

  /**
   * Ouvre le dialog de demande d'accès.
   */
  openAccessRequestDialog(plan: PlanWithAccess): void {
    const dialogRef = this.dialog.open(AccessRequestDialogComponent, {
      width: '500px',
      data: {
        type: 'plan',
        targetId: plan.id_pg,
        targetName: plan.nom
      } as AccessRequestDialogData
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.loadData();
      }
    });
  }

  /**
   * Tabs pour "Mes plans".
   */
  setTab(tab: 'actifs' | 'inactifs'): void {
    this.activeTab.set(tab);
  }

  /**
   * Pagination.
   */
  goToPage(page: number | string): void {
    if (typeof page === 'number' && page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  previousPage(): void {
    if (this.currentPage() > 1) {
      this.currentPage.update(p => p - 1);
    }
  }

  nextPage(): void {
    if (this.currentPage() < this.totalPages()) {
      this.currentPage.update(p => p + 1);
    }
  }

  /**
   * Labels et classes CSS pour les statuts.
   */
  getStatutLabel(statut: string): string {
    const keys: Record<string, string> = {
      'draft': 'plans.status.draft',
      'valide': 'plans.status.valide',
      'archive': 'plans.status.archive'
    };
    const key = keys[statut];
    return key ? this.translate.instant(key) : statut;
  }

  getStatutClass(statut: string): string {
    const classes: Record<string, string> = {
      'draft': 'status-warning',
      'valide': 'status-success',
      'archive': 'status-neutre'
    };
    return classes[statut] || '';
  }

  /**
   * Recherche de plans.
   */
  onSearch(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.searchQuery.set(input.value);
  }

  /**
   * Actions sur les plans.
   */
  editStatus(plan: PlanWithAccess): void {
    console.log('Edit status for plan:', plan.id_pg);
  }

  viewPlan(plan: PlanWithAccess): void {
    this.router.navigate(['/plans', plan.id_pg]);
  }

  followPlan(plan: PlanWithAccess): void {
    console.log('Follow plan:', plan.id_pg);
  }

  /**
   * Formate la période du plan.
   */
  formatPeriod(plan: PlanWithAccess): string {
    if (plan.annee_debut && plan.annee_fin) {
      return `${plan.annee_debut}-${plan.annee_fin}`;
    } else if (plan.annee_debut) {
      return `${plan.annee_debut}`;
    }
    return '-';
  }

  /**
   * Récupère le premier site du plan (pour affichage).
   */
  getFirstSite(plan: PlanWithAccess): string {
    if (plan.sites && plan.sites.length > 0) {
      return plan.sites[0].nom_site;
    }
    return '-';
  }
}
