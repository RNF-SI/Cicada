import { Component, inject, signal, computed, OnInit, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormControl, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MatDialog, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatAutocompleteModule, MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { MatRadioModule } from '@angular/material/radio';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { RouterModule } from '@angular/router';
import { Observable, map, startWith, debounceTime } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { OrganismeFormModalComponent } from '../organisme-form-modal/organisme-form-modal.component';
import { AuthService } from '../../../../core/services/auth.service';
import { ViewScopeToggleComponent, ViewScope } from '../../view-scope-toggle/view-scope-toggle.component';
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
  accessType?: string;
  accessLabel?: string;
  organismes?: Array<{ id_organisme: number; nom_organisme: string; principal?: boolean; type_organisme_code?: string }>;
}

interface SelectableUser {
  id: number;
  nom: string;
  email: string;
  role?: string;
  selected: boolean;
}

/** Représente un organisme (existant ou texte libre) */
interface OrganismeEntry {
  type: 'organisme' | 'text';
  organismeId?: number;
  displayName: string;
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
    MatAutocompleteModule,
    MatRadioModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatTooltipModule,
    MatSnackBarModule,
    TranslateModule,
    RouterModule,
    ViewScopeToggleComponent
  ],
  templateUrl: './plan-form-modal.component.html',
  styleUrl: './plan-form-modal.component.scss'
})
export class PlanFormModalComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  readonly dialogRef = inject(MatDialogRef<PlanFormModalComponent>);
  private readonly translate = inject(TranslateService);
  private readonly snackBar = inject(MatSnackBar);
  readonly data = inject<PlanFormModalData>(MAT_DIALOG_DATA, { optional: true });

  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly currentUser = this.authService.currentUser;

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

  // Available organismes for rédacteur selection
  availableOrganismes = signal<{ id_organisme: number; nom_organisme: string }[]>([]);

  // Organisme rédacteur principal (hybrid: organisme + free text)
  @ViewChild('organismeInput') organismeInput!: ElementRef<HTMLInputElement>;
  private readonly dialog = inject(MatDialog);
  selectedOrganisme = signal<OrganismeEntry | null>(null);
  organismeCtrl = new FormControl('');
  filteredOrganismes$!: Observable<{ id_organisme: number; nom_organisme: string }[]>;

  // Selected items
  selectedSiteIds = signal<number[]>([]);
  selectedReferentIds = signal<number[]>([]);

  // Site scope toggle
  siteScope = signal<ViewScope>('mine');
  readonly showSiteScopeToggle = computed(() => this.authService.isAdminOrganisme() || this.isSuperAdmin());

  // Search queries as signals for reactivity
  siteSearchQuery = '';
  userSearchQuery = '';
  private siteSearchSignal = signal('');
  private userSearchSignal = signal('');

  /** Types d'accès correspondant à une relation directe (mes sites) */
  private readonly directAccessTypes = new Set(['referent', 'conservateur', 'membre']);

  // Filtered lists (computed) — scope + recherche
  filteredSites = computed(() => {
    let sites = this.availableSites();

    // Filtre par scope
    const scope = this.siteScope();
    if (scope === 'mine') {
      sites = sites.filter(s => s.accessType && this.directAccessTypes.has(s.accessType));
    } else if (scope === 'organisme') {
      sites = sites.filter(s => s.accessType && s.accessType !== 'super_admin');
    }
    // scope === 'all' → pas de filtre

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

  // Détecter si un organisme CEN est lié (réactif aux sites sélectionnés)
  hasCenOrganisme = computed(() => {
    const selectedIds = this.selectedSiteIds();
    const sites = this.availableSites();
    // Vérifier si l'un des sites sélectionnés a un organisme CEN
    return sites
      .filter(s => selectedIds.includes(s.id))
      .some(s => s.organismes?.some(org => org.type_organisme_code === 'CEN'));
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
    this.setupAutocomplete();
  }

  private setupAutocomplete(): void {
    this.filteredOrganismes$ = this.organismeCtrl.valueChanges.pipe(
      startWith(''),
      debounceTime(200),
      map(value => this.filterOrganismesForAutocomplete(value || ''))
    );
  }

  private filterOrganismesForAutocomplete(value: string): { id_organisme: number; nom_organisme: string }[] {
    const filterValue = value.toLowerCase().trim();
    if (!filterValue) return this.availableOrganismes().slice(0, 20);
    return this.availableOrganismes().filter(org =>
      org.nom_organisme.toLowerCase().includes(filterValue)
    ).slice(0, 20);
  }

  private initForm(): void {
    const plan = this.data?.plan;

    this.form = this.fb.group({
      // Champs obligatoires
      nom: [plan?.nom || '', [Validators.required, Validators.maxLength(255)]],
      rang: [plan?.rang || 1, [Validators.required, Validators.min(1)]],
      ct88: [plan?.ct88 ?? false, Validators.required],
      annee_debut: [plan?.annee_debut || this.currentYear, [Validators.required, Validators.min(1900), Validators.max(2100)]],
      annee_fin: [plan?.annee_fin || this.currentYear + 5, [Validators.required, Validators.min(1900), Validators.max(2100)]],

      // Champs optionnels
      surface: [plan?.surface || null],
      date_avis_csrpn: [plan?.date_avis_csrpn ? new Date(plan.date_avis_csrpn) : null],
      id_docgestion_fcen: [plan?.id_docgestion_fcen || ''],
      id_redacteur_type: [plan?.id_redacteur_type || null],
      redacteur_nom: [plan?.redacteur_nom || '', Validators.maxLength(255)],
      redacteurs: [plan?.redacteurs || ''],
      relecteurs: [plan?.relecteurs || ''],
      autres_contributeurs: [plan?.autres_contributeurs || ''],

      // Champs existants gardés mais non affichés dans le formulaire principal
      statut: [plan?.statut || 'draft'],
      version: [plan?.version || '1', Validators.maxLength(20)],
      gestion_partagee: [plan?.gestion_partagee || false],
      risque_incendie: [plan?.risque_incendie || false],
      id_evaluation: [plan?.id_evaluation || null],
      commentaire: [plan?.commentaire || '']
    });

    // Pre-select sites and referents if editing
    if (plan?.sites) {
      this.selectedSiteIds.set(plan.sites.map(s => s.id_site));
    }
    if (plan?.referents) {
      this.selectedReferentIds.set(plan.referents.map(r => r.id_role));
    }

    // Pre-populate organisme rédacteur in edit mode
    if (plan?.organismes_redacteurs_list?.length) {
      const firstOrg = plan.organismes_redacteurs_list[0];
      this.selectedOrganisme.set({
        type: 'organisme',
        organismeId: firstOrg.id_organisme,
        displayName: firstOrg.nom_organisme
      });
    } else if (plan?.redacteur_nom) {
      this.selectedOrganisme.set({
        type: 'text',
        displayName: plan.redacteur_nom
      });
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

    // Load all accessible sites (backend filters by role, client filters by scope)
    this.adminService.getSites({ page: 1, page_size: 200 }).subscribe({
      next: (response) => {
        const sites = response.results.map(s => ({
          id: s.id_site,
          nom: s.nom_site,
          type: s.type_site_label,
          selected: this.selectedSiteIds().includes(s.id_site),
          accessType: s.current_user_access?.access_type,
          accessLabel: s.current_user_access?.role_label,
          organismes: s.organismes || []
        }));
        this.availableSites.set(sites);
      },
      error: () => this.availableSites.set([])
    });

    // Load organismes (pour sélection rédacteurs)
    this.adminService.getOrganismes({ page: 1, page_size: 1000 }).subscribe({
      next: (response) => {
        this.availableOrganismes.set(
          response.results.map(o => ({ id_organisme: o.id_organisme, nom_organisme: o.nom_organisme }))
        );
      },
      error: () => this.availableOrganismes.set([])
    });

    // Load users (referents potentiels) - if not super_admin, filter by organisme
    const currentOrgId = this.currentUser()?.organisme?.id_organisme;
    const userParams = (!this.isSuperAdmin() && currentOrgId)
      ? { page: 1, page_size: 100, organisme: currentOrgId }
      : { page: 1, page_size: 100 };

    this.adminService.getUsers(userParams).subscribe({
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

  // ==================== ORGANISME REDACTEUR ====================

  /** Sélectionne un organisme existant */
  selectOrganisme(event: MatAutocompleteSelectedEvent): void {
    const org = event.option.value;
    if (org) {
      this.selectedOrganisme.set({
        type: 'organisme',
        organismeId: org.id_organisme,
        displayName: org.nom_organisme
      });
    }
    this.organismeCtrl.setValue('');
    if (this.organismeInput) this.organismeInput.nativeElement.value = '';
  }

  /** Supprime l'organisme sélectionné */
  clearOrganisme(): void {
    this.selectedOrganisme.set(null);
    this.organismeCtrl.setValue('');
  }

  /** Affiche le nom de l'organisme pour l'autocomplete */
  displayOrganismeFn(org: any): string {
    if (!org) return '';
    if (org.freeText) return org.freeText;
    return org.nom_organisme || '';
  }

  /** Ouvre le modal de création d'organisme */
  openCreateOrganismeDialog(): void {
    const dialogRef = this.dialog.open(OrganismeFormModalComponent, {
      width: '600px',
      maxWidth: '95vw',
      data: { parentOrganismes: this.availableOrganismes() }
    });

    dialogRef.afterClosed().subscribe((org: any) => {
      if (org?.id_organisme) {
        this.availableOrganismes.update(orgs => [
          ...orgs,
          { id_organisme: org.id_organisme, nom_organisme: org.nom_organisme }
        ]);
        this.selectedOrganisme.set({
          type: 'organisme',
          organismeId: org.id_organisme,
          displayName: org.nom_organisme
        });
      }
    });
  }

  private getRoleLabel(roleLevel?: string): string {
    const labels: Record<string, string> = {
      'super_admin': 'Super Admin',
      'admin_og': 'Admin Org.',
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
    this.siteSearchSignal.set(this.siteSearchQuery);
  }

  onSiteScopeChange(scope: ViewScope): void {
    this.siteScope.set(scope);
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

    // Validation des sites obligatoires
    if (this.selectedSiteIds().length === 0) {
      this.errorMessage.set(this.translate.instant('modals.planForm.validation.sitesRequired'));
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const formValue = this.form.value;

    // Formater la date pour l'API (YYYY-MM-DD)
    let dateValidationCspn: string | undefined;
    if (formValue.date_avis_csrpn) {
      const date = new Date(formValue.date_avis_csrpn);
      dateValidationCspn = date.toISOString().split('T')[0];
    }

    const payload: PlanCreatePayload = {
      // Champs obligatoires
      nom: formValue.nom,
      sites_ids: this.selectedSiteIds(),
      rang: formValue.rang,
      ct88: formValue.ct88,
      annee_debut: formValue.annee_debut,
      annee_fin: formValue.annee_fin,

      // Champs optionnels
      surface: formValue.surface || undefined,
      date_avis_csrpn: dateValidationCspn,
      id_docgestion_fcen: formValue.id_docgestion_fcen || undefined,
      id_redacteur_type: formValue.id_redacteur_type || undefined,
      redacteur_nom: this.selectedOrganisme()?.displayName || formValue.redacteur_nom || undefined,
      redacteurs: formValue.redacteurs || undefined,
      relecteurs: formValue.relecteurs || undefined,
      autres_contributeurs: formValue.autres_contributeurs || undefined,

      // Champs additionnels
      statut: formValue.statut,
      version: formValue.version || undefined,
      gestion_partagee: formValue.gestion_partagee,
      risque_incendie: formValue.risque_incendie,
      id_evaluation: formValue.id_evaluation || undefined,
      commentaire: formValue.commentaire || undefined,
      referents_ids: this.selectedReferentIds(),
      organismes_redacteurs_ids: this.selectedOrganisme()?.organismeId
        ? [this.selectedOrganisme()!.organismeId!]
        : []
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
