/**
 * Formulaire d'ajout / édition d'un « type de poste » d'un plan de gestion (#560, #579).
 *
 * Aucun champ nominatif (RGPD) : un poste est décrit par sa fonction et son
 * organisme, jamais par la personne qui l'occupe.
 *
 * Parcours d'ajout (#579) :
 *   1. Choisir la fonction (menu déroulant unique) ;
 *   2. si absente, « ajouter une nouvelle fonction » à la volée ;
 *   3. Nombre de personnes ayant ce type de poste → une ligne par personne
 *      (« Stagiaire 1 », « Stagiaire 2 »…), chacune avec SON organisme.
 *
 * Chaque personne devient un enregistrement `Poste` distinct (`nombre = 1`)
 * partageant la même fonction : c'est le seul moyen de porter un organisme
 * par personne sans changer le modèle. L'ETP n'est plus saisi ici (#579).
 */
import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin } from 'rxjs';

import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';
import { RhService } from '../../../../core/services/rh.service';
import { AdminService } from '../../../../core/services/admin.service';
import { Fonction, Poste, PostePayload } from '../../../../core/models/rh.model';

export interface PosteFormDialogData {
  planId: number;
  /** Poste existant à éditer, ou null pour une création. */
  poste: Poste | null;
}

interface InstanceRow {
  /** Organisme de cette personne (ex. Stagiaire 1). */
  id_organisme: number | null;
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
    MatDialogModule, MatButtonModule, MatProgressSpinnerModule,
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

  // Fonction choisie (une seule par type de poste, #579)
  selectedFonctionId = signal<number | null>(null);

  // Ajout d'une fonction à la volée
  showNewFonction = signal(false);
  newFonctionLibelle = signal<string>('');
  isCreatingFonction = signal(false);

  // Création : une ligne (organisme) par personne ayant ce type de poste
  nombre = signal<number>(1);
  instances = signal<InstanceRow[]>([{ id_organisme: null }]);

  // Édition : un poste unique porte un seul organisme
  idOrganisme = signal<number | null>(null);

  // Référentiels
  allFonctions = signal<Fonction[]>([]);
  organismes = signal<OrganismeOption[]>([]);

  showError = signal(false);

  /** Libellé de la fonction choisie, pour intituler les lignes « Stagiaire 1 »… */
  selectedFonctionLabel = computed<string>(() => {
    const id = this.selectedFonctionId();
    return this.allFonctions().find((f) => f.id_fonction === id)?.libelle ?? '';
  });

  /** Erreur de formulaire, ou null. Une fonction est obligatoire. */
  formError = computed<string | null>(() => {
    if (this.selectedFonctionId() == null) {
      return this.translate.instant('plans.postes.form.errors.noFonctionSelected');
    }
    return null;
  });

  ngOnInit(): void {
    this.rhService.loadFonctions().subscribe((list) => this.allFonctions.set(list));
    this.loadOrganismes();

    const p = this.data.poste;
    if (p) {
      // Édition : on repart sur une fonction unique (la première du poste).
      this.selectedFonctionId.set(p.fonctions?.[0]?.id_fonction ?? null);
      this.idOrganisme.set(p.id_organisme ?? null);
      this.nombre.set(p.nombre ?? 1);
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

  /** Intitulé d'une ligne personne : « Stagiaire 1 », « Stagiaire 2 »… */
  instanceLabel(index: number): string {
    const fonction =
      this.selectedFonctionLabel() ||
      this.translate.instant('plans.postes.form.instanceGeneric');
    return this.translate.instant('plans.postes.form.instanceLabel', {
      fonction,
      index: index + 1,
    });
  }

  /** Ajuste le nombre de lignes personnes en préservant les organismes déjà saisis. */
  setNombre(value: number | string): void {
    const n = Math.max(1, Math.floor(Number(value) || 1));
    this.nombre.set(n);
    this.instances.update((rows) => {
      const next = rows.slice(0, n);
      while (next.length < n) next.push({ id_organisme: null });
      return next;
    });
  }

  setInstanceOrganisme(index: number, value: number | null): void {
    this.instances.update((rows) =>
      rows.map((r, i) => (i === index ? { ...r, id_organisme: value } : r)),
    );
  }

  toggleNewFonction(): void {
    this.showNewFonction.update((v) => !v);
  }

  /** Crée une fonction à la volée et la sélectionne directement. */
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
        this.selectedFonctionId.set(f.id_fonction);
        this.newFonctionLibelle.set('');
        this.showNewFonction.set(false);
        this.isCreatingFonction.set(false);
      },
      error: () => this.isCreatingFonction.set(false),
    });
  }

  save(): void {
    if (this.formError()) {
      this.showError.set(true);
      return;
    }
    this.showError.set(false);
    this.isSaving.set(true);
    this.errorMessage.set(null);

    const fonctions = [{ id_fonction: this.selectedFonctionId()!, pourcentage: null }];

    if (this.isEdit) {
      const payload: Partial<PostePayload> = {
        id_pg: this.data.planId,
        id_organisme: this.idOrganisme() ?? null,
        nombre: this.data.poste!.nombre || 1,
        fonctions,
      };
      this.rhService.updatePoste(this.data.poste!.id_poste!, payload).subscribe({
        next: (poste) => this.dialogRef.close(poste),
        error: () => {
          this.errorMessage.set('error');
          this.isSaving.set(false);
        },
      });
      return;
    }

    // Création : un poste (nombre = 1) par personne, chacun avec son organisme.
    const requests = this.instances().map((inst) =>
      this.rhService.createPoste({
        id_pg: this.data.planId,
        id_organisme: inst.id_organisme ?? null,
        nombre: 1,
        fonctions,
      }),
    );
    forkJoin(requests).subscribe({
      next: (postes) => this.dialogRef.close(postes),
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
