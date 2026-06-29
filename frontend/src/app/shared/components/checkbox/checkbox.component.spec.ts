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
});
