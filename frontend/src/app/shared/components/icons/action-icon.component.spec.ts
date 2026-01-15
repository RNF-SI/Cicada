import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActionIconComponent, ActionStatus } from './action-icon.component';

describe('ActionIconComponent', () => {
  let component: ActionIconComponent;
  let fixture: ComponentFixture<ActionIconComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ActionIconComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ActionIconComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should have planned status by default', () => {
      expect(component.status).toBe('planned');
    });

    it('should have size 28 by default', () => {
      expect(component.size).toBe(28);
    });
  });

  describe('getLabel', () => {
    it('should return correct label for planned', () => {
      component.status = 'planned';
      expect(component.getLabel()).toBe('Action prévue');
    });

    it('should return correct label for planned-realized', () => {
      component.status = 'planned-realized';
      expect(component.getLabel()).toBe('Action prévue et réalisée');
    });

    it('should return correct label for planned-partial', () => {
      component.status = 'planned-partial';
      expect(component.getLabel()).toBe('Action prévue et partiellement réalisée');
    });

    it('should return correct label for realized-unplanned', () => {
      component.status = 'realized-unplanned';
      expect(component.getLabel()).toBe('Action réalisée non prévue');
    });

    it('should return correct label for partial-unplanned', () => {
      component.status = 'partial-unplanned';
      expect(component.getLabel()).toBe('Action partiellement réalisée non prévue');
    });
  });

  describe('input changes', () => {
    it('should accept status input', () => {
      component.status = 'planned-realized';
      fixture.detectChanges();
      expect(component.status).toBe('planned-realized');
    });

    it('should accept size input', () => {
      component.size = 48;
      fixture.detectChanges();
      expect(component.size).toBe(48);
    });
  });
});
