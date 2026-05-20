import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { tap } from 'rxjs/operators';

export interface TaxrefVersion {
  referential_name: string;
  version: string;
  update_date: string;
}

export interface TaxrefAutocomplete {
  cd_nom: number;
  cd_ref: number;
  search_name: string;
  nom_valide: string;
  nom_vern: string | null;
  lb_nom: string;
  regne: string;
  group2_inpn: string;
  id_rang: string;
}

export interface TaxrefDetail {
  cd_nom: number;
  cd_ref: number;
  id_statut: string;
  id_habitat: number;
  id_rang: string;
  regne: string;
  phylum: string;
  classe: string;
  ordre: string;
  famille: string;
  sous_famille: string;
  tribu: string;
  cd_taxsup: number;
  cd_sup: number;
  lb_nom: string;
  lb_auteur: string;
  nom_complet: string;
  nom_complet_html: string;
  nom_valide: string;
  nom_vern: string | null;
  nom_vern_eng: string | null;
  group1_inpn: string;
  group2_inpn: string;
  group3_inpn: string;
  url: string;
}

export interface TaxrefListItem {
  cd_nom: number;
  cd_ref: number;
  lb_nom: string;
  nom_complet: string;
  nom_valide: string;
  nom_vern: string | null;
  regne: string;
  group2_inpn: string;
  id_rang: string;
  famille: string;
}

export interface BulkValidationFoundItem {
  input: string;
  cd_nom: number;
  nom_complet: string;
  nom_valide: string;
  nom_vern: string | null;
  regne: string;
  group2_inpn: string;
  id_rang: string;
}

export interface BulkValidationNotFoundItem {
  input: string;
  candidates: { cd_nom: number; nom_valide: string; nom_vern: string | null }[];
}

export interface BulkValidationResult {
  found: BulkValidationFoundItem[];
  not_found: BulkValidationNotFoundItem[];
}

/**
 * Libellés français des rangs taxonomiques TaxRef (codes id_rang).
 * Couvre les 47 codes rencontrés dans taxonomie.vm_taxref_list_forautocomplete
 * (la table taxonomie.bib_taxref_rangs n'en expose que 16).
 */
export const TAXREF_RANG_LABELS: Record<string, string> = {
  KD: 'Règne',
  SPRG: 'Super-règne',
  SSRG: 'Sous-règne',
  IFRG: 'Infra-règne',
  SBDV: 'Sous-division',
  PH: 'Embranchement',
  SBPH: 'Sous-embranchement',
  IFPH: 'Infra-embranchement',
  CL: 'Classe',
  SBCL: 'Sous-classe',
  SPCL: 'Super-classe',
  IFCL: 'Infra-classe',
  PVCL: 'Parv-classe',
  OR: 'Ordre',
  SBOR: 'Sous-ordre',
  SPOR: 'Super-ordre',
  IFOR: 'Infra-ordre',
  PVOR: 'Parv-ordre',
  FM: 'Famille',
  SBFM: 'Sous-famille',
  SPFM: 'Super-famille',
  GN: 'Genre',
  SSGN: 'Sous-genre',
  TR: 'Tribu',
  SSTR: 'Sous-tribu',
  SPTR: 'Super-tribu',
  ES: 'Espèce',
  SSES: 'Sous-espèce',
  VAR: 'Variété',
  SVAR: 'Sous-variété',
  FO: 'Forme',
  SSFO: 'Sous-forme',
  FOES: "Forme d'espèce",
  SC: 'Section',
  SBSC: 'Sous-section',
  AGES: 'Agrégat',
  HYB: 'Hybride',
  CVAR: 'Cultivar',
  AB: 'Aberration',
  CLAD: 'Clade',
  RACE: 'Race',
  COH: 'Cohorte',
  SCO: 'Sous-cohorte',
  SSCO: 'Sous-cohorte',
  LEG: 'Légion',
  SER: 'Série',
  SSER: 'Sous-série',
  CAR: 'Caracère',
  MO: 'Morpho-type',
  Dumm: 'Indéterminé',
};

/**
 * Libellé français d'un rang taxonomique. Si le code est inconnu, le code brut
 * est retourné pour rester informatif.
 */
export function getTaxrefRangLabel(idRang: string | null | undefined): string {
  if (!idRang) return '';
  return TAXREF_RANG_LABELS[idRang] || idRang;
}

@Injectable({
  providedIn: 'root'
})
export class TaxonomyService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/taxref';

  // Cache simple pour les résultats d'autocomplete fréquents
  private autocompleteCache = new Map<string, TaxrefAutocomplete[]>();
  private readonly maxCacheSize = 100;

  /**
   * Version courante du référentiel TaxRef.
   */
  getVersion(): Observable<TaxrefVersion> {
    return this.http.get<TaxrefVersion>(`${this.apiUrl}/version/`);
  }

  /**
   * Liste paginée de taxons avec filtres.
   */
  list(params?: {
    page?: number;
    page_size?: number;
    regne?: string;
    group2_inpn?: string;
    id_rang?: string;
    valid_only?: boolean;
  }): Observable<{ count: number; results: TaxrefListItem[] }> {
    let httpParams = new HttpParams();
    if (params?.page) httpParams = httpParams.set('page', params.page.toString());
    if (params?.page_size) httpParams = httpParams.set('page_size', params.page_size.toString());
    if (params?.regne) httpParams = httpParams.set('regne', params.regne);
    if (params?.group2_inpn) httpParams = httpParams.set('group2_inpn', params.group2_inpn);
    if (params?.id_rang) httpParams = httpParams.set('id_rang', params.id_rang);
    if (params?.valid_only) httpParams = httpParams.set('valid_only', 'true');

    return this.http.get<{ count: number; results: TaxrefListItem[] }>(
      `${this.apiUrl}/`, { params: httpParams }
    );
  }

  /**
   * Détail d'un taxon par cd_nom.
   */
  getDetail(cdNom: number): Observable<TaxrefDetail> {
    return this.http.get<TaxrefDetail>(`${this.apiUrl}/${cdNom}/`);
  }

  /**
   * Autocomplete sur les taxons (trigrammes + unaccent).
   * Résultats mis en cache côté client.
   */
  autocomplete(search: string, options?: {
    limit?: number;
    regne?: string;
    group2_inpn?: string;
  }): Observable<TaxrefAutocomplete[]> {
    if (search.length < 2) {
      return of([]);
    }

    // Vérifier le cache. #238 — inclure `limit` dans la clé pour éviter
    // qu'un appel court avec limit=20 ne masque les résultats supplémentaires
    // que demande un appel ultérieur avec un limit plus haut.
    const cacheKey = `${search}|${options?.regne || ''}|${options?.group2_inpn || ''}|${options?.limit || ''}`;
    const cached = this.autocompleteCache.get(cacheKey);
    if (cached) {
      return of(cached);
    }

    let params = new HttpParams().set('search', search);
    if (options?.limit) params = params.set('limit', options.limit.toString());
    if (options?.regne) params = params.set('regne', options.regne);
    if (options?.group2_inpn) params = params.set('group2_inpn', options.group2_inpn);

    return this.http.get<TaxrefAutocomplete[]>(
      `${this.apiUrl}/autocomplete/`, { params }
    ).pipe(
      tap(results => {
        // Gérer la taille du cache
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
   * Recherche libre sur un champ.
   */
  searchField(field: string, term: string, limit = 20): Observable<TaxrefListItem[]> {
    return this.http.get<TaxrefListItem[]>(
      `${this.apiUrl}/search/${field}/${encodeURIComponent(term)}/`,
      { params: new HttpParams().set('limit', limit.toString()) }
    );
  }

  /**
   * Valide une liste d'entrées (codes cd_nom, noms scientifiques
   * ou noms vernaculaires) contre TaxRef.
   * Auto-détection : numérique → cd_nom, texte → nom.
   */
  validateBulk(items: string[]): Observable<BulkValidationResult> {
    return this.http.post<BulkValidationResult>(
      `${this.apiUrl}/validate-bulk/`, { items }
    );
  }
}
