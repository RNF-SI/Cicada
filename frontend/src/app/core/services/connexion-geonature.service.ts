import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable } from 'rxjs';

/**
 * #769 — Connexion GeoNature / UsersHub réglée depuis Administration > Paramètres.
 *
 * Contrat de `GET /api/auth/connexion-geonature/` (super admin). Le mot de
 * passe du compte de lecture n'y figure jamais : seulement `mot_de_passe_defini`.
 */
export type ModeConnexion = 'local' | 'geonature';
/** Origine d'une valeur : le `.env` du serveur (verrouillée ici), la base, ou la valeur par défaut. */
export type OrigineReglage = 'environnement' | 'base' | null;

export const CHAMPS_CONNEXION = [
  'libelle',
  'organismes_exclus',
  'code_application',
  'db_host',
  'db_port',
  'db_name',
  'db_user',
  'db_sslmode',
] as const;
export type ChampConnexion = (typeof CHAMPS_CONNEXION)[number];

export interface EtatConnexionGeoNature {
  mode: ModeConnexion;
  configuree: boolean;
  base_sur_ce_serveur: boolean;
  valeurs: Record<ChampConnexion, string | number>;
  mot_de_passe_defini: boolean;
  origines: Record<ChampConnexion | 'db_password', OrigineReglage> & { mode: 'environnement' | 'base' };
  modifie_le: string | null;
  modifie_par: string | null;
}

export type MotifRefus = 'absent' | 'inactif' | 'sans_droit';

export interface BilanComptes {
  total: number;
  autorises: number;
  refuses: number;
  super_admins_autorises: number;
  comptes: { id: number; email: string; super_admin: boolean; motif: MotifRefus | null }[];
}

export interface ResultatTest {
  ok: boolean;
  erreur: string | null;
  message: string;
  chiffree: boolean | null;
  application: boolean | null;
  bilan: BilanComptes | null;
  vous: { autorise: boolean; motif: MotifRefus | null } | null;
}

export type SaisieConnexion = Partial<Record<ChampConnexion | 'db_password', string | number>> & {
  effacer_mot_de_passe?: boolean;
};

/** Corps d'un refus : code stable, message, et le résultat du test quand il y en a un. */
export interface ErreurConnexion {
  code: string;
  detail: string;
  test?: ResultatTest;
}

export function erreurConnexion(err: HttpErrorResponse): ErreurConnexion | null {
  const corps = err?.error;
  return corps && typeof corps.code === 'string' ? (corps as ErreurConnexion) : null;
}

/** URL du script, servi par le dépôt (le serveur de la base n'a pas toujours CICADA installé). */
export const URL_SCRIPT_LECTURE =
  'https://raw.githubusercontent.com/RNF-SI/Cicada/main/packaging/debian/usr/bin/cicada-usershub-lecture';

/**
 * Commande à lancer, en root, sur le serveur de la base UsersHub : crée le
 * compte de lecture et autorise ce serveur CICADA (même logique que le
 * formulaire d'installation).
 */
export function commandeCompteLecture(
  base: string,
  code: string,
  surCeServeur: boolean,
  adresseCicada: string,
): string {
  const db = base.trim() || '<base>';
  const app = code.trim() || 'CICADA';
  if (surCeServeur) {
    return `sudo cicada-usershub-lecture --db ${db} --docker-local --code ${app}`;
  }
  const client = adresseCicada.trim() ? `${adresseCicada.trim().replace(/\/32$/, '')}/32` : '<adresse de ce serveur>/32';
  return (
    `curl -fsSL ${URL_SCRIPT_LECTURE} -o /tmp/cicada-usershub-lecture\n` +
    `sudo bash /tmp/cicada-usershub-lecture --db ${db} --client ${client} --code ${app}`
  );
}

@Injectable({ providedIn: 'root' })
export class ConnexionGeoNatureService {
  private readonly http = inject(HttpClient);
  private readonly url = '/api/auth/connexion-geonature/';

  etat(): Observable<EtatConnexionGeoNature> {
    return this.http.get<EtatConnexionGeoNature>(this.url);
  }

  configurer(saisie: SaisieConnexion): Observable<EtatConnexionGeoNature> {
    return this.http.patch<EtatConnexionGeoNature>(this.url, saisie);
  }

  tester(): Observable<ResultatTest> {
    return this.http.post<ResultatTest>(`${this.url}tester/`, {});
  }

  activer(confirmer = false): Observable<ResultatTest> {
    return this.http.post<ResultatTest>(`${this.url}activer/`, { confirmer });
  }

  desactiver(confirmer = false): Observable<EtatConnexionGeoNature> {
    return this.http.post<EtatConnexionGeoNature>(`${this.url}desactiver/`, { confirmer });
  }
}
