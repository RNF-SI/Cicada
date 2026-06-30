import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';
import { planEditableGuard } from './plan-editable.guard';
import { AdminService } from '../../../../core/services/admin.service';

/**
 * #512 — Quand le plan n'est pas en brouillon, « Modifier l'action » depuis le
 * suivi doit rediriger vers la fiche de l'action (lecture seule), pas vers la
 * liste des enjeux.
 */
describe('planEditableGuard', () => {
  let adminService: { getPlanBySlug: jest.Mock };
  let router: { createUrlTree: jest.Mock };
  let snackBar: { open: jest.Mock };
  let translate: { instant: jest.Mock };

  const makeRoute = (params: Record<string, string>): ActivatedRouteSnapshot => ({
    paramMap: {
      get: (key: string) => params[key] ?? null,
    },
    parent: null,
  }) as unknown as ActivatedRouteSnapshot;

  const runGuard = (route: ActivatedRouteSnapshot) =>
    TestBed.runInInjectionContext(() => planEditableGuard(route, {} as never));

  beforeEach(() => {
    adminService = { getPlanBySlug: jest.fn() };
    // createUrlTree renvoie les commandes pour pouvoir asserter la cible.
    router = { createUrlTree: jest.fn((commands: unknown[]) => commands) };
    snackBar = { open: jest.fn() };
    translate = { instant: jest.fn((key: string) => key) };

    TestBed.configureTestingModule({
      providers: [
        { provide: AdminService, useValue: adminService },
        { provide: Router, useValue: router },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: TranslateService, useValue: translate },
      ],
    });
  });

  it('allows access when the plan is a draft', (done) => {
    adminService.getPlanBySlug.mockReturnValue(of({ statut: 'draft' }));

    (runGuard(makeRoute({ slug: 'plan-test', operationId: '42' })) as any).subscribe(
      (result: unknown) => {
        expect(result).toBe(true);
        done();
      },
    );
  });

  it('redirects to the read-only action when blocked on an operation edit route', (done) => {
    adminService.getPlanBySlug.mockReturnValue(of({ statut: 'valide' }));

    (runGuard(makeRoute({ slug: 'plan-test', operationId: '42' })) as any).subscribe(
      (result: unknown) => {
        expect(result).toEqual(['/plans', 'plan-test', 'enjeux', 'operations', '42']);
        expect(snackBar.open).toHaveBeenCalled();
        done();
      },
    );
  });

  it('redirects to the enjeux list when blocked without an operation', (done) => {
    adminService.getPlanBySlug.mockReturnValue(of({ statut: 'valide' }));

    (runGuard(makeRoute({ slug: 'plan-test' })) as any).subscribe((result: unknown) => {
      expect(result).toEqual(['/plans', 'plan-test', 'enjeux']);
      done();
    });
  });

  it('redirects to the read-only action when the plan lookup fails', (done) => {
    adminService.getPlanBySlug.mockReturnValue(throwError(() => new Error('boom')));

    (runGuard(makeRoute({ slug: 'plan-test', operationId: '42' })) as any).subscribe(
      (result: unknown) => {
        expect(result).toEqual(['/plans', 'plan-test', 'enjeux', 'operations', '42']);
        done();
      },
    );
  });

  it('redirects to /plans when no slug is found', () => {
    const result = runGuard(makeRoute({}));
    expect(result).toEqual(['/plans']);
  });
});
