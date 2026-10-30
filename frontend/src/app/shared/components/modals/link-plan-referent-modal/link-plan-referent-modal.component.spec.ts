/**
 * #714 — Rattacher un utilisateur au plan en tant que rédacteur externe depuis
 * « Gérer les utilisateurs » : l'ajout passe par l'endpoint dédié (rôle +
 * référent) et l'utilisateur est marqué « Rédacteur externe ».
 */
import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule } from '@ngx-translate/core';
import { signal } from '@angular/core';
import { of } from 'rxjs';

import { LinkPlanReferentModalComponent } from './link-plan-referent-modal.component';
import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';

describe('LinkPlanReferentModalComponent — rédacteur externe (#714)', () => {
  const candidat = { id_role: 42, email: 'be@bureau.fr', prenom_role: 'Bea', nom_role: 'Bureau' };
  let adminService: Record<string, jest.Mock>;
  let close: jest.Mock;
  let redacteursInstance: any[] = [];
  beforeEach(() => { redacteursInstance = []; });

  async function setup(membres: any[] = [], referents: any[] = []): Promise<LinkPlanReferentModalComponent> {
    adminService = {
      getUsers: jest.fn(() => of({ results: [candidat] })),
      getRedacteursExternesForPlan: jest.fn(() => of(redacteursInstance)),
      assignRedacteurExterneToPlan: jest.fn(() => of({})),
      assignReferentToPlan: jest.fn(() => of({})),
      assignMemberToPlan: jest.fn(() => of({})),
      removeMemberFromPlan: jest.fn(() => of({})),
    };
    close = jest.fn();
    await TestBed.configureTestingModule({
      imports: [LinkPlanReferentModalComponent, NoopAnimationsModule, TranslateModule.forRoot()],
      providers: [
        { provide: AdminService, useValue: adminService },
        {
          provide: AuthService,
          useValue: {
            isSuperAdmin: signal(false), isAdminOrganisme: signal(false),
            hasGlobalAccess: signal(false), currentUser: signal({ id: 1 }),
          },
        },
        { provide: MatDialogRef, useValue: { close } },
        { provide: MAT_DIALOG_DATA, useValue: { plan: { id_pg: 7, nom: 'Plan', membres, referents } } },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(LinkPlanReferentModalComponent);
    fixture.detectChanges();
    return fixture.componentInstance;
  }

  it('ajoute comme rédacteur externe : référent + endpoint dédié', async () => {
    const component = await setup();
    component.addAsRedacteurExterne = true;
    component.addUser(candidat as any);

    const [ajout] = component.userAssignments();
    expect(ajout.user.referent).toBe(true);
    expect(ajout.user.is_redacteur_externe).toBe(true);

    component.onSave();
    expect(adminService['assignRedacteurExterneToPlan']).toHaveBeenCalledWith(7, 42);
    expect(adminService['assignReferentToPlan']).not.toHaveBeenCalled();
    expect(close).toHaveBeenCalledWith({ success: true, changed: true });
  });

  it('sans l\'option, ajout ordinaire', async () => {
    const component = await setup();
    component.addUser(candidat as any);
    component.onSave();
    expect(adminService['assignMemberToPlan']).toHaveBeenCalledWith(7, 42);
    expect(adminService['assignRedacteurExterneToPlan']).not.toHaveBeenCalled();
  });

  it('marque le rédacteur externe déjà rattaché', async () => {
    const component = await setup([
      { id_role: 42, email: 'be@bureau.fr', referent: true, is_redacteur_externe: true },
    ]);
    expect(component.userAssignments()[0].user.is_redacteur_externe).toBe(true);
  });

  describe('#738 — « Ajouter en tant que référent » coché après le choix', () => {
    it('promeut les utilisateurs ajoutés et pas encore enregistrés', async () => {
      const component = await setup();
      component.addUser(candidat as any);
      component.setAddAsReferent(true);

      expect(component.userAssignments()[0].user.referent).toBe(true);
      component.onSave();
      expect(adminService['assignReferentToPlan']).toHaveBeenCalledWith(7, 42);
      expect(adminService['assignMemberToPlan']).not.toHaveBeenCalled();
    });

    it('la case rédacteur externe s\'applique aussi après coup', async () => {
      const component = await setup();
      component.addUser(candidat as any);
      component.setAddAsRedacteurExterne(true);
      component.onSave();
      expect(adminService['assignRedacteurExterneToPlan']).toHaveBeenCalledWith(7, 42);
    });

    it('ne touche pas aux utilisateurs déjà enregistrés', async () => {
      const component = await setup([{ id_role: 5, email: 'm@x.fr', referent: false }]);
      component.setAddAsReferent(true);
      expect(component.userAssignments()[0].user.referent).toBe(false);
      expect(component.hasChanges).toBe(false);
    });

    it('les options précèdent le champ de recherche', async () => {
      await setup();
      const fixture = TestBed.createComponent(LinkPlanReferentModalComponent);
      fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement;
      const toggle = el.querySelector('.add-as-toggle');
      const search = el.querySelector('.user-search-field');
      expect(toggle && search).toBeTruthy();
      expect(toggle!.compareDocumentPosition(search!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });
  });

  describe('#737 — rédacteurs externes de l\'instance', () => {
    const bureau = { id_role: 77, email: 'r@etoile.fr', prenom_role: 'Rita', nom_role: 'Redac', nom_organisme: 'Bureau étoile' };

    it('propose les rédacteurs externes hors de la liste des utilisateurs', async () => {
      redacteursInstance = [bureau];
      const component = await setup();
      expect(adminService['getRedacteursExternesForPlan']).toHaveBeenCalledWith(7);
      expect(component.filteredUsers().map(u => u.id_role)).toEqual([42, 77]);
      expect(component.isRedacteurExterne(77)).toBe(true);
      expect(component.isRedacteurExterne(42)).toBe(false);
    });

    it('ne duplique pas un utilisateur présent dans les deux listes', async () => {
      redacteursInstance = [{ ...candidat, nom_organisme: 'X' }];
      const component = await setup();
      expect(component.filteredUsers().map(u => u.id_role)).toEqual([42]);
    });

    it('marque le rédacteur externe ajouté, même sans cocher la case', async () => {
      redacteursInstance = [bureau];
      const component = await setup();
      component.addUser(component.filteredUsers()[1]);
      expect(component.userAssignments()[0].user.is_redacteur_externe).toBe(true);
      component.setAddAsReferent(true);
      expect(component.userAssignments()[0].user.is_redacteur_externe).toBe(true);
    });
  });

  describe('#789 — référent sans ligne membre, dernier référent', () => {
    const sophie = { id_role: 5, email: 'sophie@rnf.fr', nom_complet: 'Sophie' };
    const membre = { id_role: 6, email: 'm@rnf.fr', referent: false };

    function confirmer(component: LinkPlanReferentModalComponent): jest.Mock {
      const open = jest.fn(() => ({ afterClosed: () => of(true) }));
      (component as any).dialog = { open };
      return open;
    }

    it('liste le référent absent des membres', async () => {
      const component = await setup([membre], [sophie]);
      expect(component.visibleAssignments.map(a => a.user.id_role)).toEqual([6, 5]);
      expect(component.visibleAssignments[1].user.referent).toBe(true);
    });

    it('alerte au retrait du dernier référent, puis retire', async () => {
      const component = await setup([], [sophie]);
      const open = confirmer(component);
      component.removeUser(component.userAssignments()[0]);
      expect(component.retireDernierReferent()).toBe(true);
      component.onSave();
      const { data } = (open.mock.calls[0] as any[])[1];
      expect(data.message).toContain('modals.linkPlanReferent.confirmRemove.lastReferent');
      expect(adminService['removeMemberFromPlan']).toHaveBeenCalledWith(7, 5);
    });

    it('alerte aussi quand le dernier référent repasse membre', async () => {
      const component = await setup([{ ...sophie, referent: true }, membre]);
      const open = confirmer(component);
      component.toggleReferent(component.userAssignments()[0]);
      component.onSave();
      expect(open).toHaveBeenCalled();
      const { data } = (open.mock.calls[0] as any[])[1];
      expect(data.title).toBe('modals.linkPlanReferent.confirmRemove.titleNoReferent');
    });

    it('pas d\'alerte s\'il reste un référent', async () => {
      const component = await setup([{ ...sophie, referent: true }, { ...membre, referent: true }]);
      component.removeUser(component.userAssignments()[0]);
      expect(component.retireDernierReferent()).toBe(false);
    });
  });
});
