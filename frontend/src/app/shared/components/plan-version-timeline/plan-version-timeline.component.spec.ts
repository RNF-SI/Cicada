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
      'plans.lifecycle.actions.validate': 'Valider le plan',
      'plans.lifecycle.actions.toDraft': 'Remettre en brouillon',
      'plans.lifecycle.actions.createEvaluation': 'Lancer évaluation mi-parcours',
      'plans.lifecycle.actions.archive': 'Archiver',
      'plans.lifecycle.actions.archiveHint': '(rend inactif)',
      'plans.lifecycle.actions.reactivate': 'Réactiver',
      'plans.lifecycle.actions.reactivateHint': '(rend actif)',
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

    it('should have canManage false by default', () => {
      expect(component.canManage).toBe(false);
    });
  });

  // ==================== visibility ====================

  describe('visibility', () => {
    it('should be invisible when chain has 0 items', () => {
      component.chain = [];
      expect(component.visible).toBe(false);
    });

    it('should be invisible when chain has 1 item', () => {
      component.chain = [createChainItem({ is_current: true })];
      expect(component.visible).toBe(false);
    });

    it('should be visible when chain has 2+ items', () => {
      component.chain = [
        createChainItem({ id_pg: 1 }),
        createChainItem({ id_pg: 2, is_current: true }),
      ];
      expect(component.visible).toBe(true);
    });
  });

  // ==================== isEvaluation ====================

  describe('isEvaluation', () => {
    it('should return false when no current item has EVAL_MI_PARCOURS', () => {
      component.chain = [
        createChainItem({ id_pg: 1, is_current: true }),
      ];
      expect(component.isEvaluation).toBe(false);
    });

    it('should return true when current item has EVAL_MI_PARCOURS', () => {
      component.chain = [
        createChainItem({ id_pg: 1 }),
        createChainItem({ id_pg: 2, is_current: true, type_document_mnemonique: 'EVAL_MI_PARCOURS' }),
      ];
      expect(component.isEvaluation).toBe(true);
    });

    it('should return false when non-current item has EVAL_MI_PARCOURS', () => {
      component.chain = [
        createChainItem({ id_pg: 1, type_document_mnemonique: 'EVAL_MI_PARCOURS' }),
        createChainItem({ id_pg: 2, is_current: true }),
      ];
      expect(component.isEvaluation).toBe(false);
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

  // ==================== action buttons ====================

  describe('action buttons', () => {
    beforeEach(() => {
      // Make timeline visible with 2 items
      component.chain = [
        createChainItem({ id_pg: 1 }),
        createChainItem({ id_pg: 2, is_current: true }),
      ];
    });

    it('should show validate button when draft and canManage', () => {
      component.canManage = true;
      component.currentStatus = 'draft';
      fixture.detectChanges();
      const buttons = fixture.nativeElement.querySelectorAll('.timeline-action-btn');
      const texts = Array.from(buttons).map((b: any) => b.textContent);
      expect(texts.some((t: string) => t.includes('Valider le plan'))).toBe(true);
    });

    it('should show toDraft button when valide and canManage', () => {
      component.canManage = true;
      component.currentStatus = 'valide';
      fixture.detectChanges();
      const buttons = fixture.nativeElement.querySelectorAll('.timeline-action-btn');
      const texts = Array.from(buttons).map((b: any) => b.textContent);
      expect(texts.some((t: string) => t.includes('Remettre en brouillon'))).toBe(true);
    });

    it('should show createEvaluation button when valide, not evaluation, and canManage', () => {
      component.canManage = true;
      component.currentStatus = 'valide';
      // No EVAL_MI_PARCOURS on current item
      fixture.detectChanges();
      const buttons = fixture.nativeElement.querySelectorAll('.timeline-action-btn');
      const texts = Array.from(buttons).map((b: any) => b.textContent);
      expect(texts.some((t: string) => t.includes('évaluation mi-parcours'))).toBe(true);
    });

    it('should NOT show createEvaluation when current is evaluation', () => {
      component.canManage = true;
      component.currentStatus = 'valide';
      component.chain = [
        createChainItem({ id_pg: 1 }),
        createChainItem({ id_pg: 2, is_current: true, type_document_mnemonique: 'EVAL_MI_PARCOURS' }),
      ];
      fixture.detectChanges();
      const buttons = fixture.nativeElement.querySelectorAll('.timeline-action-btn');
      const texts = Array.from(buttons).map((b: any) => b.textContent);
      expect(texts.some((t: string) => t.includes('évaluation mi-parcours'))).toBe(false);
    });

    it('should show archive button when valide and canManage', () => {
      component.canManage = true;
      component.currentStatus = 'valide';
      fixture.detectChanges();
      const buttons = fixture.nativeElement.querySelectorAll('.timeline-action-btn');
      const texts = Array.from(buttons).map((b: any) => b.textContent);
      expect(texts.some((t: string) => t.includes('Archiver'))).toBe(true);
    });

    it('should show reactivate button when archive and canManage', () => {
      component.canManage = true;
      component.currentStatus = 'archive';
      fixture.detectChanges();
      const buttons = fixture.nativeElement.querySelectorAll('.timeline-action-btn');
      const texts = Array.from(buttons).map((b: any) => b.textContent);
      expect(texts.some((t: string) => t.includes('Réactiver'))).toBe(true);
    });

    it('should show no action buttons when canManage is false', () => {
      component.canManage = false;
      component.currentStatus = 'valide';
      fixture.detectChanges();
      const actions = fixture.nativeElement.querySelector('.timeline-actions');
      expect(actions).toBeNull();
    });
  });

  // ==================== event emission ====================

  describe('event emission', () => {
    it('should emit "valide" on onValidate', () => {
      const spy = jest.spyOn(component.statusChange, 'emit');
      component.onValidate();
      expect(spy).toHaveBeenCalledWith('valide');
    });

    it('should emit "archive" on onArchive', () => {
      const spy = jest.spyOn(component.statusChange, 'emit');
      component.onArchive();
      expect(spy).toHaveBeenCalledWith('archive');
    });

    it('should emit "draft" on onToDraft', () => {
      const spy = jest.spyOn(component.statusChange, 'emit');
      component.onToDraft();
      expect(spy).toHaveBeenCalledWith('draft');
    });

    it('should emit "valide" on onReactivate', () => {
      const spy = jest.spyOn(component.statusChange, 'emit');
      component.onReactivate();
      expect(spy).toHaveBeenCalledWith('valide');
    });

    it('should emit createEvaluation on onCreateEvaluation', () => {
      const spy = jest.spyOn(component.createEvaluation, 'emit');
      component.onCreateEvaluation();
      expect(spy).toHaveBeenCalled();
    });
  });

  // ==================== DOM rendering ====================

  describe('DOM rendering', () => {
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
  });
});
