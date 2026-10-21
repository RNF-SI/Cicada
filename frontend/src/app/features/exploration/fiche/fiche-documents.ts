import { FicheDocument, FichePlan } from '../../../core/models/exploration-fiche.model';

/**
 * #747 — Adresse à ouvrir pour un document de la fiche.
 *
 * L'instance d'origine publie une adresse absolue dès qu'elle connaît la
 * sienne (`CICADA_PUBLIC_URL`). Une adresse relative ne vaut que chez elle :
 * pour un instantané reçu du hub, elle est rattachée à `url_instance`, et sans
 * elle le document n'est pas joignable d'ici.
 */
export function lienDocument(plan: FichePlan, document: FicheDocument): string | null {
  if (!document.url) {
    return null;
  }
  if (/^https?:\/\//i.test(document.url)) {
    return document.url;
  }
  if (!plan.date_publication) {
    return document.url;
  }
  const racine = (plan.url_instance ?? '').replace(/\/+$/, '');
  return racine ? `${racine}${document.url}` : null;
}

/**
 * Un document d'un plan de cette instance, lu en direct : ouvert avec la
 * session plutôt que par un simple lien (cf. `ExplorationService.documentLocal`).
 */
export function documentLocal(plan: FichePlan, document: FicheDocument): boolean {
  return !plan.date_publication && !!document.url;
}

/** Formats affichés par le navigateur ; les autres se téléchargent (comme côté serveur). */
const EXTENSIONS_EN_LIGNE = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'];

export function documentEnLigne(document: FicheDocument): boolean {
  return EXTENSIONS_EN_LIGNE.includes((document.extension ?? '').replace(/^\./, '').toLowerCase());
}

/** Format et poids du document, ex. « PDF · 1,2 Mo ». */
export function descriptionDocument(document: FicheDocument): string {
  const morceaux: string[] = [];
  const extension = (document.extension ?? '').replace(/^\./, '');
  if (extension) {
    morceaux.push(extension.toUpperCase());
  }
  const octets = document.taille_fichier;
  if (octets) {
    const [valeur, unite] =
      octets >= 1024 * 1024 ? [octets / (1024 * 1024), 'Mo'] : [Math.max(octets / 1024, 1), 'Ko'];
    morceaux.push(`${valeur.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} ${unite}`);
  }
  return morceaux.join(' · ');
}
