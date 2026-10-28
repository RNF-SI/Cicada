import { ChangeDetectionStrategy, Component, inject, OnInit, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar } from '@angular/material/snack-bar';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  ReferentielActionsService, ReferentielDonnees,
} from '../../core/services/referentiel-actions.service';
import { downloadBlob } from '../../shared/utils/chart-image-export';

/**
 * #778 — « Référentiels de données » (bouton de l'accueil) : la version en
 * service sur l'instance de Gestref, PressRef, TaxRef et HabRef, et le
 * téléchargement de leurs données en CSV.
 */
@Component({
  selector: 'app-referentiels-donnees',
  standalone: true,
  imports: [HeaderComponent, DecimalPipe, RouterLink, MatButtonModule, TranslateModule],
  templateUrl: './referentiels-donnees.component.html',
  styleUrl: './referentiels-donnees.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ReferentielsDonneesComponent implements OnInit {
  private readonly service = inject(ReferentielActionsService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly referentiels = signal<ReferentielDonnees[]>([]);
  readonly chargement = signal(true);
  readonly erreur = signal(false);
  readonly telechargement = signal<string | null>(null);

  ngOnInit(): void {
    this.service.donnees().subscribe({
      next: r => {
        this.referentiels.set(r.referentiels);
        this.chargement.set(false);
      },
      error: () => {
        this.erreur.set(true);
        this.chargement.set(false);
      },
    });
  }

  telecharger(r: ReferentielDonnees): void {
    this.telechargement.set(r.code);
    this.service.telechargerCsv(r.code).subscribe({
      next: blob => {
        downloadBlob(`${r.version.code.toLowerCase()}.csv`, blob);
        this.telechargement.set(null);
      },
      error: () => {
        this.telechargement.set(null);
        this.snackBar.open(this.translate.instant('referentielsDonnees.erreurTelechargement'),
          this.translate.instant('common.actions.close'), { duration: 4000 });
      },
    });
  }
}
