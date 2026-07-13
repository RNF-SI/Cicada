import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslateModule } from '@ngx-translate/core';
import {
  DeleteOperationDialogComponent,
  DeleteOperationDialogData,
  DeleteOperationDialogResult,
} from './delete-operation-dialog.component';

describe('DeleteOperationDialogComponent (#538 multi-sélection)', () => {
  let fixture: ComponentFixture<DeleteOperationDialogComponent>;
  let component: DeleteOperationDialogComponent;
  let dialogRef: jest.Mocked<MatDialogRef<DeleteOperationDialogComponent>>;

  const data: DeleteOperationDialogData = {
    libelle: 'Action test',
    metriques: [
      { id_metrique: 1, nom_metrique: 'Métrique A' },
      { id_metrique: 2, nom_metrique: 'Métrique B' },
      { id_metrique: 3, nom_metrique: 'Métrique C' },
    ],
  };

  beforeEach(async () => {
    dialogRef = { close: jest.fn() } as unknown as jest.Mocked<MatDialogRef<DeleteOperationDialogComponent>>;

    await TestBed.configureTestingModule({
      imports: [DeleteOperationDialogComponent, NoopAnimationsModule, TranslateModule.forRoot()],
      providers: [
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: data },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DeleteOperationDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('coche la première métrique par défaut', () => {
    expect(component.isMetriqueSelected(1)).toBe(true);
    expect(component.isMetriqueSelected(2)).toBe(false);
    expect(component.selectedMetriqueIds().size).toBe(1);
  });

  it('permet de cocher plusieurs métriques puis de renvoyer tous les ids', () => {
    component.toggleMetrique(2);
    component.toggleMetrique(3);
    expect(component.selectedMetriqueIds().size).toBe(3);

    component.confirm();

    const result = dialogRef.close.mock.calls[0][0] as DeleteOperationDialogResult;
    expect(result.action).toBe('unlink');
    expect(result.metriqueIds).toEqual(expect.arrayContaining([1, 2, 3]));
    expect(result.metriqueIds?.length).toBe(3);
  });

  it('décoche une métrique cochée', () => {
    component.toggleMetrique(1); // décoche la première
    expect(component.isMetriqueSelected(1)).toBe(false);
    expect(component.selectedMetriqueIds().size).toBe(0);
  });

  it('confirm en mode delete renvoie action=delete sans métrique', () => {
    component.setMode('delete');
    component.confirm();
    expect(dialogRef.close).toHaveBeenCalledWith({ action: 'delete' });
  });

  it('ne ferme pas si aucune métrique cochée en mode unlink', () => {
    component.toggleMetrique(1); // décoche la seule cochée
    component.confirm();
    expect(dialogRef.close).not.toHaveBeenCalled();
  });
});
