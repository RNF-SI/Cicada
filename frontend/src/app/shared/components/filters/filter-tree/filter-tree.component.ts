import { Component, booleanAttribute, computed, input, model, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslateModule } from '@ngx-translate/core';
import { CheckboxComponent } from '../../checkbox/checkbox.component';
import { HighlightMatchPipe } from '../highlight-match.pipe';
import { matchesQuery } from '../filter-search.util';
import { FilterTheme, FilterTreeNode, FilterValue, TriState } from '../filter.types';

/** Nœud aplati pour le rendu : porte sa profondeur et son état dérivé. */
interface FlatNode<T extends FilterValue> {
  node: FilterTreeNode<T>;
  depth: number;
  hasChildren: boolean;
  expanded: boolean;
  state: TriState;
}

/**
 * Filtre hiérarchique à cases (#592, famille A3 du Figma node 4487:31534).
 *
 * Zone géographique (région → département), typologies d'habitats, etc. Vit soit directement
 * dans une carte de sidebar primary (`theme="dark"`, son usage principal), soit comme corps
 * d'un `app-filter-dropdown`.
 *
 * Reste distinct de `app-filter-option-list` à dessein : une liste plate est formellement un
 * arbre de profondeur 1, mais les fusionner obligerait la quinzaine d'appels plats à emballer
 * leurs valeurs en arbre, et rendrait mortes chez eux les branches expansion / cascade /
 * ancêtres. La logique réellement commune (repliage, segmentation) vit dans
 * `filter-search.util.ts`, importée par les deux.
 */
@Component({
  selector: 'app-filter-tree',
  standalone: true,
  imports: [CommonModule, TranslateModule, CheckboxComponent, HighlightMatchPipe],
  templateUrl: './filter-tree.component.html',
  styleUrl: './filter-tree.component.scss',
  host: {
    '[class.theme-dark]': "theme() === 'dark'",
  },
})
export class FilterTreeComponent<T extends FilterValue = FilterValue> {
  readonly nodes = input.required<FilterTreeNode<T>[]>();

  readonly selected = model<T[]>([]);
  readonly expanded = model<T[]>([]);

  readonly searchable = input(true, { transform: booleanAttribute });
  readonly searchPlaceholder = input<string>('');

  /** Nombre de nœuds racine affichés avant troncature « Voir plus ». */
  readonly maxVisible = input<number | null>(null);

  /** Cocher un parent sélectionne toute sa descendance. */
  readonly cascade = input(true, { transform: booleanAttribute });

  /** La carte primary de sidebar est son contexte principal. */
  readonly theme = input<FilterTheme>('dark');

  readonly testId = input<string>('');

  protected readonly query = signal('');
  protected readonly showAll = signal(false);

  /**
   * Arbre restreint à la recherche : un nœud est conservé s'il correspond lui-même ou s'il a
   * un descendant correspondant — les ancêtres d'une correspondance restent donc visibles.
   */
  private readonly filtered = computed<FilterTreeNode<T>[]>(() => {
    const q = this.query().trim();
    if (!q) {
      return this.nodes();
    }

    const prune = (nodes: FilterTreeNode<T>[]): FilterTreeNode<T>[] =>
      nodes.reduce<FilterTreeNode<T>[]>((kept, node) => {
        const children = node.children ? prune(node.children) : [];
        if (matchesQuery(node.label, q) || children.length) {
          kept.push({ ...node, children: children.length ? children : node.children });
        }
        return kept;
      }, []);

    return prune(this.nodes());
  });

  private readonly roots = computed(() => {
    const max = this.maxVisible();
    const all = this.filtered();
    return max !== null && !this.showAll() ? all.slice(0, max) : all;
  });

  protected readonly hiddenCount = computed(() =>
    Math.max(0, this.filtered().length - this.roots().length),
  );

  protected readonly isEmpty = computed(() => this.filtered().length === 0);

  /**
   * Aplatit l'arbre visible en une liste de lignes.
   *
   * Pendant une recherche, tous les nœuds conservés sont dépliés d'office : sinon une
   * correspondance profonde resterait invisible sous un parent replié.
   */
  protected readonly rows = computed<FlatNode<T>[]>(() => {
    const searching = this.query().trim().length > 0;
    const expandedSet = new Set(this.expanded());
    const rows: FlatNode<T>[] = [];

    const walk = (nodes: FilterTreeNode<T>[], depth: number): void => {
      for (const node of nodes) {
        const children = node.children ?? [];
        const hasChildren = children.length > 0;
        const isExpanded = searching || expandedSet.has(node.value);

        rows.push({
          node,
          depth,
          hasChildren,
          expanded: isExpanded,
          state: this.stateOf(node),
        });

        if (hasChildren && isExpanded) {
          walk(children, depth + 1);
        }
      }
    };

    walk(this.roots(), 0);
    return rows;
  });

  /** Toutes les valeurs d'un sous-arbre, nœud compris. */
  private descendants(node: FilterTreeNode<T>): T[] {
    const values: T[] = [node.value];
    for (const child of node.children ?? []) {
      values.push(...this.descendants(child));
    }
    return values;
  }

  /** Feuilles d'un sous-arbre — base du calcul d'état partiel d'un parent. */
  private leaves(node: FilterTreeNode<T>): T[] {
    if (!node.children?.length) {
      return [node.value];
    }
    return node.children.flatMap((child) => this.leaves(child));
  }

  private stateOf(node: FilterTreeNode<T>): TriState {
    const set = new Set(this.selected());
    if (!node.children?.length) {
      return set.has(node.value) ? 'checked' : 'unchecked';
    }
    const leaves = this.leaves(node);
    const count = leaves.filter((v) => set.has(v)).length;
    if (count === 0) {
      return set.has(node.value) ? 'checked' : 'unchecked';
    }
    return count === leaves.length ? 'checked' : 'indeterminate';
  }

  protected toggleNode(row: FlatNode<T>): void {
    if (row.node.disabled) {
      return;
    }

    const affected = this.cascade() ? this.descendants(row.node) : [row.node.value];
    const current = new Set(this.selected());
    const shouldSelect = row.state !== 'checked';

    for (const value of affected) {
      shouldSelect ? current.add(value) : current.delete(value);
    }

    this.selected.set([...current]);
  }

  protected toggleExpand(row: FlatNode<T>, event: MouseEvent): void {
    event.stopPropagation();
    const current = this.expanded();
    this.expanded.set(
      current.includes(row.node.value)
        ? current.filter((v) => v !== row.node.value)
        : [...current, row.node.value],
    );
  }

  protected onSearchInput(event: Event): void {
    this.query.set((event.target as HTMLInputElement).value);
  }

  protected clearSearch(): void {
    this.query.set('');
  }

  protected rowTestId(row: FlatNode<T>): string | null {
    return this.testId() ? `${this.testId()}-node-${row.node.value}` : null;
  }
}
