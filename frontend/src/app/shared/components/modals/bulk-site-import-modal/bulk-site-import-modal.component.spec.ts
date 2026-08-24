import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { BulkSiteImportModalComponent } from './bulk-site-import-modal.component';
import { AdminService } from '../../../../core/services/admin.service';
import { BulkImportValidationResult } from '../../../../core/models/admin.model';

describe('BulkSiteImportModalComponent', () => {
  let component: BulkSiteImportModalComponent;
  let fixture: ComponentFixture<BulkSiteImportModalComponent>;
  let adminServiceMock: {
    bulkImportValidate: jest.Mock;
    bulkImportExecute: jest.Mock;
    bulkImportStatus: jest.Mock;
  };
  let dialogRefMock: { close: jest.Mock };

  const mockValidationResult: BulkImportValidationResult = {
    detected_properties: ['nom', 'inpn', 'surface'],
    suggested_mapping: { nom: 'nom_site', inpn: 'id_inpn', surface: 'surf_off' },
    applied_mapping: { nom: 'nom_site', inpn: 'id_inpn', surface: 'surf_off' },
    sites: [
      {
        row_index: 0,
        original_properties: { nom: 'Site A', inpn: 'INPN001', surface: '500' },
        mapped_data: { nom_site: 'Site A', id_inpn: 'INPN001', surf_off: '500' },
        has_geometry: true,
        errors: [],
        warnings: [],
        duplicate_info: null,
      },
      {
        row_index: 1,
        original_properties: { nom: 'Site B', inpn: '', surface: '300' },
        mapped_data: { nom_site: 'Site B', surf_off: '300' },
        has_geometry: false,
        errors: [],
        warnings: ['Noms similaires existants: Site Beta'],
        duplicate_info: null,
      },
      {
        row_index: 2,
        original_properties: { nom: 'AB', inpn: 'DUP', surface: '' },
        mapped_data: { nom_site: 'AB', id_inpn: 'DUP' },
        has_geometry: false,
        errors: ['Le nom doit contenir au moins 3 caractères.'],
        warnings: [],
        duplicate_info: null,
      },
    ],
    total: 3,
    valid: 2,
    errors: 1,
    warnings: 1,
    duplicates: 0,
  };

  beforeEach(async () => {
    adminServiceMock = {
      bulkImportValidate: jest.fn(),
      bulkImportExecute: jest.fn(),
      bulkImportStatus: jest.fn(),
    };
    dialogRefMock = { close: jest.fn() };

    await TestBed.configureTestingModule({
      imports: [
        BulkSiteImportModalComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        { provide: AdminService, useValue: adminServiceMock },
        { provide: MatDialogRef, useValue: dialogRefMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(BulkSiteImportModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('File selection', () => {
    it('should accept .geojson files', () => {
      const file = new File(['{}'], 'test.geojson', { type: 'application/json' });
      adminServiceMock.bulkImportValidate.mockReturnValue(of(mockValidationResult));

      const event = { target: { files: [file] } } as unknown as Event;
      component.onFileSelected(event);

      expect(component.selectedFile()).toBe(file);
      expect(adminServiceMock.bulkImportValidate).toHaveBeenCalled();
    });

    it('should accept .csv files', () => {
      const file = new File([''], 'test.csv', { type: 'text/csv' });
      adminServiceMock.bulkImportValidate.mockReturnValue(of(mockValidationResult));

      const event = { target: { files: [file] } } as unknown as Event;
      component.onFileSelected(event);

      expect(component.selectedFile()).toBe(file);
    });

    it('should reject unsupported formats', () => {
      const file = new File([''], 'test.txt', { type: 'text/plain' });

      const event = { target: { files: [file] } } as unknown as Event;
      component.onFileSelected(event);

      expect(component.selectedFile()).toBeNull();
      expect(component.uploadError()).toBeTruthy();
    });

    it('should show feature count after upload', fakeAsync(() => {
      const file = new File(['{}'], 'test.geojson', { type: 'application/json' });
      adminServiceMock.bulkImportValidate.mockReturnValue(of(mockValidationResult));

      const event = { target: { files: [file] } } as unknown as Event;
      component.onFileSelected(event);
      tick();

      expect(component.validationResult()).toBeTruthy();
      expect(component.validationResult()!.total).toBe(3);
    }));
  });

  describe('Mapping', () => {
    beforeEach(fakeAsync(() => {
      const file = new File(['{}'], 'test.geojson', { type: 'application/json' });
      adminServiceMock.bulkImportValidate.mockReturnValue(of(mockValidationResult));
      const event = { target: { files: [file] } } as unknown as Event;
      component.onFileSelected(event);
      tick();
    }));

    it('should display detected properties', () => {
      expect(component.detectedProperties()).toEqual(['nom', 'inpn', 'surface']);
    });

    it('should have suggested mapping', () => {
      expect(component.suggestedMapping()['nom']).toBe('nom_site');
      expect(component.suggestedMapping()['inpn']).toBe('id_inpn');
    });

    it('should allow custom mapping changes', () => {
      component.onMappingChange('nom', 'id_local');
      expect(component.fieldMapping()['nom']).toBe('id_local');
    });
  });

  describe('Preview', () => {
    beforeEach(fakeAsync(() => {
      const file = new File(['{}'], 'test.geojson', { type: 'application/json' });
      adminServiceMock.bulkImportValidate.mockReturnValue(of(mockValidationResult));
      const event = { target: { files: [file] } } as unknown as Event;
      component.onFileSelected(event);
      tick();
    }));

    it('should show status chips', () => {
      const sites = component.sites();
      expect(component.getSiteStatus(sites[0])).toBe('valid');
      expect(component.getSiteStatus(sites[1])).toBe('warning');
      expect(component.getSiteStatus(sites[2])).toBe('error');
    });

    it('should disable checkbox for error rows', () => {
      const sites = component.sites();
      expect(sites[2].selected).toBe(false);
    });

    it('should allow toggling valid rows', () => {
      const initialSelected = component.selectedCount();
      component.toggleSite(0);
      const newSelected = component.selectedCount();
      expect(newSelected).toBe(initialSelected - 1);
    });

    it('should support select all toggle', () => {
      component.toggleAll();
      const sites = component.sites();
      const validSites = sites.filter(s => s.errors.length === 0);
      expect(validSites.every(s => !s.selected)).toBe(true);
    });

    it('should show summary counts', () => {
      expect(component.totalValid()).toBe(2);
      expect(component.totalErrors()).toBe(1);
    });

    it('should count selected sites', () => {
      expect(component.selectedCount()).toBe(2);
    });
  });

  describe('Import', () => {
    beforeEach(fakeAsync(() => {
      const file = new File(['{}'], 'test.geojson', { type: 'application/json' });
      adminServiceMock.bulkImportValidate.mockReturnValue(of(mockValidationResult));
      const event = { target: { files: [file] } } as unknown as Event;
      component.onFileSelected(event);
      tick();
    }));

    it('should call bulkImportExecute on import', fakeAsync(() => {
      adminServiceMock.bulkImportExecute.mockReturnValue(of({
        async: false,
        created: 2,
        failed: 0,
        validation_pending: 0,
        details: [
          { row_index: 0, nom_site: 'Site A', status: 'created' as const, site_id: 1 },
          { row_index: 1, nom_site: 'Site B', status: 'created' as const, site_id: 2 },
        ],
      }));

      component.startImport();
      tick();

      expect(adminServiceMock.bulkImportExecute).toHaveBeenCalled();
      expect(component.importResult()).toBeTruthy();
      expect(component.importResult()!.created).toBe(2);
    }));

    it('should show results after import completes', fakeAsync(() => {
      adminServiceMock.bulkImportExecute.mockReturnValue(of({
        async: false,
        created: 1,
        failed: 1,
        validation_pending: 0,
        details: [
          { row_index: 0, nom_site: 'Site A', status: 'created' as const, site_id: 1 },
          { row_index: 1, nom_site: 'Site B', status: 'failed' as const, error: 'Erreur DB' },
        ],
      }));

      component.startImport();
      tick();

      expect(component.importDetails().length).toBe(2);
      expect(component.importing()).toBe(false);
    }));

    it('should handle import errors', fakeAsync(() => {
      adminServiceMock.bulkImportExecute.mockReturnValue(throwError(() => new Error('Server error')));

      component.startImport();
      tick();

      expect(component.importing()).toBe(false);
      expect(component.importResult()).toBeTruthy();
    }));
  });

  describe('Dialog close', () => {
    it('should close with null when no import was done', () => {
      component.close();
      expect(dialogRefMock.close).toHaveBeenCalledWith(null);
    });

    it('should close with result when sites were imported', fakeAsync(() => {
      const file = new File(['{}'], 'test.geojson', { type: 'application/json' });
      adminServiceMock.bulkImportValidate.mockReturnValue(of(mockValidationResult));
      adminServiceMock.bulkImportExecute.mockReturnValue(of({
        async: false,
        created: 2,
        failed: 0,
        validation_pending: 0,
        details: [],
      }));

      const event = { target: { files: [file] } } as unknown as Event;
      component.onFileSelected(event);
      tick();

      component.startImport();
      tick();

      component.close();
      expect(dialogRefMock.close).toHaveBeenCalledWith({
        imported: true,
        created: 2,
      });
    }));
  });

  describe('Rattachement organisme / référent (#647)', () => {
    const row = (mapped: Record<string, any>, extra: Record<string, any> = {}) => ({
      row_index: 0,
      original_properties: {},
      mapped_data: mapped,
      has_geometry: false,
      errors: [],
      warnings: [],
      duplicate_info: null,
      ...extra,
    }) as any;

    it('propose les champs organisme et référent dans la correspondance', () => {
      const values = component.targetFields.map(f => f.value);
      expect(values).toContain('organisme');
      expect(values).toContain('referent');
    });

    it('affiche les colonnes organisme et référent dans la vérification', () => {
      expect(component.previewColumns).toContain('organisme');
      expect(component.previewColumns).toContain('referent');
    });

    it('affiche le nom des organismes résolus', () => {
      const site = row(
        { nom_site: 'Site A', organisme: 'CEN Alpha' },
        { resolved_organismes: [{ id_organisme: 3, nom_organisme: 'CEN Alpha' }] },
      );
      expect(component.organismeLabel(site)).toBe('CEN Alpha');
    });

    it('retombe sur la valeur brute quand l\'organisme n\'est pas résolu', () => {
      const site = row({ nom_site: 'Site A', organisme: 'Structure Fantome' });
      expect(component.organismeLabel(site)).toBe('Structure Fantome');
    });

    it('affiche le nom des référents résolus, l\'email à défaut', () => {
      const site = row(
        { nom_site: 'Site A', referent: 'a@test.fr' },
        { resolved_referents: [{ id_role: 7, nom: '', email: 'a@test.fr' }] },
      );
      expect(component.referentLabel(site)).toBe('a@test.fr');
    });

    it('affiche un tiret quand aucune colonne n\'est renseignée', () => {
      const site = row({ nom_site: 'Site A' });
      expect(component.organismeLabel(site)).toBe('-');
      expect(component.referentLabel(site)).toBe('-');
    });
  });
});
