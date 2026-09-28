import { CommonModule } from '@angular/common';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';

import {
  ExplorationCriteres,
  ExplorationPlan,
  ExplorationTri,
  referencePlan,
} from '../../../core/models/exploration.model';
import { ExplorationService } from '../../../core/services/exploration.service';
import {
  FilterDropdownComponent,
  FilterOptionListComponent,
  FilterPanelDirective,
} from '../../../shared/components/filters';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { criteresDepuisUrl, criteresVersUrl } from '../exploration-url';
import { ExplorationFiltresComponent } from '../filtres/exploration-filtres.component';

/**
 * Résultats du mode « rechercher un plan de gestion ».
 *
 * Les critères vivent dans l'URL : la page les lit au chargement et les y
 * réécrit à chaque changement. Un résultat est ainsi partageable par copie du
 * lien, et le bouton « précédent » du navigateur remonte la recherche
 * précédente au lieu de sortir de la page.
 */
@Component({
  selector: 'app-exploration-plans',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    TranslateModule,
    HeaderComponent,
    ExplorationFiltresComponent,
    FilterDropdownComponent,
    FilterOptionListComponent,
    FilterPanelDirective,
  ],
  templateUrl: './exploration-plans.component.html',
  styleUrl: './exploration-plans.component.scss',
})
export class ExplorationPlansComponent {
  private readonly exploration = inject(ExplorationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  /** Voir `referencePlan` : le slug seul ne suffit pas en fédération (#636). */
  protected readonly referencePlan = referencePlan;

  readonly criteres = signal<ExplorationCriteres>({});
  readonly motCle = signal('');
  readonly resultats = signal<ExplorationPlan[]>([]);
  readonly total = signal(0);
  readonly pageCourante = signal(1);
  readonly nombrePages = signal(1);
  readonly chargement = signal(false);
  readonly erreur = signal(false);

  readonly optionsTri = [
    { value: 'pertinence', label: 'exploration.sort.pertinence' },
    { value: 'alphabetique', label: 'exploration.sort.alphabetique' },
    { value: 'recent', label: 'exploration.sort.recent' },
  ];

  readonly triCourant = computed(() => this.criteres().tri ?? 'pertinence');

  /** Numéros de page affichés par la pagination. */
  readonly pages = computed(() =>
    Array.from({ length: this.nombrePages() }, (_, index) => index + 1),
  );

  constructor() {
    // L'URL est la source de vérité : toute navigation relance la recherche.
    this.route.queryParamMap.subscribe((params) => {
      const criteres = criteresDepuisUrl(params);
      this.criteres.set(criteres);
      this.motCle.set(criteres.q ?? '');
      this.chercher(criteres);
    });

    // Les changements venus de la barre latérale repassent par l'URL, ce qui
    // déclenche la recherche via l'abonnement ci-dessus. Un seul chemin de
    // mise à jour, donc pas de double requête ni d'état divergent.
    effect(() => {
      const criteres = this.criteres();
      if (criteres !== this.derniersCriteresCharges) {
        this.naviguer(criteres);
      }
    });
  }

  private derniersCriteresCharges: ExplorationCriteres | null = null;

  private naviguer(criteres: ExplorationCriteres): void {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: criteresVersUrl(criteres),
      replaceUrl: true,
    });
  }

  private chercher(criteres: ExplorationCriteres): void {
    this.derniersCriteresCharges = criteres;
    this.chargement.set(true);
    this.erreur.set(false);

    this.exploration.chercherPlans(criteres).subscribe({
      next: (reponse) => {
        this.resultats.set(reponse.results);
        this.total.set(reponse.pagination.count);
        this.pageCourante.set(reponse.pagination.current_page);
        this.nombrePages.set(reponse.pagination.total_pages);
        this.chargement.set(false);
      },
      error: () => {
        this.resultats.set([]);
        this.total.set(0);
        this.erreur.set(true);
        this.chargement.set(false);
      },
    });
  }

  lancerRecherche(): void {
    this.criteres.set({ ...this.criteres(), q: this.motCle().trim(), page: 1 });
  }

  effacerMotCle(): void {
    this.motCle.set('');
    this.lancerRecherche();
  }

  changerTri(tri: string | null): void {
    this.criteres.set({
      ...this.criteres(),
      tri: (tri ?? 'pertinence') as ExplorationTri,
      page: 1,
    });
  }

  allerPage(page: number): void {
    if (page < 1 || page > this.nombrePages() || page === this.pageCourante()) {
      return;
    }
    this.criteres.set({ ...this.criteres(), page });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /** Libellé de la ligne site d'une tuile : mono-site ou « Multisites : … ». */
  libelleSites(plan: ExplorationPlan): string {
    const noms = plan.sites.map((site) => site.nom_site);
    return noms.length <= 1 ? (noms[0] ?? '') : noms.join(', ');
  }

  periode(plan: ExplorationPlan): string {
    if (!plan.annee_debut && !plan.annee_fin) {
      return '';
    }
    return `${plan.annee_debut ?? '?'}-${plan.annee_fin ?? '?'}`;
  }
}
