/**
 * Page dédiée formulaire opération (action) - création + édition.
 * Conforme au Figma node-id=154-10720.
 *
 * Refactorisé pour utiliser OperationAnnee[] (table relationnelle)
 * au lieu de JSONField programmation_annuelle/programmation_mensuelle.
 */
import { Component, OnInit, inject, signal, computed, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormControl, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatRadioModule } from '@angular/material/radio';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { debounceTime, distinctUntilChanged, filter, switchMap } from 'rxjs/operators';

import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { ReferenceItemListComponent } from '../../../../shared/components/reference-item-list/reference-item-list.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import { CampanuleService } from '../../../../core/services/campanule.service';
import { InventaireService } from '../../../../core/services/inventaire.service';
import { SuiviInventaireDetail } from '../../../../core/models/inventaire.model';
import { Operation, OperationCreatePayload, OperationAnnee, OperationAnneeOrganisme, FinanceOperation, SuiviInventaire, TaxonRef, HabitatRef, GeologieRef } from '../../../../core/models/enjeu.model';
import { CampanuleAutocomplete } from '../../../../core/models/campanule.model';
import { PlanSite, PlanSiteOrganisme } from '../../../../core/models/admin.model';
import { ProtocoleCampanuleDialogComponent } from '../../../../shared/components/modals/protocole-campanule-dialog/protocole-campanule-dialog.component';

import {
  NomenclatureOption,
  NomenclatureGroup,
  buildNomenclatureGroups,
  getNomenclatureDepth,
  displayNomenclatureFn,
} from '../../../../shared/utils/nomenclature-autocomplete.utils';

@Component({
  selector: 'app-operation-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatSelectModule,
    MatCheckboxModule,
    MatRadioModule,
    MatProgressSpinnerModule,
    MatDatepickerModule,
    MatSnackBarModule,
    MatAutocompleteModule,
    MatDialogModule,
    TranslateModule,
    HeaderComponent,
    ReferenceItemListComponent
  ],
  templateUrl: './operation-form.component.html',
  styleUrl: './operation-form.component.scss'
})
export class OperationFormComponent implements OnInit {
  private readonly elRef = inject(ElementRef);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly enjeuService = inject(EnjeuService);
  private readonly adminService = inject(AdminService);
  private readonly campanuleService = inject(CampanuleService);
  private readonly inventaireService = inject(InventaireService);
  private readonly translate = inject(TranslateService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);

  form!: FormGroup;
  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  operationId = signal<number | null>(null);
  isEditMode = signal(false);
  existingOperation = signal<Operation | null>(null);

  // Query params
  prelinkedMetriqueId = signal<number | null>(null);
  returnEnjeuSlug = signal<string | null>(null);

  // Nomenclatures
  typeActionOptions = signal<NomenclatureOption[]>([]);
  prioriteOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);

  // Type d'action autocomplete
  typeActionSearchCtrl = new FormControl('');
  typeActionGroups = computed<NomenclatureGroup[]>(() => {
    return this.buildActionGroups(this.typeActionOptions(), this.typeActionSearchText());
  });
  typeActionSearchText = signal('');
  selectedTypeAction = signal<NomenclatureOption | null>(null);

  /** Vrai si le type d'action sélectionné est un code CS (Connaissance et Suivi) */
  isCSAction = computed(() => {
    const selected = this.selectedTypeAction();
    if (!selected) return false;
    const code = selected.cd_nomenclature || selected.mnemonique || '';
    return code.startsWith('CS');
  });

  /** Inventaires existants chargés (filtrés par type d'action) */
  availableInventaires = signal<{ id_suivi_inventaire: number; intitule: string; type_action_code?: string }[]>([]);
  categorieFinanceOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);

  // Objectif/Cible nomenclatures
  objectifSuiviOptions = signal<NomenclatureOption[]>([]);
  cibleSuiviOptions = signal<NomenclatureOption[]>([]);
  bancarisationOptions = signal<NomenclatureOption[]>([]);
  outilSaisieOptions = signal<NomenclatureOption[]>([]);

  // Grouped objectifs for mat-optgroup display
  objectifGroups = computed<NomenclatureGroup[]>(() => {
    return this.buildGroups(this.objectifSuiviOptions());
  });

  // Reference item lists (taxons / habitats for operation suivi)
  taxonItems: TaxonRef[] = [];
  habitatItems: HabitatRef[] = [];

  // Plan sites (for "L'action est liée au/aux")
  planSites = signal<PlanSite[]>([]);

  // Indicateurs et métriques du plan (pour les selects M2M)
  planIndicateurs = signal<{ id_indicateur: number; nom_indicateur: string }[]>([]);
  planMetriques = signal<{ id_metrique: number; nom_metrique: string; indicateur_nom: string }[]>([]);

  // Programmation annuelle via OperationAnnee[]
  years: number[] = [];
  months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
  monthLabels = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];
  operationAnnees: OperationAnnee[] = [];

  // Template mensuel unique (même mois chaque année)
  programmationMensuelleDefaut: Record<string, boolean> = {};

  // Finances
  finances: FinanceOperation[] = [];

  // Per-organisme budget data: key = `${yearIndex}-${organismeId}`
  orgBudgets: Record<string, { fonct: number | null; invest: number | null; etp: number | null }> = {};

  /** Mode de ventilation budgétaire : none, by_org, by_type, by_org_type */
  ventilationMode = signal<'none' | 'by_org' | 'by_type' | 'by_org_type'>('none');

  /** Raccourci pour rétrocompatibilité avec le code existant */
  directTotalMode = computed(() => this.ventilationMode() === 'none');

  /** Direct-entered totals per year when in mode 'none': key = yearIndex */
  directTotals: Record<number, { budget: number | null; etp: number | null }> = {};

  /** Budget par type (mode 'by_type') : key = yearIndex */
  typeBudgets: Record<number, { fonct: number | null; invest: number | null; etp: number | null }> = {};

  /** Budget par organisme (mode 'by_org', totaux) : key = `${yearIndex}-${organismeId}` */
  orgByOrgData: Record<string, { budget: number | null; etp: number | null }> = {};

  // Available organismes derived from selected sites
  availableOrganismes = computed(() => {
    this.selectedSiteIdsVersion(); // dependency trigger
    const sites = this.planSites();
    const selectedIds = this.selectedSiteIds;
    const orgMap = new Map<number, { id_organisme: number; nom_organisme: string }>();
    for (const site of sites) {
      if (!selectedIds[site.id_site]) continue;
      for (const org of site.organismes || []) {
        if (!orgMap.has(org.id_organisme)) {
          orgMap.set(org.id_organisme, { id_organisme: org.id_organisme, nom_organisme: org.nom_organisme });
        }
      }
    }
    return Array.from(orgMap.values()).sort((a, b) => a.nom_organisme.localeCompare(b.nom_organisme));
  });

  // Sites M2M checkboxes — use signal so computed can react
  selectedSiteIds: Record<number, boolean> = {};
  selectedSiteIdsVersion = signal(0); // bump to trigger recompute

  // Suivi existant toggle
  estSuiviExistant = signal(false);
  /** Mirror of the libelle form control value, for the read-only display in CS mode */
  libelleDisplay = signal('');


  // CAMPanule autocomplete
  campanuleSearchCtrl = new FormControl('');
  campanuleResults = signal<CampanuleAutocomplete[]>([]);
  selectedCampanule = signal<CampanuleAutocomplete | null>(null);

  // Collapsible sections state
  sectionsOpen: Record<string, boolean> = {
    details_suivi: true,
    protocole: true,
    bancarisation: true,
    programmation: true,
    details: true,
    emprise: true,
    indicateurs_reponse: true
  };

  // Frequency units (loaded from nomenclature FREQUENCE_EMBOITEMENT)
  frequenceUnites: { value: string; label: string }[] = [];

  ngOnInit(): void {
    window.scrollTo({ top: 0, behavior: 'instant' });
    this.loadFrequenceNomenclature();
    this.initForm();
    this.initSuiviLibelleSync();
    this.initTypeActionAutocomplete();
    this.initCampanuleAutocomplete();
    this.loadRouteParams();
  }

  private loadFrequenceNomenclature(): void {
    this.adminService.getNomenclaturesByType('FREQUENCE_EMBOITEMENT').subscribe({
      next: (nomenclatures) => {
        this.frequenceUnites = nomenclatures
          .sort((a, b) => (a.hierarchy || '').localeCompare(b.hierarchy || ''))
          .map(n => ({
            value: (n.mnemonique || '').toLowerCase(),
            label: n.label
          }));
      },
      error: () => {
        // Fallback si la nomenclature n'est pas chargée
        this.frequenceUnites = [
          { value: 'jour', label: 'Jour' },
          { value: 'semaine', label: 'Semaine' },
          { value: 'mois', label: 'Mois' },
          { value: 'an', label: 'Ans' }
        ];
      }
    });
  }

  private initForm(): void {
    this.form = this.fb.group({
      // Main card
      libelle: ['', [Validators.maxLength(500)]],
      id_type_action: [null],
      id_suivi: [null],
      intitule_suivi: [''],
      metrique_ids: [[] as number[]],
      id_priorite: [null],
      // Suivi/inventaire fields (nested in suivi_inventaire on save)
      objectif_principal: [''],
      objectif_secondaire: [''],
      cibles_principales: [null],
      cible_secondaire: [''],
      date_lancement_suivi: [null],
      protocole_dans_campanule: [null],
      protocole_campanule_nom: [''],
      cd_protocole_campanule: [null],
      nb_etp_cycle: [null],
      nom_protocole: [''],
      respect_protocole: [null],
      justification_non_respect: [''],
      differences_protocole: [''],
      description_protocole: [''],
      objectif_protocole: [''],
      periode_echantillonnage: [''],
      outil_bancarisation: [null],
      outil_saisie: [null],
      transmission_donnee: [null],
      // Programmation
      frequence_nombre: [null],
      frequence_unite: [null],
      operateurs: [''],
      partenaires: [''],
      financeurs: [''],
      // Détails
      description: [''],
      // Hidden but kept for backwards compat
      code_operation: [''],
      id_referentiel_operations: [''],
      annee_min: [null],
      annee_max: [null],
    });
  }

  private loadRouteParams(): void {
    // Walk up the route tree to find the 'slug' param (plan slug)
    const slug = this.findRouteParam('slug');
    if (slug) {
      this.planSlug.set(slug);
    }

    const opIdStr = this.route.snapshot.paramMap.get('operationId');
    if (opIdStr) {
      this.operationId.set(parseInt(opIdStr, 10));
      this.isEditMode.set(true);
    }

    const metriqueIdStr = this.route.snapshot.queryParamMap.get('metriqueId');
    if (metriqueIdStr) {
      this.prelinkedMetriqueId.set(parseInt(metriqueIdStr, 10));
    }

    const returnEnjeu = this.route.snapshot.queryParamMap.get('returnEnjeu');
    if (returnEnjeu) {
      this.returnEnjeuSlug.set(returnEnjeu);
    }

    this.loadData();
  }

  /**
   * Walk up the activated route tree to find a param by name.
   */
  private findRouteParam(name: string): string | null {
    let current = this.route.snapshot;
    while (current) {
      const value = current.paramMap.get(name);
      if (value) return value;
      current = current.parent!;
    }
    return null;
  }

  private loadData(): void {
    this.isLoadingData.set(true);

    const slug = this.planSlug();
    if (slug) {
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planNom.set(plan.nom);
          this.computeYears(plan.annee_debut, plan.annee_fin);
          // Extract plan sites
          if (plan.sites) {
            this.planSites.set(plan.sites);
            const isSingleSite = plan.sites.length === 1;
            for (const site of plan.sites) {
              this.selectedSiteIds[site.id_site] = isSingleSite;
            }
          }
          // Load operation data AFTER sites are initialized to avoid race condition
          this.loadOperationIfEdit();
          // Load enjeux after plan is loaded
          this.enjeuService.getPlanEnjeux(plan.id_pg).subscribe({
            next: (response) => {
              const indicateurs: { id_indicateur: number; nom_indicateur: string }[] = [];
              const metriques: { id_metrique: number; nom_metrique: string; indicateur_nom: string }[] = [];

              const allEnjeux = [...(response.enjeux || []), ...(response.fcr || [])];
              const seenIndicateurs = new Set<number>();
              const seenMetriques = new Set<number>();

              const collectIndicateursMetriques = (ind: any) => {
                if (!ind || seenIndicateurs.has(ind.id_indicateur)) return;
                seenIndicateurs.add(ind.id_indicateur);
                indicateurs.push({ id_indicateur: ind.id_indicateur, nom_indicateur: ind.nom_indicateur });
                for (const met of ind.metriques || []) {
                  if (seenMetriques.has(met.id_metrique)) continue;
                  seenMetriques.add(met.id_metrique);
                  metriques.push({
                    id_metrique: met.id_metrique,
                    nom_metrique: met.nom_metrique,
                    indicateur_nom: ind.nom_indicateur
                  });
                }
              };

              for (const enjeu of allEnjeux) {
                // Chemin OLT : Enjeu → OLT → NE → Indicateur → Métrique
                for (const olt of enjeu.objectifs_long_terme || []) {
                  for (const ne of olt.niveaux_exigence || []) {
                    for (const ind of ne.indicateurs || []) {
                      collectIndicateursMetriques(ind);
                    }
                  }
                }
                // Chemin OO : Enjeu → FI → Pression → OO → RA → Indicateur → Métrique
                for (const fi of enjeu.facteurs_influence || []) {
                  for (const pression of fi.pressions || []) {
                    for (const oo of pression.objectifs_operationnels || []) {
                      for (const ra of oo.resultats_attendus || []) {
                        for (const ind of ra.indicateurs || []) {
                          collectIndicateursMetriques(ind);
                        }
                      }
                    }
                  }
                }
              }

              this.planIndicateurs.set(indicateurs);
              this.planMetriques.set(metriques);
            },
            error: () => {}
          });
        },
        error: () => {
          this.computeYears(null, null);
          this.loadOperationIfEdit();
        }
      });
    } else {
      // No plan slug found: generate default years so tables render
      this.computeYears(null, null);
      this.loadOperationIfEdit();
    }

    this.adminService.getNomenclaturesByType('TYPE_ACTION').subscribe({
      next: (options) => {
        this.typeActionOptions.set(options);
        // Si on est en mode édition et que l'opération est déjà chargée, restaurer l'autocomplete
        const op = this.existingOperation();
        if (op?.id_type_action) {
          this.restoreTypeActionAutocomplete(op.id_type_action, options);
        }
      },
      error: () => this.typeActionOptions.set([])
    });

    this.adminService.getNomenclaturesByType('PRIORITE_OPERATION').subscribe({
      next: (options) => this.prioriteOptions.set(options),
      error: () => this.prioriteOptions.set([])
    });



    this.adminService.getNomenclaturesByType('CATEGORIE_FINANCE').subscribe({
      next: (options) => this.categorieFinanceOptions.set(options),
      error: () => this.categorieFinanceOptions.set([])
    });

    this.adminService.getNomenclaturesByType('OBJECTIF_SUIVI').subscribe({
      next: (options) => this.objectifSuiviOptions.set(options),
      error: () => this.objectifSuiviOptions.set([])
    });

    this.adminService.getNomenclaturesByType('CIBLE_SUIVI').subscribe({
      next: (options) => this.cibleSuiviOptions.set(options),
      error: () => this.cibleSuiviOptions.set([])
    });

    this.adminService.getNomenclaturesByType('BANCARISATION_STOCKAGE').subscribe({
      next: (options) => this.bancarisationOptions.set(options),
      error: () => this.bancarisationOptions.set([])
    });

    this.adminService.getNomenclaturesByType('OUTIL_SAISIE').subscribe({
      next: (options) => this.outilSaisieOptions.set(options),
      error: () => this.outilSaisieOptions.set([])
    });
  }

  private computeYears(anneeDebut: number | null | undefined, anneeFin: number | null | undefined): void {
    const start = anneeDebut || new Date().getFullYear();
    const end = anneeFin || start + 5;
    this.years = [];
    this.operationAnnees = [];
    for (let y = start; y <= end; y++) {
      this.years.push(y);
      this.operationAnnees.push({
        annee: y,
        periodicite: false,
        budget: null,
        etp: null,
        periodicite_mensuelle: this.emptyMensuelle()
      });
    }
    // Init default monthly template
    this.programmationMensuelleDefaut = this.emptyMensuelle();
  }

  private emptyMensuelle(): Record<string, boolean> {
    const m: Record<string, boolean> = {};
    for (const month of this.months) {
      m[month.toString()] = false;
    }
    return m;
  }

  private loadOperationIfEdit(): void {
    const opId = this.operationId();
    if (!opId) {
      const prelinkedId = this.prelinkedMetriqueId();
      if (prelinkedId) {
        // prelinkedId is now expected to be a metrique ID
        this.form.patchValue({ metrique_ids: [prelinkedId] });
      }
      this.isLoadingData.set(false);
      return;
    }

    this.enjeuService.getOperation(opId).subscribe({
      next: (operation) => {
        this.existingOperation.set(operation);
        this.populateForm(operation);
        this.isLoadingData.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.loadError'));
        this.isLoadingData.set(false);
      }
    });
  }

  private populateForm(op: Operation): void {
    // Set est_suivi_existant state
    if (op.est_suivi_existant) {
      this.estSuiviExistant.set(true);
    }

    this.form.patchValue({
      libelle: op.libelle,
      id_type_action: op.id_type_action || null,
      id_suivi: op.id_suivi || null,
      id_priorite: op.id_priorite || null,
      code_operation: op.code_operation || '',
      id_referentiel_operations: op.id_referentiel_operations || '',
      description: op.description || '',
      annee_min: op.annee_min || null,
      annee_max: op.annee_max || null,
      // Fréquence & acteurs
      frequence_nombre: op.frequence_nombre || null,
      frequence_unite: op.frequence_unite || null,
      operateurs: op.operateurs || '',
      partenaires: op.partenaires || '',
      financeurs: op.financeurs || '',
      metrique_ids: op.metrique_ids || []
    });

    // Restore type action autocomplete
    if (op.id_type_action) {
      this.restoreTypeActionAutocomplete(op.id_type_action);
    }

    // Populate suivi fields from nested suivi_inventaire
    const suivi = op.suivi_inventaire;
    if (suivi) {
      // Parse taxon references from stored string
      if (suivi.taxon_taxref) {
        this.taxonItems = suivi.taxon_taxref.split(',').map((s: string) => s.trim()).filter((s: string) => s).map((name: string) => ({
          cd_nom: 0,
          nom_complet: name,
        }));
      }
      // Parse habitat references
      if (suivi.habitat_ref) {
        this.habitatItems = suivi.habitat_ref.split(',').map((s: string) => s.trim()).filter((s: string) => s).map((name: string) => ({
          cd_hab: '',
          lb_hab_fr: name,
        }));
      }

      this.form.patchValue({
        objectif_principal: suivi.objectif_principal || '',
        objectif_secondaire: suivi.objectif_secondaire || '',
        cibles_principales: suivi.cibles_principales || null,
        cible_secondaire: suivi.cible_secondaire || '',
        date_lancement_suivi: suivi.date_lancement_suivi ? new Date(suivi.date_lancement_suivi) : null,
        outil_bancarisation: suivi.outil_bancarisation || null,
        outil_saisie: suivi.outil_saisie || null,
        transmission_donnee: suivi.transmission_donnee ?? null,
      });

      // Populate protocole fields from nested protocole
      const proto = suivi.protocole;
      if (proto) {
        this.form.patchValue({
          protocole_dans_campanule: proto.protocole_dans_campanule ?? null,
          protocole_campanule_nom: proto.protocole_campanule_nom || '',
          cd_protocole_campanule: proto.cd_protocole_campanule || null,
          nb_etp_cycle: proto.nb_etp_cycle || null,
          nom_protocole: proto.nom_protocole || '',
          respect_protocole: proto.respect_protocole ?? null,
          justification_non_respect: proto.justification_non_respect || '',
          differences_protocole: proto.differences_protocole || '',
          description_protocole: proto.description_protocole || '',
          objectif_protocole: proto.objectif_protocole || '',
          periode_echantillonnage: proto.periode_echantillonnage || '',
        });

        // Restore CAMPanule autocomplete state
        if (proto.cd_protocole_campanule && proto.protocole_campanule_nom) {
          this.campanuleSearchCtrl.setValue(proto.protocole_campanule_nom, { emitEvent: false });
          this.selectedCampanule.set({
            cd_protocole: proto.cd_protocole_campanule,
            search_name: proto.protocole_campanule_nom,
            lb_protocole_court: proto.protocole_campanule_nom,
          });
        }
      }
    }

    // Disable fields if est_suivi_existant
    if (op.est_suivi_existant) {
      this.setSuiviFieldsEnabled(false);
    }

    // For CS actions, libelle is synced with inventaire title
    if (op.id_type_action) {
      const opts = this.typeActionOptions();
      const match = opts.find(o => o.id_nomenclature === op.id_type_action);
      const code = match?.cd_nomenclature || match?.mnemonique || '';
      if (code.startsWith('CS')) {
        this.form.get('libelle')?.disable();
        this.libelleDisplay.set(op.libelle || '');
      }
    }

    // Restore site selections
    if (op.site_ids) {
      for (const siteId of op.site_ids) {
        this.selectedSiteIds[siteId] = true;
      }
      this.selectedSiteIdsVersion.update(v => v + 1);
    }

    // Restore operation_annees from relational data
    if (op.operation_annees && op.operation_annees.length > 0) {
      // Merge server data with existing year slots
      for (const serverAnnee of op.operation_annees) {
        const idx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
        if (idx >= 0) {
          this.operationAnnees[idx] = { ...serverAnnee };
          // Parse decimal strings from DRF (DecimalField serializes as string)
          if (this.operationAnnees[idx].budget != null) {
            this.operationAnnees[idx].budget = parseFloat(String(this.operationAnnees[idx].budget));
          }
          if (this.operationAnnees[idx].etp != null) {
            this.operationAnnees[idx].etp = parseFloat(String(this.operationAnnees[idx].etp));
          }
        } else {
          // Year from server not in plan range: add it
          const parsed = { ...serverAnnee };
          if (parsed.budget != null) parsed.budget = parseFloat(String(parsed.budget));
          if (parsed.etp != null) parsed.etp = parseFloat(String(parsed.etp));
          this.operationAnnees.push(parsed);
          this.years.push(serverAnnee.annee);
        }
      }
      // Re-sort
      this.years.sort((a, b) => a - b);
      this.operationAnnees.sort((a, b) => a.annee - b.annee);

      // Restore per-organisme data
      for (const serverAnnee of op.operation_annees) {
        const yearIdx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
        if (yearIdx >= 0 && serverAnnee.organismes) {
          for (const org of serverAnnee.organismes) {
            this.orgBudgets[this.orgKey(yearIdx, org.id_organisme)] = {
              fonct: org.budget_fonctionnement != null ? parseFloat(String(org.budget_fonctionnement)) : null,
              invest: org.budget_investissement != null ? parseFloat(String(org.budget_investissement)) : null,
              etp: org.etp != null ? parseFloat(String(org.etp)) : null,
            };
          }
        }
      }
    }

    // Restore ventilation mode from backend (or infer for legacy data)
    const savedMode = op.ventilation_mode || 'none';
    this.ventilationMode.set(savedMode);

    if (op.operation_annees && op.operation_annees.length > 0) {
      if (savedMode === 'by_org') {
        for (const serverAnnee of op.operation_annees) {
          const yearIdx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
          if (yearIdx >= 0 && serverAnnee.organismes) {
            for (const org of serverAnnee.organismes) {
              this.orgByOrgData[`${yearIdx}-${org.id_organisme}`] = {
                budget: org.budget_fonctionnement != null ? parseFloat(String(org.budget_fonctionnement)) : null,
                etp: org.etp != null ? parseFloat(String(org.etp)) : null,
              };
            }
          }
        }
      } else if (savedMode === 'by_type') {
        for (const serverAnnee of op.operation_annees) {
          const yearIdx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
          if (yearIdx >= 0) {
            this.typeBudgets[yearIdx] = {
              fonct: serverAnnee.budget_fonctionnement != null ? parseFloat(String(serverAnnee.budget_fonctionnement)) : null,
              invest: serverAnnee.budget_investissement != null ? parseFloat(String(serverAnnee.budget_investissement)) : null,
              etp: serverAnnee.etp != null ? parseFloat(String(serverAnnee.etp)) : null,
            };
          }
        }
      } else if (savedMode === 'none') {
        for (const serverAnnee of op.operation_annees) {
          const yearIdx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
          if (yearIdx >= 0) {
            this.directTotals[yearIdx] = {
              budget: serverAnnee.budget != null ? parseFloat(String(serverAnnee.budget)) : null,
              etp: serverAnnee.etp != null ? parseFloat(String(serverAnnee.etp)) : null,
            };
          }
        }
      }
      // Mode by_org_type: orgBudgets already populated above (lines 634-638)
    }

    // Restore default monthly template
    if (op.programmation_mensuelle_defaut && Object.keys(op.programmation_mensuelle_defaut).length > 0) {
      this.programmationMensuelleDefaut = { ...op.programmation_mensuelle_defaut };
    }

    // Restore finances
    if (op.finances && op.finances.length > 0) {
      this.finances = op.finances.map(f => ({ ...f }));
    }
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.scrollToError();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const fv = this.form.value;

    // getRawValue() includes disabled fields (for readonly suivi mode)
    const rawFv = this.form.getRawValue();

    // Use rawFv for libelle since it may be disabled (auto-filled from inventaire)
    let libelle = rawFv.libelle?.trim() || '';
    if (!libelle) {
      const selected = this.selectedTypeAction();
      if (selected) {
        const code = selected.cd_nomenclature || selected.mnemonique || '';
        libelle = `${code} - ${selected.label}`;
      }
    }

    const payload: OperationCreatePayload = {
      libelle,
    };

    if (fv.id_type_action) payload.id_type_action = fv.id_type_action;
    if (fv.id_priorite) payload.id_priorite = fv.id_priorite;
    if (fv.code_operation?.trim()) payload.code_operation = fv.code_operation.trim();
    if (fv.id_referentiel_operations?.trim()) payload.id_referentiel_operations = fv.id_referentiel_operations.trim();
    if (fv.description?.trim()) payload.description = fv.description.trim();
    if (fv.annee_min != null) payload.annee_min = fv.annee_min;
    if (fv.annee_max != null) payload.annee_max = fv.annee_max;

    // est_suivi_existant
    payload.est_suivi_existant = this.estSuiviExistant();

    // If existing suivi selected, pass id_suivi
    if (this.estSuiviExistant() && fv.id_suivi) {
      payload.id_suivi = fv.id_suivi;
    }

    // Build nested suivi_inventaire from form fields (only if CS action and not "existing suivi" mode)
    if (this.isCSAction() && !this.estSuiviExistant()) {
      const suiviData: Record<string, unknown> = {};
      // Intitulé de l'inventaire (requis pour les nouveaux)
      if (fv.intitule_suivi?.trim()) suiviData['intitule'] = fv.intitule_suivi.trim();
      // Propager le type d'action CS sélectionné
      if (fv.id_type_action) suiviData['id_type_action'] = fv.id_type_action;
      if (rawFv.objectif_principal?.trim()) suiviData['objectif_principal'] = rawFv.objectif_principal.trim();
      if (rawFv.objectif_secondaire?.trim()) suiviData['objectif_secondaire'] = rawFv.objectif_secondaire.trim();
      if (rawFv.cibles_principales) suiviData['cibles_principales'] = rawFv.cibles_principales;
      if (rawFv.cible_secondaire) suiviData['cible_secondaire'] = rawFv.cible_secondaire;
      // Serialize taxon/habitat reference lists to strings
      if (this.taxonItems.length > 0) {
        suiviData['taxon_taxref'] = this.taxonItems.map(t => t.nom_complet || String(t.cd_nom)).join(', ');
      }
      if (this.habitatItems.length > 0) {
        suiviData['habitat_ref'] = this.habitatItems.map(h => h.lb_hab_fr || h.cd_hab).join(', ');
      }
      const dateLancement = this.formatDate(rawFv.date_lancement_suivi);
      if (dateLancement) suiviData['date_lancement_suivi'] = dateLancement;
      if (rawFv.outil_bancarisation) suiviData['outil_bancarisation'] = rawFv.outil_bancarisation;
      if (rawFv.outil_saisie) suiviData['outil_saisie'] = rawFv.outil_saisie;
      if (rawFv.transmission_donnee != null) suiviData['transmission_donnee'] = rawFv.transmission_donnee;

      // Build nested protocole
      const protocoleData: Record<string, unknown> = {};
      if (rawFv.protocole_dans_campanule != null) protocoleData['protocole_dans_campanule'] = rawFv.protocole_dans_campanule;
      if (rawFv.protocole_campanule_nom) protocoleData['protocole_campanule_nom'] = rawFv.protocole_campanule_nom;
      if (rawFv.cd_protocole_campanule != null) protocoleData['cd_protocole_campanule'] = rawFv.cd_protocole_campanule;
      if (rawFv.nb_etp_cycle != null) protocoleData['nb_etp_cycle'] = rawFv.nb_etp_cycle;
      if (rawFv.nom_protocole?.trim()) protocoleData['nom_protocole'] = rawFv.nom_protocole.trim();
      if (rawFv.respect_protocole != null) protocoleData['respect_protocole'] = rawFv.respect_protocole;
      if (rawFv.justification_non_respect?.trim()) protocoleData['justification_non_respect'] = rawFv.justification_non_respect.trim();
      if (rawFv.differences_protocole?.trim()) protocoleData['differences_protocole'] = rawFv.differences_protocole.trim();
      if (rawFv.description_protocole?.trim()) protocoleData['description_protocole'] = rawFv.description_protocole.trim();
      if (rawFv.objectif_protocole?.trim()) protocoleData['objectif_protocole'] = rawFv.objectif_protocole.trim();
      if (rawFv.periode_echantillonnage?.trim()) protocoleData['periode_echantillonnage'] = rawFv.periode_echantillonnage.trim();

      if (Object.keys(protocoleData).length > 0) {
        suiviData['protocole'] = protocoleData;
      }

      if (Object.keys(suiviData).length > 0) {
        payload.suivi_inventaire = suiviData;
      }
    }

    // Fréquence
    if (fv.frequence_nombre != null) payload.frequence_nombre = fv.frequence_nombre;
    if (fv.frequence_unite) payload.frequence_unite = fv.frequence_unite;
    if (fv.operateurs?.trim()) payload.operateurs = fv.operateurs.trim();
    if (fv.partenaires?.trim()) payload.partenaires = fv.partenaires.trim();
    if (fv.financeurs?.trim()) payload.financeurs = fv.financeurs.trim();
    if (fv.metrique_ids?.length) payload.metrique_ids = fv.metrique_ids;

    // Sites
    const siteIds = Object.entries(this.selectedSiteIds)
      .filter(([_, selected]) => selected)
      .map(([id, _]) => parseInt(id, 10));
    if (siteIds.length) payload.site_ids = siteIds;

    // Template mensuel (mêmes mois chaque année)
    payload.programmation_mensuelle_defaut = { ...this.programmationMensuelleDefaut };

    // Mode de ventilation du budget
    const mode = this.ventilationMode();
    payload.ventilation_mode = mode;

    // Operation annees: apply the monthly template to all years + per-organisme data
    const orgs = this.availableOrganismes();
    type OrgEntry = { id_organisme: number; budget_fonctionnement: number | null; budget_investissement: number | null; etp: number | null };
    const anneesToSave = this.operationAnnees.map((a, idx) => {
      const base = {
        annee: a.annee,
        periodicite: a.periodicite,
        periodicite_mensuelle: { ...this.programmationMensuelleDefaut },
      };

      if (mode === 'none') {
        // Mode 1: Pas de ventilation — totaux directs
        const directData = this.getDirectTotal(idx);
        return { ...base, budget: directData.budget, etp: directData.etp, budget_fonctionnement: null, budget_investissement: null, organismes: [] as OrgEntry[] };
      }

      if (mode === 'by_type') {
        // Mode 3: Par type de budget (global, sans organismes)
        const typeData = this.getTypeBudget(idx);
        const totalBudget = (typeData.fonct || 0) + (typeData.invest || 0);
        return { ...base, budget: totalBudget || null, etp: typeData.etp, budget_fonctionnement: typeData.fonct, budget_investissement: typeData.invest, organismes: [] as OrgEntry[] };
      }

      if (mode === 'by_org') {
        // Mode 2: Par organisme (totaux, sans fonct/invest)
        const orgEntries: OrgEntry[] = [];
        for (const org of orgs) {
          const data = this.getOrgByOrgData(idx, org.id_organisme);
          if (data.budget != null || data.etp != null) {
            orgEntries.push({
              id_organisme: org.id_organisme,
              budget_fonctionnement: data.budget,
              budget_investissement: null,
              etp: data.etp,
            });
          }
        }
        const totalBudget = orgEntries.reduce((sum, o) => sum + (o.budget_fonctionnement || 0), 0);
        const totalEtp = orgEntries.reduce((sum, o) => sum + (o.etp || 0), 0);
        return { ...base, budget: orgEntries.length > 0 ? totalBudget : null, etp: orgEntries.length > 0 ? totalEtp : null, budget_fonctionnement: null, budget_investissement: null, organismes: orgEntries };
      }

      // Mode 4: by_org_type — Par organisme + type (mode actuel ventilation)
      const orgEntries: OrgEntry[] = [];
      for (const org of orgs) {
        const data = this.getOrgBudget(idx, org.id_organisme);
        if (data.fonct != null || data.invest != null || data.etp != null) {
          orgEntries.push({
            id_organisme: org.id_organisme,
            budget_fonctionnement: data.fonct,
            budget_investissement: data.invest,
            etp: data.etp,
          });
        }
      }
      const totalBudget = orgEntries.reduce((sum, o) => sum + (o.budget_fonctionnement || 0) + (o.budget_investissement || 0), 0);
      const totalEtp = orgEntries.reduce((sum, o) => sum + (o.etp || 0), 0);
      return { ...base, budget: orgEntries.length > 0 ? totalBudget : a.budget, etp: orgEntries.length > 0 ? totalEtp : a.etp, budget_fonctionnement: null, budget_investissement: null, organismes: orgEntries };
    });

    const hasAnneeData = anneesToSave.some(
      a => a.periodicite || a.budget != null || a.etp != null ||
        a.organismes.length > 0 ||
        Object.values(a.periodicite_mensuelle).some(v => v)
    );
    if (hasAnneeData) {
      payload.operation_annees = anneesToSave;
    }

    // Finances (relational)
    if (this.finances.length > 0) {
      payload.finances = this.finances
        .filter(f => f.libelle?.trim())
        .map(f => ({
          libelle: f.libelle.trim(),
          id_categorie: f.id_categorie || undefined
        }));
    }

    if (this.isEditMode()) {
      const opId = this.operationId()!;
      this.enjeuService.updateOperation(opId, payload).subscribe({
        next: () => {
          this.isLoading.set(false);
          this.snackBar.open(
            this.translate.instant('enjeux.operations.updateSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.enjeuService.refreshCurrentPlanEnjeux();
          this.goBack();
        },
        error: (error) => {
          this.isLoading.set(false);
          this.errorMessage.set(
            error.message || this.translate.instant('enjeux.messages.updateError')
          );
          this.scrollToError();
        }
      });
    } else {
      this.enjeuService.createOperation(payload).subscribe({
        next: () => {
          this.isLoading.set(false);
          this.snackBar.open(
            this.translate.instant('enjeux.operations.createSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.enjeuService.refreshCurrentPlanEnjeux();
          this.goBack();
        },
        error: (error) => {
          this.isLoading.set(false);
          this.errorMessage.set(
            error.message || this.translate.instant('enjeux.messages.createError')
          );
          this.scrollToError();
        }
      });
    }
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

  goBack(): void {
    const slug = this.planSlug();
    if (!slug) {
      this.router.navigate(['/plans']);
      return;
    }

    const returnEnjeu = this.returnEnjeuSlug();
    const opId = this.operationId();
    if (returnEnjeu) {
      this.router.navigate(
        ['/plans', slug, 'enjeux', returnEnjeu],
        { queryParams: { tab: 'operations', ...(opId ? { expandOperation: opId } : {}) } }
      );
    } else {
      this.router.navigate(['/plans', slug, 'enjeux']);
    }
  }

  toggleSection(section: string): void {
    this.sectionsOpen[section] = !this.sectionsOpen[section];
  }

  setEstSuiviExistant(value: boolean): void {
    this.estSuiviExistant.set(value);
    if (value) {
      // "Existing suivi" mode: disable suivi fields, clear intitule_suivi
      this.setSuiviFieldsEnabled(false);
      this.form.get('intitule_suivi')?.clearValidators();
      this.form.get('intitule_suivi')?.updateValueAndValidity();
      // Sync libelle from selected inventaire
      this.updateLibelle(this.getSelectedSuiviIntitule());
    } else {
      // "New suivi" mode: enable suivi fields, reset values, intitule_suivi required
      this.resetSuiviFields();
      this.setSuiviFieldsEnabled(true);
      this.form.get('intitule_suivi')?.setValidators([Validators.required]);
      this.form.get('intitule_suivi')?.updateValueAndValidity();
      this.form.get('id_suivi')?.setValue(null);
      // Sync libelle from intitule_suivi text
      this.updateLibelle(this.form.get('intitule_suivi')?.value || '');
    }
  }

  /**
   * For CS actions, libelle = intitulé de l'inventaire (existing or new).
   * Subscribe to id_suivi changes and intitule_suivi keystrokes.
   */
  private initSuiviLibelleSync(): void {
    // Existing suivi selected → sync libelle + fetch full details
    this.form.get('id_suivi')?.valueChanges.subscribe((idSuivi) => {
      if (this.isCSAction() && this.estSuiviExistant()) {
        this.updateLibelle(this.getSelectedSuiviIntitule());
        if (idSuivi) {
          this.fetchAndPopulateSuiviDetails(idSuivi);
        }
      }
    });

    // New suivi typed → sync libelle as user types
    this.form.get('intitule_suivi')?.valueChanges.subscribe((val) => {
      if (this.isCSAction() && !this.estSuiviExistant()) {
        this.updateLibelle(val || '');
      }
    });
  }

  /** Get the intitule of the currently selected existing inventaire. */
  private getSelectedSuiviIntitule(): string {
    const idSuivi = this.form.get('id_suivi')?.value;
    if (!idSuivi) return '';
    const inv = this.availableInventaires().find(i => i.id_suivi_inventaire === idSuivi);
    return inv?.intitule || '';
  }

  /** Update the libelle form control and its display signal. */
  private updateLibelle(value: string): void {
    this.form.get('libelle')?.setValue(value, { emitEvent: false });
    this.libelleDisplay.set(value);
  }

  /** Fetch full inventaire details and populate the suivi/protocole form fields. */
  private fetchAndPopulateSuiviDetails(idSuivi: number): void {
    this.inventaireService.getInventaire(idSuivi).subscribe({
      next: (detail: SuiviInventaireDetail) => {
        // Populate taxon/habitat reference lists
        if (detail.taxon_taxref) {
          this.taxonItems = detail.taxon_taxref.split(',').map(s => s.trim()).filter(s => s).map(name => ({
            cd_nom: 0,
            nom_complet: name,
          }));
        } else {
          this.taxonItems = [];
        }
        if (detail.habitat_ref) {
          this.habitatItems = detail.habitat_ref.split(',').map(s => s.trim()).filter(s => s).map(name => ({
            cd_hab: '',
            lb_hab_fr: name,
          }));
        } else {
          this.habitatItems = [];
        }

        // Populate suivi fields
        this.form.patchValue({
          objectif_principal: detail.objectif_principal || '',
          objectif_secondaire: detail.objectif_secondaire || '',
          cibles_principales: detail.cibles_principales || null,
          cible_secondaire: detail.cible_secondaire || '',
          date_lancement_suivi: detail.date_lancement_suivi ? new Date(detail.date_lancement_suivi) : null,
          outil_bancarisation: detail.outil_bancarisation || null,
          outil_saisie: detail.outil_saisie || null,
          transmission_donnee: detail.transmission_donnee ?? null,
        });

        // Populate protocole fields
        const proto = detail.protocole;
        if (proto) {
          this.form.patchValue({
            protocole_dans_campanule: proto.protocole_dans_campanule ?? null,
            protocole_campanule_nom: proto.protocole_campanule_nom || '',
            cd_protocole_campanule: proto.cd_protocole_campanule || null,
            nb_etp_cycle: proto.nb_etp_cycle || null,
            nom_protocole: proto.nom_protocole || '',
            respect_protocole: proto.respect_protocole ?? null,
            justification_non_respect: proto.justification_non_respect || '',
            differences_protocole: proto.differences_protocole || '',
            description_protocole: proto.description_protocole || '',
            objectif_protocole: proto.objectif_protocole || '',
            periode_echantillonnage: proto.periode_echantillonnage || '',
          });

          // Restore CAMPanule autocomplete state
          if (proto.cd_protocole_campanule && proto.protocole_campanule_nom) {
            this.campanuleSearchCtrl.setValue(proto.protocole_campanule_nom, { emitEvent: false });
            this.selectedCampanule.set({
              cd_protocole: proto.cd_protocole_campanule,
              search_name: proto.protocole_campanule_nom,
              lb_protocole_court: proto.protocole_campanule_nom,
            });
          }
        }
      },
    });
  }

  // ════════════════════════════════════════════════
  // Type d'action autocomplete (codes Eden 62)
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

    // Si c'est un code CS, charger les inventaires correspondants et griser le libellé
    const code = option.cd_nomenclature || option.mnemonique || '';
    if (code.startsWith('CS')) {
      this.loadInventairesByTypeAction(code);
      this.form.get('libelle')?.disable();
    } else {
      this.availableInventaires.set([]);
      this.estSuiviExistant.set(false);
      this.form.get('libelle')?.enable();
    }
  }

  clearTypeAction(): void {
    this.typeActionSearchCtrl.setValue('');
    this.selectedTypeAction.set(null);
    this.form.get('id_type_action')?.setValue(null);
    this.availableInventaires.set([]);
    this.estSuiviExistant.set(false);
    this.form.get('libelle')?.enable();
  }

  /** Charge les inventaires existants filtrés par préfixe du type d'action CS */
  private loadInventairesByTypeAction(codePrefix: string): void {
    this.inventaireService.getInventaires({ type_action_prefix: codePrefix, page_size: 200 }).subscribe({
      next: (res) => {
        const items = (res.results || []).map((inv: any) => ({
          id_suivi_inventaire: inv.id_suivi_inventaire,
          intitule: inv.intitule,
          type_action_code: inv.type_action_code,
        }));
        this.availableInventaires.set(items);
      },
      error: () => this.availableInventaires.set([]),
    });
  }

  private restoreTypeActionAutocomplete(typeActionId: number, options?: NomenclatureOption[]): void {
    const opts = options || this.typeActionOptions();
    const match = opts.find(o => o.id_nomenclature === typeActionId);
    if (match) {
      this.selectedTypeAction.set(match);
      this.typeActionSearchCtrl.setValue(this.displayTypeActionFn(match), { emitEvent: false });
    }
  }

  private buildActionGroups(options: NomenclatureOption[], searchText: string): NomenclatureGroup[] {
    return buildNomenclatureGroups(options, searchText);
  }

  getActionDepth = getNomenclatureDepth;

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

  displayCampanuleFn(option: CampanuleAutocomplete | string): string {
    if (!option) return '';
    if (typeof option === 'string') return option;
    return option.lb_protocole_court || '';
  }

  onCampanuleSelected(event: any): void {
    const selected: CampanuleAutocomplete = event.option.value;
    this.selectedCampanule.set(selected);
    this.campanuleSearchCtrl.setValue(selected.lb_protocole_court, { emitEvent: false });

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

  /** Check if objectif principal is set (to show objectif secondaire) */
  get hasObjectifPrincipal(): boolean {
    return !!this.form.get('objectif_principal')?.value;
  }

  /** Check if cible principale is set (to show cible secondaire) */
  get hasCiblePrincipale(): boolean {
    return !!this.form.get('cibles_principales')?.value;
  }

  onTaxonsChange(items: (TaxonRef | HabitatRef | GeologieRef)[]): void {
    this.taxonItems = items as TaxonRef[];
  }

  onHabitatsChange(items: (TaxonRef | HabitatRef | GeologieRef)[]): void {
    this.habitatItems = items as HabitatRef[];
  }

  private formatDate(date: Date | string | null): string | undefined {
    if (!date) return undefined;
    if (typeof date === 'string') return date;
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  private resetSuiviFields(): void {
    const fields = [
      'objectif_principal', 'objectif_secondaire',
      'cibles_principales', 'cible_secondaire',
      'date_lancement_suivi', 'protocole_dans_campanule', 'protocole_campanule_nom',
      'cd_protocole_campanule', 'nb_etp_cycle', 'nom_protocole',
      'respect_protocole', 'justification_non_respect', 'differences_protocole',
      'description_protocole', 'objectif_protocole', 'periode_echantillonnage',
      'outil_bancarisation', 'outil_saisie', 'transmission_donnee',
      'intitule_suivi'
    ];
    for (const field of fields) {
      this.form.get(field)?.reset();
    }
  }

  private setSuiviFieldsEnabled(enabled: boolean): void {
    const fields = [
      'objectif_principal', 'objectif_secondaire',
      'cibles_principales', 'cible_secondaire',
      'date_lancement_suivi', 'protocole_dans_campanule', 'protocole_campanule_nom',
      'cd_protocole_campanule', 'nb_etp_cycle', 'nom_protocole',
      'respect_protocole', 'justification_non_respect', 'differences_protocole',
      'description_protocole', 'objectif_protocole', 'periode_echantillonnage',
      'outil_bancarisation', 'outil_saisie', 'transmission_donnee'
    ];
    for (const field of fields) {
      const control = this.form.get(field);
      if (control) {
        if (enabled) {
          control.enable();
        } else {
          control.disable();
        }
      }
    }
  }

  toggleSite(siteId: number): void {
    this.selectedSiteIds[siteId] = !this.selectedSiteIds[siteId];
    this.selectedSiteIdsVersion.update(v => v + 1);
  }

  // ════════════════════════════════════════════════
  // Per-organisme budget/travail
  // ════════════════════════════════════════════════

  private orgKey(yearIdx: number, orgId: number): string {
    return `${yearIdx}-${orgId}`;
  }

  getOrgBudget(yearIdx: number, orgId: number): { fonct: number | null; invest: number | null; etp: number | null } {
    const key = this.orgKey(yearIdx, orgId);
    if (!this.orgBudgets[key]) {
      this.orgBudgets[key] = { fonct: null, invest: null, etp: null };
    }
    return this.orgBudgets[key];
  }

  updateOrgBudgetFonct(yearIdx: number, orgId: number, value: string): void {
    this.getOrgBudget(yearIdx, orgId).fonct = this.parseDecimal(value);
  }

  updateOrgBudgetInvest(yearIdx: number, orgId: number, value: string): void {
    this.getOrgBudget(yearIdx, orgId).invest = this.parseDecimal(value);
  }

  updateOrgEtp(yearIdx: number, orgId: number, value: string): void {
    this.getOrgBudget(yearIdx, orgId).etp = this.parseDecimal(value);
  }

  getOrgTotal(yearIdx: number, orgId: number): number {
    const data = this.getOrgBudget(yearIdx, orgId);
    return (data.fonct || 0) + (data.invest || 0);
  }

  getYearTotalBudget(yearIdx: number): number {
    let total = 0;
    for (const org of this.availableOrganismes()) {
      total += this.getOrgTotal(yearIdx, org.id_organisme);
    }
    return total;
  }

  getYearTotalEtp(yearIdx: number): number {
    let total = 0;
    for (const org of this.availableOrganismes()) {
      total += this.getOrgBudget(yearIdx, org.id_organisme).etp || 0;
    }
    return total;
  }

  // ════════════════════════════════════════════════
  // Programmation annuelle (OperationAnnee[])
  // ════════════════════════════════════════════════

  togglePeriodicite(index: number): void {
    const annee = this.operationAnnees[index];
    annee.periodicite = !annee.periodicite;
    if (!annee.periodicite) {
      annee.budget = null;
      annee.etp = null;
    }
  }

  updateBudget(index: number, value: string): void {
    this.operationAnnees[index].budget = this.parseDecimal(value);
  }

  updateEtp(index: number, value: string): void {
    this.operationAnnees[index].etp = this.parseDecimal(value);
  }

  duplicateFirstColumn(): void {
    if (this.operationAnnees.length < 2) return;
    const first = this.operationAnnees[0];
    for (let i = 1; i < this.operationAnnees.length; i++) {
      this.operationAnnees[i] = {
        ...this.operationAnnees[i],
        periodicite: first.periodicite,
        budget: first.budget,
        etp: first.etp,
        periodicite_mensuelle: { ...first.periodicite_mensuelle }
      };
      // Duplicate per-organisme data
      for (const org of this.availableOrganismes()) {
        const srcData = this.getOrgBudget(0, org.id_organisme);
        this.orgBudgets[this.orgKey(i, org.id_organisme)] = { ...srcData };
      }
      // Duplicate direct totals / type budgets / org totals
      const mode = this.ventilationMode();
      if (mode === 'none') {
        this.directTotals[i] = { ...this.getDirectTotal(0) };
      } else if (mode === 'by_type') {
        this.typeBudgets[i] = { ...this.getTypeBudget(0) };
      } else if (mode === 'by_org') {
        for (const org of this.availableOrganismes()) {
          this.orgByOrgData[`${i}-${org.id_organisme}`] = { ...this.getOrgByOrgData(0, org.id_organisme) };
        }
      }
    }
  }

  // ════════════════════════════════════════════════
  // Mode totaux directs
  // ════════════════════════════════════════════════

  /** Parse une valeur décimale en acceptant la virgule comme séparateur. */
  private parseDecimal(value: string): number | null {
    if (!value) return null;
    const normalized = String(value).replace(',', '.');
    const parsed = parseFloat(normalized);
    return isNaN(parsed) ? null : parsed;
  }

  onModeToggle(mode: string): void {
    this.ventilationMode.set(mode as 'none' | 'by_org' | 'by_type' | 'by_org_type');
  }

  getDirectTotal(yearIdx: number): { budget: number | null; etp: number | null } {
    if (!this.directTotals[yearIdx]) {
      this.directTotals[yearIdx] = { budget: null, etp: null };
    }
    return this.directTotals[yearIdx];
  }

  updateDirectBudget(yearIdx: number, value: string): void {
    this.getDirectTotal(yearIdx).budget = this.parseDecimal(value);
  }

  updateDirectEtp(yearIdx: number, value: string): void {
    this.getDirectTotal(yearIdx).etp = this.parseDecimal(value);
  }

  // ════════════════════════════════════════════════
  // Mode 'by_type' helpers (ventilation par type budget global)
  // ════════════════════════════════════════════════

  getTypeBudget(yearIdx: number): { fonct: number | null; invest: number | null; etp: number | null } {
    if (!this.typeBudgets[yearIdx]) {
      this.typeBudgets[yearIdx] = { fonct: null, invest: null, etp: null };
    }
    return this.typeBudgets[yearIdx];
  }

  updateTypeFonct(yearIdx: number, value: string): void {
    this.getTypeBudget(yearIdx).fonct = this.parseDecimal(value);
  }

  updateTypeInvest(yearIdx: number, value: string): void {
    this.getTypeBudget(yearIdx).invest = this.parseDecimal(value);
  }

  updateTypeEtp(yearIdx: number, value: string): void {
    this.getTypeBudget(yearIdx).etp = this.parseDecimal(value);
  }

  // ════════════════════════════════════════════════
  // Mode 'by_org' helpers (ventilation par organisme, totaux)
  // ════════════════════════════════════════════════

  getOrgByOrgData(yearIdx: number, orgId: number): { budget: number | null; etp: number | null } {
    const key = `${yearIdx}-${orgId}`;
    if (!this.orgByOrgData[key]) {
      this.orgByOrgData[key] = { budget: null, etp: null };
    }
    return this.orgByOrgData[key];
  }

  updateOrgByOrgBudget(yearIdx: number, orgId: number, value: string): void {
    this.getOrgByOrgData(yearIdx, orgId).budget = this.parseDecimal(value);
  }

  updateOrgByOrgEtp(yearIdx: number, orgId: number, value: string): void {
    this.getOrgByOrgData(yearIdx, orgId).etp = this.parseDecimal(value);
  }

  getByOrgYearTotalBudget(yearIdx: number): number {
    let total = 0;
    for (const org of this.availableOrganismes()) {
      total += this.getOrgByOrgData(yearIdx, org.id_organisme).budget || 0;
    }
    return total;
  }

  getByOrgYearTotalEtp(yearIdx: number): number {
    let total = 0;
    for (const org of this.availableOrganismes()) {
      total += this.getOrgByOrgData(yearIdx, org.id_organisme).etp || 0;
    }
    return total;
  }

  // ════════════════════════════════════════════════
  // Programmation mensuelle (template unique pour toutes les années)
  // ════════════════════════════════════════════════

  toggleMensuelleDefaut(month: string): void {
    this.programmationMensuelleDefaut[month] = !this.programmationMensuelleDefaut[month];
  }

  // ════════════════════════════════════════════════
  // Finances
  // ════════════════════════════════════════════════

  addFinance(): void {
    this.finances.push({ libelle: '', id_categorie: null });
  }

  removeFinance(index: number): void {
    this.finances.splice(index, 1);
  }

  // ════════════════════════════════════════════════
  // Fréquence
  // ════════════════════════════════════════════════

  incrementFrequence(): void {
    const current = this.form.get('frequence_nombre')?.value || 0;
    this.form.patchValue({ frequence_nombre: current + 1 });
  }

  decrementFrequence(): void {
    const current = this.form.get('frequence_nombre')?.value || 0;
    if (current > 1) {
      this.form.patchValue({ frequence_nombre: current - 1 });
    }
  }
}
