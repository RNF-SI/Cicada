import { convertToParamMap } from '@angular/router';

import { ExplorationCriteres } from '../../core/models/exploration.model';
import { criteresDepuisUrl, criteresVersUrl } from './exploration-url';

/**
 * L'URL est la source de vérité de la recherche d'exploration : ces deux
 * fonctions doivent rester exactement réciproques, sans quoi un lien partagé
 * ne rejouerait pas la même recherche.
 */
describe('exploration-url', () => {
  describe('criteresDepuisUrl', () => {
    it('lit les listes séparées par des virgules', () => {
      const criteres = criteresDepuisUrl(
        convertToParamMap({ types: 'enjeu,pression', zones: '12,34' }),
      );

      expect(criteres.types).toEqual(['enjeu', 'pression']);
      expect(criteres.zones).toEqual([12, 34]);
    });

    it('ignore les valeurs vides d\'une liste', () => {
      expect(criteresDepuisUrl(convertToParamMap({ types: 'enjeu,,' })).types).toEqual([
        'enjeu',
      ]);
    });

    it('ne retient que les identifiants numériques', () => {
      expect(criteresDepuisUrl(convertToParamMap({ zones: '12,abc' })).zones).toEqual([
        12,
      ]);
    });

    it('ne remonte titresSeulement que lorsqu\'il est désactivé', () => {
      expect(
        criteresDepuisUrl(convertToParamMap({})).titresSeulement,
      ).toBeUndefined();
      expect(
        criteresDepuisUrl(convertToParamMap({ titres_seulement: 'false' }))
          .titresSeulement,
      ).toBe(false);
    });

    it('ignore une page invalide ou égale à 1', () => {
      expect(criteresDepuisUrl(convertToParamMap({ page: '1' })).page).toBeUndefined();
      expect(criteresDepuisUrl(convertToParamMap({ page: 'x' })).page).toBeUndefined();
      expect(criteresDepuisUrl(convertToParamMap({ page: '3' })).page).toBe(3);
    });
  });

  describe('criteresVersUrl', () => {
    it('met les critères vides à null pour qu\'Angular retire le paramètre', () => {
      const params = criteresVersUrl({ q: '  ', zones: [] });

      expect(params['q']).toBeNull();
      expect(params['zones']).toBeNull();
    });

    it('omet les valeurs par défaut', () => {
      const params = criteresVersUrl({ tri: 'pertinence', onglet: [], page: 1 });

      expect(params['tri']).toBeNull();
      expect(params['onglet']).toBeNull();
      expect(params['page']).toBeNull();
    });

    it("sérialise l'onglet groupé « Objectifs » comme ses deux types", () => {
      expect(
        criteresVersUrl({ onglet: ['objectif_lt', 'objectif_op'] })['onglet'],
      ).toBe('objectif_lt,objectif_op');
    });

    it('sérialise les listes en valeurs séparées par des virgules', () => {
      expect(criteresVersUrl({ zones: [12, 34] })['zones']).toBe('12,34');
    });
  });

  it('fait un aller-retour sans perte', () => {
    const criteres: ExplorationCriteres = {
      q: 'limicole',
      titresSeulement: false,
      types: ['enjeu', 'indicateur'],
      onglet: ['objectif_lt', 'objectif_op'],
      zones: [12, 34],
      organismes: [7],
      typesSite: ['RNN'],
      categoriesEnjeu: ['ecologique'],
      typesIndicateur: ['ETAT'],
      categoriesAction: ['SP'],
      statuts: ['en_cours'],
      tri: 'alphabetique',
      page: 2,
    };

    const params = criteresVersUrl(criteres);
    const nettoyes = Object.fromEntries(
      Object.entries(params).filter(([, valeur]) => valeur !== null),
    ) as Record<string, string>;

    expect(criteresDepuisUrl(convertToParamMap(nettoyes))).toEqual(criteres);
  });
});
