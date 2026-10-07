import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable } from 'rxjs';

/**
 * #696 / #698 — État du raccordement de l'instance au hub d'exploration.
 *
 * Contrat servi par `GET /api/federation/raccordement/` (super admin). Aucun
 * jeton ni empreinte n'y figure : on ne sait que s'ils sont définis.
 */
export type SourceJetons = 'environnement' | 'adhesion' | null;
export type StatutAdhesion = '' | 'en_attente' | 'code_envoye' | 'acceptee' | 'refusee';
export type NiveauDiagnostic = 'erreur' | 'attention' | 'info' | 'ok';

export type CleDiagnostic =
  | 'identite_manquante'
  | 'adhesion_refusee'
  | 'adhesion_code_envoye'
  | 'adhesion_en_attente'
  | 'non_raccorde'
  | 'jeton_depot_absent'
  | 'partage_inactif'
  | 'derniere_publication_echec'
  | 'aucune_publication'
  | 'ok';

/** Clés d'erreur renvoyées par le backend (ou déduites côté client). */
export const CLES_ERREUR_RACCORDEMENT = [
  'identite_manquante',
  'suivi_indisponible',
  'jeton_suivi_absent',
  'deja_acceptee',
  'jetons_environnement',
  'hub_injoignable',
  'jeton_refuse',
  'contact_invalide',
  'code_invalide',
  'code_expire',
  'trop_d_essais',
  'pas_de_code',
  'erreur_inconnue',
] as const;
export type CleErreurRaccordement = (typeof CLES_ERREUR_RACCORDEMENT)[number];

export interface ConfigurationRaccordement {
  instance_id: string;
  instance_libelle: string;
  identite_valide: boolean;
  hub_url: string;
  source_jetons: SourceJetons;
  jeton_depot_defini: boolean;
  jeton_lecture_defini: boolean;
  exploration_source: 'local' | 'hub' | string;
  relais_actif: boolean;
  publication_auto: boolean;
  partage: boolean;
  suivi_disponible: boolean;
}

export interface AdhesionHub {
  statut: StatutAdhesion;
  demandee_le: string | null;
  /** Échéance du code de confirmation envoyé par RNF (statut `code_envoye`). */
  code_expire_le: string | null;
  /** Adresse de contact donnée dans la demande (RNF y écrit). */
  contact_email: string;
  motif: string;
  possible: boolean;
  erreur_suivi: string | null;
}

export interface PublicationHub {
  date: string;
  origine: 'nuit' | 'manuelle';
  resultat: 'reussie' | 'echec' | 'ignoree';
  plans: number;
  documents: number;
  depublies: number;
  message: string;
}

export interface DiagnosticRaccordement {
  niveau: NiveauDiagnostic;
  cle: CleDiagnostic;
  parametres: Record<string, string | number>;
}

export interface EtatRaccordement {
  configuration: ConfigurationRaccordement;
  adhesion: AdhesionHub;
  publications: PublicationHub[];
  diagnostic: DiagnosticRaccordement;
}

/** Corps de `POST /api/federation/raccordement/adhesion/` : qui RNF doit contacter. */
export interface DemandeAdhesion {
  contact_nom: string;
  contact_email: string;
  contact_telephone: string;
  message: string;
}

/** Corps de `POST /api/federation/raccordement/contact/` (nom et e-mail : l'utilisateur connecté, côté serveur). */
export interface MessageContactRnf {
  sujet: string;
  message: string;
}

/** Résultat de `POST /api/federation/raccordement/verifier/`. */
export interface VerificationHub {
  hub_joignable: boolean;
  instance_reconnue: boolean | null;
  active: boolean | null;
  derniere_publication: string | null;
  plans: number | null;
  contenus: number | null;
  erreur: string | null;
}

/**
 * Extrait la clé d'erreur d'une réponse HTTP du raccordement.
 *
 * Le backend la place dans le corps (`erreur`, `code` ou `cle` selon la vue,
 * voire `detail`). Toute valeur hors de la liste connue retombe sur
 * `erreur_inconnue` : afficher une clé i18n inexistante montrerait la clé brute
 * à l'utilisateur.
 */
export function cleErreurRaccordement(err: unknown): CleErreurRaccordement {
  const corps = err instanceof HttpErrorResponse ? err.error : (err as { error?: unknown })?.error;
  if (corps && typeof corps === 'object') {
    const c = corps as Record<string, unknown>;
    for (const champ of ['erreur', 'code', 'cle', 'detail']) {
      const valeur = c[champ];
      if (typeof valeur === 'string' && (CLES_ERREUR_RACCORDEMENT as readonly string[]).includes(valeur)) {
        return valeur as CleErreurRaccordement;
      }
    }
  }
  return 'erreur_inconnue';
}

/**
 * Essais restants renvoyés avec l'erreur `code_invalide`, ou `null` si absents.
 */
export function essaisRestants(err: unknown): number | null {
  const corps = err instanceof HttpErrorResponse ? err.error : (err as { error?: unknown })?.error;
  const valeur = corps && typeof corps === 'object' ? (corps as Record<string, unknown>)['essais_restants'] : null;
  return typeof valeur === 'number' ? valeur : null;
}

/**
 * Code tel que saisi → forme envoyée : majuscules, sans espaces ni tirets.
 * Le serveur normalise de son côté ; on le fait aussi pour juger qu'un code est
 * complet avant d'activer le bouton.
 */
export function normaliserCode(code: string): string {
  return (code ?? '').toUpperCase().replace(/[\s-]/g, '');
}

@Injectable({ providedIn: 'root' })
export class FederationRaccordementService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = '/api/federation/raccordement/';

  /** État complet (actualise l'adhésion en attente auprès du suivi côté serveur). */
  etat(): Observable<EtatRaccordement> {
    return this.http.get<EtatRaccordement>(this.apiUrl);
  }

  /** Vérification en direct du hub : joignable ? instance reconnue et active ? */
  verifier(): Observable<VerificationHub> {
    return this.http.post<VerificationHub>(`${this.apiUrl}verifier/`, {});
  }

  /** Tire les jetons, envoie la demande d'adhésion au suivi RNF, renvoie l'état. */
  demanderAdhesion(demande: DemandeAdhesion): Observable<EtatRaccordement> {
    return this.http.post<EtatRaccordement>(`${this.apiUrl}adhesion/`, demande);
  }

  /**
   * Saisit le code de confirmation envoyé par RNF. Succès ⇒ adhésion acceptée et
   * enrôlement sur le hub, l'état complet est renvoyé. Le code n'est ni stocké ni
   * journalisé : il ne transite que dans cette requête.
   */
  confirmerCode(code: string): Observable<EtatRaccordement> {
    return this.http.post<EtatRaccordement>(`${this.apiUrl}confirmation/`, { code });
  }

  /** Écrit à RNF (si@rnfrance.org) via l'API de suivi. */
  contacterRnf(message: MessageContactRnf): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}contact/`, message);
  }
}
