import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { TranslateModule } from '@ngx-translate/core';

import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';
import { TagComponent } from '../../../../shared/components/tag/tag.component';
import { RhService } from '../../../../core/services/rh.service';
import { Fonction, PersonnePlan, PersonnePlanPayload } from '../../../../core/models/rh.model';

export interface PersonneFormDialogData {
  planId: number;
  /** Personne existante à éditer, ou null pour une création. */
  personne: PersonnePlan | null;
}

interface FonctionRow {
  id_fonction: number;
  libelle: string;
  finance_par_defaut: boolean;
  pourcentage: number | null;
}

@Component({
  selector: 'app-personne-form-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, TranslateModule,
    MatDialogModule, MatButtonModule, MatProgressSpinnerModule, MatSelectModule,
    FormFieldComponent, TagComponent,
  ],
  templateUrl: './personne-form-dialog.component.html',
  styleUrl: './personne-form-dialog.component.scss',
})
export class PersonneFormDialogComponent implements OnInit {
  private readonly dialogRef = inject(MatDialogRef<PersonneFormDialogComponent>);
  private readonly rhService = inject(RhService);
  readonly data = inject<PersonneFormDialogData>(MAT_DIALOG_DATA);

  readonly isEdit = !!this.data.personne;
  isSaving = signal(false);
  errorMessage = signal<string | null>(null);

  // Champs du formulaire
  nom = signal<string>('');
  dateArrivee = signal<string | null>(null);
  dateDepart = signal<string | null>(null);
  fonctions = signal<FonctionRow[]>([]);

  // Référentiel
  allFonctions = signal<Fonction[]>([]);
  selectedFonctionId = signal<number | null>(null);
  newFonctionLibelle = signal<string>('');
  isCreatingFonction = signal(false);

  /** Fonctions du référentiel pas encore ajoutées à la personne. */
  availableFonctions = computed<Fonction[]>(() => {
    const used = new Set(this.fonctions().map((f) => f.id_fonction));
    return this.allFonctions().filter((f) => !used.has(f.id_fonction));
  });

  nomInvalid = signal(false);

  ngOnInit(): void {
    this.rhService.loadFonctions().subscribe((list) => this.allFonctions.set(list));
    const p = this.data.personne;
    if (p) {
      this.nom.set(p.nom);
      this.dateArrivee.set(p.date_arrivee ?? null);
      this.dateDepart.set(p.date_depart ?? null);
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

  /** Crée une fonction à la volée et l'ajoute directement à la personne. */
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
    const nom = this.nom().trim();
    if (!nom) {
      this.nomInvalid.set(true);
      return;
    }
    this.nomInvalid.set(false);
    this.isSaving.set(true);
    this.errorMessage.set(null);

    const payload: PersonnePlanPayload = {
      id_pg: this.data.planId,
      nom,
      date_arrivee: this.dateArrivee() || null,
      date_depart: this.dateDepart() || null,
      fonctions: this.fonctions().map((f) => ({
        id_fonction: f.id_fonction,
        pourcentage: f.pourcentage,
      })),
    };

    const request$ = this.isEdit
      ? this.rhService.updatePersonne(this.data.personne!.id_personne_plan!, payload)
      : this.rhService.createPersonne(payload);

    request$.subscribe({
      next: (personne) => this.dialogRef.close(personne),
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
