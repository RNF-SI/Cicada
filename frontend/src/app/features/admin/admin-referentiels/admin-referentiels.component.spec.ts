import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialog } from '@angular/material/dialog';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';

import { EtatReferentiel, ReferentielActionsService } from '../../../core/services/referentiel-actions.service';
import { AdminReferentielsComponent } from './admin-referentiels.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({});
  }
}

const ETAT: EtatReferentiel[] = [{
  code: 'TYPE_ACTION', libelle: "Types d'action (Gestref)",
  en_service: { code: 'EDEN62', libelle: 'Codification unique Eden 62' },
  versions: [{ nom: 'gestref_v1', code: 'GESTREF_V1', libelle: 'Gestref V1', depuis: 'EDEN62',
               applicable: true, en_service: false }],
  passage: null,
}];

describe('AdminReferentielsComponent (#777)', () => {
  let fixture: ComponentFixture<AdminReferentielsComponent>;
  let component: AdminReferentielsComponent;
  let service: { etatAdmin: jest.Mock; simulerAdmin: jest.Mock; passageAdmin: jest.Mock };
  let dialog: { open: jest.Mock };

  beforeEach(async () => {
    service = {
      etatAdmin: jest.fn(() => of({ referentiels: ETAT })),
      simulerAdmin: jest.fn(() => of({ rapport: { depuis: 'EDEN62', vers: 'GESTREF_V1',
        actions: { sure: 45, probable: 74, a_arbitrer: 12 }, a_arbitrer_par_code: [], plans: [],
        plans_sans_destinataire: [] } })),
      passageAdmin: jest.fn(() => of({ referentiels: ETAT })),
    };
    dialog = { open: jest.fn(() => ({ afterClosed: () => of(true) })) };
    await TestBed.configureTestingModule({
      imports: [AdminReferentielsComponent, NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FakeTranslateLoader } })],
      providers: [{ provide: ReferentielActionsService, useValue: service },
                  { provide: MatDialog, useValue: dialog }],
    }).compileComponents();
    fixture = TestBed.createComponent(AdminReferentielsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('appliquer n\'est possible qu\'après la simulation, puis demande confirmation', () => {
    const bouton = () => fixture.nativeElement.querySelector('[data-testid="referentiel-appliquer"]');
    expect(bouton().disabled).toBe(true);
    component.simuler(ETAT[0], ETAT[0].versions[0]);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="referentiel-rapport"]')).not.toBeNull();
    expect(bouton().disabled).toBe(false);
    component.sansEmail.set(true);
    component.appliquer(ETAT[0], ETAT[0].versions[0]);
    expect(dialog.open).toHaveBeenCalled();
    expect(service.passageAdmin).toHaveBeenCalledWith('TYPE_ACTION', 'appliquer', 'gestref_v1', true);
  });
});
