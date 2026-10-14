import { Component, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { segmenterSurTerme } from '../../core/models/exploration.model';
import { CLASSE_SURLIGNAGE, SurlignerDirective } from './surligner.directive';

@Component({
  standalone: true,
  imports: [SurlignerDirective],
  template: `
    <div [appSurligner]="termes()">
      <h1>Préservation des limicoles nicheurs</h1>
      <p>Les <b>Limicoles</b> hivernants, et les anatidés.</p>
      <input value="limicole" />
      <span data-sans-surlignage>limicole intact</span>
      @if (ajout()) {
        <em>Nouveau limicole rendu plus tard</em>
      }
    </div>
  `,
})
class HoteComponent {
  termes = signal('limicole');
  ajout = signal(false);
}

/** Attend que la directive ait fait sa passe (planifiée au prochain repaint). */
const prochainePasse = () => new Promise<void>((resolve) => setTimeout(resolve, 30));

describe('SurlignerDirective (#681)', () => {
  let fixture: ComponentFixture<HoteComponent>;
  let hote: HTMLElement;

  const marques = () =>
    Array.from(hote.querySelectorAll<HTMLElement>(`mark.${CLASSE_SURLIGNAGE}`)).map(
      (m) => m.textContent,
    );

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [HoteComponent] }).compileComponents();
    fixture = TestBed.createComponent(HoteComponent);
    hote = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
    await prochainePasse();
  });

  it('enveloppe chaque mot trouvé dans un <mark>, mot entier et sans tenir compte de la casse', () => {
    expect(marques()).toEqual(['limicoles', 'Limicoles']);
    // Le texte rendu reste identique : seul le balisage change.
    expect(hote.querySelector('h1')?.textContent).toBe('Préservation des limicoles nicheurs');
  });

  it('laisse intacts les champs de saisie et les zones exclues', () => {
    expect(hote.querySelector('span[data-sans-surlignage]')?.innerHTML).toBe('limicole intact');
    expect((hote.querySelector('input') as HTMLInputElement).value).toBe('limicole');
  });

  it('surligne aussi ce qu\'Angular rend plus tard', async () => {
    fixture.componentInstance.ajout.set(true);
    fixture.detectChanges();
    await prochainePasse();
    expect(marques()).toContain('limicole');
    expect(hote.querySelector('em')?.textContent).toBe('Nouveau limicole rendu plus tard');
  });

  it('retire tout surlignage quand le terme est vidé', async () => {
    fixture.componentInstance.termes.set('');
    fixture.detectChanges();
    await prochainePasse();
    expect(marques()).toEqual([]);
    expect(hote.querySelector('h1')?.innerHTML).toBe('Préservation des limicoles nicheurs');
  });

  it('ne surligne jamais deux fois quand le terme change', async () => {
    fixture.componentInstance.termes.set('anatidé');
    fixture.detectChanges();
    await prochainePasse();
    expect(marques()).toEqual(['anatidés']);
  });
});

describe('segmenterSurTerme (#650 / #681)', () => {
  const surlignes = (texte: string, terme: string) =>
    segmenterSurTerme(texte, terme)
      .filter((s) => s.surligne)
      .map((s) => s.texte);

  it('surligne le mot entier à partir du préfixe tapé', () => {
    expect(surlignes('Accueil des limicoles nicheurs', 'limicole')).toEqual(['limicoles']);
  });

  it('ignore les accents et la casse', () => {
    expect(surlignes('Forêt de Roselières', 'roseliere foret')).toEqual(['Forêt', 'Roselières']);
  });

  it('ne surligne pas un mot qui contient le terme sans commencer par lui', () => {
    expect(surlignes('et de leur faune', 'leur')).toEqual(['leur']);
    expect(surlignes('les fleurs', 'leur')).toEqual([]);
  });

  it('rend le texte intact quand rien ne correspond', () => {
    expect(segmenterSurTerme('Rien ici', 'zoster')).toEqual([{ texte: 'Rien ici', surligne: false }]);
  });
});
