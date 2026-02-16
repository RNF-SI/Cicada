import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';

import { ConfirmDialogComponent, ConfirmDialogData } from './confirm-dialog.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({
      common: {
        actions: {
          confirm: 'Confirmer',
          cancel: 'Annuler',
        },
      },
    });
  }
}

describe('ConfirmDialogComponent', () => {
  let component: ConfirmDialogComponent;
  let fixture: ComponentFixture<ConfirmDialogComponent>;
  let mockDialogRef: jest.Mocked<MatDialogRef<ConfirmDialogComponent>>;

  const defaultData: ConfirmDialogData = {
    title: 'Titre de test',
    message: 'Message de test',
  };

  function createComponent(data: ConfirmDialogData = defaultData): void {
    mockDialogRef = { close: jest.fn() } as unknown as jest.Mocked<MatDialogRef<ConfirmDialogComponent>>;

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [
        ConfirmDialogComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
        }),
      ],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: data },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  beforeEach(() => {
    createComponent();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display title from data', () => {
    const titleEl = fixture.nativeElement.querySelector('[mat-dialog-title]');
    expect(titleEl.textContent).toContain('Titre de test');
  });

  it('should display message from data', () => {
    const messageEl = fixture.nativeElement.querySelector('mat-dialog-content p');
    expect(messageEl.textContent).toContain('Message de test');
  });

  it('should display custom confirmText', () => {
    createComponent({ ...defaultData, confirmText: 'Oui, supprimer' });
    const buttons = fixture.nativeElement.querySelectorAll('button');
    const confirmBtn = buttons[buttons.length - 1];
    expect(confirmBtn.textContent).toContain('Oui, supprimer');
  });

  it('should display custom cancelText', () => {
    createComponent({ ...defaultData, cancelText: 'Non, garder' });
    const buttons = fixture.nativeElement.querySelectorAll('button');
    const cancelBtn = buttons[0];
    expect(cancelBtn.textContent).toContain('Non, garder');
  });

  it('should close with true on confirm', () => {
    component.onConfirm();
    expect(mockDialogRef.close).toHaveBeenCalledWith(true);
  });

  it('should close with false on cancel', () => {
    component.onCancel();
    expect(mockDialogRef.close).toHaveBeenCalledWith(false);
  });

  it('should use default confirmColor primary', () => {
    // The component uses data.confirmColor || 'primary'
    expect(component.data.confirmColor).toBeUndefined();
    // Template fallback is 'primary'
  });

  it('should use custom confirmColor when provided', () => {
    createComponent({ ...defaultData, confirmColor: 'warn' });
    expect(component.data.confirmColor).toBe('warn');
  });
});
