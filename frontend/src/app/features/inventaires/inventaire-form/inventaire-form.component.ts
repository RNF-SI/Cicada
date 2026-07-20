/**
 * Formulaire Suivi/Inventaire (standalone) - création + édition.
 */
import { Component, OnInit, inject, signal, computed, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { AbstractControl, FormArray, FormBuilder, FormControl, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
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
import { AccordionComponent } from '../../../shared/components/accordion/accordion.component';
import { FormFieldComponent } from '../../../shared/components/form-field/form-field.component';
import { ProtocoleCampanuleDialogComponent } from '../../../shared/components/modals/protocole-campanule-dialog/protocole-campanule-dialog.component';
import { InventaireService } from '../../../core/services/inventaire.service';
import { AdminService } from '../../../core/services/admin.service';
import { CampanuleService } from '../../../core/services/campanule.service';
import { SuiviInventaireDetail, SuiviInventaireCreatePayload } from '../../../core/models/inventaire.model';
import { TaxonRef, HabitatRef, GeologieRef } from '../../../core/models/enjeu.model';
import { CampanuleAutocomplete, campanuleProtocoleLabel } from '../../../core/models/campanule.model';

import {
  NomenclatureOption,
  NomenclatureGroup,
  buildNomenclatureGroups,
  getNomenclatureDepth,
  displayNomenclatureFn,
} from '../../../shared/utils/nomenclature-autocomplete.utils';
import { serializeTaxonRefs, parseTaxonRefs } from '../../../shared/utils/taxon-ref.utils';

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
    ReferenceItemListComponent,
    AccordionComponent,
    FormFieldComponent,
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

  // CAMPanule autocomplete — un état par protocole (#252)
  campanuleSearchCtrls: FormControl[] = [];
  campanuleResults = signal<CampanuleAutocomplete[][]>([]);
  selectedCampanules = signal<(CampanuleAutocomplete | null)[]>([]);
  private campanuleSubs: Subscription[] = [];

  ngOnInit(): void {
    this.initForm();
    this.initTypeActionAutocomplete();
    this.loadNomenclatures();
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
      'frequence_unite',
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

    // Indicateurs (conditionnels)
    this.applyRequiredValidator('suit_indicateur', v('integre_plan_gestion') === true);
    this.applyRequiredValidator(
      'type_indicateur',
      v('integre_plan_gestion') === true && v('suit_indicateur') === true,
    );

    // Chaque protocole porte ses propres validators conditionnels (#252).
    let auMoinsUnProtocoleRenseigne = false;
    for (const group of this.protocolesArray.controls) {
      const gv = (name: string) => group.get(name)?.value;
      const isCampanule = gv('protocole_dans_campanule') === true;
      const isNotCampanule = gv('protocole_dans_campanule') === false;
      if (isCampanule || isNotCampanule) auMoinsUnProtocoleRenseigne = true;

      this.setRequired(group.get('protocole_dans_campanule'), true);
      this.setRequired(group.get('cd_protocole_campanule'), isCampanule);
      // #413 — le nom d'un protocole non-CAMPanule (nom local) est facultatif.
      this.setRequired(group.get('nom_protocole'), false);
      // #414 — « Respect strict du protocole » réservé aux protocoles CAMPanule.
      this.setRequired(group.get('respect_protocole'), isCampanule);
      // Champs visibles uniquement en mode hors-CAMPanule
      this.setRequired(group.get('documentation_disponible'), isNotCampanule);
      this.setRequired(group.get('nb_etp_cycle'), isNotCampanule);
    }

    // La fréquence est portée par le suivi : requise dès qu'un protocole est
    // renseigné, quel qu'il soit.
    this.applyRequiredValidator('frequence_nombre', auMoinsUnProtocoleRenseigne);
    this.applyRequiredValidator('frequence_unite', auMoinsUnProtocoleRenseigne);
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

  private setRequired(ctrl: AbstractControl | null, required: boolean): void {
    if (!ctrl) return;
    if (required) {
      ctrl.setValidators([Validators.required]);
    } else {
      ctrl.clearValidators();
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
      // Protocoles (#252 — un suivi peut en mobiliser plusieurs)
      protocoles: this.fb.array([]),
      // Fréquence : portée par le suivi, pas par le protocole, mais affichée
      // dans la section protocole.
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

    // Un formulaire vierge démarre avec un protocole (cas très majoritaire).
    this.addProtocole();
  }

  // ════════════════════════════════════════════════
  // Protocoles (FormArray) — #252
  // ════════════════════════════════════════════════

  get protocolesArray(): FormArray<FormGroup> {
    return this.form.get('protocoles') as FormArray<FormGroup>;
  }

  /** Nombre de protocoles au-delà duquel on affiche une mention d'ergonomie. */
  private readonly protocolesSoftLimit = 3;

  get showProtocolesSoftLimitHint(): boolean {
    return this.protocolesArray.length > this.protocolesSoftLimit;
  }

  private createProtocoleGroup(): FormGroup {
    return this.fb.group({
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
    });
  }

  /**
   * Ajoute un protocole vide et lui attache son propre état d'autocomplete
   * CAMPanule (chaque ligne a sa recherche et sa sélection indépendantes).
   */
  addProtocole(): void {
    const group = this.createProtocoleGroup();
    this.protocolesArray.push(group);

    const searchCtrl = new FormControl('');
    this.campanuleSearchCtrls.push(searchCtrl);
    this.campanuleResults.update((all) => [...all, []]);
    this.selectedCampanules.update((all) => [...all, null]);
    this.bindCampanuleAutocomplete(searchCtrl, this.campanuleSearchCtrls.length - 1);

    // Le nouveau groupe doit recevoir ses validators conditionnels.
    group.valueChanges.subscribe(() => this.syncConditionalValidators());
    this.syncConditionalValidators();
  }

  /** Retire un protocole (le dernier restant n'est pas supprimable). */
  removeProtocole(index: number): void {
    if (this.protocolesArray.length <= 1) return;
    this.protocolesArray.removeAt(index);
    this.campanuleSearchCtrls.splice(index, 1);
    this.campanuleResults.update((all) => all.filter((_, i) => i !== index));
    this.selectedCampanules.update((all) => all.filter((_, i) => i !== index));
    // Les souscriptions restantes portent un index devenu faux : on rebranche.
    this.rebindCampanuleAutocompletes();
    this.syncConditionalValidators();
  }

  protocoleGroup(index: number): FormGroup {
    return this.protocolesArray.at(index);
  }

  /** Vide le FormArray et le reconstruit avec `count` blocs vierges. */
  private resetProtocoles(count: number): void {
    this.protocolesArray.clear();
    this.campanuleSearchCtrls = [];
    this.campanuleResults.set([]);
    this.selectedCampanules.set([]);
    this.campanuleSubs.forEach((sub) => sub.unsubscribe());
    this.campanuleSubs = [];
    for (let i = 0; i < count; i++) {
      this.addProtocole();
    }
  }

  /** Titre affiché dans l'en-tête d'un bloc protocole. */
  protocoleTitle(index: number): string {
    const group = this.protocolesArray.at(index);
    const nom =
      group?.get('protocole_campanule_nom')?.value?.trim() ||
      group?.get('nom_protocole')?.value?.trim();
    const defaut = this.translate.instant('inventaires.form.protocoleIndex', { index: index + 1 });
    return nom || defaut;
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

  /** (Re)branche les souscriptions d'autocomplete sur les index courants. */
  private rebindCampanuleAutocompletes(): void {
    this.campanuleSubs.forEach((sub) => sub.unsubscribe());
    this.campanuleSubs = [];
    this.campanuleSearchCtrls.forEach((ctrl, index) =>
      this.bindCampanuleAutocomplete(ctrl, index),
    );
  }

  /** #584 — nombre de protocoles proposés quand aucun terme n'est saisi. */
  private static readonly CAMPANULE_DEFAULT_LIMIT = 100;

  /**
   * #584 — Au clic dans le champ, on affiche d'emblée les protocoles par ordre
   * alphabétique plutôt qu'une liste vide en attente de saisie.
   */
  onCampanuleFocus(index: number): void {
    const search = this.campanuleSearchCtrls[index]?.value;
    if (typeof search === 'string' && search.length > 0) return;
    if (this.campanuleResultsAt(index).length > 0) return;

    this.campanuleService
      .autocomplete('', InventaireFormComponent.CAMPANULE_DEFAULT_LIMIT)
      .subscribe({
        next: (results) => this.setCampanuleResults(index, results),
        error: () => this.setCampanuleResults(index, []),
      });
  }

  private bindCampanuleAutocomplete(searchCtrl: FormControl, index: number): void {
    this.campanuleSubs.push(
      searchCtrl.valueChanges.pipe(
        debounceTime(300),
        distinctUntilChanged(),
        // Une chaîne vide est acceptée : elle recharge la liste alphabétique (#584).
        filter((val): val is string => typeof val === 'string'),
        switchMap((search) => this.campanuleService.autocomplete(
          search,
          search ? 20 : InventaireFormComponent.CAMPANULE_DEFAULT_LIMIT,
        ))
      ).subscribe({
        next: (results) => this.setCampanuleResults(index, results),
        error: () => this.setCampanuleResults(index, []),
      })
    );

    // Si l'utilisateur édite le texte après une sélection, on invalide la
    // sélection — sinon le formulaire conserverait un cd_protocole qui ne
    // correspond plus à ce qui est affiché.
    this.campanuleSubs.push(
      searchCtrl.valueChanges.subscribe((val) => {
        if (typeof val !== 'string') return; // option object → géré par onCampanuleSelected
        const selected = this.selectedCampanules()[index];
        if (selected && val !== selected.lb_protocole_court) {
          this.setSelectedCampanule(index, null);
          this.protocolesArray.at(index)?.patchValue({
            protocole_campanule_nom: '',
            cd_protocole_campanule: null,
            description_protocole: '',
            objectif_protocole: '',
            periode_echantillonnage: '',
          });
        }
      })
    );
  }

  private setCampanuleResults(index: number, results: CampanuleAutocomplete[]): void {
    this.campanuleResults.update((all) => all.map((r, i) => (i === index ? results : r)));
  }

  private setSelectedCampanule(index: number, value: CampanuleAutocomplete | null): void {
    this.selectedCampanules.update((all) => all.map((s, i) => (i === index ? value : s)));
  }

  campanuleResultsAt(index: number): CampanuleAutocomplete[] {
    return this.campanuleResults()[index] || [];
  }

  selectedCampanuleAt(index: number): CampanuleAutocomplete | null {
    return this.selectedCampanules()[index] || null;
  }

  /**
   * Au blur du champ CAMPanule, on force la cohérence : si du texte a été
   * saisi mais qu'aucun protocole n'a été sélectionné dans la liste, on vide
   * le champ — l'utilisateur doit obligatoirement choisir une option.
   */
  onCampanuleBlur(index: number): void {
    const ctrl = this.campanuleSearchCtrls[index];
    const val = ctrl?.value;
    const selected = this.selectedCampanuleAt(index);
    if (typeof val === 'string' && val.trim() && !selected) {
      ctrl.setValue('', { emitEvent: false });
      this.setCampanuleResults(index, []);
    }
    // Marque le contrôle requis comme touched pour afficher l'erreur si besoin.
    this.protocolesArray.at(index)?.get('cd_protocole_campanule')?.markAsTouched();
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
  showDocumentationUrl(index: number): boolean {
    return this.protocolesArray.at(index)?.get('documentation_disponible')?.value === true;
  }

  /** Au moins un protocole a un mode (CAMPanule ou non) choisi. */
  get hasAnyProtocoleRenseigne(): boolean {
    return this.protocolesArray.controls.some((g) => {
      const v = g.get('protocole_dans_campanule')?.value;
      return v === true || v === false;
    });
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
    // Parse taxon references from stored string (JSON avec cd_nom, cf. #563)
    if (suivi.taxon_taxref) {
      this.taxonItems = parseTaxonRefs(suivi.taxon_taxref);
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

    // Populate protocoles (#252) — `protocole` singulier conservé en repli pour
    // les réponses d'API antérieures.
    const protocoles = suivi.protocoles?.length
      ? suivi.protocoles
      : (suivi.protocole ? [suivi.protocole] : []);

    if (protocoles.length > 0) {
      this.resetProtocoles(protocoles.length);

      protocoles.forEach((p, index) => {
        this.protocolesArray.at(index).patchValue({
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
          this.campanuleSearchCtrls[index]?.setValue(p.protocole_campanule_nom, { emitEvent: false });
          if (p.cd_protocole_campanule) {
            this.setSelectedCampanule(index, {
              cd_protocole: p.cd_protocole_campanule,
              search_name: p.protocole_campanule_nom,
              lb_protocole_court: p.protocole_campanule_nom,
            });
          }
        }
      });
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

  /** Libellé d'affichage d'un protocole (nom court, sinon nom complet). #564 */
  campanuleLabel(option: CampanuleAutocomplete): string {
    return campanuleProtocoleLabel(option);
  }

  displayCampanuleFn(option: CampanuleAutocomplete | string): string {
    if (!option) return '';
    if (typeof option === 'string') return option;
    return campanuleProtocoleLabel(option);
  }

  onCampanuleSelected(event: any, index: number): void {
    const selected: CampanuleAutocomplete = event.option.value;
    const group = this.protocolesArray.at(index);
    if (!group) return;

    this.setSelectedCampanule(index, selected);
    this.campanuleSearchCtrls[index]?.setValue(campanuleProtocoleLabel(selected), { emitEvent: false });

    // Auto-fill form fields from Campanule reference data
    group.patchValue({
      protocole_campanule_nom: campanuleProtocoleLabel(selected),
      cd_protocole_campanule: selected.cd_protocole,
    });

    // Fetch full protocol details to populate description/objectif/période
    this.campanuleService.getProtocole(selected.cd_protocole).subscribe({
      next: (detail) => {
        group.patchValue({
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
            group.patchValue({ periode_echantillonnage: periodes });
          }
        }
      },
    });
  }

  onCampanuleReset(index: number): void {
    this.setSelectedCampanule(index, null);
    this.campanuleSearchCtrls[index]?.setValue('');
    this.protocolesArray.at(index)?.patchValue({
      protocole_campanule_nom: '',
      cd_protocole_campanule: null,
      description_protocole: '',
      objectif_protocole: '',
      periode_echantillonnage: '',
    });
  }

  consulterProtocole(index: number): void {
    const cdProtocole = this.protocolesArray.at(index)?.get('cd_protocole_campanule')?.value;
    if (!cdProtocole) return;

    this.dialog.open(ProtocoleCampanuleDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { cdProtocole },
    });
  }

  isCampanule(index: number): boolean {
    return this.protocolesArray.at(index)?.get('protocole_dans_campanule')?.value === true;
  }

  isNotCampanule(index: number): boolean {
    return this.protocolesArray.at(index)?.get('protocole_dans_campanule')?.value === false;
  }

  isNonRespect(index: number): boolean {
    return this.protocolesArray.at(index)?.get('respect_protocole')?.value === false;
  }

  hasCampanuleSelected(index: number): boolean {
    return !!this.protocolesArray.at(index)?.get('cd_protocole_campanule')?.value;
  }

  /** Erreur d'un contrôle d'un bloc protocole (équivalent indexé de shouldShowError). */
  shouldShowProtocoleError(index: number, controlName: string): boolean {
    const ctrl = this.protocolesArray.at(index)?.get(controlName);
    if (!ctrl) return false;
    return ctrl.invalid && (ctrl.touched || ctrl.dirty);
  }

  getProtocoleErrorMessage(index: number, controlName: string): string | null {
    const ctrl = this.protocolesArray.at(index)?.get(controlName);
    if (!ctrl || !ctrl.errors) return null;
    if (ctrl.errors['required']) {
      return this.translate.instant('common.validation.required');
    }
    return null;
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

  /**
   * Faut-il afficher une erreur pour ce contrôle ? `touched` (et `dirty` au cas
   * où le contrôle n'a pas reçu de blur — datepicker, selects natifs, etc.).
   */
  shouldShowError(controlName: string): boolean {
    const ctrl = this.form.get(controlName);
    if (!ctrl) return false;
    return ctrl.invalid && (ctrl.touched || ctrl.dirty);
  }

  /**
   * Message d'erreur traduit pour ce contrôle, ou null s'il n'y en a pas.
   * Utilisé par les `<mat-error>` et les messages des champs custom (radios,
   * fréquence, autocomplete CAMPanule).
   */
  getErrorMessage(controlName: string): string | null {
    const ctrl = this.form.get(controlName);
    if (!ctrl || !ctrl.errors) return null;
    if (ctrl.errors['required']) {
      return this.translate.instant('common.validation.required');
    }
    if (ctrl.errors['maxlength']) {
      return this.translate.instant('common.validation.maxLength', {
        max: ctrl.errors['maxlength'].requiredLength,
      });
    }
    return null;
  }

  private showValidationErrorMessage(): void {
    const labels = new Set<string>();
    for (const [name, control] of Object.entries(this.form.controls)) {
      if (control.invalid && this.fieldLabelKeys[name]) {
        labels.add(this.translate.instant(this.fieldLabelKeys[name]));
      }
    }
    // Les champs protocole vivent dans un FormArray : on les parcourt à part (#252).
    for (const group of this.protocolesArray.controls) {
      for (const [name, control] of Object.entries(group.controls)) {
        if (control.invalid && this.fieldLabelKeys[name]) {
          labels.add(this.translate.instant(this.fieldLabelKeys[name]));
        }
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
      // Priorité au premier contrôle invalide : c'est là que l'utilisateur doit corriger.
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
      // Fallback : bannière (cas erreur backend sans contrôle invalide).
      const banner = this.elRef.nativeElement.querySelector('.error-banner');
      banner?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }

  /** Sérialise un bloc protocole du FormArray vers le format attendu par l'API. */
  private buildProtocolePayload(pv: Record<string, any>): Record<string, unknown> {
    const data: Record<string, unknown> = {};
    if (pv['protocole_dans_campanule'] != null) data['protocole_dans_campanule'] = pv['protocole_dans_campanule'];
    if (pv['protocole_campanule_nom']?.trim()) data['protocole_campanule_nom'] = pv['protocole_campanule_nom'].trim();
    if (pv['cd_protocole_campanule'] != null) data['cd_protocole_campanule'] = pv['cd_protocole_campanule'];
    if (pv['nb_etp_cycle'] != null) data['nb_etp_cycle'] = pv['nb_etp_cycle'];
    if (pv['nom_protocole']?.trim()) data['nom_protocole'] = pv['nom_protocole'].trim();
    if (pv['description_protocole']?.trim()) data['description_protocole'] = pv['description_protocole'].trim();
    if (pv['objectif_protocole']?.trim()) data['objectif_protocole'] = pv['objectif_protocole'].trim();
    if (pv['periode_echantillonnage']?.trim()) data['periode_echantillonnage'] = pv['periode_echantillonnage'].trim();
    if (pv['respect_protocole'] != null) data['respect_protocole'] = pv['respect_protocole'];
    if (pv['justification_non_respect']?.trim()) data['justification_non_respect'] = pv['justification_non_respect'].trim();
    if (pv['differences_protocole']?.trim()) data['differences_protocole'] = pv['differences_protocole'].trim();
    if (pv['mode_validation']?.trim()) data['mode_validation'] = pv['mode_validation'].trim();
    if (Array.isArray(pv['periode_suivi']) && pv['periode_suivi'].length > 0) {
      data['periode_suivi'] = pv['periode_suivi'].join(',');
    } else if (typeof pv['periode_suivi'] === 'string' && pv['periode_suivi']) {
      // Rétrocompat si jamais on reçoit une string
      data['periode_suivi'] = pv['periode_suivi'];
    }
    if (pv['documentation_disponible'] != null) data['documentation_disponible'] = pv['documentation_disponible'];
    if (pv['documentation_disponible'] === true && pv['url_documentation']?.trim()) {
      data['url_documentation'] = pv['url_documentation'].trim();
    }
    return data;
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
    // Taxons : JSON (préserve cd_nom, gère les virgules dans les noms) — #563
    if (this.taxonItems.length > 0) {
      payload.taxon_taxref = serializeTaxonRefs(this.taxonItems);
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

    // Build nested protocoles (#252) — la liste envoyée fait foi côté backend.
    payload.protocoles = (fv.protocoles || [])
      .map((pv: Record<string, any>) => this.buildProtocolePayload(pv))
      .filter((p: Record<string, unknown>) => Object.keys(p).length > 0);

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
