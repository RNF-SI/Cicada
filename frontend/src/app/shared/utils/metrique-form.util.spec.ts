import {
  blankMetriqueFormData,
  metriqueRefToFormData,
  buildMetriqueGridFields,
} from './metrique-form.util';
import { MetriqueRef } from '../../core/models/enjeu.model';

describe('blankMetriqueFormData', () => {
  it('produit une grille vide à 5 niveaux, NUMERIQUE croissant par défaut', () => {
    const fd = blankMetriqueFormData();
    expect(fd.type_metrique).toBeNull();
    expect(fd.format_metrique).toBeNull();
    expect(fd.sens_variation).toBe('CROISSANT');
    expect(Object.keys(fd.scores)).toHaveLength(5);
    expect(fd.scores[1]).toEqual({ inf: null, sup: null, val: null, label: '' });
    expect(fd._inactiveLevels).toEqual([]);
  });
});

describe('metriqueRefToFormData', () => {
  it('reconstruit une MetriqueFormData TEXTE depuis une MetriqueRef', () => {
    const ref: MetriqueRef = {
      id_metrique: 7,
      nom_metrique: 'Satisfaction',
      indicateur_id: 3,
      indicateur_nom: 'Réponse usagers',
      type_metrique_id: 12,
      format_metrique_id: 1371,
      etat_reference: 'Bon',
      score_1_label: 'Très mauvais',
      score_5_label: 'Très bon',
      inactive_levels: [4],
    };
    const fd = metriqueRefToFormData(ref);
    expect(fd.id_metrique).toBe(7);
    expect(fd.nom_metrique).toBe('Satisfaction');
    expect(fd.type_metrique).toBe(12);
    expect(fd.format_metrique).toBe(1371);
    expect(fd.etat_reference).toBe('Bon');
    expect(fd.scores[1].label).toBe('Très mauvais');
    expect(fd.scores[5].label).toBe('Très bon');
    expect(fd._inactiveLevels).toEqual([4]);
  });

  it('convertit les bornes numériques en nombres', () => {
    const ref: MetriqueRef = {
      id_metrique: 1, nom_metrique: 'm', indicateur_id: 1, indicateur_nom: 'i',
      score_1_inf: 0 as any, score_1_sup: '35' as any,
      has_borne_score1: true,
    };
    const fd = metriqueRefToFormData(ref);
    expect(fd.scores[1].inf).toBe(0);
    expect(fd.scores[1].sup).toBe(35);
    expect(fd.has_score1_optional_bound).toBe(true);
  });
});

describe('buildMetriqueGridFields', () => {
  const base = blankMetriqueFormData();

  it('TEXTE : n’émet que les libellés des niveaux actifs + inactive_levels', () => {
    const fd = { ...base, scores: { ...base.scores } };
    fd.scores[1] = { inf: null, sup: null, val: null, label: 'Mauvais' };
    fd.scores[2] = { inf: null, sup: null, val: null, label: 'Bon' };
    fd._inactiveLevels = [3, 4, 5];
    const out = buildMetriqueGridFields(fd, 'TEXTE');
    expect(out['score_1_label']).toBe('Mauvais');
    expect(out['score_2_label']).toBe('Bon');
    expect(out['score_3_label']).toBeUndefined();
    expect(out['inactive_levels']).toEqual([3, 4, 5]);
    // pas de champs NUMERIQUE
    expect(out['sens_variation']).toBeUndefined();
  });

  it('CHIFFRE : émet les valeurs val', () => {
    const fd = { ...base, scores: { ...base.scores } };
    fd.scores[1] = { inf: null, sup: null, val: 10, label: '' };
    fd.scores[2] = { inf: null, sup: null, val: 20, label: '' };
    fd._inactiveLevels = [3, 4, 5];
    const out = buildMetriqueGridFields(fd, 'CHIFFRE');
    expect(out['score_1_val']).toBe(10);
    expect(out['score_2_val']).toBe(20);
    expect(out['inactive_levels']).toEqual([3, 4, 5]);
  });

  it('NUMERIQUE : émet sens_variation, inclusivité, bornes et inactive_levels', () => {
    const fd = { ...base, scores: { ...base.scores } };
    fd.scores[1] = { inf: 0, sup: 35, val: null, label: '' };
    fd.scores[2] = { inf: 35, sup: 100, val: null, label: '' };
    const out = buildMetriqueGridFields(fd, 'NUMERIQUE');
    expect(out['sens_variation']).toBe('CROISSANT');
    expect(out['score_1_sup_inclusive']).toBe(true);
    expect(out['has_borne_score1']).toBe(false);
    expect(out['inactive_levels']).toEqual([]);
  });
});
