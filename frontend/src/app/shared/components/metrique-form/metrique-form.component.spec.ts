import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Observable, of } from 'rxjs';
import { MetriqueFormComponent } from './metrique-form.component';
import { MetriqueFormData } from '../../../core/models/enjeu.model';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<Record<string, never>> {
    return of({});
  }
}

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
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FakeTranslateLoader } }),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MetriqueFormComponent);
    component = fixture.componentInstance;
    component.metrique = freshMetrique();
    fixture.detectChanges();
  });

  describe('mainBlock (vue flat du bloc principal)', () => {
    it('expose les valeurs des scores depuis metrique.scores[N]', () => {
      const block = component.mainBlock;
      expect(block.score_1_sup).toBe(10);
      expect(block.score_2_inf).toBe(10);
      expect(block.score_5_inf).toBe(40);
      expect(block.sens_variation).toBe('CROISSANT');
    });

    it('propage les changements vers metrique.scores[N]', () => {
      const updated = { ...component.mainBlock, score_3_inf: 25 };
      component.onMainBlockChange(updated);
      expect(component.metrique.scores[3].inf).toBe(25);
    });

    it('propage le sens de variation', () => {
      component.onMainBlockChange({ ...component.mainBlock, sens_variation: 'DECROISSANT' });
      expect(component.metrique.sens_variation).toBe('DECROISSANT');
    });
  });

  describe('blocs complémentaires (#247)', () => {
    it('démarre avec aucun bloc complémentaire', () => {
      expect(component.blocks.length).toBe(0);
    });

    it('addBlock() ajoute un bloc OR / CROISSANT vide', () => {
      component.addBlock();
      expect(component.blocks.length).toBe(1);
      expect(component.blocks[0].position).toBe(1);
      expect(component.blocks[0].logical_op).toBe('OR');
      expect(component.blocks[0].sens_variation).toBe('CROISSANT');
      expect(component.blocks[0].group_open).toBe(0);
      expect(component.blocks[0].group_close).toBe(0);
    });

    it('addBlock() x3 numérote les positions correctement', () => {
      component.addBlock();
      component.addBlock();
      component.addBlock();
      expect(component.blocks.map(b => b.position)).toEqual([1, 2, 3]);
    });

    it('removeBlock() renumérote les positions restantes', () => {
      component.addBlock();
      component.addBlock();
      component.addBlock();
      component.removeBlock(1);
      expect(component.blocks.length).toBe(2);
      expect(component.blocks.map(b => b.position)).toEqual([1, 2]);
    });

    it('setBlockLogicalOp() change l\'opérateur', () => {
      component.addBlock();
      component.setBlockLogicalOp(0, 'AND');
      expect(component.blocks[0].logical_op).toBe('AND');
    });

    it('toggleParensOpen() bascule group_open entre 0 et 1', () => {
      component.addBlock();
      expect(component.blocks[0].group_open).toBe(0);
      component.toggleParensOpen(0);
      expect(component.blocks[0].group_open).toBe(1);
      component.toggleParensOpen(0);
      expect(component.blocks[0].group_open).toBe(0);
    });

    it('toggleParensClose() bascule group_close', () => {
      component.addBlock();
      component.toggleParensClose(0);
      expect(component.blocks[0].group_close).toBe(1);
    });
  });

  describe('événements', () => {
    it('émet delete au clic corbeille', () => {
      const spy = jest.fn();
      component.delete.subscribe(spy);
      component.onMetriqueDelete();
      expect(spy).toHaveBeenCalled();
    });

    it('émet metriqueChange après modification du bloc principal', () => {
      const spy = jest.fn();
      component.metriqueChange.subscribe(spy);
      component.onMainBlockChange({ ...component.mainBlock, score_1_sup: 15 });
      expect(spy).toHaveBeenCalledWith(component.metrique);
    });

    it('émet metriqueChange après ajout d\'un bloc', () => {
      const spy = jest.fn();
      component.metriqueChange.subscribe(spy);
      component.addBlock();
      expect(spy).toHaveBeenCalled();
    });
  });

  describe('#359 niveaux actifs (Chiffre / Texte)', () => {
    it('tous les niveaux actifs par défaut', () => {
      expect([1, 2, 3, 4, 5].every(l => component.isLevelActive(l))).toBe(true);
    });

    it('toggleLevelActive désactive puis réactive un niveau', () => {
      component.toggleLevelActive(3);
      expect(component.isLevelActive(3)).toBe(false);
      expect(component.metrique._inactiveLevels).toContain(3);
      component.toggleLevelActive(3);
      expect(component.isLevelActive(3)).toBe(true);
      expect(component.metrique._inactiveLevels).not.toContain(3);
    });

    it('désactiver un niveau vide sa valeur et son label', () => {
      component.metrique.scores[2].val = 12;
      component.metrique.scores[2].label = 'Bon';
      component.toggleLevelActive(2);
      expect(component.metrique.scores[2].val).toBeNull();
      expect(component.metrique.scores[2].label).toBe('');
    });

    it('émet metriqueChange au toggle', () => {
      const spy = jest.fn();
      component.metriqueChange.subscribe(spy);
      component.toggleLevelActive(4);
      expect(spy).toHaveBeenCalled();
    });
  });
});
