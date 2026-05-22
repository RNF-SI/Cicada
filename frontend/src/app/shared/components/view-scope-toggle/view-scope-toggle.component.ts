import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule } from '@ngx-translate/core';

/**
 * Type de scope d'affichage pour les listes de sites/plans.
 * - 'mine': Uniquement les éléments auxquels l'utilisateur est directement lié (ex: référent du plan)
 * - 'sites': Plans des sites auxquels l'utilisateur est lié (membre ou référent du site)
 * - 'organisme': Tous les éléments de l'organisme de l'utilisateur
 * - 'all': Tous les éléments (super_admin uniquement)
 */
export type ViewScope = 'mine' | 'sites' | 'organisme' | 'all';

export interface ViewScopeOption {
  value: ViewScope;
  label: string;
  icon: string;
  tooltip: string;
}

/**
 * Composant réutilisable pour basculer entre différents scopes d'affichage.
 * Utilisé pour les listes de sites et plans de gestion.
 *
 * Usage:
 * <app-view-scope-toggle
 *   [currentScope]="currentScope()"
 *   [showAllOption]="isSuperAdmin()"
 *   (scopeChange)="onScopeChange($event)">
 * </app-view-scope-toggle>
 */
@Component({
  selector: 'app-view-scope-toggle',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonToggleModule,
    MatTooltipModule,
    TranslateModule
  ],
  template: `
    <div class="view-scope-toggle">
      <mat-button-toggle-group
        [value]="currentScope"
        (change)="onScopeChange($event.value)"
        aria-label="Scope d'affichage">
        @for (option of availableOptions; track option.value) {
          <mat-button-toggle
            [value]="option.value"
            [matTooltip]="option.tooltip"
            [attr.aria-label]="option.tooltip">
            <!-- Icône check retirée (revue design #310) : le fond coloré suffit pour indiquer la sélection -->
            <span class="toggle-icons">
              <i class="fi {{ option.icon }}"></i>
            </span>
            <span class="toggle-label">{{ option.label }}</span>
          </mat-button-toggle>
        }
      </mat-button-toggle-group>
    </div>
  `,
  styles: [`
    .view-scope-toggle {
      display: inline-flex;
    }

    /* Groupe principal - MDC et legacy */
    :host ::ng-deep .mat-button-toggle-group,
    :host ::ng-deep .mat-mdc-button-toggle-group {
      // Background blanc (revue design #314 : fond du switch en blanc, pas en gris)
      background-color: #FFFFFF !important;
      border: 1px solid #C6C6C6 !important;
      border-radius: 9999px !important;
      overflow: hidden !important;
      box-shadow: none !important;
    }

    /* Boutons individuels */
    :host ::ng-deep .mat-button-toggle,
    :host ::ng-deep .mat-mdc-button-toggle {
      border: none !important;
      background-color: transparent;
      overflow: hidden;
    }

    :host ::ng-deep .mat-button-toggle .mat-button-toggle-label-content,
    :host ::ng-deep .mat-mdc-button-toggle .mdc-button__label,
    :host ::ng-deep .mat-button-toggle-label-content {
      display: flex !important;
      align-items: center !important;
      gap: 12px !important;
      padding: 8px 24px !important;
      line-height: 24px !important;
      font-family: 'Nunito', sans-serif !important;
      font-size: 15px !important;
      font-weight: 700 !important;
      color: #746F6E !important;
      letter-spacing: 0 !important;
    }

    :host ::ng-deep .mat-button-toggle i,
    :host ::ng-deep .mat-mdc-button-toggle i {
      font-size: 18px;
      line-height: 1;
    }

    :host ::ng-deep .toggle-icons {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    :host ::ng-deep .check-icon {
      font-size: 14px !important;
    }

    :host ::ng-deep .toggle-label {
      white-space: nowrap;
    }

    /* Bordure entre boutons */
    :host ::ng-deep .mat-button-toggle + .mat-button-toggle,
    :host ::ng-deep .mat-mdc-button-toggle + .mat-mdc-button-toggle {
      border-left: 1px solid #C6C6C6 !important;
    }

    /* Bouton sélectionné */
    :host ::ng-deep .mat-button-toggle-checked,
    :host ::ng-deep .mat-mdc-button-toggle-checked {
      background-color: #025359 !important;
    }

    :host ::ng-deep .mat-button-toggle-checked .mat-button-toggle-label-content,
    :host ::ng-deep .mat-mdc-button-toggle-checked .mdc-button__label,
    :host ::ng-deep .mat-button-toggle-checked .mat-button-toggle-label-content {
      color: #FFFFFF !important;
    }

    /* Désactiver le checkbox wrapper par défaut d'Angular Material */
    :host ::ng-deep .mat-button-toggle-checkbox-wrapper {
      display: none !important;
    }

    :host ::ng-deep .mat-button-toggle-checked .mat-button-toggle-button:has(.mat-button-toggle-checkbox-wrapper) {
      padding-left: 0 !important;
    }

    :host ::ng-deep .mat-button-toggle-checked .mat-button-toggle-button,
    :host ::ng-deep .mat-mdc-button-toggle-checked button {
      padding-left: 0 !important;
    }

    /* Arrondis premier bouton */
    :host ::ng-deep .mat-button-toggle:first-child,
    :host ::ng-deep .mat-mdc-button-toggle:first-child,
    :host ::ng-deep .mat-button-toggle:first-child .mat-button-toggle-button,
    :host ::ng-deep .mat-mdc-button-toggle:first-child button {
      border-radius: 9999px 0 0 9999px !important;
    }

    /* Arrondis dernier bouton */
    :host ::ng-deep .mat-button-toggle:last-child,
    :host ::ng-deep .mat-mdc-button-toggle:last-child,
    :host ::ng-deep .mat-button-toggle:last-child .mat-button-toggle-button,
    :host ::ng-deep .mat-mdc-button-toggle:last-child button {
      border-radius: 0 9999px 9999px 0 !important;
    }

    /* Bouton unique */
    :host ::ng-deep .mat-button-toggle:only-child,
    :host ::ng-deep .mat-mdc-button-toggle:only-child,
    :host ::ng-deep .mat-button-toggle:only-child .mat-button-toggle-button,
    :host ::ng-deep .mat-mdc-button-toggle:only-child button {
      border-radius: 9999px !important;
    }

    /* Masquer bordure entre bouton sélectionné et voisin */
    :host ::ng-deep .mat-button-toggle-checked + .mat-button-toggle,
    :host ::ng-deep .mat-button-toggle + .mat-button-toggle-checked,
    :host ::ng-deep .mat-mdc-button-toggle-checked + .mat-mdc-button-toggle,
    :host ::ng-deep .mat-mdc-button-toggle + .mat-mdc-button-toggle-checked {
      border-left-color: transparent !important;
    }

    /* Hover */
    :host ::ng-deep .mat-button-toggle:not(.mat-button-toggle-checked):hover,
    :host ::ng-deep .mat-mdc-button-toggle:not(.mat-mdc-button-toggle-checked):hover {
      background-color: #F8F5F1 !important;
    }

    /* Focus */
    :host ::ng-deep .mat-button-toggle:focus,
    :host ::ng-deep .mat-mdc-button-toggle:focus {
      outline: none !important;
    }

    :host ::ng-deep .mat-button-toggle-button:focus,
    :host ::ng-deep .mat-mdc-button-toggle button:focus {
      outline: 2px solid #025359;
      outline-offset: -2px;
    }

    /* Responsive */
    @media (max-width: 768px) {
      :host ::ng-deep .mat-button-toggle .mat-button-toggle-label-content,
      :host ::ng-deep .mat-mdc-button-toggle .mdc-button__label {
        padding: 8px 16px !important;
        gap: 8px !important;
      }

      :host ::ng-deep .toggle-label {
        display: none;
      }
    }
  `]
})
export class ViewScopeToggleComponent {
  /**
   * Scope actuellement sélectionné.
   */
  @Input() currentScope: ViewScope = 'mine';

  /**
   * Afficher l'option "Tous" (pour super_admin uniquement).
   */
  @Input() showAllOption = false;

  /**
   * Afficher l'option "Sites" (plans des sites liés à l'utilisateur).
   */
  @Input() showSitesOption = false;

  /**
   * Afficher l'option "Organisme" (pour admin_og et super_admin).
   */
  @Input() showOrganismeOption = true;

  /**
   * Label personnalisé pour "Mes sites" / "Mes plans".
   */
  @Input() mineLabel = 'Mes sites';

  /**
   * Label personnalisé pour "Mes sites" (plans des sites).
   */
  @Input() sitesLabel = 'Mes sites';

  /**
   * Label personnalisé pour "Sites de l'organisme" / "Plans de l'organisme".
   */
  @Input() organismeLabel = 'Mon organisme';

  /**
   * Label personnalisé pour "Tous les sites" / "Tous les plans".
   */
  @Input() allLabel = 'Tous';

  /**
   * Événement émis lors du changement de scope.
   */
  @Output() scopeChange = new EventEmitter<ViewScope>();

  /**
   * Options disponibles en fonction des permissions.
   */
  get availableOptions(): ViewScopeOption[] {
    const options: ViewScopeOption[] = [
      {
        value: 'mine',
        label: this.mineLabel,
        icon: 'fi-rr-user',
        tooltip: `Afficher uniquement ${this.mineLabel.toLowerCase()}`
      }
    ];

    if (this.showSitesOption) {
      options.push({
        value: 'sites',
        label: this.sitesLabel,
        icon: 'fi-rr-marker',
        tooltip: `Afficher les plans de ${this.sitesLabel.toLowerCase()}`
      });
    }

    if (this.showOrganismeOption) {
      options.push({
        value: 'organisme',
        label: this.organismeLabel,
        icon: 'fi-rr-users-alt',
        tooltip: `Afficher tous les éléments de ${this.organismeLabel.toLowerCase()}`
      });
    }

    if (this.showAllOption) {
      options.push({
        value: 'all',
        label: this.allLabel,
        icon: 'fi-rr-globe',
        tooltip: `Afficher ${this.allLabel.toLowerCase()} les éléments`
      });
    }

    return options;
  }

  onScopeChange(scope: ViewScope): void {
    this.scopeChange.emit(scope);
  }
}
