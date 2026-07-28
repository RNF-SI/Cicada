/**
 * Tests du formulaire « type de poste » (#560, #579).
 *
 * Depuis #579 : une fonction unique par type de poste, N personnes → N
 * enregistrements `Poste` (nombre = 1), un organisme par personne, aucun ETP
 * saisi ici. Aucune donnée nominative (RGPD).
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
  { id_fonction: 1, libelle: 'Garde-technicien', finance_par_defaut: true, type_poste: 'salarie' },
  { id_fonction: 2, libelle: 'Animateur nature', finance_par_defaut: true, type_poste: 'salarie' },
  { id_fonction: 3, libelle: 'Stagiaire', finance_par_defaut: false, type_poste: 'stagiaire' },
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
      createPoste: jest.fn().mockImplementation((p: any) => of({ id_poste: 90 + (p.id_organisme ?? 0) })),
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

  it('charge le référentiel des fonctions et les organismes des sites du plan', async () => {
    await setup();
    expect(comp.allFonctions()).toHaveLength(3);
    // Dédoublonnés (RNF est sur les 2 sites) et triés par nom.
    expect(comp.organismes().map((o) => o.nom_organisme)).toEqual(['CEN AURA', 'RNF']);
  });

  it('ne demande que les fonctions du plan courant (#631)', async () => {
    await setup();
    expect(rhService.loadFonctions).toHaveBeenCalledWith(7);
  });

  it('démarre avec une seule ligne personne', async () => {
    await setup();
    expect(comp.instances()).toHaveLength(1);
    expect(comp.selectedFonctionId()).toBeNull();
  });

  it('setNombre ajoute des lignes personnes en préservant les organismes saisis', async () => {
    await setup();
    comp.setInstanceOrganisme(0, 5);
    comp.setNombre(3);
    expect(comp.instances()).toHaveLength(3);
    expect(comp.instances()[0].id_organisme).toBe(5); // préservé
    expect(comp.instances()[1].id_organisme).toBeNull();
  });

  it('setNombre réduit le nombre de lignes (et jamais sous 1)', async () => {
    await setup();
    comp.setNombre(4);
    comp.setNombre(2);
    expect(comp.instances()).toHaveLength(2);
    comp.setNombre(0);
    expect(comp.instances()).toHaveLength(1);
    expect(comp.nombre()).toBe(1);
  });

  it('formError signale une fonction manquante', async () => {
    await setup();
    expect(comp.formError()).toBe('plans.postes.form.errors.noFonctionSelected');
    comp.selectedFonctionId.set(3);
    expect(comp.formError()).toBeNull();
  });

  it('createFonction ajoute la fonction, la sélectionne et referme le champ', async () => {
    await setup();
    (rhService.createFonction as jest.Mock).mockReturnValue(
      of({ id_fonction: 9, libelle: 'Bénévole', finance_par_defaut: false }),
    );
    comp.toggleNewFonction();
    expect(comp.showNewFonction()).toBe(true);
    comp.newFonctionLibelle.set('Bénévole');
    comp.createFonction();
    expect(comp.allFonctions().some((f) => f.id_fonction === 9)).toBe(true);
    expect(comp.selectedFonctionId()).toBe(9);
    expect(comp.showNewFonction()).toBe(false);
    // #631 — la fonction créée reste attachée au plan courant.
    expect(rhService.createFonction).toHaveBeenCalledWith('Bénévole', true, 'salarie', 7);
  });

  it('save() transmet le nom local et le commentaire, détourés (#632)', async () => {
    await setup();
    comp.selectedFonctionId.set(1);
    comp.nomLocal.set('  Garde du secteur nord  ');
    comp.commentaire.set('  Poste partagé avec la commune.  ');
    comp.save();
    expect(rhService.createPoste).toHaveBeenCalledWith(
      expect.objectContaining({
        nom_local: 'Garde du secteur nord',
        commentaire: 'Poste partagé avec la commune.',
      }),
    );
  });

  it('reprend le nom local et le commentaire du poste édité (#632)', async () => {
    await setup({
      poste: {
        id_poste: 42, id_pg: 7, nombre: 1,
        nom_local: 'Garde du secteur nord', commentaire: 'Mi-temps',
        fonctions: [{ id_fonction: 1, fonction_libelle: 'Garde-technicien', type_poste: 'salarie' }],
      } as Poste,
    });
    expect(comp.nomLocal()).toBe('Garde du secteur nord');
    expect(comp.commentaire()).toBe('Mi-temps');
  });

  it('save() bloque et affiche l’erreur quand aucune fonction n’est choisie', async () => {
    await setup();
    comp.save();
    expect(comp.showError()).toBe(true);
    expect(rhService.createPoste).not.toHaveBeenCalled();
  });

  it('save() crée un poste (nombre = 1) par personne, chacun avec son organisme, sans ETP ni nom (RGPD)', async () => {
    await setup();
    comp.selectedFonctionId.set(3);
    comp.setNombre(2);
    comp.setInstanceOrganisme(0, 5);
    comp.setInstanceOrganisme(1, 10);
    comp.save();

    expect(rhService.createPoste).toHaveBeenCalledTimes(2);
    expect(rhService.createPoste).toHaveBeenNthCalledWith(1, {
      id_pg: 7,
      id_organisme: 5,
      organisme_libre: '',
      nom_local: '',
      commentaire: '',
      nombre: 1,
      cout_jour: null,
      fonctions: [{ id_fonction: 3, pourcentage: null }],
    });
    expect(rhService.createPoste).toHaveBeenNthCalledWith(2, {
      id_pg: 7,
      id_organisme: 10,
      organisme_libre: '',
      nom_local: '',
      commentaire: '',
      nombre: 1,
      cout_jour: null,
      fonctions: [{ id_fonction: 3, pourcentage: null }],
    });
    // Aucun champ etp dans le payload (#579).
    expect((rhService.createPoste as jest.Mock).mock.calls[0][0]).not.toHaveProperty('etp');
    expect(dialogRef.close).toHaveBeenCalled();
  });

  it('save() sans organisme envoie null', async () => {
    await setup();
    comp.selectedFonctionId.set(1);
    comp.save();
    expect(rhService.createPoste).toHaveBeenCalledWith(
      expect.objectContaining({ id_organisme: null, nombre: 1 }),
    );
  });

  it('save() en erreur ne ferme pas la modale et relâche le bouton', async () => {
    await setup();
    (rhService.createPoste as jest.Mock).mockReturnValue(throwError(() => new Error('boom')));
    comp.selectedFonctionId.set(1);
    comp.save();
    expect(dialogRef.close).not.toHaveBeenCalled();
    expect(comp.isSaving()).toBe(false);
    expect(comp.errorMessage()).not.toBeNull();
  });

  describe('coût jour (#596)', () => {
    it('demande le coût jour pour un salarié / stagiaire', async () => {
      await setup();
      comp.onFonctionChange(1); // salarié
      expect(comp.showCoutJour()).toBe(true);
      expect(comp.coutJour()).toBeNull();
    });

    it('masque le coût jour pour un prestataire et l’efface', async () => {
      await setup();
      comp.allFonctions.update((l) => [
        ...l,
        { id_fonction: 4, libelle: 'Presta SIG', finance_par_defaut: true, type_poste: 'prestataire' },
      ]);
      comp.setCoutJour(120);
      comp.onFonctionChange(4);
      expect(comp.showCoutJour()).toBe(false);
      expect(comp.coutJour()).toBeNull();
    });

    it('met le coût jour à 0 par défaut pour un bénévole', async () => {
      await setup();
      comp.allFonctions.update((l) => [
        ...l,
        { id_fonction: 5, libelle: 'Bénévole', finance_par_defaut: false, type_poste: 'benevole' },
      ]);
      comp.onFonctionChange(5);
      expect(comp.showCoutJour()).toBe(true);
      expect(comp.coutJour()).toBe(0);
    });

    it('inclut le coût jour saisi par personne dans le payload de création (#603)', async () => {
      await setup();
      comp.onFonctionChange(1);
      comp.setInstanceOrganisme(0, 5);
      comp.setInstanceCoutJour(0, 350);
      comp.save();
      expect(rhService.createPoste).toHaveBeenCalledWith(
        expect.objectContaining({ cout_jour: 350 }),
      );
    });
  });

  // #622 — un prestataire n'a pas de coût jour, donc pas de temps de travail à
  // programmer : on ne peut plus en créer. Son coût reste saisissable en
  // « Coût prestataire » du budget de l'action (saisie et suivi).
  describe('type « prestataire » retiré (#622)', () => {
    it('ne propose plus « prestataire » à la création d’une fonction', async () => {
      await setup();
      expect(comp.typePosteOptions).toEqual(['salarie', 'stagiaire', 'benevole', 'partenaire']);
      expect(comp.typePosteOptions).not.toContain('prestataire');
    });

    it('réinjecte la fonction du poste édité si elle a été désactivée', async () => {
      // La fonction « Prestataire » n'est plus renvoyée par le référentiel
      // actif : sans réinjection, le menu s'afficherait vide et
      // l'enregistrement perdrait la fonction du poste.
      await setup({
        poste: {
          id_poste: 42, id_pg: 7, id_organisme: null, organisme_libre: 'Bureau SIG', nombre: 1,
          fonctions: [
            { id_fonction: 99, fonction_libelle: 'Prestataire', finance_par_defaut: true, type_poste: 'prestataire', pourcentage: null },
          ],
        } as unknown as Poste,
      });
      expect(comp.allFonctions().map((f) => f.id_fonction)).toContain(99);
      expect(comp.selectedFonctionId()).toBe(99);
      expect(comp.selectedType()).toBe('prestataire');
      expect(comp.selectedFonctionLabel()).toBe('Prestataire');
    });

    it('ne duplique pas une fonction déjà présente dans le référentiel', async () => {
      await setup({
        poste: {
          id_poste: 42, id_pg: 7, id_organisme: 10, nombre: 1,
          fonctions: [{ id_fonction: 1, fonction_libelle: 'Garde-technicien', pourcentage: null }],
        } as unknown as Poste,
      });
      expect(comp.allFonctions()).toHaveLength(3);
    });
  });

  describe('prestataire (#599)', () => {
    function addPresta() {
      comp.allFonctions.update((l) => [
        ...l,
        { id_fonction: 4, libelle: 'Presta SIG', finance_par_defaut: true, type_poste: 'prestataire' },
      ]);
    }

    it('préremplit les organismes libres « presta1 », « presta2 »', async () => {
      await setup();
      addPresta();
      comp.setNombre(2);
      comp.onFonctionChange(4);
      expect(comp.isOrganismeLibre()).toBe(true);
      expect(comp.instances().map((i) => i.organisme_libre)).toEqual(['presta1', 'presta2']);
    });

    it('envoie organisme_libre et id_organisme null au save', async () => {
      await setup();
      addPresta();
      comp.onFonctionChange(4);
      comp.setInstanceOrganismeLibre(0, 'Bureau SIG');
      comp.save();
      expect(rhService.createPoste).toHaveBeenCalledWith(
        expect.objectContaining({ id_organisme: null, organisme_libre: 'Bureau SIG', cout_jour: null }),
      );
    });
  });

  it('instanceLabel intitule les lignes avec la fonction choisie', async () => {
    await setup();
    comp.selectedFonctionId.set(3);
    comp.instanceLabel(0);
    const translate = TestBed.inject(TranslateService);
    expect(translate.instant).toHaveBeenCalledWith(
      'plans.postes.form.instanceLabel',
      { fonction: 'Stagiaire', index: 1 },
    );
  });

  describe('édition', () => {
    const POSTE: Poste = {
      id_poste: 42,
      id_pg: 7,
      id_organisme: 10,
      nombre: 1,
      etp: '1.50',
      fonctions: [
        { id_fonction: 1, fonction_libelle: 'Garde-technicien', finance_par_defaut: true, pourcentage: null },
      ],
    } as Poste;

    it('hydrate le formulaire depuis le poste existant', async () => {
      await setup({ poste: POSTE });
      expect(comp.isEdit).toBe(true);
      expect(comp.selectedFonctionId()).toBe(1);
      expect(comp.idOrganisme()).toBe(10);
    });

    it('save() appelle updatePoste avec la fonction et l’organisme, sans créer de poste', async () => {
      await setup({ poste: POSTE });
      comp.idOrganisme.set(5);
      comp.save();
      expect(rhService.updatePoste).toHaveBeenCalledWith(
        42,
        expect.objectContaining({
          id_organisme: 5,
          fonctions: [{ id_fonction: 1, pourcentage: null }],
        }),
      );
      expect(rhService.createPoste).not.toHaveBeenCalled();
    });
  });

  it('cancel() ferme sans rien renvoyer', async () => {
    await setup();
    comp.cancel();
    expect(dialogRef.close).toHaveBeenCalledWith(null);
  });
});
