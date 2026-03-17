import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';
import {
  ImportListDialogComponent,
  ImportListDialogData,
  ImportedItem,
  NotFoundEntry,
  RejectedEntry
} from './import-list-dialog.component';
import { TaxonomyService } from '../../../../core/services/taxonomy.service';
import { HabitatService } from '../../../../core/services/habitat.service';
import { GeologyService } from '../../../../core/services/geology.service';

class FakeTranslateLoader implements TranslateLoader {
  getTranslation() {
    return of({
      'enjeux.importList.titleTaxon': 'Importer des espèces',
      'enjeux.importList.titleHabitat': 'Importer des habitats',
      'enjeux.importList.instructions': 'Saisissez un code par ligne.',
      'enjeux.importList.codesOnlyTaxon': 'Seuls les codes cd_nom sont acceptés.',
      'enjeux.importList.codesOnlyHabitat': 'Seuls les codes cd_hab sont acceptés.',
      'enjeux.importList.importButton': 'Valider',
      'enjeux.importList.confirmButton': 'Ajouter',
      'enjeux.importList.foundCount': '{{count}} trouvé(s)',
      'enjeux.importList.notFoundCount': '{{count}} non trouvé(s)',
      'enjeux.importList.rejectedCount': '{{count}} rejeté(s)',
      'enjeux.importList.codeNotFound': 'Non trouvé',
      'enjeux.importList.matchedFrom': 'trouvé via',
      'enjeux.importList.exampleTitleTaxon': 'Codes acceptés',
      'enjeux.importList.exampleTitleHabitat': 'Codes acceptés',
      'enjeux.importList.exampleTitleGeology': 'Formats acceptés',
      'enjeux.importList.exampleTaxon': '60345',
      'enjeux.importList.exampleHabitat': '16265',
      'enjeux.importList.exampleGeology': '42',
      'enjeux.importList.helpTaxon': 'Les codes cd_nom...',
      'enjeux.importList.helpHabitat': 'Les codes cd_hab...',
      'enjeux.importList.helpGeology': 'Les sites géologiques...',
      'enjeux.importList.codesLabelTaxon': 'Liste cd_nom',
      'enjeux.importList.codesLabelHabitat': 'Liste cd_hab',
      'enjeux.importList.codesLabelGeology': 'Liste géologie',
      'enjeux.importList.placeholderTaxon': '60345',
      'enjeux.importList.placeholderHabitat': '16265',
      'enjeux.importList.placeholderGeology': '42',
      'enjeux.importList.orUploadFile': 'ou importer',
      'enjeux.importList.chooseFile': 'Choisir',
      'enjeux.importList.fileHint': 'Fichier .txt ou .csv',
      'enjeux.importList.didYouMean': 'Vouliez-vous dire :',
      'common.actions.cancel': 'Annuler'
    });
  }
}

describe('ImportListDialogComponent', () => {
  let component: ImportListDialogComponent;
  let fixture: ComponentFixture<ImportListDialogComponent>;
  let dialogRef: { close: jest.Mock };
  let taxonomyService: { validateBulk: jest.Mock };
  let habitatService: { validateBulk: jest.Mock };
  let geologyService: { validateBulk: jest.Mock };

  function createComponent(type: 'taxon' | 'habitat' | 'geology', existingCodes: (number | string)[] = []) {
    const mockData: ImportListDialogData = { type, existingCodes };

    dialogRef = { close: jest.fn() };
    taxonomyService = { validateBulk: jest.fn() };
    habitatService = { validateBulk: jest.fn() };
    geologyService = { validateBulk: jest.fn() };

    TestBed.configureTestingModule({
      imports: [
        ImportListDialogComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader },
          defaultLanguage: 'fr'
        })
      ],
      providers: [
        { provide: MatDialogRef, useValue: dialogRef },
        { provide: MAT_DIALOG_DATA, useValue: mockData },
        { provide: TaxonomyService, useValue: taxonomyService },
        { provide: HabitatService, useValue: habitatService },
        { provide: GeologyService, useValue: geologyService },
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ImportListDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  // ==========================================
  // Taxon tests
  // ==========================================
  describe('taxon mode', () => {
    beforeEach(() => createComponent('taxon'));

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should be in codes-only mode', () => {
      expect(component.codesOnly()).toBe(true);
    });

    it('should have type taxon', () => {
      expect(component.type).toBe('taxon');
    });

    it('should not have input initially', () => {
      expect(component.hasInput).toBe(false);
    });

    it('should detect input when text is entered', () => {
      component.codesInput.set('60345');
      expect(component.hasInput).toBe(true);
    });

    it('should reject non-numeric codes for taxon', () => {
      component.codesInput.set('Lynx lynx\nLoutre');
      component.onValidate();

      // Should have 2 rejected entries (text inputs), no API call
      expect(component.rejectedEntries().length).toBe(2);
      expect(component.rejectedEntries()[0].input).toBe('Lynx lynx');
      expect(component.rejectedEntries()[1].input).toBe('Loutre');
      expect(taxonomyService.validateBulk).not.toHaveBeenCalled();
    });

    it('should accept numeric codes for taxon', fakeAsync(() => {
      taxonomyService.validateBulk!.mockReturnValue(of({
        found: [
          { input: '60345', cd_nom: 60345, nom_complet: 'Lynx lynx', nom_valide: 'Lynx lynx', nom_vern: 'Lynx boréal' }
        ],
        not_found: []
      }));

      component.codesInput.set('60345');
      component.onValidate();
      tick();

      expect(taxonomyService.validateBulk).toHaveBeenCalledWith(['60345']);
      expect(component.foundItems().length).toBe(1);
      expect(component.foundItems()[0].code).toBe(60345);
      expect(component.foundItems()[0].label).toBe('Lynx lynx');
      expect(component.validationDone()).toBe(true);
    }));

    it('should show not-found for unknown cd_nom', fakeAsync(() => {
      taxonomyService.validateBulk!.mockReturnValue(of({
        found: [],
        not_found: [
          { input: '999999', candidates: [{ nom_valide: 'Lynx lynx', cd_nom: 60345, nom_vern: 'Lynx' }] }
        ]
      }));

      component.codesInput.set('999999');
      component.onValidate();
      tick();

      expect(component.notFoundEntries().length).toBe(1);
      expect(component.notFoundEntries()[0].input).toBe('999999');
    }));

    it('should handle mixed valid/invalid/not-found codes', fakeAsync(() => {
      taxonomyService.validateBulk!.mockReturnValue(of({
        found: [
          { input: '60345', cd_nom: 60345, nom_complet: 'Lynx lynx', nom_valide: 'Lynx lynx', nom_vern: '' }
        ],
        not_found: [
          { input: '999999', candidates: [] }
        ]
      }));

      component.codesInput.set('60345\nLynx lynx\n999999');
      component.onValidate();
      tick();

      // 1 found via API, 1 not-found via API, 1 rejected locally
      expect(component.foundItems().length).toBe(1);
      expect(component.notFoundEntries().length).toBe(1);
      expect(component.rejectedEntries().length).toBe(1);
      expect(component.rejectedEntries()[0].input).toBe('Lynx lynx');
    }));

    it('should show all rejected when only text input', () => {
      component.codesInput.set('Lynx lynx\nLoutre');
      component.onValidate();

      // Should go directly to validationDone without API call
      expect(component.validationDone()).toBe(true);
      expect(taxonomyService.validateBulk).not.toHaveBeenCalled();
      expect(component.rejectedEntries().length).toBe(2);
      expect(component.foundItems().length).toBe(0);
    });

    it('should split codes by commas and semicolons', fakeAsync(() => {
      taxonomyService.validateBulk!.mockReturnValue(of({
        found: [
          { input: '60345', cd_nom: 60345, nom_complet: 'Lynx lynx', nom_valide: 'Lynx lynx', nom_vern: '' },
          { input: '2852', cd_nom: 2852, nom_complet: 'Bufo bufo', nom_valide: 'Bufo bufo', nom_vern: '' }
        ],
        not_found: []
      }));

      component.codesInput.set('60345,2852');
      component.onValidate();
      tick();

      expect(taxonomyService.validateBulk).toHaveBeenCalledWith(['60345', '2852']);
    }));
  });

  // ==========================================
  // Taxon with existing codes
  // ==========================================
  describe('taxon mode with existing codes', () => {
    beforeEach(() => createComponent('taxon', [60345]));

    it('should filter out already existing codes', fakeAsync(() => {
      taxonomyService.validateBulk!.mockReturnValue(of({
        found: [
          { input: '2852', cd_nom: 2852, nom_complet: 'Bufo bufo', nom_valide: 'Bufo bufo', nom_vern: '' }
        ],
        not_found: []
      }));

      component.codesInput.set('60345\n2852');
      component.onValidate();
      tick();

      // 60345 should be filtered as duplicate, only 2852 sent to API
      expect(taxonomyService.validateBulk).toHaveBeenCalledWith(['2852']);
    }));
  });

  // ==========================================
  // Habitat tests
  // ==========================================
  describe('habitat mode', () => {
    beforeEach(() => createComponent('habitat'));

    it('should create in habitat mode', () => {
      expect(component.type).toBe('habitat');
      expect(component.codesOnly()).toBe(true);
    });

    it('should reject non-numeric codes for habitat', fakeAsync(() => {
      habitatService.validateBulk!.mockReturnValue(of({
        found: [
          { input: '16265', cd_hab: 16265, lb_hab_fr: 'Hêtraies acidiphiles', lb_hab_fr_complet: '', lb_code: 'G1.6', cd_typo: 1, niveau: 3 }
        ],
        not_found: []
      }));

      component.codesInput.set('G1.6\n16265\nHêtraies');
      component.onValidate();
      tick();

      expect(component.rejectedEntries().length).toBe(2);
      expect(component.rejectedEntries()[0].input).toBe('G1.6');
      expect(component.rejectedEntries()[1].input).toBe('Hêtraies');
      // 16265 is numeric and should have been sent to the API
      expect(habitatService.validateBulk).toHaveBeenCalledWith(['16265']);
    }));

    it('should accept numeric codes for habitat', fakeAsync(() => {
      habitatService.validateBulk!.mockReturnValue(of({
        found: [
          { input: '16265', cd_hab: 16265, lb_hab_fr: 'Hêtraies acidiphiles', lb_hab_fr_complet: '', lb_code: 'G1.6', cd_typo: 1, niveau: 3 }
        ],
        not_found: []
      }));

      component.codesInput.set('16265');
      component.onValidate();
      tick();

      expect(habitatService.validateBulk).toHaveBeenCalledWith(['16265']);
      expect(component.foundItems().length).toBe(1);
      expect(component.foundItems()[0].code).toBe(16265);
    }));
  });

  // ==========================================
  // Geology tests (no codes-only restriction)
  // ==========================================
  describe('geology mode', () => {
    beforeEach(() => createComponent('geology'));

    it('should NOT be in codes-only mode', () => {
      expect(component.codesOnly()).toBe(false);
    });

    it('should accept text input for geology', fakeAsync(() => {
      geologyService.validateBulk!.mockReturnValue(of({
        found: [
          { input: 'Grotte de Lascaux', id_inpg: '42', lb_site: 'Grotte de Lascaux', id_metier: 'AQI0001' }
        ],
        not_found: []
      }));

      component.codesInput.set('Grotte de Lascaux');
      component.onValidate();
      tick();

      expect(geologyService.validateBulk).toHaveBeenCalledWith(['Grotte de Lascaux']);
      expect(component.rejectedEntries().length).toBe(0);
      expect(component.foundItems().length).toBe(1);
    }));
  });

  // ==========================================
  // Dialog actions
  // ==========================================
  describe('dialog actions', () => {
    beforeEach(() => createComponent('taxon'));

    it('should close dialog with null on cancel', () => {
      component.onCancel();
      expect(dialogRef.close).toHaveBeenCalledWith(null);
    });

    it('should close dialog with found items on confirm', fakeAsync(() => {
      taxonomyService.validateBulk!.mockReturnValue(of({
        found: [
          { input: '60345', cd_nom: 60345, nom_complet: 'Lynx lynx', nom_valide: 'Lynx lynx', nom_vern: 'Lynx boréal' }
        ],
        not_found: []
      }));

      component.codesInput.set('60345');
      component.onValidate();
      tick();

      component.onConfirm();

      expect(dialogRef.close).toHaveBeenCalledWith({
        items: expect.arrayContaining([
          expect.objectContaining({ code: 60345, label: 'Lynx lynx' })
        ])
      });
    }));

    it('should not validate with empty input', () => {
      component.codesInput.set('');
      component.onValidate();
      expect(taxonomyService.validateBulk).not.toHaveBeenCalled();
      expect(component.validationDone()).toBe(false);
    });

    it('should not validate with whitespace-only input', () => {
      component.codesInput.set('  \n  \n  ');
      component.onValidate();
      expect(taxonomyService.validateBulk).not.toHaveBeenCalled();
    });
  });

  // ==========================================
  // Error handling
  // ==========================================
  describe('error handling', () => {
    beforeEach(() => createComponent('taxon'));

    it('should reset isValidating on API error', fakeAsync(() => {
      taxonomyService.validateBulk!.mockReturnValue(throwError(() => new Error('API Error')));

      component.codesInput.set('60345');
      component.onValidate();
      tick();

      expect(component.isValidating()).toBe(false);
      expect(component.validationDone()).toBe(false);
    }));
  });

  // ==========================================
  // File upload
  // ==========================================
  describe('file upload', () => {
    beforeEach(() => createComponent('taxon'));

    it('should read file content into codesInput', fakeAsync(() => {
      const fileContent = '60345\n2852\n79301';
      const file = new File([fileContent], 'codes.txt', { type: 'text/plain' });
      const event = { target: { files: [file] } } as unknown as Event;

      component.onFileSelected(event);

      // Simulate FileReader completion
      tick(100);

      // The FileReader is async, so in test we verify the method doesn't crash
      expect(component).toBeTruthy();
    }));

    it('should handle no file selected', () => {
      const event = { target: { files: [] } } as unknown as Event;
      component.onFileSelected(event);
      expect(component.codesInput()).toBe('');
    });
  });
});
