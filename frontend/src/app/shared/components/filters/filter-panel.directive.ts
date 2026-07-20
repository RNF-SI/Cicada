import { Directive, TemplateRef, inject } from '@angular/core';

/**
 * Marque le `ng-template` fournissant le corps du panneau d'un `app-filter-dropdown` (#592).
 *
 * Le contenu est déclaré dans le template de la page appelante, donc il porte l'encapsulation
 * de cette page — ce qui est voulu : le corps se style lui-même (`app-filter-option-list`,
 * `app-filter-tree`), tandis que le châssis du panneau reste stylé par le dropdown.
 *
 * @example
 * ```html
 * <app-filter-dropdown label="Enjeu">
 *   <ng-template appFilterPanel>
 *     <app-filter-option-list [options]="enjeux()" [(selected)]="filters.enjeux" />
 *   </ng-template>
 * </app-filter-dropdown>
 * ```
 */
@Directive({
  selector: '[appFilterPanel]',
  standalone: true,
})
export class FilterPanelDirective {
  readonly templateRef = inject<TemplateRef<unknown>>(TemplateRef);
}
