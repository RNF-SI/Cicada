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
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import { Enjeu, EnjeuCreatePayload, EnjeuUpdatePayload } from '../../../../core/models/enjeu.model';

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
    HeaderComponent
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

  ngOnInit(): void {
    this.initForm();
    this.loadRouteParams();
  }

  private initForm(): void {
    this.form = this.fb.group({
      libelle: ['', [Validators.required, Validators.maxLength(500)]],
      intitule_court: ['', [Validators.maxLength(50)]],
      rang: [1, [Validators.required, Validators.min(1), Validators.max(3)]],
      categorie_ecologique: [true, Validators.required],
      habitat: [false],
      espece: [false],
      processus: [false],
      etat_enjeu: [''],
      description: ['']
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
      habitat: enjeu.habitat || false,
      espece: enjeu.espece || false,
      processus: enjeu.processus || false,
      etat_enjeu: enjeu.etat_enjeu || '',
      description: enjeu.description || ''
    });
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
      id_categorie: categorieId || 0, // Le backend devrait trouver l'ID si 0
      libelle: formValue.libelle,
      intitule_court: formValue.intitule_court || undefined,
      rang: formValue.rang,
      categorie_ecologique: formValue.categorie_ecologique,
      habitat: formValue.habitat,
      espece: formValue.espece,
      processus: formValue.processus,
      etat_enjeu: formValue.etat_enjeu || undefined,
      description: formValue.description || undefined
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
      habitat: formValue.habitat,
      espece: formValue.espece,
      processus: formValue.processus,
      etat_enjeu: formValue.etat_enjeu || undefined,
      description: formValue.description || undefined
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
      this.router.navigate(['/plans', slug, 'enjeux']);
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
