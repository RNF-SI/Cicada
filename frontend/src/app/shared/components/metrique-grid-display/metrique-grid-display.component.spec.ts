import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateModule } from '@ngx-translate/core';
import { MetriqueGridDisplayComponent, GridMetrique } from './metrique-grid-display.component';

/** TranslateService minimal : renvoie la clé (suffit pour tester le formatage). */
const fakeTranslate = { instant: (k: string) => k } as any;

function makeComponent(): MetriqueGridDisplayComponent {
  return new MetriqueGridDisplayComponent(fakeTranslate);
}

describe('MetriqueGridDisplayComponent (#515)', () => {
  describe('getScoreRange — NUMERIQUE', () => {
    it('formate un intervalle borné [inf ; sup]', () => {
      const c = makeComponent();
      const met: GridMetrique = {
        type_metrique_mnemonique: 'NUMERIQUE',
        score_2_inf: 10, score_2_sup: 20,
        score_2_sup_inclusive: true, score_1_sup_inclusive: true,
      };
      // inf inclusif (palier 1 sup inclusif → palier 2 inf exclusif → ']')
      expect(c.getScoreRange(met, 2)).toBe(']10 ; 20]');
    });

    it('formate une borne ouverte supérieure (≤)', () => {
      const c = makeComponent();
      const met: GridMetrique = { type_metrique_mnemonique: 'NUMERIQUE', score_1_sup: 5, score_1_sup_inclusive: true };
      expect(c.getScoreRange(met, 1)).toBe('≤ 5');
    });

    it('formate une borne ouverte inférieure (≥) sur le dernier palier', () => {
      const c = makeComponent();
      const met: GridMetrique = { type_metrique_mnemonique: 'NUMERIQUE', score_5_inf: 40, score_4_sup_inclusive: true };
      // palier 4 sup inclusif → palier 5 inf exclusif → '>'
      expect(c.getScoreRange(met, 5)).toBe('> 40');
    });

    it('rend "- - -" pour un palier sans bornes', () => {
      const c = makeComponent();
      expect(c.getScoreRange({ type_metrique_mnemonique: 'NUMERIQUE' }, 3)).toBe('- - -');
    });

    it('masque un palier désactivé', () => {
      const c = makeComponent();
      const met: GridMetrique = { type_metrique_mnemonique: 'NUMERIQUE', score_2_inf: 10, score_2_sup: 20, inactive_levels: [2] };
      expect(c.getScoreRange(met, 2)).toBe('- - -');
    });
  });

  describe('getScoreRange — TEXTE / CHIFFRE', () => {
    it('rend le libellé pour TEXTE', () => {
      const c = makeComponent();
      const met: GridMetrique = { type_metrique_mnemonique: 'TEXTE', score_3_label: 'Présence moyenne' };
      expect(c.getScoreRange(met, 3)).toBe('Présence moyenne');
    });

    it('rend la valeur numérique pour CHIFFRE', () => {
      const c = makeComponent();
      const met: GridMetrique = { type_metrique_mnemonique: 'CHIFFRE', score_4_val: 3.5 };
      expect(c.getScoreRange(met, 4)).toBe('3.5');
    });
  });

  describe('isIndetermine', () => {
    it('vrai pour une métrique INDETERMINE', () => {
      expect(makeComponent().isIndetermine({ type_metrique_mnemonique: 'INDETERMINE' })).toBe(true);
    });
    it('faux sinon', () => {
      expect(makeComponent().isIndetermine({ type_metrique_mnemonique: 'NUMERIQUE' })).toBe(false);
    });
  });

  describe('getScoreGroups — fusion de paliers identiques', () => {
    it('fusionne deux paliers adjacents de même valeur (colspan 2)', () => {
      const c = makeComponent();
      const met: GridMetrique = { type_metrique_mnemonique: 'TEXTE', score_1_label: 'Oui', score_2_label: 'Oui' };
      const groups = c.getScoreGroups(met);
      expect(groups[0]).toEqual(expect.objectContaining({ primaryLevel: 1, colspan: 2, value: 'Oui' }));
    });

    it('ne fusionne pas les cellules vides', () => {
      const c = makeComponent();
      const groups = c.getScoreGroups({ type_metrique_mnemonique: 'NUMERIQUE' });
      // 5 cellules vides distinctes
      expect(groups.length).toBe(5);
      expect(groups.every(g => g.colspan === 1)).toBe(true);
    });
  });

  describe('hasExtraBlocks', () => {
    it('vrai si score_blocks non vide', () => {
      expect(makeComponent().hasExtraBlocks({ score_blocks: [{}] })).toBe(true);
    });
    it('faux sans blocs complémentaires', () => {
      expect(makeComponent().hasExtraBlocks({})).toBe(false);
    });
  });

  // Retour #515 : la grille scrollait horizontalement (table de 10 colonnes).
  // On garantit désormais que les métadonnées sont séparées de la grille et que
  // la table de paliers ne compte que 5 colonnes → affichage sans scroll.
  describe('rendu — pas de table large scrollable (retour #515)', () => {
    let fixture: ComponentFixture<MetriqueGridDisplayComponent>;

    beforeEach(async () => {
      await TestBed.configureTestingModule({
        imports: [MetriqueGridDisplayComponent, TranslateModule.forRoot()],
      }).compileComponents();
      fixture = TestBed.createComponent(MetriqueGridDisplayComponent);
    });

    it('rend les métadonnées hors de la grille de paliers', () => {
      fixture.componentInstance.metriques = [
        { id_metrique: 1, nom_metrique: 'Densité', unite: 'ind/ha', type_metrique_mnemonique: 'NUMERIQUE', score_1_sup: 5 },
      ];
      fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement;
      // Métadonnées dans une liste de définition dédiée, hors de la table.
      expect(el.querySelector('.metrique-meta dd')?.textContent).toContain('Densité');
      expect(el.querySelector('.metrique-scores .metrique-meta')).toBeNull();
    });

    it('la table de paliers ne compte que 5 colonnes (pas 10)', () => {
      fixture.componentInstance.metriques = [
        { id_metrique: 1, nom_metrique: 'Densité', type_metrique_mnemonique: 'NUMERIQUE', score_1_sup: 5 },
      ];
      fixture.detectChanges();
      const headers = fixture.nativeElement.querySelectorAll('.metrique-scores thead th');
      expect(headers.length).toBe(5);
    });
  });
});
