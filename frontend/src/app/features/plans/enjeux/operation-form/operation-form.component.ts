/**
 * Page dédiée formulaire opération (action) - création + édition.
 * Conforme au Figma node-id=154-10720.
 *
 * Refactorisé pour utiliser OperationAnnee[] (table relationnelle)
 * au lieu de JSONField programmation_annuelle/programmation_mensuelle.
 */
import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatRadioModule } from '@angular/material/radio';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import { Operation, OperationCreatePayload, OperationAnnee, FinanceOperation, SuiviInventaire } from '../../../../core/models/enjeu.model';
import { PlanSite } from '../../../../core/models/admin.model';

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
    MatSelectModule,
    MatCheckboxModule,
    MatRadioModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    TranslateModule,
    HeaderComponent
  ],
  templateUrl: './operation-form.component.html',
  styleUrl: './operation-form.component.scss'
})
export class OperationFormComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly enjeuService = inject(EnjeuService);
  private readonly adminService = inject(AdminService);
  private readonly translate = inject(TranslateService);
  private readonly snackBar = inject(MatSnackBar);

  form!: FormGroup;
  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);

  planId = signal<number | null>(null);
  planNom = signal<string>('');
  operationId = signal<number | null>(null);
  isEditMode = signal(false);
  existingOperation = signal<Operation | null>(null);

  // Query param: pré-lier un indicateur
  prelinkedIndicateurId = signal<number | null>(null);

  // Nomenclatures
  typeActionOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);
  prioriteOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);
  operateurOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);
  categorieFinanceOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);

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

  // Sites M2M checkboxes
  selectedSiteIds: Record<number, boolean> = {};

  // Suivi existant toggle
  estSuiviExistant = signal(false);

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

  // Frequency units
  frequenceUnites = [
    { value: 'jour', label: '' },
    { value: 'semaine', label: '' },
    { value: 'mois', label: '' },
    { value: 'an', label: '' }
  ];

  ngOnInit(): void {
    this.initFrequenceLabels();
    this.initForm();
    this.loadRouteParams();
  }

  private initFrequenceLabels(): void {
    this.frequenceUnites = [
      { value: 'jour', label: this.translate.instant('enjeux.operations.uniteJour') },
      { value: 'semaine', label: this.translate.instant('enjeux.operations.uniteSemaine') },
      { value: 'mois', label: this.translate.instant('enjeux.operations.uniteMois') },
      { value: 'an', label: this.translate.instant('enjeux.operations.uniteAn') }
    ];
  }

  private initForm(): void {
    this.form = this.fb.group({
      // Main card
      libelle: ['', [Validators.required, Validators.maxLength(500)]],
      id_type_action: [null],
      metrique_ids: [[]],
      id_priorite: [null],
      // Suivi/inventaire fields (nested in suivi_inventaire on save)
      objectif_principal: [''],
      cibles_principales: [null],
      taxon_taxref: [null],
      annee_lancement_suivi: [null],
      protocole_dans_campanule: [null],
      protocole_campanule_nom: [null],
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
      indicateur_ids: [[]]
    });
  }

  private loadRouteParams(): void {
    // Walk up the route tree to find the 'id' param (plan ID)
    const planIdStr = this.findRouteParam('id');
    if (planIdStr) {
      this.planId.set(parseInt(planIdStr, 10));
    }

    const opIdStr = this.route.snapshot.paramMap.get('operationId');
    if (opIdStr) {
      this.operationId.set(parseInt(opIdStr, 10));
      this.isEditMode.set(true);
    }

    const indicateurIdStr = this.route.snapshot.queryParamMap.get('indicateurId');
    if (indicateurIdStr) {
      this.prelinkedIndicateurId.set(parseInt(indicateurIdStr, 10));
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

    const planId = this.planId();
    if (planId) {
      this.adminService.getPlan(planId).subscribe({
        next: (plan) => {
          this.planNom.set(plan.nom);
          this.computeYears(plan.annee_debut, plan.annee_fin);
          // Extract plan sites
          if (plan.sites) {
            this.planSites.set(plan.sites);
            for (const site of plan.sites) {
              this.selectedSiteIds[site.id_site] = false;
            }
          }
        },
        error: () => {
          this.computeYears(null, null);
        }
      });

      this.enjeuService.getPlanEnjeux(planId).subscribe({
        next: (response) => {
          const indicateurs: { id_indicateur: number; nom_indicateur: string }[] = [];
          const metriques: { id_metrique: number; nom_metrique: string; indicateur_nom: string }[] = [];

          const allEnjeux = [...(response.enjeux || []), ...(response.fcr || [])];
          for (const enjeu of allEnjeux) {
            for (const olt of enjeu.objectifs_long_terme || []) {
              for (const ne of olt.niveaux_exigence || []) {
                for (const ind of ne.indicateurs || []) {
                  indicateurs.push({ id_indicateur: ind.id_indicateur, nom_indicateur: ind.nom_indicateur });
                  for (const met of ind.metriques || []) {
                    metriques.push({
                      id_metrique: met.id_metrique,
                      nom_metrique: met.nom_metrique,
                      indicateur_nom: ind.nom_indicateur
                    });
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
    } else {
      // No plan ID found: generate default years so tables render
      this.computeYears(null, null);
    }

    this.adminService.getNomenclaturesByType('TYPE_ACTION').subscribe({
      next: (options) => this.typeActionOptions.set(options),
      error: () => this.typeActionOptions.set([])
    });

    this.adminService.getNomenclaturesByType('PRIORITE_OPERATION').subscribe({
      next: (options) => this.prioriteOptions.set(options),
      error: () => this.prioriteOptions.set([])
    });

    this.adminService.getNomenclaturesByType('OPERATEUR_TYPE').subscribe({
      next: (options) => this.operateurOptions.set(options),
      error: () => this.operateurOptions.set([])
    });

    this.adminService.getNomenclaturesByType('CATEGORIE_FINANCE').subscribe({
      next: (options) => this.categorieFinanceOptions.set(options),
      error: () => this.categorieFinanceOptions.set([])
    });

    this.loadOperationIfEdit();
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
        id_operateur: null,
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
      const prelinkedId = this.prelinkedIndicateurId();
      if (prelinkedId) {
        this.form.patchValue({ indicateur_ids: [prelinkedId] });
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
      indicateur_ids: op.indicateur_ids || [],
      metrique_ids: op.metrique_ids || []
    });

    // Populate suivi fields from nested suivi_inventaire
    const suivi = op.suivi_inventaire;
    if (suivi) {
      this.form.patchValue({
        objectif_principal: suivi.objectif_principal || '',
        cibles_principales: suivi.cibles_principales || null,
        taxon_taxref: suivi.taxon_taxref || null,
        annee_lancement_suivi: suivi.annee_lancement_suivi || null,
        outil_bancarisation: suivi.outil_bancarisation || null,
        outil_saisie: suivi.outil_saisie || null,
        transmission_donnee: suivi.transmission_donnee ?? null,
      });

      // Populate protocole fields from nested protocole
      const proto = suivi.protocole;
      if (proto) {
        this.form.patchValue({
          protocole_dans_campanule: proto.protocole_dans_campanule ?? null,
          protocole_campanule_nom: proto.protocole_campanule_nom || null,
          respect_protocole: proto.respect_protocole ?? null,
          justification_non_respect: proto.justification_non_respect || '',
          differences_protocole: proto.differences_protocole || '',
          description_protocole: proto.description_protocole || '',
          objectif_protocole: proto.objectif_protocole || '',
          periode_echantillonnage: proto.periode_echantillonnage || '',
        });
      }
    }

    // Disable fields if est_suivi_existant
    if (op.est_suivi_existant) {
      this.setSuiviFieldsEnabled(false);
    }

    // Restore site selections
    if (op.site_ids) {
      for (const siteId of op.site_ids) {
        this.selectedSiteIds[siteId] = true;
      }
    }

    // Restore operation_annees from relational data
    if (op.operation_annees && op.operation_annees.length > 0) {
      // Merge server data with existing year slots
      for (const serverAnnee of op.operation_annees) {
        const idx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
        if (idx >= 0) {
          this.operationAnnees[idx] = { ...serverAnnee };
        } else {
          // Year from server not in plan range: add it
          this.operationAnnees.push({ ...serverAnnee });
          this.years.push(serverAnnee.annee);
        }
      }
      // Re-sort
      this.years.sort((a, b) => a - b);
      this.operationAnnees.sort((a, b) => a.annee - b.annee);
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
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const fv = this.form.value;

    // getRawValue() includes disabled fields (for readonly suivi mode)
    const rawFv = this.form.getRawValue();

    const payload: OperationCreatePayload = {
      libelle: fv.libelle,
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

    // Build nested suivi_inventaire from form fields (only if not in "existing suivi" mode)
    if (!this.estSuiviExistant()) {
      const suiviData: Record<string, unknown> = {};
      if (rawFv.objectif_principal?.trim()) suiviData['objectif_principal'] = rawFv.objectif_principal.trim();
      if (rawFv.cibles_principales) suiviData['cibles_principales'] = rawFv.cibles_principales;
      if (rawFv.taxon_taxref) suiviData['taxon_taxref'] = rawFv.taxon_taxref;
      if (rawFv.annee_lancement_suivi != null) suiviData['annee_lancement_suivi'] = rawFv.annee_lancement_suivi;
      if (rawFv.outil_bancarisation) suiviData['outil_bancarisation'] = rawFv.outil_bancarisation;
      if (rawFv.outil_saisie) suiviData['outil_saisie'] = rawFv.outil_saisie;
      if (rawFv.transmission_donnee != null) suiviData['transmission_donnee'] = rawFv.transmission_donnee;

      // Build nested protocole
      const protocoleData: Record<string, unknown> = {};
      if (rawFv.protocole_dans_campanule != null) protocoleData['protocole_dans_campanule'] = rawFv.protocole_dans_campanule;
      if (rawFv.protocole_campanule_nom) protocoleData['protocole_campanule_nom'] = rawFv.protocole_campanule_nom;
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
    if (fv.indicateur_ids?.length) payload.indicateur_ids = fv.indicateur_ids;
    if (fv.metrique_ids?.length) payload.metrique_ids = fv.metrique_ids;

    // Sites
    const siteIds = Object.entries(this.selectedSiteIds)
      .filter(([_, selected]) => selected)
      .map(([id, _]) => parseInt(id, 10));
    if (siteIds.length) payload.site_ids = siteIds;

    // Template mensuel (mêmes mois chaque année)
    payload.programmation_mensuelle_defaut = { ...this.programmationMensuelleDefaut };

    // Operation annees: apply the monthly template to all years
    const anneesToSave = this.operationAnnees.map(a => ({
      annee: a.annee,
      periodicite: a.periodicite,
      budget: a.budget,
      etp: a.etp,
      id_operateur: a.id_operateur || undefined,
      periodicite_mensuelle: { ...this.programmationMensuelleDefaut }
    }));

    const hasAnneeData = anneesToSave.some(
      a => a.periodicite || a.budget != null || a.etp != null || a.id_operateur != null ||
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
        }
      });
    }
  }

  goBack(): void {
    const planId = this.planId();
    if (planId) {
      this.router.navigate(['/plans', planId, 'enjeux']);
    } else {
      this.router.navigate(['/plans']);
    }
  }

  toggleSection(section: string): void {
    this.sectionsOpen[section] = !this.sectionsOpen[section];
  }

  setEstSuiviExistant(value: boolean): void {
    this.estSuiviExistant.set(value);
    if (value) {
      // When switching to "existing suivi" mode, disable suivi fields
      this.setSuiviFieldsEnabled(false);
    } else {
      // When switching back to manual mode, re-enable suivi fields
      this.setSuiviFieldsEnabled(true);
    }
  }

  private setSuiviFieldsEnabled(enabled: boolean): void {
    const fields = [
      'objectif_principal', 'cibles_principales', 'taxon_taxref',
      'annee_lancement_suivi', 'protocole_dans_campanule', 'protocole_campanule_nom',
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
      annee.id_operateur = null;
    }
  }

  updateBudget(index: number, value: string): void {
    this.operationAnnees[index].budget = value ? parseFloat(value) : null;
  }

  updateEtp(index: number, value: string): void {
    this.operationAnnees[index].etp = value ? parseFloat(value) : null;
  }

  updateOperateur(index: number, value: number | null): void {
    this.operationAnnees[index].id_operateur = value;
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
        id_operateur: first.id_operateur,
        periodicite_mensuelle: { ...first.periodicite_mensuelle }
      };
    }
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
