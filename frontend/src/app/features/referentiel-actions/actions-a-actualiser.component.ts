import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  ActionAActualiser, ActionsAActualiserReponse, PlanAActualiser, ReferentielActionsService,
} from '../../core/services/referentiel-actions.service';
import { AccordionComponent } from '../../shared/components/accordion/accordion.component';
import {
  ActualiserTypeDialogComponent, ActualiserTypeDialogData, ActualiserTypeDialogResult,
} from '../../shared/components/modals/actualiser-type-dialog/actualiser-type-dialog.component';

/**
 * #751 — après un passage du référentiel des types d'action : les actions des
 * plans de l'utilisateur dont le type est à choisir, celles déjà actualisées
 * (par qui) et celles changées automatiquement sur une correspondance probable.
 * Page ouverte par la notification « Types d'action à actualiser ».
 */
@Component({
  selector: 'app-actions-a-actualiser',
  standalone: true,
  imports: [DatePipe, RouterLink, MatButtonModule, TranslateModule, AccordionComponent],
  templateUrl: './actions-a-actualiser.component.html',
  styleUrl: './actions-a-actualiser.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ActionsAActualiserComponent implements OnInit {
  private readonly service = inject(ReferentielActionsService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly route = inject(ActivatedRoute);

  readonly chargement = signal(true);
  readonly erreur = signal(false);
  readonly donnees = signal<ActionsAActualiserReponse | null>(null);
  readonly planFiltre = signal<number | null>(null);

  readonly plans = computed<PlanAActualiser[]>(() => this.donnees()?.plans ?? []);
  readonly totalActualisees = computed(() =>
    this.plans().reduce((n, p) => n + p.actualisees.length, 0));

  ngOnInit(): void {
    const plan = Number(this.route.snapshot.queryParamMap.get('plan'));
    this.planFiltre.set(Number.isFinite(plan) && plan > 0 ? plan : null);
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.service.aActualiser(this.planFiltre()).subscribe({
      next: d => {
        this.donnees.set(d);
        this.erreur.set(false);
        this.chargement.set(false);
      },
      error: () => {
        this.erreur.set(true);
        this.chargement.set(false);
      },
    });
  }

  ficheLink(plan: PlanAActualiser, a: ActionAActualiser): unknown[] | null {
    return plan.slug ? ['/plans', plan.slug, 'enjeux', 'operations', a.id_operation, 'fiche'] : null;
  }

  choisirType(a: ActionAActualiser): void {
    const data: ActualiserTypeDialogData = {
      operationId: a.id_operation,
      libelle: a.libelle,
      codeAffichage: a.code_affichage,
      ancienCode: a.ancien_code,
      ancienLibelle: a.ancien_libelle,
      suggestionId: a.suggestion_id,
      suggestionCode: a.suggestion_code,
      suggestionLibelle: a.suggestion_libelle,
      note: a.note,
      typeActuelId: a.type_actuel_id,
    };
    this.dialog.open<ActualiserTypeDialogComponent, ActualiserTypeDialogData, ActualiserTypeDialogResult>(
      ActualiserTypeDialogComponent, { data, width: '760px', maxWidth: '95vw', maxHeight: '90vh' },
    ).afterClosed().subscribe(res => {
      if (!res) return;
      if (res.operation) {
        this.snackBar.open(this.translate.instant('referentielActions.enregistre'),
          this.translate.instant('common.actions.close'), { duration: 3000 });
      }
      // Choix enregistré ou fait par un autre : la liste a changé dans les deux cas.
      this.charger();
    });
  }
}
