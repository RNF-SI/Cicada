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

  async function setup(membres: any[] = []): Promise<LinkPlanReferentModalComponent> {
    adminService = {
      getUsers: jest.fn(() => of({ results: [candidat] })),
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
        { provide: MAT_DIALOG_DATA, useValue: { plan: { id_pg: 7, nom: 'Plan', membres } } },
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
});
