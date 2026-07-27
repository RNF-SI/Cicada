import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { EXPLORATION_ONGLETS } from '../../core/models/exploration.model';
import {
  FilterDropdownComponent,
  FilterOptionListComponent,
  FilterPanelDirective,
} from '../../shared/components/filters';
import { HeaderComponent } from '../../shared/components/header/header.component';

/** Les deux modes du sélecteur « Rechercher : ». */
type ModeExploration = 'contenu' | 'plan';

/**
 * Page d'accueil de l'exploration des données.
 *
 * Porte le choix du mode et la saisie initiale, puis délègue à la page de
 * résultats correspondante. Les critères transitent par l'URL : un résultat
 * reste ainsi partageable par simple copie du lien.
 */
@Component({
  selector: 'app-exploration',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    TranslateModule,
    HeaderComponent,
    FilterDropdownComponent,
    FilterOptionListComponent,
    FilterPanelDirective,
  ],
  templateUrl: './exploration.component.html',
  styleUrl: './exploration.component.scss',
})
export class ExplorationComponent {
  private readonly router = inject(Router);
  private readonly translate = inject(TranslateService);

  readonly mode = signal<ModeExploration>('contenu');
  readonly motCle = signal('');
  /** Clés d'onglet cochées dans le dropdown « Type de données ». */
  readonly types = signal<string[]>([]);

  readonly optionsTypes = computed(() =>
    EXPLORATION_ONGLETS.map((onglet) => ({
      value: onglet.cle,
      label: this.translate.instant(onglet.label),
    })),
  );

  /** Résumé affiché sous le libellé du dropdown : « Toutes » ou la liste choisie. */
  readonly resumeTypes = computed(() => {
    const choisis = this.types();
    if (!choisis.length) {
      return this.translate.instant('exploration.search.allData');
    }
    return EXPLORATION_ONGLETS.filter((onglet) => choisis.includes(onglet.cle))
      .map((onglet) => this.translate.instant(onglet.label))
      .join(', ');
  });

  changerMode(mode: ModeExploration): void {
    this.mode.set(mode);
  }

  rechercher(): void {
    const params: Record<string, string> = {};
    const motCle = this.motCle().trim();
    if (motCle) {
      params['q'] = motCle;
    }

    if (this.mode() === 'plan') {
      this.router.navigate(['/exploration/plans'], { queryParams: params });
      return;
    }

    // Le dropdown raisonne en onglets ; l'URL, en types de contenu.
    const types = EXPLORATION_ONGLETS.filter((onglet) =>
      this.types().includes(onglet.cle),
    ).flatMap((onglet) => onglet.types);
    if (types.length) {
      params['types'] = types.join(',');
    }
    this.router.navigate(['/exploration/contenus'], { queryParams: params });
  }
}
