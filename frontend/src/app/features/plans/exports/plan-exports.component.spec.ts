import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { Observable, of, throwError } from 'rxjs';

import { Component } from '@angular/core';

import { PlanExportsComponent } from './plan-exports.component';
import { AdminService } from '../../../core/services/admin.service';
import { AuthService } from '../../../core/services/auth.service';
import { EnjeuService } from '../../../core/services/enjeu.service';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({});
  }
}

/** Header et sidebar sont testés ailleurs : on les neutralise ici. */
@Component({ selector: 'app-header', standalone: true, template: '' })
class MockHeaderComponent {}

@Component({
  selector: 'app-plan-sidebar',
  standalone: true,
  template: '',
  inputs: ['planId', 'planSlug', 'activePage', 'canManage', 'selectedEnjeuSlug'],
})
class MockPlanSidebarComponent {}

const mockPlan = { id_pg: 10, nom: 'Plan Test', slug: 'plan-test', referents: [] };

describe('PlanExportsComponent (#617)', () => {
  let fixture: ComponentFixture<PlanExportsComponent>;
  let component: PlanExportsComponent;
  let mockAdminService: any;
  let mockSnackBar: { open: jest.Mock };

  beforeEach(async () => {
    const blob = () => of(new Blob(['x']));
    mockAdminService = {
      getPlanBySlug: jest.fn().mockReturnValue(of(mockPlan)),
      getPlan: jest.fn().mockReturnValue(of(mockPlan)),
      downloadPlanDocx: jest.fn().mockImplementation(blob),
      downloadArborescencePresentation: jest.fn().mockImplementation(blob),
      downloadFichesActions: jest.fn().mockImplementation(blob),
      downloadBudgetPrevisionnel: jest.fn().mockImplementation(blob),
      downloadBudgetSuivi: jest.fn().mockImplementation(blob),
      downloadRhPrevisionnel: jest.fn().mockImplementation(blob),
      downloadRhSuivi: jest.fn().mockImplementation(blob),
      downloadArborescenceTemplate: jest.fn().mockImplementation(blob),
    };
    mockSnackBar = { open: jest.fn() };

    await TestBed.configureTestingModule({
      imports: [
        PlanExportsComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
        }),
      ],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AdminService, useValue: mockAdminService },
        { provide: MatSnackBar, useValue: mockSnackBar },
        {
          provide: AuthService,
          useValue: {
            isSuperAdmin: () => false,
            isRedacteurPrincipal: () => false,
            isAdminOrganisme: () => false,
            currentUser: () => ({ id: 42 }),
            isAuthenticated: () => true,
          },
        },
        {
          provide: EnjeuService,
          useValue: {
            getPlanEnjeux: jest.fn().mockReturnValue(of({ plan_id: 10, enjeux: [], fcr: [] })),
            currentPlanEnjeux: jest.fn().mockReturnValue(null),
          },
        },
        { provide: ActivatedRoute, useValue: { paramMap: of(new Map([['slug', 'plan-test']]) as any) } },
      ],
    })
      .overrideComponent(PlanExportsComponent, {
        remove: { imports: [HeaderComponent, PlanSidebarComponent] },
        add: { imports: [MockHeaderComponent, MockPlanSidebarComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(PlanExportsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    // Le download crée un <a> et appelle click() : neutralise l'API blob de jsdom.
    (URL as any).createObjectURL = jest.fn().mockReturnValue('blob:fake');
    (URL as any).revokeObjectURL = jest.fn();
  });

  it('charge le plan depuis le slug de la route', () => {
    expect(mockAdminService.getPlanBySlug).toHaveBeenCalledWith('plan-test');
    expect(component.planId()).toBe(10);
    expect(component.isLoading()).toBe(false);
  });

  it('rend les 8 exports du plan, sans condition de permission', () => {
    const testIds: string[] = Array.from(
      fixture.nativeElement.querySelectorAll('[data-testid]')
    ).map((el: any) => el.getAttribute('data-testid'));
    expect(testIds).toEqual(
      expect.arrayContaining([
        'plan-docx-export',
        'arbo-export-presentation',
        'fiches-actions-export',
        'budget-prev-export',
        'budget-suivi-export',
        'rh-prev-export',
        'rh-suivi-export',
        'arbo-export-prefilled',
      ])
    );
  });

  it('appelle le bon endpoint pour chaque export', () => {
    const byId = (id: string) =>
      fixture.nativeElement.querySelector(`[data-testid="${id}"]`) as HTMLButtonElement;

    byId('plan-docx-export').click();
    expect(mockAdminService.downloadPlanDocx).toHaveBeenCalledWith(10);

    byId('rh-suivi-export').click();
    expect(mockAdminService.downloadRhSuivi).toHaveBeenCalledWith(10);

    // Export du contenu = modèle pré-rempli (empty = false).
    byId('arbo-export-prefilled').click();
    expect(mockAdminService.downloadArborescenceTemplate).toHaveBeenCalledWith(10, false);
  });

  it('libère l\'indicateur de chargement et notifie en cas d\'erreur', () => {
    mockAdminService.downloadPlanDocx.mockReturnValue(throwError(() => new Error('boom')));
    const item = component.groups[0].items[0];
    component.download(item);
    expect(component.isDownloading(item.key)).toBe(false);
    expect(mockSnackBar.open).toHaveBeenCalled();
  });
});
