import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { AuthService } from '../../core/services/auth.service';
import { AdminService } from '../../core/services/admin.service';
import { AdminPlan, PlanStatut, AdminOrganisme } from '../../core/models/admin.model';
import { PlanFormModalComponent } from '../../shared/components/modals/plan-form-modal/plan-form-modal.component';

// Interface for linked site display
interface DisplaySiteLie {
  id: number;
  nom: string;
  type?: string;
  rang?: number;
}

// Interface for linked referent display
interface DisplayReferent {
  id: number;
  nom: string;
  email: string;
}

// Interface for display (mapping from API model)
interface DisplayPlan {
  id: number;
  nom: string;
  statut: PlanStatut;
  statutLabel: string;
  version?: string;
  periodeDebut?: number;
  periodeFin?: number;
  periode: string;
  gestionPartagee: boolean;
  ct88: boolean;
  risqueIncendie: boolean;
  evaluationLabel?: string;
  redacteurNom?: string;
  commentaire?: string;
  dateAjout?: Date;
  dateMaj?: Date;
  sites: DisplaySiteLie[];
  referents: DisplayReferent[];
}

interface DisplayOrganisme {
  id: number;
  nom: string;
}

@Component({
  selector: 'app-admin-plans',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    MatDialogModule,
    MatSnackBarModule,
    MatProgressSpinnerModule,
    MatTooltipModule
  ],
  templateUrl: './admin-plans.component.html',
  styleUrl: './admin-plans.component.scss'
})
export class AdminPlansComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  readonly currentUser = this.authService.currentUser;
  readonly isSuperAdmin = this.authService.isSuperAdmin;

  // Filter state
  searchQuery = '';
  filterStatut: PlanStatut | '' = '';
  filterOrganisme = '';
  isLoading = signal(false);

  plans = signal<DisplayPlan[]>([]);
  organismes = signal<DisplayOrganisme[]>([]);
  filteredPlans = signal<DisplayPlan[]>([]);

  // Statistics
  totalPlans = computed(() => this.filteredPlans().length);
  plansValides = computed(() => this.filteredPlans().filter(p => p.statut === 'valide').length);
  plansBrouillon = computed(() => this.filteredPlans().filter(p => p.statut === 'draft').length);
  plansArchives = computed(() => this.filteredPlans().filter(p => p.statut === 'archive').length);

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.isLoading.set(true);

    // Load organismes for filter dropdown
    this.adminService.getOrganismes().subscribe({
      next: (response) => {
        this.organismes.set(response.results.map(org => ({
          id: org.id_organisme,
          nom: org.nom_organisme
        })));
      }
    });

    // Load plans
    this.loadPlans();
  }

  loadPlans(): void {
    this.isLoading.set(true);

    // For non-super admin, filter by their organisme
    const currentOrgId = this.currentUser()?.organisme?.id;
    const organismeFilter = !this.isSuperAdmin() && currentOrgId ? currentOrgId : undefined;

    this.adminService.getPlans({
      search: this.searchQuery || undefined,
      statut: this.filterStatut || undefined,
      organisme: organismeFilter
    }).subscribe({
      next: (response) => {
        const mapped = response.results.map(plan => this.mapPlan(plan));
        this.plans.set(mapped);
        this.applyFilters();
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
        this.isLoading.set(false);
      }
    });
  }

  private mapPlan(plan: AdminPlan): DisplayPlan {
    const statutLabels: Record<PlanStatut, string> = {
      'draft': 'Brouillon',
      'valide': 'Valide',
      'archive': 'Archive'
    };

    const periode = plan.annee_debut && plan.annee_fin
      ? `${plan.annee_debut} - ${plan.annee_fin}`
      : plan.annee_debut
        ? `Depuis ${plan.annee_debut}`
        : 'Non definie';

    return {
      id: plan.id_pg,
      nom: plan.nom,
      statut: plan.statut,
      statutLabel: statutLabels[plan.statut] || plan.statut,
      version: plan.version,
      periodeDebut: plan.annee_debut,
      periodeFin: plan.annee_fin,
      periode,
      gestionPartagee: plan.gestion_partagee,
      ct88: plan.ct88,
      risqueIncendie: plan.risque_incendie,
      evaluationLabel: plan.evaluation_label,
      redacteurNom: plan.redacteur_nom,
      commentaire: plan.commentaire,
      dateAjout: plan.date_ajout ? new Date(plan.date_ajout) : undefined,
      dateMaj: plan.date_maj ? new Date(plan.date_maj) : undefined,
      sites: (plan.sites || []).map(s => ({
        id: s.id_site,
        nom: s.nom_site,
        type: s.type_site_label,
        rang: s.rang
      })),
      referents: (plan.referents || []).map(r => ({
        id: r.id_role,
        nom: r.nom_complet || `${r.prenom_role || ''} ${r.nom_role || ''}`.trim() || r.email,
        email: r.email
      }))
    };
  }

  filterPlans(): void {
    this.applyFilters();
  }

  onSearchChange(): void {
    // Reload from API when search changes
    this.loadPlans();
  }

  private applyFilters(): void {
    let result = this.plans();

    // Filter by search query (already applied by API, but add local filtering for other fields)
    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      result = result.filter(plan =>
        plan.nom.toLowerCase().includes(query) ||
        plan.redacteurNom?.toLowerCase().includes(query) ||
        plan.sites.some(s => s.nom.toLowerCase().includes(query))
      );
    }

    // Filter by status
    if (this.filterStatut) {
      result = result.filter(plan => plan.statut === this.filterStatut);
    }

    this.filteredPlans.set(result);
  }

  // Actions
  openAddPlanModal(): void {
    const dialogRef = this.dialog.open(PlanFormModalComponent, {
      width: '1100px',
      maxWidth: '95vw',
      maxHeight: '90vh'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.success) {
        this.snackBar.open('Plan de gestion cree avec succes', 'Fermer', { duration: 3000 });
        this.loadPlans();
      }
    });
  }

  editPlan(plan: DisplayPlan): void {
    // First get the full plan data
    this.adminService.getPlan(plan.id).subscribe({
      next: (fullPlan) => {
        const dialogRef = this.dialog.open(PlanFormModalComponent, {
          width: '1100px',
          maxWidth: '95vw',
          maxHeight: '90vh',
          data: { plan: fullPlan }
        });

        dialogRef.afterClosed().subscribe(result => {
          if (result?.success) {
            this.snackBar.open('Plan de gestion modifie avec succes', 'Fermer', { duration: 3000 });
            this.loadPlans();
          }
        });
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
      }
    });
  }

  viewPlan(plan: DisplayPlan): void {
    // Navigate to plan detail page
    window.location.href = `/plans/${plan.id}`;
  }

  validerPlan(plan: DisplayPlan): void {
    if (plan.statut !== 'draft') {
      this.snackBar.open('Seuls les plans en brouillon peuvent etre valides', 'OK', { duration: 3000 });
      return;
    }

    this.adminService.updatePlanStatus(plan.id, 'valide').subscribe({
      next: () => {
        this.snackBar.open('Plan valide avec succes', 'Fermer', { duration: 3000 });
        this.loadPlans();
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
      }
    });
  }

  archiverPlan(plan: DisplayPlan): void {
    if (plan.statut === 'archive') {
      this.snackBar.open('Ce plan est deja archive', 'OK', { duration: 3000 });
      return;
    }

    this.adminService.updatePlanStatus(plan.id, 'archive').subscribe({
      next: () => {
        this.snackBar.open('Plan archive avec succes', 'Fermer', { duration: 3000 });
        this.loadPlans();
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
      }
    });
  }

  restaurerPlan(plan: DisplayPlan): void {
    if (plan.statut !== 'archive') {
      return;
    }

    this.adminService.updatePlanStatus(plan.id, 'draft').subscribe({
      next: () => {
        this.snackBar.open('Plan restaure en brouillon', 'Fermer', { duration: 3000 });
        this.loadPlans();
      },
      error: (error: Error) => {
        this.snackBar.open(error.message, 'Fermer', { duration: 5000 });
      }
    });
  }

  // Helper methods for display
  getStatutClass(statut: PlanStatut): string {
    const classes: Record<PlanStatut, string> = {
      'draft': 'statut-draft',
      'valide': 'statut-valide',
      'archive': 'statut-archive'
    };
    return classes[statut] || '';
  }

  getOtherSitesNames(sites: DisplaySiteLie[]): string {
    return sites.slice(2).map(s => s.nom).join(', ');
  }

  getOtherReferentsNames(referents: DisplayReferent[]): string {
    return referents.slice(2).map(r => r.nom).join(', ');
  }

  formatDate(date?: Date): string {
    if (!date) return '-';
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  }
}
