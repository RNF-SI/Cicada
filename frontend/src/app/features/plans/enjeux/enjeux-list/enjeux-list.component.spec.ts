import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { RouterTestingModule } from '@angular/router/testing';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { Observable, of, throwError, Subject } from 'rxjs';

import { EnjeuxListComponent } from './enjeux-list.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import {
  Enjeu, PlanEnjeuxResponse, FacteurInfluence, Pression,
  ObjectifLongTerme, EtatActuel, NiveauExigence, Indicateur,
  ObjectifOperationnel, ResultatAttendu
} from '../../../../core/models/enjeu.model';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({
      enjeux: {
        types: { enjeu: 'Enjeu', fcr: 'FCR' },
        enjeuForm: {
          ecologique: 'Écologique',
          socioEconomique: 'Socio-économique',
          habitat: 'Un/des habitat(s)',
          espece: 'Une/des espèce(s)',
          patrimoineGeologique: 'Du patrimoine géologique',
          fonctionnaliteEcosysteme: 'Fonctionnalité écosystème',
          autreEcologique: 'Autre',
          valeurPaysagere: 'Valeur paysagère',
          patrimoineCulturel: 'Patrimoine culturel',
          developpementDurable: 'Développement durable',
          usages: 'Usages',
          valeurAjoutee: 'Valeur ajoutée',
          autreSocioEco: 'Autre socio-éco',
        },
        accordion: {
          habitats: 'Habitats',
          especes: 'Espèces',
          processus: 'Processus',
        },
        facteurInfluence: {
          createSuccess: 'Facteur créé',
          updateSuccess: 'Facteur mis à jour',
          deleteTitle: 'Supprimer le facteur',
          deleteConfirm: 'Confirmer suppression ?',
          deleteSuccess: 'Facteur supprimé',
        },
        pression: {
          createSuccess: 'Pression créée',
          updateSuccess: 'Pression mise à jour',
          deleteTitle: 'Supprimer la pression',
          deleteConfirm: 'Confirmer suppression ?',
          deleteSuccess: 'Pression supprimée',
        },
        etatActuel: {
          createSuccess: 'État actuel créé',
          updateSuccess: 'État actuel mis à jour',
          deleteTitle: 'Supprimer l\'état actuel',
          deleteConfirm: 'Confirmer suppression ?',
          deleteSuccess: 'État actuel supprimé',
        },
        olt: {
          createSuccess: 'OLT créé',
          updateSuccess: 'OLT mis à jour',
          deleteTitle: 'Supprimer l\'OLT',
          deleteConfirm: 'Confirmer suppression ?',
          deleteSuccess: 'OLT supprimé',
        },
        niveauExigence: {
          createSuccess: 'NE créé',
          updateSuccess: 'NE mis à jour',
          deleteTitle: 'Supprimer le NE',
          deleteConfirm: 'Confirmer suppression ?',
          deleteSuccess: 'NE supprimé',
        },
        indicateurs: {
          createSuccess: 'Indicateur créé',
          updateSuccess: 'Indicateur mis à jour',
          deleteConfirm: 'Confirmer suppression ?',
          deleteSuccess: 'Indicateur supprimé',
        },
        indicateur: {
          createSuccess: 'Indicateur créé',
        },
        metriques: {
          deleteSuccess: 'Métrique supprimée',
          partialError: 'Erreur partielle métriques',
        },
        oo: {
          createSuccess: 'OO créé',
          updateSuccess: 'OO mis à jour',
          deleteTitle: 'Supprimer l\'OO',
          deleteConfirm: 'Confirmer suppression ?',
          deleteSuccess: 'OO supprimé',
        },
        resultatAttendu: {
          createSuccess: 'RA créé',
          updateSuccess: 'RA mis à jour',
          deleteTitle: 'Supprimer le RA',
          deleteConfirm: 'Confirmer suppression ?',
          deleteSuccess: 'RA supprimé',
        },
        messages: {
          loadError: 'Erreur de chargement',
          createError: 'Erreur de création',
          updateError: 'Erreur de mise à jour',
          deleteError: 'Erreur de suppression',
        },
      },
      common: {
        actions: {
          delete: 'Supprimer',
          cancel: 'Annuler',
          close: 'Fermer',
        },
        loading: 'Chargement...',
      },
    });
  }
}

const mockEnjeu1: Enjeu = {
  id_enjeu: 1,
  id_pg: 10,
  id_categorie: 100,
  categorie_mnemonique: 'ENJEU',
  libelle: 'Protection zones humides',
  slug: 'protection-zones-humides',
  rang: 1,
  categorie_ecologique: true,
  habitat: true,
  espece: true,
  processus: false,
  patrimoine_geologique: false,
  geo_ex_situ: false,
  geo_in_situ: false,
  fonctionnalite_ecosysteme: false,
  autre_ecologique: false,
  valeur_paysagere: false,
  patrimoine_culturel: false,
  developpement_durable: false,
  usages: false,
  valeur_ajoutee: false,
  autre_socioeco: false,
  nb_facteurs_influence: 2,
  facteurs_influence: [
    {
      id_facteur_influence: 101, id_enjeu: 1, libelle: 'Urbanisation', date_ajout: '', date_maj: '',
      pressions: [
        {
          id_pression: 301, id_facteur_influence: 101, libelle: 'Pression Urbaine', date_ajout: '', date_maj: '',
          objectifs_operationnels: [
            {
              id_oo: 1001, id_pression: 301, libelle: 'OO Test', date_ajout: '', date_maj: '',
              resultats_attendus: [
                { id_ra: 1101, id_oo: 1001, libelle: 'RA Test', date_ajout: '', date_maj: '' }
              ]
            }
          ],
          nb_objectifs_operationnels: 1,
        }
      ],
      nb_pressions: 1,
    },
    { id_facteur_influence: 102, id_enjeu: 1, libelle: 'Agriculture', date_ajout: '', date_maj: '' },
  ],
  date_ajout: '2024-01-01T00:00:00Z',
  date_maj: '2024-01-15T00:00:00Z',
};

const mockEnjeu2: Enjeu = {
  id_enjeu: 3,
  id_pg: 10,
  id_categorie: 100,
  categorie_mnemonique: 'ENJEU',
  libelle: 'Biodiversité aquatique',
  slug: 'biodiversite-aquatique',
  rang: 2,
  categorie_ecologique: false,
  habitat: false,
  espece: true,
  processus: true,
  patrimoine_geologique: false,
  geo_ex_situ: false,
  geo_in_situ: false,
  fonctionnalite_ecosysteme: false,
  autre_ecologique: false,
  valeur_paysagere: false,
  patrimoine_culturel: false,
  developpement_durable: false,
  usages: false,
  valeur_ajoutee: false,
  autre_socioeco: false,
  date_ajout: '2024-02-01T00:00:00Z',
  date_maj: '2024-02-15T00:00:00Z',
};

const mockFcr: Enjeu = {
  id_enjeu: 2,
  id_pg: 10,
  id_categorie: 101,
  categorie_mnemonique: 'FCR',
  libelle: 'Connaissance scientifique',
  slug: 'connaissance-scientifique',
  categorie_fcr_label: 'Connaissance',
  habitat: false,
  espece: false,
  processus: false,
  patrimoine_geologique: false,
  geo_ex_situ: false,
  geo_in_situ: false,
  fonctionnalite_ecosysteme: false,
  autre_ecologique: false,
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
  enjeux: [mockEnjeu1, mockEnjeu2],
  fcr: [mockFcr],
  total_enjeux: 2,
  total_fcr: 1,
};

describe('EnjeuxListComponent', () => {
  let component: EnjeuxListComponent;
  let fixture: ComponentFixture<EnjeuxListComponent>;
  let router: Router;
  let translate: TranslateService;
  let mockSnackBarOpen: jest.SpyInstance;
  let mockDialogOpen: jest.SpyInstance;
  let mockEnjeuService: {
    [key: string]: jest.Mock;
    getPlanEnjeux: jest.Mock;
    deleteEnjeu: jest.Mock;
    createFacteurInfluence: jest.Mock;
    updateFacteurInfluence: jest.Mock;
    deleteFacteurInfluence: jest.Mock;
    createPression: jest.Mock;
    updatePression: jest.Mock;
    deletePression: jest.Mock;
    createEtatActuel: jest.Mock;
    updateEtatActuel: jest.Mock;
    deleteEtatActuel: jest.Mock;
    createObjectifLongTerme: jest.Mock;
    updateObjectifLongTerme: jest.Mock;
    deleteObjectifLongTerme: jest.Mock;
    createNiveauExigence: jest.Mock;
    updateNiveauExigence: jest.Mock;
    deleteNiveauExigence: jest.Mock;
    createIndicateur: jest.Mock;
    updateIndicateur: jest.Mock;
    deleteIndicateur: jest.Mock;
    createMetrique: jest.Mock;
    updateMetrique: jest.Mock;
    deleteMetrique: jest.Mock;
    createObjectifOperationnel: jest.Mock;
    updateObjectifOperationnel: jest.Mock;
    deleteObjectifOperationnel: jest.Mock;
    createResultatAttendu: jest.Mock;
    updateResultatAttendu: jest.Mock;
    deleteResultatAttendu: jest.Mock;
  };
  let mockAdminService: { getPlanBySlug: jest.Mock; getNomenclaturesByType: jest.Mock };
  let routeParamsSubject: Subject<any>;

  function setup(parentParams: Record<string, string> = { slug: 'plan-test' }, routeParams: Record<string, string> = {}): void {
    routeParamsSubject = new Subject<any>();

    mockEnjeuService = {
      getPlanEnjeux: jest.fn().mockReturnValue(of(mockPlanEnjeuxResponse)),
      deleteEnjeu: jest.fn().mockReturnValue(of(void 0)),
      // Facteurs
      createFacteurInfluence: jest.fn().mockReturnValue(of({ id_facteur_influence: 999, id_enjeu: 1, libelle: 'Nouveau', date_ajout: '', date_maj: '' })),
      updateFacteurInfluence: jest.fn().mockReturnValue(of({ id_facteur_influence: 101, id_enjeu: 1, libelle: 'Modifié', date_ajout: '', date_maj: '' })),
      deleteFacteurInfluence: jest.fn().mockReturnValue(of(void 0)),
      // Pressions
      createPression: jest.fn().mockReturnValue(of({ id_pression: 888, id_facteur_influence: 101, libelle: 'Nouvelle', date_ajout: '', date_maj: '' })),
      updatePression: jest.fn().mockReturnValue(of({ id_pression: 301, id_facteur_influence: 101, libelle: 'Modifiée', date_ajout: '', date_maj: '' })),
      deletePression: jest.fn().mockReturnValue(of(void 0)),
      // États actuels
      createEtatActuel: jest.fn().mockReturnValue(of({ id_etat_actuel: 602, id_enjeu: 1, libelle: 'Nouvel état', date_ajout: '', date_maj: '' })),
      updateEtatActuel: jest.fn().mockReturnValue(of({ id_etat_actuel: 601, id_enjeu: 1, libelle: 'État modifié', date_ajout: '', date_maj: '' })),
      deleteEtatActuel: jest.fn().mockReturnValue(of(void 0)),
      // OLT
      createObjectifLongTerme: jest.fn().mockReturnValue(of({ id_olt: 502, id_etat_actuel: 601, libelle: 'Nouvel OLT', date_ajout: '', date_maj: '' })),
      updateObjectifLongTerme: jest.fn().mockReturnValue(of({ id_olt: 501, id_etat_actuel: 601, libelle: 'OLT modifié', date_ajout: '', date_maj: '' })),
      deleteObjectifLongTerme: jest.fn().mockReturnValue(of(void 0)),
      // Niveaux d'exigence
      createNiveauExigence: jest.fn().mockReturnValue(of({ id_ne: 702, id_olt: 501, libelle: 'Nouveau NE', date_ajout: '', date_maj: '' })),
      updateNiveauExigence: jest.fn().mockReturnValue(of({ id_ne: 701, id_olt: 501, libelle: 'NE modifié', date_ajout: '', date_maj: '' })),
      deleteNiveauExigence: jest.fn().mockReturnValue(of(void 0)),
      // Indicateurs
      createIndicateur: jest.fn().mockReturnValue(of({ id_indicateur: 802, id_ne: 701, nom_indicateur: 'Nouvel ind', est_standardise: false, date_ajout: '', date_maj: '' })),
      updateIndicateur: jest.fn().mockReturnValue(of({ id_indicateur: 801, id_ne: 701, nom_indicateur: 'Ind modifié', est_standardise: false, date_ajout: '', date_maj: '' })),
      deleteIndicateur: jest.fn().mockReturnValue(of(void 0)),
      // Métriques
      createMetrique: jest.fn().mockReturnValue(of({ id_metrique: 902, id_indicateur: 801, nom_metrique: 'Nouvelle met', date_ajout: '', date_maj: '' })),
      updateMetrique: jest.fn().mockReturnValue(of({ id_metrique: 901, id_indicateur: 801, nom_metrique: 'Met modifiée', date_ajout: '', date_maj: '' })),
      deleteMetrique: jest.fn().mockReturnValue(of(void 0)),
      // OO
      createObjectifOperationnel: jest.fn().mockReturnValue(of({ id_oo: 1002, id_pression: 301, libelle: 'Nouvel OO', date_ajout: '', date_maj: '' })),
      updateObjectifOperationnel: jest.fn().mockReturnValue(of({ id_oo: 1001, id_pression: 301, libelle: 'OO modifié', date_ajout: '', date_maj: '' })),
      deleteObjectifOperationnel: jest.fn().mockReturnValue(of(void 0)),
      // RA
      createResultatAttendu: jest.fn().mockReturnValue(of({ id_ra: 1102, id_oo: 1001, libelle: 'Nouveau RA', date_ajout: '', date_maj: '' })),
      updateResultatAttendu: jest.fn().mockReturnValue(of({ id_ra: 1101, id_oo: 1001, libelle: 'RA modifié', date_ajout: '', date_maj: '' })),
      deleteResultatAttendu: jest.fn().mockReturnValue(of(void 0)),
    };
    mockAdminService = {
      getPlanBySlug: jest.fn().mockReturnValue(of({ id_pg: 10, nom: 'Plan Test', annee_debut: null, annee_fin: null })),
      getNomenclaturesByType: jest.fn().mockReturnValue(of([])),
    };

    const activatedRoute = {
      snapshot: {
        paramMap: {
          get: (key: string) => routeParams[key] || null,
        },
      },
      parent: {
        snapshot: {
          paramMap: {
            get: (key: string) => parentParams[key] || null,
          },
        },
      },
      params: routeParamsSubject.asObservable(),
    };

    TestBed.configureTestingModule({
      imports: [
        EnjeuxListComponent,
        NoopAnimationsModule,
        HttpClientTestingModule,
        RouterTestingModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
        }),
      ],
      providers: [
        { provide: ActivatedRoute, useValue: activatedRoute },
        { provide: EnjeuService, useValue: mockEnjeuService },
        { provide: AdminService, useValue: mockAdminService },
      ],
    }).compileComponents();

    router = TestBed.inject(Router);
    jest.spyOn(router, 'navigate').mockResolvedValue(true);
    mockSnackBarOpen = jest.spyOn(MatSnackBar.prototype, 'open').mockImplementation();
    translate = TestBed.inject(TranslateService);
    translate.use('fr');

    fixture = TestBed.createComponent(EnjeuxListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  afterEach(() => {
    mockSnackBarOpen?.mockRestore();
    mockDialogOpen?.mockRestore();
  });

  // =========================================================================
  // Initialization and signals
  // =========================================================================

  describe('initialization', () => {
    it('should create', () => {
      setup();
      expect(component).toBeTruthy();
    });

    it('should load planSlug from parent route', () => {
      setup();
      expect(component.planSlug()).toBe('plan-test');
    });

    it('should call loadPlanData on init', () => {
      setup();
      expect(mockAdminService.getPlanBySlug).toHaveBeenCalledWith('plan-test');
      expect(mockEnjeuService.getPlanEnjeux).toHaveBeenCalledWith(10, true);
    });

    it('should set isLoading false after data loaded', () => {
      setup();
      expect(component.isLoading()).toBe(false);
    });

    it('should set errorMessage if no planSlug', () => {
      setup({});
      expect(component.errorMessage()).toBe('Slug du plan non trouvé');
      expect(component.isLoading()).toBe(false);
    });

    it('should set selectedEnjeuSlug from route params', () => {
      setup();
      routeParamsSubject.next({ enjeuSlug: 'protection-zones-humides' });
      expect(component.selectedEnjeuSlug()).toBe('protection-zones-humides');
    });

    it('should clear selectedEnjeuSlug when no enjeuSlug in route', () => {
      setup();
      routeParamsSubject.next({ enjeuSlug: 'protection-zones-humides' });
      expect(component.selectedEnjeuSlug()).toBe('protection-zones-humides');
      routeParamsSubject.next({});
      expect(component.selectedEnjeuSlug()).toBeNull();
    });
  });

  // =========================================================================
  // Computed properties
  // =========================================================================

  describe('computed properties', () => {
    beforeEach(() => setup());

    it('should compute enjeux from planEnjeuxData', () => {
      expect(component.enjeux().length).toBe(2);
      expect(component.enjeux()[0].libelle).toBe('Protection zones humides');
    });

    it('should compute fcr from planEnjeuxData', () => {
      expect(component.fcr().length).toBe(1);
      expect(component.fcr()[0].libelle).toBe('Connaissance scientifique');
    });

    it('should compute totalCount', () => {
      expect(component.totalCount()).toBe(3); // 2 enjeux + 1 fcr
    });

    it('should compute hasData', () => {
      expect(component.hasData()).toBe(true);
    });

    it('should return empty arrays when no data', () => {
      component['planEnjeuxData'].set(null);
      expect(component.enjeux()).toEqual([]);
      expect(component.fcr()).toEqual([]);
      expect(component.totalCount()).toBe(0);
      expect(component.hasData()).toBe(false);
    });

    it('should find selectedEnjeu from enjeux list', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      expect(component.selectedEnjeu()?.libelle).toBe('Protection zones humides');
    });

    it('should find selectedEnjeu from fcr list', () => {
      component['selectedEnjeuSlug'].set('connaissance-scientifique');
      expect(component.selectedEnjeu()?.libelle).toBe('Connaissance scientifique');
    });

    it('should return null selectedEnjeu when no slug', () => {
      component['selectedEnjeuSlug'].set(null);
      expect(component.selectedEnjeu()).toBeNull();
    });
  });

  // =========================================================================
  // Detail computed properties
  // =========================================================================

  describe('detail computed properties', () => {
    beforeEach(() => setup());

    it('should compute isSelectedFcr', () => {
      component['selectedEnjeuSlug'].set('connaissance-scientifique');
      expect(component.isSelectedFcr()).toBe(true);

      component['selectedEnjeuSlug'].set('protection-zones-humides');
      expect(component.isSelectedFcr()).toBe(false);
    });

    it('should compute selectedCategoryLabel for ecologique', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      const label = component.selectedCategoryLabel();
      expect(label).toBe('Écologique');
    });

    it('should compute selectedCategoryLabel for socio-economique', () => {
      component['selectedEnjeuSlug'].set('biodiversite-aquatique');
      const label = component.selectedCategoryLabel();
      expect(label).toBe('Socio-économique');
    });

    it('should compute selectedTypeLabels', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      const labels = component.selectedTypeLabels();
      expect(labels).toContain('Un/des habitat(s)');
      expect(labels).toContain('Une/des espèce(s)');
      expect(labels).not.toContain('Processus');
    });

    it('should compute selectedHasTaxons', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      expect(component.selectedHasTaxons()).toBe(false);
    });

    it('should compute selectedDisplayIndex for enjeu', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      expect(component.selectedDisplayIndex()).toBe(1);

      component['selectedEnjeuSlug'].set('biodiversite-aquatique');
      expect(component.selectedDisplayIndex()).toBe(2);
    });

    it('should compute selectedDisplayIndex for fcr', () => {
      component['selectedEnjeuSlug'].set('connaissance-scientifique');
      expect(component.selectedDisplayIndex()).toBe(1);
    });

    it('should return 0 for selectedDisplayIndex when no selection', () => {
      component['selectedEnjeuSlug'].set(null);
      expect(component.selectedDisplayIndex()).toBe(0);
    });

    it('should compute selectedFcrCategoryLabel', () => {
      component['selectedEnjeuSlug'].set('connaissance-scientifique');
      expect(component.selectedFcrCategoryLabel()).toBe('Connaissance');
    });
  });

  // =========================================================================
  // Navigation
  // =========================================================================

  describe('navigation', () => {
    beforeEach(() => setup());

    it('should navigate to new enjeu', () => {
      component.navigateToNewEnjeu();
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux', 'nouveau']);
    });

    it('should navigate to new FCR', () => {
      component.navigateToNewFcr();
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux', 'fcr', 'nouveau']);
    });

    it('should navigate to edit enjeu', () => {
      component.navigateToEdit(mockEnjeu1);
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux', 'protection-zones-humides', 'modifier']);
    });

    it('should navigate to edit FCR', () => {
      component.navigateToEdit(mockFcr);
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux', 'fcr', 2, 'modifier']);
    });

    it('should navigate to enjeu detail', () => {
      component.navigateToEnjeuDetail(mockEnjeu1);
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux', 'protection-zones-humides']);
    });
  });

  // =========================================================================
  // Tab and expand/collapse
  // =========================================================================

  describe('tabs and expand/collapse', () => {
    beforeEach(() => setup());

    it('should set active tab', () => {
      component.setActiveTab('olt');
      expect(component.activeTab()).toBe('olt');
      component.setActiveTab('operations');
      expect(component.activeTab()).toBe('operations');
    });

    it('should toggle enjeu detail expanded', () => {
      expect(component.enjeuDetailExpanded()).toBe(true);
      component.toggleEnjeuDetail();
      expect(component.enjeuDetailExpanded()).toBe(false);
    });

    it('should toggle FCR expanded', () => {
      expect(component.isFcrExpanded(2)).toBe(false);
      component.toggleFcr(2);
      expect(component.isFcrExpanded(2)).toBe(true);
      component.toggleFcr(2);
      expect(component.isFcrExpanded(2)).toBe(false);
    });
  });

  // =========================================================================
  // Delete enjeu
  // =========================================================================

  describe('delete enjeu', () => {
    beforeEach(() => setup());

    it('should call deleteEnjeu and reload on success', () => {
      const callsBefore = mockEnjeuService.getPlanEnjeux.mock.calls.length;
      component.onEnjeuDelete(mockEnjeu1);
      expect(mockEnjeuService.deleteEnjeu).toHaveBeenCalledWith(1);
      // loadPlanData is called again after delete
      expect(mockEnjeuService.getPlanEnjeux.mock.calls.length).toBeGreaterThan(callsBefore);
    });

    it('should navigate back to list if deleted enjeu was selected', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.onEnjeuDelete(mockEnjeu1);
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux']);
    });

    it('should set errorMessage on delete error', () => {
      mockEnjeuService.deleteEnjeu.mockReturnValue(throwError(() => new Error('fail')));
      component.onEnjeuDelete(mockEnjeu1);
      expect(component.errorMessage()).toBeTruthy();
    });
  });

  // =========================================================================
  // Facteurs d'influence
  // =========================================================================

  describe('facteurs d\'influence', () => {
    beforeEach(() => setup());

    it('should toggle facteur expanded state', () => {
      expect(component.isFacteurExpanded(101)).toBe(false);
      component.toggleFacteur(101);
      expect(component.isFacteurExpanded(101)).toBe(true);
      component.toggleFacteur(101);
      expect(component.isFacteurExpanded(101)).toBe(false);
    });

    it('should start adding facteur', () => {
      component.startAddFacteur();
      expect(component.addingFacteurInfluence()).toBe(true);
      expect(component.newFacteurLibelle).toBe('');
    });

    it('should cancel adding facteur', () => {
      component.startAddFacteur();
      component.newFacteurLibelle = 'Test';
      component.cancelAddFacteur();
      expect(component.addingFacteurInfluence()).toBe(false);
      expect(component.newFacteurLibelle).toBe('');
    });

    it('should call createFacteurInfluence on save', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newFacteurLibelle = 'Nouveau facteur';
      component.newFacteurDescription = 'Description';
      component.saveFacteurInfluence();

      expect(mockEnjeuService.createFacteurInfluence).toHaveBeenCalledWith({
        id_enjeu: 1,
        libelle: 'Nouveau facteur',
        description: 'Description',
      });
    });

    it('should not save facteur with empty libelle', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newFacteurLibelle = '   ';
      component.saveFacteurInfluence();
      expect(mockEnjeuService.createFacteurInfluence).not.toHaveBeenCalled();
    });

    it('should open confirm dialog on delete facteur', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);

      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        date_ajout: '',
        date_maj: '',
      };
      component.deleteFacteur(facteur);
      expect(mockDialogOpen).toHaveBeenCalled();
    });

    it('should call deleteFacteurInfluence after confirm', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);

      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        date_ajout: '',
        date_maj: '',
      };
      component.deleteFacteur(facteur);
      expect(mockEnjeuService.deleteFacteurInfluence).toHaveBeenCalledWith(101);
    });

    it('should not call deleteFacteurInfluence when dialog cancelled', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);

      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        date_ajout: '',
        date_maj: '',
      };
      component.deleteFacteur(facteur);
      expect(mockEnjeuService.deleteFacteurInfluence).not.toHaveBeenCalled();
    });

    it('should start editing facteur with pre-filled values', () => {
      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        description: 'Expansion urbaine',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditFacteur(facteur);
      expect(component.editingFacteurId()).toBe(101);
      expect(component.editFacteurLibelle).toBe('Urbanisation');
      expect(component.editFacteurDescription).toBe('Expansion urbaine');
    });

    it('should cancel editing facteur and reset fields', () => {
      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditFacteur(facteur);
      component.cancelEditFacteur();
      expect(component.editingFacteurId()).toBeNull();
      expect(component.editFacteurLibelle).toBe('');
      expect(component.editFacteurDescription).toBe('');
    });

    it('should call updateFacteurInfluence on save', () => {
      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditFacteur(facteur);
      component.editFacteurLibelle = 'Urbanisation modifiée';
      component.editFacteurDescription = 'Nouvelle desc';
      component.saveEditFacteur(facteur);

      expect(mockEnjeuService.updateFacteurInfluence).toHaveBeenCalledWith(101, {
        libelle: 'Urbanisation modifiée',
        description: 'Nouvelle desc',
      });
    });

    it('should not save edit facteur with empty libelle', () => {
      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditFacteur(facteur);
      component.editFacteurLibelle = '   ';
      component.saveEditFacteur(facteur);
      expect(mockEnjeuService.updateFacteurInfluence).not.toHaveBeenCalled();
    });

    it('should reset editing state after successful update', () => {
      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditFacteur(facteur);
      component.editFacteurLibelle = 'Modifié';
      component.saveEditFacteur(facteur);
      expect(component.editingFacteurId()).toBeNull();
    });

    it('should set errorMessage on update facteur error', () => {
      mockEnjeuService.updateFacteurInfluence.mockReturnValue(throwError(() => new Error('Update failed')));
      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditFacteur(facteur);
      component.editFacteurLibelle = 'Modifié';
      component.saveEditFacteur(facteur);
      expect(component.errorMessage()).toBeTruthy();
    });
  });

  // =========================================================================
  // Pressions
  // =========================================================================

  describe('pressions', () => {
    beforeEach(() => setup());

    it('should toggle pression expanded state', () => {
      expect(component.isPressionExpanded(201)).toBe(false);
      component.togglePression(201);
      expect(component.isPressionExpanded(201)).toBe(true);
      component.togglePression(201);
      expect(component.isPressionExpanded(201)).toBe(false);
    });

    it('should start adding pression for facteur', () => {
      component.startAddPression(101);
      expect(component.addingPressionForFacteur()).toBe(101);
      expect(component.newPressionLibelle).toBe('');
    });

    it('should cancel adding pression', () => {
      component.startAddPression(101);
      component.newPressionLibelle = 'Test';
      component.cancelAddPression();
      expect(component.addingPressionForFacteur()).toBeNull();
      expect(component.newPressionLibelle).toBe('');
    });

    it('should call createPression on save', () => {
      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        date_ajout: '',
        date_maj: '',
      };
      component.newPressionLibelle = 'Nouvelle pression';
      component.newPressionDescription = 'Desc';
      component.savePression(facteur);

      expect(mockEnjeuService.createPression).toHaveBeenCalledWith({
        id_facteur_influence: 101,
        libelle: 'Nouvelle pression',
        description: 'Desc',
      });
    });

    it('should not save pression with empty libelle', () => {
      const facteur: FacteurInfluence = {
        id_facteur_influence: 101,
        id_enjeu: 1,
        libelle: 'Urbanisation',
        date_ajout: '',
        date_maj: '',
      };
      component.newPressionLibelle = '   ';
      component.savePression(facteur);
      expect(mockEnjeuService.createPression).not.toHaveBeenCalled();
    });

    it('should call deletePression after confirm', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);

      const pression: Pression = {
        id_pression: 301,
        id_facteur_influence: 101,
        libelle: 'Pression test',
        date_ajout: '',
        date_maj: '',
      };
      component.deletePression(pression);
      expect(mockEnjeuService.deletePression).toHaveBeenCalledWith(301);
    });

    it('should not delete pression when dialog cancelled', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);

      const pression: Pression = {
        id_pression: 301,
        id_facteur_influence: 101,
        libelle: 'Pression test',
        date_ajout: '',
        date_maj: '',
      };
      component.deletePression(pression);
      expect(mockEnjeuService.deletePression).not.toHaveBeenCalled();
    });

    it('should start editing pression with pre-filled values', () => {
      const pression: Pression = {
        id_pression: 301,
        id_facteur_influence: 101,
        libelle: 'Pression test',
        description: 'Description pression',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditPression(pression);
      expect(component.editingPressionId()).toBe(301);
      expect(component.editPressionLibelle).toBe('Pression test');
      expect(component.editPressionDescription).toBe('Description pression');
    });

    it('should cancel editing pression and reset fields', () => {
      const pression: Pression = {
        id_pression: 301,
        id_facteur_influence: 101,
        libelle: 'Pression test',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditPression(pression);
      component.cancelEditPression();
      expect(component.editingPressionId()).toBeNull();
      expect(component.editPressionLibelle).toBe('');
      expect(component.editPressionDescription).toBe('');
    });

    it('should call updatePression on save', () => {
      const pression: Pression = {
        id_pression: 301,
        id_facteur_influence: 101,
        libelle: 'Pression test',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditPression(pression);
      component.editPressionLibelle = 'Pression modifiée';
      component.editPressionDescription = 'Nouvelle desc';
      component.saveEditPression(pression);

      expect(mockEnjeuService.updatePression).toHaveBeenCalledWith(301, {
        libelle: 'Pression modifiée',
        description: 'Nouvelle desc',
      });
    });

    it('should not save edit pression with empty libelle', () => {
      const pression: Pression = {
        id_pression: 301,
        id_facteur_influence: 101,
        libelle: 'Pression test',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditPression(pression);
      component.editPressionLibelle = '   ';
      component.saveEditPression(pression);
      expect(mockEnjeuService.updatePression).not.toHaveBeenCalled();
    });

    it('should reset editing state after successful pression update', () => {
      const pression: Pression = {
        id_pression: 301,
        id_facteur_influence: 101,
        libelle: 'Pression test',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditPression(pression);
      component.editPressionLibelle = 'Modifiée';
      component.saveEditPression(pression);
      expect(component.editingPressionId()).toBeNull();
    });

    it('should set errorMessage on update pression error', () => {
      mockEnjeuService.updatePression.mockReturnValue(throwError(() => new Error('Update failed')));
      const pression: Pression = {
        id_pression: 301,
        id_facteur_influence: 101,
        libelle: 'Pression test',
        date_ajout: '',
        date_maj: '',
      };
      component.startEditPression(pression);
      component.editPressionLibelle = 'Modifiée';
      component.saveEditPression(pression);
      expect(component.errorMessage()).toBeTruthy();
    });
  });

  // =========================================================================
  // OLT (Objectifs à Long Terme)
  // =========================================================================

  describe('OLT', () => {
    beforeEach(() => setup());

    const mockEtat: EtatActuel = {
      id_etat_actuel: 601, id_enjeu: 1, libelle: 'État actuel test', date_ajout: '', date_maj: '',
    };
    const mockOlt: ObjectifLongTerme = {
      id_olt: 501, id_etat_actuel: 1, libelle: 'OLT Test', date_ajout: '', date_maj: '',
    };

    it('should toggle OLT expanded state', () => {
      expect(component.isOltExpanded(501)).toBe(false);
      component.toggleOlt(501);
      expect(component.isOltExpanded(501)).toBe(true);
      component.toggleOlt(501);
      expect(component.isOltExpanded(501)).toBe(false);
    });

    it('should start adding OLT', () => {
      component.startAddOlt(601);
      expect(component.addingOltForEtat()).toBe(601);
      expect(component.newOltLibelle).toBe('');
    });

    it('should cancel adding OLT', () => {
      component.startAddOlt(601);
      component.newOltLibelle = 'Test';
      component.cancelAddOlt();
      expect(component.addingOltForEtat()).toBeNull();
      expect(component.newOltLibelle).toBe('');
    });

    it('should call createObjectifLongTerme on save', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newOltLibelle = 'Nouvel OLT';
      component.newOltDescription = 'Desc OLT';
      component.saveOlt(mockEtat);

      expect(mockEnjeuService.createObjectifLongTerme).toHaveBeenCalledWith({
        id_etat_actuel: 601,
        libelle: 'Nouvel OLT',
        description: 'Desc OLT',
      });
    });

    it('should not save OLT with empty libelle', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newOltLibelle = '   ';
      component.saveOlt(mockEtat);
      expect(mockEnjeuService.createObjectifLongTerme).not.toHaveBeenCalled();
    });

    it('should start editing OLT with pre-filled values', () => {
      component.startEditOlt(mockOlt);
      expect(component.editingOltId()).toBe(501);
      expect(component.editOltLibelle).toBe('OLT Test');
    });

    it('should cancel editing OLT', () => {
      component.startEditOlt(mockOlt);
      component.cancelEditOlt();
      expect(component.editingOltId()).toBeNull();
      expect(component.editOltLibelle).toBe('');
    });

    it('should call updateObjectifLongTerme on save edit', () => {
      component.startEditOlt(mockOlt);
      component.editOltLibelle = 'OLT modifié';
      component.saveEditOlt(mockOlt);
      expect(mockEnjeuService.updateObjectifLongTerme).toHaveBeenCalledWith(501, {
        libelle: 'OLT modifié',
        description: undefined,
      });
    });

    it('should not save edit OLT with empty libelle', () => {
      component.startEditOlt(mockOlt);
      component.editOltLibelle = '   ';
      component.saveEditOlt(mockOlt);
      expect(mockEnjeuService.updateObjectifLongTerme).not.toHaveBeenCalled();
    });

    it('should reset editing state after successful OLT update', () => {
      component.startEditOlt(mockOlt);
      component.editOltLibelle = 'Modifié';
      component.saveEditOlt(mockOlt);
      expect(component.editingOltId()).toBeNull();
    });

    it('should set errorMessage on OLT update error', () => {
      mockEnjeuService.updateObjectifLongTerme.mockReturnValue(throwError(() => new Error('fail')));
      component.startEditOlt(mockOlt);
      component.editOltLibelle = 'Modifié';
      component.saveEditOlt(mockOlt);
      expect(component.errorMessage()).toBeTruthy();
    });

    it('should call deleteObjectifLongTerme after confirm', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteOlt(mockOlt);
      expect(mockEnjeuService.deleteObjectifLongTerme).toHaveBeenCalledWith(501);
    });

    it('should not delete OLT when dialog cancelled', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteOlt(mockOlt);
      expect(mockEnjeuService.deleteObjectifLongTerme).not.toHaveBeenCalled();
    });
  });

  // =========================================================================
  // État actuel
  // =========================================================================

  describe('état actuel', () => {
    beforeEach(() => setup());

    const mockOlt: ObjectifLongTerme = {
      id_olt: 501, id_etat_actuel: 1, libelle: 'OLT Test', date_ajout: '', date_maj: '',
    };
    const mockEtat: EtatActuel = {
      id_etat_actuel: 601, id_enjeu: 1, libelle: 'État actuel test', date_ajout: '', date_maj: '',
    };

    it('should toggle état actuel expanded state', () => {
      expect(component.isEtatExpanded(601)).toBe(false);
      component.toggleEtat(601);
      expect(component.isEtatExpanded(601)).toBe(true);
      component.toggleEtat(601);
      expect(component.isEtatExpanded(601)).toBe(false);
    });

    it('should start adding état actuel', () => {
      component.startAddEtat();
      expect(component.addingEtat()).toBe(true);
      expect(component.newEtatLibelle).toBe('');
    });

    it('should cancel adding état actuel', () => {
      component.startAddEtat();
      component.newEtatLibelle = 'Test';
      component.cancelAddEtat();
      expect(component.addingEtat()).toBe(false);
      expect(component.newEtatLibelle).toBe('');
    });

    it('should call createEtatActuel on save', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newEtatLibelle = 'Nouvel état';
      component.newEtatDescription = 'Desc';
      component.saveEtatActuel();

      expect(mockEnjeuService.createEtatActuel).toHaveBeenCalledWith({
        id_enjeu: 1,
        libelle: 'Nouvel état',
        description: 'Desc',
      });
    });

    it('should not save état actuel with empty libelle', () => {
      component.newEtatLibelle = '   ';
      component.saveEtatActuel();
      expect(mockEnjeuService.createEtatActuel).not.toHaveBeenCalled();
    });

    it('should start editing état actuel with pre-filled values', () => {
      component.startEditEtat(mockEtat);
      expect(component.editingEtatId()).toBe(601);
      expect(component.editEtatLibelle).toBe('État actuel test');
    });

    it('should cancel editing état actuel', () => {
      component.startEditEtat(mockEtat);
      component.cancelEditEtat();
      expect(component.editingEtatId()).toBeNull();
      expect(component.editEtatLibelle).toBe('');
    });

    it('should call updateEtatActuel on save edit', () => {
      component.startEditEtat(mockEtat);
      component.editEtatLibelle = 'État modifié';
      component.saveEditEtat(mockEtat);
      expect(mockEnjeuService.updateEtatActuel).toHaveBeenCalledWith(601, {
        libelle: 'État modifié',
        description: undefined,
      });
    });

    it('should not save edit état with empty libelle', () => {
      component.startEditEtat(mockEtat);
      component.editEtatLibelle = '   ';
      component.saveEditEtat(mockEtat);
      expect(mockEnjeuService.updateEtatActuel).not.toHaveBeenCalled();
    });

    it('should reset editing state after successful état update', () => {
      component.startEditEtat(mockEtat);
      component.editEtatLibelle = 'Modifié';
      component.saveEditEtat(mockEtat);
      expect(component.editingEtatId()).toBeNull();
    });

    it('should set errorMessage on état update error', () => {
      mockEnjeuService.updateEtatActuel.mockReturnValue(throwError(() => new Error('fail')));
      component.startEditEtat(mockEtat);
      component.editEtatLibelle = 'Modifié';
      component.saveEditEtat(mockEtat);
      expect(component.errorMessage()).toBeTruthy();
    });

    it('should call deleteEtatActuel after confirm', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteEtatActuel(mockEtat);
      expect(mockEnjeuService.deleteEtatActuel).toHaveBeenCalledWith(601);
    });

    it('should not delete état when dialog cancelled', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteEtatActuel(mockEtat);
      expect(mockEnjeuService.deleteEtatActuel).not.toHaveBeenCalled();
    });
  });

  // =========================================================================
  // Niveau d'exigence
  // =========================================================================

  describe('niveau d\'exigence', () => {
    beforeEach(() => setup());

    const mockOlt: ObjectifLongTerme = {
      id_olt: 501, id_etat_actuel: 1, libelle: 'OLT Test', date_ajout: '', date_maj: '',
    };
    const mockNe: NiveauExigence = {
      id_ne: 701, id_olt: 501, libelle: 'NE Test', date_ajout: '', date_maj: '',
    };

    it('should start adding NE', () => {
      component.startAddNe(501);
      expect(component.addingNeForOlt()).toBe(501);
      expect(component.newNeLibelle).toBe('');
    });

    it('should cancel adding NE', () => {
      component.startAddNe(501);
      component.newNeLibelle = 'Test';
      component.cancelAddNe();
      expect(component.addingNeForOlt()).toBeNull();
      expect(component.newNeLibelle).toBe('');
    });

    it('should call createNiveauExigence on save', () => {
      component.newNeLibelle = 'Nouveau NE';
      component.newNeDescription = 'Desc';
      component.saveNe(mockOlt);

      expect(mockEnjeuService.createNiveauExigence).toHaveBeenCalledWith({
        id_olt: 501,
        libelle: 'Nouveau NE',
        description: 'Desc',
      });
    });

    it('should not save NE with empty libelle', () => {
      component.newNeLibelle = '   ';
      component.saveNe(mockOlt);
      expect(mockEnjeuService.createNiveauExigence).not.toHaveBeenCalled();
    });

    it('should start editing NE with pre-filled values', () => {
      component.startEditNe(mockNe);
      expect(component.editingNeId()).toBe(701);
      expect(component.editNeLibelle).toBe('NE Test');
    });

    it('should cancel editing NE', () => {
      component.startEditNe(mockNe);
      component.cancelEditNe();
      expect(component.editingNeId()).toBeNull();
      expect(component.editNeLibelle).toBe('');
    });

    it('should call updateNiveauExigence on save edit', () => {
      component.startEditNe(mockNe);
      component.editNeLibelle = 'NE modifié';
      component.saveEditNe(mockNe);
      expect(mockEnjeuService.updateNiveauExigence).toHaveBeenCalledWith(701, {
        libelle: 'NE modifié',
        description: undefined,
      });
    });

    it('should not save edit NE with empty libelle', () => {
      component.startEditNe(mockNe);
      component.editNeLibelle = '   ';
      component.saveEditNe(mockNe);
      expect(mockEnjeuService.updateNiveauExigence).not.toHaveBeenCalled();
    });

    it('should reset editing state after successful NE update', () => {
      component.startEditNe(mockNe);
      component.editNeLibelle = 'Modifié';
      component.saveEditNe(mockNe);
      expect(component.editingNeId()).toBeNull();
    });

    it('should set errorMessage on NE update error', () => {
      mockEnjeuService.updateNiveauExigence.mockReturnValue(throwError(() => new Error('fail')));
      component.startEditNe(mockNe);
      component.editNeLibelle = 'Modifié';
      component.saveEditNe(mockNe);
      expect(component.errorMessage()).toBeTruthy();
    });

    it('should call deleteNiveauExigence after confirm', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteNe(mockNe);
      expect(mockEnjeuService.deleteNiveauExigence).toHaveBeenCalledWith(701);
    });

    it('should not delete NE when dialog cancelled', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteNe(mockNe);
      expect(mockEnjeuService.deleteNiveauExigence).not.toHaveBeenCalled();
    });
  });

  // =========================================================================
  // Indicateurs
  // =========================================================================

  describe('indicateurs', () => {
    beforeEach(() => setup());

    const mockNe: NiveauExigence = {
      id_ne: 701, id_olt: 501, libelle: 'NE Test', date_ajout: '', date_maj: '',
    };
    const mockIndicateur: Indicateur = {
      id_indicateur: 801, id_ne: 701, nom_indicateur: 'Indicateur test',
      est_standardise: false, date_ajout: '', date_maj: '',
      metriques: [{ id_metrique: 901, id_indicateur: 801, nom_metrique: 'Métrique test', date_ajout: '', date_maj: '' }],
    };

    it('should toggle indicateur expanded state', () => {
      expect(component.isIndicateurExpanded(801)).toBe(false);
      component.toggleIndicateur(801);
      expect(component.isIndicateurExpanded(801)).toBe(true);
      component.toggleIndicateur(801);
      expect(component.isIndicateurExpanded(801)).toBe(false);
    });

    it('should start adding indicateur', () => {
      component.startAddIndicateur(701);
      expect(component.addingIndicateurForNe()).toBe(701);
      expect(component.newIndicateurNom).toBe('');
    });

    it('should cancel adding indicateur', () => {
      component.startAddIndicateur(701);
      component.cancelAddIndicateur();
      expect(component.addingIndicateurForNe()).toBeNull();
    });

    it('should call createIndicateur on save', () => {
      component.newIndicateurNom = 'Nouvel indicateur';
      component.newIndicateurDescription = 'Desc';
      component.newIndicateurStandardise = true;
      component.saveIndicateur(mockNe);

      expect(mockEnjeuService.createIndicateur).toHaveBeenCalledWith(expect.objectContaining({
        id_ne: 701,
        nom_indicateur: 'Nouvel indicateur',
        est_standardise: true,
      }));
    });

    it('should not save indicateur with empty nom', () => {
      component.newIndicateurNom = '   ';
      component.saveIndicateur(mockNe);
      expect(mockEnjeuService.createIndicateur).not.toHaveBeenCalled();
    });

    it('should start editing indicateur with pre-filled values', () => {
      component.startEditIndicateur(mockIndicateur);
      expect(component.editingIndicateurId()).toBe(801);
      expect(component.editIndicateurNom).toBe('Indicateur test');
      expect(component.editIndicateurStandardise).toBe(false);
      expect(component.editIndicateurMetriques.length).toBe(1);
    });

    it('should cancel editing indicateur', () => {
      component.startEditIndicateur(mockIndicateur);
      component.cancelEditIndicateur();
      expect(component.editingIndicateurId()).toBeNull();
      expect(component.editIndicateurMetriques.length).toBe(0);
    });

    it('should call updateIndicateur on save edit', () => {
      component.startEditIndicateur(mockIndicateur);
      component.editIndicateurNom = 'Indicateur modifié';
      component.editIndicateurMetriques = []; // no metrique ops
      component.saveEditIndicateur(mockIndicateur);
      expect(mockEnjeuService.updateIndicateur).toHaveBeenCalledWith(801, expect.objectContaining({
        nom_indicateur: 'Indicateur modifié',
      }));
    });

    it('should not save edit indicateur with empty nom', () => {
      component.startEditIndicateur(mockIndicateur);
      component.editIndicateurNom = '   ';
      component.saveEditIndicateur(mockIndicateur);
      expect(mockEnjeuService.updateIndicateur).not.toHaveBeenCalled();
    });

    it('should call deleteIndicateur after confirm', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteIndicateur(mockIndicateur);
      expect(mockEnjeuService.deleteIndicateur).toHaveBeenCalledWith(801);
    });

    it('should not delete indicateur when dialog cancelled', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteIndicateur(mockIndicateur);
      expect(mockEnjeuService.deleteIndicateur).not.toHaveBeenCalled();
    });
  });

  // =========================================================================
  // Métriques
  // =========================================================================

  describe('métriques', () => {
    beforeEach(() => setup());

    it('should create empty metrique with default values', () => {
      const met = component.createEmptyMetrique();
      expect(met.nom_metrique).toBe('');
      expect(met.type_metrique).toBeNull();
      expect(met.scores[1].inf).toBeNull();
    });

    it('should add metrique to form', () => {
      component.indicateurFormMetriques = [];
      component.addMetriqueToForm();
      expect(component.indicateurFormMetriques.length).toBe(1);
    });

    it('should remove metrique from form', () => {
      component.indicateurFormMetriques = [component.createEmptyMetrique(), component.createEmptyMetrique()];
      component.removeMetriqueFromForm(0);
      expect(component.indicateurFormMetriques.length).toBe(1);
    });

    it('should call deleteMetrique', () => {
      component.deleteMetrique({ id_metrique: 901 });
      expect(mockEnjeuService.deleteMetrique).toHaveBeenCalledWith(901);
    });

    it('should build metrique payload correctly', () => {
      const met = component.createEmptyMetrique();
      met.nom_metrique = 'Test';
      met.unite = 'kg';
      met.ponderation = 0.5;
      const payload = component.buildMetriquePayload(801, met);
      expect(payload.id_indicateur).toBe(801);
      expect(payload.nom_metrique).toBe('Test');
      expect(payload.unite).toBe('kg');
      expect(payload.ponderation).toBe(0.5);
    });

    it('should return score range formatted', () => {
      const met = { score_1_inf: 0, score_1_sup: 2 };
      expect(component.getScoreRange(met, 1)).toBe('0 - 2');
    });

    it('should return >= for inf only', () => {
      const met = { score_1_inf: 5 };
      expect(component.getScoreRange(met, 1)).toBe('≥ 5');
    });

    it('should return <= for sup only', () => {
      const met = { score_1_sup: 10 };
      expect(component.getScoreRange(met, 1)).toBe('≤ 10');
    });

    it('should return dash for no scores', () => {
      expect(component.getScoreRange({}, 1)).toBe('- - -');
    });
  });

  // =========================================================================
  // Objectifs opérationnels (OO)
  // =========================================================================

  describe('objectifs opérationnels', () => {
    beforeEach(() => setup());

    const mockOo: ObjectifOperationnel = {
      id_oo: 1001, id_pression: 301, libelle: 'OO Test', date_ajout: '', date_maj: '',
    };

    it('should toggle OO expanded state', () => {
      expect(component.isOoExpanded(1001)).toBe(false);
      component.toggleOo(1001);
      expect(component.isOoExpanded(1001)).toBe(true);
      component.toggleOo(1001);
      expect(component.isOoExpanded(1001)).toBe(false);
    });

    it('should start adding OO', () => {
      component.startAddOo();
      expect(component.addingOo()).toBe(true);
      expect(component.newOoLibelle).toBe('');
    });

    it('should cancel adding OO', () => {
      component.startAddOo();
      component.newOoLibelle = 'Test';
      component.cancelAddOo();
      expect(component.addingOo()).toBe(false);
      expect(component.newOoLibelle).toBe('');
    });

    it('should call createObjectifOperationnel on save', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newOoLibelle = 'Nouvel OO';
      component.newOoDescription = 'Desc OO';
      component.newOoPressionId = 301;
      component.saveOo();

      expect(mockEnjeuService.createObjectifOperationnel).toHaveBeenCalledWith(expect.objectContaining({
        id_pression: 301,
        libelle: 'Nouvel OO',
        description: 'Desc OO',
      }));
    });

    it('should not save OO with empty libelle', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newOoLibelle = '   ';
      component.newOoPressionId = 301;
      component.saveOo();
      expect(mockEnjeuService.createObjectifOperationnel).not.toHaveBeenCalled();
    });

    it('should not save OO without pression', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newOoLibelle = 'Nouvel OO';
      component.newOoPressionId = null;
      component.saveOo();
      expect(mockEnjeuService.createObjectifOperationnel).not.toHaveBeenCalled();
    });

    it('should start editing OO with pre-filled values', () => {
      component.startEditOo(mockOo);
      expect(component.editingOoId()).toBe(1001);
      expect(component.editOoLibelle).toBe('OO Test');
    });

    it('should cancel editing OO', () => {
      component.startEditOo(mockOo);
      component.cancelEditOo();
      expect(component.editingOoId()).toBeNull();
      expect(component.editOoLibelle).toBe('');
    });

    it('should call updateObjectifOperationnel on save edit', () => {
      component.startEditOo(mockOo);
      component.editOoLibelle = 'OO modifié';
      component.saveEditOo(mockOo);
      expect(mockEnjeuService.updateObjectifOperationnel).toHaveBeenCalledWith(1001, expect.objectContaining({
        id_pression: 301,
        libelle: 'OO modifié',
      }));
    });

    it('should not save edit OO with empty libelle', () => {
      component.startEditOo(mockOo);
      component.editOoLibelle = '   ';
      component.saveEditOo(mockOo);
      expect(mockEnjeuService.updateObjectifOperationnel).not.toHaveBeenCalled();
    });

    it('should not save edit OO without pression', () => {
      component.startEditOo(mockOo);
      component.editOoLibelle = 'OO modifié';
      component.editOoPressionId = null;
      component.saveEditOo(mockOo);
      expect(mockEnjeuService.updateObjectifOperationnel).not.toHaveBeenCalled();
    });

    it('should reset editing state after successful OO update', () => {
      component.startEditOo(mockOo);
      component.editOoLibelle = 'Modifié';
      component.saveEditOo(mockOo);
      expect(component.editingOoId()).toBeNull();
    });

    it('should set errorMessage on OO update error', () => {
      mockEnjeuService.updateObjectifOperationnel.mockReturnValue(throwError(() => new Error('fail')));
      component.startEditOo(mockOo);
      component.editOoLibelle = 'Modifié';
      component.saveEditOo(mockOo);
      expect(component.errorMessage()).toBeTruthy();
    });

    it('should call deleteObjectifOperationnel after confirm', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteOo(mockOo);
      expect(mockEnjeuService.deleteObjectifOperationnel).toHaveBeenCalledWith(1001);
    });

    it('should not delete OO when dialog cancelled', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteOo(mockOo);
      expect(mockEnjeuService.deleteObjectifOperationnel).not.toHaveBeenCalled();
    });
  });

  // =========================================================================
  // Résultats attendus (RA)
  // =========================================================================

  describe('résultats attendus', () => {
    beforeEach(() => setup());

    const mockOo: ObjectifOperationnel = {
      id_oo: 1001, id_pression: 301, libelle: 'OO Test', date_ajout: '', date_maj: '',
    };
    const mockRa: ResultatAttendu = {
      id_ra: 1101, id_oo: 1001, libelle: 'RA Test', date_ajout: '', date_maj: '',
    };

    it('should start adding RA', () => {
      component.startAddRa(1001);
      expect(component.addingRaForOo()).toBe(1001);
      expect(component.newRaLibelle).toBe('');
    });

    it('should cancel adding RA', () => {
      component.startAddRa(1001);
      component.newRaLibelle = 'Test';
      component.cancelAddRa();
      expect(component.addingRaForOo()).toBeNull();
      expect(component.newRaLibelle).toBe('');
    });

    it('should call createResultatAttendu on save', () => {
      component.newRaLibelle = 'Nouveau RA';
      component.newRaDescription = 'Desc';
      component.saveRa(mockOo);

      expect(mockEnjeuService.createResultatAttendu).toHaveBeenCalledWith({
        id_oo: 1001,
        libelle: 'Nouveau RA',
        description: 'Desc',
      });
    });

    it('should not save RA with empty libelle', () => {
      component.newRaLibelle = '   ';
      component.saveRa(mockOo);
      expect(mockEnjeuService.createResultatAttendu).not.toHaveBeenCalled();
    });

    it('should start editing RA with pre-filled values', () => {
      component.startEditRa(mockRa);
      expect(component.editingRaId()).toBe(1101);
      expect(component.editRaLibelle).toBe('RA Test');
    });

    it('should cancel editing RA', () => {
      component.startEditRa(mockRa);
      component.cancelEditRa();
      expect(component.editingRaId()).toBeNull();
      expect(component.editRaLibelle).toBe('');
    });

    it('should call updateResultatAttendu on save edit', () => {
      component.startEditRa(mockRa);
      component.editRaLibelle = 'RA modifié';
      component.saveEditRa(mockRa);
      expect(mockEnjeuService.updateResultatAttendu).toHaveBeenCalledWith(1101, {
        libelle: 'RA modifié',
        description: undefined,
      });
    });

    it('should not save edit RA with empty libelle', () => {
      component.startEditRa(mockRa);
      component.editRaLibelle = '   ';
      component.saveEditRa(mockRa);
      expect(mockEnjeuService.updateResultatAttendu).not.toHaveBeenCalled();
    });

    it('should reset editing state after successful RA update', () => {
      component.startEditRa(mockRa);
      component.editRaLibelle = 'Modifié';
      component.saveEditRa(mockRa);
      expect(component.editingRaId()).toBeNull();
    });

    it('should set errorMessage on RA update error', () => {
      mockEnjeuService.updateResultatAttendu.mockReturnValue(throwError(() => new Error('fail')));
      component.startEditRa(mockRa);
      component.editRaLibelle = 'Modifié';
      component.saveEditRa(mockRa);
      expect(component.errorMessage()).toBeTruthy();
    });

    it('should call deleteResultatAttendu after confirm', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteRa(mockRa);
      expect(mockEnjeuService.deleteResultatAttendu).toHaveBeenCalledWith(1101);
    });

    it('should not delete RA when dialog cancelled', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteRa(mockRa);
      expect(mockEnjeuService.deleteResultatAttendu).not.toHaveBeenCalled();
    });
  });

  // =========================================================================
  // Error handling
  // =========================================================================

  describe('error handling', () => {
    it('should set errorMessage on loadPlanData failure', () => {
      const errorEnjeuService = {
        getPlanEnjeux: jest.fn().mockReturnValue(throwError(() => new Error('Network error'))),
      } as any;
      const errorAdminService = {
        getPlanBySlug: jest.fn().mockReturnValue(of({ id_pg: 10, nom: 'Plan Test', annee_debut: null, annee_fin: null })),
        getNomenclaturesByType: jest.fn().mockReturnValue(of([])),
      };

      routeParamsSubject = new Subject<any>();

      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        imports: [
          EnjeuxListComponent,
          NoopAnimationsModule,
          HttpClientTestingModule,
          RouterTestingModule,
          TranslateModule.forRoot({
            loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          }),
        ],
        providers: [
          {
            provide: ActivatedRoute, useValue: {
              snapshot: { paramMap: { get: () => null } },
              parent: { snapshot: { paramMap: { get: (key: string) => key === 'slug' ? 'plan-test' : null } } },
              params: routeParamsSubject.asObservable(),
            }
          },
          { provide: EnjeuService, useValue: errorEnjeuService },
          { provide: AdminService, useValue: errorAdminService },
        ],
      }).compileComponents();

      const fix = TestBed.createComponent(EnjeuxListComponent);
      fix.detectChanges();

      expect(fix.componentInstance.errorMessage()).toBeTruthy();
      expect(fix.componentInstance.isLoading()).toBe(false);
    });
  });
});
