import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CheckboxComponent } from './checkbox.component';

describe('CheckboxComponent', () => {
  let fixture: ComponentFixture<CheckboxComponent>;
  let component: CheckboxComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CheckboxComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(CheckboxComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  function labelEl(): HTMLLabelElement {
    return fixture.nativeElement.querySelector('label.app-checkbox');
  }
  function inputEl(): HTMLInputElement {
    return fixture.nativeElement.querySelector('input.app-checkbox__input');
  }

  it('émet checkedChange exactement une fois quand on clique le label (pas de double-toggle)', () => {
    const emissions: boolean[] = [];
    component.checkedChange.subscribe((v) => emissions.push(v));

    labelEl().click();

    expect(emissions).toEqual([true]); // un seul toggle false → true
    expect(component.checked).toBe(true);
  });

  it('émet checkedChange exactement une fois quand on clique l\'input', () => {
    const emissions: boolean[] = [];
    component.checkedChange.subscribe((v) => emissions.push(v));

    inputEl().click();

    expect(emissions).toEqual([true]);
    expect(component.checked).toBe(true);
  });

  it('ne bascule pas quand disabled', () => {
    component.disabled = true;
    fixture.detectChanges();
    const emissions: boolean[] = [];
    component.checkedChange.subscribe((v) => emissions.push(v));
    labelEl().click();
    expect(emissions).toEqual([]);
    expect(component.checked).toBe(false);
  });

  // ============================================
  // Extensions #592 (système de filtres unifié)
  // ============================================

  function boxEl(): HTMLElement {
    return fixture.nativeElement.querySelector('.app-checkbox__box');
  }

  describe('état indéterminé', () => {
    beforeEach(() => {
      component.indeterminate = true;
      fixture.detectChanges();
    });

    it('rend un tiret plutôt qu\'une coche', () => {
      expect(boxEl().querySelector('i')?.className).toContain('fi-rr-minus-small');
    });

    it('positionne la PROPRIÉTÉ DOM indeterminate (ce n\'est pas un attribut HTML)', () => {
      expect(inputEl().indeterminate).toBe(true);
      expect(inputEl().hasAttribute('indeterminate')).toBe(false);
    });

    it('expose aria-checked="mixed"', () => {
      expect(inputEl().getAttribute('aria-checked')).toBe('mixed');
    });

    it('coche — et ne décoche pas — au clic, puis lève l\'état indéterminé', () => {
      labelEl().click();
      fixture.detectChanges();

      expect(component.checked).toBe(true);
      expect(component.indeterminate).toBe(false);
      expect(inputEl().indeterminate).toBe(false);
    });

    it('cède le pas à checked quand les deux sont vrais', () => {
      component.checked = true;
      fixture.detectChanges();

      expect(boxEl().querySelector('i')?.className).toContain('fi-rr-check');
      expect(inputEl().indeterminate).toBe(false);
    });
  });

  describe('variantes size / theme', () => {
    it('n\'applique aucune classe de variante par défaut', () => {
      // Garde-fou : les ~60 instances existantes ne doivent pas bouger d'un pixel.
      expect(labelEl().classList.contains('app-checkbox--md')).toBe(false);
      expect(labelEl().classList.contains('app-checkbox--dark')).toBe(false);
    });

    it('applique la classe md quand size="md"', () => {
      component.size = 'md';
      fixture.detectChanges();
      expect(labelEl().classList.contains('app-checkbox--md')).toBe(true);
    });

    it('applique la classe sombre quand theme="dark"', () => {
      component.theme = 'dark';
      fixture.detectChanges();
      expect(labelEl().classList.contains('app-checkbox--dark')).toBe(true);
    });
  });
});
