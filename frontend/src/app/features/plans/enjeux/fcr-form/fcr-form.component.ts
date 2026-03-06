/**
 * Composant formulaire pour créer ou modifier un FCR (Facteur Clé de Réussite).
 * Champs spécifiques aux FCR : catégorie FCR (Connaissance, Ancrage territorial, etc.).
 */
import { Component, OnInit, inject, signal, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatRadioModule } from '@angular/material/radio';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import { Enjeu, FcrCreatePayload, EnjeuUpdatePayload } from '../../../../core/models/enjeu.model';

interface FcrCategorieOption {
  id: number;
  mnemonique: string;
  label: string;
  translateKey: string;
}

@Component({
  selector: 'app-fcr-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatRadioModule,
    MatProgressSpinnerModule,
    MatExpansionModule,
    MatTooltipModule,
    MatSnackBarModule,
    TranslateModule,
    HeaderComponent
  ],
  templateUrl: './fcr-form.component.html',
  styleUrl: './fcr-form.component.scss'
})
export class FcrFormComponent implements OnInit {
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
  fcrId = signal<number | null>(null);
  isEditMode = signal(false);
  existingFcr = signal<Enjeu | null>(null);

  // ID de la nomenclature "FCR"
  fcrCategorieId = signal<number | null>(null);

  // Options de catégorie FCR
  fcrCategorieOptions = signal<FcrCategorieOption[]>([]);

  ngOnInit(): void {
    this.initForm();
    this.loadRouteParams();
  }

  private initForm(): void {
    this.form = this.fb.group({
      libelle: ['', [Validators.required, Validators.maxLength(500)]],
      intitule_court: ['', [Validators.maxLength(50)]],
      id_categorie_fcr: [null, Validators.required],
      description: ['']
    });
  }

  private loadRouteParams(): void {
    // Récupérer le slug du plan en remontant l'arbre des routes
    const slug = this.findRouteParam('slug');

    if (slug) {
      this.planSlug.set(slug);
    }

    // Récupérer l'ID du FCR si mode édition (FCRs keep numeric IDs in URLs)
    const fcrIdStr = this.route.snapshot.paramMap.get('fcrId');
    if (fcrIdStr) {
      this.fcrId.set(parseInt(fcrIdStr, 10));
      this.isEditMode.set(true);
    }

    this.loadData();
  }

  private loadData(): void {
    this.isLoadingData.set(true);

    // Charger le plan par slug
    const slug = this.planSlug();
    if (slug) {
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planNom.set(plan.nom);
        },
        error: () => {
          // Non bloquant
        }
      });
    }

    // Charger l'ID de la nomenclature FCR
    this.adminService.getNomenclatureByMnemonique('CATEGORIE_ENJEU', 'FCR').subscribe({
      next: (nomenclature) => {
        this.fcrCategorieId.set(nomenclature.id_nomenclature);
      },
      error: () => {
        // Fallback
      }
    });

    // Charger les catégories FCR
    this.adminService.getNomenclaturesByType('CATEGORIE_FCR').subscribe({
      next: (nomenclatures) => {
        const options: FcrCategorieOption[] = nomenclatures.map(n => ({
          id: n.id_nomenclature,
          mnemonique: n.mnemonique || '',
          label: n.label,
          translateKey: this.getTranslateKeyForFcrCategorie(n.mnemonique || '')
        }));
        this.fcrCategorieOptions.set(options);
        this.loadFcrIfEdit();
      },
      error: () => {
        // Utiliser des valeurs par défaut
        this.fcrCategorieOptions.set([
          { id: 0, mnemonique: 'CONNAISSANCE', label: 'Connaissance', translateKey: 'enjeux.fcrForm.connaissance' },
          { id: 0, mnemonique: 'ANCRAGE', label: 'Ancrage territorial', translateKey: 'enjeux.fcrForm.ancrage' },
          { id: 0, mnemonique: 'FONCTIONNEMENT', label: 'Fonctionnement de l\'aire protégée', translateKey: 'enjeux.fcrForm.fonctionnement' },
          { id: 0, mnemonique: 'AUTRE', label: 'Autre', translateKey: 'enjeux.fcrForm.autre' }
        ]);
        this.loadFcrIfEdit();
      }
    });
  }

  private getTranslateKeyForFcrCategorie(mnemonique: string): string {
    const mapping: Record<string, string> = {
      'CONNAISSANCE': 'enjeux.fcrForm.connaissance',
      'ANCRAGE': 'enjeux.fcrForm.ancrage',
      'FONCTIONNEMENT': 'enjeux.fcrForm.fonctionnement',
      'AUTRE': 'enjeux.fcrForm.autre'
    };
    return mapping[mnemonique] || 'enjeux.fcrForm.autre';
  }

  private loadFcrIfEdit(): void {
    const fcrId = this.fcrId();
    if (!fcrId) {
      this.isLoadingData.set(false);
      return;
    }

    this.enjeuService.getEnjeu(fcrId).subscribe({
      next: (fcr) => {
        this.existingFcr.set(fcr);
        this.populateForm(fcr);
        this.isLoadingData.set(false);
      },
      error: (error) => {
        this.errorMessage.set(
          this.translate.instant('enjeux.messages.loadError')
        );
        this.isLoadingData.set(false);
      }
    });
  }

  private populateForm(fcr: Enjeu): void {
    this.form.patchValue({
      libelle: fcr.libelle,
      intitule_court: fcr.intitule_court || '',
      id_categorie_fcr: fcr.id_categorie_fcr,
      description: fcr.description || ''
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
      this.updateFcr(formValue);
    } else {
      this.createFcr(formValue);
    }
  }

  private createFcr(formValue: any): void {
    const planId = this.planId();
    const categorieId = this.fcrCategorieId();

    if (!planId) {
      this.errorMessage.set('ID du plan manquant');
      this.isLoading.set(false);
      this.scrollToError();
      return;
    }

    const payload: FcrCreatePayload = {
      id_pg: planId,
      id_categorie: categorieId || 0, // Le backend devrait trouver l'ID si 0
      libelle: formValue.libelle,
      intitule_court: formValue.intitule_court || undefined,
      id_categorie_fcr: formValue.id_categorie_fcr,
      description: formValue.description || undefined
    };

    this.enjeuService.createFcr(payload).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.fcrCreateSuccess'),
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

  private updateFcr(formValue: any): void {
    const fcrId = this.fcrId();
    if (!fcrId) {
      this.errorMessage.set('ID du FCR manquant');
      this.isLoading.set(false);
      this.scrollToError();
      return;
    }

    const payload: EnjeuUpdatePayload = {
      libelle: formValue.libelle,
      intitule_court: formValue.intitule_court || undefined,
      id_categorie_fcr: formValue.id_categorie_fcr,
      description: formValue.description || undefined
    };

    this.enjeuService.updateEnjeu(fcrId, payload).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.fcrUpdateSuccess'),
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
    let route: ActivatedRoute | null = this.route;
    while (route) {
      const value = route.snapshot?.paramMap?.get(name);
      if (value) return value;
      route = route.parent;
    }
    return null;
  }

  // Helpers pour le template
  get intituleCourtLength(): number {
    return this.form.get('intitule_court')?.value?.length || 0;
  }
}
