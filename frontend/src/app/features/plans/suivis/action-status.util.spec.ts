import {
  getActionStatusForYear, getActionIcon, ACTION_LEGEND_ITEMS, ACTION_ICON_MAP,
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
});
