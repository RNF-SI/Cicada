import {
  getActionStatusForYear, getActionIcon, ACTION_LEGEND_ITEMS, ACTION_ICON_MAP,
  getGlobalRealisationKind, getGlobalRealisationLabelKey,
} from './action-status.util';
import { Operation } from '../../../core/models/enjeu.model';

/** Construit une opération minimale avec une année programmée et un niveau. */
function op(annee: number, periodicite: boolean, niveau: string | null): Operation {
  return {
    id_operation: 1,
    libelle: 'Op',
    operation_annees: [
      {
        annee,
        periodicite,
        realisation: niveau ? { niveau_realisation_mnemonique: niveau } : null,
      } as any,
    ],
    date_ajout: '', date_maj: '',
  } as Operation;
}

describe('action-status.util', () => {
  describe('getActionStatusForYear', () => {
    it('prévu + TERMINE → planned-realized', () => {
      expect(getActionStatusForYear(op(2025, true, 'TERMINE'), 2025)).toBe('planned-realized');
    });
    it('prévu + PARTIEL → planned-partial', () => {
      expect(getActionStatusForYear(op(2025, true, 'PARTIEL'), 2025)).toBe('planned-partial');
    });
    it('prévu + NON_REALISE → planned-not-realized (#379)', () => {
      expect(getActionStatusForYear(op(2025, true, 'NON_REALISE'), 2025)).toBe('planned-not-realized');
    });
    it('prévu sans réalisation → planned', () => {
      expect(getActionStatusForYear(op(2025, true, null), 2025)).toBe('planned');
    });
    it('non prévu + TERMINE → realized-unplanned', () => {
      expect(getActionStatusForYear(op(2025, false, 'TERMINE'), 2025)).toBe('realized-unplanned');
    });
    it('non prévu + PARTIEL → partial-unplanned', () => {
      expect(getActionStatusForYear(op(2025, false, 'PARTIEL'), 2025)).toBe('partial-unplanned');
    });
    it('non prévu sans réalisation → null', () => {
      expect(getActionStatusForYear(op(2025, false, null), 2025)).toBeNull();
    });
    it('année absente → null', () => {
      expect(getActionStatusForYear(op(2025, true, 'TERMINE'), 2030)).toBeNull();
    });
  });

  describe('getActionIcon', () => {
    it('renvoie le chemin de l\'asset pour un statut', () => {
      expect(getActionIcon('planned-not-realized')).toBe(ACTION_ICON_MAP['planned-not-realized']);
      expect(getActionIcon('planned-not-realized')).toContain('non-realise.svg');
    });
    it('renvoie une chaîne vide pour null', () => {
      expect(getActionIcon(null)).toBe('');
    });
  });

  it('la légende contient les 6 statuts dont « non réalisée »', () => {
    expect(ACTION_LEGEND_ITEMS.length).toBe(6);
    expect(ACTION_LEGEND_ITEMS.some(i => i.status === 'planned-not-realized')).toBe(true);
  });

  describe('getGlobalRealisationKind (#460)', () => {
    it('TERMINE → realise', () => {
      expect(getGlobalRealisationKind('TERMINE')).toBe('realise');
    });
    it('PARTIEL → partiel', () => {
      expect(getGlobalRealisationKind('PARTIEL')).toBe('partiel');
    });
    it('EN_COURS → en-cours (sablier)', () => {
      expect(getGlobalRealisationKind('EN_COURS')).toBe('en-cours');
    });
    it('NON_DEMARRE → non-commencee', () => {
      expect(getGlobalRealisationKind('NON_DEMARRE')).toBe('non-commencee');
    });
    it('null / undefined / aucune réponse → non-commencee', () => {
      expect(getGlobalRealisationKind(null)).toBe('non-commencee');
      expect(getGlobalRealisationKind(undefined)).toBe('non-commencee');
    });
    it('NON_REALISE / ABANDONNE / REPORTE → non-realise', () => {
      expect(getGlobalRealisationKind('NON_REALISE')).toBe('non-realise');
      expect(getGlobalRealisationKind('ABANDONNE')).toBe('non-realise');
      expect(getGlobalRealisationKind('REPORTE')).toBe('non-realise');
    });
  });

  describe('getGlobalRealisationLabelKey (#460)', () => {
    it('mappe chaque mnémonique vers sa clé i18n', () => {
      expect(getGlobalRealisationLabelKey('EN_COURS')).toBe('plans.suivis.actionGlobal.statut.enCours');
      expect(getGlobalRealisationLabelKey('NON_DEMARRE')).toBe('plans.suivis.actionGlobal.statut.nonCommencee');
      expect(getGlobalRealisationLabelKey(null)).toBe('plans.suivis.actionGlobal.statut.nonCommencee');
      expect(getGlobalRealisationLabelKey('TERMINE')).toBe('plans.suivis.actionGlobal.statut.realise');
    });
  });
});
