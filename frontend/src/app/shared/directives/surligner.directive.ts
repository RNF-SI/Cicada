import {
  Directive,
  ElementRef,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  inject,
} from '@angular/core';

import { segmenterSurTerme } from '../../core/models/exploration.model';

/** Classe posée sur chaque `<mark>` créé, pour le style et pour le retrait. */
export const CLASSE_SURLIGNAGE = 'surlignage-recherche';

/**
 * Surligne, dans tout le sous-arbre de l'élément hôte, les mots d'une
 * recherche (#681).
 *
 * Les écrans réels du plan — arborescence, fiche action, page du plan — sont
 * des gabarits de plusieurs milliers de lignes : y insérer un surlignage
 * libellé par libellé reviendrait à les réécrire. La directive travaille donc
 * sur le DOM rendu : elle parcourt les nœuds texte, découpe ceux qui portent
 * un mot cherché (même découpage que les tuiles de l'exploration :
 * `segmenterSurTerme`, insensible aux accents, par début de mot) et enveloppe
 * les passages dans un `<mark>`.
 *
 * Angular re-rend ces écrans par morceaux (accordéons, `@if` imbriqués) : un
 * `MutationObserver` réapplique le surlignage après chaque rendu, hors zone
 * pour ne pas relancer la détection de changements. Le surlignage se retire
 * proprement — chaque `<mark>` est remplacé par son texte — avant chaque
 * nouvelle passe et à la destruction, pour ne jamais surligner deux fois.
 *
 * Usage : `<div [appSurligner]="motCle">…</div>`. Un élément portant
 * `data-sans-surlignage` est laissé intact, ainsi que les champs de saisie.
 */
@Directive({
  selector: '[appSurligner]',
  standalone: true,
})
export class SurlignerDirective implements OnChanges, OnDestroy {
  @Input('appSurligner') termes: string | null | undefined = '';

  private readonly hote = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly zone = inject(NgZone);

  private observateur: MutationObserver | null = null;
  private planifie = false;
  private enCours = false;

  ngOnChanges(): void {
    this.zone.runOutsideAngular(() => {
      if (this.termes?.trim()) {
        this.observer();
        this.planifier();
      } else {
        this.arreter();
        this.retirer();
      }
    });
  }

  ngOnDestroy(): void {
    this.arreter();
    this.retirer();
  }

  // ------------------------------------------------------------------ //
  // Observation des rendus
  // ------------------------------------------------------------------ //

  private observer(): void {
    if (this.observateur || typeof MutationObserver === 'undefined') {
      return;
    }
    this.observateur = new MutationObserver(() => {
      // Nos propres remplacements déclenchent aussi des mutations : on les
      // ignore pendant la passe, sinon la directive se relancerait sans fin.
      if (!this.enCours) {
        this.planifier();
      }
    });
    this.observateur.observe(this.hote.nativeElement, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }

  private arreter(): void {
    this.observateur?.disconnect();
    this.observateur = null;
  }

  /** Regroupe les rendus en rafale en une seule passe, au prochain repaint. */
  private planifier(): void {
    if (this.planifie) {
      return;
    }
    this.planifie = true;
    const executer = () => {
      this.planifie = false;
      this.appliquer();
    };
    if (typeof requestAnimationFrame === 'function') {
      requestAnimationFrame(executer);
    } else {
      setTimeout(executer, 0);
    }
  }

  // ------------------------------------------------------------------ //
  // Surlignage
  // ------------------------------------------------------------------ //

  private appliquer(): void {
    this.enCours = true;
    try {
      this.retirer();
      const termes = this.termes?.trim() ?? '';
      if (!termes) {
        return;
      }
      for (const noeud of this.noeudsTexte()) {
        this.surlignerNoeud(noeud, termes);
      }
    } finally {
      // Les mutations de la passe sont livrées de façon asynchrone : on
      // attend un tour pour les laisser passer avant de réécouter.
      setTimeout(() => {
        this.enCours = false;
      }, 0);
    }
  }

  private noeudsTexte(): Text[] {
    const racine = this.hote.nativeElement;
    const doc = racine.ownerDocument;
    const marcheur = doc.createTreeWalker(racine, NodeFilter.SHOW_TEXT, {
      acceptNode: (noeud) =>
        this.estSurlignable(noeud as Text)
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_REJECT,
    });
    const noeuds: Text[] = [];
    let courant = marcheur.nextNode();
    while (courant) {
      noeuds.push(courant as Text);
      courant = marcheur.nextNode();
    }
    return noeuds;
  }

  private estSurlignable(noeud: Text): boolean {
    if (!noeud.nodeValue?.trim()) {
      return false;
    }
    for (
      let parent = noeud.parentElement;
      parent && parent !== this.hote.nativeElement.parentElement;
      parent = parent.parentElement
    ) {
      const balise = parent.tagName;
      if (
        balise === 'SCRIPT' ||
        balise === 'STYLE' ||
        balise === 'MARK' ||
        balise === 'INPUT' ||
        balise === 'TEXTAREA' ||
        balise === 'SELECT' ||
        parent.hasAttribute('data-sans-surlignage') ||
        parent.isContentEditable
      ) {
        return false;
      }
    }
    return true;
  }

  private surlignerNoeud(noeud: Text, termes: string): void {
    const segments = segmenterSurTerme(noeud.nodeValue ?? '', termes);
    if (!segments.some((segment) => segment.surligne)) {
      return;
    }
    const doc = noeud.ownerDocument;
    const fragment = doc.createDocumentFragment();
    for (const segment of segments) {
      if (segment.surligne) {
        const marque = doc.createElement('mark');
        marque.className = CLASSE_SURLIGNAGE;
        marque.textContent = segment.texte;
        fragment.appendChild(marque);
      } else {
        fragment.appendChild(doc.createTextNode(segment.texte));
      }
    }
    noeud.parentNode?.replaceChild(fragment, noeud);
  }

  /** Défait tout surlignage posé par cette directive. */
  private retirer(): void {
    const racine = this.hote.nativeElement;
    const marques = Array.from(
      racine.querySelectorAll<HTMLElement>(`mark.${CLASSE_SURLIGNAGE}`),
    );
    const parents = new Set<Node>();
    for (const marque of marques) {
      const parent = marque.parentNode;
      if (!parent) {
        continue;
      }
      parent.replaceChild(
        racine.ownerDocument.createTextNode(marque.textContent ?? ''),
        marque,
      );
      parents.add(parent);
    }
    // Recoller les nœuds texte voisins : `segmenterSurTerme` doit revoir le
    // texte d'un seul tenant à la passe suivante.
    for (const parent of parents) {
      parent.normalize();
    }
  }
}
