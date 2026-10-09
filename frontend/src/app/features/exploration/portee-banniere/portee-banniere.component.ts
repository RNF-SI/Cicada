import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';

import { AuthService } from '../../../core/services/auth.service';
import { ExplorationService } from '../../../core/services/exploration.service';
import { SettingsService } from '../../../core/services/settings.service';

/**
 * #636 — Bannière de portée de l'exploration.
 *
 * Dit sur quoi porte la recherche, sur l'accueil comme sur les pages de
 * résultats :
 * - partage actif : une ligne discrète (« N structures participantes ») ;
 * - partage inactif : un encadré **permanent**, non refermable, qui explique
 *   que la recherche se limite à la structure et ce que le partage ouvrirait.
 *   Sans lui, une exploration restreinte se lit comme une panne, et l'on
 *   conclut que les autres structures n'ont pas de plans.
 *
 * Seul un super admin peut activer le partage (paramètres de l'instance) :
 * lui reçoit le lien, les autres l'invitation à en parler.
 */
@Component({
  selector: 'app-portee-banniere',
  standalone: true,
  imports: [RouterModule, TranslateModule],
  templateUrl: './portee-banniere.component.html',
  styleUrl: './portee-banniere.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PorteeBanniereComponent {
  private readonly settings = inject(SettingsService);
  private readonly auth = inject(AuthService);
  private readonly exploration = inject(ExplorationService);

  /** `centre` sur l'accueil (bandeau centré), `gauche` sur les résultats. */
  readonly alignement = input<'centre' | 'gauche'>('gauche');

  /** Les structures qui alimentent la recherche (portée chiffrée). */
  private readonly instances = toSignal(this.exploration.instances(), {
    initialValue: [],
  });

  readonly partageActif = computed(() => this.settings.partageFederationActif());
  readonly nombreStructures = computed(() => this.instances().length);
  readonly peutActiver = computed(() => this.auth.isSuperAdmin());

  /**
   * Clé de la ligne « nationale » — chiffrée dès qu'on sait combien de
   * structures publient. On rend la clé et non le texte : le pipe se
   * réévalue quand le dictionnaire finit de charger.
   */
  readonly cleNationale = computed(() =>
    this.nombreStructures() > 1
      ? 'exploration.perimetreNational.nationaleDetail'
      : 'exploration.perimetreNational.nationale',
  );
}
