import { TagVariant } from '../components/tag/tag.component';

/**
 * Apparence d'un tag : variante de couleur + icône Flaticon optionnelle.
 * `icon` absent = tag sans icône (variante neutre de la maquette).
 */
export interface TagAppearance {
  variant: TagVariant;
  icon?: string;
}

/**
 * Source de vérité unique de l'apparence des tags, d'après Figma
 * « 🧩 Tags » (node 4487:30877).
 *
 * Règle de la maquette : icône + couleur seulement pour les statuts principaux
 * où les deux font sens. Tout le reste (type d'aire protégée, référence de site
 * ou d'organisme, libellés annexes) est soit un tag `neutral` sans icône, soit
 * du texte simple sans tag du tout — cf. les annotations de la maquette.
 */

/** Statut d'un plan de gestion. */
export const PLAN_STATUS_TAG: Record<string, TagAppearance> = {
  draft: { variant: 'draft', icon: 'fi-rr-edit' },
  valide: { variant: 'success', icon: 'fi-rr-check' },
  // La maquette nomme cette icône `fi-rr-file-check` (document coché), mais ce
  // glyphe n'existe pas dans le set Uicons Rounded Regular 2.6.0 chargé par
  // index.html. `fi-rr-memo-circle-check` est l'équivalent disponible.
  modifie: { variant: 'info', icon: 'fi-rr-memo-circle-check' },
  mi_parcours: { variant: 'info', icon: 'fi-rr-memo-circle-check' },
  archive: { variant: 'muted', icon: 'fi-rr-box' },
  // #277 — étapes CSRPN : libellés neutres, sans icône (cf. « Avis CSRPN
  // demandé » dans la maquette).
  avis_csrpn: { variant: 'neutral' },
  comite_consultatif: { variant: 'neutral' },
  arrete_pref: { variant: 'neutral' },
};

/** Statut d'une demande de validation. */
export const VALIDATION_STATUS_TAG: Record<string, TagAppearance> = {
  approved: { variant: 'success', icon: 'fi-rr-check' },
  rejected: { variant: 'error', icon: 'fi-rr-cross' },
  cancelled: { variant: 'error', icon: 'fi-rr-cross' },
  expired: { variant: 'error', icon: 'fi-rr-cross' },
  pending: { variant: 'warning', icon: 'fi-rr-edit' },
};

/** Rôle d'un utilisateur. */
export const USER_ROLE_TAG: Record<string, TagAppearance> = {
  super_admin: { variant: 'error', icon: 'fi-rr-admin-alt' },
  admin_og: { variant: 'error', icon: 'fi-rr-admin-alt' },
  referent: { variant: 'warning', icon: 'fi-rr-star' },
  redacteur_principal: { variant: 'warning', icon: 'fi-rr-pencil' },
  user: { variant: 'info', icon: 'fi-rr-user' },
};

/** Statut d'un compte utilisateur. */
export const USER_STATUS_TAG: Record<string, TagAppearance> = {
  active: { variant: 'success', icon: 'fi-rr-check' },
  inactive: { variant: 'error', icon: 'fi-rr-cross' },
  rgpd_pending: { variant: 'warning', icon: 'fi-rr-edit' },
  anonymized: { variant: 'neutral' },
};

/** Niveau d'un log technique. */
export const LOG_LEVEL_TAG: Record<string, TagAppearance> = {
  critical: { variant: 'neutral', icon: 'fi-rr-megaphone' },
  error: { variant: 'error', icon: 'fi-rr-cross' },
  warning: { variant: 'warning', icon: 'fi-rr-shield-exclamation' },
  info: { variant: 'info', icon: 'fi-rr-info' },
};

/** Repli neutre : tag saumon sans icône. */
export const NEUTRAL_TAG: TagAppearance = { variant: 'neutral' };

/**
 * Apparence d'un tag de priorité d'action de gestion (#566).
 *
 * Priorité 1 / 2 / 3 → palette scores (rouge / orange / jaune), conformément au
 * CLAUDE.md (« score-* : Scores / priorités ») et au kit UI. Texte noir, AA.
 * Sans icône (couleur suffisante). Détection sur le libellé (« Priorité 1 »…),
 * cohérente avec le reste de l'application. Renvoie `null` si aucune priorité.
 */
export function getPrioriteTag(prioriteLabel: string | null | undefined): TagAppearance | null {
  const label = prioriteLabel ?? '';
  if (!label) return null;
  if (label.includes('1')) return { variant: 'score-very-bad' };
  if (label.includes('2')) return { variant: 'score-bad' };
  if (label.includes('3')) return { variant: 'score-neutral' };
  return NEUTRAL_TAG;
}

/** Apparence d'un statut de plan, avec repli neutre si inconnu. */
export function getPlanStatusTag(statut: string | null | undefined): TagAppearance {
  return PLAN_STATUS_TAG[statut ?? ''] ?? NEUTRAL_TAG;
}

/** Apparence d'un statut de demande de validation, avec repli neutre si inconnu. */
export function getValidationStatusTag(statut: string | null | undefined): TagAppearance {
  return VALIDATION_STATUS_TAG[statut ?? ''] ?? NEUTRAL_TAG;
}

/**
 * Alias des libellés d'accès renvoyés par l'API vers la clé de rôle du kit.
 * La maquette ne connaît qu'un seul tag « Utilisateur » : un membre d'un site
 * ou d'un plan doit donc s'afficher comme tel, quel que soit l'écran.
 * Les niveaux qui ne sont pas un rôle (`conservateur`, `organisme`, `plan`…)
 * ne sont volontairement PAS aliasés : ils retombent sur le tag neutre.
 */
const USER_ROLE_ALIASES: Record<string, string> = {
  utilisateur: 'user',
  membre: 'user',
};

/**
 * Apparence du rôle d'un utilisateur, avec repli neutre si inconnu.
 *
 * L'API expose le niveau de rôle sous la forme `utilisateur` (alias de `user`).
 * Le statut « référent » n'est pas un rôle : c'est un niveau d'accès porté par
 * `is_referent`, qui prime sur le rôle de base `utilisateur`.
 */
export function getUserRoleTag(
  niveauRole: string | null | undefined,
  isReferent = false,
): TagAppearance {
  const role = niveauRole ?? '';
  const normalized = USER_ROLE_ALIASES[role] ?? role;
  if (isReferent && normalized === 'user') {
    return USER_ROLE_TAG['referent'];
  }
  return USER_ROLE_TAG[normalized] ?? NEUTRAL_TAG;
}

/**
 * Apparence du niveau d'un log technique, avec repli neutre si inconnu.
 * L'API renvoie le niveau en majuscules (`WARNING`, `ERROR`, `CRITICAL`).
 */
export function getLogLevelTag(level: string | null | undefined): TagAppearance {
  return LOG_LEVEL_TAG[(level ?? '').toLowerCase()] ?? NEUTRAL_TAG;
}
