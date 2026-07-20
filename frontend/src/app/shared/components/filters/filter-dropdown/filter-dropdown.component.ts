import {
  Component,
  ElementRef,
  booleanAttribute,
  computed,
  contentChild,
  input,
  model,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { CdkConnectedOverlay, CdkOverlayOrigin, ConnectedPosition } from '@angular/cdk/overlay';
import { FilterPanelDirective } from '../filter-panel.directive';
import { FilterTheme, FilterTriggerVariant } from '../filter.types';

let nextPanelId = 0;

/**
 * Déclencheur + panneau flottant d'un filtre (#592).
 *
 * Deux apparences, correspondant aux deux familles du Figma :
 * - `field` : champ blanc 44px bordé, texte « Sélectionner » — filtres de sidebar (famille A).
 * - `inline` : bouton 36px transparent, libellé gras primary + badge compteur — barres
 *   horizontales (famille B).
 *
 * ## Pourquoi le CDK et non `mat-menu`
 *
 * `mat-menu` rend son contenu dans le conteneur global d'overlay, donc **hors de la portée de
 * style du composant** : c'est ce qui obligeait à un bloc global en `!important` avec des hex en
 * dur (ancien `styles.scss`). Il **ferme aussi à l'activation d'un item par contrat** (motif ARIA
 * `menu`), d'où les `stopPropagation()` sur chaque ligne des anciens multiselects. Enfin la
 * sémantique était fausse : un filtre est une `listbox`, pas un `menu`.
 *
 * En déclarant le panneau via `<ng-template cdkConnectedOverlay>` **dans ce composant**, Angular
 * applique l'attribut d'encapsulation du composant aux nœuds projetés : tout le style du panneau
 * vit dans le SCSS du composant, sans `::ng-deep` ni `!important`.
 *
 * Le backdrop transparent supprime structurellement le besoin de `stopPropagation()` : un clic
 * dans le panneau n'atteint jamais un gestionnaire de fermeture.
 */
@Component({
  selector: 'app-filter-dropdown',
  standalone: true,
  imports: [CommonModule, CdkOverlayOrigin, CdkConnectedOverlay],
  templateUrl: './filter-dropdown.component.html',
  styleUrl: './filter-dropdown.component.scss',
  host: {
    '[class.theme-dark]': "theme() === 'dark'",
    '[class.variant-field]': "variant() === 'field'",
    '[class.variant-inline]': "variant() === 'inline'",
  },
})
export class FilterDropdownComponent {
  /** Apparence du déclencheur. */
  readonly variant = input<FilterTriggerVariant>('inline');

  /** Libellé du filtre. Visible en `inline`, sert d'`aria-label` en `field`. */
  readonly label = input.required<string>();

  /** Texte affiché quand rien n'est sélectionné (variante `field`). */
  readonly placeholder = input<string>('');

  /** Résumé de la sélection affiché sur le déclencheur fermé (variante `field`). */
  readonly summary = input<string>('');

  /** Nombre de valeurs actives — affiche la pastille compteur quand > 0. */
  readonly activeCount = input<number, unknown>(0, { transform: (v) => Number(v) || 0 });

  /** Contexte de rendu (clair / carte primary). */
  readonly theme = input<FilterTheme>('light');

  readonly disabled = input(false, { transform: booleanAttribute });

  /**
   * Largeur du panneau. Par défaut (`null`), elle découle de la variante :
   * - `field` → `trigger` : le panneau s'accole au champ, bord à bord (spec Figma) ;
   * - `inline` → `auto` : le panneau se dimensionne à son contenu. Le forcer à la largeur
   *   d'un bouton étroit ferait passer les libellés à la ligne.
   */
  readonly panelWidth = input<'trigger' | 'auto' | null>(null);

  /** Racine des `data-testid` (déclencheur, panneau, options) — ancrage E2E stable. */
  readonly testId = input<string>('');

  /** État d'ouverture, bidirectionnel. */
  readonly open = model(false);

  readonly opened = output<void>();
  readonly closed = output<void>();

  readonly panelId = `app-filter-panel-${nextPanelId++}`;

  private readonly triggerRef = viewChild<ElementRef<HTMLButtonElement>>('trigger');
  protected readonly panel = contentChild(FilterPanelDirective);

  /** Largeur mesurée du déclencheur, pour aligner le panneau en variante `field`. */
  private readonly triggerWidth = signal<number | null>(null);

  /** Largeur effective, après application du défaut lié à la variante. */
  protected readonly effectivePanelWidth = computed<'trigger' | 'auto'>(
    () => this.panelWidth() ?? (this.variant() === 'field' ? 'trigger' : 'auto'),
  );

  /**
   * Largeur du déclencheur appliquée en **minimum**, jamais en largeur fixe.
   *
   * Le panneau doit s'accoler au champ (donc au moins aussi large que lui), mais une
   * largeur fixe le tronquerait dès que le champ est étroit : dans la barre d'outils des
   * logs serveur, un champ « Niveau » compact rognait l'option « WARNING ».
   */
  protected readonly overlayMinWidth = computed(() =>
    this.effectivePanelWidth() === 'trigger' ? (this.triggerWidth() ?? undefined) : undefined,
  );

  protected readonly panelClasses = computed(() => [
    'app-filter-overlay',
    this.theme() === 'dark' ? 'theme-dark' : 'theme-light',
    this.variant() === 'field' ? 'variant-field' : 'variant-inline',
  ]);

  /** Texte du déclencheur en variante `field` : sélection résumée, sinon placeholder. */
  protected readonly fieldText = computed(() => this.summary() || this.placeholder());

  protected readonly overlayPositions: ConnectedPosition[] = [
    { originX: 'start', originY: 'bottom', overlayX: 'start', overlayY: 'top' },
    // Bascule au-dessus quand le bas du viewport est trop proche.
    { originX: 'start', originY: 'top', overlayX: 'start', overlayY: 'bottom' },
  ];

  toggle(): void {
    if (this.disabled()) {
      return;
    }
    this.open() ? this.close() : this.openPanel();
  }

  openPanel(): void {
    if (this.disabled() || this.open()) {
      return;
    }
    const width = this.triggerRef()?.nativeElement.offsetWidth ?? null;
    this.triggerWidth.set(width);
    this.open.set(true);
    this.opened.emit();
  }

  /**
   * Ferme le panneau. Rend le focus au déclencheur quand la fermeture vient du clavier,
   * conformément au motif combobox — mais pas sur un clic extérieur, qui doit laisser le
   * focus suivre l'intention de l'utilisateur.
   */
  close(restoreFocus = false): void {
    if (!this.open()) {
      return;
    }
    this.open.set(false);
    this.closed.emit();
    if (restoreFocus) {
      this.triggerRef()?.nativeElement.focus();
    }
  }

  protected onTriggerKeydown(event: KeyboardEvent): void {
    if (event.key === 'ArrowDown' && !this.open()) {
      event.preventDefault();
      this.openPanel();
    }
  }

  /**
   * Échap ferme et rend le focus au déclencheur.
   *
   * Volontairement **pas de piège de focus** : un filtre est une `listbox`, pas un dialogue.
   * Tab doit pouvoir en sortir naturellement — le piéger enfermerait l'utilisateur clavier.
   */
  protected onPanelKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      event.stopPropagation();
      this.close(true);
    }
  }
}
