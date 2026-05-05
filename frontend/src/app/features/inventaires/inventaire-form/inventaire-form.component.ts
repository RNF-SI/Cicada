/**
 * Formulaire Suivi/Inventaire (standalone) - création + édition.
 */
import { Component, OnInit, inject, signal, computed, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormControl, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { debounceTime, distinctUntilChanged, filter, switchMap } from 'rxjs/operators';

import { HeaderComponent } from '../../../shared/components/header/header.component';
import { ReferenceItemListComponent } from '../../../shared/components/reference-item-list/reference-item-list.component';
import { ProtocoleCampanuleDialogComponent } from '../../../shared/components/modals/protocole-campanule-dialog/protocole-campanule-dialog.component';
import { InventaireService } from '../../../core/services/inventaire.service';
import { AdminService } from '../../../core/services/admin.service';
import { CampanuleService } from '../../../core/services/campanule.service';
import { SuiviInventaireDetail, SuiviInventaireCreatePayload } from '../../../core/models/inventaire.model';
import { TaxonRef, HabitatRef, GeologieRef } from '../../../core/models/enjeu.model';
import { CampanuleAutocomplete } from '../../../core/models/campanule.model';

import {
  NomenclatureOption,
  NomenclatureGroup,
  buildNomenclatureGroups,
  getNomenclatureDepth,
  displayNomenclatureFn,
} from '../../../shared/utils/nomenclature-autocomplete.utils';

@Component({
  selector: 'app-inventaire-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatRadioModule,
    MatAutocompleteModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDialogModule,
    MatButtonModule,
    MatDatepickerModule,
    MatNativeDateModule,
    TranslateModule,
    HeaderComponent,
    ReferenceItemListComponent
  ],
  templateUrl: './inventaire-form.component.html',
  styleUrl: './inventaire-form.component.scss'
})
export class InventaireFormComponent implements OnInit {
  private readonly elRef = inject(ElementRef);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly inventaireService = inject(InventaireService);
  private readonly adminService = inject(AdminService);
  private readonly campanuleService = inject(CampanuleService);
  private readonly translate = inject(TranslateService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);

  form!: FormGroup;
  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);

  suiviId = signal<number | null>(null);
  isEditMode = signal(false);
  existingSuivi = signal<SuiviInventaireDetail | null>(null);

  // Nomenclatures
  typeActionCSOptions = signal<NomenclatureOption[]>([]);
  statutSuiviOptions = signal<NomenclatureOption[]>([]);

  // Type d'action CS autocomplete
  typeActionSearchCtrl = new FormControl('');
  typeActionGroups = computed<NomenclatureGroup[]>(() => {
    return this.buildActionGroups(this.typeActionCSOptions(), this.typeActionSearchText());
  });
  typeActionSearchText = signal('');
  selectedTypeAction = signal<NomenclatureOption | null>(null);
  objectifSuiviOptions = signal<NomenclatureOption[]>([]);
  cibleSuiviOptions = signal<NomenclatureOption[]>([]);
  typeIndicateurOptions = signal<NomenclatureOption[]>([]);
  periodeSuiviOptions = signal<NomenclatureOption[]>([]);
  frequenceEmboitementOptions = signal<NomenclatureOption[]>([]);
  bancarisationOptions = signal<NomenclatureOption[]>([]);
  outilSaisieOptions = signal<NomenclatureOption[]>([]);

  // Grouped objectifs for mat-optgroup display
  objectifGroups = computed<NomenclatureGroup[]>(() => {
    return this.buildGroups(this.objectifSuiviOptions());
  });

  // Reference item lists (taxons / habitats)
  taxonItems: TaxonRef[] = [];
  habitatItems: HabitatRef[] = [];

  // Collapsible sections state
  sectionsOpen: Record<string, boolean> = {
    protocole: true,
    bancarisation: true,
    details: true
  };

  // CAMPanule autocomplete
  campanuleSearchCtrl = new FormControl('');
  campanuleResults = signal<CampanuleAutocomplete[]>([]);
  selectedCampanule = signal<CampanuleAutocomplete | null>(null);

  ngOnInit(): void {
    this.initForm();
    this.initTypeActionAutocomplete();
    this.loadNomenclatures();
    this.initCampanuleAutocomplete();
    this.initValidatorsSync();
    this.loadRouteParams();
  }

  /**
   * Subscribe à tous les contrôles dont le changement de valeur peut faire
   * apparaître / disparaître un autre champ requis, pour re-synchroniser les
   * validators conditionnels.
   */
  private initValidatorsSync(): void {
    const watched = [
      'integre_plan_gestion',
      'suit_indicateur',
      'protocole_dans_campanule',
      'frequence_unite',
      'documentation_disponible',
    ];
    for (const name of watched) {
      this.form.get(name)?.valueChanges.subscribe(() => this.syncConditionalValidators());
    }
    // Synchro initiale (form vide → impose les "always required")
    this.syncConditionalValidators();
  }

  /**
   * Met à jour Validators.required sur tous les champs marqués d'un `*` dans
   * le template. Les conditions reflètent les `@if` du HTML pour éviter
   * d'imposer un required sur un champ caché.
   */
  private syncConditionalValidators(): void {
    const v = (name: string) => this.form.get(name)?.value;

    // Toujours requis (champs visibles en haut de formulaire)
    this.applyRequiredValidator('intitule', true);
    this.applyRequiredValidator('integre_plan_gestion', true);
    this.applyRequiredValidator('objectif_principal', true);
    this.applyRequiredValidator('cibles_principales', true);
    this.applyRequiredValidator('date_lancement_suivi', true);
    this.applyRequiredValidator('protocole_dans_campanule', true);

    // Indicateurs (conditionnels)
    this.applyRequiredValidator('suit_indicateur', v('integre_plan_gestion') === true);
    this.applyRequiredValidator(
      'type_indicateur',
      v('integre_plan_gestion') === true && v('suit_indicateur') === true,
    );

    // Protocole : exclusif Oui/Non
    const isCampanule = v('protocole_dans_campanule') === true;
    const isNotCampanule = v('protocole_dans_campanule') === false;
    const protocoleSet = isCampanule || isNotCampanule;

    this.applyRequiredValidator('cd_protocole_campanule', isCampanule);
    this.applyRequiredValidator('nom_protocole', isNotCampanule);
    // Champs visibles dans les 2 modes (dès qu'un mode est choisi)
    this.applyRequiredValidator('frequence_nombre', protocoleSet);
    this.applyRequiredValidator('frequence_unite', protocoleSet);
    this.applyRequiredValidator('respect_protocole', protocoleSet);
    // Champs visibles uniquement en mode hors-CAMPanule
    this.applyRequiredValidator('documentation_disponible', isNotCampanule);
    this.applyRequiredValidator('nb_etp_cycle', isNotCampanule);
  }

  private applyRequiredValidator(controlName: string, required: boolean): void {
    const ctrl = this.form.get(controlName);
    if (!ctrl) return;
    if (required) {
      // Pour intitule on garde maxLength
      if (controlName === 'intitule') {
        ctrl.setValidators([Validators.required, Validators.maxLength(500)]);
      } else {
        ctrl.setValidators([Validators.required]);
      }
    } else {
      if (controlName === 'intitule') {
        ctrl.setValidators([Validators.maxLength(500)]);
      } else {
        ctrl.clearValidators();
      }
    }
    ctrl.updateValueAndValidity({ emitEvent: false });
  }

  private initForm(): void {
    this.form = this.fb.group({
      // Main card
      intitule: ['', [Validators.required, Validators.maxLength(500)]],
      id_type_action: [null],
      integre_plan_gestion: [null],
      suit_indicateur: [null],
      type_indicateur: [''],
      objectif_principal: [''],
      objectif_secondaire: [''],
      cibles_principales: [null],
      cible_secondaire: [''],
      date_lancement_suivi: [null],
      id_statut: [null],
      annee_fin_suivi: [null],
      // Protocole section
      protocole_dans_campanule: [null],
      protocole_campanule_nom: [''],
      cd_protocole_campanule: [null],
      nb_etp_cycle: [null],
      nom_protocole: [''],
      description_protocole: [''],
      objectif_protocole: [''],
      periode_echantillonnage: [''],
      respect_protocole: [null],
      justification_non_respect: [''],
      differences_protocole: [''],
      mode_validation: [''],
      periode_suivi: [[] as string[]],
      documentation_disponible: [null],
      url_documentation: [''],
      frequence_nombre: [null],
      frequence_unite: [''],
      frequence_unite_precision: [''],
      // Bancarisation section
      outil_bancarisation: [''],
      outil_saisie: [''],
      transmission_donnee: [null],
      // Details section
      commentaires: [''],
    });
  }

  // ════════════════════════════════════════════════
  // Type d'action CS autocomplete
  // ════════════════════════════════════════════════

  private initTypeActionAutocomplete(): void {
    this.typeActionSearchCtrl.valueChanges.subscribe((val) => {
      if (typeof val === 'string') {
        this.typeActionSearchText.set(val);
      }
    });
  }

  displayTypeActionFn = displayNomenclatureFn;

  onTypeActionSelected(option: NomenclatureOption): void {
    this.selectedTypeAction.set(option);
    this.form.get('id_type_action')?.setValue(option.id_nomenclature);
  }

  clearTypeAction(): void {
    this.typeActionSearchCtrl.setValue('');
    this.selectedTypeAction.set(null);
    this.form.get('id_type_action')?.setValue(null);
  }

  getActionDepth = getNomenclatureDepth;

  private buildActionGroups(options: NomenclatureOption[], searchText: string): NomenclatureGroup[] {
    return buildNomenclatureGroups(options, searchText);
  }

  private restoreTypeActionAutocomplete(typeActionId: number, options?: NomenclatureOption[]): void {
    const opts = options || this.typeActionCSOptions();
    const match = opts.find(o => o.id_nomenclature === typeActionId);
    if (match) {
      this.selectedTypeAction.set(match);
      this.typeActionSearchCtrl.setValue(this.displayTypeActionFn(match), { emitEvent: false });
    }
  }

  // ════════════════════════════════════════════════
  // CAMPanule autocomplete
  // ════════════════════════════════════════════════

  private initCampanuleAutocomplete(): void {
    this.campanuleSearchCtrl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      filter((val): val is string => typeof val === 'string' && val.length >= 1),
      switchMap((search) => this.campanuleService.autocomplete(search))
    ).subscribe({
      next: (results) => this.campanuleResults.set(results),
      error: () => this.campanuleResults.set([]),
    });
  }

  private loadNomenclatures(): void {
    // Type d'action filtré sur les codes CS (Connaissance et Suivi)
    this.adminService.getNomenclaturesByTypeAndPrefix('TYPE_ACTION', 'CS').subscribe({
      next: (data) => {
        this.typeActionCSOptions.set(data);
        const suivi = this.existingSuivi();
        if (suivi?.id_type_action) {
          this.restoreTypeActionAutocomplete(suivi.id_type_action, data);
        }
      },
    });
    this.adminService.getNomenclaturesByType('STATUT_SUIVI').subscribe({
      next: (data) => this.statutSuiviOptions.set(data),
    });
    this.adminService.getNomenclaturesByType('OBJECTIF_SUIVI').subscribe({
      next: (data) => this.objectifSuiviOptions.set(data),
    });
    this.adminService.getNomenclaturesByType('CIBLE_SUIVI').subscribe({
      next: (data) => this.cibleSuiviOptions.set(data),
    });
    this.adminService.getNomenclaturesByType('TYPE_INDICATEUR').subscribe({
      next: (data) => this.typeIndicateurOptions.set(data),
    });
    this.adminService.getNomenclaturesByType('PERIODE_SUIVI').subscribe({
      next: (data) => this.periodeSuiviOptions.set(data),
    });
    this.adminService.getNomenclaturesByType('FREQUENCE_EMBOITEMENT').subscribe({
      next: (data) => this.frequenceEmboitementOptions.set(data),
    });
    this.adminService.getNomenclaturesByType('BANCARISATION_STOCKAGE').subscribe({
      next: (data) => this.bancarisationOptions.set(data),
    });
    this.adminService.getNomenclaturesByType('OUTIL_SAISIE').subscribe({
      next: (data) => this.outilSaisieOptions.set(data),
    });
  }

  /** Build grouped nomenclature structure from flat options using definition field */
  private buildGroups(options: NomenclatureOption[]): NomenclatureGroup[] {
    const groups: NomenclatureGroup[] = [];
    const groupMap = new Map<string, NomenclatureOption[]>();

    for (const opt of options) {
      const groupKey = opt.definition || '';
      if (!groupMap.has(groupKey)) {
        groupMap.set(groupKey, []);
      }
      groupMap.get(groupKey)!.push(opt);
    }

    for (const [groupLabel, opts] of groupMap) {
      groups.push({ groupLabel, options: opts });
    }
    return groups;
  }

  /** Check if selected cible requires taxref display */
  get showTaxref(): boolean {
    const cible = this.form.get('cibles_principales')?.value;
    return cible === 'ESPECES';
  }

  /** Check if selected cible requires habitat display */
  get showHabitat(): boolean {
    const cible = this.form.get('cibles_principales')?.value;
    return cible === 'HABITATS_VEGETATIONS';
  }

  /** Show suit_indicateur when integre_plan_gestion == true */
  get showSuitIndicateur(): boolean {
    return this.form.get('integre_plan_gestion')?.value === true;
  }

  /** Show type_indicateur when suit_indicateur == true */
  get showTypeIndicateur(): boolean {
    return this.showSuitIndicateur && this.form.get('suit_indicateur')?.value === true;
  }

  /** Get display label for selected objectif: "Groupe - Label" */
  getObjectifDisplayLabel(mnemonique: string): string {
    if (!mnemonique) return '';
    const opt = this.objectifSuiviOptions().find(o => o.mnemonique === mnemonique);
    if (!opt) return mnemonique;
    return opt.definition ? `${opt.definition} - ${opt.label}` : opt.label;
  }

  /** Check if objectif principal is set (to show objectif secondaire) */
  get hasObjectifPrincipal(): boolean {
    return !!this.form.get('objectif_principal')?.value;
  }

  /** Check if cible principale is set (to show cible secondaire) */
  get hasCiblePrincipale(): boolean {
    return !!this.form.get('cibles_principales')?.value;
  }

  /** Show documentation URL when documentation_disponible == true */
  get showDocumentationUrl(): boolean {
    return this.form.get('documentation_disponible')?.value === true;
  }

  /** Show frequency precision field when frequence_unite == 'AUTRE' */
  get showFrequencePrecision(): boolean {
    return this.form.get('frequence_unite')?.value === 'AUTRE';
  }

  private loadRouteParams(): void {
    const suiviIdStr = this.route.snapshot.paramMap.get('suiviId');
    if (suiviIdStr) {
      const id = parseInt(suiviIdStr, 10);
      if (!isNaN(id)) {
        this.suiviId.set(id);
        this.isEditMode.set(true);
        this.loadSuivi(id);
        return;
      }
    }
    this.isLoadingData.set(false);
  }

  private loadSuivi(id: number): void {
    this.inventaireService.getInventaire(id).subscribe({
      next: (suivi) => {
        this.existingSuivi.set(suivi);
        this.populateForm(suivi);
        this.isLoadingData.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('inventaires.errors.loadFailed'));
        this.isLoadingData.set(false);
      }
    });
  }

  private populateForm(suivi: SuiviInventaireDetail): void {
    // Parse taxon references from stored string
    if (suivi.taxon_taxref) {
      this.taxonItems = suivi.taxon_taxref.split(',').map(s => s.trim()).filter(s => s).map(name => ({
        cd_nom: 0,
        nom_complet: name,
      }));
    }
    // Parse habitat references from stored string
    if (suivi.habitat_ref) {
      this.habitatItems = suivi.habitat_ref.split(',').map(s => s.trim()).filter(s => s).map(name => ({
        cd_hab: '',
        lb_hab_fr: name,
      }));
    }

    this.form.patchValue({
      intitule: suivi.intitule || '',
      integre_plan_gestion: suivi.integre_plan_gestion,
      suit_indicateur: suivi.suit_indicateur ?? null,
      type_indicateur: suivi.type_indicateur || '',
      objectif_principal: suivi.objectif_principal || '',
      objectif_secondaire: suivi.objectif_secondaire || '',
      cibles_principales: suivi.cibles_principales || '',
      cible_secondaire: suivi.cible_secondaire || '',
      date_lancement_suivi: suivi.date_lancement_suivi ? new Date(suivi.date_lancement_suivi) : null,
      id_statut: suivi.id_statut,
      annee_fin_suivi: suivi.annee_fin_suivi,
      // Frequency
      frequence_nombre: suivi.frequence_nombre,
      frequence_unite: suivi.frequence_unite || '',
      frequence_unite_precision: suivi.frequence_unite_precision || '',
      // Bancarisation
      outil_bancarisation: suivi.outil_bancarisation || '',
      outil_saisie: suivi.outil_saisie || '',
      transmission_donnee: suivi.transmission_donnee,
      // Details
      commentaires: suivi.commentaires || '',
    });

    // Populate protocole fields
    if (suivi.protocole) {
      const p = suivi.protocole;
      this.form.patchValue({
        protocole_dans_campanule: p.protocole_dans_campanule,
        protocole_campanule_nom: p.protocole_campanule_nom || '',
        cd_protocole_campanule: p.cd_protocole_campanule,
        nb_etp_cycle: p.nb_etp_cycle,
        nom_protocole: p.nom_protocole || '',
        description_protocole: p.description_protocole || '',
        objectif_protocole: p.objectif_protocole || '',
        periode_echantillonnage: p.periode_echantillonnage || '',
        respect_protocole: p.respect_protocole,
        justification_non_respect: p.justification_non_respect || '',
        differences_protocole: p.differences_protocole || '',
        mode_validation: p.mode_validation || '',
        periode_suivi: p.periode_suivi ? p.periode_suivi.split(',').map(s => s.trim()).filter(Boolean) : [],
        documentation_disponible: p.documentation_disponible ?? null,
        url_documentation: p.url_documentation || '',
      });

      // Restore autocomplete display if Campanule was selected
      if (p.protocole_dans_campanule && p.protocole_campanule_nom) {
        this.campanuleSearchCtrl.setValue(p.protocole_campanule_nom, { emitEvent: false });
        if (p.cd_protocole_campanule) {
          this.selectedCampanule.set({
            cd_protocole: p.cd_protocole_campanule,
            search_name: p.protocole_campanule_nom,
            lb_protocole_court: p.protocole_campanule_nom,
          });
        }
      }
    }

    // Réajuster les validators d'après l'état chargé (sinon les conditionnels
    // sur protocole_dans_campanule, suit_indicateur, etc., ne sont pas posés).
    this.syncConditionalValidators();
  }

  toggleSection(section: string): void {
    this.sectionsOpen[section] = !this.sectionsOpen[section];
  }

  incrementFrequence(delta: number): void {
    const current = this.form.get('frequence_nombre')?.value || 0;
    const newVal = Math.max(0, current + delta);
    this.form.patchValue({ frequence_nombre: newVal || null });
  }

  onTaxonsChange(items: (TaxonRef | HabitatRef | GeologieRef)[]): void {
    this.taxonItems = items as TaxonRef[];
  }

  onHabitatsChange(items: (TaxonRef | HabitatRef | GeologieRef)[]): void {
    this.habitatItems = items as HabitatRef[];
  }

  // ─── CAMPanule autocomplete ──────────────────────────────────

  displayCampanuleFn(option: CampanuleAutocomplete | string): string {
    if (!option) return '';
    if (typeof option === 'string') return option;
    return option.lb_protocole_court || '';
  }

  onCampanuleSelected(event: any): void {
    const selected: CampanuleAutocomplete = event.option.value;
    this.selectedCampanule.set(selected);
    this.campanuleSearchCtrl.setValue(selected.lb_protocole_court, { emitEvent: false });

    // Auto-fill form fields from Campanule reference data
    this.form.patchValue({
      protocole_campanule_nom: selected.lb_protocole_court,
      cd_protocole_campanule: selected.cd_protocole,
    });

    // Fetch full protocol details to populate description/objectif/période
    this.campanuleService.getProtocole(selected.cd_protocole).subscribe({
      next: (detail) => {
        this.form.patchValue({
          description_protocole: detail.description || '',
          objectif_protocole: detail.descr_objectif_prot || '',
        });
        // Build période from échantillonnage data
        if (detail.echantillonnages && detail.echantillonnages.length > 0) {
          const periodes = detail.echantillonnages
            .filter(e => e.periode_an)
            .map(e => e.periode_an)
            .join('; ');
          if (periodes) {
            this.form.patchValue({ periode_echantillonnage: periodes });
          }
        }
      },
    });
  }

  onCampanuleReset(): void {
    this.selectedCampanule.set(null);
    this.campanuleSearchCtrl.setValue('');
    this.form.patchValue({
      protocole_campanule_nom: '',
      cd_protocole_campanule: null,
      description_protocole: '',
      objectif_protocole: '',
      periode_echantillonnage: '',
    });
  }

  consulterProtocole(): void {
    const cdProtocole = this.form.get('cd_protocole_campanule')?.value;
    if (!cdProtocole) return;

    this.dialog.open(ProtocoleCampanuleDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { cdProtocole },
    });
  }

  get isCampanule(): boolean {
    return this.form.get('protocole_dans_campanule')?.value === true;
  }

  get isNotCampanule(): boolean {
    return this.form.get('protocole_dans_campanule')?.value === false;
  }

  get isNonRespect(): boolean {
    return this.form.get('respect_protocole')?.value === false;
  }

  get hasCampanuleSelected(): boolean {
    return !!this.form.get('cd_protocole_campanule')?.value;
  }

  /** Format date to ISO string (YYYY-MM-DD) for backend */
  private formatDate(date: Date | string | null): string | undefined {
    if (!date) return undefined;
    if (typeof date === 'string') return date;
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  cancel(): void {
    if (this.isEditMode() && this.suiviId()) {
      this.router.navigate(['/inventaires', this.suiviId()]);
    } else {
      this.router.navigate(['/inventaires']);
    }
  }

  /** Tableau (formControlName → clé i18n du label) pour les messages d'erreur. */
  private readonly fieldLabelKeys: Record<string, string> = {
    intitule: 'inventaires.form.intitule',
    integre_plan_gestion: 'inventaires.form.integrePG',
    suit_indicateur: 'inventaires.form.suitIndicateur',
    type_indicateur: 'inventaires.form.typeIndicateur',
    objectif_principal: 'inventaires.form.objectifPrincipal',
    cibles_principales: 'inventaires.form.ciblesPrincipales',
    date_lancement_suivi: 'inventaires.form.dateLancement',
    protocole_dans_campanule: 'inventaires.form.protocoleCampanule',
    cd_protocole_campanule: 'inventaires.form.protocoleCampanuleNom',
    nom_protocole: 'inventaires.form.nomProtocole',
    frequence_nombre: 'inventaires.form.frequence',
    frequence_unite: 'inventaires.form.frequence',
    respect_protocole: 'inventaires.form.respectProtocole',
    documentation_disponible: 'inventaires.form.documentationDisponible',
    nb_etp_cycle: 'inventaires.form.nbEtpCycle',
  };

  private showValidationErrorMessage(): void {
    const labels = new Set<string>();
    for (const [name, control] of Object.entries(this.form.controls)) {
      if (control.invalid && this.fieldLabelKeys[name]) {
        labels.add(this.translate.instant(this.fieldLabelKeys[name]));
      }
    }
    const list = Array.from(labels);
    if (list.length > 0) {
      this.errorMessage.set(
        this.translate.instant('inventaires.errors.validationFailedWithFields', {
          fields: list.join(', '),
        }),
      );
    } else {
      this.errorMessage.set(this.translate.instant('inventaires.errors.validationFailed'));
    }
  }

  private scrollToError(): void {
    setTimeout(() => {
      const banner = this.elRef.nativeElement.querySelector('.error-banner');
      if (banner) {
        banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      const candidates = this.elRef.nativeElement.querySelectorAll(
        'mat-form-field.ng-invalid, mat-radio-group.ng-invalid, mat-select.ng-invalid, .ng-invalid:not(form):not(mat-form-field):not(mat-radio-group):not(mat-select)',
      ) as NodeListOf<HTMLElement>;
      for (const el of Array.from(candidates)) {
        if (el.tagName === 'FORM') continue;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        const focusable = el.querySelector('input, textarea, [tabindex]:not([tabindex="-1"])') as HTMLElement | null;
        focusable?.focus({ preventScroll: true });
        return;
      }
    });
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.showValidationErrorMessage();
      this.scrollToError();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const fv = this.form.value;

    const payload: SuiviInventaireCreatePayload = {
      intitule: fv.intitule,
      id_type_action: fv.id_type_action,
    };

    // Main fields
    if (fv.integre_plan_gestion != null) payload.integre_plan_gestion = fv.integre_plan_gestion;
    if (fv.integre_plan_gestion === true && fv.suit_indicateur != null) payload.suit_indicateur = fv.suit_indicateur;
    if (fv.integre_plan_gestion === true && fv.suit_indicateur === true && fv.type_indicateur?.trim()) {
      payload.type_indicateur = fv.type_indicateur.trim();
    }
    if (fv.objectif_principal?.trim()) payload.objectif_principal = fv.objectif_principal.trim();
    if (fv.objectif_secondaire?.trim()) payload.objectif_secondaire = fv.objectif_secondaire.trim();
    if (fv.cibles_principales) payload.cibles_principales = fv.cibles_principales;
    if (fv.cible_secondaire) payload.cible_secondaire = fv.cible_secondaire;
    // Serialize taxon/habitat reference lists to strings
    if (this.taxonItems.length > 0) {
      payload.taxon_taxref = this.taxonItems.map(t => t.nom_complet || String(t.cd_nom)).join(', ');
    }
    if (this.habitatItems.length > 0) {
      payload.habitat_ref = this.habitatItems.map(h => h.lb_hab_fr || h.cd_hab).join(', ');
    }
    const dateLancement = this.formatDate(fv.date_lancement_suivi);
    if (dateLancement) payload.date_lancement_suivi = dateLancement;
    if (fv.id_statut) payload.id_statut = fv.id_statut;
    if (fv.annee_fin_suivi != null) payload.annee_fin_suivi = fv.annee_fin_suivi;

    // Frequency (on SuiviInventaire, displayed in protocole section)
    if (fv.frequence_nombre != null) payload.frequence_nombre = fv.frequence_nombre;
    if (fv.frequence_unite) payload.frequence_unite = fv.frequence_unite;
    if (fv.frequence_unite === 'AUTRE' && fv.frequence_unite_precision?.trim()) {
      payload.frequence_unite_precision = fv.frequence_unite_precision.trim();
    }

    // Bancarisation
    if (fv.outil_bancarisation?.trim()) payload.outil_bancarisation = fv.outil_bancarisation.trim();
    if (fv.outil_saisie?.trim()) payload.outil_saisie = fv.outil_saisie.trim();
    if (fv.transmission_donnee != null) payload.transmission_donnee = fv.transmission_donnee;

    // Details
    if (fv.commentaires?.trim()) payload.commentaires = fv.commentaires.trim();

    // Build nested protocole
    const protocoleData: Record<string, unknown> = {};
    if (fv.protocole_dans_campanule != null) protocoleData['protocole_dans_campanule'] = fv.protocole_dans_campanule;
    if (fv.protocole_campanule_nom?.trim()) protocoleData['protocole_campanule_nom'] = fv.protocole_campanule_nom.trim();
    if (fv.cd_protocole_campanule != null) protocoleData['cd_protocole_campanule'] = fv.cd_protocole_campanule;
    if (fv.nb_etp_cycle != null) protocoleData['nb_etp_cycle'] = fv.nb_etp_cycle;
    if (fv.nom_protocole?.trim()) protocoleData['nom_protocole'] = fv.nom_protocole.trim();
    if (fv.description_protocole?.trim()) protocoleData['description_protocole'] = fv.description_protocole.trim();
    if (fv.objectif_protocole?.trim()) protocoleData['objectif_protocole'] = fv.objectif_protocole.trim();
    if (fv.periode_echantillonnage?.trim()) protocoleData['periode_echantillonnage'] = fv.periode_echantillonnage.trim();
    if (fv.respect_protocole != null) protocoleData['respect_protocole'] = fv.respect_protocole;
    if (fv.justification_non_respect?.trim()) protocoleData['justification_non_respect'] = fv.justification_non_respect.trim();
    if (fv.differences_protocole?.trim()) protocoleData['differences_protocole'] = fv.differences_protocole.trim();
    if (fv.mode_validation?.trim()) protocoleData['mode_validation'] = fv.mode_validation.trim();
    if (Array.isArray(fv.periode_suivi) && fv.periode_suivi.length > 0) {
      protocoleData['periode_suivi'] = fv.periode_suivi.join(',');
    } else if (typeof fv.periode_suivi === 'string' && fv.periode_suivi) {
      // Rétrocompat si jamais on reçoit une string
      protocoleData['periode_suivi'] = fv.periode_suivi;
    }
    if (fv.documentation_disponible != null) protocoleData['documentation_disponible'] = fv.documentation_disponible;
    if (fv.documentation_disponible === true && fv.url_documentation?.trim()) {
      protocoleData['url_documentation'] = fv.url_documentation.trim();
    }

    if (Object.keys(protocoleData).length > 0) {
      payload.protocole = protocoleData;
    }

    const request$ = this.isEditMode()
      ? this.inventaireService.updateInventaire(this.suiviId()!, payload)
      : this.inventaireService.createInventaire(payload);

    request$.subscribe({
      next: (result) => {
        this.isLoading.set(false);
        const msgKey = this.isEditMode()
          ? 'inventaires.messages.updateSuccess'
          : 'inventaires.messages.createSuccess';
        this.snackBar.open(
          this.translate.instant(msgKey),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        // Navigate to detail page after save
        const id = result?.id_suivi_inventaire || this.suiviId();
        if (id) {
          this.router.navigate(['/inventaires', id]);
        } else {
          this.router.navigate(['/inventaires']);
        }
      },
      error: () => {
        this.isLoading.set(false);
        this.errorMessage.set(
          this.translate.instant('inventaires.errors.saveFailed')
        );
      }
    });
  }
}
