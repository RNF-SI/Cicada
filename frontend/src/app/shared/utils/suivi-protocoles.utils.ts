import { Protocole } from '../../core/models/enjeu.model';

/**
 * Protocoles envoyés par la fiche d'une action CS (#715).
 *
 * Un suivi peut porter plusieurs protocoles (#252), saisis dans le module
 * Inventaires. La fiche action n'en édite qu'un, le premier, et ne connaît pas
 * tous ses champs (période de suivi, documentation, mode de validation). Or le
 * serveur remplace la liste entière à chaque enregistrement : n'envoyer que le
 * protocole édité supprimait les suivants et vidait ces champs.
 *
 * On renvoie donc la liste complète : le premier protocole mis à jour avec ce
 * que la fiche action a saisi, les autres tels quels.
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
 * Champs du protocole que la fiche action saisit, tous présents : une valeur
 * vide (`''` / `null`) efface celle du protocole existant.
 */
export type ProtocoleSaisiParAction = { [K in ChampSaisiParAction]: Protocole[K] | null };

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
 */
export function protocolesDepuisAction(
  existants: Protocole[],
  saisi: ProtocoleSaisiParAction,
): Record<string, unknown>[] | undefined {
  if (existants.length > 0) {
    const [premier, ...suivants] = existants;
    return [
      { ...protocoleInscriptible(premier), ...saisi },
      ...suivants.map(protocoleInscriptible),
    ];
  }
  const renseigne = Object.values(saisi).some(estRenseigne);
  return renseigne ? [saisi as Record<string, unknown>] : undefined;
}
