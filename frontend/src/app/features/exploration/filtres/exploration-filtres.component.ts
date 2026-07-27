import { CommonModule } from '@angular/common';
import { Component, computed, inject, input, model, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ExplorationCriteres } from '../../../core/models/exploration.model';
import { ExplorationService } from '../../../core/services/exploration.service';
import {
  FilterDropdownComponent,
  FilterOptionListComponent,
  FilterPanelDirective,
  FilterTreeComponent,
  FilterTreeNode,
} from '../../../shared/components/filters';

/**
 * Barre latérale de filtres de l'exploration des données.
 *
 * Partagée par les deux modes : le mode « plan de gestion » masque simplement
 * les groupes qui n'ont de sens que sur du contenu (enjeux, indicateurs,
 * objectifs, actions), via l'entrée `contenu`. Les deux modes gardent ainsi
 * exactement la même mécanique de sélection et le même rendu.
 *
 * Le composant ne connaît pas la recherche : il émet ses critères et laisse la
 * page décider quoi en faire (mise à jour de l'URL, relance de la requête).
 */
@Component({
  selector: 'app-exploration-filtres',
  standalone: true,
  imports: [
    CommonModule,
    TranslateModule,
    FilterDropdownComponent,
    FilterOptionListComponent,
    FilterPanelDirective,
    FilterTreeComponent,
  ],
  templateUrl: './exploration-filtres.component.html',
  styleUrl: './exploration-filtres.component.scss',
})
export class ExplorationFiltresComponent {
  private readonly exploration = inject(ExplorationService);
  private readonly translate = inject(TranslateService);

  /** Affiche les groupes propres au contenu (enjeux, indicateurs, objectifs, actions). */
  readonly contenu = input(false);

  /** Critères courants — bidirectionnels, la page les recopie dans l'URL. */
  readonly criteres = model.required<ExplorationCriteres>();

  protected readonly zonesEtendues = signal<number[]>([]);

  /** Arbre régions → départements. */
  private readonly zones = toSignal(this.exploration.zones(), { initialValue: [] });
  private readonly organismes = toSignal(this.exploration.organismes(), {
    initialValue: [],
  });
  private readonly typesSite = toSignal(
    this.exploration.nomenclatures('TYPE_SITE'),
    { initialValue: [] },
  );
  private readonly categoriesAction = toSignal(
    this.exploration.nomenclatures('CATEGORIE_ACTION_RESERVE'),
    { initialValue: [] },
  );

  protected readonly arbreZones = computed<FilterTreeNode<number>[]>(() =>
    this.zones().map((region) => ({
      value: region.id_area,
      label: region.nom,
      children: region.departements.map((departement) => ({
        value: departement.id_area,
        label: departement.nom,
      })),
    })),
  );

  protected readonly optionsOrganismes = computed(() =>
    this.organismes().map((organisme) => ({
      value: organisme.id,
      label: organisme.nom_organisme,
    })),
  );

  protected readonly optionsTypesSite = computed(() =>
    this.typesSite().map((nomenclature) => ({
      value: nomenclature.mnemonique,
      label: nomenclature.mnemonique,
    })),
  );

  protected readonly optionsActions = computed(() =>
    this.categoriesAction().map((nomenclature) => ({
      value: nomenclature.mnemonique,
      label: `${nomenclature.mnemonique} - ${nomenclature.label}`,
    })),
  );

  protected readonly optionsEnjeux = computed(() => [
    { value: 'ecologique', label: this.t('exploration.filters.enjeu.ecologique') },
    { value: 'socioeco', label: this.t('exploration.filters.enjeu.socioeco') },
  ]);

  protected readonly optionsIndicateurs = computed(() => [
    { value: 'ETAT', label: this.t('exploration.filters.indicateur.etat') },
    { value: 'PRESSION', label: this.t('exploration.filters.indicateur.pression') },
    { value: 'REPONSE', label: this.t('exploration.filters.indicateur.reponse') },
  ]);

  protected readonly optionsObjectifs = computed(() => [
    { value: 'objectif_op', label: this.t('exploration.types.objectif_op.pluriel') },
    { value: 'objectif_lt', label: this.t('exploration.types.objectif_lt.pluriel') },
  ]);

  protected readonly optionsStatuts = computed(() => [
    { value: 'en_cours', label: this.t('exploration.filters.statut.enCours') },
    { value: 'archive', label: this.t('exploration.filters.statut.archive') },
    { value: 'valide', label: this.t('exploration.filters.statut.valide') },
  ]);

  /**
   * Objectifs sélectionnés — dérivés de `types`, qui porte aussi le choix du
   * dropdown « Type de données ». Les deux contrôles agissent sur le même
   * critère : les garder séparés ferait diverger l'affichage de la requête.
   */
  protected readonly objectifsSelectionnes = computed(() =>
    (this.criteres().types ?? []).filter(
      (type) => type === 'objectif_lt' || type === 'objectif_op',
    ),
  );

  protected readonly nombreFiltresActifs = computed(() => {
    const c = this.criteres();
    return (
      (c.zones?.length ?? 0) +
      (c.organismes?.length ?? 0) +
      (c.typesSite?.length ?? 0) +
      (c.categoriesEnjeu?.length ?? 0) +
      (c.typesIndicateur?.length ?? 0) +
      (c.categoriesAction?.length ?? 0) +
      (c.statuts?.length ?? 0) +
      this.objectifsSelectionnes().length
    );
  });

  private t(cle: string): string {
    return this.translate.instant(cle);
  }

  /** Met à jour un critère et notifie la page. */
  protected majCritere<K extends keyof ExplorationCriteres>(
    cle: K,
    valeur: ExplorationCriteres[K],
  ): void {
    this.criteres.set({ ...this.criteres(), [cle]: valeur, page: 1 });
  }

  /** Le filtre de statut est une union fermée : on la rétablit ici. */
  protected majStatuts(valeurs: string[]): void {
    this.majCritere('statuts', valeurs as ExplorationCriteres['statuts']);
  }

  /** Les objectifs cochés remplacent la part « objectifs » de `types`. */
  protected majObjectifs(valeurs: string[]): void {
    const autres = (this.criteres().types ?? []).filter(
      (type) => type !== 'objectif_lt' && type !== 'objectif_op',
    );
    this.majCritere('types', [...autres, ...valeurs] as ExplorationCriteres['types']);
  }

  protected reinitialiser(): void {
    this.criteres.set({
      q: this.criteres().q,
      titresSeulement: this.criteres().titresSeulement,
      onglet: this.criteres().onglet,
      tri: this.criteres().tri,
      page: 1,
    });
  }
}
