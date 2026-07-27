import { CommonModule } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';

import {
  FicheEnjeu,
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

  readonly plan = signal<FichePlan | null>(null);
  readonly chargement = signal(true);
  readonly introuvable = signal(false);

  /** Objet mis en évidence, sous la forme `type:id`. */
  readonly focus = signal<string | null>(null);
  readonly enjeuxOuverts = signal<number[]>([]);

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
        this.ouvrirEnjeuCible(plan);
      },
      error: () => {
        this.plan.set(null);
        this.introuvable.set(true);
        this.chargement.set(false);
      },
    });
  }

  /** Ouvre l'enjeu qui contient l'objet ciblé, puis fait défiler jusqu'à lui. */
  private ouvrirEnjeuCible(plan: FichePlan): void {
    const cible = this.focus();
    if (!cible) {
      return;
    }

    const enjeu = plan.enjeux.find((candidat) => this.contient(candidat, cible));
    if (enjeu) {
      this.enjeuxOuverts.set([enjeu.id_enjeu]);
    }

    // Le défilement attend que l'accordéon soit rendu.
    setTimeout(() => {
      document
        .getElementById(this.ancreDe(cible))
        ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 300);
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

  periodeAction(action: { annee_min: number | null; annee_max: number | null }): string {
    if (!action.annee_min && !action.annee_max) {
      return '';
    }
    if (action.annee_min === action.annee_max) {
      return String(action.annee_min);
    }
    return `${action.annee_min ?? '?'}-${action.annee_max ?? '?'}`;
  }
}
