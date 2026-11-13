/**
 * #862 — Dates sans heure (avis CSRPN, comité, arrêté préfectoral, date d'un
 * document, date d'une mesure, lancement d'un suivi).
 *
 * Le serveur les échange en « AAAA-MM-JJ ». Le sélecteur de date rend, lui,
 * minuit HEURE LOCALE. Deux pièges, à éviter partout :
 * - `date.toISOString()` passe en UTC : en métropole (UTC+1/+2), le 15/03
 *   devient « 2026-03-14 » ;
 * - `new Date('2026-03-14')` est minuit UTC : affiché le 13/03 en Guyane ou aux
 *   Antilles, et une mesure du 1er janvier y compte pour l'année précédente.
 *
 * Un test de structure (`dates.utils.spec.ts`) refuse ces deux motifs.
 */

const ISO = /^(\d{4})-(\d{2})-(\d{2})/;

/** Date du sélecteur (ou chaîne déjà au format) → « AAAA-MM-JJ », jour local. */
export function dateLocaleISO(date: Date | string | null | undefined): string | null {
  if (!date) return null;
  if (typeof date === 'string') {
    const m = ISO.exec(date);
    return m ? `${m[1]}-${m[2]}-${m[3]}` : null;
  }
  if (isNaN(date.getTime())) return null;
  const a = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const j = String(date.getDate()).padStart(2, '0');
  return `${a}-${m}-${j}`;
}

/** « AAAA-MM-JJ » du serveur → Date à minuit local (pour un sélecteur de date). */
export function dateDepuisISO(texte: string | null | undefined): Date | null {
  const m = texte ? ISO.exec(texte) : null;
  if (!m) return null;
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

/** Année d'une date du serveur, sans passer par un fuseau. */
export function anneeDe(texte: string | null | undefined): number | null {
  const m = texte ? ISO.exec(texte) : null;
  return m ? Number(m[1]) : null;
}
