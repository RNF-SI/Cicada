import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialog } from '@angular/material/dialog';
import { MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { of } from 'rxjs';
import { ReferenceItemListComponent } from './reference-item-list.component';
import { TaxonomyService } from '../../../core/services/taxonomy.service';
import { HabitatService } from '../../../core/services/habitat.service';
import { GeologyService } from '../../../core/services/geology.service';
import { TaxonRef, HabitatRef } from '../../../core/models/enjeu.model';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation() {
    return of({
      'enjeux.referenceList.taxonCount': '{{count}} taxon(s)',
      'enjeux.referenceList.habitatCount': '{{count}} habitat(s)',
      'enjeux.referenceList.geologyCount': '{{count}} site(s)',
      'enjeux.referenceList.importList': 'Importer',
      'enjeux.referenceList.searchTaxon': 'Rechercher un taxon',
      'enjeux.referenceList.searchHabitat': 'Rechercher un habitat',
      'enjeux.referenceList.searchGeology': 'Rechercher un site',
      'enjeux.referenceList.searchTaxonPlaceholder': 'Nom...',
      'enjeux.referenceList.searchHabitatPlaceholder': 'Nom...',
      'enjeux.referenceList.searchGeologyPlaceholder': 'Nom...',
      'enjeux.referenceList.searchHint': 'Min 2 caractères',
      'common.actions.delete': 'Supprimer'
    });
  }
}

describe('ReferenceItemListComponent', () => {
  let component: ReferenceItemListComponent;
  let fixture: ComponentFixture<ReferenceItemListComponent>;
  let taxonomyService: { autocomplete: jest.Mock; validateBulk: jest.Mock };
  let habitatService: { autocomplete: jest.Mock; validateBulk: jest.Mock };
  let geologyService: { autocomplete: jest.Mock; validateBulk: jest.Mock };
  let dialog: { open: jest.Mock };

  beforeEach(async () => {
    taxonomyService = {
      autocomplete: jest.fn().mockReturnValue(of([])),
      validateBulk: jest.fn().mockReturnValue(of({ found: [], not_found: [] })),
    };
    habitatService = {
      autocomplete: jest.fn().mockReturnValue(of([])),
      validateBulk: jest.fn().mockReturnValue(of({ found: [], not_found: [] })),
    };
    geologyService = {
      autocomplete: jest.fn().mockReturnValue(of([])),
      validateBulk: jest.fn().mockReturnValue(of({ found: [], not_found: [] })),
    };
    dialog = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(null) }),
    };

    await TestBed.configureTestingModule({
      imports: [
        ReferenceItemListComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          defaultLanguage: 'fr'
        })
      ],
      providers: [
        { provide: TaxonomyService, useValue: taxonomyService },
        { provide: HabitatService, useValue: habitatService },
        { provide: GeologyService, useValue: geologyService },
        { provide: MatDialog, useValue: dialog },
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ReferenceItemListComponent);
    component = fixture.componentInstance;
  });

  // ==========================================
  // Initialization
  // ==========================================
  describe('initialization', () => {
    it('should create', () => {
      fixture.detectChanges();
      expect(component).toBeTruthy();
    });

    it('should default to taxon type', () => {
      fixture.detectChanges();
      expect(component.type).toBe('taxon');
    });

    it('should start with empty items', () => {
      fixture.detectChanges();
      expect(component.items).toEqual([]);
    });

    it('should start with empty autocomplete results', () => {
      fixture.detectChanges();
      expect(component.autocompleteResults()).toEqual([]);
    });
  });

  // ==========================================
  // Autocomplete search
  // ==========================================
  describe('autocomplete search', () => {
    it('should search taxons when type is taxon', fakeAsync(() => {
      component.type = 'taxon';
      fixture.detectChanges();

      taxonomyService.autocomplete!.mockReturnValue(of([
        { cd_nom: 60345, lb_nom: 'Lynx lynx', nom_valide: 'Lynx lynx', nom_vern: 'Lynx boréal', regne: 'Animalia' }
      ]));

      component.searchControl.setValue('Lynx');
      tick(300); // debounce

      // #238 — limit dynamique : 'Lynx' (4 chars) → limit=50
      expect(taxonomyService.autocomplete).toHaveBeenCalledWith('Lynx', { limit: 50 });
      expect(component.autocompleteResults().length).toBe(1);
    }));

    it('should search habitats when type is habitat', fakeAsync(() => {
      component.type = 'habitat';
      fixture.detectChanges();

      habitatService.autocomplete!.mockReturnValue(of([
        { cd_hab: 16265, lb_hab_fr: 'Hêtraies acidiphiles', search_name: 'Hêtraies' }
      ]));

      component.searchControl.setValue('Hêt');
      tick(300);

      expect(habitatService.autocomplete).toHaveBeenCalledWith('Hêt', { limit: 20 });
    }));

    it('should not search with less than 2 characters', fakeAsync(() => {
      component.type = 'taxon';
      fixture.detectChanges();

      component.searchControl.setValue('L');
      tick(300);

      expect(taxonomyService.autocomplete).not.toHaveBeenCalled();
      expect(component.autocompleteResults()).toEqual([]);
    }));
  });

  // ==========================================
  // Autocomplete selection
  // ==========================================
  describe('onAutocompleteSelected', () => {
    it('should add a taxon when selected', () => {
      component.type = 'taxon';
      component.items = [];
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.itemsChange, 'emit');
      const event = {
        option: {
          value: { cd_nom: 60345, lb_nom: 'Lynx lynx', nom_valide: 'Lynx lynx', nom_vern: 'Lynx boréal', regne: 'Animalia', id_rang: 'ES' }
        }
      } as MatAutocompleteSelectedEvent;

      component.onAutocompleteSelected(event);

      expect(component.items.length).toBe(1);
      expect((component.items[0] as TaxonRef).cd_nom).toBe(60345);
      expect((component.items[0] as TaxonRef).id_rang).toBe('ES');
      expect(emitSpy).toHaveBeenCalled();
    });

    it('should preserve id_rang for higher-rank taxa (family, order, etc.)', () => {
      component.type = 'taxon';
      component.items = [];
      fixture.detectChanges();

      const event = {
        option: {
          value: { cd_nom: 186210, lb_nom: 'Cervidae', nom_valide: 'Cervidae Goldfuss, 1820', nom_vern: 'Cerfs, Chevreuils', regne: 'Animalia', id_rang: 'FM' }
        }
      } as MatAutocompleteSelectedEvent;

      component.onAutocompleteSelected(event);

      expect((component.items[0] as TaxonRef).id_rang).toBe('FM');
    });

    it('should not add duplicate taxon', () => {
      component.type = 'taxon';
      component.items = [{ cd_nom: 60345, nom_complet: 'Lynx lynx' }];
      fixture.detectChanges();

      const event = {
        option: {
          value: { cd_nom: 60345, lb_nom: 'Lynx lynx', nom_valide: 'Lynx lynx', nom_vern: '', regne: 'Animalia' }
        }
      } as MatAutocompleteSelectedEvent;

      component.onAutocompleteSelected(event);

      expect(component.items.length).toBe(1);
    });

    it('should add a habitat when selected', () => {
      component.type = 'habitat';
      component.items = [];
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.itemsChange, 'emit');
      const event = {
        option: {
          value: { cd_hab: 16265, lb_hab_fr: 'Hêtraies acidiphiles', search_name: 'Hêtraies' }
        }
      } as MatAutocompleteSelectedEvent;

      component.onAutocompleteSelected(event);

      expect(component.items.length).toBe(1);
      expect((component.items[0] as HabitatRef).cd_hab).toBe('16265');
      expect(emitSpy).toHaveBeenCalled();
    });

    it('should clear search after selection', () => {
      component.type = 'taxon';
      component.items = [];
      fixture.detectChanges();

      const event = {
        option: {
          value: { cd_nom: 60345, lb_nom: 'Lynx lynx', nom_valide: 'Lynx lynx', nom_vern: '', regne: 'Animalia' }
        }
      } as MatAutocompleteSelectedEvent;

      component.onAutocompleteSelected(event);

      expect(component.searchControl.value).toBe('');
      expect(component.autocompleteResults()).toEqual([]);
    });

    it('should ignore null selection', () => {
      component.type = 'taxon';
      fixture.detectChanges();

      const event = { option: { value: null } } as MatAutocompleteSelectedEvent;
      component.onAutocompleteSelected(event);

      expect(component.items.length).toBe(0);
    });
  });

  // ==========================================
  // Remove item
  // ==========================================
  describe('removeItem', () => {
    it('should remove item at given index', () => {
      component.type = 'taxon';
      component.items = [
        { cd_nom: 1, nom_complet: 'Species A' },
        { cd_nom: 2, nom_complet: 'Species B' },
        { cd_nom: 3, nom_complet: 'Species C' },
      ];
      fixture.detectChanges();

      const emitSpy = jest.spyOn(component.itemsChange, 'emit');
      component.removeItem(1);

      expect(component.items.length).toBe(2);
      expect((component.items[0] as TaxonRef).cd_nom).toBe(1);
      expect((component.items[1] as TaxonRef).cd_nom).toBe(3);
      expect(emitSpy).toHaveBeenCalled();
    });
  });

  // ==========================================
  // Import dialog
  // ==========================================
  describe('openImportDialog', () => {
    it('should open dialog with correct width for taxon', () => {
      component.type = 'taxon';
      component.items = [{ cd_nom: 60345, nom_complet: 'Lynx' }];
      fixture.detectChanges();

      component.openImportDialog();

      expect(dialog.open).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          width: '1300px',
          maxWidth: '95vw',
          maxHeight: '90vh',
          data: { type: 'taxon', existingCodes: [60345] },
        })
      );
    });

    it('should open dialog with habitat codes', () => {
      component.type = 'habitat';
      component.items = [{ cd_hab: '16265', lb_hab_fr: 'Hêtraies' }];
      fixture.detectChanges();

      component.openImportDialog();

      expect(dialog.open).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          data: { type: 'habitat', existingCodes: ['16265'] },
        })
      );
    });

    it('should add imported items on dialog close', () => {
      component.type = 'taxon';
      component.items = [];
      fixture.detectChanges();

      const importedItems = [
        { code: 60345, label: 'Lynx lynx', secondaryLabel: 'Lynx', input: '60345', valid: true },
        { code: 2852, label: 'Bufo bufo', input: '2852', valid: true },
      ];

      dialog.open!.mockReturnValue({
        afterClosed: () => of({ items: importedItems })
      } as any);

      const emitSpy = jest.spyOn(component.itemsChange, 'emit');
      component.openImportDialog();

      expect(component.items.length).toBe(2);
      expect((component.items[0] as TaxonRef).cd_nom).toBe(60345);
      expect((component.items[1] as TaxonRef).cd_nom).toBe(2852);
      expect(emitSpy).toHaveBeenCalled();
    });

    it('should not add duplicates from import', () => {
      component.type = 'taxon';
      component.items = [{ cd_nom: 60345, nom_complet: 'Lynx lynx' }];
      fixture.detectChanges();

      const importedItems = [
        { code: 60345, label: 'Lynx lynx', input: '60345', valid: true },
        { code: 2852, label: 'Bufo bufo', input: '2852', valid: true },
      ];

      dialog.open!.mockReturnValue({
        afterClosed: () => of({ items: importedItems })
      } as any);

      component.openImportDialog();

      // Only 2852 should be added, 60345 already exists
      expect(component.items.length).toBe(2);
    });

    it('should not modify items if dialog cancelled', () => {
      component.type = 'taxon';
      component.items = [{ cd_nom: 60345, nom_complet: 'Lynx' }];
      fixture.detectChanges();

      dialog.open!.mockReturnValue({
        afterClosed: () => of(null)
      } as any);

      component.openImportDialog();

      expect(component.items.length).toBe(1);
    });
  });

  // ==========================================
  // Display helpers
  // ==========================================
  describe('getItemLabel', () => {
    beforeEach(() => fixture.detectChanges());

    it('should return nom_complet for taxon', () => {
      component.type = 'taxon';
      expect(component.getItemLabel({ cd_nom: 60345, nom_complet: 'Lynx lynx' })).toBe('Lynx lynx');
    });

    it('should return fallback for taxon without name', () => {
      component.type = 'taxon';
      expect(component.getItemLabel({ cd_nom: 60345 })).toBe('cd_nom: 60345');
    });

    it('should return lb_hab_fr for habitat', () => {
      component.type = 'habitat';
      expect(component.getItemLabel({ cd_hab: '16265', lb_hab_fr: 'Hêtraies' })).toBe('Hêtraies');
    });
  });

  describe('getItemSecondary', () => {
    beforeEach(() => fixture.detectChanges());

    it('should combine rang and nom_vern for taxon', () => {
      component.type = 'taxon';
      expect(component.getItemSecondary({ cd_nom: 60345, nom_vern: 'Lynx boréal', id_rang: 'ES' })).toBe('Espèce · Lynx boréal');
    });

    it('should fall back to nom_vern alone when id_rang missing', () => {
      component.type = 'taxon';
      expect(component.getItemSecondary({ cd_nom: 60345, nom_vern: 'Lynx boréal' })).toBe('Lynx boréal');
    });

    it('should show rang alone for higher-rank taxa without nom_vern', () => {
      component.type = 'taxon';
      expect(component.getItemSecondary({ cd_nom: 186210, id_rang: 'FM' })).toBe('Famille');
    });

    it('should return empty string for taxon without nom_vern or id_rang', () => {
      component.type = 'taxon';
      expect(component.getItemSecondary({ cd_nom: 60345 })).toBe('');
    });

    it('should return cd_hab for habitat', () => {
      component.type = 'habitat';
      expect(component.getItemSecondary({ cd_hab: '16265', lb_hab_fr: 'Hêtraies' })).toBe('cd_hab: 16265');
    });
  });

  describe('getResultLabel (autocomplete dropdown)', () => {
    beforeEach(() => fixture.detectChanges());

    it('should prefer lb_hab_fr_complet for habitat to disambiguate variants', () => {
      const result = {
        cd_hab: 25683,
        lb_hab_fr: 'Quercetalia pubescentis',
        lb_hab_fr_complet: 'Quercetalia pubescentis Tüxen 1931 nom. nud. (art. 2b, 8)',
        search_name: '',
      } as any;
      expect(component.getResultLabel(result)).toBe(
        'Quercetalia pubescentis Tüxen 1931 nom. nud. (art. 2b, 8)'
      );
    });

    it('should fall back to lb_hab_fr when complet is missing', () => {
      const result = { cd_hab: 1, lb_hab_fr: 'Hêtraies', search_name: '' } as any;
      expect(component.getResultLabel(result)).toBe('Hêtraies');
    });
  });

  describe('getResultSecondary (autocomplete dropdown)', () => {
    beforeEach(() => fixture.detectChanges());

    it('should include rang and nom_vern for species taxon', () => {
      const result = { cd_nom: 60345, nom_vern: 'Lynx boréal', id_rang: 'ES' } as any;
      expect(component.getResultSecondary(result)).toBe('Espèce · Lynx boréal — cd_nom: 60345');
    });

    it('should show rang alone for higher-rank taxa without nom_vern', () => {
      const result = { cd_nom: 186210, nom_vern: null, id_rang: 'FM' } as any;
      expect(component.getResultSecondary(result)).toBe('Famille — cd_nom: 186210');
    });

    it('should pass through unknown id_rang codes', () => {
      const result = { cd_nom: 1, nom_vern: null, id_rang: 'XYZ' } as any;
      expect(component.getResultSecondary(result)).toBe('XYZ — cd_nom: 1');
    });

    it('should fall back to cd_nom alone when nothing else available', () => {
      const result = { cd_nom: 99, nom_vern: null, id_rang: null } as any;
      expect(component.getResultSecondary(result)).toBe('cd_nom: 99');
    });

    it('should include typology, code and cd_hab for habitat', () => {
      const result = {
        cd_hab: 3372,
        lb_code: '57.0.1',
        lb_typo: "Unités_phytosociologiques_des_Cahiers_d'habitats",
        lb_hab_fr: 'Quercetalia pubescenti-sessiliflorae',
      } as any;
      expect(component.getResultSecondary(result)).toBe(
        "Unités phytosociologiques des Cahiers d'habitats · 57.0.1 — cd_hab: 3372"
      );
    });

    it('should fall back to typology + cd_hab when lb_code is missing', () => {
      const result = {
        cd_hab: 25686,
        lb_code: null,
        lb_typo: 'Prodrome_des_végétations_de_France_(PVF1)',
        lb_hab_fr: 'Quercetalia pubescenti-sessiliflorae',
      } as any;
      expect(component.getResultSecondary(result)).toBe(
        'Prodrome des végétations de France (PVF1) — cd_hab: 25686'
      );
    });

    it('should fall back to cd_hab alone when typology and code are missing', () => {
      const result = { cd_hab: 1000, lb_code: null, lb_typo: null } as any;
      expect(component.getResultSecondary(result)).toBe('cd_hab: 1000');
    });
  });

  describe('displayFn', () => {
    beforeEach(() => fixture.detectChanges());

    it('should return empty string for null', () => {
      expect(component.displayFn(null as any)).toBe('');
    });

    it('should return string as-is', () => {
      expect(component.displayFn('test')).toBe('test');
    });

    it('should return nom_valide for taxon result', () => {
      expect(component.displayFn({ cd_nom: 1, nom_valide: 'Lynx lynx', lb_nom: 'L. lynx' } as any)).toBe('Lynx lynx');
    });

    it('should return lb_hab_fr for habitat result', () => {
      expect(component.displayFn({ cd_hab: 1, lb_hab_fr: 'Hêtraies', search_name: '' } as any)).toBe('Hêtraies');
    });
  });

  // ==========================================
  // Cleanup
  // ==========================================
  describe('ngOnDestroy', () => {
    it('should complete destroy$ subject', () => {
      fixture.detectChanges();
      const completeSpy = jest.spyOn(component['destroy$'], 'complete');
      component.ngOnDestroy();
      expect(completeSpy).toHaveBeenCalled();
    });
  });

  // ==========================================
  // #368 — Habitat libre (hors HabRef)
  // ==========================================
  describe('#368 habitat libre', () => {
    it('allowFreeText vrai uniquement pour les habitats', () => {
      component.type = 'habitat';
      expect(component.allowFreeText).toBe(true);
      component.type = 'taxon';
      expect(component.allowFreeText).toBe(false);
    });

    it('addFreeTextHabitat ajoute un item sans cd_hab', () => {
      component.type = 'habitat';
      component.items = [];
      const emitted: HabitatRef[][] = [];
      component.itemsChange.subscribe(v => emitted.push(v as HabitatRef[]));
      component.freeTextControl.setValue('  Mangrove de Mayotte  ');
      component.addFreeTextHabitat();
      expect(component.items.length).toBe(1);
      const added = component.items[0] as HabitatRef;
      expect(added.cd_hab).toBe('');
      expect(added.lb_hab_fr).toBe('Mangrove de Mayotte');
      expect(emitted.length).toBe(1);
      expect(component.freeTextControl.value).toBe('');
    });

    it('addFreeTextHabitat ignore un libellé vide', () => {
      component.type = 'habitat';
      component.items = [];
      component.freeTextControl.setValue('   ');
      component.addFreeTextHabitat();
      expect(component.items.length).toBe(0);
    });

    it('addFreeTextHabitat dédoublonne (insensible à la casse)', () => {
      component.type = 'habitat';
      component.items = [{ cd_hab: '', lb_hab_fr: 'Récif corallien' }];
      component.freeTextControl.setValue('récif corallien');
      component.addFreeTextHabitat();
      expect(component.items.length).toBe(1);
    });

    it('toggleFreeTextMode bascule et vide le champ à la fermeture', () => {
      component.freeTextControl.setValue('xxx');
      component.toggleFreeTextMode();
      expect(component.freeTextMode()).toBe(true);
      component.toggleFreeTextMode();
      expect(component.freeTextMode()).toBe(false);
      expect(component.freeTextControl.value).toBe('');
    });
  });

  // ==========================================
  // #471 — Taxon introuvable : recherche par synonymes
  // ==========================================
  describe('#471 recherche par synonymes', () => {
    it('allowSynonymSearch vrai uniquement pour les taxons', () => {
      component.type = 'taxon';
      expect(component.allowSynonymSearch).toBe(true);
      component.type = 'habitat';
      expect(component.allowSynonymSearch).toBe(false);
    });

    it('enableSynonymSearch active le mode et relance la recherche avec include_synonyms', fakeAsync(() => {
      component.type = 'taxon';
      fixture.detectChanges();

      // Terme déjà saisi, recherche standard passée
      taxonomyService.autocomplete!.mockReturnValue(of([]));
      component.searchControl.setValue('Rana');
      tick(300);
      expect(taxonomyService.autocomplete).toHaveBeenLastCalledWith('Rana', { limit: 50 });

      // Activation de la recherche élargie → même terme, avec synonymes
      component.enableSynonymSearch();
      tick(300);

      expect(component.synonymMode()).toBe(true);
      expect(taxonomyService.autocomplete).toHaveBeenLastCalledWith('Rana', { limit: 50, include_synonyms: true });
    }));

    it('résout un synonyme sélectionné vers le taxon accepté (cd_ref)', () => {
      component.type = 'taxon';
      component.items = [];
      fixture.detectChanges();

      const event = {
        option: {
          value: {
            cd_nom: 351,           // synonyme
            cd_ref: 292,           // taxon accepté
            is_synonyme: true,
            lb_nom: 'Rana esculenta',
            nom_valide: 'Pelophylax kl. esculentus',
            nom_vern: 'Grenouille verte',
            regne: 'Animalia',
            id_rang: 'ES',
          }
        }
      } as MatAutocompleteSelectedEvent;

      component.onAutocompleteSelected(event);

      expect(component.items.length).toBe(1);
      const added = component.items[0] as TaxonRef;
      expect(added.cd_nom).toBe(292); // cd_ref, pas cd_nom du synonyme
      expect(added.nom_complet).toBe('Pelophylax kl. esculentus');
    });

    it('conserve cd_nom pour un taxon valide (non synonyme)', () => {
      component.type = 'taxon';
      component.items = [];
      fixture.detectChanges();

      const event = {
        option: {
          value: {
            cd_nom: 60345, cd_ref: 60345, is_synonyme: false,
            lb_nom: 'Lynx lynx', nom_valide: 'Lynx lynx', regne: 'Animalia', id_rang: 'ES',
          }
        }
      } as MatAutocompleteSelectedEvent;

      component.onAutocompleteSelected(event);

      expect((component.items[0] as TaxonRef).cd_nom).toBe(60345);
    });

    it('getResultSynonymHint renvoie le nom valide pour un synonyme, sinon vide', () => {
      fixture.detectChanges();
      expect(component.getResultSynonymHint({
        cd_nom: 351, cd_ref: 292, is_synonyme: true, nom_valide: 'Pelophylax kl. esculentus',
      } as any)).toBe('Pelophylax kl. esculentus');
      expect(component.getResultSynonymHint({
        cd_nom: 60345, is_synonyme: false, nom_valide: 'Lynx lynx',
      } as any)).toBe('');
      // habitat → pas de hint synonyme
      expect(component.getResultSynonymHint({ cd_hab: 1, lb_hab_fr: 'Hêtraies' } as any)).toBe('');
    });
  });
});
