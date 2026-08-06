import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { TranslateModule } from '@ngx-translate/core';

import { FicheAction } from '../../../../core/models/exploration-fiche.model';
import { TagComponent } from '../../../../shared/components/tag/tag.component';

export interface ExplorationActionModaleData {
  action: FicheAction;
  /** Nom du plan, pour situer l'action quand la modale est ouverte seule. */
  planNom: string;
}

/**
 * Fiche action en **lecture seule**, ouverte depuis l'exploration (#634).
 *
 * Elle rend ce que l'API publique expose : le cadre de l'action (indicateur et
 * métriques suivis), sa programmation et ses acteurs. Le budget, les moyens
 * humains et le suivi des réalisations relèvent de la gestion interne de
 * l'organisme et ne sont pas publiés — c'est ce qui la distingue de la fiche
 * action interne, et pourquoi elle ne réutilise pas ce composant-là.
 *
 * Aucune requête : tout vient de la fiche du plan déjà chargée.
 */
@Component({
  selector: 'app-exploration-action-modale',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, TranslateModule, TagComponent],
  templateUrl: './exploration-action-modale.component.html',
  styleUrl: './exploration-action-modale.component.scss',
})
export class ExplorationActionModaleComponent {
  private readonly reference = inject(MatDialogRef<ExplorationActionModaleComponent>);
  readonly data = inject<ExplorationActionModaleData>(MAT_DIALOG_DATA);

  get action(): FicheAction {
    return this.data.action;
  }

  /** Période de programmation, ou chaîne vide si l'action n'en porte pas. */
  get periode(): string {
    const { annee_min, annee_max } = this.action;
    if (!annee_min && !annee_max) {
      return '';
    }
    return annee_min === annee_max ? String(annee_min) : `${annee_min ?? '?'}-${annee_max ?? '?'}`;
  }

  metriqueLibelle(metrique: { nom_metrique: string; unite: string | null }): string {
    return metrique.unite ? `${metrique.nom_metrique} (${metrique.unite})` : metrique.nom_metrique;
  }

  fermer(): void {
    this.reference.close();
  }
}
