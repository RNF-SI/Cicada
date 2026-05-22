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

  // ==================== getNodeIcon ====================

  describe('getNodeIcon', () => {
    it('should return time-forward icon for EVAL_MI_PARCOURS', () => {
      const item = createChainItem({ type_document_mnemonique: 'EVAL_MI_PARCOURS' });
      expect(component.getNodeIcon(item)).toBe('fi-rr-time-forward');
    });

    it('should return refresh icon for PLAN_REVISE', () => {
      const item = createChainItem({ type_document_mnemonique: 'PLAN_REVISE' });
      expect(component.getNodeIcon(item)).toBe('fi-rr-refresh');
    });

    it('should return document icon for default/PLAN_INITIAL', () => {
      const item = createChainItem({ type_document_mnemonique: 'PLAN_INITIAL' });
      expect(component.getNodeIcon(item)).toBe('fi-rr-document');
    });
  });

  // ==================== getStatusClass ====================

  describe('getStatusClass', () => {
    it('should return status-warning for draft', () => {
      const item = createChainItem({ statut: 'draft' });
      expect(component.getStatusClass(item)).toBe('status-warning');
    });

    it('should return status-success for valide', () => {
      const item = createChainItem({ statut: 'valide' });
      expect(component.getStatusClass(item)).toBe('status-success');
    });

    it('should return status-neutre for archive', () => {
      const item = createChainItem({ statut: 'archive' });
      expect(component.getStatusClass(item)).toBe('status-neutre');
    });

    it('should return empty string for unknown status', () => {
      const item = createChainItem({ statut: 'unknown' as PlanStatut });
      expect(component.getStatusClass(item)).toBe('');
    });
  });

  // ==================== DOM rendering ====================

  describe('DOM rendering', () => {
    it('should always render the timeline (read-only)', () => {
      component.chain = [
        createChainItem({ id_pg: 1, is_current: true }),
      ];
      fixture.detectChanges();
      const timeline = fixture.nativeElement.querySelector('.version-timeline');
      expect(timeline).toBeTruthy();
    });

    it('should display current badge for current item', () => {
      component.chain = [
        createChainItem({ id_pg: 1, version: '1' }),
        createChainItem({ id_pg: 2, version: '2', is_current: true }),
      ];
      fixture.detectChanges();
      const badge = fixture.nativeElement.querySelector('.current-badge');
      expect(badge).toBeTruthy();
      expect(badge.textContent).toContain('actuel');
    });

    it('should render correct number of timeline nodes', () => {
      component.chain = [
        createChainItem({ id_pg: 1 }),
        createChainItem({ id_pg: 2 }),
        createChainItem({ id_pg: 3, is_current: true }),
      ];
      fixture.detectChanges();
      const nodes = fixture.nativeElement.querySelectorAll('.timeline-node-row');
      expect(nodes.length).toBe(3);
    });

    it('should not render any action buttons (read-only timeline)', () => {
      component.chain = [
        createChainItem({ id_pg: 1 }),
        createChainItem({ id_pg: 2, is_current: true }),
      ];
      fixture.detectChanges();
      const actions = fixture.nativeElement.querySelector('.timeline-actions');
      expect(actions).toBeNull();
    });
  });

  // ==================== isNextRangDraft (#280) ====================

  describe('isNextRangDraft', () => {
    it('renvoie false pour le plan courant', () => {
      const current = createChainItem({ id_pg: 1, statut: 'valide', rang: 1, is_current: true });
      component.chain = [current];
      expect(component.isNextRangDraft(current)).toBe(false);
    });

    it('renvoie false pour un brouillon de même rang (évaluation mi-parcours)', () => {
      const current = createChainItem({ id_pg: 1, statut: 'valide', rang: 1, is_current: true });
      const evalDraft = createChainItem({ id_pg: 2, statut: 'draft', rang: 1 });
      component.chain = [current, evalDraft];
      expect(component.isNextRangDraft(evalDraft)).toBe(false);
    });

    it('renvoie true pour un brouillon de rang supérieur', () => {
      const current = createChainItem({ id_pg: 1, statut: 'valide', rang: 1, is_current: true });
      const nextRang = createChainItem({ id_pg: 2, statut: 'draft', rang: 2 });
      component.chain = [current, nextRang];
      expect(component.isNextRangDraft(nextRang)).toBe(true);
    });

    it('renvoie false pour un plan validé de rang supérieur (déjà validé, pas brouillon)', () => {
      const current = createChainItem({ id_pg: 1, statut: 'valide', rang: 1, is_current: true });
      const nextRangValide = createChainItem({ id_pg: 2, statut: 'valide', rang: 2 });
      component.chain = [current, nextRangValide];
      expect(component.isNextRangDraft(nextRangValide)).toBe(false);
    });

    it('renvoie false si rang manquant sur l\'élément testé', () => {
      const current = createChainItem({ id_pg: 1, statut: 'valide', rang: 1, is_current: true });
      const unknown = createChainItem({ id_pg: 2, statut: 'draft', rang: undefined });
      component.chain = [current, unknown];
      expect(component.isNextRangDraft(unknown)).toBe(false);
    });

    it('rend un header cliquable pour le rang suivant (pas de timeline-node-row)', () => {
      component.chain = [
        createChainItem({ id_pg: 1, statut: 'valide', rang: 1, is_current: true }),
        createChainItem({ id_pg: 2, statut: 'draft', rang: 2, slug: 'rang-2-draft' }),
      ];
      fixture.detectChanges();
      // Le rang courant montre 1 timeline-node-row, le rang suivant montre un header link
      const nodes = fixture.nativeElement.querySelectorAll('.timeline-node-row');
      expect(nodes.length).toBe(1);
      const nextRangLink = fixture.nativeElement.querySelector('.rang-next .rang-header-link');
      expect(nextRangLink).toBeTruthy();
    });
  });

  // ==================== rangGroups (sections par rang) ====================

  describe('rangGroups', () => {
    it('regroupe les items par rang et marque previous/current/next', () => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1, statut: 'archive' }),
        createChainItem({ id_pg: 2, rang: 2, statut: 'valide', is_current: true }),
        createChainItem({ id_pg: 3, rang: 3, statut: 'draft' }),
      ];
      fixture.detectChanges();
      const groups = component.rangGroups();
      expect(groups.length).toBe(3);
      expect(groups[0].position).toBe('previous');
      expect(groups[1].position).toBe('current');
      expect(groups[2].position).toBe('next');
    });

    it('choisit la dernière version validée comme cible de navigation', () => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1, statut: 'archive', version: '1' }),
        createChainItem({ id_pg: 2, rang: 1, statut: 'archive', version: '2' }),
        createChainItem({ id_pg: 3, rang: 2, statut: 'valide', is_current: true }),
      ];
      fixture.detectChanges();
      const previous = component.rangGroups().find(g => g.position === 'previous');
      expect(previous?.navigationTarget?.id_pg).toBe(2);  // v2 archive
    });

    it('prefere valide/modifie a archive a draft pour la navigation', () => {
      component.chain = [
        createChainItem({ id_pg: 1, rang: 1, statut: 'valide', is_current: true }),
        createChainItem({ id_pg: 2, rang: 2, statut: 'draft', version: '1' }),
        createChainItem({ id_pg: 3, rang: 2, statut: 'archive', version: '2' }),
        createChainItem({ id_pg: 4, rang: 2, statut: 'modifie', version: '3' }),
      ];
      fixture.detectChanges();
      const next = component.rangGroups().find(g => g.position === 'next');
      expect(next?.navigationTarget?.id_pg).toBe(4);  // modifie wins
    });
  });
});
