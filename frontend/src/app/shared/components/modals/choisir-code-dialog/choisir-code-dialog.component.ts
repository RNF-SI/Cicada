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
  ElementAActualiser, ReferentielActionsService,
} from '../../../../core/services/referentiel-actions.service';
import { HabitatAutocompleteComponent } from '../../habitat-autocomplete/habitat-autocomplete.component';
import { TaxonAutocompleteComponent } from '../../taxon-autocomplete/taxon-autocomplete.component';
import {
  buildNomenclatureGroups, displayNomenclatureFn, getNomenclatureDepth, NomenclatureOption,
} from '../../../utils/nomenclature-autocomplete.utils';

export interface ChoisirCodeDialogData {
  referentiel: 'PRESSREF' | 'TAXREF' | 'HABREF';
  referentielLibelle: string;
  element: ElementAActualiser;
  /** `correction` : changer un code posé automatiquement. */
  mode?: 'choix' | 'correction';
}

export interface ChoisirCodeDialogResult {
  element?: ElementAActualiser;
  conflit?: { actualise_par: string; code_actuel: string };
}

/**
 * #779 — choisir (ou corriger) le code d'un élément après un passage de PressRef,
 * TaxRef ou HabRef : équivalents de la table en un clic, ou recherche libre
 * (nomenclature PressRef, recherche de taxon, recherche d'habitat).
 */
@Component({
  selector: 'app-choisir-code-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule, MatDialogModule, MatButtonModule, MatAutocompleteModule,
    MatFormFieldModule, MatInputModule, TranslateModule,
    TaxonAutocompleteComponent, HabitatAutocompleteComponent,
  ],
  templateUrl: './choisir-code-dialog.component.html',
  styleUrl: '../actualiser-type-dialog/actualiser-type-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ChoisirCodeDialogComponent implements OnInit {
  private readonly dialogRef = inject(MatDialogRef<ChoisirCodeDialogComponent, ChoisirCodeDialogResult>);
  private readonly adminService = inject(AdminService);
  private readonly service = inject(ReferentielActionsService);
  private readonly translate = inject(TranslateService);
  readonly data: ChoisirCodeDialogData = inject(MAT_DIALOG_DATA);

  /** Code choisi : un équivalent, ou le résultat de la recherche libre. */
  readonly choisi = signal<string | null>(null);
  readonly enregistrement = signal(false);
  readonly erreur = signal<string | null>(null);
  readonly conflit = signal<{ actualise_par: string; code_actuel: string } | null>(null);

  // Recherche libre : PressRef par la nomenclature, TaxRef / HabRef par leurs recherches.
  readonly typesPression = signal<NomenclatureOption[]>([]);
  readonly recherche = signal('');
  readonly rechercheCtrl = new FormControl<string | NomenclatureOption>('');
  readonly codeCtrl = new FormControl<number | null>(null);
  readonly groupes = computed(() => buildNomenclatureGroups(this.typesPression(), this.recherche(),
    { searchInDefinition: true }));
  readonly display = displayNomenclatureFn;
  readonly depth = getNomenclatureDepth;

  readonly propositions = computed(() => this.data.element.options.filter(
    o => this.data.mode !== 'correction' || o.code !== this.data.element.code_actuel));

  ngOnInit(): void {
    if (this.data.referentiel === 'PRESSREF') {
      this.adminService.getNomenclaturesByType('TYPE_PRESSION').subscribe({
        next: opts => this.typesPression.set(opts as NomenclatureOption[]),
        error: () => this.typesPression.set([]),
      });
      this.rechercheCtrl.valueChanges.subscribe(v => {
        if (typeof v === 'string') this.recherche.set(v);
      });
    }
    this.codeCtrl.valueChanges.subscribe(v => this.choisi.set(v !== null && v !== undefined ? String(v) : null));
  }

  choisirProposition(code: string): void {
    this.choisi.set(code);
  }

  choisirPression(o: NomenclatureOption): void {
    this.choisi.set(o.cd_nomenclature || o.mnemonique);
  }

  annuler(): void {
    this.dialogRef.close();
  }

  valider(): void {
    const code = this.choisi();
    if (!code || this.enregistrement()) return;
    this.enregistrement.set(true);
    this.erreur.set(null);
    this.service.actualiserElement(this.data.element.id, code, this.data.element.code_actuel).subscribe({
      next: element => this.dialogRef.close({ element }),
      error: (e: HttpErrorResponse) => {
        this.enregistrement.set(false);
        if (e.status === 409 && e.error?.code === 'code_deja_modifie') {
          this.conflit.set({ actualise_par: e.error.actualise_par, code_actuel: e.error.code_actuel });
          return;
        }
        this.erreur.set(e.error?.detail || e.error?.code?.[0]
          || this.translate.instant('referentielActions.dialog.erreur'));
      },
    });
  }

  fermerSurConflit(): void {
    this.dialogRef.close({ conflit: this.conflit() ?? undefined });
  }
}
