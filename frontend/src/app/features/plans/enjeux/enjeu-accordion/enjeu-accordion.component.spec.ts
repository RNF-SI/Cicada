import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';

import { EnjeuAccordionComponent } from './enjeu-accordion.component';
import { Enjeu } from '../../../../core/models/enjeu.model';

/**
 * Fake translate loader that returns the key as value.
 */
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(_lang: string): Observable<any> {
    return of({
      enjeux: {
        types: { enjeu: 'Enjeu', fcr: 'FCR' },
        enjeuForm: {
          ecologique: 'Écologique',
          socioEconomique: 'Socio-économique',
          enjeuLieAEcologique: 'L\'enjeu est lié à :',
          enjeuLieASocioEco: 'L\'enjeu est lié :',
          habitat: 'Un/des habitat(s)',
          espece: 'Une/des espèce(s)',
          patrimoineGeologique: 'Du patrimoine géologique',
          fonctionnaliteEcosysteme: 'Une/des fonctionnalité(s) des écosystèmes',
          autreEcologique: 'Autre',
          valeurPaysagere: 'à la valeur paysagère',
          patrimoineCulturel: 'au maintien du patrimoine culturel',
          developpementDurable: 'au développement durable des ressources',
          usages: 'aux usages',
          valeurAjoutee: 'à une/des valeurs ajoutées sociale, économique, scientifique ou éducative',
          autreSocioEco: 'Autre (socio-éco)',
        },
        fcrForm: { categorie: 'Catégorie' },
        accordion: {
          priorite: 'Priorité',
          categorie: 'Catégorie',
          enjeuLieA: 'Lié à',
          habitats: 'Habitats',
          especes: 'Espèces',
          processus: 'Processus',
          listeEspeces: 'Espèces',
          listeHabitats: 'Habitats',
          voirListe: 'Voir la liste',
          etatEnjeu: 'État',
          detailsCommentaires: 'Détails',
        },
        facteurInfluence: {
          countSuffix: 'facteur(s)',
          viewButton: 'Voir les facteurs',
        },
        messages: {
          enjeuDeleteConfirmTitle: 'Supprimer l\'enjeu',
          enjeuDeleteConfirm: 'Êtes-vous sûr ?',
          fcrDeleteConfirmTitle: 'Supprimer le FCR',
          fcrDeleteConfirm: 'Êtes-vous sûr ?',
        },
      },
      common: {
        actions: {
          edit: 'Modifier',
          delete: 'Supprimer',
          cancel: 'Annuler',
        },
        createdAt: 'Créé le',
        by: 'par',
      },
    });
  }
}

describe('EnjeuAccordionComponent', () => {
  let component: EnjeuAccordionComponent;
  let fixture: ComponentFixture<EnjeuAccordionComponent>;
  let mockDialog: jest.Mocked<MatDialog>;

  const baseEnjeu: Enjeu = {
    id_enjeu: 1,
    id_pg: 10,
    id_categorie: 100,
    categorie_mnemonique: 'ENJEU',
    categorie_label: 'Enjeu de conservation',
    libelle: 'Protection zones humides',
    intitule_court: 'Zones humides',
    rang: 1,
    categorie_ecologique: true,
    habitat: true,
    espece: true,
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
    nb_facteurs_influence: 3,
    nb_taxons: 5,
    nb_habitats: 2,
    date_ajout: '2024-01-01T00:00:00Z',
    date_maj: '2024-01-15T00:00:00Z',
    createur_nom: 'Jean Dupont',
  };

  const baseFcr: Enjeu = {
    id_enjeu: 2,
    id_pg: 10,
    id_categorie: 101,
    categorie_mnemonique: 'FCR',
    categorie_label: 'FCR',
    libelle: 'Connaissance scientifique',
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
    categorie_fcr_label: 'Connaissance',
    date_ajout: '2024-01-01T00:00:00Z',
    date_maj: '2024-01-01T00:00:00Z',
  };

  beforeEach(async () => {
    mockDialog = {
      open: jest.fn(),
    } as unknown as jest.Mocked<MatDialog>;

    await TestBed.configureTestingModule({
      imports: [
        EnjeuAccordionComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
        }),
      ],
    })
    .overrideComponent(EnjeuAccordionComponent, {
      add: { providers: [{ provide: MatDialog, useValue: mockDialog }] },
    })
    .compileComponents();

    const translate = TestBed.inject(TranslateService);
    translate.use('fr');

    fixture = TestBed.createComponent(EnjeuAccordionComponent);
    component = fixture.componentInstance;
    component.enjeu = { ...baseEnjeu };
    fixture.detectChanges();
  });

  // =========================================================================
  // Initialization and inputs
  // =========================================================================

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should start collapsed by default', () => {
      expect(component.expanded()).toBe(false);
    });

    it('should start expanded when initiallyExpanded=true', () => {
      component.initiallyExpanded = true;
      component.ngOnInit();
      expect(component.expanded()).toBe(true);
    });

    it('should apply .fcr class when isFcr=true', () => {
      component.isFcr = true;
      fixture.detectChanges();
      const el = fixture.nativeElement.querySelector('.accordion');
      expect(el.classList.contains('fcr')).toBe(true);
    });
  });

  // =========================================================================
  // Toggle and events
  // =========================================================================

  describe('toggle and events', () => {
    it('should toggle expanded signal', () => {
      expect(component.expanded()).toBe(false);
      component.toggle();
      expect(component.expanded()).toBe(true);
      component.toggle();
      expect(component.expanded()).toBe(false);
    });

    it('should emit edit event with enjeu', () => {
      const spy = jest.spyOn(component.edit, 'emit');
      const mockEvent = { stopPropagation: jest.fn() } as unknown as Event;
      component.onEdit(mockEvent);
      expect(mockEvent.stopPropagation).toHaveBeenCalled();
      expect(spy).toHaveBeenCalledWith(baseEnjeu);
    });

    it('should stop propagation on edit', () => {
      const mockEvent = { stopPropagation: jest.fn() } as unknown as Event;
      component.onEdit(mockEvent);
      expect(mockEvent.stopPropagation).toHaveBeenCalled();
    });

    it('should emit navigateToDetail event', () => {
      const spy = jest.spyOn(component.navigateToDetail, 'emit');
      const mockEvent = { stopPropagation: jest.fn() } as unknown as Event;
      component.onNavigateToDetail(mockEvent);
      expect(spy).toHaveBeenCalledWith(baseEnjeu);
    });
  });

  // =========================================================================
  // Computed getters
  // =========================================================================

  describe('computed getters', () => {
    it('should return categoryLabel "Écologique" for ecological', () => {
      component.enjeu = { ...baseEnjeu, categorie_ecologique: true, categorie_socio_economique: false };
      expect(component.categoryLabel).toBe('Écologique');
    });

    it('should return categoryLabel "Socio-économique" for non-ecological', () => {
      component.enjeu = { ...baseEnjeu, categorie_ecologique: false, categorie_socio_economique: true };
      expect(component.categoryLabel).toBe('Socio-économique');
    });

    it('should return transversal categoryLabel when both categories are true (#260)', () => {
      component.enjeu = { ...baseEnjeu, categorie_ecologique: true, categorie_socio_economique: true };
      // Le test utilise le translate stub qui renvoie la clé brute
      expect(component.categoryLabel).toBe('enjeux.enjeuForm.transversal');
    });

    it('should return empty string categoryLabel when undefined', () => {
      component.enjeu = { ...baseEnjeu, categorie_ecologique: undefined };
      expect(component.categoryLabel).toBe('');
    });

    it('should return typeLabels for ecological checkboxes', () => {
      component.enjeu = { ...baseEnjeu, habitat: true, espece: true, patrimoine_geologique: false };
      const labels = component.typeLabels;
      expect(labels).toContain('Un/des habitat(s)');
      expect(labels).toContain('Une/des espèce(s)');
      expect(labels).not.toContain('Du patrimoine géologique');
    });

    it('should return typeLabels for all ecological types', () => {
      component.enjeu = {
        ...baseEnjeu,
        habitat: true, espece: true, patrimoine_geologique: true,
        fonctionnalite_ecosysteme: true, autre_ecologique: true,
      };
      expect(component.typeLabels.length).toBe(5);
    });

    it('should return typeLabels for socio-economic checkboxes', () => {
      component.enjeu = {
        ...baseEnjeu,
        categorie_ecologique: false,
        habitat: false, espece: false,
        valeur_paysagere: true, patrimoine_culturel: true, usages: false,
      };
      const labels = component.typeLabels;
      expect(labels).toContain('à la valeur paysagère');
      expect(labels).toContain('au maintien du patrimoine culturel');
      expect(labels).not.toContain('aux usages');
    });

    it('should return fcrCategoryLabel', () => {
      component.enjeu = { ...baseFcr };
      expect(component.fcrCategoryLabel).toBe('Connaissance');
    });

    it('should return hasTaxons true with taxons array', () => {
      component.enjeu = {
        ...baseEnjeu,
        taxons: [{ cd_nom: 1 }],
        nb_taxons: 0,
      };
      expect(component.hasTaxons).toBe(true);
    });

    it('should return hasTaxons true with nb_taxons > 0', () => {
      component.enjeu = { ...baseEnjeu, taxons: [], nb_taxons: 5 };
      expect(component.hasTaxons).toBe(true);
    });

    it('should return hasHabitats true with habitats array', () => {
      component.enjeu = {
        ...baseEnjeu,
        habitats: [{ cd_hab: 'H1' }],
        nb_habitats: 0,
      };
      expect(component.hasHabitats).toBe(true);
    });

    it('should return facteurCount from facteurs_influence array', () => {
      component.enjeu = {
        ...baseEnjeu,
        facteurs_influence: [
          { id_facteur_influence: 1, id_enjeu: 1, libelle: 'F1', date_ajout: '', date_maj: '' },
          { id_facteur_influence: 2, id_enjeu: 1, libelle: 'F2', date_ajout: '', date_maj: '' },
        ],
        nb_facteurs_influence: undefined,
      };
      expect(component.facteurCount).toBe(2);
    });

    it('should return facteurCount from nb_facteurs_influence', () => {
      component.enjeu = { ...baseEnjeu, facteurs_influence: undefined, nb_facteurs_influence: 5 };
      expect(component.facteurCount).toBe(5);
    });

    it('should return taxonCount', () => {
      component.enjeu = { ...baseEnjeu, taxons: undefined, nb_taxons: 3 };
      expect(component.taxonCount).toBe(3);
    });

    it('should return habitatCount', () => {
      component.enjeu = { ...baseEnjeu, habitats: undefined, nb_habitats: 4 };
      expect(component.habitatCount).toBe(4);
    });
  });

  // =========================================================================
  // Delete dialog
  // =========================================================================

  describe('delete dialog', () => {
    it('should open dialog for enjeu delete', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialog.open.mockReturnValue(mockDialogRef);

      const mockEvent = { stopPropagation: jest.fn() } as unknown as Event;
      component.isFcr = false;
      component.onDelete(mockEvent);

      expect(mockDialog.open).toHaveBeenCalled();
      const dialogData = mockDialog.open.mock.calls[0][1]?.data as any;
      expect(dialogData.title).toBe('Supprimer l\'enjeu');
    });

    it('should open dialog for FCR delete with FCR title', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialog.open.mockReturnValue(mockDialogRef);

      const mockEvent = { stopPropagation: jest.fn() } as unknown as Event;
      component.isFcr = true;
      component.onDelete(mockEvent);

      const dialogData = mockDialog.open.mock.calls[0][1]?.data as any;
      expect(dialogData.title).toBe('Supprimer le FCR');
    });

    it('should not emit delete when dialog is cancelled', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialog.open.mockReturnValue(mockDialogRef);
      const spy = jest.spyOn(component.delete, 'emit');

      const mockEvent = { stopPropagation: jest.fn() } as unknown as Event;
      component.onDelete(mockEvent);

      expect(spy).not.toHaveBeenCalled();
    });

    it('should emit delete when dialog is confirmed', () => {
      const mockDialogRef = { afterClosed: () => of(true) } as MatDialogRef<any>;
      mockDialog.open.mockReturnValue(mockDialogRef);
      const spy = jest.spyOn(component.delete, 'emit');

      const mockEvent = { stopPropagation: jest.fn() } as unknown as Event;
      component.onDelete(mockEvent);

      expect(spy).toHaveBeenCalledWith(baseEnjeu);
    });

    it('should use confirmColor warn', () => {
      const mockDialogRef = { afterClosed: () => of(false) } as MatDialogRef<any>;
      mockDialog.open.mockReturnValue(mockDialogRef);

      const mockEvent = { stopPropagation: jest.fn() } as unknown as Event;
      component.onDelete(mockEvent);

      const dialogData = mockDialog.open.mock.calls[0][1]?.data as any;
      expect(dialogData.confirmColor).toBe('warn');
    });
  });
});
