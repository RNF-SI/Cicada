/**
 * Formulaire de création / édition d'un poste d'un plan de gestion (#560).
 *
 * Aucun champ nominatif (RGPD) : un poste est décrit par ses fonctions, le
 * nombre d'exemplaires (ex. 3 stagiaires), l'ETP TOTAL de l'ensemble et son
 * organisme.
 *
 * Deux façons de décrire les fonctions, exclusives l'une de l'autre :
 * - **quotités vides** → poste combiné (« garde animateur » à 1 ETP) : chaque
 *   fonction s'applique à tout le temps du poste ;
 * - **quotités renseignées** → répartition explicite (50 % / 50 %), dont la
 *   somme doit faire 100 %.
 */
import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';
import { RhService } from '../../../../core/services/rh.service';
import { AdminService } from '../../../../core/services/admin.service';
import { Fonction, Poste, PostePayload } from '../../../../core/models/rh.model';

export interface PosteFormDialogData {
  planId: number;
  /** Poste existant à éditer, ou null pour une création. */
  poste: Poste | null;
}

interface FonctionRow {
  id_fonction: number;
  libelle: string;
  finance_par_defaut: boolean;
  pourcentage: number | null;
}

interface OrganismeOption {
  id_organisme: number;
  nom_organisme: string;
}

@Component({
  selector: 'app-poste-form-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, TranslateModule,
    MatDialogModule, MatButtonModule, MatProgressSpinnerModule, MatSelectModule,
    FormFieldComponent,
  ],
  templateUrl: './poste-form-dialog.component.html',
  styleUrl: './poste-form-dialog.component.scss',
})
export class PosteFormDialogComponent implements OnInit {
  private readonly dialogRef = inject(MatDialogRef<PosteFormDialogComponent>);
  private readonly rhService = inject(RhService);
  private readonly adminService = inject(AdminService);
  private readonly translate = inject(TranslateService);
  readonly data = inject<PosteFormDialogData>(MAT_DIALOG_DATA);

  readonly isEdit = !!this.data.poste;
  isSaving = signal(false);
  errorMessage = signal<string | null>(null);

  // Champs du formulaire
  nombre = signal<number>(1);
  etp = signal<number | null>(null);
  idOrganisme = signal<number | null>(null);
  fonctions = signal<FonctionRow[]>([]);

  // Référentiels
  allFonctions = signal<Fonction[]>([]);
  organismes = signal<OrganismeOption[]>([]);
  selectedFonctionId = signal<number | null>(null);
  newFonctionLibelle = signal<string>('');
  isCreatingFonction = signal(false);

  /** Fonctions du référentiel pas encore ajoutées au poste. */
  availableFonctions = computed<Fonction[]>(() => {
    const used = new Set(this.fonctions().map((f) => f.id_fonction));
    return this.allFonctions().filter((f) => !used.has(f.id_fonction));
  });

  /** Le poste cumule ses fonctions (aucune quotité saisie). */
  isCombine = computed(() =>
    this.fonctions().length > 0 && this.fonctions().every((f) => f.pourcentage == null),
  );

  /** Somme des quotités, pour le contrôle des 100 %. */
  totalQuotite = computed(() =>
    this.fonctions().reduce((sum, f) => sum + (f.pourcentage ?? 0), 0),
  );

  /**
   * Message d'erreur des fonctions, ou null. Reproduit la règle du backend :
   * toutes les quotités, ou aucune ; et si quotités, somme = 100.
   */
  fonctionsError = computed<string | null>(() => {
    const rows = this.fonctions();
    if (rows.length === 0) return this.translate.instant('plans.postes.form.errors.noFonction');
    const renseignees = rows.filter((f) => f.pourcentage != null);
    if (renseignees.length === 0) return null;
    if (renseignees.length !== rows.length) {
      return this.translate.instant('plans.postes.form.errors.partialQuotite');
    }
    if (this.totalQuotite() !== 100) {
      return this.translate.instant('plans.postes.form.errors.sumQuotite', {
        total: this.totalQuotite(),
      });
    }
    return null;
  });

  showFonctionsError = signal(false);

  ngOnInit(): void {
    this.rhService.loadFonctions().subscribe((list) => this.allFonctions.set(list));
    this.loadOrganismes();

    const p = this.data.poste;
    if (p) {
      this.nombre.set(p.nombre ?? 1);
      this.etp.set(p.etp != null && p.etp !== '' ? Number(p.etp) : null);
      this.idOrganisme.set(p.id_organisme ?? null);
      this.fonctions.set(
        (p.fonctions || []).map((f) => ({
          id_fonction: f.id_fonction,
          libelle: f.fonction_libelle || '',
          finance_par_defaut: f.finance_par_defaut ?? true,
          pourcentage:
            f.pourcentage != null && f.pourcentage !== '' ? Number(f.pourcentage) : null,
        })),
      );
    }
  }

  /** Organismes proposés : ceux des sites du plan (mêmes que la ventilation). */
  private loadOrganismes(): void {
    this.adminService.getPlan(this.data.planId).subscribe({
      next: (plan: any) => {
        const map = new Map<number, OrganismeOption>();
        for (const site of plan.sites || []) {
          for (const org of site.organismes || []) {
            if (!map.has(org.id_organisme)) {
              map.set(org.id_organisme, {
                id_organisme: org.id_organisme,
                nom_organisme: org.nom_organisme,
              });
            }
          }
        }
        this.organismes.set(
          Array.from(map.values()).sort((a, b) =>
            a.nom_organisme.localeCompare(b.nom_organisme),
          ),
        );
      },
    });
  }

  addFonction(): void {
    const id = this.selectedFonctionId();
    if (id == null) return;
    const f = this.allFonctions().find((x) => x.id_fonction === id);
    if (!f) return;
    this.fonctions.update((rows) => [
      ...rows,
      {
        id_fonction: f.id_fonction,
        libelle: f.libelle,
        finance_par_defaut: f.finance_par_defaut,
        pourcentage: null,
      },
    ]);
    this.selectedFonctionId.set(null);
  }

  removeFonction(id: number): void {
    this.fonctions.update((rows) => rows.filter((r) => r.id_fonction !== id));
  }

  setPourcentage(id: number, value: string): void {
    const num = value === '' ? null : Number(value);
    this.fonctions.update((rows) =>
      rows.map((r) => (r.id_fonction === id ? { ...r, pourcentage: num } : r)),
    );
  }

  /** Répartit les quotités à parts égales entre les fonctions du poste. */
  repartirQuotites(): void {
    const rows = this.fonctions();
    if (rows.length === 0) return;
    const part = Math.round((100 / rows.length) * 100) / 100;
    this.fonctions.set(
      rows.map((r, i) => ({
        ...r,
        // La dernière absorbe l'arrondi pour que la somme fasse exactement 100.
        pourcentage: i === rows.length - 1
          ? Math.round((100 - part * (rows.length - 1)) * 100) / 100
          : part,
      })),
    );
  }

  /** Repasse le poste en « cumul de fonctions » (aucune quotité). */
  effacerQuotites(): void {
    this.fonctions.update((rows) => rows.map((r) => ({ ...r, pourcentage: null })));
  }

  /** Crée une fonction à la volée et l'ajoute directement au poste. */
  createFonction(): void {
    const libelle = this.newFonctionLibelle().trim();
    if (!libelle || this.isCreatingFonction()) return;
    this.isCreatingFonction.set(true);
    this.rhService.createFonction(libelle).subscribe({
      next: (f) => {
        if (!this.allFonctions().some((x) => x.id_fonction === f.id_fonction)) {
          this.allFonctions.update((list) =>
            [...list, f].sort((a, b) => a.libelle.localeCompare(b.libelle)),
          );
        }
        if (!this.fonctions().some((r) => r.id_fonction === f.id_fonction)) {
          this.fonctions.update((rows) => [
            ...rows,
            {
              id_fonction: f.id_fonction,
              libelle: f.libelle,
              finance_par_defaut: f.finance_par_defaut,
              pourcentage: null,
            },
          ]);
        }
        this.newFonctionLibelle.set('');
        this.isCreatingFonction.set(false);
      },
      error: () => this.isCreatingFonction.set(false),
    });
  }

  save(): void {
    if (this.fonctionsError()) {
      this.showFonctionsError.set(true);
      return;
    }
    this.showFonctionsError.set(false);
    this.isSaving.set(true);
    this.errorMessage.set(null);

    const payload: PostePayload = {
      id_pg: this.data.planId,
      id_organisme: this.idOrganisme() ?? null,
      nombre: this.nombre() || 1,
      etp: this.etp(),
      fonctions: this.fonctions().map((f) => ({
        id_fonction: f.id_fonction,
        pourcentage: f.pourcentage,
      })),
    };

    const request$ = this.isEdit
      ? this.rhService.updatePoste(this.data.poste!.id_poste!, payload)
      : this.rhService.createPoste(payload);

    request$.subscribe({
      next: (poste) => this.dialogRef.close(poste),
      error: () => {
        this.errorMessage.set('error');
        this.isSaving.set(false);
      },
    });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
