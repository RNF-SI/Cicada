import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';

import { CampanuleService } from '../../../../core/services/campanule.service';
import { CampanuleProtocoleDetail } from '../../../../core/models/campanule.model';
import { ProtocoleCampanuleDialogComponent } from './protocole-campanule-dialog.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({ campanule: { dialog: { urlPerm: 'Lien permanent INPN', urlProtocole: 'Page du protocole' } } });
  }
}

function rendre(protocole: Partial<CampanuleProtocoleDetail>): HTMLElement {
  TestBed.configureTestingModule({
    imports: [
      ProtocoleCampanuleDialogComponent, NoopAnimationsModule,
      TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FakeTranslateLoader } }),
    ],
    providers: [
      { provide: MatDialogRef, useValue: { close: jest.fn() } },
      { provide: MAT_DIALOG_DATA, useValue: { cdProtocole: 900101 } },
      { provide: CampanuleService, useValue: { getProtocole: () => of({ cd_protocole: 900101, lb_protocole_court: 'DAT', ...protocole }) } },
    ],
  });
  const fixture = TestBed.createComponent(ProtocoleCampanuleDialogComponent);
  fixture.componentInstance['translate'].use('fr');
  fixture.detectChanges();
  return fixture.nativeElement as HTMLElement;
}

describe('ProtocoleCampanuleDialogComponent (#781)', () => {
  it('protocole hors INPN : pas de « Lien permanent INPN », références avec les liens', () => {
    const el = rendre({
      url: 'https://ancrage.reserves-naturelles.org/',
      references: ['Guide méthodologique Natur\'Adapt — 2023.', 'Retours d\'expérience…'],
    });
    expect(el.textContent).not.toContain('INPN');
    expect(el.textContent).toContain('Page du protocole');
    const refs = el.querySelector('[data-testid="protocole-references"]');
    expect(refs?.textContent).toContain('Guide méthodologique');
    expect(refs?.querySelectorAll('p').length).toBe(2);
  });

  it('informations complémentaires affichées', () => {
    const el = rendre({ infos_complementaires: 'Qui le réalise ? Un stagiaire.' });
    expect(el.querySelector('[data-testid="protocole-infos-complementaires"]')?.textContent)
      .toContain('Qui le réalise ?');
  });
});
