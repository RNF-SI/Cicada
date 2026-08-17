import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';

import {
  FicheAction,
  FicheEnjeu,
  FicheIndicateur,
  FicheMetrique,
  FichePalier,
  FichePlan,
} from '../../../core/models/exploration-fiche.model';
import { ExplorationService } from '../../../core/services/exploration.service';
import { AccordionComponent } from '../../../shared/components/accordion/accordion.component';
import {
  AnchorNavComponent,
  AnchorNavItem,
} from '../../../shared/components/anchor-nav/anchor-nav.component';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { TagComponent } from '../../../shared/components/tag/tag.component';
import {
  ExplorationActionModaleComponent,
} from './action-modale/exploration-action-modale.component';

/**
 * Fiche publique d'un plan de gestion, en lecture seule.
 *
 * Écran d'arrivée des résultats d'exploration. Il n'existe pas de maquette pour
 * cette page : sa structure reprend celle de la page plan et de l'arborescence
 * (bandeau vert, navigation par ancres, accordéons d'enjeux), amputée de tout
 * ce qui relève de la gestion interne.
 *
 * Le paramètre `focus=<type>:<id>` — posé par les tuiles de résultat — ouvre
 * l'enjeu contenant l'objet trouvé et le met en évidence : sans cela, arriver
 * sur un plan de deux cents objets pour en retrouver un seul serait pénible.
 */
@Component({
  selector: 'app-exploration-fiche',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    TranslateModule,
    HeaderComponent,
    AccordionComponent,
    AnchorNavComponent,
    TagComponent,
  ],
  templateUrl: './exploration-fiche.component.html',
  styleUrl: './exploration-fiche.component.scss',
})
export class ExplorationFicheComponent {
  private readonly exploration = inject(ExplorationService);
  private readonly route = inject(ActivatedRoute);
  private readonly dialog = inject(MatDialog);

  readonly plan = signal<FichePlan | null>(null);
  readonly chargement = signal(true);
  readonly introuvable = signal(false);

  /** Objet mis en évidence, sous la forme `type:id`. */
  readonly focus = signal<string | null>(null);
  readonly enjeuxOuverts = signal<number[]>([]);
  /**
   * Branches de l'arborescence repliées, sous la forme `olt:12` / `oo:4`.
   *
   * On mémorise les **fermées** et non les ouvertes : un plan bien rempli
   * s'ouvre entier, l'utilisateur replie ce qui l'encombre. L'inverse
   * l'obligerait à déplier branche par branche pour voir son plan (#634).
   */
  readonly branchesRepliees = signal<string[]>([]);

  /**
   * Actions rattachées à chaque indicateur, pour les afficher **dans**
   * l'arborescence et non seulement dans la liste à plat.
   *
   * Une action pend de son indicateur, ou d'une de ses métriques — les deux
   * chemins existent en base et se croisent (#634).
   */
  readonly actionsParIndicateur = computed<Map<number, FicheAction[]>>(() => {
    const plan = this.plan();
    const parIndicateur = new Map<number, FicheAction[]>();
    if (!plan) {
      return parIndicateur;
    }

    const indicateurDeMetrique = new Map<number, number>();
    for (const indicateur of this.tousLesIndicateurs(plan)) {
      for (const metrique of indicateur.metriques) {
        indicateurDeMetrique.set(metrique.id_metrique, indicateur.id_indicateur);
      }
    }

    for (const action of plan.actions) {
      const cibles = new Set<number>();
      if (action.id_indicateur) {
        cibles.add(action.id_indicateur);
      }
      for (const metrique of action.metriques) {
        const id = indicateurDeMetrique.get(metrique.id_metrique);
        if (id) {
          cibles.add(id);
        }
      }
      for (const id of cibles) {
        parIndicateur.set(id, [...(parIndicateur.get(id) ?? []), action]);
      }
    }
    return parIndicateur;
  });

  readonly ancres = computed<AnchorNavItem[]>(() => {
    const plan = this.plan();
    if (!plan) {
      return [];
    }
    const ancres: AnchorNavItem[] = [
      { id: 'apercu', label: 'exploration.fiche.apercu' },
    ];
    if (plan.enjeux.length) {
      ancres.push({ id: 'enjeux', label: 'exploration.fiche.enjeux' });
    }
    if (plan.actions.length) {
      ancres.push({ id: 'actions', label: 'exploration.fiche.actions' });
    }
    return ancres;
  });

  readonly periode = computed(() => {
    const plan = this.plan();
    if (!plan?.annee_debut && !plan?.annee_fin) {
      return '';
    }
    return `${plan?.annee_debut ?? '?'}-${plan?.annee_fin ?? '?'}`;
  });

  constructor() {
    this.route.paramMap.subscribe((params) => {
      const slug = params.get('slug');
      if (slug) {
        this.charger(slug);
      }
    });
    this.route.queryParamMap.subscribe((params) => {
      this.focus.set(params.get('focus'));
    });
  }

  private charger(slug: string): void {
    this.chargement.set(true);
    this.introuvable.set(false);

    this.exploration.fiche(slug).subscribe({
      next: (plan) => {
        this.plan.set(plan);
        this.chargement.set(false);
        this.ouvrirCible(plan);
      },
      error: () => {
        this.plan.set(null);
        this.introuvable.set(true);
        this.chargement.set(false);
      },
    });
  }

  /**
   * Déplie ce qui contient l'objet ciblé, puis fait défiler jusqu'à lui.
   *
   * Une action **ouvre sa fiche** : c'est la demande d'origine (« cliquer sur
   * la flèche doit amener à la fiche action », #634). Les autres types ouvrent
   * l'enjeu de leur branche, pour arriver à l'endroit de l'arborescence qui les
   * contient.
   */
  private ouvrirCible(plan: FichePlan): void {
    const cible = this.focus();
    if (!cible) {
      return;
    }

    const [type, brut] = cible.split(':');
    const id = Number(brut);

    const enjeu = plan.enjeux.find((candidat) => this.contient(candidat, cible));
    if (enjeu) {
      this.enjeuxOuverts.set([enjeu.id_enjeu]);
    }

    // Le défilement attend que l'accordéon soit rendu.
    setTimeout(() => {
      document
        .getElementById(this.ancreDe(cible))
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });

      if (type === 'action') {
        const action = plan.actions.find((candidate) => candidate.id_operation === id);
        if (action) {
          this.ouvrirAction(action);
        }
      }
    }, 300);
  }

  /** Ouvre la fiche action en lecture seule (#634). */
  ouvrirAction(action: FicheAction, evenement?: Event): void {
    evenement?.stopPropagation();
    this.dialog.open(ExplorationActionModaleComponent, {
      data: { action, planNom: this.plan()?.nom ?? '' },
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
    });
  }

  private contient(enjeu: FicheEnjeu, cible: string): boolean {
    return this.ancresDe(enjeu).includes(cible);
  }

  /** Toutes les ancres portées par un enjeu et sa descendance. */
  private ancresDe(enjeu: FicheEnjeu): string[] {
    const ancres = [`enjeu:${enjeu.id_enjeu}`];

    for (const facteur of enjeu.facteurs) {
      ancres.push(`facteur:${facteur.id_facteur_influence}`);
      for (const pression of facteur.pressions) {
        ancres.push(`pression:${pression.id_pression}`);
      }
    }
    for (const objectif of enjeu.objectifs_long_terme) {
      ancres.push(`objectif_lt:${objectif.id_olt}`);
      for (const niveau of objectif.niveaux_exigence) {
        for (const indicateur of niveau.indicateurs) {
          ancres.push(`indicateur:${indicateur.id_indicateur}`);
        }
      }
    }
    for (const objectif of enjeu.objectifs_operationnels) {
      ancres.push(`objectif_op:${objectif.id_oo}`);
      for (const resultat of objectif.resultats_attendus) {
        for (const indicateur of resultat.indicateurs) {
          ancres.push(`indicateur:${indicateur.id_indicateur}`);
        }
      }
    }
    return ancres;
  }

  ancreDe(cible: string): string {
    return `objet-${cible.replace(':', '-')}`;
  }

  /** Vrai si l'objet donné est celui que la recherche a fait remonter. */
  estCible(type: string, id: number): boolean {
    return this.focus() === `${type}:${id}`;
  }

  estOuvert(enjeu: FicheEnjeu): boolean {
    return this.enjeuxOuverts().includes(enjeu.id_enjeu);
  }

  basculerEnjeu(enjeu: FicheEnjeu, ouvert: boolean): void {
    const ouverts = this.enjeuxOuverts().filter((id) => id !== enjeu.id_enjeu);
    this.enjeuxOuverts.set(ouvert ? [...ouverts, enjeu.id_enjeu] : ouverts);
  }

  // ---------------------------------------------------------------- //
  // Arborescence : branches repliables et contenu d'un indicateur
  // ---------------------------------------------------------------- //

  estBrancheOuverte(cle: string): boolean {
    return !this.branchesRepliees().includes(cle);
  }

  basculerBranche(cle: string): void {
    const repliees = this.branchesRepliees();
    this.branchesRepliees.set(
      repliees.includes(cle) ? repliees.filter((c) => c !== cle) : [...repliees, cle],
    );
  }

  toutDeplier(): void {
    this.branchesRepliees.set([]);
  }

  toutReplier(): void {
    const plan = this.plan();
    if (!plan) {
      return;
    }
    const cles: string[] = [];
    for (const enjeu of plan.enjeux) {
      cles.push(...enjeu.objectifs_long_terme.map((olt) => `olt:${olt.id_olt}`));
      cles.push(...enjeu.objectifs_operationnels.map((oo) => `oo:${oo.id_oo}`));
    }
    this.branchesRepliees.set(cles);
  }

  /** Actions rattachées à un indicateur, pour l'afficher dans sa branche. */
  actionsDe(indicateur: FicheIndicateur): FicheAction[] {
    return this.actionsParIndicateur().get(indicateur.id_indicateur) ?? [];
  }

  /** Libellé d'une métrique, unité comprise quand elle en porte une. */
  libelleMetrique(metrique: FicheMetrique): string {
    return metrique.unite ? `${metrique.nom_metrique} (${metrique.unite})` : metrique.nom_metrique;
  }

  /** Classe de fond du palier, alignée sur la palette de scores du kit UI. */
  classePalier(palier: FichePalier): string {
    return [
      '',
      'bg-score-very-bad',
      'bg-score-bad',
      'bg-score-neutral',
      'bg-score-good',
      'bg-score-very-good',
    ][palier.niveau];
  }

  /** Tous les indicateurs du plan, quel que soit leur point d'accroche. */
  private tousLesIndicateurs(plan: FichePlan): FicheIndicateur[] {
    const indicateurs: FicheIndicateur[] = [];
    for (const enjeu of plan.enjeux) {
      for (const olt of enjeu.objectifs_long_terme) {
        for (const niveau of olt.niveaux_exigence) {
          indicateurs.push(...niveau.indicateurs);
        }
      }
      for (const oo of enjeu.objectifs_operationnels) {
        for (const resultat of oo.resultats_attendus) {
          indicateurs.push(...resultat.indicateurs);
        }
      }
    }
    return indicateurs;
  }

  periodeAction(action: FicheAction): string {
    if (!action.annee_min && !action.annee_max) {
      return '';
    }
    if (action.annee_min === action.annee_max) {
      return String(action.annee_min);
    }
    return `${action.annee_min ?? '?'}-${action.annee_max ?? '?'}`;
  }
}
