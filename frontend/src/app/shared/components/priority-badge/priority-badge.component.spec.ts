import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PriorityBadgeComponent } from './priority-badge.component';

/**
 * Verrouille le format et la palette du kit UI « Priorité d'un enjeu » (#566) :
 * libellé « Priorité » + pastille ronde portant le chiffre, colorée par niveau
 * (1 → rouge, 2 → jaune, 3 → bleu). Le retour de test Sophie portait justement
 * sur ces deux points (ancien pill « Priorité N » en mauvaises couleurs).
 */
describe('PriorityBadgeComponent (#566)', () => {
  let fixture: ComponentFixture<PriorityBadgeComponent>;
  let component: PriorityBadgeComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PriorityBadgeComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(PriorityBadgeComponent);
    component = fixture.componentInstance;
  });

  function render(label: string | null | undefined): HTMLElement {
    component.label = label;
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('affiche le mot « Priorité » et une pastille avec le chiffre', () => {
    const el = render('Priorité 1');
    expect(el.querySelector('.priority-badge__label')?.textContent?.trim()).toBe('Priorité');
    const circle = el.querySelector('.priority-badge__circle');
    expect(circle?.textContent?.trim()).toBe('1');
  });

  it('applique la classe de niveau (couleur) attendue pour 1/2/3', () => {
    expect(render('Priorité 1').querySelector('.priority-badge__circle--1')).toBeTruthy();
    expect(render('Priorité 2').querySelector('.priority-badge__circle--2')).toBeTruthy();
    expect(render('Priorité 3').querySelector('.priority-badge__circle--3')).toBeTruthy();
  });

  it('ne rend rien quand la priorité est absente', () => {
    for (const empty of [null, undefined, '']) {
      const el = render(empty);
      expect(el.querySelector('.priority-badge')).toBeNull();
    }
  });

  it('peut masquer le libellé et ne garder que la pastille', () => {
    component.label = 'Priorité 2';
    component.showLabel = false;
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.priority-badge__label')).toBeNull();
    expect(el.querySelector('.priority-badge__circle')?.textContent?.trim()).toBe('2');
  });
});
