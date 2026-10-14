import { Injectable, inject } from '@angular/core';
import { NavigationEnd, Router, UrlTree } from '@angular/router';
import { filter } from 'rxjs';

const CLE_STOCKAGE = 'cicada.exploration.derniere-recherche';

/**
 * #683 — Retour à la recherche d'exploration en cours.
 *
 * Depuis un résultat d'exploration, l'utilisateur ouvre une fiche action, puis
 * « Voir dans le plan de gestion », puis navigue dans l'arborescence : plusieurs
 * écrans plus loin, « Retour à l'exploration » doit le ramener à **sa**
 * recherche (mot, onglet, facettes, page), et non à la page d'accueil de
 * l'exploration ni à l'arborescence d'un plan qui n'est pas le sien. Le
 * navigateur ne le permet pas (« précédent » remonterait écran par écran) :
 * le service retient donc la dernière adresse d'exploration visitée.
 *
 * Instancié par le composant racine pour suivre toutes les navigations, et
 * conservé dans le `sessionStorage` pour survivre à un rechargement de page.
 */
@Injectable({ providedIn: 'root' })
export class ExplorationRetourService {
  private readonly router = inject(Router);
  private derniere: string | null = this.lire();

  constructor() {
    // `events` peut manquer sur les faux routeurs des tests de composants.
    this.router.events
      ?.pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe(e => {
        if (e.urlAfterRedirects.startsWith('/exploration')) {
          this.derniere = e.urlAfterRedirects;
          this.ecrire(this.derniere);
        }
      });
  }

  /**
   * Adresse de retour : la dernière recherche d'exploration, sinon une
   * recherche sur le mot surligné, sinon l'accueil de l'exploration.
   */
  lienRetour(motCle?: string | null): UrlTree {
    if (this.derniere) {
      return this.router.parseUrl(this.derniere);
    }
    return motCle
      ? this.router.createUrlTree(['/exploration/contenus'], { queryParams: { q: motCle } })
      : this.router.createUrlTree(['/exploration']);
  }

  retourner(motCle?: string | null): void {
    this.router.navigateByUrl(this.lienRetour(motCle));
  }

  private lire(): string | null {
    try {
      return sessionStorage.getItem(CLE_STOCKAGE);
    } catch {
      return null;
    }
  }

  private ecrire(url: string): void {
    try {
      sessionStorage.setItem(CLE_STOCKAGE, url);
    } catch {
      // Stockage indisponible (navigation privée…) : le retour se fera sur le mot cherché.
    }
  }
}
