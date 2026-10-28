import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { MatTabsModule } from '@angular/material/tabs';
import { forkJoin } from 'rxjs';

import {
  ActionAActualiser, ActionsAActualiserReponse, PlanAActualiser, ReferentielActionsService,
  ReferentielElements,
} from '../../core/services/referentiel-actions.service';
import { ReferentielElementsComponent } from './referentiel-elements/referentiel-elements.component';
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
  imports: [HeaderComponent, DatePipe, RouterLink, MatButtonModule, MatTabsModule, TranslateModule, AccordionComponent,
    ReferentielElementsComponent],
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
  /** #779 — PressRef, TaxRef, HabRef touchés par un passage. */
  readonly autres = signal<ReferentielElements[]>([]);

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
    forkJoin([this.service.aActualiser(this.planFiltre()),
              this.service.referentielsAActualiser(this.planFiltre())]).subscribe({
      next: ([d, autres]) => {
        this.donnees.set(d);
        this.autres.set(autres.referentiels);
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

  readonly acceptation = signal(false);

  /** « Accepter toutes les propositions » : actions à un seul équivalent (#776). */
  accepterTout(): void {
    if (this.acceptation()) return;
    this.acceptation.set(true);
    this.service.accepterPropositions(this.planFiltre()).subscribe({
      next: b => {
        this.acceptation.set(false);
        this.snackBar.open(this.translate.instant('referentielActions.accepterToutBilan', {
          acceptees: b.acceptees, plusieurs: b.plusieurs_options, suivi: b.suivi_requis,
        }), this.translate.instant('common.actions.close'), { duration: 6000 });
        this.charger();
      },
      error: () => {
        this.acceptation.set(false);
        this.erreur.set(true);
      },
    });
  }

  /** Choisir le type d'une action à actualiser, ou corriger un changement automatique. */
  choisirType(a: ActionAActualiser, mode: 'choix' | 'correction' = 'choix'): void {
    const data: ActualiserTypeDialogData = {
      operationId: a.id_operation,
      libelle: a.libelle,
      codeAffichage: a.code_affichage,
      ancienCode: a.ancien_code,
      ancienLibelle: a.ancien_libelle,
      options: a.options,
      note: a.note,
      typeActuelId: a.type_actuel_id,
      typeActuelCode: a.type_actuel_code,
      aUnSuivi: a.a_un_suivi,
      mode,
    };
    this.dialog.open<ActualiserTypeDialogComponent, ActualiserTypeDialogData, ActualiserTypeDialogResult>(
      ActualiserTypeDialogComponent, { data, width: '760px', maxWidth: '95vw', maxHeight: '90vh', autoFocus: 'dialog' },
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
