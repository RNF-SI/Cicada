import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateModule } from '@ngx-translate/core';
import { FilterTreeComponent } from './filter-tree.component';
import { FilterTreeNode } from '../filter.types';

describe('FilterTreeComponent', () => {
  let fixture: ComponentFixture<FilterTreeComponent<string>>;
  let component: FilterTreeComponent<string>;

  const NODES: FilterTreeNode<string>[] = [
    {
      value: 'ara',
      label: 'Auvergne-Rhône-Alpes',
      children: [
        { value: 'ain', label: 'Ain' },
        { value: 'allier', label: 'Allier' },
        { value: 'ardeche', label: 'Ardèche' },
      ],
    },
    {
      value: 'bretagne',
      label: 'Bretagne',
      children: [{ value: 'armor', label: "Côtes d'Armor" }],
    },
    { value: 'corse', label: 'Corse' },
  ];

  const rows = () =>
    Array.from(fixture.nativeElement.querySelectorAll('.tree-row__main')) as HTMLButtonElement[];
  const labels = () => rows().map((r) => r.textContent?.trim());
  const items = () =>
    Array.from(fixture.nativeElement.querySelectorAll('.tree-item')) as HTMLElement[];
  const boxes = () =>
    Array.from(fixture.nativeElement.querySelectorAll('.tree-row input')) as HTMLInputElement[];

  function type(text: string): void {
    const input = fixture.nativeElement.querySelector('.tree-search__input') as HTMLInputElement;
    input.value = text;
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FilterTreeComponent, TranslateModule.forRoot()],
    }).compileComponents();

    fixture = TestBed.createComponent<FilterTreeComponent<string>>(FilterTreeComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('nodes', NODES);
    fixture.detectChanges();
  });

  it('n’affiche que les racines tant que rien n’est déplié', () => {
    expect(labels()).toEqual(['Auvergne-Rhône-Alpes', 'Bretagne', 'Corse']);
  });

  describe('expansion', () => {
    it('déplie un nœud au clic sur son chevron', () => {
      (fixture.nativeElement.querySelector('.tree-row__toggle') as HTMLElement).click();
      fixture.detectChanges();

      expect(labels()).toContain('Ain');
      expect(items()[0].getAttribute('aria-expanded')).toBe('true');
    });

    it('n’affiche pas de chevron sur une feuille', () => {
      // « Corse » n'a pas d'enfants : sa ligne ne doit porter aucun bouton d'expansion.
      const corse = items()[2] as HTMLElement;
      expect(corse.querySelector('.tree-row__toggle')).toBeNull();
      expect(corse.getAttribute('aria-expanded')).toBeNull();
    });

    it('déplier ne modifie pas la sélection', () => {
      (fixture.nativeElement.querySelector('.tree-row__toggle') as HTMLElement).click();
      fixture.detectChanges();

      expect(component.selected()).toEqual([]);
    });
  });

  describe('cascade', () => {
    it('cocher un parent sélectionne toute sa descendance', () => {
      rows()[0].click();
      fixture.detectChanges();

      expect(component.selected()).toEqual(['ara', 'ain', 'allier', 'ardeche']);
    });

    it('décocher un parent vide sa descendance', () => {
      rows()[0].click();
      fixture.detectChanges();
      rows()[0].click();
      fixture.detectChanges();

      expect(component.selected()).toEqual([]);
    });

    it('désactivée, ne touche que le nœud cliqué', () => {
      fixture.componentRef.setInput('cascade', false);
      fixture.detectChanges();

      rows()[0].click();
      fixture.detectChanges();

      expect(component.selected()).toEqual(['ara']);
    });
  });

  describe('état des parents', () => {
    it('est indéterminé sur sélection partielle des enfants', () => {
      fixture.componentRef.setInput('selected', ['ain']);
      fixture.detectChanges();

      expect(boxes()[0].indeterminate).toBe(true);
      expect(boxes()[0].checked).toBe(false);
    });

    it('est coché quand toutes les feuilles le sont', () => {
      fixture.componentRef.setInput('selected', ['ain', 'allier', 'ardeche']);
      fixture.detectChanges();

      expect(boxes()[0].checked).toBe(true);
      expect(boxes()[0].indeterminate).toBe(false);
    });
  });

  describe('recherche', () => {
    it('conserve les ancêtres d’une correspondance profonde', () => {
      type('Ain');
      // « Ain » est un enfant : son parent doit rester visible pour le situer.
      expect(labels()).toEqual(['Auvergne-Rhône-Alpes', 'Ain']);
    });

    it('déplie d’office pendant la recherche', () => {
      // Sans cela, une correspondance profonde resterait cachée sous un parent replié.
      type('Armor');
      expect(labels()).toContain("Côtes d'Armor");
    });

    it('ignore les accents', () => {
      type('ardeche');
      expect(labels()).toEqual(['Auvergne-Rhône-Alpes', 'Ardèche']);
    });

    it('met la portion trouvée en gras', () => {
      type('bret');
      expect(rows()[0].querySelector('strong')?.textContent).toBe('Bret');
    });

    it('affiche un état vide sans correspondance', () => {
      type('zzzz');
      expect(rows().length).toBe(0);
      expect(fixture.nativeElement.querySelector('.tree-empty')).not.toBeNull();
    });

    it('restaure l’arbre replié une fois la recherche effacée', () => {
      type('Ain');
      type('');
      expect(labels()).toEqual(['Auvergne-Rhône-Alpes', 'Bretagne', 'Corse']);
    });
  });

  describe('« Voir plus »', () => {
    it('tronque les racines puis les révèle', () => {
      fixture.componentRef.setInput('maxVisible', 2);
      fixture.detectChanges();
      expect(rows().length).toBe(2);

      fixture.nativeElement.querySelector('.tree-more').click();
      fixture.detectChanges();
      expect(rows().length).toBe(3);
    });
  });

  it('expose les rôles ARIA de l’arbre', () => {
    expect(fixture.nativeElement.querySelector('.tree-list').getAttribute('role')).toBe('tree');
    expect(items()[0].getAttribute('role')).toBe('treeitem');
    expect(items()[0].getAttribute('aria-level')).toBe('1');
  });
});
