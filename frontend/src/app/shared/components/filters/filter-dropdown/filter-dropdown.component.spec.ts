import { Component, viewChild } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateModule } from '@ngx-translate/core';
import { FilterDropdownComponent } from './filter-dropdown.component';
import { FilterPanelDirective } from '../filter-panel.directive';

/** Hôte de test : reproduit l'usage réel (corps projeté via `ng-template appFilterPanel`). */
@Component({
  standalone: true,
  imports: [FilterDropdownComponent, FilterPanelDirective],
  template: `
    <app-filter-dropdown
      label="Enjeu"
      testId="filter-enjeu"
      [variant]="variant"
      [activeCount]="activeCount"
      [disabled]="disabled">
      <ng-template appFilterPanel>
        <button class="panel-content" type="button">contenu</button>
      </ng-template>
    </app-filter-dropdown>
  `,
})
class HostComponent {
  readonly dropdown = viewChild.required(FilterDropdownComponent);
  variant: 'field' | 'inline' = 'inline';
  activeCount = 0;
  disabled = false;
}

describe('FilterDropdownComponent', () => {
  let fixture: ComponentFixture<HostComponent>;
  let host: HostComponent;

  const trigger = () =>
    fixture.nativeElement.querySelector('.filter-trigger') as HTMLButtonElement;
  /** Le panneau est rendu dans le conteneur d'overlay du CDK, hors de l'élément hôte. */
  const panel = () => document.querySelector('.filter-panel') as HTMLElement | null;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent, TranslateModule.forRoot()],
    }).compileComponents();

    fixture = TestBed.createComponent(HostComponent);
    host = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    host.dropdown().close();
    fixture.detectChanges();
  });

  it('démarre fermé, sans panneau dans le DOM', () => {
    expect(host.dropdown().open()).toBe(false);
    expect(panel()).toBeNull();
    expect(trigger().getAttribute('aria-expanded')).toBe('false');
  });

  it('ouvre au clic et projette le corps fourni', () => {
    trigger().click();
    fixture.detectChanges();

    expect(host.dropdown().open()).toBe(true);
    expect(panel()).not.toBeNull();
    expect(panel()!.querySelector('.panel-content')).not.toBeNull();
  });

  it('referme au second clic', () => {
    trigger().click();
    fixture.detectChanges();
    trigger().click();
    fixture.detectChanges();

    expect(host.dropdown().open()).toBe(false);
    expect(panel()).toBeNull();
  });

  it('câble aria-expanded et aria-controls', () => {
    trigger().click();
    fixture.detectChanges();

    expect(trigger().getAttribute('aria-expanded')).toBe('true');
    expect(trigger().getAttribute('aria-controls')).toBe(host.dropdown().panelId);
    expect(panel()!.id).toBe(host.dropdown().panelId);
    expect(trigger().getAttribute('aria-haspopup')).toBe('listbox');
  });

  it('ouvre à la flèche bas depuis le déclencheur', () => {
    trigger().dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
    fixture.detectChanges();

    expect(host.dropdown().open()).toBe(true);
  });

  it('Échap ferme et rend le focus au déclencheur', () => {
    trigger().click();
    fixture.detectChanges();

    panel()!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    fixture.detectChanges();

    expect(host.dropdown().open()).toBe(false);
    expect(document.activeElement).toBe(trigger());
  });

  it('ferme au clic sur le backdrop', () => {
    trigger().click();
    fixture.detectChanges();

    const backdrop = document.querySelector('.cdk-overlay-backdrop') as HTMLElement;
    expect(backdrop).not.toBeNull();
    backdrop.click();
    fixture.detectChanges();

    expect(host.dropdown().open()).toBe(false);
  });

  it('un clic DANS le panneau ne le referme pas (sans stopPropagation)', () => {
    // Régression de l'ancien `mat-menu`, qui fermait à chaque activation d'item et
    // imposait un `stopPropagation()` sur chaque ligne.
    trigger().click();
    fixture.detectChanges();

    (panel()!.querySelector('.panel-content') as HTMLElement).click();
    fixture.detectChanges();

    expect(host.dropdown().open()).toBe(true);
  });

  it('n’ouvre pas quand désactivé', () => {
    host.disabled = true;
    fixture.detectChanges();

    trigger().click();
    fixture.detectChanges();

    expect(host.dropdown().open()).toBe(false);
    expect(trigger().disabled).toBe(true);
  });

  describe('pastille compteur', () => {
    it('est absente à zéro', () => {
      expect(fixture.nativeElement.querySelector('.filter-trigger__badge')).toBeNull();
    });

    it('affiche le nombre de valeurs actives', () => {
      host.activeCount = 2;
      fixture.detectChanges();

      expect(
        fixture.nativeElement.querySelector('.filter-trigger__badge').textContent.trim(),
      ).toBe('2');
    });
  });

  describe('variante field', () => {
    beforeEach(() => {
      host.variant = 'field';
      fixture.detectChanges();
    });

    it('rend une zone de texte plutôt que le libellé et la pastille', () => {
      expect(host.dropdown().variant()).toBe('field');
      expect(trigger().querySelector('.filter-trigger__text')).not.toBeNull();
      expect(trigger().querySelector('.filter-trigger__label')).toBeNull();
    });

    it('expose le libellé en aria-label', () => {
      expect(trigger().getAttribute('aria-label')).toBe('Enjeu');
    });
  });

  it('expose des data-testid stables pour l’E2E', () => {
    expect(trigger().getAttribute('data-testid')).toBe('filter-enjeu');

    trigger().click();
    fixture.detectChanges();

    expect(panel()!.getAttribute('data-testid')).toBe('filter-enjeu-panel');
  });
});
