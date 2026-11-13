/**
 * #803 — Un seul suivi par rang : une version dont le suivi se poursuit dans
 * une version plus récente renvoie, depuis chaque page de suivi, vers la même
 * page de la version qui le porte.
 */
import { readFileSync } from 'fs';
import { join } from 'path';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { SuiviPoursuiviBannerComponent } from './suivi-poursuivi-banner.component';

describe('SuiviPoursuiviBannerComponent (#803)', () => {
  let fixture: ComponentFixture<SuiviPoursuiviBannerComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [SuiviPoursuiviBannerComponent, TranslateModule.forRoot()],
      providers: [provideRouter([])],
    });
    fixture = TestBed.createComponent(SuiviPoursuiviBannerComponent);
  });

  it("n'affiche rien quand la version porte son suivi", () => {
    fixture.componentRef.setInput('suite', null);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="suivi-poursuivi"]')).toBeNull();
  });

  it('renvoie vers la même page de la version qui porte le suivi', () => {
    fixture.componentRef.setInput('suite', {
      id_pg: 12, slug: 'pg-v2', nom: 'PG v2', version: '2', statut: 'modifie',
    });
    fixture.componentRef.setInput('page', 'bilan');
    fixture.detectChanges();
    const lien: HTMLAnchorElement = fixture.nativeElement.querySelector(
      '[data-testid="suivi-poursuivi-lien"]');
    expect(lien.getAttribute('href')).toBe('/plans/pg-v2/bilan');
  });
});

describe('Pages de suivi — renvoi vers la version qui porte le suivi (#803)', () => {
  const read = (f: string) => readFileSync(join(__dirname, '..', f), 'utf8');
  const pages: Record<string, string> = {
    'plan-suivi-actions.component': 'suivi-actions',
    'plan-tableau-de-bord.component': 'tableau-de-bord',
    'plan-bilan.component': 'bilan',
    'suivi-saisie/suivi-saisie.component': 'suivi-actions',
    'indicateur-saisie/indicateur-saisie.component': 'tableau-de-bord',
    'planification-annuelle/plan-planification-annuelle.component': 'planification-annuelle',
  };
  for (const [fichier, page] of Object.entries(pages)) {
    it(`${fichier} affiche le bandeau et lit suivi_poursuivi_dans`, () => {
      expect(read(`${fichier}.html`)).toContain(
        `<app-suivi-poursuivi-banner [suite]="suiteSuivi()" page="${page}">`);
      expect(read(`${fichier}.ts`)).toContain('this.suiteSuivi.set(plan.suivi_poursuivi_dans ?? null)');
    });
  }
});
