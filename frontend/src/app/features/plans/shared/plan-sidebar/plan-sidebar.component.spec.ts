import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ComponentRef } from '@angular/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';

import { PlanSidebarComponent } from './plan-sidebar.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AdminService } from '../../../../core/services/admin.service';
import { PlanEnjeuxResponse, Enjeu } from '../../../../core/models/enjeu.model';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({
      plans: {
        sidebar: {
          overview: 'Vue d\'ensemble',
          enjeux: 'Enjeux & FCR',
        },
      },
      enjeux: {
        types: { enjeu: 'Enjeu', fcr: 'FCR' },
      },
    });
  }
}

const mockEnjeu: Enjeu = {
  id_enjeu: 1,
  id_pg: 10,
  id_categorie: 100,
  categorie_mnemonique: 'ENJEU',
  libelle: 'Protection zones humides',
  slug: 'protection-zones-humides',
  habitat: true,
  espece: false,
  patrimoine_geologique: false,
  geo_ex_situ: false,
  geo_in_situ: false,
  geo_documents: false,
  geo_autre: false,
  fonctionnalite_ecosysteme: false,
  autre_ecologique: false,
  processus: false,
  valeur_paysagere: false,
  patrimoine_culturel: false,
  developpement_durable: false,
  usages: false,
  valeur_ajoutee: false,
  autre_socioeco: false,
  date_ajout: '2024-01-01T00:00:00Z',
  date_maj: '2024-01-15T00:00:00Z',
};

const mockFcr: Enjeu = {
  id_enjeu: 2,
  id_pg: 10,
  id_categorie: 101,
  categorie_mnemonique: 'FCR',
  libelle: 'Connaissance scientifique',
  slug: 'connaissance-scientifique',
  habitat: false,
  espece: false,
  patrimoine_geologique: false,
  geo_ex_situ: false,
  geo_in_situ: false,
  geo_documents: false,
  geo_autre: false,
  fonctionnalite_ecosysteme: false,
  autre_ecologique: false,
  processus: false,
  valeur_paysagere: false,
  patrimoine_culturel: false,
  developpement_durable: false,
  usages: false,
  valeur_ajoutee: false,
  autre_socioeco: false,
  date_ajout: '2024-01-01T00:00:00Z',
  date_maj: '2024-01-01T00:00:00Z',
};

const mockPlanEnjeuxResponse: PlanEnjeuxResponse = {
  plan_id: 10,
  plan_nom: 'Plan Test',
  plan_slug: 'plan-test',
  enjeux: [mockEnjeu],
  fcr: [mockFcr],
  total_enjeux: 1,
  total_fcr: 1,
};

describe('PlanSidebarComponent', () => {
  let component: PlanSidebarComponent;
  let componentRef: ComponentRef<PlanSidebarComponent>;
  let fixture: ComponentFixture<PlanSidebarComponent>;
  let mockEnjeuService: { getPlanEnjeux: jest.Mock; currentPlanEnjeux: jest.Mock };
  let mockRouter: { navigate: jest.Mock };
  let mockAuthService: {
    isSuperAdmin: jest.Mock;
    isRedacteurPrincipal: jest.Mock;
    isAdminOrganisme: jest.Mock;
    currentUser: jest.Mock;
  };
  let mockAdminService: { getPlan: jest.Mock };

  beforeEach(async () => {
    // `currentPlanEnjeux()` retourne null avant le premier chargement —
    // le composant déclenche alors `getPlanEnjeux()` (qui alimente
    // ensuite le signal). Une fois `getPlanEnjeux` consommé, le test
    // surcharge le mock pour exposer la réponse aux `computed`.
    mockEnjeuService = {
      getPlanEnjeux: jest.fn().mockReturnValue(of(mockPlanEnjeuxResponse)),
      currentPlanEnjeux: jest.fn().mockReturnValue(mockPlanEnjeuxResponse),
    };
    // Force le 1er chargement : la sidebar appelle getPlanEnjeux seulement
    // si le cache n'a pas le plan demandé. On part de null pour les
    // assertions qui vérifient l'appel ; les tests qui lisent `enjeux()`
    // bénéficient quand même de la valeur pré-alimentée.

    mockRouter = {
      navigate: jest.fn(),
    };

    // Par défaut : simple utilisateur, non référent, aucun droit de gestion.
    mockAuthService = {
      isSuperAdmin: jest.fn().mockReturnValue(false),
      isRedacteurPrincipal: jest.fn().mockReturnValue(false),
      isAdminOrganisme: jest.fn().mockReturnValue(false),
      currentUser: jest.fn().mockReturnValue({ id: 42 }),
    };
    mockAdminService = {
      getPlan: jest.fn().mockReturnValue(of({ referents: [] })),
    };

    await TestBed.configureTestingModule({
      imports: [
        PlanSidebarComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
        }),
      ],
      providers: [
        { provide: EnjeuService, useValue: mockEnjeuService },
        { provide: Router, useValue: mockRouter },
        { provide: AuthService, useValue: mockAuthService },
        { provide: AdminService, useValue: mockAdminService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(PlanSidebarComponent);
    component = fixture.componentInstance;
    componentRef = fixture.componentRef;
    componentRef.setInput('planId', 10);
    componentRef.setInput('planSlug', 'plan-test');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should call getPlanEnjeux on init with planId when cache is empty', () => {
    // Cache vide → fetch déclenché. Avec le cache déjà alimenté, l'effect
    // skip volontairement l'appel (#228 — partage du signal service).
    mockEnjeuService.currentPlanEnjeux.mockReturnValueOnce(null);
    componentRef.setInput('planId', 20);  // change planId pour déclencher l'effect
    fixture.detectChanges();
    expect(mockEnjeuService.getPlanEnjeux).toHaveBeenCalledWith(20, true);
  });

  it('should populate enjeux signal from response', () => {
    expect(component.enjeux()).toEqual([mockEnjeu]);
  });

  it('should populate fcr signal from response', () => {
    expect(component.fcr()).toEqual([mockFcr]);
  });

  it('should start with parametrageMenuExpanded true', () => {
    expect(component.parametrageMenuExpanded()).toBe(true);
  });

  it('should toggle parametrageMenuExpanded', () => {
    component.toggleParametrageMenu();
    expect(component.parametrageMenuExpanded()).toBe(false);
    component.toggleParametrageMenu();
    expect(component.parametrageMenuExpanded()).toBe(true);
  });

  it('should flag parametrage as active on settings and postes pages', () => {
    componentRef.setInput('activePage', 'settings');
    fixture.detectChanges();
    expect(component.isParametrageActive()).toBe(true);
    componentRef.setInput('activePage', 'postes');
    fixture.detectChanges();
    expect(component.isParametrageActive()).toBe(true);
    componentRef.setInput('activePage', 'overview');
    fixture.detectChanges();
    expect(component.isParametrageActive()).toBe(false);
  });

  it('should start with detailsMenuExpanded true', () => {
    expect(component.detailsMenuExpanded()).toBe(true);
  });

  it('should toggle detailsMenuExpanded', () => {
    expect(component.detailsMenuExpanded()).toBe(true);
    component.toggleDetailsMenu();
    expect(component.detailsMenuExpanded()).toBe(false);
    component.toggleDetailsMenu();
    expect(component.detailsMenuExpanded()).toBe(true);
  });

  it('should navigate to overview', () => {
    component.navigateToOverview();
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/plans', 'plan-test']);
  });

  it('should navigate to enjeux list', () => {
    component.navigateToEnjeux();
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux']);
  });

  it('should navigate to enjeu detail on selectEnjeu', () => {
    component.selectEnjeu(mockEnjeu);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux', 'protection-zones-humides']);
  });

  // #583 — La section « Paramétrage » (Paramètres, Postes/RH) est le premier
  // item du menu, au-dessus de « Vue d'ensemble » qui redevient une entrée plate.
  describe('menu order (#583)', () => {
    it('renders Paramétrage first, then Vue d\'ensemble, for a manager', () => {
      componentRef.setInput('canManage', true);
      fixture.detectChanges();
      const labels: string[] = Array.from(
        fixture.nativeElement.querySelectorAll('.menu-item span')
      ).map((el: any) => el.textContent.trim());
      expect(labels[0]).toBe('plans.detail.sidebar.parametrage');
      expect(labels[1]).toBe('plans.detail.sidebar.overview');
    });

    it('nests Paramètres and Postes/RH under Paramétrage', () => {
      componentRef.setInput('canManage', true);
      fixture.detectChanges();
      const subLabels: string[] = Array.from(
        fixture.nativeElement.querySelectorAll('.menu-item-wrapper')[0].querySelectorAll('.submenu-item')
      ).map((el: any) => el.textContent.trim());
      expect(subLabels).toEqual(['plans.settings.openButton', 'plans.postes.sidebarEntry']);
    });

    it('hides the Paramétrage section for a non-manager', () => {
      componentRef.setInput('canManage', false);
      fixture.detectChanges();
      const labels: string[] = Array.from(
        fixture.nativeElement.querySelectorAll('.menu-item span')
      ).map((el: any) => el.textContent.trim());
      expect(labels).not.toContain('plans.detail.sidebar.parametrage');
      expect(labels[0]).toBe('plans.detail.sidebar.overview');
    });

    it('renders Vue d\'ensemble without a chevron (flat entry)', () => {
      componentRef.setInput('canManage', true);
      fixture.detectChanges();
      const overview = Array.from(
        fixture.nativeElement.querySelectorAll('.menu-item')
      ).find((el: any) => el.textContent.includes('plans.detail.sidebar.overview')) as HTMLElement;
      expect(overview.querySelector('.chevron')).toBeNull();
      expect(overview.classList).not.toContain('has-children');
    });
  });

  // #578 — Le sous-menu « Paramétrage » (Paramètres, Postes) doit être visible
  // sur toutes les pages du PG, sans que chaque page fournisse `canManage`.
  describe('effectiveCanManage (#578)', () => {
    it('honours an explicit canManage override (true) without fetching the plan', () => {
      mockAdminService.getPlan.mockClear();
      componentRef.setInput('canManage', true);
      fixture.detectChanges();
      expect(component.effectiveCanManage()).toBe(true);
      expect(mockAdminService.getPlan).not.toHaveBeenCalled();
    });

    it('honours an explicit canManage override (false) without fetching the plan', () => {
      mockAdminService.getPlan.mockClear();
      componentRef.setInput('canManage', false);
      fixture.detectChanges();
      expect(component.effectiveCanManage()).toBe(false);
      expect(mockAdminService.getPlan).not.toHaveBeenCalled();
    });

    it('grants management to an admin/super admin from role alone (no plan fetch)', () => {
      // `roleCanManage` est un computed : il fige sa valeur au 1er calcul. En
      // prod `isSuperAdmin` est un signal réactif ; ici le mock jest.fn() ne
      // l'est pas, donc on positionne le flag AVANT de créer le composant.
      mockAuthService.isSuperAdmin.mockReturnValue(true);
      mockAdminService.getPlan.mockClear();
      const fx = TestBed.createComponent(PlanSidebarComponent);
      fx.componentRef.setInput('planId', 30);
      fx.componentRef.setInput('planSlug', 'plan-test');
      fx.detectChanges();
      expect(fx.componentInstance.effectiveCanManage()).toBe(true);
      expect(mockAdminService.getPlan).not.toHaveBeenCalled();
    });

    it('grants management to a plain user who is a referent of the plan', () => {
      mockAdminService.getPlan.mockReturnValue(of({ referents: [{ id_role: 42 }] }));
      componentRef.setInput('planId', 31); // re-déclenche l'effect de fetch
      fixture.detectChanges();
      expect(mockAdminService.getPlan).toHaveBeenCalledWith(31);
      expect(component.effectiveCanManage()).toBe(true);
    });

    it('denies management to a plain user who is not a referent', () => {
      mockAdminService.getPlan.mockReturnValue(of({ referents: [{ id_role: 99 }] }));
      componentRef.setInput('planId', 32);
      fixture.detectChanges();
      expect(component.effectiveCanManage()).toBe(false);
    });
  });
});
