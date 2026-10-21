import { FicheDocument, FichePlan } from '../../../core/models/exploration-fiche.model';
import { descriptionDocument, documentEnLigne, documentLocal, lienDocument } from './fiche-documents';

const document = (url: string | null): FicheDocument => ({
  id_document: 'a1b2', titre: 'Arrêté', nom_fichier: 'arrete.pdf', type_fichier: 'Document principal',
  support: url ? 'numerique' : 'papier', extension: '.pdf', taille_fichier: 1258291,
  date_document: null, description: null, url,
});

const plan = (datePublication: string | null, urlInstance = ''): FichePlan =>
  ({ date_publication: datePublication, url_instance: urlInstance } as FichePlan);

describe('#747 — documents de la fiche d’exploration', () => {
  it('garde une adresse absolue telle quelle', () => {
    const url = 'https://cicada.rnf.fr/api/public/documents/a1b2/';
    expect(lienDocument(plan('2026-10-20', 'https://autre.fr'), document(url))).toBe(url);
  });

  it('rattache une adresse relative d’un instantané à son instance d’origine', () => {
    expect(lienDocument(plan('2026-10-20', 'https://cen.fr/'), document('/api/public/documents/a1b2/')))
      .toBe('https://cen.fr/api/public/documents/a1b2/');
  });

  it('sans adresse d’origine, un instantané n’a pas de lien joignable', () => {
    expect(lienDocument(plan('2026-10-20'), document('/api/public/documents/a1b2/'))).toBeNull();
  });

  it('un document papier n’a pas de lien', () => {
    expect(lienDocument(plan(null), document(null))).toBeNull();
    expect(documentLocal(plan(null), document(null))).toBe(false);
  });

  it('un document d’une fiche lue en direct s’ouvre avec la session', () => {
    expect(documentLocal(plan(null), document('/api/public/documents/a1b2/'))).toBe(true);
    expect(documentLocal(plan('2026-10-20'), document('https://x/'))).toBe(false);
  });

  it('PDF ouvert dans le navigateur, bureautique téléchargée', () => {
    expect(documentEnLigne(document('x'))).toBe(true);
    expect(documentEnLigne({ ...document('x'), extension: '.docx' })).toBe(false);
  });

  it('décrit format et poids', () => {
    expect(descriptionDocument(document('x'))).toBe('PDF · 1,2 Mo');
  });
});
