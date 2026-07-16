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
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import { DeleteOperationDialogComponent } from '../../../../shared/components/modals';
import {
  Enjeu, PlanEnjeuxResponse, FacteurInfluence, Pression,
  ObjectifLongTerme, NiveauExigence, Indicateur,
  ObjectifOperationnel, ResultatAttendu
} from '../../../../core/models/enjeu.model';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({
      enjeux: {
        types: { enjeu: 'Enjeu', fcr: 'FCR' },
        enjeuForm: {
          ecologique: 'Conservation du patrimoine naturel',
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
          fcrPressureNotMandatory: "Pour un FCR, aucune pression préalable n'est requise (sauf catégorie ancrage).",
        },
        pression: {
          createSuccess: 'Pression créée',
          updateSuccess: 'Pression mise à jour',
          deleteTitle: 'Supprimer la pression',
          deleteConfirm: 'Confirmer suppression ?',
          deleteSuccess: 'Pression supprimée',
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
  geo_documents: false,
  geo_autre: false,
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
              id_oo: 1001, pressions: [{id_pression: 301, libelle: 'Pression Urbaine'}], pression_ids: [301], libelle: 'OO Test', date_ajout: '', date_maj: '',
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
    {
      id_facteur_influence: 102, id_enjeu: 1, libelle: 'Agriculture', date_ajout: '', date_maj: '',
      pressions: [
        {
          id_pression: 302, id_facteur_influence: 102, libelle: 'Pression Agricole', date_ajout: '', date_maj: '',
          objectifs_operationnels: [],
          nb_objectifs_operationnels: 0,
        }
      ],
      nb_pressions: 1,
    },
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
  geo_documents: false,
  geo_autre: false,
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
  geo_documents: false,
  geo_autre: false,
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
    deleteOperation: jest.Mock;
    removeMetriqueFromOperation: jest.Mock;
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
      // OLT
      createObjectifLongTerme: jest.fn().mockReturnValue(of({ id_olt: 502, id_enjeu: 1, libelle: 'Nouvel OLT', date_ajout: '', date_maj: '' })),
      updateObjectifLongTerme: jest.fn().mockReturnValue(of({ id_olt: 501, id_enjeu: 1, libelle: 'OLT modifié', date_ajout: '', date_maj: '' })),
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
      // Opérations (#457)
      deleteOperation: jest.fn().mockReturnValue(of(void 0)),
      removeMetriqueFromOperation: jest.fn().mockReturnValue(of(void 0)),
      // Cache signal partagé (sidebar) — #228 retour 2026-05-12
      currentPlanEnjeux: jest.fn().mockReturnValue(null),
      updatePlanEnjeuxCache: jest.fn(),
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
      fragment: of(null),
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
  // OLT global numbering — auto + manuel (#229 / #442)
  // =========================================================================

  describe('oltGlobalRank — numérotation manuelle (#442)', () => {
    beforeEach(() => setup());

    /** Construit un plan à 2 enjeux, chacun avec des OLT donnés. */
    function setOlts(oltsEnjeu1: any[], oltsEnjeu2: any[] = []): void {
      const mk = (olts: any[]) => olts.map((o, i) => ({
        id_olt: o.id, libelle: `OLT ${o.id}`, id_enjeu: 1,
        ordre: i, numero_manuel: o.numero_manuel ?? null,
        date_ajout: '', date_maj: '',
      }));
      component.planEnjeuxData.set({
        ...mockPlanEnjeuxResponse,
        enjeux: [
          { ...mockEnjeu1, ordre: 0, objectifs_long_terme: mk(oltsEnjeu1) },
          { ...mockEnjeu2, ordre: 1, objectifs_long_terme: mk(oltsEnjeu2) },
        ],
        fcr: [],
      } as any);
    }

    it('numérote automatiquement 1..N dans l\'ordre des enjeux quand aucun numéro fixé', () => {
      setOlts([{ id: 10 }, { id: 11 }], [{ id: 20 }, { id: 21 }]);
      expect(component.getOltGlobalNumber(10)).toBe(1);
      expect(component.getOltGlobalNumber(11)).toBe(2);
      expect(component.getOltGlobalNumber(20)).toBe(3);
      expect(component.getOltGlobalNumber(21)).toBe(4);
    });

    it('respecte un numéro fixé manuellement et le maintient stable', () => {
      // OLT de l'enjeu 2 (id 20) fixé à 1 : il garde le numéro 1.
      setOlts([{ id: 10 }, { id: 11 }], [{ id: 20, numero_manuel: 1 }]);
      expect(component.getOltGlobalNumber(20)).toBe(1);
    });

    it('l\'auto-numérotation saute l\'indice occupé par un numéro fixé', () => {
      // id 20 fixé à 1 → les OLT auto (10, 11) sautent le 1 : 2 puis 3.
      setOlts([{ id: 10 }, { id: 11 }], [{ id: 20, numero_manuel: 1 }]);
      expect(component.getOltGlobalNumber(10)).toBe(2);
      expect(component.getOltGlobalNumber(11)).toBe(3);
      expect(component.getOltGlobalNumber(20)).toBe(1);
    });

    it('supporte plusieurs numéros fixés simultanément', () => {
      setOlts(
        [{ id: 10, numero_manuel: 3 }, { id: 11 }],
        [{ id: 20, numero_manuel: 1 }, { id: 21 }],
      );
      // Réservés : 1 et 3. Auto (11, 21) → 2 puis 4.
      expect(component.getOltGlobalNumber(10)).toBe(3);
      expect(component.getOltGlobalNumber(11)).toBe(2);
      expect(component.getOltGlobalNumber(20)).toBe(1);
      expect(component.getOltGlobalNumber(21)).toBe(4);
    });
  });

  // =========================================================================
  // OO numbering — auto + manuel (#526, décline #442)
  // =========================================================================

  describe('ooLocalRank — numérotation manuelle (#526)', () => {
    beforeEach(() => setup());

    /**
     * Prépare un FCR sélectionné dont les OO sont rattachés directement
     * (chemin `objectifs_operationnels`, sans pression). `selectedOos()` les
     * trie par `ordre`.
     */
    function setOos(oos: { id: number; numero_manuel?: number | null }[]): void {
      const mk = oos.map((o, i) => ({
        id_oo: o.id, libelle: `OO ${o.id}`, id_enjeu: mockFcr.id_enjeu,
        pressions: [], pression_ids: [], ordre: i,
        numero_manuel: o.numero_manuel ?? null,
        date_ajout: '', date_maj: '',
      }));
      component.planEnjeuxData.set({
        ...mockPlanEnjeuxResponse,
        fcr: [{ ...mockFcr, objectifs_operationnels: mk } as any],
      } as any);
      component['selectedEnjeuSlug'].set('connaissance-scientifique');
    }

    it('numérote automatiquement 1..N dans l\'ordre quand aucun numéro fixé', () => {
      setOos([{ id: 10 }, { id: 11 }, { id: 12 }]);
      expect(component.getOoNumber(10)).toBe(1);
      expect(component.getOoNumber(11)).toBe(2);
      expect(component.getOoNumber(12)).toBe(3);
    });

    it('respecte un numéro fixé manuellement et le maintient stable', () => {
      setOos([{ id: 10 }, { id: 11, numero_manuel: 1 }]);
      expect(component.getOoNumber(11)).toBe(1);
    });

    it('l\'auto-numérotation saute l\'indice occupé par un numéro fixé', () => {
      // id 11 fixé à 1 → les OO auto (10, 12) sautent le 1 : 2 puis 3.
      setOos([{ id: 10 }, { id: 11, numero_manuel: 1 }, { id: 12 }]);
      expect(component.getOoNumber(10)).toBe(2);
      expect(component.getOoNumber(11)).toBe(1);
      expect(component.getOoNumber(12)).toBe(3);
    });

    it('supporte plusieurs numéros fixés simultanément', () => {
      setOos([{ id: 10, numero_manuel: 3 }, { id: 11 }, { id: 12, numero_manuel: 1 }]);
      // Réservés : 1 et 3. Auto (11) → 2.
      expect(component.getOoNumber(10)).toBe(3);
      expect(component.getOoNumber(11)).toBe(2);
      expect(component.getOoNumber(12)).toBe(1);
    });
  });

  // =========================================================================
  // Enjeu / FCR numbering — auto + manuel (#526, décline #442)
  // =========================================================================

  describe('getEnjeuDisplayNumber — numérotation manuelle Enjeu/FCR (#526)', () => {
    beforeEach(() => setup());

    /** Prépare des enjeux et FCR avec numéros fixés éventuels. */
    function setEnjeux(
      enjeux: { id: number; numero_manuel?: number | null }[],
      fcrs: { id: number; numero_manuel?: number | null }[] = [],
    ): void {
      const mkEnjeu = enjeux.map((e, i) => ({
        ...mockEnjeu1, id_enjeu: e.id, ordre: i,
        numero_manuel: e.numero_manuel ?? null,
      }));
      const mkFcr = fcrs.map((f, i) => ({
        ...mockFcr, id_enjeu: f.id, ordre: i,
        numero_manuel: f.numero_manuel ?? null,
      }));
      component.planEnjeuxData.set({
        ...mockPlanEnjeuxResponse,
        enjeux: mkEnjeu as any,
        fcr: mkFcr as any,
      } as any);
    }

    it('numérote automatiquement 1..N dans l\'ordre quand aucun numéro fixé', () => {
      setEnjeux([{ id: 10 }, { id: 11 }, { id: 12 }]);
      const list = component.enjeux();
      expect(component.getEnjeuDisplayNumber(list[0], false, 0)).toBe(1);
      expect(component.getEnjeuDisplayNumber(list[1], false, 1)).toBe(2);
      expect(component.getEnjeuDisplayNumber(list[2], false, 2)).toBe(3);
    });

    it('respecte un numéro fixé et fait sauter l\'indice aux autres', () => {
      setEnjeux([{ id: 10 }, { id: 11, numero_manuel: 1 }, { id: 12 }]);
      const byId = (id: number) => component.enjeux().find(e => e.id_enjeu === id)!;
      expect(component.getEnjeuDisplayNumber(byId(11), false, 1)).toBe(1);
      expect(component.getEnjeuDisplayNumber(byId(10), false, 0)).toBe(2);
      expect(component.getEnjeuDisplayNumber(byId(12), false, 2)).toBe(3);
    });

    it('numérote les FCR indépendamment des enjeux', () => {
      setEnjeux([{ id: 10 }, { id: 11 }], [{ id: 20 }, { id: 21, numero_manuel: 1 }]);
      const enjeuById = (id: number) => component.enjeux().find(e => e.id_enjeu === id)!;
      const fcrById = (id: number) => component.fcr().find(e => e.id_enjeu === id)!;
      // Enjeux : 1, 2 (liste propre)
      expect(component.getEnjeuDisplayNumber(enjeuById(10), false, 0)).toBe(1);
      expect(component.getEnjeuDisplayNumber(enjeuById(11), false, 1)).toBe(2);
      // FCR : 21 fixé à 1, 20 auto saute à 2 (liste FCR propre)
      expect(component.getEnjeuDisplayNumber(fcrById(21), true, 1)).toBe(1);
      expect(component.getEnjeuDisplayNumber(fcrById(20), true, 0)).toBe(2);
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
      expect(label).toBe('Conservation du patrimoine naturel');
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

    // #492 — La note « pression non obligatoire » est identique pour TOUS les FCR
    // (y compris hors ancrage) et mentionne toujours « (sauf catégorie ancrage) ».
    it('should always mention "(sauf catégorie ancrage)" in the FCR pressure note', () => {
      const translate = TestBed.inject(TranslateService);
      const note = translate.instant('enjeux.facteurInfluence.fcrPressureNotMandatory');
      expect(note).toContain('aucune pression préalable');
      expect(note).toContain('(sauf catégorie ancrage)');
      // Plus de variante conditionnelle par catégorie.
      expect((component as any).selectedFcrIsAncrage).toBeUndefined();
    });
  });

  // =========================================================================
  // #474 — pressions proposées au rattachement d'un OO de FCR
  // =========================================================================

  describe('ecologicalPressionGroups (#474)', () => {
    beforeEach(() => setup());

    it('lists ecological enjeux pressions grouped by « enjeu › facteur »', () => {
      component['selectedEnjeuSlug'].set('connaissance-scientifique'); // FCR sans pression propre
      const groups = component.ecologicalPressionGroups();
      const labels = groups.map(g => g.label);
      expect(labels).toContain('Protection zones humides › Urbanisation');
      expect(labels).toContain('Protection zones humides › Agriculture');
      // Les pressions écologiques sont bien exposées
      expect(groups.flatMap(g => g.pressions.map(p => p.id_pression))).toEqual(
        expect.arrayContaining([301, 302]),
      );
    });

    it('inclut les pressions propres au FCR sélectionné ET les met en premier', () => {
      // FCR portant sa propre pression (retour test 02/07/2026)
      const fcrWithPression: Enjeu = {
        ...mockFcr,
        facteurs_influence: [
          {
            id_facteur_influence: 201, id_enjeu: mockFcr.id_enjeu, libelle: 'Moyens humains', date_ajout: '', date_maj: '',
            pressions: [
              { id_pression: 401, id_facteur_influence: 201, libelle: 'Pression FCR', date_ajout: '', date_maj: '', objectifs_operationnels: [], nb_objectifs_operationnels: 0 },
            ],
            nb_pressions: 1,
          },
        ],
      };
      component.planEnjeuxData.set({ ...mockPlanEnjeuxResponse, fcr: [fcrWithPression] });
      component['selectedEnjeuSlug'].set('connaissance-scientifique');

      const groups = component.ecologicalPressionGroups();
      // La pression propre du FCR apparaît…
      const fcrGroup = groups.find(g => g.pressions.some(p => p.id_pression === 401));
      expect(fcrGroup).toBeDefined();
      expect(fcrGroup!.label).toBe('Connaissance scientifique › Moyens humains');
      // …et en PREMIER (avant les pressions des enjeux écologiques).
      expect(groups[0].pressions[0].id_pression).toBe(401);
      // Les pressions écologiques suivent toujours.
      expect(groups.flatMap(g => g.pressions.map(p => p.id_pression))).toEqual(
        expect.arrayContaining([401, 301, 302]),
      );
    });

    it('n\'ajoute pas les pressions du FCR quand un enjeu écologique est sélectionné', () => {
      const fcrWithPression: Enjeu = {
        ...mockFcr,
        facteurs_influence: [
          {
            id_facteur_influence: 201, id_enjeu: mockFcr.id_enjeu, libelle: 'Moyens humains', date_ajout: '', date_maj: '',
            pressions: [
              { id_pression: 401, id_facteur_influence: 201, libelle: 'Pression FCR', date_ajout: '', date_maj: '', objectifs_operationnels: [], nb_objectifs_operationnels: 0 },
            ],
            nb_pressions: 1,
          },
        ],
      };
      component.planEnjeuxData.set({ ...mockPlanEnjeuxResponse, fcr: [fcrWithPression] });
      component['selectedEnjeuSlug'].set('protection-zones-humides'); // enjeu écologique, pas FCR

      const groups = component.ecologicalPressionGroups();
      expect(groups.flatMap(g => g.pressions.map(p => p.id_pression))).not.toContain(401);
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

    it('should carry the current tab when editing an action so the user returns to it, not the OO tab (#576)', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.setActiveTab('olt');
      component.navigateToEditOperation(2445);
      expect(router.navigate).toHaveBeenCalledWith(
        ['/plans', 'plan-test', 'enjeux', 'operations', 2445, 'modifier'],
        { queryParams: { returnTab: 'olt', returnEnjeu: 'protection-zones-humides' } }
      );
    });

    it('should open the action fiche (not the form) in a new tab (#494, #455)', () => {
      const openSpy = jest.spyOn(window, 'open').mockReturnValue(null);
      component.navigateToViewOperation(2445);
      expect(openSpy).toHaveBeenCalledTimes(1);
      const [url, target] = openSpy.mock.calls[0];
      expect(url).toContain('/plans/plan-test/enjeux/operations/2445/fiche');
      expect(target).toBe('_blank');
      openSpy.mockRestore();
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

    // #481 — Rappel de l'ordre de saisie fusionné dans l'unique note d'aide,
    // en haut des onglets « Vision à long terme » et « Stratégie opérationnelle »
    // (pas dans le formulaire d'action).
    it('should show the saisie-order line in a single help note on the OLT and operations tabs', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');

      component.setActiveTab('olt');
      fixture.detectChanges();
      const el = fixture.nativeElement as HTMLElement;
      // Une seule note d'aide, contenant le rappel de l'ordre de saisie.
      expect(el.querySelectorAll('.olt-content .olt-info-note').length).toBe(1);
      expect(el.querySelector('.olt-content .olt-info-note .saisie-order-line')).toBeTruthy();

      component.setActiveTab('operations');
      fixture.detectChanges();
      expect(el.querySelectorAll('.oo-content .olt-info-note').length).toBe(1);
      expect(el.querySelector('.oo-content .olt-info-note .saisie-order-line')).toBeTruthy();
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
  // #531 — retour depuis la fiche action vers la position dans l'architecture
  // =========================================================================

  describe('expandAndScrollToOperation — position de l\'action (#531)', () => {
    beforeEach(() => setup());

    /** Injecte une chaîne OO → RA → indicateur → métrique → opération(555). */
    function seedOperationUnderOo(): void {
      const enjeu = JSON.parse(JSON.stringify(mockEnjeu1));
      enjeu.facteurs_influence[0].pressions[0].objectifs_operationnels[0]
        .resultats_attendus[0].indicateurs = [
          { id_indicateur: 8801, metriques: [{ id_metrique: 9901, operations: [{ id_operation: 555 }] }] },
        ];
      component.planEnjeuxData.set({ ...mockPlanEnjeuxResponse, enjeux: [enjeu] });
      component['selectedEnjeuSlug'].set('protection-zones-humides');
    }

    it('ouvre l\'onglet operations et déplie la chaîne OO → indicateur → action', () => {
      seedOperationUnderOo();
      component['pendingScrollToOperation'].set(555);

      component['expandAndScrollToOperation']();

      // Régression #531 : l'onglet « operations » doit être forcé (sinon le nœud
      // n'est pas rendu et le scroll échoue), et toute la chaîne parente dépliée.
      expect(component.activeTab()).toBe('operations');
      expect(component.expandedOoIds().has(1001)).toBe(true);
      expect(component.expandedOoIndicateurIds().has(8801)).toBe(true);
      expect(component.expandedOoOperationIds().has(555)).toBe(true);
    });
  });

  // =========================================================================
  // Delete enjeu
  // =========================================================================

  describe('delete enjeu', () => {
    beforeEach(() => setup());

    it('should call deleteEnjeu and reload on success', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      const callsBefore = mockEnjeuService.getPlanEnjeux.mock.calls.length;
      component.onEnjeuDelete(mockEnjeu1);
      expect(mockEnjeuService.deleteEnjeu).toHaveBeenCalledWith(1);
      // loadPlanData is called again after delete
      expect(mockEnjeuService.getPlanEnjeux.mock.calls.length).toBeGreaterThan(callsBefore);
    });

    it('should navigate back to list if deleted enjeu was selected', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.onEnjeuDelete(mockEnjeu1);
      expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'enjeux']);
    });

    it('should set errorMessage on delete error', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      mockEnjeuService.deleteEnjeu.mockReturnValue(throwError(() => new Error('fail')));
      component.onEnjeuDelete(mockEnjeu1);
      expect(component.errorMessage()).toBeTruthy();
    });
  });

  // =========================================================================
  // Suppression d'une action / retrait du lien métrique (#457)
  // =========================================================================

  describe('deleteOperation — choix suppression / retrait lien (#457)', () => {
    beforeEach(() => setup());

    const opMultiMetriques = (): any => ({
      id_operation: 42,
      libelle: 'Action multi',
      metriques: [
        { id_metrique: 11, nom_metrique: 'Métrique A', indicateur_type: 'ETAT' },
        { id_metrique: 22, nom_metrique: 'Métrique B', indicateur_type: 'PRESSION' },
      ],
    });

    const opSingleMetrique = (): any => ({
      id_operation: 43,
      libelle: 'Action simple',
      metriques: [
        { id_metrique: 11, nom_metrique: 'Métrique A', indicateur_type: 'ETAT' },
      ],
    });

    it('ouvre le dialogue de choix quand l\'action est liée à plusieurs métriques', () => {
      const mockDialogRef = { afterClosed: () => of({ action: 'cancel' }) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteOperation(opMultiMetriques());
      expect(mockDialogOpen).toHaveBeenCalledWith(DeleteOperationDialogComponent, expect.anything());
      expect(mockEnjeuService.deleteOperation).not.toHaveBeenCalled();
      expect(mockEnjeuService.removeMetriqueFromOperation).not.toHaveBeenCalled();
    });

    it('supprime l\'action entièrement quand le choix est « delete »', () => {
      const mockDialogRef = { afterClosed: () => of({ action: 'delete' }) } as MatDialogRef<any>;
      jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteOperation(opMultiMetriques());
      expect(mockEnjeuService.deleteOperation).toHaveBeenCalledWith(42);
      expect(mockEnjeuService.removeMetriqueFromOperation).not.toHaveBeenCalled();
    });

    it('retire seulement le lien quand le choix est « unlink »', () => {
      const mockDialogRef = { afterClosed: () => of({ action: 'unlink', metriqueIds: [22] }) } as MatDialogRef<any>;
      jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteOperation(opMultiMetriques());
      expect(mockEnjeuService.removeMetriqueFromOperation).toHaveBeenCalledWith(42, 22);
      expect(mockEnjeuService.deleteOperation).not.toHaveBeenCalled();
    });

    it('#538 — retire plusieurs liens en une passe quand plusieurs métriques sont cochées', () => {
      const mockDialogRef = { afterClosed: () => of({ action: 'unlink', metriqueIds: [22, 11] }) } as MatDialogRef<any>;
      jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteOperation(opMultiMetriques());
      expect(mockEnjeuService.removeMetriqueFromOperation).toHaveBeenCalledWith(42, 22);
      expect(mockEnjeuService.removeMetriqueFromOperation).toHaveBeenCalledWith(42, 11);
      expect(mockEnjeuService.deleteOperation).not.toHaveBeenCalled();
    });

    it('utilise la confirmation simple (suppression) pour une action liée à une seule métrique', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteOperation(opSingleMetrique());
      expect(mockDialogOpen).toHaveBeenCalledWith(ConfirmDialogComponent, expect.anything());
      expect(mockDialogOpen).not.toHaveBeenCalledWith(DeleteOperationDialogComponent, expect.anything());
      expect(mockEnjeuService.deleteOperation).toHaveBeenCalledWith(43);
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
        id_type_pression: null,
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

    const mockOlt: ObjectifLongTerme = {
      id_olt: 501, id_enjeu: 1, libelle: 'OLT Test', date_ajout: '', date_maj: '',
    };

    it('should toggle OLT expanded state', () => {
      expect(component.isOltExpanded(501)).toBe(false);
      component.toggleOlt(501);
      expect(component.isOltExpanded(501)).toBe(true);
      component.toggleOlt(501);
      expect(component.isOltExpanded(501)).toBe(false);
    });

    it('should start adding OLT', () => {
      component.startAddOlt();
      expect(component.addingOlt()).toBe(true);
      expect(component.newOltLibelle).toBe('');
    });

    it('should cancel adding OLT', () => {
      component.startAddOlt();
      component.newOltLibelle = 'Test';
      component.cancelAddOlt();
      expect(component.addingOlt()).toBe(false);
      expect(component.newOltLibelle).toBe('');
    });

    it('should call createObjectifLongTerme on save', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newOltLibelle = 'Nouvel OLT';
      component.newOltDescription = 'Desc OLT';
      component.saveOlt();

      expect(mockEnjeuService.createObjectifLongTerme).toHaveBeenCalledWith({
        id_enjeu: 1,
        libelle: 'Nouvel OLT',
        description: 'Desc OLT',
      });
    });

    it('should not save OLT with empty libelle', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newOltLibelle = '   ';
      component.saveOlt();
      expect(mockEnjeuService.createObjectifLongTerme).not.toHaveBeenCalled();
    });

    it('should show confirmation dialog when OLT already exists for enjeu', () => {
      // Simuler un enjeu avec un OLT existant
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      const enjeu = component.selectedEnjeu();
      if (enjeu) {
        enjeu.objectifs_long_terme = [mockOlt];
      }

      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);

      component.startAddOlt();

      expect(mockDialogOpen).toHaveBeenCalled();
    });

    it('should not open form when OLT confirmation dialog is cancelled', () => {
      // Simuler un enjeu avec un OLT existant
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      const enjeu = component.selectedEnjeu();
      if (enjeu) {
        enjeu.objectifs_long_terme = [mockOlt];
      }

      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialogOpen = jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);

      component.startAddOlt();

      expect(component.addingOlt()).toBe(false);
    });

    it('should open form directly when no OLT exists', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      const enjeu = component.selectedEnjeu();
      if (enjeu) {
        enjeu.objectifs_long_terme = [];
      }

      component.startAddOlt();

      expect(component.addingOlt()).toBe(true);
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
        numero_manuel: null,
      });
    });

    it('should send numero_manuel when a fixed number is set (#442)', () => {
      component.startEditOlt(mockOlt);
      component.editOltLibelle = 'OLT fixé';
      component.editOltNumero = 3;
      component.saveEditOlt(mockOlt);
      expect(mockEnjeuService.updateObjectifLongTerme).toHaveBeenCalledWith(501, {
        libelle: 'OLT fixé',
        description: undefined,
        numero_manuel: 3,
      });
    });

    it('should reset numero_manuel to null when field is cleared/zero (#442)', () => {
      component.startEditOlt(mockOlt);
      component.editOltLibelle = 'OLT auto';
      component.editOltNumero = 0;
      component.saveEditOlt(mockOlt);
      expect(mockEnjeuService.updateObjectifLongTerme).toHaveBeenCalledWith(501, {
        libelle: 'OLT auto',
        description: undefined,
        numero_manuel: null,
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
  // Niveau d'exigence
  // =========================================================================

  describe('niveau d\'exigence', () => {
    beforeEach(() => setup());

    const mockOlt: ObjectifLongTerme = {
      id_olt: 501, id_enjeu: 1, libelle: 'OLT Test', date_ajout: '', date_maj: '',
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
      // New direction and inclusivity defaults
      expect(met.sens_variation).toBe('CROISSANT');
      expect(met.score_1_sup_inclusive).toBe(true);
      expect(met.score_2_sup_inclusive).toBe(true);
      expect(met.score_3_sup_inclusive).toBe(true);
      expect(met.score_4_sup_inclusive).toBe(true);
      expect(met.has_score1_optional_bound).toBe(false);
      expect(met.has_score5_optional_bound).toBe(false);
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
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      jest.spyOn(MatDialog.prototype, 'open').mockReturnValue(mockDialogRef);
      component.deleteMetrique({ id_metrique: 901 });
      expect(mockEnjeuService.deleteMetrique).toHaveBeenCalledWith(901);
    });

    it('blocks save when a CHIFFRE active level has no value', () => {
      jest.spyOn(mockEnjeuService, 'createIndicateur');
      const met = component.createEmptyMetrique();
      met.nom_metrique = 'Effectifs';
      // Force type CHIFFRE via stub du mnémonique.
      jest.spyOn(component, 'getMetriqueTypeMnemonique').mockReturnValue('CHIFFRE');
      met.type_metrique = 1351;
      met.scores[1].val = 1;
      // niveau 2 actif mais vide (val null) → doit bloquer
      component.indicateurFormMetriques = [met];
      component.newIndicateurNom = 'Indic';
      const snackSpy = jest.spyOn((component as any).snackBar, 'open');
      component.saveIndicateur({ id_ne: 1 });
      expect(snackSpy).toHaveBeenCalled();
      expect(mockEnjeuService.createIndicateur).not.toHaveBeenCalled();
    });

    it('allows save when CHIFFRE empty level is marked inactive', () => {
      const met = component.createEmptyMetrique();
      met.nom_metrique = 'Effectifs';
      jest.spyOn(component, 'getMetriqueTypeMnemonique').mockReturnValue('CHIFFRE');
      met.scores[1].val = 1; met.scores[3].val = 3; met.scores[4].val = 4; met.scores[5].val = 5;
      met._inactiveLevels = [2];
      component.indicateurFormMetriques = [met];
      component.newIndicateurNom = 'Indic';
      component.saveIndicateur({ id_ne: 1 });
      expect(mockEnjeuService.createIndicateur).toHaveBeenCalled();
    });

    it('nulls bounds of inactive NUMERIQUE levels in payload (principal + block)', () => {
      const met = component.createEmptyMetrique();
      met.nom_metrique = 'Test blocs';
      met.scores[1] = { inf: null, sup: 11, val: null, label: '' };
      met.scores[2] = { inf: 11, sup: 22, val: null, label: '' }; // sera inactivé
      met._inactiveLevels = [2];
      met.score_blocks = [{
        position: 1, intitule: 'élec', unite: 'A', logical_op: 'OR',
        group_open: 0, group_close: 0, sens_variation: 'CROISSANT',
        score_1_inf: null, score_1_sup: 1,
        score_2_inf: 11, score_2_sup: 22, // niveau 2 inactif sur le bloc
        score_3_inf: null, score_3_sup: null,
        score_4_inf: null, score_4_sup: null,
        score_5_inf: null, score_5_sup: null,
        score_1_sup_inclusive: true, score_2_sup_inclusive: true,
        score_3_sup_inclusive: true, score_4_sup_inclusive: true,
        has_borne_score1: false, has_borne_score5: false,
        inactive_levels: [2],
      }];
      const payload = component.buildMetriquePayload(801, met) as any;
      expect(payload.score_2_inf).toBeNull();
      expect(payload.score_2_sup).toBeNull();
      expect(payload.score_blocks[0].score_2_inf).toBeNull();
      expect(payload.score_blocks[0].score_2_sup).toBeNull();
    });

    it('arrondit les bornes de seuil à 4 décimales dans le payload (#575)', () => {
      const met = component.createEmptyMetrique();
      met.nom_metrique = 'Précision';
      met.scores[3] = { inf: 1.111, sup: 4.12345, val: null, label: '' }; // 5 déc.
      met.score_blocks = [{
        position: 1, intitule: 'b', unite: 'u', logical_op: 'OR',
        group_open: 0, group_close: 0, sens_variation: 'CROISSANT',
        score_1_inf: null, score_1_sup: null,
        score_2_inf: null, score_2_sup: null,
        score_3_inf: null, score_3_sup: 2.111119, // 6 déc.
        score_4_inf: null, score_4_sup: null,
        score_5_inf: null, score_5_sup: null,
        score_1_sup_inclusive: true, score_2_sup_inclusive: true,
        score_3_sup_inclusive: true, score_4_sup_inclusive: true,
        has_borne_score1: false, has_borne_score5: false,
        inactive_levels: [],
      }];
      const payload = component.buildMetriquePayload(801, met) as any;
      const decimals = (n: number) => (n.toString().split('.')[1] || '').length;
      // Une saisie ≤ 4 décimales est préservée.
      expect(payload.score_3_inf).toBe(1.111);
      // Une saisie plus précise est ramenée à 4 décimales (max backend).
      expect(decimals(payload.score_3_sup)).toBeLessThanOrEqual(4);
      expect(payload.score_3_sup).toBeCloseTo(4.1235, 4);
      expect(decimals(payload.score_blocks[0].score_3_sup)).toBeLessThanOrEqual(4);
    });

    it('getScoreRange conserve jusqu\'à 4 décimales (#575)', () => {
      const met: any = {
        type_metrique_mnemonique: 'NUMERIQUE',
        sens_variation: 'CROISSANT',
        score_3_inf: 1.111, score_3_sup: 2.111,
        score_2_sup_inclusive: false, score_3_sup_inclusive: true,
      };
      const range = component.getScoreRange(met, 3);
      expect(range).toContain('1.111');
      expect(range).toContain('2.111');
      expect(range).not.toContain('1.11 ');
    });

    it('getScoreRange masque un niveau NUMERIQUE inactif (données résiduelles)', () => {
      const met: any = {
        type_metrique_mnemonique: 'NUMERIQUE',
        inactive_levels: [2],
        score_2_inf: 11, score_2_sup: 22,
      };
      expect(component.getScoreRange(met, 2)).toBe('- - -');
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
      // Direction, inclusivity and bound checkboxes included for NUMERIQUE
      expect(payload.sens_variation).toBe('CROISSANT');
      expect(payload.score_1_sup_inclusive).toBe(true);
      expect(payload.score_2_sup_inclusive).toBe(true);
      expect(payload.score_3_sup_inclusive).toBe(true);
      expect(payload.score_4_sup_inclusive).toBe(true);
      expect(payload.has_borne_score1).toBe(false);
      expect(payload.has_borne_score5).toBe(false);
    });

    it('should return score range with bracket notation', () => {
      // Level 1: leftBracket always '[', rightBracket ']' when sup_inclusive defaults to true
      const met = { score_1_inf: 0, score_1_sup: 2 };
      expect(component.getScoreRange(met, 1)).toBe('[0\u00A0;\u00A02]');
    });

    it('should return bracket notation with exclusive sup', () => {
      // Level 1 with score_1_sup_inclusive=false -> rightBracket = '['
      const met = { score_1_inf: 0, score_1_sup: 20, score_1_sup_inclusive: false };
      expect(component.getScoreRange(met, 1)).toBe('[0\u00A0;\u00A020[');
    });

    it('should return bracket notation for level 2 with previous inclusive', () => {
      // Level 2: leftBracket depends on score_1_sup_inclusive
      // score_1_sup_inclusive=true -> leftBracket = ']' (exclusive inf)
      const met = { score_2_inf: 20, score_2_sup: 40, score_1_sup_inclusive: true };
      expect(component.getScoreRange(met, 2)).toBe(']20\u00A0;\u00A040]');
    });

    it('should return compact notation for inf only (open upper bound)', () => {
      // Level 1, inf only: ≥ 5
      const met = { score_1_inf: 5 };
      expect(component.getScoreRange(met, 1)).toBe('≥\u00A05');
    });

    it('should return compact notation for sup only (open lower bound)', () => {
      // Level 1, sup only: ≤ 10
      const met = { score_1_sup: 10 };
      expect(component.getScoreRange(met, 1)).toBe('≤\u00A010');
    });

    it('should return compact notation with exclusive sup', () => {
      // Level 1, sup only, exclusive: < 10
      const met = { score_1_sup: 10, score_1_sup_inclusive: false };
      expect(component.getScoreRange(met, 1)).toBe('<\u00A010');
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
      id_oo: 1001, pressions: [{id_pression: 301, libelle: 'Pression Urbaine'}], pression_ids: [301], libelle: 'OO Test', date_ajout: '', date_maj: '',
    };

    it('should toggle OO expanded state', () => {
      expect(component.isOoExpanded(1001)).toBe(false);
      component.toggleOo(1001);
      expect(component.isOoExpanded(1001)).toBe(true);
      component.toggleOo(1001);
      expect(component.isOoExpanded(1001)).toBe(false);
    });

    it('should start adding OO and reset pression ids', () => {
      component.newOoPressionIds = [301];
      component.startAddOo();
      expect(component.addingOo()).toBe(true);
      expect(component.newOoLibelle).toBe('');
      expect(component.newOoPressionIds).toEqual([]);
    });

    it('should cancel adding OO and reset pression ids', () => {
      component.startAddOo();
      component.newOoLibelle = 'Test';
      component.newOoPressionIds = [301];
      component.cancelAddOo();
      expect(component.addingOo()).toBe(false);
      expect(component.newOoLibelle).toBe('');
      expect(component.newOoPressionIds).toEqual([]);
    });

    it('should call createObjectifOperationnel on save', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newOoLibelle = 'Nouvel OO';
      component.newOoDescription = 'Desc OO';
      component.newOoPressionIds = [301];
      component.saveOo();

      expect(mockEnjeuService.createObjectifOperationnel).toHaveBeenCalledWith(expect.objectContaining({
        pression_ids: [301],
        libelle: 'Nouvel OO',
        description: 'Desc OO',
      }));
    });

    it('should not save OO with empty libelle', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newOoLibelle = '   ';
      component.newOoPressionIds = [301];
      component.saveOo();
      expect(mockEnjeuService.createObjectifOperationnel).not.toHaveBeenCalled();
    });

    it('should not save OO without pression', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.newOoLibelle = 'Nouvel OO';
      component.newOoPressionIds = [];
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
        pression_ids: [301],
        libelle: 'OO modifié',
        numero_manuel: null,
      }));
    });

    it('should send numero_manuel when a fixed number is set (#526)', () => {
      component.startEditOo(mockOo);
      component.editOoLibelle = 'OO fixé';
      component.editOoNumero = 3;
      component.saveEditOo(mockOo);
      expect(mockEnjeuService.updateObjectifOperationnel).toHaveBeenCalledWith(1001, expect.objectContaining({
        numero_manuel: 3,
      }));
    });

    it('should reset numero_manuel to null when field is cleared/zero (#526)', () => {
      component.startEditOo(mockOo);
      component.editOoLibelle = 'OO auto';
      component.editOoNumero = 0;
      component.saveEditOo(mockOo);
      expect(mockEnjeuService.updateObjectifOperationnel).toHaveBeenCalledWith(1001, expect.objectContaining({
        numero_manuel: null,
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
      component.editOoPressionIds = [];
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
      id_oo: 1001, pressions: [{id_pression: 301, libelle: 'Pression Urbaine'}], pression_ids: [301], libelle: 'OO Test', date_ajout: '', date_maj: '',
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
  // Boutons « Je n'ai pas de … » (#523)
  // =========================================================================

  describe('boutons « Je n\'ai pas de … » (#523)', () => {
    beforeEach(() => setup());

    const placeholder = 'enjeux.undefined.label';

    it('createUndefinedFacteur crée un facteur « Non défini » et affiche la préconisation', () => {
      component['selectedEnjeuSlug'].set('protection-zones-humides');
      component.createUndefinedFacteur();
      expect(mockEnjeuService.createFacteurInfluence).toHaveBeenCalledWith({
        id_enjeu: 1,
        libelle: placeholder,
      });
      expect(mockSnackBarOpen).toHaveBeenCalled();
    });

    it('createUndefinedPression crée une pression « Non défini »', () => {
      const facteur: FacteurInfluence = {
        id_facteur_influence: 101, id_enjeu: 1, libelle: 'F', date_ajout: '', date_maj: '',
      };
      component.createUndefinedPression(facteur);
      expect(mockEnjeuService.createPression).toHaveBeenCalledWith({
        id_facteur_influence: 101,
        libelle: placeholder,
      });
    });

    it('createUndefinedNe crée un niveau d\'exigence « Non défini »', () => {
      const olt: ObjectifLongTerme = {
        id_olt: 501, id_enjeu: 1, libelle: 'OLT', date_ajout: '', date_maj: '',
      };
      component.createUndefinedNe(olt);
      expect(mockEnjeuService.createNiveauExigence).toHaveBeenCalledWith({
        id_olt: 501,
        libelle: placeholder,
      });
    });

    it('createUndefinedRa crée un résultat attendu « Non défini »', () => {
      const oo: ObjectifOperationnel = {
        id_oo: 1001, pressions: [], pression_ids: [], libelle: 'OO', date_ajout: '', date_maj: '',
      };
      component.createUndefinedRa(oo);
      expect(mockEnjeuService.createResultatAttendu).toHaveBeenCalledWith({
        id_oo: 1001,
        libelle: placeholder,
      });
    });

    it('createUndefinedIndicateur crée un indicateur d\'état « Non défini » sur le NE', () => {
      const ne: NiveauExigence = {
        id_ne: 701, id_olt: 501, libelle: 'NE', date_ajout: '', date_maj: '',
      };
      component.createUndefinedIndicateur(ne);
      expect(mockEnjeuService.createIndicateur).toHaveBeenCalledWith({
        id_ne: 701,
        nom_indicateur: placeholder,
        est_standardise: false,
      });
    });

    it('createUndefinedIndicateurForRa crée un indicateur de pression « Non défini » sur le RA', () => {
      const ra: ResultatAttendu = {
        id_ra: 1101, id_oo: 1001, libelle: 'RA', date_ajout: '', date_maj: '',
      };
      component.createUndefinedIndicateurForRa(ra);
      expect(mockEnjeuService.createIndicateur).toHaveBeenCalledWith({
        id_resultat_attendu: 1101,
        nom_indicateur: placeholder,
        est_standardise: false,
      });
    });

    it('affiche errorMessage si la création du placeholder échoue', () => {
      mockEnjeuService.createNiveauExigence.mockReturnValue(throwError(() => new Error('fail')));
      const olt: ObjectifLongTerme = {
        id_olt: 501, id_enjeu: 1, libelle: 'OLT', date_ajout: '', date_maj: '',
      };
      component.createUndefinedNe(olt);
      expect(component.errorMessage()).toBeTruthy();
    });
  });

  // =========================================================================
  // Error handling
  // =========================================================================

  describe('error handling', () => {
    it('should set errorMessage on loadPlanData failure', () => {
      const errorEnjeuService = {
        getPlanEnjeux: jest.fn().mockReturnValue(throwError(() => new Error('Network error'))),
        currentPlanEnjeux: jest.fn().mockReturnValue(null),
        updatePlanEnjeuxCache: jest.fn(),
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
              fragment: of(null),
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

  // =========================================================================
  // #249 / #261 — Drag-and-drop reorder
  // =========================================================================
  describe('drag-and-drop reorder', () => {
    function dropEvent(previousIndex: number, currentIndex: number): any {
      return { previousIndex, currentIndex };
    }

    it('onEnjeuDrop calls ReorderService.reorder with planId and ordered ids', () => {
      setup();
      component['planId'].set(10);
      // Override planEnjeuxData to ensure enjeux() returns at least 2 items
      const reorderSpy = jest.spyOn(component['reorderService'], 'reorder').mockReturnValue(of({ updated: 2 }));

      component.onEnjeuDrop(dropEvent(0, 1));

      expect(reorderSpy).toHaveBeenCalledWith(
        'enjeux',
        expect.objectContaining({
          parent_id: 10,
          // 2 enjeux dans le mock : id_enjeu 1 et 3 ; après swap → [3, 1]
          ordered_ids: [3, 1],
        }),
      );
      reorderSpy.mockRestore();
    });

    it('onEnjeuDrop rolls back (reloads data) when reorder API fails', () => {
      setup();
      component['planId'].set(10);
      const reorderSpy = jest.spyOn(component['reorderService'], 'reorder').mockReturnValue(
        throwError(() => new Error('boom')),
      );
      // Reset the call count for loadPlanData via getPlanEnjeux
      mockEnjeuService.getPlanEnjeux.mockClear();

      component.onEnjeuDrop(dropEvent(0, 1));

      expect(reorderSpy).toHaveBeenCalled();
      // Rollback : nouveau fetch des données (silent=true)
      expect(mockEnjeuService.getPlanEnjeux).toHaveBeenCalled();
      reorderSpy.mockRestore();
    });

    it('onIndicateurNeDrop forwards parent_type=ne for indicators of a NE', () => {
      setup();
      const reorderSpy = jest.spyOn(component['reorderService'], 'reorder').mockReturnValue(of({ updated: 2 }));

      const ne = {
        id_ne: 99,
        indicateurs: [
          { id_indicateur: 10, nom_indicateur: 'A' },
          { id_indicateur: 11, nom_indicateur: 'B' },
        ],
      } as any;

      component.onIndicateurNeDrop(dropEvent(0, 1), ne);

      expect(reorderSpy).toHaveBeenCalledWith(
        'indicateurs',
        expect.objectContaining({
          parent_id: 99,
          ordered_ids: [11, 10],
          parent_type: 'ne',
        }),
      );
      reorderSpy.mockRestore();
    });

    it('onIndicateurRaDrop forwards parent_type=ra for indicators of a RA', () => {
      setup();
      const reorderSpy = jest.spyOn(component['reorderService'], 'reorder').mockReturnValue(of({ updated: 2 }));

      const ra = {
        id_ra: 77,
        indicateurs: [
          { id_indicateur: 20, nom_indicateur: 'A' },
          { id_indicateur: 21, nom_indicateur: 'B' },
        ],
      } as any;

      component.onIndicateurRaDrop(dropEvent(0, 1), ra);

      expect(reorderSpy).toHaveBeenCalledWith(
        'indicateurs',
        expect.objectContaining({
          parent_id: 77,
          ordered_ids: [21, 20],
          parent_type: 'ra',
        }),
      );
      reorderSpy.mockRestore();
    });

    it('isAnyInlineEditActive locks drag while an inline edit form is open (#559)', () => {
      setup();
      expect(component.isAnyInlineEditActive()).toBe(false);

      component.editingOltId.set(42);
      expect(component.isAnyInlineEditActive()).toBe(true);

      component.editingOltId.set(null);
      expect(component.isAnyInlineEditActive()).toBe(false);

      component.editingIndicateurId.set(7);
      expect(component.isAnyInlineEditActive()).toBe(true);
      component.editingIndicateurId.set(null);
    });

    it('onOperationDrop forwards parent_type=indicateur for actions of an indicator (#544)', () => {
      setup();
      const reorderSpy = jest.spyOn(component['reorderService'], 'reorder').mockReturnValue(of({ updated: 2 }));

      const ind = {
        id_indicateur: 55,
        operations: [
          { id_operation: 30, libelle: 'CS1' },
          { id_operation: 31, libelle: 'CS2' },
        ],
      } as any;

      component.onOperationDrop(dropEvent(0, 1), ind);

      expect(reorderSpy).toHaveBeenCalledWith(
        'operations',
        expect.objectContaining({
          parent_id: 55,
          ordered_ids: [31, 30],
          parent_type: 'indicateur',
        }),
      );
      reorderSpy.mockRestore();
    });

    it('does not call reorder API when previous and current index are equal (no-op)', () => {
      setup();
      component['planId'].set(10);
      const reorderSpy = jest.spyOn(component['reorderService'], 'reorder');

      component.onEnjeuDrop(dropEvent(1, 1));

      expect(reorderSpy).not.toHaveBeenCalled();
      reorderSpy.mockRestore();
    });

    // #472 — déplacement de pression entre facteurs d'influence
    it('onPressionDrop reorders within the same facteur (same container)', () => {
      setup();
      const reorderSpy = jest.spyOn(component['reorderService'], 'reorder').mockReturnValue(of({ updated: 2 }));
      const facteur = {
        id_facteur_influence: 5,
        pressions: [{ id_pression: 1 }, { id_pression: 2 }],
      } as any;
      const sameContainer = { data: facteur.pressions };
      const event = {
        previousIndex: 0,
        currentIndex: 1,
        previousContainer: sameContainer,
        container: sameContainer,
      } as any;

      component.onPressionDrop(event, facteur);

      expect(reorderSpy).toHaveBeenCalledWith(
        'pressions',
        expect.objectContaining({ parent_id: 5, ordered_ids: [2, 1] }),
      );
      reorderSpy.mockRestore();
    });

    it('onPressionDrop moves a pression to another facteur (cross container)', () => {
      setup();
      const moveSpy = jest.spyOn(component['reorderService'], 'movePression').mockReturnValue(of({}));
      const targetFacteur = { id_facteur_influence: 8, pressions: [] } as any;
      const event = {
        previousIndex: 0,
        currentIndex: 0,
        previousContainer: { data: [{ id_pression: 42 }] },
        container: { data: targetFacteur.pressions },
      } as any;

      component.onPressionDrop(event, targetFacteur);

      expect(moveSpy).toHaveBeenCalledWith(42, { new_facteur_id: 8, position: 0 });
      moveSpy.mockRestore();
    });

    it('connectedPressionDroplistIds excludes the current facteur', () => {
      setup();
      jest.spyOn(component, 'selectedFacteurs').mockReturnValue([
        { id_facteur_influence: 1 },
        { id_facteur_influence: 2 },
        { id_facteur_influence: 3 },
      ] as any);

      expect(component.connectedPressionDroplistIds(2)).toEqual([
        'pressions-droplist-1',
        'pressions-droplist-3',
      ]);
    });
  });
});
