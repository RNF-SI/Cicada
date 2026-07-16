import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslateModule } from '@ngx-translate/core';
import {
  ShareElementDialogComponent,
  ShareElementDialogData,
  ShareElementDialogResult,
} from './share-element-dialog.component';

function setup(data: ShareElementDialogData) {
  const dialogRef = { close: jest.fn() } as unknown as jest.Mocked<MatDialogRef<ShareElementDialogComponent>>;

  TestBed.configureTestingModule({
    imports: [ShareElementDialogComponent, NoopAnimationsModule, TranslateModule.forRoot()],
    providers: [
      { provide: MatDialogRef, useValue: dialogRef },
      { provide: MAT_DIALOG_DATA, useValue: data },
    ],
  });

  const fixture: ComponentFixture<ShareElementDialogComponent> = TestBed.createComponent(ShareElementDialogComponent);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, dialogRef };
}

afterEach(() => TestBed.resetTestingModule());

describe('ShareElementDialogComponent — facteur', () => {
  const data: ShareElementDialogData = {
    elementType: 'facteur',
    elementLabel: 'Agriculture',
    mode: 'link',
    enjeux: [
      { id_enjeu: 10, libelle: 'Enjeu A' },
      { id_enjeu: 20, libelle: 'Enjeu B' },
    ],
  };

  it('démarre dans le mode présélectionné et expose les cibles', () => {
    const { component } = setup(data);
    expect(component.mode()).toBe('link');
    expect(component.isOo).toBe(false);
    expect(component.hasTargets()).toBe(true);
    expect(component.canConfirm()).toBe(false);
  });

  it('confirme un lien vers l\'enjeu choisi', () => {
    const { component, dialogRef } = setup(data);
    component.selectEnjeu(20);
    expect(component.canConfirm()).toBe(true);
    component.confirm();
    const result = dialogRef.close.mock.calls[0][0] as ShareElementDialogResult;
    expect(result).toEqual({ mode: 'link', targetEnjeuId: 20 });
  });

  it('bascule en copie et renvoie mode=copy', () => {
    const { component, dialogRef } = setup(data);
    component.setMode('copy');
    component.selectEnjeu(10);
    component.confirm();
    const result = dialogRef.close.mock.calls[0][0] as ShareElementDialogResult;
    expect(result).toEqual({ mode: 'copy', targetEnjeuId: 10 });
  });

  it('filtre les enjeux par recherche', () => {
    const { component } = setup(data);
    component.onSearchChange('enjeu b');
    expect(component.filteredEnjeux().map(e => e.id_enjeu)).toEqual([20]);
  });

  it('ferme sans résultat à l\'annulation', () => {
    const { component, dialogRef } = setup(data);
    component.cancel();
    expect(dialogRef.close).toHaveBeenCalledWith(null);
  });
});

describe('ShareElementDialogComponent — OO (cible pression)', () => {
  const data: ShareElementDialogData = {
    elementType: 'oo',
    elementLabel: 'OO 1',
    mode: 'copy',
    enjeux: [
      {
        id_enjeu: 10,
        libelle: 'Enjeu A',
        pressions: [
          { id_pression: 100, libelle: 'Pression P1', facteurLibelle: 'Facteur F1' },
          { id_pression: 101, libelle: 'Pression P2', facteurLibelle: 'Facteur F1' },
        ],
      },
      { id_enjeu: 20, libelle: 'Enjeu B', pressions: [] },
    ],
  };

  it('cible une pression et renvoie targetPressionId', () => {
    const { component, dialogRef } = setup(data);
    expect(component.isOo).toBe(true);
    component.selectPression(101);
    expect(component.canConfirm()).toBe(true);
    component.confirm();
    const result = dialogRef.close.mock.calls[0][0] as ShareElementDialogResult;
    expect(result).toEqual({ mode: 'copy', targetPressionId: 101 });
  });

  it('hasTargets est faux si aucune pression disponible', () => {
    const { component } = setup({ ...data, enjeux: [{ id_enjeu: 20, libelle: 'Enjeu B', pressions: [] }] });
    expect(component.hasTargets()).toBe(false);
  });

  it('la recherche filtre par libellé de pression ou de facteur', () => {
    const { component } = setup(data);
    component.onSearchChange('p2');
    const groups = component.filteredEnjeux();
    expect(groups).toHaveLength(1);
    expect(groups[0].pressions!.map(p => p.id_pression)).toEqual([101]);
  });
});
