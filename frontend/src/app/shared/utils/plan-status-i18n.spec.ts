import { readFileSync } from 'fs';
import { join } from 'path';

/**
 * #205 — Le statut « Archivé » d'un plan de gestion est libellé « Terminé »
 * dans l'interface : un PG terminé reste consultable, et « Terminé » parle
 * davantage aux gestionnaires. Seuls les LIBELLÉS changent — la valeur en
 * base et le contrat d'API restent `archive`.
 *
 * Ces tests lisent le vrai fichier de traductions (et non un stub) afin de
 * détecter un renommage partiel ou un retour en arrière.
 */
describe('i18n — libellés du statut « Terminé » (#205)', () => {
  const translations = JSON.parse(
    readFileSync(join(__dirname, '../../../assets/i18n/fr.json'), 'utf-8')
  );

  /** Résout une clé pointée, ex. `plans.status.archive`. */
  function t(key: string): unknown {
    return key.split('.').reduce<any>((node, part) => node?.[part], translations);
  }

  describe('libellé de statut', () => {
    it('affiche « Terminé » sur le détail/la liste des plans', () => {
      expect(t('plans.status.archive')).toBe('Terminé');
    });

    it('affiche « Terminé » dans l’administration des plans', () => {
      expect(t('admin.plans.status.archive')).toBe('Terminé');
    });

    it('libelle la statistique agrégée « Terminés »', () => {
      expect(t('admin.plans.stats.archives')).toBe('Terminés');
    });
  });

  describe('verbe d’action', () => {
    it('utilise « Terminer » sur le bouton de cycle de vie', () => {
      expect(t('plans.lifecycle.actions.archive')).toBe('Terminer');
    });

    it('utilise « Terminer » dans l’administration des plans', () => {
      expect(t('admin.plans.actions.archive')).toBe('Terminer');
    });

    it('utilise « Terminer » dans la modale de clôture du plan précédent (#246)', () => {
      expect(t('plans.lifecycle.archivePrevious.title')).toBe('Terminer le plan précédent ?');
      expect(t('plans.lifecycle.archivePrevious.archive')).toBe('Terminer le précédent');
    });

    it('titre la confirmation « Terminer le plan de gestion »', () => {
      expect(t('plans.lifecycle.warnings.archiveTitle')).toBe('Terminer le plan de gestion');
    });
  });

  describe('aucun vocabulaire « archiv* » résiduel', () => {
    /** Aplatit un sous-arbre de traductions en paires [clé, valeur]. */
    function flatten(node: unknown, prefix = ''): Array<[string, string]> {
      if (typeof node === 'string') return [[prefix, node]];
      if (node === null || typeof node !== 'object') return [];
      return Object.entries(node as Record<string, unknown>).flatMap(([k, v]) =>
        flatten(v, prefix ? `${prefix}.${k}` : k)
      );
    }

    // Un renommage partiel (statut renommé mais pas le verbe, ou une modale
    // oubliée) laisserait « Archiver »/« archivé » visible quelque part.
    it.each(['plans', 'admin.plans'])(
      'ne laisse aucun libellé « archiv* » sous %s',
      (subtree) => {
        const offenders = flatten(t(subtree), subtree).filter(([, value]) =>
          /archiv/i.test(value)
        );
        expect(offenders).toEqual([]);
      }
    );
  });
});
