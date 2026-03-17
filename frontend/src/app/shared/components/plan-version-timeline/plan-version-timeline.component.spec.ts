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
    version: '1.0',
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
        createChainItem({ id_pg: 1, version: '1.0' }),
        createChainItem({ id_pg: 2, version: '1.1', is_current: true }),
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
});
