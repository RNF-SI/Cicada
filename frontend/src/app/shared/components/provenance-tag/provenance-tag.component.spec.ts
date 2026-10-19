/**
 * #692 — Pastille de provenance : la structure d'où vient une donnée explorée.
 */
import { TestBed } from '@angular/core/testing';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { ProvenanceTagComponent } from './provenance-tag.component';

function setup(inputs: Record<string, unknown>) {
  TestBed.configureTestingModule({
    imports: [ProvenanceTagComponent, TranslateModule.forRoot()],
  });
  const translate = TestBed.inject(TranslateService);
  translate.setTranslation('fr', {
    exploration: {
      provenance: {
        identifiant: 'Identifiant : {{id}}',
        publication: 'publié le {{date}}',
      },
    },
  });
  translate.use('fr');
  const fixture = TestBed.createComponent(ProvenanceTagComponent);
  for (const [cle, valeur] of Object.entries(inputs)) {
    fixture.componentRef.setInput(cle, valeur);
  }
  fixture.detectChanges();
  return fixture;
}

describe('ProvenanceTagComponent (#692)', () => {
  it('affiche le nom de la structure', () => {
    const el: HTMLElement = setup({ libelle: 'Réserves Naturelles de France' }).nativeElement;
    expect(el.textContent).toContain('Réserves Naturelles de France');
    expect(el.querySelector('.provenance-tag')).not.toBeNull();
  });

  it('donne au survol l\'identifiant technique et la date de publication', () => {
    const fixture = setup({
      libelle: 'CEN Auvergne-Rhône-Alpes', instanceId: 'cen', datePublication: '2026-10-12T02:30:00Z',
    });
    expect(fixture.componentInstance.infobulle()).toBe('Identifiant : cen · publié le 12/10/2026');
  });

  it('sans date (lecture en direct), l\'infobulle ne donne que l\'identifiant', () => {
    const fixture = setup({ libelle: 'RNF', instanceId: 'rnf', datePublication: null });
    expect(fixture.componentInstance.infobulle()).toBe('Identifiant : rnf');
  });
});
