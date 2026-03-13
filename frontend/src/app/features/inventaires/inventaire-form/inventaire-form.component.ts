/**
 * Formulaire Suivi/Inventaire (standalone) - création + édition.
 */
import { Component, OnInit, inject, signal } from '@angular/core';
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
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { debounceTime, distinctUntilChanged, filter, switchMap } from 'rxjs/operators';
import { of } from 'rxjs';

import { HeaderComponent } from '../../../shared/components/header/header.component';
import { ReferenceItemListComponent } from '../../../shared/components/reference-item-list/reference-item-list.component';
import { ProtocoleCampanuleDialogComponent } from '../../../shared/components/modals/protocole-campanule-dialog/protocole-campanule-dialog.component';
import { InventaireService } from '../../../core/services/inventaire.service';
import { AdminService } from '../../../core/services/admin.service';
import { CampanuleService } from '../../../core/services/campanule.service';
import { SuiviInventaireDetail, SuiviInventaireCreatePayload } from '../../../core/models/inventaire.model';
import { TaxonRef, HabitatRef, GeologieRef } from '../../../core/models/enjeu.model';
import { CampanuleAutocomplete } from '../../../core/models/campanule.model';

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
    TranslateModule,
    HeaderComponent,
    ReferenceItemListComponent
  ],
  templateUrl: './inventaire-form.component.html',
  styleUrl: './inventaire-form.component.scss'
})
export class InventaireFormComponent implements OnInit {
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
  typeSuiviOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);
  statutSuiviOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);
  objectifSuiviOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);
  cibleSuiviOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);

  // Reference item lists (taxons / habitats)
  taxonItems: TaxonRef[] = [];
  habitatItems: HabitatRef[] = [];

  // Collapsible sections state
  sectionsOpen: Record<string, boolean> = {
    protocole: true,
    bancarisation: true,
    details: true
  };

  // Frequency units
  frequenceUnites: { value: string; label: string }[] = [];

  // CAMPanule autocomplete
  campanuleSearchCtrl = new FormControl('');
  campanuleResults = signal<CampanuleAutocomplete[]>([]);
  selectedCampanule = signal<CampanuleAutocomplete | null>(null);

  ngOnInit(): void {
    this.initFrequenceLabels();
    this.initForm();
    this.loadNomenclatures();
    this.initCampanuleAutocomplete();
    this.loadRouteParams();
  }

  private initFrequenceLabels(): void {
    this.frequenceUnites = [
      { value: 'jour', label: this.translate.instant('inventaires.form.uniteJour') },
      { value: 'semaine', label: this.translate.instant('inventaires.form.uniteSemaine') },
      { value: 'mois', label: this.translate.instant('inventaires.form.uniteMois') },
      { value: 'an', label: this.translate.instant('inventaires.form.uniteAn') },
    ];
  }

  private initForm(): void {
    this.form = this.fb.group({
      // Main card
      intitule: ['', [Validators.required, Validators.maxLength(500)]],
      prix_indicatif: [null],
      id_type_suivi: [null],
      integre_plan_gestion: [null],
      objectif_principal: [''],
      cibles_principales: [null],
      cible_secondaire: [''],
      annee_lancement_suivi: [null],
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
      // Bancarisation section
      outil_bancarisation: [''],
      outil_saisie: [''],
      transmission_donnee: [null],
      // Details section
      id_statut: [null],
      annee_fin_suivi: [null],
      frequence_nombre: [null],
      frequence_unite: [null],
      commentaires: [''],
    });
  }

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
    this.adminService.getNomenclaturesByType('TYPE_SUIVI').subscribe({
      next: (data) => this.typeSuiviOptions.set(data),
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
      prix_indicatif: suivi.prix_indicatif,
      id_type_suivi: suivi.id_type_suivi,
      integre_plan_gestion: suivi.integre_plan_gestion,
      objectif_principal: suivi.objectif_principal || '',
      cibles_principales: suivi.cibles_principales || '',
      cible_secondaire: suivi.cible_secondaire || '',
      annee_lancement_suivi: suivi.annee_lancement_suivi,
      // Bancarisation
      outil_bancarisation: suivi.outil_bancarisation || '',
      outil_saisie: suivi.outil_saisie || '',
      transmission_donnee: suivi.transmission_donnee,
      // Details
      id_statut: suivi.id_statut,
      annee_fin_suivi: suivi.annee_fin_suivi,
      frequence_nombre: suivi.frequence_nombre,
      frequence_unite: suivi.frequence_unite,
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

  cancel(): void {
    this.router.navigate(['/inventaires']);
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const fv = this.form.value;

    const payload: SuiviInventaireCreatePayload = {
      intitule: fv.intitule,
    };

    // Main fields
    if (fv.prix_indicatif != null) payload.prix_indicatif = fv.prix_indicatif;
    if (fv.id_type_suivi) payload.id_type_suivi = fv.id_type_suivi;
    if (fv.integre_plan_gestion != null) payload.integre_plan_gestion = fv.integre_plan_gestion;
    if (fv.objectif_principal?.trim()) payload.objectif_principal = fv.objectif_principal.trim();
    if (fv.cibles_principales) payload.cibles_principales = fv.cibles_principales;
    if (fv.cible_secondaire?.trim()) payload.cible_secondaire = fv.cible_secondaire.trim();
    // Serialize taxon/habitat reference lists to strings
    if (this.taxonItems.length > 0) {
      payload.taxon_taxref = this.taxonItems.map(t => t.nom_complet || String(t.cd_nom)).join(', ');
    }
    if (this.habitatItems.length > 0) {
      payload.habitat_ref = this.habitatItems.map(h => h.lb_hab_fr || h.cd_hab).join(', ');
    }
    if (fv.annee_lancement_suivi != null) payload.annee_lancement_suivi = fv.annee_lancement_suivi;

    // Bancarisation
    if (fv.outil_bancarisation?.trim()) payload.outil_bancarisation = fv.outil_bancarisation.trim();
    if (fv.outil_saisie?.trim()) payload.outil_saisie = fv.outil_saisie.trim();
    if (fv.transmission_donnee != null) payload.transmission_donnee = fv.transmission_donnee;

    // Details
    if (fv.id_statut) payload.id_statut = fv.id_statut;
    if (fv.annee_fin_suivi != null) payload.annee_fin_suivi = fv.annee_fin_suivi;
    if (fv.frequence_nombre != null) payload.frequence_nombre = fv.frequence_nombre;
    if (fv.frequence_unite) payload.frequence_unite = fv.frequence_unite;
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

    if (Object.keys(protocoleData).length > 0) {
      payload.protocole = protocoleData;
    }

    const request$ = this.isEditMode()
      ? this.inventaireService.updateInventaire(this.suiviId()!, payload)
      : this.inventaireService.createInventaire(payload);

    request$.subscribe({
      next: () => {
        this.isLoading.set(false);
        const msgKey = this.isEditMode()
          ? 'inventaires.messages.updateSuccess'
          : 'inventaires.messages.createSuccess';
        this.snackBar.open(
          this.translate.instant(msgKey),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.router.navigate(['/inventaires']);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(
          this.translate.instant('inventaires.errors.saveFailed')
        );
      }
    });
  }
}
