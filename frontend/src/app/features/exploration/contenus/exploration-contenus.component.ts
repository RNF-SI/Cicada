import { CommonModule } from '@angular/common';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  EXPLORATION_ONGLETS,
  ExplorationContenu,
  ExplorationCriteres,
  ExplorationOnglet,
  ExplorationTri,
  ExplorationType,
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

/** Une puce de filtre actif, avec de quoi la retirer. */
interface PuceFiltre {
  cle: keyof ExplorationCriteres;
  valeur: string | number;
  label: string;
}

/**
 * Résultats du mode « rechercher un contenu d'un plan de gestion ».
 *
 * Même charpente que le mode « plan de gestion » — critères dans l'URL, barre
 * latérale partagée — plus trois éléments qui lui sont propres : les onglets
 * typés avec leurs compteurs, les puces de filtres actifs, et le switch
 * « rechercher dans les titres uniquement ».
 */
@Component({
  selector: 'app-exploration-contenus',
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
  templateUrl: './exploration-contenus.component.html',
  styleUrl: './exploration-contenus.component.scss',
})
export class ExplorationContenusComponent {
  private readonly exploration = inject(ExplorationService);
  private readonly translate = inject(TranslateService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  /**
   * Identifiant de fiche à mettre dans le lien d'une tuile.
   *
   * En fédération, deux instances produisent couramment le même slug pour des
   * plans différents : lier par slug nu ouvrirait l'homonyme local au lieu du
   * plan cliqué, sans rien signaler (#636).
   */
  protected readonly referencePlan = referencePlan;

  readonly criteres = signal<ExplorationCriteres>({});
  readonly motCle = signal('');
  readonly resultats = signal<ExplorationContenu[]>([]);
  readonly compteurs = signal<Record<string, number>>({});
  readonly total = signal(0);
  /**
   * #651 — La recherche n'a trouvé aucun résultat exact et montre des termes
   * approchants. Le dire, sinon l'utilisateur prend l'à-peu-près pour une
   * réponse.
   */
  readonly approximatif = signal(false);
  readonly pageCourante = signal(1);
  readonly nombrePages = signal(1);
  readonly chargement = signal(false);
  readonly erreur = signal(false);

  readonly onglets = EXPLORATION_ONGLETS;

  readonly optionsTri = [
    { value: 'pertinence', label: 'exploration.sort.pertinence' },
    { value: 'alphabetique', label: 'exploration.sort.alphabetique' },
    { value: 'recent', label: 'exploration.sort.recent' },
  ];

  readonly triCourant = computed(() => this.criteres().tri ?? 'pertinence');

  /**
   * Clé de l'onglet actif, déduite des types qu'il couvre. « Tout » dès que
   * l'URL ne porte pas d'onglet, ou qu'elle porte une combinaison qui ne
   * correspond à aucun onglet.
   */
  readonly ongletCourant = computed(() => {
    const actifs = this.criteres().onglet ?? [];
    if (!actifs.length) {
      return 'tout';
    }
    const onglet = EXPLORATION_ONGLETS.find(
      (candidat) =>
        candidat.types.length === actifs.length &&
        candidat.types.every((type) => actifs.includes(type)),
    );
    return onglet?.cle ?? 'tout';
  });

  readonly pages = computed(() =>
    Array.from({ length: this.nombrePages() }, (_, index) => index + 1),
  );

  /**
   * Entrées du dropdown « Type de données ». Elles épousent les onglets, donc
   * « Objectifs » y est une seule ligne couvrant les deux types.
   */
  readonly optionsTypes = computed(() =>
    EXPLORATION_ONGLETS.map((onglet) => ({
      value: onglet.cle,
      label: this.translate.instant(onglet.label),
    })),
  );

  /**
   * Clés d'onglet touchées par le filtre `types` courant.
   *
   * Couverture partielle suffisante : le groupe « Objectifs » de la barre
   * latérale peut ne retenir que les objectifs à long terme, auquel cas le
   * dropdown doit tout de même montrer « Objectifs » comme restreint plutôt
   * que d'afficher « Toutes les données ».
   */
  readonly typesSelectionnes = computed(() => {
    const types = this.criteres().types ?? [];
    return EXPLORATION_ONGLETS.filter((onglet) =>
      onglet.types.some((type) => types.includes(type)),
    ).map((onglet) => onglet.cle);
  });

  readonly resumeTypes = computed(() => {
    const cles = this.typesSelectionnes();
    if (!cles.length) {
      return this.translate.instant('exploration.search.allData');
    }
    return EXPLORATION_ONGLETS.filter((onglet) => cles.includes(onglet.cle))
      .map((onglet) => this.translate.instant(onglet.label))
      .join(', ');
  });

  // Référentiels servant à libeller les puces de filtres actifs. Ils sont
  // mis en cache par le service : la barre latérale les a déjà chargés.
  private readonly zones = toSignal(this.exploration.zones(), { initialValue: [] });
  private readonly organismes = toSignal(this.exploration.organismes(), {
    initialValue: [],
  });

  /**
   * Puces des filtres actifs, affichées au-dessus des onglets.
   *
   * Seuls les filtres dont le libellé n'est pas déjà lisible dans la barre
   * latérale y figurent : zones, organismes et types d'aires — c'est ce que
   * montre la maquette.
   */
  readonly puces = computed<PuceFiltre[]>(() => {
    const c = this.criteres();
    const puces: PuceFiltre[] = [];

    const departements = new Map<number, string>();
    for (const region of this.zones()) {
      departements.set(region.id_area, region.nom);
      for (const departement of region.departements) {
        departements.set(departement.id_area, departement.nom);
      }
    }
    for (const zone of c.zones ?? []) {
      puces.push({
        cle: 'zones',
        valeur: zone,
        label: departements.get(zone) ?? String(zone),
      });
    }

    const organismes = new Map(
      this.organismes().map((organisme) => [organisme.id, organisme.nom_organisme]),
    );
    for (const organisme of c.organismes ?? []) {
      puces.push({
        cle: 'organismes',
        valeur: organisme,
        label: organismes.get(organisme) ?? String(organisme),
      });
    }

    for (const type of c.typesSite ?? []) {
      puces.push({ cle: 'typesSite', valeur: type, label: type });
    }

    return puces;
  });

  private derniersCriteresCharges: ExplorationCriteres | null = null;

  constructor() {
    this.route.queryParamMap.subscribe((params) => {
      const criteres = criteresDepuisUrl(params);
      this.criteres.set(criteres);
      this.motCle.set(criteres.q ?? '');
      this.chercher(criteres);
    });

    effect(() => {
      const criteres = this.criteres();
      if (criteres !== this.derniersCriteresCharges) {
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: criteresVersUrl(criteres),
          replaceUrl: true,
        });
      }
    });
  }

  private chercher(criteres: ExplorationCriteres): void {
    this.derniersCriteresCharges = criteres;
    this.chargement.set(true);
    this.erreur.set(false);

    this.exploration.chercherContenus(criteres).subscribe({
      next: (reponse) => {
        this.resultats.set(reponse.results);
        this.compteurs.set(reponse.compteurs ?? {});
        this.approximatif.set(reponse.approximatif === true);
        this.total.set(reponse.pagination.count);
        this.pageCourante.set(reponse.pagination.current_page);
        this.nombrePages.set(reponse.pagination.total_pages);
        this.chargement.set(false);
      },
      error: () => {
        this.resultats.set([]);
        this.compteurs.set({});
        this.approximatif.set(false);
        this.total.set(0);
        this.erreur.set(true);
        this.chargement.set(false);
      },
    });
  }

  /** Compteur d'un onglet : somme des types qu'il regroupe. */
  compteur(onglet: ExplorationOnglet): number {
    return onglet.types.reduce(
      (total, type) => total + (this.compteurs()[type] ?? 0),
      0,
    );
  }

  compteurTout(): number {
    return this.compteurs()['tout'] ?? 0;
  }

  lancerRecherche(): void {
    this.criteres.set({ ...this.criteres(), q: this.motCle().trim(), page: 1 });
  }

  effacerMotCle(): void {
    this.motCle.set('');
    this.lancerRecherche();
  }

  /** Le dropdown raisonne en clés d'onglet : on les redéploie en types. */
  majTypes(cles: string[]): void {
    const types = EXPLORATION_ONGLETS.filter((onglet) => cles.includes(onglet.cle))
      .flatMap((onglet) => onglet.types);
    this.criteres.set({ ...this.criteres(), types, page: 1 });
  }

  changerOnglet(onglet: ExplorationOnglet | null): void {
    this.criteres.set({
      ...this.criteres(),
      onglet: onglet ? onglet.types : [],
      page: 1,
    });
  }

  changerTri(tri: string | null): void {
    this.criteres.set({
      ...this.criteres(),
      tri: (tri ?? 'pertinence') as ExplorationTri,
      page: 1,
    });
  }

  retirerPuce(puce: PuceFiltre): void {
    const criteres = { ...this.criteres() };
    const valeurs = criteres[puce.cle] as (string | number)[] | undefined;
    (criteres as Record<string, unknown>)[puce.cle] =
      valeurs?.filter((valeur) => valeur !== puce.valeur) ?? [];
    this.criteres.set({ ...criteres, page: 1 });
  }

  reinitialiser(): void {
    this.criteres.set({
      q: this.criteres().q,
      titresSeulement: this.criteres().titresSeulement,
      tri: this.criteres().tri,
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

  /** Libellé de la ligne « parent » d'une tuile (« ↳ Objectif : … »). */
  libelleParent(contenu: ExplorationContenu): string {
    if (!contenu.parent_type) {
      return '';
    }
    return this.translate.instant(`exploration.results.parent.${contenu.parent_type}`);
  }

  libelleSites(contenu: ExplorationContenu): string {
    return contenu.plan.sites.map((site) => site.nom_site).join(', ');
  }

  periode(contenu: ExplorationContenu): string {
    const { annee_debut, annee_fin } = contenu.plan;
    if (!annee_debut && !annee_fin) {
      return '';
    }
    return `${annee_debut ?? '?'}-${annee_fin ?? '?'}`;
  }
}
