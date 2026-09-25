import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateModule } from '@ngx-translate/core';

import { PaginationComponent } from './pagination.component';

describe('PaginationComponent', () => {
  let fixture: ComponentFixture<PaginationComponent>;

  const setup = (totalItems: number, currentPage = 1, pageSize = 20) => {
    fixture = TestBed.createComponent(PaginationComponent);
    fixture.componentRef.setInput('totalItems', totalItems);
    fixture.componentRef.setInput('currentPage', currentPage);
    fixture.componentRef.setInput('pageSize', pageSize);
    fixture.detectChanges();
  };

  const el = (): HTMLElement => fixture.nativeElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PaginationComponent, TranslateModule.forRoot()]
    }).compileComponents();
  });

  it('rend les boutons de page avec la classe stylée .page-btn (#659)', () => {
    setup(31);

    const buttons = el().querySelectorAll('button.page-btn');
    // précédent + pages 1 et 2 + suivant
    expect(buttons.length).toBe(4);
    expect(el().querySelector('.page-btn.active')?.textContent?.trim()).toBe('1');
    expect(el().querySelector('.page-btn.active')?.getAttribute('aria-current')).toBe('page');
  });

  it('marque les flèches avec .page-nav et les désactive aux bornes', () => {
    setup(31);

    const navs = el().querySelectorAll<HTMLButtonElement>('button.page-nav');
    expect(navs.length).toBe(2);
    expect(navs[0].disabled).toBe(true);   // page 1 : pas de précédent
    expect(navs[1].disabled).toBe(false);
  });

  // Deux ellipses portent la même valeur (-1) : avec `track p`, Angular levait
  // une erreur de clés dupliquées dès qu'un jeu de pages en affichait deux.
  it('affiche deux ellipses sans erreur de clés dupliquées', () => {
    expect(() => setup(400, 10)).not.toThrow();

    expect(el().querySelectorAll('.page-ellipsis').length).toBe(2);
    // L'ellipsis n'est plus un <button> : rien à cliquer.
    expect(el().querySelectorAll('button.page-ellipsis').length).toBe(0);
  });

  it("n'affiche rien sans élément", () => {
    setup(0);

    expect(el().querySelector('.pagination-container')).toBeNull();
  });
});
