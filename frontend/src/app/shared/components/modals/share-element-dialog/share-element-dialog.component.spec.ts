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

describe('ShareElementDialogComponent — résultat attendu (cible OO, #585)', () => {
  const data: ShareElementDialogData = {
    elementType: 'ra',
    elementLabel: 'RA 1',
    mode: 'link',
    enjeux: [
      {
        id_enjeu: 10,
        libelle: 'Enjeu A',
        objectifs: [
          { id_oo: 200, libelle: 'Restaurer les berges', numero: 1 },
          { id_oo: 201, libelle: 'Limiter la fréquentation', numero: 2 },
        ],
      },
      { id_enjeu: 20, libelle: 'Enjeu B', objectifs: [] },
    ],
  };

  it('cible un objectif opérationnel et renvoie targetOoId', () => {
    const { component, dialogRef } = setup(data);
    expect(component.isRa).toBe(true);
    expect(component.canConfirm()).toBe(false);

    component.selectOo(201);

    expect(component.canConfirm()).toBe(true);
    component.confirm();
    const result = dialogRef.close.mock.calls[0][0] as ShareElementDialogResult;
    expect(result).toEqual({ mode: 'link', targetOoId: 201 });
  });

  it('un second clic sur la même cible la désélectionne', () => {
    const { component } = setup(data);
    component.selectOo(200);
    component.selectOo(200);
    expect(component.canConfirm()).toBe(false);
  });

  it('hasTargets est faux si aucun objectif disponible', () => {
    const { component } = setup({
      ...data, enjeux: [{ id_enjeu: 20, libelle: 'Enjeu B', objectifs: [] }],
    });
    expect(component.hasTargets()).toBe(false);
  });

  it('la recherche filtre par libellé d\'objectif', () => {
    const { component } = setup(data);
    component.onSearchChange('berges');
    const groupes = component.filteredEnjeux();
    expect(groupes).toHaveLength(1);
    expect(groupes[0].objectifs!.map(o => o.id_oo)).toEqual([200]);
  });

  it('le mode copie reste disponible et remonte la même cible', () => {
    const { component, dialogRef } = setup({ ...data, mode: 'copy' });
    component.selectOo(200);
    component.confirm();
    expect(dialogRef.close.mock.calls[0][0]).toEqual({ mode: 'copy', targetOoId: 200 });
  });
});

describe('ShareElementDialogComponent — action (#585)', () => {
  const data: ShareElementDialogData = {
    elementType: 'operation',
    elementLabel: 'Fauche tardive',
    mode: 'link',
    enjeux: [],
    indicateurs: [
      {
        id_indicateur: 1,
        nom: 'Surface de roselière',
        contexte: 'Enjeu A › NE 1',
        metriques: [
          { id_metrique: 11, nom: 'Surface (ha)' },
          { id_metrique: 12, nom: 'Recouvrement (%)' },
        ],
      },
      {
        id_indicateur: 2,
        nom: 'Pression de pâturage',
        contexte: 'Enjeu B › RA 1',
        metriques: [],
      },
    ],
  };

  it('expose les indicateurs comme cibles', () => {
    const { component } = setup(data);
    expect(component.isOperation).toBe(true);
    expect(component.typeKey).toBe('operation');
    expect(component.hasTargets()).toBe(true);
    expect(component.canConfirm()).toBe(false);
  });

  it('confirme un lien vers la métrique choisie', () => {
    const { component, dialogRef } = setup(data);
    component.selectMetrique(12);
    expect(component.canConfirm()).toBe(true);
    component.confirm();
    const result = dialogRef.close.mock.calls[0][0] as ShareElementDialogResult;
    expect(result).toEqual({ mode: 'link', targetMetriqueId: 12 });
  });

  it('interdit de cibler un indicateur en mode « lier »', () => {
    // Une action n'a qu'un seul indicateur porteur (FK) : le partage exige une métrique.
    const { component } = setup(data);
    expect(component.canTargetIndicateurDirectly()).toBe(false);
    component.selectIndicateur(1);
    expect(component.selectedIndicateurId()).toBeNull();
    expect(component.canConfirm()).toBe(false);
  });

  it('autorise l\'indicateur comme cible en mode « copier »', () => {
    const { component, dialogRef } = setup({ ...data, mode: 'copy' });
    expect(component.canTargetIndicateurDirectly()).toBe(true);
    component.selectIndicateur(2);
    expect(component.canConfirm()).toBe(true);
    component.confirm();
    const result = dialogRef.close.mock.calls[0][0] as ShareElementDialogResult;
    expect(result).toEqual({ mode: 'copy', targetIndicateurId: 2 });
  });

  it('les cibles indicateur et métrique sont exclusives', () => {
    const { component } = setup({ ...data, mode: 'copy' });
    component.selectIndicateur(1);
    component.selectMetrique(11);
    expect(component.selectedIndicateurId()).toBeNull();
    expect(component.selectedMetriqueId()).toBe(11);

    component.selectIndicateur(1);
    expect(component.selectedMetriqueId()).toBeNull();
    expect(component.selectedIndicateurId()).toBe(1);
  });

  it('repasser en « lier » annule une cible indicateur déjà choisie', () => {
    const { component } = setup({ ...data, mode: 'copy' });
    component.selectIndicateur(1);
    component.setMode('link');
    expect(component.selectedIndicateurId()).toBeNull();
    expect(component.canConfirm()).toBe(false);
  });

  const sansMetrique: ShareElementDialogData = {
    ...data,
    indicateurs: [{ id_indicateur: 2, nom: 'X', metriques: [] }],
  };

  it('hasTargets est faux en mode « lier » quand aucun indicateur n\'a de métrique', () => {
    expect(setup(sansMetrique).component.hasTargets()).toBe(false);
  });

  it('hasTargets est vrai en mode « copier » : l\'indicateur seul reste une cible', () => {
    expect(setup({ ...sansMetrique, mode: 'copy' }).component.hasTargets()).toBe(true);
  });

  it('la recherche filtre par nom d\'indicateur, de contexte ou de métrique', () => {
    const { component } = setup(data);

    component.onSearchChange('recouvrement');
    expect(component.filteredIndicateurs().map(i => i.id_indicateur)).toEqual([1]);
    expect(component.filteredIndicateurs()[0].metriques).toHaveLength(1);

    component.onSearchChange('Enjeu B');
    expect(component.filteredIndicateurs().map(i => i.id_indicateur)).toEqual([2]);

    component.onSearchChange('roselière');
    expect(component.filteredIndicateurs()[0].metriques).toHaveLength(2);
  });
});
