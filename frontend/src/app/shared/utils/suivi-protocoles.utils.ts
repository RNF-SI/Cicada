import { Protocole } from '../../core/models/enjeu.model';

/**
 * Protocoles envoyés par la fiche d'une action CS (#715, #732).
 *
 * Un suivi peut porter plusieurs protocoles (#252) ; la fiche action les saisit
 * tous depuis #732, mais ne connaît pas tous leurs champs (période de suivi,
 * documentation, mode de validation : propres au module Inventaires). Or le
 * serveur remplace la liste entière à chaque enregistrement : n'envoyer que ce
 * que la fiche action saisit viderait ces champs.
 *
 * Chaque protocole saisi est donc fusionné avec le protocole existant de même
 * `id_protocole` (relu de l'API), qui garde ainsi ses autres champs. Un
 * protocole retiré de la fiche disparaît ; un protocole ajouté n'a pas d'id.
 */

type ChampSaisiParAction =
  | 'protocole_dans_campanule'
  | 'protocole_campanule_nom'
  | 'cd_protocole_campanule'
  | 'nb_etp_cycle'
  | 'nom_protocole'
  | 'respect_protocole'
  | 'justification_non_respect'
  | 'differences_protocole'
  | 'description_protocole'
  | 'objectif_protocole'
  | 'periode_echantillonnage';

/**
 * Champs d'un protocole que la fiche action saisit, tous présents : une valeur
 * vide (`''` / `null`) efface celle du protocole existant. `id_protocole`
 * désigne le protocole existant édité (null pour un protocole ajouté) : il ne
 * sert qu'à la fusion et n'est jamais envoyé.
 */
export type ProtocoleSaisiParAction =
  { [K in ChampSaisiParAction]: Protocole[K] | null } & { id_protocole: number | null };

/** Retire les champs non inscriptibles d'un protocole relu de l'API. */
export function protocoleInscriptible(p: Protocole): Record<string, unknown> {
  const { id_protocole, date_ajout, date_maj, ...rest } = p as Record<string, any>;
  return rest;
}

function estRenseigne(v: unknown): boolean {
  return v !== null && v !== undefined && v !== '';
}

/**
 * Liste à envoyer dans `suivi_inventaire.protocoles`, ou `undefined` pour ne
 * pas toucher aux protocoles (nouveau suivi sans protocole saisi).
 *
 * Un bloc ajouté puis laissé vide est ignoré : il ne doit pas créer un
 * protocole sans contenu.
 */
export function protocolesDepuisAction(
  existants: Protocole[],
  saisis: ProtocoleSaisiParAction[],
): Record<string, unknown>[] | undefined {
  const parId = new Map(existants.filter((p) => p.id_protocole != null).map((p) => [p.id_protocole!, p]));

  const liste = saisis.flatMap(({ id_protocole, ...champs }) => {
    const existant = id_protocole != null ? parId.get(id_protocole) : undefined;
    if (existant) return [{ ...protocoleInscriptible(existant), ...champs }];
    return Object.values(champs).some(estRenseigne) ? [champs as Record<string, unknown>] : [];
  });

  if (existants.length === 0 && liste.length === 0) return undefined;
  return liste;
}
