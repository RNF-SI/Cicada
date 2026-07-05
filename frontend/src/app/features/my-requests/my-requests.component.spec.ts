import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { RouterTestingModule } from '@angular/router/testing';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule } from '@ngx-translate/core';
import { of } from 'rxjs';

import { MyRequestsComponent } from './my-requests.component';
import { ValidationService } from '../../core/services/validation.service';
import { ModuleService } from '../../core/services/module.service';
import { ValidationRequestListItem } from '../../core/models/notification.model';

/**
 * Tests #467 — annulation d'une création de site.
 * Une demande `site_creation` déclenche une confirmation (suppression du site) ;
 * les autres types s'annulent directement.
 */
describe('MyRequestsComponent — cancel site creation (#467)', () => {
  let component: MyRequestsComponent;
  let fixture: ComponentFixture<MyRequestsComponent>;
  let validationService: { getMyRequests: jest.Mock; getRequestValidators: jest.Mock; cancelRequest: jest.Mock };
  let dialogOpen: jest.Mock;

  const makeRequest = (over: Partial<ValidationRequestListItem>): ValidationRequestListItem =>
    ({
      id: 1,
      request_type: 'site_access',
      status: 'pending',
      target_name: 'Mon site',
      ...over,
    } as ValidationRequestListItem);

  beforeEach(async () => {
    validationService = {
      getMyRequests: jest.fn().mockReturnValue(of([])),
      getRequestValidators: jest.fn().mockReturnValue(of({ validators: [] })),
      cancelRequest: jest.fn().mockReturnValue(of({ status: 'cancelled' })),
    };
    await TestBed.configureTestingModule({
      imports: [MyRequestsComponent, NoopAnimationsModule, RouterTestingModule, TranslateModule.forRoot()],
      providers: [
        { provide: ValidationService, useValue: validationService },
        { provide: ModuleService, useValue: { getModulesRequiringAccess: jest.fn().mockReturnValue(of([])) } },
        { provide: MatSnackBar, useValue: { open: jest.fn() } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MyRequestsComponent);
    component = fixture.componentInstance;
    // Remplace la référence MatDialog du composant par un mock contrôlable.
    dialogOpen = jest.fn();
    (component as unknown as { dialog: MatDialog }).dialog = { open: dialogOpen } as unknown as MatDialog;
  });

  it('opens a confirmation dialog for a site_creation request and cancels only if confirmed', () => {
    dialogOpen.mockReturnValue({ afterClosed: () => of(true) } as any);

    component.cancelRequest(makeRequest({ request_type: 'site_creation', id: 7 }));

    expect(dialogOpen).toHaveBeenCalledTimes(1);
    expect(validationService.cancelRequest).toHaveBeenCalledWith(7);
  });

  it('does not cancel a site_creation request if the confirmation is dismissed', () => {
    dialogOpen.mockReturnValue({ afterClosed: () => of(false) } as any);

    component.cancelRequest(makeRequest({ request_type: 'site_creation', id: 7 }));

    expect(dialogOpen).toHaveBeenCalledTimes(1);
    expect(validationService.cancelRequest).not.toHaveBeenCalled();
  });

  it('cancels a non-site_creation request directly without a confirmation dialog', () => {
    component.cancelRequest(makeRequest({ request_type: 'site_access', id: 3 }));

    expect(dialogOpen).not.toHaveBeenCalled();
    expect(validationService.cancelRequest).toHaveBeenCalledWith(3);
  });

  it('ignores non-pending requests', () => {
    component.cancelRequest(makeRequest({ request_type: 'site_creation', status: 'approved' }));

    expect(dialogOpen).not.toHaveBeenCalled();
    expect(validationService.cancelRequest).not.toHaveBeenCalled();
  });
});
