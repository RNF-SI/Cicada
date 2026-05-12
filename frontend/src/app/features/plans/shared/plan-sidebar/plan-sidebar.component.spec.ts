import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ComponentRef } from '@angular/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';

import { PlanSidebarComponent } from './plan-sidebar.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
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
});
