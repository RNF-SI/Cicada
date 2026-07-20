import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateModule } from '@ngx-translate/core';
import { FilterOptionListComponent } from './filter-option-list.component';
import { FilterOption } from '../filter.types';

describe('FilterOptionListComponent', () => {
  let fixture: ComponentFixture<FilterOptionListComponent<string>>;
  let component: FilterOptionListComponent<string>;

  const OPTIONS: FilterOption<string>[] = [
    { value: 'pressions', label: 'Pressions' },
    { value: 'facteurs', label: "Facteurs d'influence" },
    { value: 'objectifs', label: 'Objectifs' },
    { value: 'categorie', label: "Catégorie d'action" },
  ];

  const rows = () =>
    Array.from(fixture.nativeElement.querySelectorAll('.option-row')) as HTMLButtonElement[];
  const labels = () => rows().map((r) => r.textContent?.trim());
  const searchInput = () =>
    fixture.nativeElement.querySelector('.option-search__input') as HTMLInputElement;

  function type(text: string): void {
    const input = searchInput();
    input.value = text;
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FilterOptionListComponent, TranslateModule.forRoot()],
    }).compileComponents();

    fixture = TestBed.createComponent<FilterOptionListComponent<string>>(FilterOptionListComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('options', OPTIONS);
    fixture.detectChanges();
  });

  it('rend une ligne par option', () => {
    expect(rows().length).toBe(4);
  });

  it('marque les options sélectionnées via aria-selected', () => {
    fixture.componentRef.setInput('selected', ['objectifs']);
    fixture.detectChanges();

    expect(rows()[2].getAttribute('aria-selected')).toBe('true');
    expect(rows()[0].getAttribute('aria-selected')).toBe('false');
  });

  describe('multi-sélection', () => {
    it('ajoute puis retire une valeur au clic', () => {
      rows()[0].click();
      fixture.detectChanges();
      expect(component.selected()).toEqual(['pressions']);

      rows()[0].click();
      fixture.detectChanges();
      expect(component.selected()).toEqual([]);
    });

    it('cumule plusieurs valeurs', () => {
      rows()[0].click();
      fixture.detectChanges();
      rows()[2].click();
      fixture.detectChanges();

      expect(component.selected()).toEqual(['pressions', 'objectifs']);
    });
  });

  describe('mono-sélection', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('multiple', false);
      fixture.detectChanges();
    });

    it('ne rend aucune case à cocher', () => {
      expect(fixture.nativeElement.querySelector('app-checkbox')).toBeNull();
    });

    it('remplace la sélection au lieu de la cumuler', () => {
      rows()[0].click();
      fixture.detectChanges();
      rows()[2].click();
      fixture.detectChanges();

      expect(component.selected()).toEqual(['objectifs']);
    });

    it('déclare la listbox non multi-sélectionnable', () => {
      const list = fixture.nativeElement.querySelector('.option-list');
      expect(list.getAttribute('aria-multiselectable')).toBe('false');
    });
  });

  describe('recherche', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('searchable', true);
      fixture.detectChanges();
    });

    it('restreint la liste', () => {
      type('objec');
      expect(labels()).toEqual(['Objectifs']);
    });

    it('ignore accents et casse', () => {
      type('CATEGORIE');
      expect(labels()).toEqual(["Catégorie d'action"]);
    });

    it('met la portion trouvée en gras', () => {
      type('press');
      const strong = rows()[0].querySelector('strong');
      expect(strong?.textContent).toBe('Press');
    });

    it('affiche un état vide sans correspondance', () => {
      type('zzzz');
      expect(rows().length).toBe(0);
      expect(fixture.nativeElement.querySelector('.option-empty')).not.toBeNull();
    });

    it('efface la recherche via le bouton dédié', () => {
      type('objec');
      fixture.nativeElement.querySelector('.option-search__clear').click();
      fixture.detectChanges();

      expect(searchInput().value).toBe('');
      expect(rows().length).toBe(4);
    });
  });

  describe('case maître', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('masterLabel', 'Toutes les données');
      fixture.detectChanges();
    });

    const master = () =>
      fixture.nativeElement.querySelector('.option-master input') as HTMLInputElement;

    it('est décochée quand rien n’est sélectionné', () => {
      expect(master().checked).toBe(false);
      expect(master().indeterminate).toBe(false);
    });

    it('est indéterminée sur sélection partielle', () => {
      fixture.componentRef.setInput('selected', ['pressions']);
      fixture.detectChanges();

      expect(master().indeterminate).toBe(true);
      expect(master().checked).toBe(false);
    });

    it('est cochée quand tout est sélectionné', () => {
      fixture.componentRef.setInput('selected', OPTIONS.map((o) => o.value));
      fixture.detectChanges();

      expect(master().checked).toBe(true);
      expect(master().indeterminate).toBe(false);
    });

    it('sélectionne tout depuis un état partiel', () => {
      fixture.componentRef.setInput('selected', ['pressions']);
      fixture.detectChanges();

      master().click();
      fixture.detectChanges();

      expect(component.selected()).toEqual(OPTIONS.map((o) => o.value));
    });

    it('vide la sélection depuis un état complet', () => {
      fixture.componentRef.setInput('selected', OPTIONS.map((o) => o.value));
      fixture.detectChanges();

      master().click();
      fixture.detectChanges();

      expect(component.selected()).toEqual([]);
    });
  });

  describe('« Voir plus »', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('maxVisible', 2);
      fixture.detectChanges();
    });

    it('tronque la liste', () => {
      expect(rows().length).toBe(2);
      expect(fixture.nativeElement.querySelector('.option-more')).not.toBeNull();
    });

    it('révèle le reste au clic', () => {
      fixture.nativeElement.querySelector('.option-more').click();
      fixture.detectChanges();

      expect(rows().length).toBe(4);
      expect(fixture.nativeElement.querySelector('.option-more')).toBeNull();
    });
  });

  it('n’émet rien pour une option désactivée', () => {
    fixture.componentRef.setInput('options', [{ value: 'x', label: 'X', disabled: true }]);
    fixture.detectChanges();

    expect(rows()[0].disabled).toBe(true);
    expect(component.selected()).toEqual([]);
  });

  it('propage les data-testid des options', () => {
    fixture.componentRef.setInput('testId', 'filter-type');
    fixture.detectChanges();

    expect(rows()[0].getAttribute('data-testid')).toBe('filter-type-option-pressions');
  });
});
