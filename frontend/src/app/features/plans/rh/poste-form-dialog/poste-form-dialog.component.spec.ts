/**
 * Tests du formulaire de poste (#560).
 *
 * L'essentiel porte sur la règle des quotités, qui double celle du backend
 * (`PosteWriteSerializer.validate_fonctions`) : toutes les quotités, ou
 * aucune ; et si quotités, la somme doit faire 100 %.
 */
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { PosteFormDialogComponent, PosteFormDialogData } from './poste-form-dialog.component';
import { RhService } from '../../../../core/services/rh.service';
import { AdminService } from '../../../../core/services/admin.service';
import { Fonction, Poste } from '../../../../core/models/rh.model';

const FONCTIONS: Fonction[] = [
  { id_fonction: 1, libelle: 'Garde-technicien', finance_par_defaut: true },
  { id_fonction: 2, libelle: 'Animateur nature', finance_par_defaut: true },
  { id_fonction: 3, libelle: 'Bénévole', finance_par_defaut: false },
];

const PLAN = {
  id_pg: 7,
  sites: [
    { id_site: 1, organismes: [{ id_organisme: 10, nom_organisme: 'RNF' }] },
    { id_site: 2, organismes: [{ id_organisme: 5, nom_organisme: 'CEN AURA' }, { id_organisme: 10, nom_organisme: 'RNF' }] },
  ],
};

describe('PosteFormDialogComponent', () => {
  let fixture: ComponentFixture<PosteFormDialogComponent>;
  let comp: PosteFormDialogComponent;
  let rhService: jest.Mocked<Partial<RhService>>;
  let dialogRef: { close: jest.Mock };

  async function setup(data: Partial<PosteFormDialogData> = {}) {
    rhService = {
      loadFonctions: jest.fn().mockReturnValue(of(FONCTIONS)),
      createFonction: jest.fn(),
      createPoste: jest.fn().mockReturnValue(of({ id_poste: 99 })),
      updatePoste: jest.fn().mockReturnValue(of({ id_poste: 42 })),
    } as any;
    dialogRef = { close: jest.fn() };

    await TestBed.configureTestingModule({
      imports: [PosteFormDialogComponent, NoopAnimationsModule, TranslateModule.forRoot()],
      providers: [
        { provide: RhService, useValue: rhService },
        { provide: AdminService, useValue: { getPlan: jest.fn().mockReturnValue(of(PLAN)) } },
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: { planId: 7, poste: null, ...data } },
      ],
    }).compileComponents();

    // On renvoie la clé i18n telle quelle : les tests comparent des clés.
    const translate = TestBed.inject(TranslateService);
    jest.spyOn(translate, 'instant').mockImplementation((key: any) => key);

    fixture = TestBed.createComponent(PosteFormDialogComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  }

  function addFonction(id: number) {
    comp.selectedFonctionId.set(id);
    comp.addFonction();
  }

  it('charge le référentiel des fonctions et les organismes des sites du plan', async () => {
    await setup();
    expect(comp.allFonctions()).toHaveLength(3);
    // Dédoublonnés (RNF est sur les 2 sites) et triés par nom.
    expect(comp.organismes().map((o) => o.nom_organisme)).toEqual(['CEN AURA', 'RNF']);
  });

  it('ne propose plus une fonction déjà ajoutée au poste', async () => {
    await setup();
    addFonction(1);
    expect(comp.availableFonctions().map((f) => f.id_fonction)).toEqual([2, 3]);
  });

  it('sans quotité, le poste est combiné (garde animateur à 1 ETP)', async () => {
    await setup();
    addFonction(1);
    addFonction(2);
    expect(comp.isCombine()).toBe(true);
    expect(comp.fonctionsError()).toBeNull();
  });

  it('refuse des quotités partielles (toutes ou aucune)', async () => {
    await setup();
    addFonction(1);
    addFonction(2);
    comp.setPourcentage(1, '50');
    expect(comp.isCombine()).toBe(false);
    expect(comp.fonctionsError()).toBe('plans.postes.form.errors.partialQuotite');
  });

  it('refuse une somme de quotités différente de 100', async () => {
    await setup();
    addFonction(1);
    addFonction(2);
    comp.setPourcentage(1, '50');
    comp.setPourcentage(2, '30');
    expect(comp.totalQuotite()).toBe(80);
    expect(comp.fonctionsError()).toBe('plans.postes.form.errors.sumQuotite');
  });

  it('accepte 50 / 50', async () => {
    await setup();
    addFonction(1);
    addFonction(2);
    comp.setPourcentage(1, '50');
    comp.setPourcentage(2, '50');
    expect(comp.fonctionsError()).toBeNull();
  });

  it('refuse un poste sans fonction', async () => {
    await setup();
    expect(comp.fonctionsError()).toBe('plans.postes.form.errors.noFonction');
  });

  it('repartirQuotites répartit à parts égales et la somme fait exactement 100', async () => {
    await setup();
    addFonction(1);
    addFonction(2);
    addFonction(3);
    comp.repartirQuotites();
    // 3 fonctions : 33,33 / 33,33 / 33,34 — la dernière absorbe l'arrondi.
    expect(comp.totalQuotite()).toBe(100);
    expect(comp.fonctionsError()).toBeNull();
  });

  it('effacerQuotites repasse le poste en cumul de fonctions', async () => {
    await setup();
    addFonction(1);
    addFonction(2);
    comp.repartirQuotites();
    expect(comp.isCombine()).toBe(false);
    comp.effacerQuotites();
    expect(comp.isCombine()).toBe(true);
    expect(comp.fonctionsError()).toBeNull();
  });

  it('setPourcentage avec une chaîne vide remet la quotité à null', async () => {
    await setup();
    addFonction(1);
    comp.setPourcentage(1, '100');
    comp.setPourcentage(1, '');
    expect(comp.isCombine()).toBe(true);
  });

  it('save() bloque et affiche l’erreur quand les quotités sont invalides', async () => {
    await setup();
    addFonction(1);
    addFonction(2);
    comp.setPourcentage(1, '50');
    comp.save();
    expect(comp.showFonctionsError()).toBe(true);
    expect(rhService.createPoste).not.toHaveBeenCalled();
  });

  it('save() envoie le nombre, l’ETP total et les fonctions, sans aucun nom (RGPD)', async () => {
    await setup();
    addFonction(1);
    comp.nombre.set(3);
    comp.etp.set(1.5);
    comp.idOrganisme.set(5);
    comp.save();

    expect(rhService.createPoste).toHaveBeenCalledWith({
      id_pg: 7,
      id_organisme: 5,
      nombre: 3,
      etp: 1.5,
      fonctions: [{ id_fonction: 1, pourcentage: null }],
    });
    expect(dialogRef.close).toHaveBeenCalledWith({ id_poste: 99 });
  });

  it('save() sans organisme envoie null', async () => {
    await setup();
    addFonction(1);
    comp.save();
    expect(rhService.createPoste).toHaveBeenCalledWith(
      expect.objectContaining({ id_organisme: null, nombre: 1, etp: null }),
    );
  });

  it('save() en erreur ne ferme pas la modale et relâche le bouton', async () => {
    await setup();
    (rhService.createPoste as jest.Mock).mockReturnValue(throwError(() => new Error('boom')));
    addFonction(1);
    comp.save();
    expect(dialogRef.close).not.toHaveBeenCalled();
    expect(comp.isSaving()).toBe(false);
    expect(comp.errorMessage()).not.toBeNull();
  });

  describe('édition', () => {
    const POSTE: Poste = {
      id_poste: 42,
      id_pg: 7,
      id_organisme: 10,
      nombre: 3,
      etp: '1.50',
      fonctions: [
        { id_fonction: 1, fonction_libelle: 'Garde-technicien', finance_par_defaut: true, pourcentage: '50.00' },
        { id_fonction: 2, fonction_libelle: 'Animateur nature', finance_par_defaut: true, pourcentage: '50.00' },
      ],
    } as Poste;

    it('hydrate le formulaire depuis le poste existant', async () => {
      await setup({ poste: POSTE });
      expect(comp.isEdit).toBe(true);
      expect(comp.nombre()).toBe(3);
      expect(comp.etp()).toBe(1.5);
      expect(comp.idOrganisme()).toBe(10);
      expect(comp.totalQuotite()).toBe(100);
      expect(comp.fonctionsError()).toBeNull();
    });

    it('save() appelle updatePoste sur l’identifiant du poste', async () => {
      await setup({ poste: POSTE });
      comp.save();
      expect(rhService.updatePoste).toHaveBeenCalledWith(42, expect.objectContaining({ nombre: 3 }));
      expect(rhService.createPoste).not.toHaveBeenCalled();
    });
  });

  it('cancel() ferme sans rien renvoyer', async () => {
    await setup();
    comp.cancel();
    expect(dialogRef.close).toHaveBeenCalledWith(null);
  });
});
