/**
 * Composant pleine page pour la création d'un nouveau plan de gestion.
 * Layout: Hero section + Card contenant le formulaire + Action bar.
 *
 * Fonctionnalités:
 * - Création de site via modal
 * - Rédacteurs/Relecteurs: sélection d'utilisateurs ou saisie libre
 * - Organisme rédacteur: sélection d'organisme ou saisie libre
 */
import { Component, inject, signal, computed, OnInit, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormBuilder, FormGroup, FormControl, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatRadioModule } from '@angular/material/radio';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatChipsModule } from '@angular/material/chips';
import { MatAutocompleteModule, MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { COMMA, ENTER } from '@angular/cdk/keycodes';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Observable, map, startWith, debounceTime, distinctUntilChanged } from 'rxjs';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { SiteFormModalComponent, SiteFormModalResult } from '../../shared/components/modals/site-form-modal/site-form-modal.component';
import {
  PlanCreatePayload,
  AdminUser,
  AdminOrganisme
} from '../../core/models/admin.model';

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
  pendingValidation?: boolean;
}

/** Représente un rédacteur ou relecteur (utilisateur ou texte libre) */
interface PersonEntry {
  type: 'user' | 'text';
  userId?: number;
  displayName: string;
  email?: string;
}

/** Représente un organisme (existant ou texte libre) */
interface OrganismeEntry {
  type: 'organisme' | 'text';
  organismeId?: number;
  displayName: string;
}

@Component({
  selector: 'app-plan-create',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    RouterModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
    MatRadioModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatTooltipModule,
    MatChipsModule,
    MatAutocompleteModule,
    MatIconModule,
    MatDialogModule,
    MatSnackBarModule,
    TranslateModule,
    HeaderComponent
  ],
  templateUrl: './plan-create.component.html',
  styleUrl: './plan-create.component.scss'
})
export class PlanCreateComponent implements OnInit {
  @ViewChild('redacteursInput') redacteursInput!: ElementRef<HTMLInputElement>;
  @ViewChild('relecteursInput') relecteursInput!: ElementRef<HTMLInputElement>;
  @ViewChild('organismeInput') organismeInput!: ElementRef<HTMLInputElement>;

  private readonly elRef = inject(ElementRef);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly translate = inject(TranslateService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly currentUser = this.authService.currentUser;

  form!: FormGroup;
  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);

  // Nomenclatures
  redacteurTypes = signal<NomenclatureItem[]>([]);

  // Available sites
  availableSites = signal<SelectableSite[]>([]);

  // Selected items
  selectedSiteIds = signal<number[]>([]);

  // Search query
  siteSearchQuery = '';
  private siteSearchSignal = signal('');

  // Filtered list (computed)
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

  // Current year for validation
  currentYear = new Date().getFullYear();

  // Separator keys for chips
  readonly separatorKeysCodes = [ENTER, COMMA] as const;

  // === Rédacteurs (hybrid: users + free text) ===
  redacteurs = signal<PersonEntry[]>([]);
  redacteursCtrl = new FormControl('');
  availableUsers = signal<AdminUser[]>([]);
  filteredUsers$!: Observable<AdminUser[]>;

  // === Relecteurs (hybrid: users + free text) ===
  relecteurs = signal<PersonEntry[]>([]);
  relecteursCtrl = new FormControl('');
  filteredUsersForRelecteurs$!: Observable<AdminUser[]>;

  // === Organisme rédacteur (hybrid: organisme + free text) ===
  selectedOrganisme = signal<OrganismeEntry | null>(null);
  organismeCtrl = new FormControl('');
  availableOrganismes = signal<AdminOrganisme[]>([]);
  filteredOrganismes$!: Observable<AdminOrganisme[]>;

  ngOnInit(): void {
    this.initForm();
    this.loadData();
    this.setupAutocomplete();
  }

  private initForm(): void {
    this.form = this.fb.group({
      // Champs obligatoires
      nom: ['', [Validators.required, Validators.maxLength(255)]],
      rang: [1, [Validators.required, Validators.min(1)]],
      ct88: [false, Validators.required],
      annee_debut: [this.currentYear, [Validators.required, Validators.min(1900), Validators.max(2100)]],
      annee_fin: [this.currentYear + 5, [Validators.required, Validators.min(1900), Validators.max(2100)]],

      // Champs optionnels
      surface: [null],
      date_validation_cspn: [null],
      id_docgestion_fcen: [''],
      id_redacteur_type: [null],

      // Champs additionnels non affichés
      statut: ['draft'],
      version: ['1.0', Validators.maxLength(20)],
      commentaire: ['']
    });
  }

  private setupAutocomplete(): void {
    // Autocomplete pour rédacteurs
    this.filteredUsers$ = this.redacteursCtrl.valueChanges.pipe(
      startWith(''),
      debounceTime(200),
      distinctUntilChanged(),
      map(value => this.filterUsers(value || ''))
    );

    // Autocomplete pour relecteurs
    this.filteredUsersForRelecteurs$ = this.relecteursCtrl.valueChanges.pipe(
      startWith(''),
      debounceTime(200),
      distinctUntilChanged(),
      map(value => this.filterUsers(value || ''))
    );

    // Autocomplete pour organisme
    this.filteredOrganismes$ = this.organismeCtrl.valueChanges.pipe(
      startWith(''),
      debounceTime(200),
      distinctUntilChanged(),
      map(value => this.filterOrganismes(value || ''))
    );
  }

  private filterUsers(value: string): AdminUser[] {
    const filterValue = value.toLowerCase().trim();
    if (!filterValue) return this.availableUsers().slice(0, 10);

    return this.availableUsers().filter(user => {
      const fullName = `${user.prenom_role || ''} ${user.nom_role || ''}`.toLowerCase();
      return fullName.includes(filterValue) || user.email.toLowerCase().includes(filterValue);
    }).slice(0, 10);
  }

  private filterOrganismes(value: string): AdminOrganisme[] {
    const filterValue = value.toLowerCase().trim();
    if (!filterValue) return this.availableOrganismes().slice(0, 10);

    return this.availableOrganismes().filter(org =>
      org.nom_organisme.toLowerCase().includes(filterValue)
    ).slice(0, 10);
  }

  private loadData(): void {
    this.isLoadingData.set(true);

    const currentOrgId = this.currentUser()?.organisme?.id_organisme;
    const filterByOrg = !this.isSuperAdmin() && currentOrgId;

    // Load redacteur types
    this.adminService.getRedacteurTypes().subscribe({
      next: (types) => this.redacteurTypes.set(types),
      error: () => this.redacteurTypes.set([])
    });

    // Load users for autocomplete
    this.adminService.getUsers({ page: 1, page_size: 200 }).subscribe({
      next: (response) => this.availableUsers.set(response.results),
      error: () => this.availableUsers.set([])
    });

    // Load organismes for autocomplete
    this.adminService.getOrganismes({ page: 1 }).subscribe({
      next: (response) => this.availableOrganismes.set(response.results),
      error: () => this.availableOrganismes.set([])
    });

    // Load sites - if admin_org, only load sites from their organisme
    if (filterByOrg) {
      this.adminService.getOrganismeSites(currentOrgId!).subscribe({
        next: (orgSites) => {
          const sites = orgSites.map(s => ({
            id: s.id_site,
            nom: s.nom_site,
            type: s.type_site_label || s.type_site,
            selected: false,
            pendingValidation: false
          }));
          this.availableSites.set(sites);
          this.isLoadingData.set(false);
        },
        error: () => {
          this.availableSites.set([]);
          this.isLoadingData.set(false);
        }
      });
    } else {
      this.adminService.getSites({ page: 1, page_size: 200 }).subscribe({
        next: (response) => {
          const sites = response.results.map(s => ({
            id: s.id_site,
            nom: s.nom_site,
            type: s.type_site_label,
            selected: false,
            pendingValidation: false
          }));
          this.availableSites.set(sites);
          this.isLoadingData.set(false);
        },
        error: () => {
          this.availableSites.set([]);
          this.isLoadingData.set(false);
        }
      });
    }
  }

  // ==================== SITES ====================

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
    const newIds = [...new Set([...current, ...allSiteIds])];
    this.selectedSiteIds.set(newIds);
  }

  deselectAllSites(): void {
    const filteredIds = this.filteredSites().map(s => s.id);
    const current = this.selectedSiteIds();
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

  /** Ouvre le modal de création de site */
  openCreateSiteModal(): void {
    const dialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '1300px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      disableClose: false,
      data: {
        organismeId: this.currentUser()?.organisme?.id_organisme
      }
    });

    dialogRef.afterClosed().subscribe((result: SiteFormModalResult | undefined) => {
      if (result?.site) {
        // Déterminer le type du site (peut être un objet ou une string)
        let siteType: string | undefined;
        if (typeof result.site.type_site_label === 'string') {
          siteType = result.site.type_site_label;
        } else if (result.site.type_site_label && typeof result.site.type_site_label === 'object') {
          siteType = (result.site.type_site_label as { label?: string }).label;
        } else if (typeof result.site.type_site === 'string') {
          siteType = result.site.type_site;
        }

        // Ajouter le nouveau site à la liste
        const newSite: SelectableSite = {
          id: result.site.id_site,
          nom: result.site.nom_site,
          type: siteType,
          selected: false,
          pendingValidation: result.validationPending || false
        };

        // Ajouter en haut de la liste
        this.availableSites.update(sites => [newSite, ...sites]);

        // Sélectionner automatiquement le nouveau site (même en attente de validation)
        this.selectedSiteIds.update(ids => [...ids, result.site!.id_site]);

        if (result.validationPending) {
          this.snackBar.open(
            this.translate.instant('modals.planForm.messages.sitePendingValidation'),
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
        } else {
          this.snackBar.open(
            this.translate.instant('modals.planForm.messages.siteCreated'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
        }
      }
    });
  }

  // ==================== REDACTEURS ====================

  /** Ajoute un utilisateur comme rédacteur */
  addRedacteurFromUser(event: MatAutocompleteSelectedEvent): void {
    const user = event.option.value as AdminUser;
    const entry: PersonEntry = {
      type: 'user',
      userId: user.id_role,
      displayName: `${user.prenom_role || ''} ${user.nom_role || ''}`.trim() || user.email,
      email: user.email
    };

    // Éviter les doublons
    if (!this.redacteurs().some(r => r.type === 'user' && r.userId === user.id_role)) {
      this.redacteurs.update(list => [...list, entry]);
    }

    this.redacteursCtrl.setValue('');
    if (this.redacteursInput) {
      this.redacteursInput.nativeElement.value = '';
    }
  }

  /** Ajoute un texte libre comme rédacteur */
  addRedacteurFromText(event: any): void {
    const value = (event.value || '').trim();
    if (value) {
      const entry: PersonEntry = {
        type: 'text',
        displayName: value
      };

      // Éviter les doublons
      if (!this.redacteurs().some(r => r.type === 'text' && r.displayName === value)) {
        this.redacteurs.update(list => [...list, entry]);
      }
    }

    event.chipInput?.clear();
    this.redacteursCtrl.setValue('');
  }

  /** Supprime un rédacteur */
  removeRedacteur(entry: PersonEntry): void {
    this.redacteurs.update(list => list.filter(r => r !== entry));
  }

  // ==================== RELECTEURS ====================

  /** Ajoute un utilisateur comme relecteur */
  addRelecteurFromUser(event: MatAutocompleteSelectedEvent): void {
    const user = event.option.value as AdminUser;
    const entry: PersonEntry = {
      type: 'user',
      userId: user.id_role,
      displayName: `${user.prenom_role || ''} ${user.nom_role || ''}`.trim() || user.email,
      email: user.email
    };

    if (!this.relecteurs().some(r => r.type === 'user' && r.userId === user.id_role)) {
      this.relecteurs.update(list => [...list, entry]);
    }

    this.relecteursCtrl.setValue('');
    if (this.relecteursInput) {
      this.relecteursInput.nativeElement.value = '';
    }
  }

  /** Ajoute un texte libre comme relecteur */
  addRelecteurFromText(event: any): void {
    const value = (event.value || '').trim();
    if (value) {
      const entry: PersonEntry = {
        type: 'text',
        displayName: value
      };

      if (!this.relecteurs().some(r => r.type === 'text' && r.displayName === value)) {
        this.relecteurs.update(list => [...list, entry]);
      }
    }

    event.chipInput?.clear();
    this.relecteursCtrl.setValue('');
  }

  /** Supprime un relecteur */
  removeRelecteur(entry: PersonEntry): void {
    this.relecteurs.update(list => list.filter(r => r !== entry));
  }

  // ==================== ORGANISME REDACTEUR ====================

  /** Sélectionne un organisme existant ou texte libre */
  selectOrganisme(event: MatAutocompleteSelectedEvent): void {
    const value = event.option.value;

    // Free text option
    if (value?.freeText) {
      const text = (value.freeText as string).trim();
      if (text) {
        this.selectedOrganisme.set({
          type: 'text',
          displayName: text
        });
      }
      this.organismeCtrl.setValue('');
      if (this.organismeInput) {
        this.organismeInput.nativeElement.value = '';
      }
      return;
    }

    const org = value as AdminOrganisme;
    if (org) {
      this.selectedOrganisme.set({
        type: 'organisme',
        organismeId: org.id_organisme,
        displayName: org.nom_organisme
      });
    }

    this.organismeCtrl.setValue('');
    if (this.organismeInput) {
      this.organismeInput.nativeElement.value = '';
    }
  }

  /** Définit un organisme en texte libre */
  setOrganismeFromText(): void {
    const value = this.organismeCtrl.value?.trim();
    if (value) {
      this.selectedOrganisme.set({
        type: 'text',
        displayName: value
      });
      this.organismeCtrl.setValue('');
    }
  }

  /** Supprime l'organisme sélectionné */
  clearOrganisme(): void {
    this.selectedOrganisme.set(null);
    this.organismeCtrl.setValue('');
  }

  /** Affiche le nom de l'utilisateur pour l'autocomplete */
  displayUserFn(user: AdminUser): string {
    if (!user) return '';
    return `${user.prenom_role || ''} ${user.nom_role || ''}`.trim() || user.email;
  }

  /** Affiche le nom de l'organisme pour l'autocomplete */
  displayOrganismeFn(org: any): string {
    if (!org) return '';
    if (org.freeText) return org.freeText;
    return org.nom_organisme || '';
  }

  // ==================== SOUMISSION ====================

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.scrollToError();
      return;
    }

    // Validation des sites obligatoires
    if (this.selectedSiteIds().length === 0) {
      this.errorMessage.set(this.translate.instant('modals.planForm.validation.sitesRequired'));
      this.scrollToError();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const formValue = this.form.value;

    // Formater la date pour l'API (YYYY-MM-DD)
    let dateValidationCspn: string | undefined;
    if (formValue.date_validation_cspn) {
      const date = new Date(formValue.date_validation_cspn);
      dateValidationCspn = date.toISOString().split('T')[0];
    }

    // Formater les rédacteurs (JSON string)
    const redacteursData = this.redacteurs().map(r => ({
      type: r.type,
      user_id: r.userId,
      name: r.displayName,
      email: r.email
    }));

    // Formater les relecteurs (JSON string)
    const relecteursData = this.relecteurs().map(r => ({
      type: r.type,
      user_id: r.userId,
      name: r.displayName,
      email: r.email
    }));

    // Formater l'organisme rédacteur
    const orgEntry = this.selectedOrganisme();
    let redacteurNom: string | undefined;
    if (orgEntry) {
      redacteurNom = orgEntry.displayName;
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
      date_validation_cspn: dateValidationCspn,
      id_docgestion_fcen: formValue.id_docgestion_fcen || undefined,
      id_redacteur_type: formValue.id_redacteur_type || undefined,
      redacteur_nom: redacteurNom,
      // Stocker les rédacteurs/relecteurs comme JSON strings
      redacteurs: redacteursData.length > 0 ? JSON.stringify(redacteursData) : undefined,
      relecteurs: relecteursData.length > 0 ? JSON.stringify(relecteursData) : undefined,

      // Champs additionnels
      statut: formValue.statut,
      version: formValue.version || undefined,
      commentaire: formValue.commentaire || undefined
    };

    this.adminService.createPlan(payload).subscribe({
      next: (plan) => {
        this.isLoading.set(false);
        this.router.navigate(['/plans', plan.slug]);
      },
      error: (error: Error) => {
        this.isLoading.set(false);
        this.errorMessage.set(error.message);
        this.scrollToError();
      }
    });
  }

  private scrollToError(): void {
    setTimeout(() => {
      const banner = this.elRef.nativeElement.querySelector('.error-banner');
      if (banner) {
        banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      const invalid = this.elRef.nativeElement.querySelector('mat-form-field.ng-invalid');
      invalid?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }

  onCancel(): void {
    this.router.navigate(['/plans']);
  }
}
