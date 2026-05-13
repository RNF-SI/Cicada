import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';
import {
  MiParcoursPromptDialogComponent,
  MiParcoursPromptDialogResult,
} from './mi-parcours-prompt-dialog.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({});
  }
}

describe('MiParcoursPromptDialogComponent (#276)', () => {
  let component: MiParcoursPromptDialogComponent;
  let fixture: ComponentFixture<MiParcoursPromptDialogComponent>;
  let dialogRefMock: { close: jest.Mock };

  beforeEach(async () => {
    dialogRefMock = { close: jest.fn() };

    await TestBed.configureTestingModule({
      imports: [
        MiParcoursPromptDialogComponent,
        NoopAnimationsModule,
        MatDialogModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          defaultLanguage: 'fr',
        }),
      ],
      providers: [
        { provide: MatDialogRef, useValue: dialogRefMock },
        { provide: MAT_DIALOG_DATA, useValue: { planName: 'Plan Test' } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MiParcoursPromptDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('expose le nom du plan via data', () => {
    expect(component.data.planName).toBe('Plan Test');
  });

  it('pickModifie() ferme avec isMiParcours=false', () => {
    component.pickModifie();
    expect(dialogRefMock.close).toHaveBeenCalledWith({ isMiParcours: false } as MiParcoursPromptDialogResult);
  });

  it('pickMiParcours() ferme avec isMiParcours=true', () => {
    component.pickMiParcours();
    expect(dialogRefMock.close).toHaveBeenCalledWith({ isMiParcours: true } as MiParcoursPromptDialogResult);
  });

  it('cancel() ferme avec isMiParcours=null', () => {
    component.cancel();
    expect(dialogRefMock.close).toHaveBeenCalledWith({ isMiParcours: null } as MiParcoursPromptDialogResult);
  });
});
