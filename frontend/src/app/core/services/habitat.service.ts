import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { tap } from 'rxjs/operators';

export interface HabitatAutocomplete {
  cd_hab: number;
  cd_typo: number | null;
  lb_code: string | null;
  search_name: string;
  lb_hab_fr: string | null;
  lb_hab_fr_complet: string | null;
  lb_typo: string | null;
  niveau: number | null;
}

export interface HabitatDetail {
  cd_hab: number;
  fg_validite: string;
  cd_typo: number;
  lb_code: string;
  lb_hab_fr: string;
  lb_hab_fr_complet: string;
  lb_hab_en: string;
  lb_auteur: string;
  niveau: number;
  lb_description: string;
  cd_hab_sup: number | null;
  path_cd_hab: string;
  cd_corresp_encours: string;
  date_creation: string;
  date_maj: string;
}

export interface Typologie {
  cd_typo: number;
  cd_table: string;
  lb_typo: string;
  nom_jeu_donnees: string;
  date_creation: string;
  date_mise_jour: string;
  auteur_jeu_donnees: string;
  territoire: string;
}

export interface CorrespondanceHabitat {
  id: number;
  cd_hab: number;
  cd_hab_entre: number;
  cd_typo_entre: number;
  /** Nom de la typologie correspondante (EUNIS, CORINE_biotopes, …) — #89. */
  lb_typo?: string;
  lb_code_entre: string;
  lb_hab_entre: string;
  niveau_entre: number;
  type_rel: string;
}

/** Classification d'origine d'un habitat (référentiel + code). #89 */
export interface HabitatOwnInfo {
  cd_hab: number;
  lb_code: string | null;
  lb_typo: string | null;
  lb_hab_fr: string | null;
  lb_hab_fr_complet: string | null;
  niveau: number | null;
}

/** Réponse de l'endpoint correspondance : origine + habitats liés. #89 */
export interface HabitatCorrespondanceResponse {
  habitat: HabitatOwnInfo | null;
  related: CorrespondanceHabitat[];
}

export interface HabitatBulkFoundItem {
  input: string;
  cd_hab: number;
  lb_hab_fr: string | null;
  lb_hab_fr_complet: string | null;
  cd_typo: number | null;
  lb_code: string | null;
  niveau: number | null;
}

export interface HabitatBulkNotFoundItem {
  input: string;
  candidates: { cd_hab: number; lb_hab_fr: string | null; lb_code: string | null }[];
}

export interface HabitatBulkValidationResult {
  found: HabitatBulkFoundItem[];
  not_found: HabitatBulkNotFoundItem[];
}

@Injectable({
  providedIn: 'root'
})
export class HabitatService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/habref';

  // Cache simple pour les résultats d'autocomplete
  private autocompleteCache = new Map<string, HabitatAutocomplete[]>();
  private readonly maxCacheSize = 100;

  /**
   * Détail d'un habitat par cd_hab.
   */
  getDetail(cdHab: number): Observable<HabitatDetail> {
    return this.http.get<HabitatDetail>(`${this.apiUrl}/${cdHab}/`);
  }

  /**
   * Autocomplete sur les habitats (trigrammes + unaccent).
   */
  autocomplete(search: string, options?: {
    cdTypo?: number;
    /** #469 — restreint la recherche à une ou plusieurs typologies. */
    cdTypos?: number[];
    limit?: number;
  }): Observable<HabitatAutocomplete[]> {
    if (search.length < 2) {
      return of([]);
    }

    // #469 — normalise les typologies (valeur unique ou liste) en un seul
    // paramètre `cd_typo` séparé par des virgules.
    const typos = (options?.cdTypos ?? (options?.cdTypo != null ? [options.cdTypo] : []))
      .filter(t => t != null);
    const cdTypoParam = typos.join(',');

    // #238 — inclure `limit` dans la clé pour éviter qu'un appel court
    // (limit=20) ne masque les résultats d'un appel ultérieur plus large.
    const cacheKey = `${search}|${cdTypoParam}|${options?.limit || ''}`;
    const cached = this.autocompleteCache.get(cacheKey);
    if (cached) {
      return of(cached);
    }

    let params = new HttpParams().set('search', search);
    if (cdTypoParam) params = params.set('cd_typo', cdTypoParam);
    if (options?.limit) params = params.set('limit', options.limit.toString());

    return this.http.get<HabitatAutocomplete[]>(
      `${this.apiUrl}/autocomplete/`, { params }
    ).pipe(
      tap(results => {
        if (this.autocompleteCache.size >= this.maxCacheSize) {
          const firstKey = this.autocompleteCache.keys().next().value;
          if (firstKey !== undefined) {
            this.autocompleteCache.delete(firstKey);
          }
        }
        this.autocompleteCache.set(cacheKey, results);
      })
    );
  }

  /**
   * Liste des typologies d'habitats.
   * @param onlyWithHabitats #469 — ne renvoie que les typologies ayant des
   *   habitats indexés (pour peupler le filtre de recherche).
   */
  getTypologies(onlyWithHabitats = false): Observable<Typologie[]> {
    let params = new HttpParams();
    if (onlyWithHabitats) params = params.set('with_habitats', '1');
    return this.http.get<Typologie[]>(`${this.apiUrl}/typo/`, { params });
  }

  /**
   * Classification d'origine d'un habitat + habitats liés (même référentiel).
   */
  getCorrespondances(cdHab: number): Observable<HabitatCorrespondanceResponse> {
    return this.http.get<HabitatCorrespondanceResponse>(
      `${this.apiUrl}/correspondance/${cdHab}/`
    );
  }

  /**
   * Valide une liste d'entrées (codes cd_hab, codes nomenclature lb_code,
   * ou noms français) contre HabRef.
   * Auto-détection : numérique → cd_hab, code type "G1.6" → lb_code, texte → nom.
   */
  validateBulk(items: string[]): Observable<HabitatBulkValidationResult> {
    return this.http.post<HabitatBulkValidationResult>(
      `${this.apiUrl}/validate-bulk/`, { items }
    );
  }
}
