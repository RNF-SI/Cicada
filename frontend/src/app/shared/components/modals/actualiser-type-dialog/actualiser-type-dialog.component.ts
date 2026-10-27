import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AdminService } from '../../../../core/services/admin.service';
import {
  ReferentielActionsService, TypeDejaModifie,
} from '../../../../core/services/referentiel-actions.service';
import {
  buildNomenclatureGroups, displayNomenclatureFn, getNomenclatureDepth, NomenclatureOption,
} from '../../../utils/nomenclature-autocomplete.utils';

export interface ActualiserTypeDialogData {
  operationId: number;
  libelle: string;
  codeAffichage?: string | null;
  ancienCode: string;
  ancienLibelle: string;
  suggestionId: number | null;
  suggestionCode: string;
  suggestionLibelle: string;
  note: string;
  /** Type affiché à l'ouverture (souvent vide) : sert à détecter un choix concurrent. */
  typeActuelId: number | null;
}

export interface ActualiserTypeDialogResult {
  /** Fiche de l'action renvoyée par le serveur après enregistrement. */
  operation?: unknown;
  /** Un autre référent a choisi le type entre-temps. */
  conflit?: TypeDejaModifie;
}

/**
 * #751 — choisir le nouveau type d'une action après un passage du référentiel
 * des types d'action. Fonctionne aussi dans un plan validé (seul le type change).
 */
@Component({
  selector: 'app-actualiser-type-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule, MatDialogModule, MatButtonModule, MatAutocompleteModule,
    MatFormFieldModule, MatInputModule, TranslateModule,
  ],
  templateUrl: './actualiser-type-dialog.component.html',
  styleUrl: './actualiser-type-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ActualiserTypeDialogComponent implements OnInit {
  private readonly dialogRef = inject(MatDialogRef<ActualiserTypeDialogComponent, ActualiserTypeDialogResult>);
  private readonly adminService = inject(AdminService);
  private readonly service = inject(ReferentielActionsService);
  private readonly translate = inject(TranslateService);
  readonly data: ActualiserTypeDialogData = inject(MAT_DIALOG_DATA);

  readonly options = signal<NomenclatureOption[]>([]);
  readonly recherche = signal('');
  readonly choisi = signal<NomenclatureOption | null>(null);
  readonly enregistrement = signal(false);
  readonly erreur = signal<string | null>(null);
  readonly conflit = signal<TypeDejaModifie | null>(null);
  readonly searchCtrl = new FormControl<string | NomenclatureOption>('');

  readonly groupes = computed(() => buildNomenclatureGroups(this.options(), this.recherche()));
  readonly suggestion = computed(() =>
    this.options().find(o => o.id_nomenclature === this.data.suggestionId) ?? null);

  readonly display = displayNomenclatureFn;
  readonly depth = getNomenclatureDepth;

  ngOnInit(): void {
    this.adminService.getNomenclaturesByType('TYPE_ACTION').subscribe({
      next: opts => this.options.set(opts as NomenclatureOption[]),
      error: () => this.options.set([]),
    });
    this.searchCtrl.valueChanges.subscribe(v => {
      if (typeof v === 'string') {
        this.recherche.set(v);
        if (this.choisi() && v !== this.display(this.choisi())) this.choisi.set(null);
      }
    });
  }

  choisir(option: NomenclatureOption): void {
    this.choisi.set(option);
    this.searchCtrl.setValue(option, { emitEvent: false });
  }

  utiliserSuggestion(): void {
    const s = this.suggestion();
    if (s) this.choisir(s);
  }

  effacer(): void {
    this.choisi.set(null);
    this.searchCtrl.setValue('');
  }

  annuler(): void {
    this.dialogRef.close();
  }

  valider(): void {
    const type = this.choisi();
    if (!type || this.enregistrement()) return;
    this.enregistrement.set(true);
    this.erreur.set(null);
    this.service.actualiserType(this.data.operationId, type.id_nomenclature, this.data.typeActuelId)
      .subscribe({
        next: operation => this.dialogRef.close({ operation }),
        error: (e: HttpErrorResponse) => {
          this.enregistrement.set(false);
          if (e.status === 409 && e.error?.code === 'type_deja_modifie') {
            this.conflit.set(e.error as TypeDejaModifie);
            return;
          }
          this.erreur.set(e.error?.detail || e.error?.id_type_action?.[0]
            || this.translate.instant('referentielActions.dialog.erreur'));
        },
      });
  }

  fermerSurConflit(): void {
    this.dialogRef.close({ conflit: this.conflit() ?? undefined });
  }
}
