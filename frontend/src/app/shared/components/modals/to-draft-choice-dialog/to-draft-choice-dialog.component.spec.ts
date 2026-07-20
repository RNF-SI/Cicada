import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';
import {
  ToDraftChoiceDialogComponent,
  ToDraftChoiceDialogData,
  ToDraftChoiceDialogResult,
} from './to-draft-choice-dialog.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({});
  }
}

describe('ToDraftChoiceDialogComponent (#436)', () => {
  let component: ToDraftChoiceDialogComponent;
  let fixture: ComponentFixture<ToDraftChoiceDialogComponent>;
  let dialogRefMock: { close: jest.Mock };

  const createComponent = async (data: ToDraftChoiceDialogData) => {
    dialogRefMock = { close: jest.fn() };

    await TestBed.resetTestingModule()
      .configureTestingModule({
        imports: [
          ToDraftChoiceDialogComponent,
          NoopAnimationsModule,
          MatDialogModule,
          TranslateModule.forRoot({
            loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
            defaultLanguage: 'fr',
          }),
        ],
        providers: [
          { provide: MatDialogRef, useValue: dialogRefMock },
          { provide: MAT_DIALOG_DATA, useValue: data },
        ],
      })
      .compileComponents();

    fixture = TestBed.createComponent(ToDraftChoiceDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  beforeEach(async () => {
    await createComponent({ planName: 'Plan Test', canCreateNewVersion: true });
  });

  it('pickNewVersion() ferme avec le choix new-version', () => {
    component.pickNewVersion();
    expect(dialogRefMock.close).toHaveBeenCalledWith({ choice: 'new-version' } as ToDraftChoiceDialogResult);
  });

  it('pickToDraft() ferme avec le choix to-draft', () => {
    component.pickToDraft();
    expect(dialogRefMock.close).toHaveBeenCalledWith({ choice: 'to-draft' } as ToDraftChoiceDialogResult);
  });

  it('cancel() ferme avec le choix cancel', () => {
    component.cancel();
    expect(dialogRefMock.close).toHaveBeenCalledWith({ choice: 'cancel' } as ToDraftChoiceDialogResult);
  });

  it('affiche les implications des deux options quand la nouvelle version est possible', () => {
    const html = fixture.nativeElement as HTMLElement;
    expect(html.querySelector('.choice-card-recommended')).toBeTruthy();
    expect(html.querySelector('.choice-card-warning')).toBeTruthy();
    // 3 implications listées par option
    expect(html.querySelectorAll('.choice-implications li').length).toBe(6);
  });

  it('masque l’option « nouvelle version » quand elle est indisponible', async () => {
    await createComponent({ planName: 'Plan Test', canCreateNewVersion: false });
    const html = fixture.nativeElement as HTMLElement;
    expect(html.querySelector('.choice-card-recommended')).toBeNull();
    expect(html.querySelector('.choice-card-warning')).toBeTruthy();
    expect(html.querySelector('.hint')).toBeTruthy();
  });
});
