/**
 * #746 — Rendu Markdown minimal des textes d'instance (CGU).
 *
 * Volontairement restreint à ce qu'un texte juridique utilise : titres (#, ##,
 * ###), paragraphes, listes à puces et numérotées, gras, italique et liens
 * http(s). Le texte est échappé AVANT toute mise en forme : aucun HTML saisi
 * n'est rendu, et un lien ne peut pas porter un autre schéma que http(s).
 */

function echapper(texte: string): string {
  return texte
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function enLigne(texte: string): string {
  return echapper(texte)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\s][^*]*?)\*/g, '$1<em>$2</em>');
}

export function renderMarkdown(source: string | null | undefined): string {
  const blocs: string[] = [];
  let paragraphe: string[] = [];
  let liste: { type: 'ul' | 'ol'; items: string[] } | null = null;

  const fermer = (): void => {
    if (paragraphe.length) {
      blocs.push(`<p>${paragraphe.map(enLigne).join('<br>')}</p>`);
      paragraphe = [];
    }
    if (liste) {
      blocs.push(`<${liste.type}>${liste.items.map(i => `<li>${enLigne(i)}</li>`).join('')}</${liste.type}>`);
      liste = null;
    }
  };

  for (const brute of (source ?? '').split(/\r?\n/)) {
    const ligne = brute.trim();
    const titre = /^(#{1,3})\s+(.*)$/.exec(ligne);
    const puce = /^[-*]\s+(.*)$/.exec(ligne);
    const numero = /^\d+[.)]\s+(.*)$/.exec(ligne);

    if (!ligne) {
      fermer();
    } else if (titre) {
      fermer();
      const niveau = titre[1].length;
      blocs.push(`<h${niveau}>${enLigne(titre[2])}</h${niveau}>`);
    } else if (puce || numero) {
      const type = puce ? 'ul' : 'ol';
      if (paragraphe.length || (liste && liste.type !== type)) {
        fermer();
      }
      liste ??= { type, items: [] };
      liste.items.push((puce ?? numero)![1]);
    } else {
      if (liste) {
        fermer();
      }
      paragraphe.push(ligne);
    }
  }
  fermer();
  return blocs.join('');
}
