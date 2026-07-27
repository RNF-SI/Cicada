/**
 * #611 — numérotation des postes homonymes dans les listes de choix.
 */
import { posteDisplayLabel, posteDisplayLabelById } from './poste-label';

const POSTES = [
  { id_poste: 1, libelle: 'Conservateur' },
  { id_poste: 2, libelle: 'Animateur nature' },
  { id_poste: 3, libelle: 'Animateur nature' },
  { id_poste: 4, libelle: 'Garde-technicien' },
];

describe('posteDisplayLabel (#611)', () => {
  it('numérote les postes qui partagent le même libellé', () => {
    expect(posteDisplayLabel(POSTES[1], POSTES)).toBe('Animateur nature 1');
    expect(posteDisplayLabel(POSTES[2], POSTES)).toBe('Animateur nature 2');
  });

  it('ne numérote pas un libellé unique', () => {
    expect(posteDisplayLabel(POSTES[0], POSTES)).toBe('Conservateur');
    expect(posteDisplayLabel(POSTES[3], POSTES)).toBe('Garde-technicien');
  });

  it('retombe sur le libellé de repli quand le poste n’en a pas', () => {
    const sansLibelle = { id_poste: 9, libelle: '' };
    expect(posteDisplayLabel(sansLibelle, [sansLibelle], 'Poste sans nom')).toBe('Poste sans nom');
    expect(posteDisplayLabel(null, POSTES, 'Poste sans nom')).toBe('Poste sans nom');
  });

  it('n’invente pas d’indice pour un poste absent de la liste', () => {
    const inconnu = { id_poste: 99, libelle: 'Animateur nature' };
    expect(posteDisplayLabel(inconnu, POSTES)).toBe('Animateur nature');
  });

  it('résout aussi depuis un identifiant', () => {
    expect(posteDisplayLabelById(3, POSTES)).toBe('Animateur nature 2');
    expect(posteDisplayLabelById(1, POSTES)).toBe('Conservateur');
    expect(posteDisplayLabelById(null, POSTES, '—')).toBe('—');
    expect(posteDisplayLabelById(42, POSTES, '—')).toBe('—');
  });
});
