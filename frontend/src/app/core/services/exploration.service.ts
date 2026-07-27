import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, map, shareReplay } from 'rxjs';

import {
  ExplorationContenu,
  ExplorationCriteres,
  ExplorationPlan,
  ExplorationReponse,
  NomenclatureOption,
  OrganismePublic,
  ZoneRegion,
} from '../models/exploration.model';

/**
 * Accès à l'API d'exploration des données.
 *
 * Le service ne porte pas d'état de recherche : les critères vivent dans l'URL
 * (query params), ce qui rend un résultat partageable par simple copie du lien
 * et fait fonctionner le bouton « précédent » du navigateur. Seul l'arbre des
 * zones géographiques est mis en cache — c'est un référentiel figé.
 */
@Injectable({ providedIn: 'root' })
export class ExplorationService {
  private readonly http = inject(HttpClient);

  private readonly urlContenus = '/api/exploration/contenus/';
  private readonly urlPlans = '/api/exploration/plans/';
  private readonly urlZones = '/api/geo/zones/';

  private zones$?: Observable<ZoneRegion[]>;
  private organismes$?: Observable<OrganismePublic[]>;
  private readonly nomenclatures$ = new Map<string, Observable<NomenclatureOption[]>>();

  readonly chargement = signal(false);

  /** Construit les paramètres HTTP à partir des critères, en omettant les vides. */
  private parametres(criteres: ExplorationCriteres): HttpParams {
    let params = new HttpParams();

    const texte = (cle: string, valeur?: string) => {
      if (valeur?.trim()) {
        params = params.set(cle, valeur.trim());
      }
    };
    const multiple = (cle: string, valeurs?: (string | number)[]) => {
      if (valeurs?.length) {
        params = params.set(cle, valeurs.join(','));
      }
    };

    texte('q', criteres.q);
    // Le mode « titres uniquement » est le défaut côté serveur : on ne
    // transmet que la désactivation, pour garder des URLs lisibles.
    if (criteres.titresSeulement === false) {
      params = params.set('titres_seulement', 'false');
    }
    multiple('types', criteres.types);
    multiple('onglet', criteres.onglet);
    multiple('zones', criteres.zones);
    multiple('organismes', criteres.organismes);
    multiple('types_site', criteres.typesSite);
    multiple('categories_enjeu', criteres.categoriesEnjeu);
    multiple('types_indicateur', criteres.typesIndicateur);
    multiple('categories_action', criteres.categoriesAction);
    multiple('statuts', criteres.statuts);
    if (criteres.tri && criteres.tri !== 'pertinence') {
      params = params.set('tri', criteres.tri);
    }
    if (criteres.page && criteres.page > 1) {
      params = params.set('page', String(criteres.page));
    }

    return params;
  }

  /** Recherche dans le contenu des plans de gestion. */
  chercherContenus(
    criteres: ExplorationCriteres,
  ): Observable<ExplorationReponse<ExplorationContenu>> {
    return this.http.get<ExplorationReponse<ExplorationContenu>>(this.urlContenus, {
      params: this.parametres(criteres),
    });
  }

  /** Recherche un plan de gestion par nom, site, département ou région. */
  chercherPlans(
    criteres: ExplorationCriteres,
  ): Observable<ExplorationReponse<ExplorationPlan>> {
    return this.http.get<ExplorationReponse<ExplorationPlan>>(this.urlPlans, {
      params: this.parametres(criteres),
    });
  }

  /** Arbre régions → départements du filtre « zone géographique ». */
  zones(): Observable<ZoneRegion[]> {
    this.zones$ ??= this.http
      .get<ZoneRegion[]>(this.urlZones)
      .pipe(shareReplay({ bufferSize: 1, refCount: false }));
    return this.zones$;
  }

  /**
   * Organismes proposés par le filtre « organismes gestionnaires ».
   *
   * On passe par la liste publique et non par `/api/users/organismes/`, qui est
   * restreinte à l'organisme de l'utilisateur : l'exploration est transverse,
   * son filtre doit l'être aussi.
   */
  organismes(): Observable<OrganismePublic[]> {
    this.organismes$ ??= this.http
      .get<OrganismePublic[]>('/api/users/organismes/public/')
      .pipe(shareReplay({ bufferSize: 1, refCount: false }));
    return this.organismes$;
  }

  /** Nomenclature complète d'un type, mise en cache (référentiel figé). */
  nomenclatures(type: string): Observable<NomenclatureOption[]> {
    if (!this.nomenclatures$.has(type)) {
      this.nomenclatures$.set(
        type,
        this.http
          .get<{ results?: NomenclatureOption[] } | NomenclatureOption[]>(
            '/api/nomenclatures/',
            { params: new HttpParams().set('type', type).set('page_size', '200') },
          )
          .pipe(
            map((reponse) =>
              Array.isArray(reponse) ? reponse : (reponse.results ?? []),
            ),
            shareReplay({ bufferSize: 1, refCount: false }),
          ),
      );
    }
    return this.nomenclatures$.get(type)!;
  }
}
