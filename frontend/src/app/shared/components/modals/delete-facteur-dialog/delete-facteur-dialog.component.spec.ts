import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslateModule } from '@ngx-translate/core';
import { DeleteFacteurDialogComponent, DeleteFacteurDialogData } from './delete-facteur-dialog.component';

describe('DeleteFacteurDialogComponent (#730)', () => {
  let fixture: ComponentFixture<DeleteFacteurDialogComponent>;
  let component: DeleteFacteurDialogComponent;
  let dialogRef: jest.Mocked<MatDialogRef<DeleteFacteurDialogComponent>>;
  const data: DeleteFacteurDialogData = { libelle: 'Urbanisation', enjeuLibelle: 'Zones humides', nbEnjeux: 2 };

  beforeEach(async () => {
    dialogRef = { close: jest.fn() } as unknown as jest.Mocked<MatDialogRef<DeleteFacteurDialogComponent>>;
    await TestBed.configureTestingModule({
      imports: [DeleteFacteurDialogComponent, NoopAnimationsModule, TranslateModule.forRoot()],
      providers: [
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: data },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(DeleteFacteurDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('propose par défaut le retrait du lien (option non destructive)', () => {
    component.confirm();
    expect(dialogRef.close).toHaveBeenCalledWith({ action: 'unlink' });
  });

  it('renvoie la suppression quand on la choisit', () => {
    (fixture.nativeElement as HTMLElement)
      .querySelector<HTMLButtonElement>('[data-testid="facteur-delete-choice"]')!.click();
    component.confirm();
    expect(dialogRef.close).toHaveBeenCalledWith({ action: 'delete' });
  });

  it('annuler ne supprime rien', () => {
    component.cancel();
    expect(dialogRef.close).toHaveBeenCalledWith({ action: 'cancel' });
  });
});
