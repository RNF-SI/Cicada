import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateModule, TranslateLoader, TranslateFakeLoader } from '@ngx-translate/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MetriqueFormComponent } from './metrique-form.component';
import { MetriqueFormData } from '../../../core/models/enjeu.model';

function freshMetrique(): MetriqueFormData {
  return {
    nom_metrique: '',
    type_metrique: null,
    unite: '',
    ponderation: null,
    etat_reference: '',
    scores: {
      1: { inf: null, sup: 10, val: null, label: '' },
      2: { inf: 10, sup: 20, val: null, label: '' },
      3: { inf: 20, sup: 30, val: null, label: '' },
      4: { inf: 30, sup: 40, val: null, label: '' },
      5: { inf: 40, sup: null, val: null, label: '' },
    },
    sens_variation: 'CROISSANT',
    score_1_sup_inclusive: true,
    score_2_sup_inclusive: true,
    score_3_sup_inclusive: false,
    score_4_sup_inclusive: true,
    has_score1_optional_bound: false,
    has_score5_optional_bound: false,
  };
}

describe('MetriqueFormComponent', () => {
  let component: MetriqueFormComponent;
  let fixture: ComponentFixture<MetriqueFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        MetriqueFormComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: TranslateFakeLoader } }),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MetriqueFormComponent);
    component = fixture.componentInstance;
    component.metrique = freshMetrique();
    fixture.detectChanges();
  });

  describe('niveaux actifs', () => {
    it('considère tous les niveaux actifs par défaut', () => {
      for (let level = 1 as 1 | 2 | 3 | 4 | 5; level <= 5; level = (level + 1) as any) {
        expect(component.isLevelActive(level)).toBe(true);
      }
    });

    it('désactive et efface les bornes du niveau ciblé', () => {
      component.toggleLevelActive(2);
      expect(component.isLevelActive(2)).toBe(false);
      expect(component.metrique.scores[2].inf).toBeNull();
      expect(component.metrique.scores[2].sup).toBeNull();
    });

    it('réactive un niveau précédemment désactivé', () => {
      component.toggleLevelActive(2);
      component.toggleLevelActive(2);
      expect(component.isLevelActive(2)).toBe(true);
    });
  });

  describe('mapping valeur-limite ↔ score_N_inf/sup', () => {
    it('renvoie le score_N_sup comme valeur de la frontière N (CROISSANT)', () => {
      // Boundary 1 = entre palier 1 et 2 → score_1_sup
      expect(component.getBoundaryValue(1)).toBe(10);
      expect(component.getBoundaryValue(2)).toBe(20);
      expect(component.getBoundaryValue(3)).toBe(30);
      expect(component.getBoundaryValue(4)).toBe(40);
    });

    it('met à jour les deux paliers adjacents lors d\'un changement de frontière', () => {
      component.setBoundaryValue(2, 25);
      expect(component.metrique.scores[2].sup).toBe(25);
      expect(component.metrique.scores[3].inf).toBe(25);
    });

    it('inverse l\'ordre des paliers en sens DECROISSANT', () => {
      component.metrique.sens_variation = 'DECROISSANT';
      // Avec DECROISSANT, ordered = [5, 4, 3, 2, 1].
      // Boundary 1 sépare ordered[0]=5 et ordered[1]=4 → score_5_sup
      expect(component.scoreMetaOrdered[0].level).toBe(5);
      expect(component.scoreMetaOrdered[4].level).toBe(1);
    });
  });

  describe('inclusivité des frontières', () => {
    it('lit score_N_sup_inclusive pour la frontière N (CROISSANT)', () => {
      expect(component.isBoundaryInLeft(1)).toBe(true);   // score_1_sup_inclusive
      expect(component.isBoundaryInLeft(3)).toBe(false);  // score_3_sup_inclusive
    });

    it('bascule l\'inclusivité de la frontière ciblée', () => {
      const before = component.metrique.score_2_sup_inclusive;
      component.toggleBoundaryInclusion(2);
      expect(component.metrique.score_2_sup_inclusive).toBe(!before);
    });
  });

  describe('événements', () => {
    it('émet l\'événement delete au clic corbeille', () => {
      const spy = jest.fn();
      component.delete.subscribe(spy);
      component.onMetriqueDelete();
      expect(spy).toHaveBeenCalled();
    });

    it('émet metriqueChange après chaque mutation', () => {
      const spy = jest.fn();
      component.metriqueChange.subscribe(spy);
      component.setBoundaryValue(1, 5);
      expect(spy).toHaveBeenCalledWith(component.metrique);
    });
  });
});
