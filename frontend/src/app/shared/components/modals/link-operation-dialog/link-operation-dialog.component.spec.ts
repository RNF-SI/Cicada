import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslateModule } from '@ngx-translate/core';
import { of } from 'rxjs';
import {
  LinkOperationDialogComponent,
  LinkOperationDialogData,
  LinkOperationDialogResult,
} from './link-operation-dialog.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';

function setup(data: LinkOperationDialogData, opsResponse: any) {
  const dialogRef = { close: jest.fn() } as unknown as jest.Mocked<MatDialogRef<LinkOperationDialogComponent>>;
  const enjeuService = { getOperationsByPlan: jest.fn().mockReturnValue(of(opsResponse)) };

  TestBed.configureTestingModule({
    imports: [LinkOperationDialogComponent, NoopAnimationsModule, TranslateModule.forRoot()],
    providers: [
      { provide: MatDialogRef, useValue: dialogRef },
      { provide: MAT_DIALOG_DATA, useValue: data },
      { provide: EnjeuService, useValue: enjeuService },
    ],
  });

  const fixture: ComponentFixture<LinkOperationDialogComponent> = TestBed.createComponent(LinkOperationDialogComponent);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, dialogRef };
}

afterEach(() => TestBed.resetTestingModule());

describe('LinkOperationDialogComponent — mode indicateur (#539)', () => {
  const opsResponse = {
    groups: [
      {
        operations: [
          { id_operation: 1, libelle: 'Déjà rattachée', id_indicateur: 7, metrique_ids: [] },
          { id_operation: 2, libelle: 'Liable', id_indicateur: null, metrique_ids: [] },
          { id_operation: 3, libelle: 'Autre indicateur', id_indicateur: 9, metrique_ids: [] },
        ],
      },
    ],
  };

  it('active le mode indicateur quand aucune métrique n\'est fournie', () => {
    const { component } = setup({ planId: 1, indicateurId: 7, indicateurNom: 'Ind 7' }, opsResponse);
    expect(component.isIndicateurMode).toBe(true);
    expect(component.contextNom).toBe('Ind 7');
  });

  it('exclut les actions déjà rattachées à cet indicateur, garde les autres', () => {
    const { component } = setup({ planId: 1, indicateurId: 7, indicateurNom: 'Ind 7' }, opsResponse);
    component.selectLink();
    const ids = component.filteredOperations().map(o => o.id_operation);
    expect(ids).not.toContain(1); // déjà rattachée à l'indicateur 7
    expect(ids).toEqual(expect.arrayContaining([2, 3]));
  });

  it('renvoie action=link avec l\'operationId choisi', () => {
    const { component, dialogRef } = setup({ planId: 1, indicateurId: 7, indicateurNom: 'Ind 7' }, opsResponse);
    component.selectLink();
    component.selectOperation(2);
    component.confirmSelection();
    const result = dialogRef.close.mock.calls[0][0] as LinkOperationDialogResult;
    expect(result).toEqual({ action: 'link', operationId: 2 });
  });

  it('renvoie action=copy quand on choisit « Copier » (#552)', () => {
    const { component, dialogRef } = setup({ planId: 1, indicateurId: 7, indicateurNom: 'Ind 7' }, opsResponse);
    component.selectCopy();
    expect(component.mode()).toBe('copy');
    component.selectOperation(2);
    component.confirmSelection();
    const result = dialogRef.close.mock.calls[0][0] as LinkOperationDialogResult;
    expect(result).toEqual({ action: 'copy', operationId: 2 });
  });
});

describe('LinkOperationDialogComponent — mode métrique (existant)', () => {
  const opsResponse = {
    groups: [
      {
        operations: [
          { id_operation: 1, libelle: 'Déjà liée', id_indicateur: null, metrique_ids: [5] },
          { id_operation: 2, libelle: 'Liable', id_indicateur: null, metrique_ids: [] },
        ],
      },
    ],
  };

  it('n\'est pas en mode indicateur et exclut les actions déjà liées à la métrique', () => {
    const { component } = setup({ planId: 1, metriqueId: 5, metriqueNom: 'Métrique X' }, opsResponse);
    expect(component.isIndicateurMode).toBe(false);
    component.selectLink();
    const ids = component.filteredOperations().map(o => o.id_operation);
    expect(ids).toEqual([2]);
  });
});
