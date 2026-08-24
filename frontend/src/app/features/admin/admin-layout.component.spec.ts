import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, signal } from '@angular/core';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { AdminLayoutComponent } from './admin-layout.component';
import { AuthService } from '../../core/services/auth.service';
import { ErrorLogService } from '../../core/services/error-log.service';
import { OrphansService } from '../../core/services/orphans.service';
import { SystemUpdateService } from '../../core/services/system-update.service';
import { HeaderComponent } from '../../shared/components/header/header.component';

/** Le header est testé ailleurs : on le neutralise ici. */
@Component({ selector: 'app-header', standalone: true, template: '' })
class MockHeaderComponent {}

describe('AdminLayoutComponent — version de l\'application (#646)', () => {
  let fixture: ComponentFixture<AdminLayoutComponent>;
  let component: AdminLayoutComponent;
  let getAppVersion: jest.Mock;

  /**
   * @param niveau rôle de l'utilisateur connecté
   * @param version réponse de l'API version (null = échec ou non chargée)
   */
  async function setup(niveau: string, version: string | null = '0.1.48') {
    getAppVersion = jest.fn().mockReturnValue(of(version));

    await TestBed.resetTestingModule()
      .configureTestingModule({
        imports: [AdminLayoutComponent],
        providers: [
          provideRouter([]),
          provideHttpClient(),
          provideHttpClientTesting(),
          {
            provide: AuthService,
            useValue: {
              currentUser: signal({ id_role: 1, niveau_role: niveau, is_referent: false }),
              isSuperAdmin: () => niveau === 'super_admin',
              isAdminOrganisme: () => niveau === 'admin_og' || niveau === 'super_admin',
              isImpersonating: signal(false),
              impersonationInfo: signal(null),
              hasRole: (r: string) =>
                niveau === 'super_admin' || (niveau === 'admin_og' && r !== 'super_admin'),
              getUserDisplayName: () => 'Test',
              getOriginalUserDisplayName: () => 'Test',
            },
          },
          {
            provide: ErrorLogService,
            useValue: {
              unacknowledgedCount: signal(0),
              startAutoRefresh: jest.fn(),
              stopAutoRefresh: jest.fn(),
            },
          },
          {
            provide: OrphansService,
            useValue: {
              count: signal(0),
              startAutoRefresh: jest.fn(),
              stopAutoRefresh: jest.fn(),
            },
          },
          { provide: SystemUpdateService, useValue: { getAppVersion } },
        ],
      })
      .overrideComponent(AdminLayoutComponent, {
        remove: { imports: [HeaderComponent] },
        add: { imports: [MockHeaderComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(AdminLayoutComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('affiche la version en pied de sidebar pour un super admin', async () => {
    await setup('super_admin');

    expect(getAppVersion).toHaveBeenCalled();
    expect(component.appVersion()).toBe('0.1.48');
    const footer = fixture.nativeElement.querySelector('.sidebar-version');
    expect(footer.textContent.trim()).toBe('CICADA v0.1.48');
  });

  it('affiche aussi la version pour un admin organisme', async () => {
    await setup('admin_og');

    const footer = fixture.nativeElement.querySelector('.sidebar-version');
    expect(footer.textContent.trim()).toBe('CICADA v0.1.48');
  });

  it('n\'affiche rien plutôt qu\'un numéro faux quand l\'API échoue', async () => {
    await setup('super_admin', null);

    expect(component.appVersion()).toBeNull();
    expect(fixture.nativeElement.querySelector('.sidebar-version')).toBeNull();
  });

  it('expose l\'entrée « Mise à jour » au super admin', async () => {
    await setup('super_admin');

    const item = component.visibleNavItems().find(i => i.route === '/administration/mise-a-jour');
    expect(item).toBeDefined();
    expect(item!.label).toBe('Mise à jour');
  });

  it('masque l\'entrée « Mise à jour » à un admin organisme', async () => {
    await setup('admin_og');

    expect(
      component.visibleNavItems().some(i => i.route === '/administration/mise-a-jour')
    ).toBe(false);
  });
});
