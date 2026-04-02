/**
 * Composant pleine page pour la création d'un nouveau plan de gestion.
 * Layout: Hero section + Card contenant le formulaire + Action bar.
 *
 * Fonctionnalités:
 * - Création de site via modal
 * - Rédacteurs/Relecteurs: champs texte libre
 * - Organisme rédacteur principal: sélection d'organisme ou saisie libre
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
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Observable, map, startWith, debounceTime, distinctUntilChanged } from 'rxjs';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { ViewScopeToggleComponent, ViewScope } from '../../shared/components/view-scope-toggle/view-scope-toggle.component';
import { SiteFormModalComponent, SiteFormModalResult } from '../../shared/components/modals/site-form-modal/site-form-modal.component';
import {
  PlanCreatePayload,
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
  accessType?: string;
  accessLabel?: string;
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
    HeaderComponent,
    ViewScopeToggleComponent
  ],
  templateUrl: './plan-create.component.html',
  styleUrl: './plan-create.component.scss'
})
export class PlanCreateComponent implements OnInit {
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
  readonly isRedacteurPrincipal = this.authService.isRedacteurPrincipal;
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

  // Site scope toggle
  siteScope = signal<ViewScope>('mine');
  readonly showSiteScopeToggle = computed(() => this.authService.isAdminOrganisme() || this.isSuperAdmin());

  // Search query
  siteSearchQuery = '';
  private siteSearchSignal = signal('');

  /** Types d'accès correspondant à une relation directe (mes sites) */
  private readonly directAccessTypes = new Set(['referent', 'conservateur', 'membre']);

  // Filtered list (computed) — scope + recherche
  filteredSites = computed(() => {
    let sites = this.availableSites();

    // Filtre par scope
    const scope = this.siteScope();
    if (scope === 'mine') {
      sites = sites.filter(s => s.accessType && this.directAccessTypes.has(s.accessType));
    } else if (scope === 'organisme') {
      // Inclut les sites directs + sites de l'organisme (exclut seulement super_admin sans lien)
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

  // Current year for validation
  currentYear = new Date().getFullYear();

  // === Organisme rédacteur (hybrid: organisme + free text) ===
  selectedOrganisme = signal<OrganismeEntry | null>(null);
  organismeCtrl = new FormControl('');
  availableOrganismes = signal<AdminOrganisme[]>([]);
  filteredOrganismes$!: Observable<AdminOrganisme[]>;

  ngOnInit(): void {
    // Super admin defaults to 'all' scope to see every site
    if (this.authService.isSuperAdmin()) {
      this.siteScope.set('all');
    }
    // Rédacteur principal defaults to 'all' scope (accès global)
    else if (this.authService.isRedacteurPrincipal()) {
      this.siteScope.set('all');
    }
    // Admin organisme defaults to 'organisme' scope to see all their org's sites
    else if (this.authService.isAdminOrganisme()) {
      this.siteScope.set('organisme');
    }
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
      redacteurs: [''],
      relecteurs: [''],
      autres_contributeurs: [''],

      // Champs additionnels non affichés
      statut: ['draft'],
      version: ['1.0', Validators.maxLength(20)],
      commentaire: ['']
    });
  }

  private setupAutocomplete(): void {
    // Autocomplete pour organisme
    this.filteredOrganismes$ = this.organismeCtrl.valueChanges.pipe(
      startWith(''),
      debounceTime(200),
      distinctUntilChanged(),
      map(value => this.filterOrganismes(value || ''))
    );
  }

  private filterOrganismes(value: string): AdminOrganisme[] {
    const filterValue = value.toLowerCase().trim();
    if (!filterValue) return this.availableOrganismes().slice(0, 20);

    return this.availableOrganismes().filter(org =>
      org.nom_organisme.toLowerCase().includes(filterValue)
    ).slice(0, 20);
  }

  private loadData(): void {
    this.isLoadingData.set(true);

    // Load redacteur types
    this.adminService.getRedacteurTypes().subscribe({
      next: (types) => this.redacteurTypes.set(types),
      error: () => this.redacteurTypes.set([])
    });

    // Load organismes for autocomplete
    this.adminService.getOrganismes({ page: 1, page_size: 1000 }).subscribe({
      next: (response) => this.availableOrganismes.set(response.results),
      error: () => this.availableOrganismes.set([])
    });

    // Load all accessible sites (backend filters by role, client filters by scope)
    this.adminService.getSites({ page: 1, page_size: 1000 }).subscribe({
      next: (response) => {
        const sites = response.results.map(s => ({
          id: s.id_site,
          nom: s.nom_site,
          type: s.type_site_label,
          selected: false,
          pendingValidation: false,
          accessType: s.current_user_access?.access_type,
          accessLabel: s.current_user_access?.role_label
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

  onSiteScopeChange(scope: ViewScope): void {
    this.siteScope.set(scope);
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
      redacteurs: formValue.redacteurs || undefined,
      relecteurs: formValue.relecteurs || undefined,
      autres_contributeurs: formValue.autres_contributeurs || undefined,

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
