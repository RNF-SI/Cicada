
import { Component, computed, effect, inject, signal, ChangeDetectionStrategy } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  EXPLORATION_ONGLETS,
  EXPLORATION_PORTEES,
  ExplorationChampExtrait,
  ExplorationContenu,
  ExplorationCriteres,
  ExplorationMaillon,
  ExplorationOnglet,
  ExplorationTri,
  ExplorationType,
  SegmentTexte,
  referencePlan,
  segmenterSurTerme,
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

/** Où mène le clic sur une tuile (#683). */
interface LienTuile {
  commands: (string | number)[];
  queryParams: Record<string, string>;
  fragment?: string;
  /** Clé de traduction du libellé « Ouvre : … » affiché sur la tuile. */
  cible: 'arborescence' | 'ficheAction' | 'plan' | 'fichePublique';
}

/** Un extrait à afficher sous la tuile : le champ qui a répondu, et le passage. */
interface Motif {
  champ: ExplorationChampExtrait;
  extrait: string;
}

/**
 * Type de fragment compris par la page d'arborescence (`#<type>-<id>`), pour
 * chaque type de résultat. Les objectifs y portent leurs abréviations.
 */
const FRAGMENT_PAR_TYPE: Partial<Record<ExplorationType, string>> = {
  facteur: 'facteur',
  pression: 'pression',
  objectif_lt: 'olt',
  objectif_op: 'oo',
  indicateur: 'indicateur',
};

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
    FormsModule,
    RouterModule,
    TranslateModule,
    HeaderComponent,
    ExplorationFiltresComponent,
    FilterDropdownComponent,
    FilterOptionListComponent,
    FilterPanelDirective
],
  templateUrl: './exploration-contenus.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
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

  /**
   * Mots à surligner pour une tuile (#681).
   *
   * Ceux de la requête, lus dans les **critères** et non dans le champ de
   * saisie : le champ peut avoir été modifié sans que la recherche ait été
   * relancée. En repli approximatif, le serveur désigne le mot qu'il a
   * réellement retenu (« Flamant » pour « flamand ») : c'est lui qu'on montre.
   */
  protected termes(contenu: ExplorationContenu): string {
    const retenus = contenu.termes_surlignes ?? [];
    return retenus.length ? retenus.join(' ') : (this.criteres().q ?? '');
  }

  /** Découpe un texte pour surligner ce qui répond à la recherche (#650). */
  protected segments(texte: string, contenu: ExplorationContenu): SegmentTexte[] {
    return segmenterSurTerme(texte, this.termes(contenu));
  }

  private surligne(texte: string, contenu: ExplorationContenu): boolean {
    return this.segments(texte, contenu).some((segment) => segment.surligne);
  }

  /**
   * Pourquoi ce résultat est là, champ par champ (#650, #681).
   *
   * « Il ne doit pas y avoir de résultat dont on ne comprenne pas pourquoi il
   * est ressorti. » Le titre et les maillons de l'arborescence sont surlignés
   * sur place ; pour tout ce qui n'est pas affiché — espèce rattachée,
   * description, parent hors arbre, enfant — on montre le passage qui a
   * répondu. L'extrait du contexte est omis quand un maillon de l'arbre porte
   * déjà le surlignage : il répéterait ce que l'œil vient de voir.
   */
  protected motifs(contenu: ExplorationContenu): Motif[] {
    const extraits = contenu.extraits ?? {};
    const motifs: Motif[] = [];
    for (const champ of ['rattachements', 'description', 'contexte', 'enfants'] as const) {
      const extrait = extraits[champ];
      if (!extrait) {
        continue;
      }
      if (champ === 'contexte' && this.cheminSurligne(contenu)) {
        continue;
      }
      motifs.push({ champ, extrait });
    }
    return motifs;
  }

  /** Vrai si un maillon de l'ascendance porte le mot cherché. */
  protected cheminSurligne(contenu: ExplorationContenu): boolean {
    return contenu.chemin.some((maillon) => this.surligne(maillon.libelle, contenu));
  }

  /**
   * Résultat sans aucun mot surligné nulle part : le dire plutôt que de
   * laisser croire à une erreur. Ne devrait pas arriver, mais une
   * radicalisation agressive ou un mot ignoré par le dictionnaire peuvent
   * y conduire.
   */
  protected sansSurlignage(contenu: ExplorationContenu): boolean {
    if (!this.criteres().q) {
      return false;
    }
    if (this.surligne(contenu.titre, contenu) || this.cheminSurligne(contenu)) {
      return false;
    }
    return !this.motifs(contenu).some((motif) => this.surligne(motif.extrait, contenu));
  }

  /**
   * Où mène le clic sur une tuile (#683).
   *
   * Vers l'**écran réel** du plan dès que celui-ci existe dans cette base :
   * la fiche action pour une action, l'arborescence ouverte sur la branche
   * et l'objet pour le reste. Un plan reçu d'une autre instance (#636) n'a
   * pas d'écran ici : sa fiche publique — l'instantané déposé — reste le
   * seul endroit où le montrer. Le mot cherché voyage dans `q` pour être
   * surligné à l'arrivée.
   */
  protected lien(contenu: ExplorationContenu): LienTuile {
    const queryParams: Record<string, string> = {};
    const termes = this.termes(contenu).trim();
    if (termes) {
      queryParams['q'] = termes;
    }

    if (!contenu.acces_direct) {
      return {
        commands: ['/exploration/plans', referencePlan(contenu.plan)],
        queryParams: { ...queryParams, focus: `${contenu.type_contenu}:${contenu.id_objet}` },
        cible: 'fichePublique',
      };
    }

    const slug = contenu.plan.slug;
    if (contenu.type_contenu === 'action') {
      return {
        commands: ['/plans', slug, 'enjeux', 'operations', contenu.id_objet, 'fiche'],
        queryParams,
        cible: 'ficheAction',
      };
    }
    if (!contenu.enjeu_slug) {
      return { commands: ['/plans', slug], queryParams, cible: 'plan' };
    }
    const fragment = FRAGMENT_PAR_TYPE[contenu.type_contenu];
    return {
      commands: ['/plans', slug, 'enjeux', contenu.enjeu_slug],
      queryParams,
      fragment: fragment ? `${fragment}-${contenu.id_objet}` : undefined,
      cible: 'arborescence',
    };
  }

  /** Libellé du type d'un maillon de l'arborescence. */
  protected libelleMaillon(maillon: ExplorationMaillon): string {
    return this.translate.instant(`exploration.chemin.${maillon.type}`);
  }

  /** Rappel de la portée active, affiché au-dessus des résultats (#686). */
  readonly resumePortee = computed(() => {
    const axes = this.criteres().portee ?? [];
    const base = this.translate.instant('exploration.portee.resume.base');
    const ajouts = EXPLORATION_PORTEES.filter((axe) => axes.includes(axe)).map((axe) =>
      this.translate.instant(`exploration.portee.resume.${axe}`),
    );
    return ajouts.length ? `${base} + ${ajouts.join(' + ')}` : base;
  });

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
      portee: this.criteres().portee,
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
