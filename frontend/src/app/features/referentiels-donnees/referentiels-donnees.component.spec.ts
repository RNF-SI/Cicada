import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';

import { ReferentielActionsService } from '../../core/services/referentiel-actions.service';
import * as exportImage from '../../shared/utils/chart-image-export';
import { ReferentielsDonneesComponent } from './referentiels-donnees.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({});
  }
}

describe('ReferentielsDonneesComponent (#778)', () => {
  let fixture: ComponentFixture<ReferentielsDonneesComponent>;
  const service = {
    donnees: jest.fn(() => of({ referentiels: [
      { code: 'TAXREF', libelle: 'Taxons (TaxRef)', version: { code: 'TAXREF_V18', libelle: 'TaxRef v18' },
        nombre: 8000, source_url: 'https://inpn.mnhn.fr/telechargement/referentielEspece/taxref' },
      { code: 'TYPE_ACTION', libelle: "Types d'action (Gestref)", version: { code: 'GESTREF_V1', libelle: 'Gestref V1' },
        nombre: 177, source_url: null },
    ] })),
    telechargerCsv: jest.fn(() => of(new Blob(['code;libelle']))),
    // Utilisés par l'en-tête commun (bandeau #772).
    compte: signal(null),
    rafraichirCompte: jest.fn(),
    oublierCompte: jest.fn(),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReferentielsDonneesComponent, NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FakeTranslateLoader } })],
      providers: [provideRouter([]), { provide: ReferentielActionsService, useValue: service }],
    }).compileComponents();
    fixture = TestBed.createComponent(ReferentielsDonneesComponent);
    fixture.detectChanges();
  });

  it('affiche chaque référentiel avec sa version et télécharge son CSV', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('[data-testid="referentiel-donnees-TAXREF"]')?.textContent).toContain('TaxRef v18');
    const spy = jest.spyOn(exportImage, 'downloadBlob').mockImplementation(() => undefined);
    (el.querySelector('[data-testid="referentiel-donnees-TYPE_ACTION"] button') as HTMLButtonElement).click();
    expect(service.telechargerCsv).toHaveBeenCalledWith('TYPE_ACTION');
    expect(spy).toHaveBeenCalledWith('gestref_v1.csv', expect.any(Blob));
  });
});
