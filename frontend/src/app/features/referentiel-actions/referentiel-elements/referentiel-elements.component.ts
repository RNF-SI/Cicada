import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, Output, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  ElementAActualiser, ReferentielActionsService, ReferentielElements,
} from '../../../core/services/referentiel-actions.service';
import { AccordionComponent } from '../../../shared/components/accordion/accordion.component';
import {
  ChoisirCodeDialogComponent, ChoisirCodeDialogData, ChoisirCodeDialogResult,
} from '../../../shared/components/modals/choisir-code-dialog/choisir-code-dialog.component';

/**
 * #779 — éléments d'un référentiel (PressRef, TaxRef, HabRef) touchés par un
 * passage : à choisir (ancien code conservé), actualisés, changés
 * automatiquement (modifiables), plan par plan.
 */
@Component({
  selector: 'app-referentiel-elements',
  standalone: true,
  imports: [DatePipe, MatButtonModule, TranslateModule, AccordionComponent],
  templateUrl: './referentiel-elements.component.html',
  styleUrl: '../actions-a-actualiser.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ReferentielElementsComponent {
  private readonly service = inject(ReferentielActionsService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  @Input({ required: true }) referentiel!: ReferentielElements;
  @Input() planId: number | null = null;
  @Output() modifie = new EventEmitter<void>();

  readonly acceptation = signal(false);

  choisir(element: ElementAActualiser, mode: 'choix' | 'correction' = 'choix'): void {
    this.dialog.open<ChoisirCodeDialogComponent, ChoisirCodeDialogData, ChoisirCodeDialogResult>(
      ChoisirCodeDialogComponent, {
        width: '760px', maxWidth: '95vw', maxHeight: '90vh', autoFocus: 'dialog',
        data: { referentiel: this.referentiel.code, referentielLibelle: this.referentiel.libelle, element, mode },
      },
    ).afterClosed().subscribe(res => {
      if (!res) return;
      if (res.element) {
        this.snackBar.open(this.translate.instant('referentielActions.enregistre'),
          this.translate.instant('common.actions.close'), { duration: 3000 });
      }
      this.modifie.emit();
    });
  }

  accepterTout(): void {
    if (this.acceptation()) return;
    this.acceptation.set(true);
    this.service.accepterPropositionsReferentiel(this.referentiel.code, this.planId).subscribe({
      next: b => {
        this.acceptation.set(false);
        this.snackBar.open(this.translate.instant('referentielActions.code.accepterToutBilan', {
          acceptees: b.acceptees, plusieurs: b.plusieurs_options,
        }), this.translate.instant('common.actions.close'), { duration: 6000 });
        this.modifie.emit();
      },
      error: () => this.acceptation.set(false),
    });
  }
}
