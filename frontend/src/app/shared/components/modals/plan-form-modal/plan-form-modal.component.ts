import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { AdminService } from '../../../../core/services/admin.service';
import {
  AdminPlan,
  PlanCreatePayload,
  PlanStatut,
  AdminSite,
  AdminUser
} from '../../../../core/models/admin.model';

export interface PlanFormModalData {
  plan?: AdminPlan; // If provided, edit mode
}

interface NomenclatureItem {
  id_nomenclature: number;
  cd_nomenclature: string;
  label: string;
}

interface SelectableSite {
  id: number;
  nom: string;
  type?: string;
  selected: boolean;
}

interface SelectableUser {
  id: number;
  nom: string;
  email: string;
  role?: string;
  selected: boolean;
}

@Component({
  selector: 'app-plan-form-modal',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatIconModule,
    MatAutocompleteModule
  ],
  templateUrl: './plan-form-modal.component.html',
  styleUrl: './plan-form-modal.component.scss'
})
export class PlanFormModalComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly adminService = inject(AdminService);
  private readonly dialogRef = inject(MatDialogRef<PlanFormModalComponent>);
  readonly data = inject<PlanFormModalData>(MAT_DIALOG_DATA, { optional: true });

  form!: FormGroup;
  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);

  // Nomenclatures
  evaluationTypes = signal<NomenclatureItem[]>([]);
  redacteurTypes = signal<NomenclatureItem[]>([]);

  // Available sites and users
  availableSites = signal<SelectableSite[]>([]);
  availableUsers = signal<SelectableUser[]>([]);

  // Selected items
  selectedSiteIds = signal<number[]>([]);
  selectedReferentIds = signal<number[]>([]);

  // Search queries as signals for reactivity
  siteSearchQuery = '';
  userSearchQuery = '';
  private siteSearchSignal = signal('');
  private userSearchSignal = signal('');

  // Filtered lists (computed)
  filteredSites = computed(() => {
    const sites = this.availableSites();
    const query = this.siteSearchSignal().toLowerCase().trim();
    if (!query) {
      return sites;
    }
    return sites.filter(site =>
      site.nom.toLowerCase().includes(query) ||
      (site.type && site.type.toLowerCase().includes(query))
    );
  });

  filteredUsers = computed(() => {
    const users = this.availableUsers();
    const query = this.userSearchSignal().toLowerCase().trim();
    if (!query) {
      return users;
    }
    return users.filter(user =>
      user.nom.toLowerCase().includes(query) ||
      user.email.toLowerCase().includes(query) ||
      (user.role && user.role.toLowerCase().includes(query))
    );
  });

  // Current year for validation
  currentYear = new Date().getFullYear();

  get isEditMode(): boolean {
    return !!this.data?.plan;
  }

  get modalTitle(): string {
    return this.isEditMode ? 'Modifier le plan de gestion' : 'Nouveau plan de gestion';
  }

  ngOnInit(): void {
    this.initForm();
    this.loadData();
  }

  private initForm(): void {
    const plan = this.data?.plan;

    this.form = this.fb.group({
      nom: [plan?.nom || '', [Validators.required, Validators.maxLength(255)]],
      statut: [plan?.statut || 'draft'],
      version: [plan?.version || '1.0', Validators.maxLength(20)],
      annee_debut: [plan?.annee_debut || this.currentYear, [Validators.min(1900), Validators.max(2100)]],
      annee_fin: [plan?.annee_fin || this.currentYear + 10, [Validators.min(1900), Validators.max(2100)]],
      gestion_partagee: [plan?.gestion_partagee || false],
      ct88: [plan?.ct88 || false],
      risque_incendie: [plan?.risque_incendie || false],
      id_evaluation: [plan?.id_evaluation || null],
      id_redacteur_type: [plan?.id_redacteur_type || null],
      redacteur_nom: [plan?.redacteur_nom || '', Validators.maxLength(255)],
      commentaire: [plan?.commentaire || '']
    });

    // Pre-select sites and referents if editing
    if (plan?.sites) {
      this.selectedSiteIds.set(plan.sites.map(s => s.id_site));
    }
    if (plan?.referents) {
      this.selectedReferentIds.set(plan.referents.map(r => r.id_role));
    }
  }

  private loadData(): void {
    this.isLoadingData.set(true);

    // Load evaluation types
    this.adminService.getEvaluationTypes().subscribe({
      next: (types) => this.evaluationTypes.set(types),
      error: () => this.evaluationTypes.set([])
    });

    // Load redacteur types
    this.adminService.getRedacteurTypes().subscribe({
      next: (types) => this.redacteurTypes.set(types),
      error: () => this.redacteurTypes.set([])
    });

    // Load sites
    this.adminService.getSites({ page: 1, page_size: 100 }).subscribe({
      next: (response) => {
        const sites = response.results.map(s => ({
          id: s.id_site,
          nom: s.nom_site,
          type: s.type_site_label,
          selected: this.selectedSiteIds().includes(s.id_site)
        }));
        this.availableSites.set(sites);
      },
      error: () => this.availableSites.set([])
    });

    // Load users (referents potentiels)
    this.adminService.getUsers({ page: 1, page_size: 100 }).subscribe({
      next: (response) => {
        const users = response.results.map(u => ({
          id: u.id_role,
          nom: `${u.prenom_role || ''} ${u.nom_role || ''}`.trim() || u.email,
          email: u.email,
          role: this.getRoleLabel(u.role_level),
          selected: this.selectedReferentIds().includes(u.id_role)
        }));
        this.availableUsers.set(users);
        this.isLoadingData.set(false);
      },
      error: () => {
        this.availableUsers.set([]);
        this.isLoadingData.set(false);
      }
    });
  }

  private getRoleLabel(roleLevel?: string): string {
    const labels: Record<string, string> = {
      'super_admin': 'Super Admin',
      'admin_og': 'Admin Org.',
      'referent': 'Referent',
      'utilisateur': 'Utilisateur'
    };
    return roleLevel ? labels[roleLevel] || roleLevel : '';
  }

  // Site selection methods
  toggleSite(siteId: number): void {
    const current = this.selectedSiteIds();
    if (current.includes(siteId)) {
      this.selectedSiteIds.set(current.filter(id => id !== siteId));
    } else {
      this.selectedSiteIds.set([...current, siteId]);
    }
  }

  selectAllSites(): void {
    const allSiteIds = this.filteredSites().map(s => s.id);
    const current = this.selectedSiteIds();
    // Add all filtered sites that are not already selected
    const newIds = [...new Set([...current, ...allSiteIds])];
    this.selectedSiteIds.set(newIds);
  }

  deselectAllSites(): void {
    const filteredIds = this.filteredSites().map(s => s.id);
    const current = this.selectedSiteIds();
    // Remove only filtered sites from selection
    this.selectedSiteIds.set(current.filter(id => !filteredIds.includes(id)));
  }

  isSiteSelected(siteId: number): boolean {
    return this.selectedSiteIds().includes(siteId);
  }

  getSelectedSitesCount(): number {
    return this.selectedSiteIds().length;
  }

  filterSites(): void {
    // Update the signal to trigger computed recomputation
    this.siteSearchSignal.set(this.siteSearchQuery);
  }

  // User/Referent selection methods
  toggleReferent(userId: number): void {
    const current = this.selectedReferentIds();
    if (current.includes(userId)) {
      this.selectedReferentIds.set(current.filter(id => id !== userId));
    } else {
      this.selectedReferentIds.set([...current, userId]);
    }
  }

  selectAllReferents(): void {
    const allUserIds = this.filteredUsers().map(u => u.id);
    const current = this.selectedReferentIds();
    // Add all filtered users that are not already selected
    const newIds = [...new Set([...current, ...allUserIds])];
    this.selectedReferentIds.set(newIds);
  }

  deselectAllReferents(): void {
    const filteredIds = this.filteredUsers().map(u => u.id);
    const current = this.selectedReferentIds();
    // Remove only filtered users from selection
    this.selectedReferentIds.set(current.filter(id => !filteredIds.includes(id)));
  }

  isReferentSelected(userId: number): boolean {
    return this.selectedReferentIds().includes(userId);
  }

  getSelectedReferentsCount(): number {
    return this.selectedReferentIds().length;
  }

  filterUsers(): void {
    // Update the signal to trigger computed recomputation
    this.userSearchSignal.set(this.userSearchQuery);
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const formValue = this.form.value;

    const payload: PlanCreatePayload = {
      nom: formValue.nom,
      statut: formValue.statut,
      version: formValue.version || undefined,
      annee_debut: formValue.annee_debut || undefined,
      annee_fin: formValue.annee_fin || undefined,
      gestion_partagee: formValue.gestion_partagee,
      ct88: formValue.ct88,
      risque_incendie: formValue.risque_incendie,
      id_evaluation: formValue.id_evaluation || undefined,
      id_redacteur_type: formValue.id_redacteur_type || undefined,
      redacteur_nom: formValue.redacteur_nom || undefined,
      commentaire: formValue.commentaire || undefined,
      sites_ids: this.selectedSiteIds(),
      referents_ids: this.selectedReferentIds()
    };

    const request$ = this.isEditMode
      ? this.adminService.updatePlan(this.data!.plan!.id_pg, payload)
      : this.adminService.createPlan(payload);

    request$.subscribe({
      next: (plan) => {
        this.isLoading.set(false);
        this.dialogRef.close({ success: true, plan });
      },
      error: (error: Error) => {
        this.isLoading.set(false);
        this.errorMessage.set(error.message);
      }
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
