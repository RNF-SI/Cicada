import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { EXPLORATION_ONGLETS } from '../../core/models/exploration.model';
import {
  FilterDropdownComponent,
  FilterOptionListComponent,
  FilterPanelDirective,
} from '../../shared/components/filters';
import { ExplorationService } from '../../core/services/exploration.service';
import { SettingsService } from '../../core/services/settings.service';
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
  private readonly settings = inject(SettingsService);
  private readonly exploration = inject(ExplorationService);

  /**
   * #636 — Les structures qui alimentent la recherche.
   *
   * Sert à annoncer une portée **chiffrée** plutôt qu'un principe : « 4
   * structures participantes » se vérifie, « toutes les structures
   * participantes » laisse entière la question de savoir lesquelles.
   */
  private readonly instances = toSignal(this.exploration.instances(), {
    initialValue: [],
  });

  /**
   * #636 — L'exploration porte-t-elle sur toutes les structures, ou seulement
   * sur celle-ci ?
   *
   * Affiché avant même la recherche : découvrir après coup que le corpus est
   * restreint fait chercher une panne là où il y a un choix de la structure.
   */
  readonly partageActif = computed(() => this.settings.partageFederationActif());

  /** Nombre de structures qui alimentent la recherche. */
  readonly nombreStructures = computed(() => this.instances().length);

  /**
   * Clé du message de portée — chiffrée dès qu'on sait combien de structures
   * publient.
   *
   * On rend la clé et non le texte : la traduction reste faite par le pipe,
   * qui se réévalue quand le dictionnaire finit de charger. `instant()` dans un
   * `computed` ne dépend d'aucun signal et laisserait la clé brute à l'écran si
   * le premier rendu précédait le chargement.
   */
  readonly porteeCle = computed(() => {
    if (!this.partageActif()) {
      return 'exploration.portee.locale';
    }
    return this.nombreStructures() > 1
      ? 'exploration.portee.nationaleDetail'
      : 'exploration.portee.nationale';
  });

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
