import { ComponentFixture, TestBed } from '@angular/core/testing';
import { StepperComponent, StepperStep } from './stepper.component';

/**
 * Le composant étapes (Figma « 🔢 Composant étapes », node 4487:31377) n'a
 * qu'UNE seule « étape actuelle » à la fois. Deux conventions d'`id` coexistent
 * chez les appelants (0-based pour l'import en masse, 1-based dans la doc du
 * composant) : les deux doivent donner le même résultat.
 */
describe('StepperComponent', () => {
  let component: StepperComponent;
  let fixture: ComponentFixture<StepperComponent>;

  const zeroBased: StepperStep[] = [
    { id: 0, label: 'Fichier' },
    { id: 1, label: 'Correspondance' },
    { id: 2, label: 'Vérification' },
    { id: 3, label: 'Résultats' },
  ];

  const oneBased: StepperStep[] = [
    { id: 1, label: 'Fichier' },
    { id: 2, label: 'Correspondance' },
    { id: 3, label: 'Vérification' },
    { id: 4, label: 'Résultats' },
  ];

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [StepperComponent] }).compileComponents();
    fixture = TestBed.createComponent(StepperComponent);
    component = fixture.componentInstance;
  });

  function currentLabels(): string[] {
    return Array.from(
      fixture.nativeElement.querySelectorAll('.app-stepper__step--current .app-stepper__label'),
    ).map((el) => (el as HTMLElement).textContent!.trim());
  }

  describe('étape actuelle', () => {
    // Régression : `id === currentStep || index + 1 === currentStep` marquait
    // Fichier (index 0 → 0+1=1) ET Correspondance (id 1) comme courantes.
    it('ne marque qu\'une seule étape courante avec des id 0-based', () => {
      component.steps = zeroBased;
      component.currentStep = 1;
      fixture.detectChanges();
      expect(currentLabels()).toEqual(['Correspondance']);
    });

    it('ne marque qu\'une seule étape courante avec des id 1-based', () => {
      component.steps = oneBased;
      component.currentStep = 3;
      fixture.detectChanges();
      expect(currentLabels()).toEqual(['Vérification']);
    });

    it('gère la première et la dernière étape (id 0-based)', () => {
      component.steps = zeroBased;
      component.currentStep = 0;
      fixture.detectChanges();
      expect(currentLabels()).toEqual(['Fichier']);

      component.currentStep = 3;
      fixture.detectChanges();
      expect(currentLabels()).toEqual(['Résultats']);
    });

    it('résout un currentStep donné comme index 1-based quand les id sont des chaînes', () => {
      component.steps = [
        { id: 'file', label: 'Fichier' },
        { id: 'map', label: 'Correspondance' },
      ];
      component.currentStep = 2;
      fixture.detectChanges();
      expect(currentLabels()).toEqual(['Correspondance']);
    });
  });

  describe('étapes passées', () => {
    it('affiche une coche sur les étapes marquées complétées', () => {
      component.steps = [
        { id: 0, label: 'Fichier', completed: true },
        { id: 1, label: 'Correspondance' },
      ];
      component.currentStep = 1;
      fixture.detectChanges();

      const completed = fixture.nativeElement.querySelectorAll('.app-stepper__step--completed');
      expect(completed.length).toBe(1);
      expect(completed[0].querySelector('i.fi-rr-check')).toBeTruthy();
    });

    it('déduit les étapes passées de l\'étape courante si `completed` est absent', () => {
      component.steps = zeroBased;
      component.currentStep = 2;
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelectorAll('.app-stepper__step--completed').length).toBe(2);
    });

    it('trace en primary le trait qui suit une étape passée', () => {
      component.steps = zeroBased;
      component.currentStep = 1;
      fixture.detectChanges();
      const lines = fixture.nativeElement.querySelectorAll('.app-stepper__line');
      // 4 étapes → 3 traits ; seul celui après l'étape 1 (passée) est « done »
      expect(lines.length).toBe(3);
      expect(lines[0].classList).toContain('app-stepper__line--done');
      expect(lines[1].classList).not.toContain('app-stepper__line--done');
    });
  });

  describe('navigation arrière', () => {
    it('émet stepClick sur une étape passée', () => {
      component.steps = zeroBased;
      component.currentStep = 2;
      const spy = jest.fn();
      component.stepClick.subscribe(spy);

      component.onClick(zeroBased[0], 0);
      expect(spy).toHaveBeenCalledWith(zeroBased[0]);
    });

    it('n\'émet pas sur l\'étape courante ni sur une étape à venir', () => {
      component.steps = zeroBased;
      component.currentStep = 1;
      const spy = jest.fn();
      component.stepClick.subscribe(spy);

      component.onClick(zeroBased[1], 1); // courante
      component.onClick(zeroBased[3], 3); // à venir
      expect(spy).not.toHaveBeenCalled();
    });

    it('n\'émet pas quand allowGoBack est désactivé', () => {
      component.steps = zeroBased;
      component.currentStep = 2;
      component.allowGoBack = false;
      const spy = jest.fn();
      component.stepClick.subscribe(spy);

      component.onClick(zeroBased[0], 0);
      expect(spy).not.toHaveBeenCalled();
    });
  });
});
