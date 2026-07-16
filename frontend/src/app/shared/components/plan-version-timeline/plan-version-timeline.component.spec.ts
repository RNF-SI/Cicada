import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import { PlanVersionTimelineComponent } from './plan-version-timeline.component';
import { PlanVersionChainItem, PlanStatut } from '../../../core/models/admin.model';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'plans.lifecycle.timeline.current': 'actuel',
      'plans.lifecycle.timeline.planInitial': 'Plan initial',
      'plans.lifecycle.timeline.rang': 'Rang',
      'plans.lifecycle.timeline.versionsSingular': 'version',
      'plans.lifecycle.timeline.versionsPlural': 'versions',
      'plans.lifecycle.timeline.viewingThisPlan': 'Vous visualisez ce plan',
      'plans.status.draft': 'Brouillon',
      'plans.status.valide': 'Validé',
      'plans.status.archive': 'Archivé',
    });
  }
}

function createChainItem(overrides: Partial<PlanVersionChainItem> = {}): PlanVersionChainItem {
  return {
    id_pg: 1,
    nom: 'Plan Test',
    slug: 'plan-test',
    version: '1',
    statut: 'valide' as PlanStatut,
    annee_debut: 2024,
    annee_fin: 2034,
    type_document: undefined,
    type_document_mnemonique: undefined,
    is_current: false,
    ...overrides,
  };
}

describe('PlanVersionTimelineComponent', () => {
  let component: PlanVersionTimelineComponent;
  let fixture: ComponentFixture<PlanVersionTimelineComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        PlanVersionTimelineComponent,
        NoopAnimationsModule,
        RouterTestingModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          defaultLanguage: 'fr',
        }),
      ],
    }).compileComponents();

    const translateService = TestBed.inject(TranslateService);
    translateService.use('fr');

    fixture = TestBed.createComponent(PlanVersionTimelineComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  // ==================== initialization ====================

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should have empty chain by default', () => {
      expect(component.chain).toEqual([]);
    });
  });

  // ==================== statusTag (couleur + icône Figma) ====================

  describe('statusTag', () => {
    it('mappe draft sur la variante draft avec icône edit', () => {
      expect(component.statusTag(createChainItem({ statut: 'draft' }))).toEqual({
        variant: 'draft',
        icon: 'fi-rr-edit',
      });
    });

    it('mappe valide sur la variante success avec icône check', () => {
      expect(component.statusTag(createChainItem({ statut: 'valide' }))).toEqual({
        variant: 'success',
        icon: 'fi-rr-check',
      });
    });

    it('mappe archive sur la variante muted avec icône box', () => {
      expect(component.statusTag(createChainItem({ statut: 'archive' }))).toEqual({
        variant: 'muted',
        icon: 'fi-rr-box',
      });
    });

    it('retombe sur un tag neutre sans icône pour un statut inconnu', () => {
      const tag = component.statusTag(createChainItem({ statut: 'unknown' as PlanStatut }));
      expect(tag.variant).toBe('neutral');
      expect(tag.icon).toBeUndefined();
    });
  });

  // ==================== rangGroups (sections par rang) ====================

  describe('rangGroups', () => {
    it('regroupe par rang, du plus récent au plus ancien', () => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1, statut: 'archive' }),
        createChainItem({ id_pg: 2, rang: 2, statut: 'valide', is_current: true }),
        createChainItem({ id_pg: 3, rang: 3, statut: 'draft' }),
      ];
      fixture.detectChanges();
      expect(component.rangGroups().map(g => g.rang)).toEqual([3, 2, 1]);
    });

    it('marque le rang qui contient le plan consulté', () => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1, statut: 'archive' }),
        createChainItem({ id_pg: 2, rang: 2, statut: 'valide', is_current: true }),
      ];
      fixture.detectChanges();
      expect(component.rangGroups().find(g => g.hasCurrent)?.rang).toBe(2);
    });

    it('trie les versions d\'un rang de la plus récente à la plus ancienne', () => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1, version: '1' }),
        createChainItem({ id_pg: 3, rang: 1, version: '3', is_current: true }),
        createChainItem({ id_pg: 2, rang: 1, version: '2' }),
      ];
      fixture.detectChanges();
      expect(component.rangGroups()[0].items.map(i => i.version)).toEqual(['3', '2', '1']);
    });
  });

  // ==================== expansion des rangs ====================

  describe('expansion', () => {
    beforeEach(() => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1, statut: 'archive' }),
        createChainItem({ id_pg: 2, rang: 2, statut: 'valide', is_current: true }),
      ];
      fixture.detectChanges();
    });

    it('ouvre par défaut le rang du plan consulté et garde les autres fermés', () => {
      expect(component.isExpanded(2)).toBe(true);
      expect(component.isExpanded(1)).toBe(false);
    });

    it('déplie un autre rang sans refermer celui du plan consulté', () => {
      component.toggleRang(1);
      expect(component.isExpanded(1)).toBe(true);
      expect(component.isExpanded(2)).toBe(true);
    });

    it('replie le rang du plan consulté au clic', () => {
      component.toggleRang(2);
      expect(component.isExpanded(2)).toBe(false);
    });

    it('réinitialise l\'état déplié quand la chaîne change', () => {
      component.toggleRang(1);
      expect(component.isExpanded(1)).toBe(true);

      component.chain = [createChainItem({ id_pg: 9, rang: 5, is_current: true })];
      fixture.detectChanges();
      expect(component.isExpanded(5)).toBe(true);
    });
  });

  // ==================== DOM rendering ====================

  describe('DOM rendering', () => {
    it('should always render the timeline (read-only)', () => {
      component.chain = [createChainItem({ id_pg: 1, is_current: true })];
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('.version-timeline')).toBeTruthy();
    });

    it('affiche une section par rang', () => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1 }),
        createChainItem({ id_pg: 2, rang: 2, is_current: true }),
      ];
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelectorAll('.rang-section').length).toBe(2);
    });

    it('n\'affiche que les versions du rang déplié', () => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1, version: '1' }),
        createChainItem({ id_pg: 2, rang: 2, version: '1', is_current: true }),
        createChainItem({ id_pg: 3, rang: 2, version: '2' }),
      ];
      fixture.detectChanges();
      // Seul le rang 2 (celui du plan consulté) est ouvert → ses 2 versions
      expect(fixture.nativeElement.querySelectorAll('.version-card').length).toBe(2);
    });

    it('indique « Vous visualisez ce plan » sur la version courante et une flèche sur les autres', () => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1, version: '1' }),
        createChainItem({ id_pg: 2, rang: 1, version: '2', is_current: true }),
      ];
      fixture.detectChanges();

      const hints = fixture.nativeElement.querySelectorAll('.version-current-hint');
      expect(hints.length).toBe(1);
      expect(hints[0].textContent).toContain('Vous visualisez ce plan');
      expect(fixture.nativeElement.querySelectorAll('.version-goto').length).toBe(1);
    });

    it('cercle la carte du plan consulté', () => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1, version: '1' }),
        createChainItem({ id_pg: 2, rang: 1, version: '2', is_current: true }),
      ];
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelectorAll('.version-card--current').length).toBe(1);
    });

    it('should not render any action buttons (read-only timeline)', () => {
      component.chain = [
        createChainItem({ id_pg: 1 }),
        createChainItem({ id_pg: 2, is_current: true }),
      ];
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('.timeline-actions')).toBeNull();
    });
  });
});
