/**
 * Composant formulaire pour créer ou modifier un Enjeu.
 * Champs spécifiques aux Enjeux : priorité, catégorie écologique, type (habitat/espèce/processus).
 */
import { Component, OnInit, inject, signal, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatRadioModule } from '@angular/material/radio';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { ReferenceItemListComponent } from '../../../../shared/components/reference-item-list/reference-item-list.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import { Enjeu, EnjeuCreatePayload, EnjeuUpdatePayload, TaxonRef, HabitatRef, GeologieRef } from '../../../../core/models/enjeu.model';

@Component({
  selector: 'app-enjeu-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatRadioModule,
    MatCheckboxModule,
    MatProgressSpinnerModule,
    MatExpansionModule,
    MatTooltipModule,
    MatSnackBarModule,
    TranslateModule,
    HeaderComponent,
    ReferenceItemListComponent
  ],
  templateUrl: './enjeu-form.component.html',
  styleUrl: './enjeu-form.component.scss'
})
export class EnjeuFormComponent implements OnInit {
  private readonly elRef = inject(ElementRef);
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
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  enjeuId = signal<number | null>(null);
  enjeuSlug = signal<string | null>(null);
  isEditMode = signal(false);
  existingEnjeu = signal<Enjeu | null>(null);

  // ID de la nomenclature "ENJEU" (à récupérer dynamiquement)
  enjeuCategorieId = signal<number | null>(null);

  // Listes de taxons, habitats et géologies liés à l'enjeu
  taxonItems: TaxonRef[] = [];
  habitatItems: HabitatRef[] = [];
  geologieItems: GeologieRef[] = [];

  ngOnInit(): void {
    this.initForm();
    this.loadRouteParams();
  }

  private initForm(): void {
    this.form = this.fb.group({
      libelle: ['', [Validators.required, Validators.maxLength(500)]],
      intitule_court: ['', [Validators.maxLength(25)]],
      rang: [1, [Validators.required, Validators.min(1), Validators.max(3)]],
      categorie_ecologique: [true, Validators.required],
      // Checkboxes écologiques
      habitat: [false],
      espece: [false],
      patrimoine_geologique: [false],
      geo_ex_situ: [false],
      geo_in_situ: [false],
      fonctionnalite_ecosysteme: [false],
      autre_ecologique: [false],
      autre_ecologique_precision: [''],
      // Checkboxes socio-économiques
      valeur_paysagere: [false],
      patrimoine_culturel: [false],
      developpement_durable: [false],
      usages: [false],
      valeur_ajoutee: [false],
      autre_socioeco: [false],
      autre_socioeco_precision: [''],
      etat_enjeu: [''],
      description: ['']
    });

    // Réinitialiser les sous-champs géologiques quand patrimoine_geologique est décoché
    this.form.get('patrimoine_geologique')?.valueChanges.subscribe(isGeo => {
      if (!isGeo) {
        this.form.patchValue({
          geo_ex_situ: false,
          geo_in_situ: false
        }, { emitEvent: false });
      }
    });

    // Réinitialiser les listes quand les checkboxes sont décochées
    this.form.get('habitat')?.valueChanges.subscribe(isChecked => {
      if (!isChecked) {
        this.habitatItems = [];
      }
    });
    this.form.get('espece')?.valueChanges.subscribe(isChecked => {
      if (!isChecked) {
        this.taxonItems = [];
      }
    });
    this.form.get('patrimoine_geologique')?.valueChanges.subscribe(isChecked => {
      if (!isChecked) {
        this.geologieItems = [];
      }
    });

    // Réinitialiser les checkboxes de l'autre catégorie lors du changement
    this.form.get('categorie_ecologique')?.valueChanges.subscribe(isEcologique => {
      if (isEcologique) {
        // Réinitialiser les checkboxes socio-économiques
        this.form.patchValue({
          valeur_paysagere: false,
          patrimoine_culturel: false,
          developpement_durable: false,
          usages: false,
          valeur_ajoutee: false,
          autre_socioeco: false,
          autre_socioeco_precision: ''
        }, { emitEvent: false });
      } else {
        // Réinitialiser les checkboxes écologiques
        this.form.patchValue({
          habitat: false,
          espece: false,
          patrimoine_geologique: false,
          geo_ex_situ: false,
          geo_in_situ: false,
          fonctionnalite_ecosysteme: false,
          autre_ecologique: false,
          autre_ecologique_precision: ''
        }, { emitEvent: false });
      }
    });

    // Réinitialiser les précisions quand "autre" est décoché
    this.form.get('autre_ecologique')?.valueChanges.subscribe(isChecked => {
      if (!isChecked) {
        this.form.patchValue({ autre_ecologique_precision: '' }, { emitEvent: false });
      }
    });
    this.form.get('autre_socioeco')?.valueChanges.subscribe(isChecked => {
      if (!isChecked) {
        this.form.patchValue({ autre_socioeco_precision: '' }, { emitEvent: false });
      }
    });
  }

  private loadRouteParams(): void {
    // Récupérer le slug du plan en remontant l'arbre des routes
    const slug = this.findRouteParam('slug');

    if (slug) {
      this.planSlug.set(slug);
    }

    // Récupérer le slug de l'enjeu si mode édition
    const enjeuSlug = this.route.snapshot.paramMap.get('enjeuSlug');
    if (enjeuSlug) {
      this.enjeuSlug.set(enjeuSlug);
      this.isEditMode.set(true);
    }

    this.loadData();
  }

  private planLoaded = false;
  private nomenclatureLoaded = false;

  private loadData(): void {
    this.isLoadingData.set(true);
    this.planLoaded = false;
    this.nomenclatureLoaded = false;

    // Charger le plan par slug
    const slug = this.planSlug();
    if (slug) {
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planNom.set(plan.nom);
          this.planLoaded = true;
          this.tryLoadEnjeuIfEdit();
        },
        error: () => {
          this.planLoaded = true;
          this.tryLoadEnjeuIfEdit();
        }
      });
    } else {
      this.planLoaded = true;
    }

    // Charger l'ID de la nomenclature ENJEU
    this.adminService.getNomenclatureByMnemonique('CATEGORIE_ENJEU', 'ENJEU').subscribe({
      next: (nomenclature) => {
        this.enjeuCategorieId.set(nomenclature.id_nomenclature);
        this.nomenclatureLoaded = true;
        this.tryLoadEnjeuIfEdit();
      },
      error: () => {
        // Fallback - on continuera sans, le backend devrait gérer
        this.nomenclatureLoaded = true;
        this.tryLoadEnjeuIfEdit();
      }
    });
  }

  private tryLoadEnjeuIfEdit(): void {
    if (this.planLoaded && this.nomenclatureLoaded) {
      this.loadEnjeuIfEdit();
    }
  }

  private loadEnjeuIfEdit(): void {
    const slug = this.enjeuSlug();
    const planId = this.planId();
    if (!slug || !planId) {
      this.isLoadingData.set(false);
      return;
    }

    // Load all enjeux for the plan and find by slug
    this.enjeuService.getPlanEnjeux(planId).subscribe({
      next: (response) => {
        const all = [...response.enjeux, ...response.fcr];
        const enjeu = all.find(e => e.slug === slug);
        if (enjeu) {
          this.enjeuId.set(enjeu.id_enjeu);
          this.existingEnjeu.set(enjeu);
          this.populateForm(enjeu);
        } else {
          this.errorMessage.set(this.translate.instant('enjeux.messages.loadError'));
        }
        this.isLoadingData.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.loadError'));
        this.isLoadingData.set(false);
      }
    });
  }

  private populateForm(enjeu: Enjeu): void {
    this.form.patchValue({
      libelle: enjeu.libelle,
      intitule_court: enjeu.intitule_court || '',
      rang: enjeu.rang || 1,
      categorie_ecologique: enjeu.categorie_ecologique ?? true,
      // Écologique
      habitat: enjeu.habitat || false,
      espece: enjeu.espece || false,
      patrimoine_geologique: enjeu.patrimoine_geologique || false,
      geo_ex_situ: enjeu.geo_ex_situ || false,
      geo_in_situ: enjeu.geo_in_situ || false,
      fonctionnalite_ecosysteme: enjeu.fonctionnalite_ecosysteme || false,
      autre_ecologique: enjeu.autre_ecologique || false,
      autre_ecologique_precision: enjeu.autre_ecologique_precision || '',
      // Socio-économique
      valeur_paysagere: enjeu.valeur_paysagere || false,
      patrimoine_culturel: enjeu.patrimoine_culturel || false,
      developpement_durable: enjeu.developpement_durable || false,
      usages: enjeu.usages || false,
      valeur_ajoutee: enjeu.valeur_ajoutee || false,
      autre_socioeco: enjeu.autre_socioeco || false,
      autre_socioeco_precision: enjeu.autre_socioeco_precision || '',
      etat_enjeu: enjeu.etat_enjeu || '',
      description: enjeu.description || ''
    }, { emitEvent: false });

    // Charger les listes de taxons, habitats et géologies
    this.taxonItems = enjeu.taxons ? [...enjeu.taxons] : [];
    this.habitatItems = enjeu.habitats ? [...enjeu.habitats] : [];
    this.geologieItems = enjeu.geologies ? [...enjeu.geologies] : [];
  }

  onTaxonsChange(items: (TaxonRef | HabitatRef | GeologieRef)[]): void {
    this.taxonItems = items as TaxonRef[];
  }

  onHabitatsChange(items: (TaxonRef | HabitatRef | GeologieRef)[]): void {
    this.habitatItems = items as HabitatRef[];
  }

  onGeologiesChange(items: (TaxonRef | HabitatRef | GeologieRef)[]): void {
    this.geologieItems = items as GeologieRef[];
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.scrollToError();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const formValue = this.form.value;

    if (this.isEditMode()) {
      this.updateEnjeu(formValue);
    } else {
      this.createEnjeu(formValue);
    }
  }

  private createEnjeu(formValue: any): void {
    const planId = this.planId();
    const categorieId = this.enjeuCategorieId();

    if (!planId) {
      this.errorMessage.set('ID du plan manquant');
      this.isLoading.set(false);
      this.scrollToError();
      return;
    }

    const payload: EnjeuCreatePayload = {
      id_pg: planId,
      id_categorie: categorieId || 0,
      libelle: formValue.libelle,
      intitule_court: formValue.intitule_court || undefined,
      rang: formValue.rang,
      categorie_ecologique: formValue.categorie_ecologique,
      // Écologique
      habitat: formValue.habitat,
      espece: formValue.espece,
      patrimoine_geologique: formValue.patrimoine_geologique,
      geo_ex_situ: formValue.geo_ex_situ,
      geo_in_situ: formValue.geo_in_situ,
      fonctionnalite_ecosysteme: formValue.fonctionnalite_ecosysteme,
      autre_ecologique: formValue.autre_ecologique,
      autre_ecologique_precision: formValue.autre_ecologique_precision || undefined,
      // Socio-économique
      valeur_paysagere: formValue.valeur_paysagere,
      patrimoine_culturel: formValue.patrimoine_culturel,
      developpement_durable: formValue.developpement_durable,
      usages: formValue.usages,
      valeur_ajoutee: formValue.valeur_ajoutee,
      autre_socioeco: formValue.autre_socioeco,
      autre_socioeco_precision: formValue.autre_socioeco_precision || undefined,
      etat_enjeu: formValue.etat_enjeu || undefined,
      description: formValue.description || undefined,
      // Listes de taxons, habitats et géologies
      taxons_data: this.taxonItems.length > 0 ? this.taxonItems : undefined,
      habitats_data: this.habitatItems.length > 0 ? this.habitatItems : undefined,
      geologies_data: this.geologieItems.length > 0 ? this.geologieItems : undefined,
    };

    this.enjeuService.createEnjeu(payload).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.enjeuCreateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.navigateBack();
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

  private updateEnjeu(formValue: any): void {
    const enjeuId = this.enjeuId();
    if (!enjeuId) {
      this.errorMessage.set('ID de l\'enjeu manquant');
      this.isLoading.set(false);
      this.scrollToError();
      return;
    }

    const payload: EnjeuUpdatePayload = {
      libelle: formValue.libelle,
      intitule_court: formValue.intitule_court || undefined,
      rang: formValue.rang,
      categorie_ecologique: formValue.categorie_ecologique,
      // Écologique
      habitat: formValue.habitat,
      espece: formValue.espece,
      patrimoine_geologique: formValue.patrimoine_geologique,
      geo_ex_situ: formValue.geo_ex_situ,
      geo_in_situ: formValue.geo_in_situ,
      fonctionnalite_ecosysteme: formValue.fonctionnalite_ecosysteme,
      autre_ecologique: formValue.autre_ecologique,
      autre_ecologique_precision: formValue.autre_ecologique_precision || undefined,
      // Socio-économique
      valeur_paysagere: formValue.valeur_paysagere,
      patrimoine_culturel: formValue.patrimoine_culturel,
      developpement_durable: formValue.developpement_durable,
      usages: formValue.usages,
      valeur_ajoutee: formValue.valeur_ajoutee,
      autre_socioeco: formValue.autre_socioeco,
      autre_socioeco_precision: formValue.autre_socioeco_precision || undefined,
      etat_enjeu: formValue.etat_enjeu || undefined,
      description: formValue.description || undefined,
      // Listes de taxons, habitats et géologies
      taxons_data: this.taxonItems.length > 0 ? this.taxonItems : undefined,
      habitats_data: this.habitatItems.length > 0 ? this.habitatItems : undefined,
      geologies_data: this.geologieItems.length > 0 ? this.geologieItems : undefined,
    };

    this.enjeuService.updateEnjeu(enjeuId, payload).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.enjeuUpdateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.navigateBack();
      },
      error: (error) => {
        this.isLoading.set(false);
        this.errorMessage.set(
          error.message || this.translate.instant('enjeux.messages.updateError')
        );
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
    this.navigateBack();
  }

  private navigateBack(): void {
    const slug = this.planSlug();
    if (slug) {
      const enjeuSlug = this.enjeuSlug();
      this.router.navigate(['/plans', slug, 'enjeux'], enjeuSlug ? { fragment: enjeuSlug } : {});
    } else {
      this.router.navigate(['/plans']);
    }
  }

  private findRouteParam(name: string): string | null {
    for (const segment of this.route.snapshot.pathFromRoot) {
      const value = segment.paramMap.get(name);
      if (value) return value;
    }
    return null;
  }

  // Helpers pour le template
  get intituleCourtLength(): number {
    return this.form.get('intitule_court')?.value?.length || 0;
  }
}
