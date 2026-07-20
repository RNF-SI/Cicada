import { computed, signal, Signal, WritableSignal } from '@angular/core';

/**
 * Fabrique d'état de filtres (#592).
 *
 * Remplace les implémentations dupliquées de `clearFilters()` / `hasActiveFilters()` que l'on
 * trouvait dans au moins six composants (`inventaires-list`, `plan-bilan`, `plan-suivi-actions`,
 * `plan-tableau-de-bord`, plus les `onFilterChange()` des pages d'administration).
 *
 * **Périmètre volontairement étroit** : ce helper porte l'état et en dérive l'activité.
 * Il ne connaît ni prédicats de filtrage, ni tri, ni synchronisation d'URL, ni persistance —
 * chaque page conserve son propre `computed` de filtrage. S'il gagnait une option `predicate`,
 * il serait devenu un store et le découpage aurait échoué.
 *
 * @example
 * ```ts
 * readonly filters = createFilterSet({
 *   enjeu: null as number | null,
 *   priorite: null as string | null,
 *   realisation: 'all' as 'all' | 'realized' | 'not-realized',
 * }, {
 *   // « all » est la valeur neutre de ce filtre, pas une valeur active.
 *   isActive: { realisation: (v) => v !== 'all' },
 * });
 *
 * // Template : filters.enjeu() · filters.hasActive() · (click)="filters.reset()"
 * ```
 */

/** Prédicats d'activité personnalisés, par clé. */
export type FilterActivityMap<S> = Partial<{
  [K in keyof S]: (value: S[K]) => boolean;
}>;

export interface FilterSetOptions<S> {
  /**
   * Surcharge, clé par clé, du test « ce filtre est-il actif ? ».
   * Nécessaire dès qu'une valeur neutre n'est ni vide ni nulle (ex : `'all'`).
   */
  isActive?: FilterActivityMap<S>;

  /**
   * Effet de bord additionnel exécuté à la fin de `reset()`.
   *
   * Existe pour les pages dont la réinitialisation fait plus que vider les champs — typiquement
   * `inventaires-list`, qui doit aussi revenir en page 1 et recharger. Sans cette échappatoire,
   * ces pages garderaient leur méthode maison et l'abstraction raterait sa cible.
   */
  onReset?: () => void;
}

export type FilterSet<S extends Record<string, unknown>> = {
  readonly [K in keyof S]: WritableSignal<S[K]>;
} & {
  /** Remet tous les filtres à leur valeur initiale, puis exécute `onReset`. */
  reset(): void;
  /** Nombre de filtres actuellement actifs. */
  readonly activeCount: Signal<number>;
  /** Vrai dès qu'au moins un filtre est actif. */
  readonly hasActive: Signal<boolean>;
};

/**
 * Test d'activité par défaut : un tableau non vide, une chaîne non vide une fois `trim`ée,
 * sinon toute valeur autre que `null` / `undefined`.
 */
/**
 * Copie défensive des valeurs initiales de type tableau.
 *
 * Sans cela, `reset()` réinjecterait l'instance de tableau reçue à la construction : une
 * mutation en place chez un appelant corromprait définitivement l'état initial.
 */
function cloneInitial<V>(value: V): V {
  return Array.isArray(value) ? ([...value] as V) : value;
}

function isActiveByDefault(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.length > 0;
  }
  if (typeof value === 'string') {
    return value.trim().length > 0;
  }
  return value !== null && value !== undefined;
}

export function createFilterSet<S extends Record<string, unknown>>(
  initial: S,
  options: FilterSetOptions<S> = {},
): FilterSet<S> {
  const keys = Object.keys(initial) as (keyof S)[];
  const signals = {} as { [K in keyof S]: WritableSignal<S[K]> };

  for (const key of keys) {
    signals[key] = signal(cloneInitial(initial[key])) as WritableSignal<S[typeof key]>;
  }

  const activeCount = computed(() => {
    let count = 0;
    for (const key of keys) {
      const test = options.isActive?.[key] ?? isActiveByDefault;
      if (test(signals[key]() as S[typeof key])) {
        count++;
      }
    }
    return count;
  });

  const reset = (): void => {
    for (const key of keys) {
      signals[key].set(cloneInitial(initial[key]));
    }
    options.onReset?.();
  };

  return Object.assign(signals, {
    reset,
    activeCount,
    hasActive: computed(() => activeCount() > 0),
  }) as FilterSet<S>;
}
