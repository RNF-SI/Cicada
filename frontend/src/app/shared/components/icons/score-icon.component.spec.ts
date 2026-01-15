import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ScoreIconComponent, ScoreLevel } from './score-icon.component';

describe('ScoreIconComponent', () => {
  let component: ScoreIconComponent;
  let fixture: ComponentFixture<ScoreIconComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScoreIconComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ScoreIconComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should have neutral level by default', () => {
      expect(component.level).toBe('neutral');
    });

    it('should have size 20 by default', () => {
      expect(component.size).toBe(20);
    });
  });

  describe('getBackgroundColor', () => {
    it('should return correct color for very-bad', () => {
      component.level = 'very-bad';
      expect(component.getBackgroundColor()).toBe('#FF7579');
    });

    it('should return correct color for bad', () => {
      component.level = 'bad';
      expect(component.getBackgroundColor()).toBe('#FA9965');
    });

    it('should return correct color for neutral', () => {
      component.level = 'neutral';
      expect(component.getBackgroundColor()).toBe('#F7D35C');
    });

    it('should return correct color for good', () => {
      component.level = 'good';
      expect(component.getBackgroundColor()).toBe('#82DB8A');
    });

    it('should return correct color for very-good', () => {
      component.level = 'very-good';
      expect(component.getBackgroundColor()).toBe('#81C9D8');
    });

    it('should return correct color for no-data', () => {
      component.level = 'no-data';
      expect(component.getBackgroundColor()).toBe('#DADADA');
    });
  });

  describe('getElementColor', () => {
    it('should return dark color for neutral level', () => {
      component.level = 'neutral';
      expect(component.getElementColor()).toBe('#333333');
    });

    it('should return dark color for no-data level', () => {
      component.level = 'no-data';
      expect(component.getElementColor()).toBe('#333333');
    });

    it('should return white for very-bad level', () => {
      component.level = 'very-bad';
      expect(component.getElementColor()).toBe('#FFFFFF');
    });

    it('should return white for bad level', () => {
      component.level = 'bad';
      expect(component.getElementColor()).toBe('#FFFFFF');
    });

    it('should return white for good level', () => {
      component.level = 'good';
      expect(component.getElementColor()).toBe('#FFFFFF');
    });

    it('should return white for very-good level', () => {
      component.level = 'very-good';
      expect(component.getElementColor()).toBe('#FFFFFF');
    });
  });

  describe('getLabel', () => {
    it('should return correct label for very-bad', () => {
      component.level = 'very-bad';
      expect(component.getLabel()).toBe('Très mauvais');
    });

    it('should return correct label for bad', () => {
      component.level = 'bad';
      expect(component.getLabel()).toBe('Mauvais');
    });

    it('should return correct label for neutral', () => {
      component.level = 'neutral';
      expect(component.getLabel()).toBe('Moyen');
    });

    it('should return correct label for good', () => {
      component.level = 'good';
      expect(component.getLabel()).toBe('Bon');
    });

    it('should return correct label for very-good', () => {
      component.level = 'very-good';
      expect(component.getLabel()).toBe('Très bon');
    });

    it('should return correct label for no-data', () => {
      component.level = 'no-data';
      expect(component.getLabel()).toBe('Sans donnée');
    });
  });

  describe('input changes', () => {
    it('should accept level input', () => {
      component.level = 'good';
      fixture.detectChanges();
      expect(component.level).toBe('good');
    });

    it('should accept size input', () => {
      component.size = 32;
      fixture.detectChanges();
      expect(component.size).toBe(32);
    });
  });
});
