import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subject, Subscription, debounceTime, distinctUntilChanged, filter } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { AdminSite, SiteCreatePayload, GeoJSONGeometry, DuplicateCheckResult, DuplicateSite } from '../../../../core/models/admin.model';
import { LeafletMapEditComponent } from '../../leaflet-map-edit/leaflet-map-edit.component';

export interface SiteFormModalData {
  site?: AdminSite; // If provided, edit mode
  organismeId?: number; // If provided, auto-link site to this organisme after creation
  principal?: boolean; // If true, set as principal site for the organisme
  existingPolygon?: GeoJSONGeometry | null; // Existing polygon geometry
  existingPoint?: GeoJSONGeometry | null; // Existing point geometry
}

/**
 * Result returned when modal is closed
 */
export interface SiteFormModalResult {
  site?: AdminSite;
  validationPending?: boolean;
  message?: string;
  /** Action requested due to duplicate detection */
  duplicateAction?: 'request_access' | 'request_org_link';
  /** Site targeted by the duplicate action */
  duplicateSite?: DuplicateSite;
  /** Whether to also request personal access when linking organisme */
  alsoRequestAccess?: boolean;
}

interface SiteType {
  id_nomenclature: number;
  cd_nomenclature: string;
  label: string;
}

@Component({
  selector: 'app-site-form-modal',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatIconModule,
    TranslateModule,
    LeafletMapEditComponent
  ],
  templateUrl: './site-form-modal.component.html',
  styleUrl: './site-form-modal.component.scss'
})
export class SiteFormModalComponent implements OnInit, OnDestroy {
  private readonly fb = inject(FormBuilder);
  private readonly adminService = inject(AdminService);
  private readonly dialogRef = inject(MatDialogRef<SiteFormModalComponent>);
  private readonly translate = inject(TranslateService);
  readonly data = inject<SiteFormModalData>(MAT_DIALOG_DATA, { optional: true });

  form!: FormGroup;
  isLoading = signal(false);
  isLoadingTypes = signal(true);
  errorMessage = signal<string | null>(null);
  siteTypes = signal<SiteType[]>([]);

  // Geometry signals
  polygonGeometry = signal<GeoJSONGeometry | null>(null);
  pointGeometry = signal<GeoJSONGeometry | null>(null);
  activeGeometryTab = signal<number>(0);

  // Duplicate detection signals
  duplicateCheckResult = signal<DuplicateCheckResult | null>(null);
  isCheckingDuplicates = signal(false);
  showDuplicateWarning = signal(false);
  duplicateWarningDismissed = signal(false);

  // Subjects for debounced input
  private nameSubject = new Subject<string>();
  private inpnSubject = new Subject<string>();
  private subscriptions: Subscription[] = [];

  get isEditMode(): boolean {
    return !!this.data?.site;
  }

  /** Check if there's an exact INPN match (blocking) */
  get hasInpnDuplicate(): boolean {
    const result = this.duplicateCheckResult();
    return result !== null && result.exact_inpn_match !== null;
  }

  /** Check if there are similar names (warning) */
  get hasSimilarNames(): boolean {
    const result = this.duplicateCheckResult();
    return result ? result.similar_names.length > 0 : false;
  }

  ngOnInit(): void {
    this.initForm();
    this.loadSiteTypes();
    this.setupDuplicateChecking();

    // Initialize geometry from data
    if (this.data?.existingPolygon) {
      this.polygonGeometry.set(this.data.existingPolygon);
    }
    if (this.data?.existingPoint) {
      this.pointGeometry.set(this.data.existingPoint);
    }
  }

  ngOnDestroy(): void {
    this.subscriptions.forEach(sub => sub.unsubscribe());
    this.nameSubject.complete();
    this.inpnSubject.complete();
  }

  /**
   * Setup debounced duplicate checking on name and INPN fields
   */
  private setupDuplicateChecking(): void {
    // Don't check duplicates in edit mode (could be changed if needed)
    if (this.isEditMode) return;

    // Debounced name checking (500ms, min 3 chars)
    const nameSub = this.nameSubject.pipe(
      debounceTime(500),
      distinctUntilChanged(),
      filter(name => name.length >= 3)
    ).subscribe(name => this.checkDuplicates());

    // Debounced INPN checking (300ms, min 1 char)
    const inpnSub = this.inpnSubject.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      filter(inpn => inpn.length >= 1)
    ).subscribe(() => this.checkDuplicates());

    this.subscriptions.push(nameSub, inpnSub);
  }

  /**
   * Called when name field changes
   */
  onNameInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.nameSubject.next(value);
    // Reset dismissed state when user types
    this.duplicateWarningDismissed.set(false);
  }

  /**
   * Called when INPN field changes
   */
  onInpnInput(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.inpnSubject.next(value);
    // Reset dismissed state when user types
    this.duplicateWarningDismissed.set(false);
  }

  /**
   * Check for duplicate sites
   */
  private checkDuplicates(): void {
    const nomSite = this.form.get('nom_site')?.value?.trim() || '';
    const idInpn = this.form.get('id_inpn')?.value?.trim() || '';

    // Nothing to check
    if (nomSite.length < 3 && !idInpn) {
      this.duplicateCheckResult.set(null);
      this.showDuplicateWarning.set(false);
      return;
    }

    this.isCheckingDuplicates.set(true);

    const params: { nom_site?: string; id_inpn?: string; exclude_id?: number } = {};
    if (nomSite.length >= 3) params.nom_site = nomSite;
    if (idInpn) params.id_inpn = idInpn;
    if (this.isEditMode && this.data?.site?.id_site) {
      params.exclude_id = this.data.site.id_site;
    }

    this.adminService.checkDuplicates(params).subscribe({
      next: (result) => {
        this.isCheckingDuplicates.set(false);
        this.duplicateCheckResult.set(result);

        // Show warning if duplicates found and not dismissed
        const hasDuplicates = result.exact_inpn_match !== null || result.similar_names.length > 0;
        this.showDuplicateWarning.set(hasDuplicates && !this.duplicateWarningDismissed());
      },
      error: () => {
        this.isCheckingDuplicates.set(false);
        // Don't block user on check error
      }
    });
  }

  /**
   * Request access to an existing site (when user's org already manages the site)
   */
  requestAccessToSite(site: DuplicateSite): void {
    const result: SiteFormModalResult = {
      duplicateAction: 'request_access',
      duplicateSite: site
    };
    this.dialogRef.close(result);
  }

  /**
   * Request to link organisme to an existing site
   * @param site The site to link to
   * @param alsoRequestAccess If true, also request personal access after org link is approved
   */
  requestOrgLink(site: DuplicateSite, alsoRequestAccess: boolean = false): void {
    const result: SiteFormModalResult = {
      duplicateAction: 'request_org_link',
      duplicateSite: site,
      alsoRequestAccess
    };
    this.dialogRef.close(result);
  }

  /**
   * Dismiss the similar names warning and continue with creation
   */
  continueCreation(): void {
    this.duplicateWarningDismissed.set(true);
    this.showDuplicateWarning.set(false);
  }

  private initForm(): void {
    const site = this.data?.site;

    // Pour le type de site, utiliser type_site.id_nomenclature (format SiteDetailSerializer)
    const typeId = site?.type_site?.id_nomenclature || null;

    this.form = this.fb.group({
      nom_site: [site?.nom_site || '', [Validators.required, Validators.maxLength(255)]],
      id_local: [site?.id_local || '', Validators.maxLength(50)],
      id_inpn: [site?.id_inpn || '', Validators.maxLength(50)],
      id_type_site: [typeId],
      surf_off: [site?.surf_off || null, [Validators.min(0)]],
      marin: [site?.marin || false],
      outre_mer: [site?.outre_mer || false],
      active: [site?.active !== false], // Default to true
      requestAsReferent: [true] // Default to true (user wants to become referent)
    });
  }

  private loadSiteTypes(): void {
    this.isLoadingTypes.set(true);
    this.adminService.getSiteTypes().subscribe({
      next: (types) => {
        this.siteTypes.set(types);
        this.isLoadingTypes.set(false);
      },
      error: () => {
        // Fallback: use hardcoded types if API fails
        this.siteTypes.set([
          { id_nomenclature: 42, cd_nomenclature: 'RNN', label: 'Reserve Naturelle Nationale' },
          { id_nomenclature: 43, cd_nomenclature: 'RNR', label: 'Reserve Naturelle Regionale' },
          { id_nomenclature: 44, cd_nomenclature: 'PNR', label: 'Parc Naturel Regional' },
          { id_nomenclature: 45, cd_nomenclature: 'ENS', label: 'Espace Naturel Sensible' },
          { id_nomenclature: 46, cd_nomenclature: 'APB', label: 'Arrete de Protection de Biotope' }
        ]);
        this.isLoadingTypes.set(false);
      }
    });
  }

  /**
   * Called when polygon geometry changes on the map
   */
  onPolygonChange(geojson: any): void {
    this.polygonGeometry.set(geojson);
  }

  /**
   * Called when point geometry changes on the map
   */
  onPointChange(geojson: any): void {
    this.pointGeometry.set(geojson);
  }

  /**
   * Change the geometry tab
   */
  onGeometryTabChange(index: number): void {
    this.activeGeometryTab.set(index);
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    // Block submission if there's an exact INPN duplicate (in create mode)
    if (!this.isEditMode && this.hasInpnDuplicate) {
      this.errorMessage.set(this.translate.instant('modals.siteForm.errors.inpnDuplicate'));
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const payload: SiteCreatePayload = {
      nom_site: this.form.value.nom_site,
      id_local: this.form.value.id_local || undefined,
      id_inpn: this.form.value.id_inpn || undefined,
      type_site_id: this.form.value.id_type_site || undefined,
      surf_off: this.form.value.surf_off || undefined,
      marin: this.form.value.marin,
      outre_mer: this.form.value.outre_mer,
      active: this.form.value.active,
      // Add geometry data
      geom_geojson: this.polygonGeometry() || undefined,
      geom_pt_geojson: this.pointGeometry() || undefined,
      // Add referent request (only relevant for creation by non-admin)
      request_as_referent: this.form.value.requestAsReferent
    };

    if (this.isEditMode) {
      this.adminService.updateSite(this.data!.site!.slug, payload).subscribe({
        next: (site) => {
          this.isLoading.set(false);
          this.dialogRef.close({ site, validationPending: false });
        },
        error: (error: Error) => {
          this.isLoading.set(false);
          this.errorMessage.set(error.message);
        }
      });
    } else {
      // Create site and optionally link to organisme
      this.adminService.createSite(payload).subscribe({
        next: (response: any) => {
          // Check if validation is pending (response from backend includes this flag)
          const validationPending = response.validation_pending || false;

          // If organismeId is provided, auto-link the site (only if site is active)
          if (this.data?.organismeId && !validationPending) {
            this.adminService.assignSiteToOrganisme(
              this.data.organismeId,
              response.id_site,
              this.data.principal || false
            ).subscribe({
              next: () => {
                this.isLoading.set(false);
                this.dialogRef.close({ site: response, validationPending: false });
              },
              error: (error: Error) => {
                // Site was created but linking failed - still close with site
                this.isLoading.set(false);
                this.errorMessage.set(this.translate.instant('modals.siteForm.messages.linkError', { error: error.message }));
                // Still close after a delay to show the message
                setTimeout(() => this.dialogRef.close({ site: response, validationPending: false }), 2000);
              }
            });
          } else {
            this.isLoading.set(false);
            // Pass validation status along with site data
            this.dialogRef.close({
              site: response,
              validationPending,
              message: response.message
            });
          }
        },
        error: (error: Error) => {
          this.isLoading.set(false);
          this.errorMessage.set(error.message);
        }
      });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
