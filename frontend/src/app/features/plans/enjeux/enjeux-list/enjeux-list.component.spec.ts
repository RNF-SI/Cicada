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
import { Enjeu, PlanEnjeuxResponse, FacteurInfluence, Pression } from '../../../../core/models/enjeu.model';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({
      enjeux: {
        types: { enjeu: 'Enjeu', fcr: 'FCR' },
        enjeuForm: {
          ecologique: 'Écologique',
          socioEconomique: 'Socio-économique',
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
  nb_facteurs_influence: 2,
  facteurs_influence: [
    { id_facteur_influence: 101, id_enjeu: 1, libelle: 'Urbanisation', date_ajout: '', date_maj: '', pressions: [] },
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
    getPlanEnjeux: jest.Mock;
    deleteEnjeu: jest.Mock;
    createFacteurInfluence: jest.Mock;
    updateFacteurInfluence: jest.Mock;
    deleteFacteurInfluence: jest.Mock;
    createPression: jest.Mock;
    updatePression: jest.Mock;
    deletePression: jest.Mock;
  };
  let mockAdminService: { getPlanBySlug: jest.Mock };
  let routeParamsSubject: Subject<any>;

  function setup(parentParams: Record<string, string> = { slug: 'plan-test' }, routeParams: Record<string, string> = {}): void {
    routeParamsSubject = new Subject<any>();

    mockEnjeuService = {
      getPlanEnjeux: jest.fn().mockReturnValue(of(mockPlanEnjeuxResponse)),
      deleteEnjeu: jest.fn().mockReturnValue(of(void 0)),
      createFacteurInfluence: jest.fn().mockReturnValue(of({ id_facteur_influence: 999, id_enjeu: 1, libelle: 'Nouveau', date_ajout: '', date_maj: '' })),
      updateFacteurInfluence: jest.fn().mockReturnValue(of({ id_facteur_influence: 101, id_enjeu: 1, libelle: 'Modifié', date_ajout: '', date_maj: '' })),
      deleteFacteurInfluence: jest.fn().mockReturnValue(of(void 0)),
      createPression: jest.fn().mockReturnValue(of({ id_pression: 888, id_facteur_influence: 101, libelle: 'Nouvelle', date_ajout: '', date_maj: '' })),
      updatePression: jest.fn().mockReturnValue(of({ id_pression: 301, id_facteur_influence: 101, libelle: 'Modifiée', date_ajout: '', date_maj: '' })),
      deletePression: jest.fn().mockReturnValue(of(void 0)),
    };
    mockAdminService = {
      getPlanBySlug: jest.fn().mockReturnValue(of({ id_pg: 10, nom: 'Plan Test', annee_debut: null, annee_fin: null })),
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
      expect(labels).toContain('Habitats');
      expect(labels).toContain('Espèces');
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
  // Error handling
  // =========================================================================

  describe('error handling', () => {
    it('should set errorMessage on loadPlanData failure', () => {
      mockEnjeuService = {
        getPlanEnjeux: jest.fn().mockReturnValue(throwError(() => new Error('Network error'))),
        deleteEnjeu: jest.fn(),
        createFacteurInfluence: jest.fn(),
        updateFacteurInfluence: jest.fn(),
        deleteFacteurInfluence: jest.fn(),
        createPression: jest.fn(),
        updatePression: jest.fn(),
        deletePression: jest.fn(),
      };
      mockAdminService = {
        getPlanBySlug: jest.fn().mockReturnValue(of({ id_pg: 10, nom: 'Plan Test', annee_debut: null, annee_fin: null })),
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
          { provide: EnjeuService, useValue: mockEnjeuService },
          { provide: AdminService, useValue: mockAdminService },
        ],
      }).compileComponents();

      const fix = TestBed.createComponent(EnjeuxListComponent);
      fix.detectChanges();

      expect(fix.componentInstance.errorMessage()).toBeTruthy();
      expect(fix.componentInstance.isLoading()).toBe(false);
    });
  });
});
