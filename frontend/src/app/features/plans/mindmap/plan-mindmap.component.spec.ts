import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute } from '@angular/router';
import { provideRouter } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { PlanMindmapComponent } from './plan-mindmap.component';
import { MindmapNode } from '../../../core/models/mindmap.model';

/**
 * #591 — Tableau d'arborescence : libellés, palette par colonne, alignement
 * (l'état actuel occupe deux colonnes) et suppression de la légende.
 */
describe('PlanMindmapComponent (#591)', () => {
  let fixture: ComponentFixture<PlanMindmapComponent>;
  let component: PlanMindmapComponent;

  const node = (entityType: string, branche?: 'etat' | 'reponse'): MindmapNode =>
    ({ name: 'x', entityType, branche } as MindmapNode);

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PlanMindmapComponent, TranslateModule.forRoot(), NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: new Map<string, string>() } },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PlanMindmapComponent);
    component = fixture.componentInstance;
  });

  describe('libellés', () => {
    it('nomme « Action » et non « Opération » (item 1)', () => {
      expect(component.getEntityLabelKey(node('operation')))
        .toBe('plans.mindmap.entities.operation');
    });

    it('distingue indicateur d\'état et indicateur de réponse', () => {
      expect(component.getEntityLabelKey(node('indicateur', 'etat')))
        .toBe('plans.mindmap.entities.indicateur');
      expect(component.getEntityLabelKey(node('indicateur', 'reponse')))
        .toBe('plans.mindmap.entities.indicateur_reponse');
    });

    it('retourne une chaîne vide pour un nœud absent', () => {
      expect(component.getEntityLabelKey(null)).toBe('');
    });
  });

  describe('palette par colonne (item 3)', () => {
    const cases: [string, 'etat' | 'reponse' | undefined, string, string][] = [
      ['enjeu', undefined, '#025359', '#ffffff'],
      ['etat_enjeu', undefined, '#C0E3CF', '#025359'],
      ['olt', undefined, '#F5B399', '#025359'],
      ['niveau_exigence', undefined, '#F5B399', '#025359'],
      ['indicateur', 'etat', '#F8CAB8', '#025359'],
      ['metrique', 'etat', '#F8CAB8', '#025359'],
      ['facteur', undefined, '#C0E3CF', '#025359'],
      ['pression', undefined, '#C0E3CF', '#025359'],
      ['oo', undefined, '#FEC180', '#025359'],
      ['resultat_attendu', undefined, '#FEC180', '#025359'],
      ['indicateur', 'reponse', '#FED4A6', '#025359'],
      ['metrique', 'reponse', '#FED4A6', '#025359'],
      ['operation', undefined, '#B74D5D', '#ffffff'],
    ];

    it.each(cases)('%s (%s) → fond %s / texte %s', (type, branche, bg, fg) => {
      const n = node(type, branche);
      expect(component.getEntityColor(n)).toBe(bg);
      expect(component.getTextColor(n)).toBe(fg);
    });

    it('retombe sur un calcul de luminance hors tableau principal', () => {
      // mesure = #746F6E (foncé) → texte blanc, aucune couleur imposée.
      expect(component.getTextColor(node('mesure'))).toBe('#ffffff');
    });
  });

  describe('alignement (item 2)', () => {
    it('fait occuper deux colonnes à l\'état actuel', () => {
      expect(component.getSpan(node('etat_enjeu'))).toBe(2);
    });

    it('laisse une seule colonne aux autres types', () => {
      for (const t of ['enjeu', 'facteur', 'pression', 'olt', 'indicateur', 'operation']) {
        expect(component.getSpan(node(t))).toBe(1);
      }
    });

    it('aligne la colonne Action des deux branches d\'un enjeu', () => {
      // Branche état : enjeu → état actuel (2 col.) → OLT → NE → ind. → métrique → action
      // Branche réponse : enjeu → facteur → pression → OO → RA → ind. → métrique → action
      const chain = (types: [string, ('etat' | 'reponse')?][]): MindmapNode => {
        let leaf: MindmapNode | undefined;
        for (let i = types.length - 1; i >= 0; i--) {
          const [t, b] = types[i];
          const n = node(t, b);
          if (leaf) n.children = [leaf];
          leaf = n;
        }
        return leaf!;
      };

      const brancheEtat = chain([
        ['etat_enjeu'], ['olt'], ['niveau_exigence'],
        ['indicateur', 'etat'], ['metrique', 'etat'], ['operation'],
      ]);
      const brancheReponse = chain([
        ['facteur'], ['pression'], ['oo'], ['resultat_attendu'],
        ['indicateur', 'reponse'], ['metrique', 'reponse'], ['operation'],
      ]);

      const columns = (n: MindmapNode) => component['subtreeColumns'](n);
      expect(columns(brancheEtat)).toBe(7);
      expect(columns(brancheReponse)).toBe(7);
    });
  });

  describe('légende (item 4)', () => {
    it('n\'expose plus de légende', () => {
      expect((component as unknown as Record<string, unknown>)['legendItems']).toBeUndefined();
    });
  });
});
