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
  let adminServiceSpy: jasmine.SpyObj<AdminService>;
  let dialogRefSpy: jasmine.SpyObj<MatDialogRef<BulkSiteImportModalComponent>>;

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
    adminServiceSpy = jasmine.createSpyObj('AdminService', [
      'bulkImportValidate',
      'bulkImportExecute',
      'bulkImportStatus',
    ]);
    dialogRefSpy = jasmine.createSpyObj('MatDialogRef', ['close']);

    await TestBed.configureTestingModule({
      imports: [
        BulkSiteImportModalComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot(),
      ],
      providers: [
        { provide: AdminService, useValue: adminServiceSpy },
        { provide: MatDialogRef, useValue: dialogRefSpy },
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
      adminServiceSpy.bulkImportValidate.and.returnValue(of(mockValidationResult));

      const event = { target: { files: [file] } } as unknown as Event;
      component.onFileSelected(event);

      expect(component.selectedFile()).toBe(file);
      expect(adminServiceSpy.bulkImportValidate).toHaveBeenCalled();
    });

    it('should accept .csv files', () => {
      const file = new File([''], 'test.csv', { type: 'text/csv' });
      adminServiceSpy.bulkImportValidate.and.returnValue(of(mockValidationResult));

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
      adminServiceSpy.bulkImportValidate.and.returnValue(of(mockValidationResult));

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
      adminServiceSpy.bulkImportValidate.and.returnValue(of(mockValidationResult));
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
      adminServiceSpy.bulkImportValidate.and.returnValue(of(mockValidationResult));
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
      // Error row should not be selected
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
      // After toggling all off (they were on for valid sites)
      const sites = component.sites();
      const validSites = sites.filter(s => s.errors.length === 0);
      // All should now be deselected
      expect(validSites.every(s => !s.selected)).toBeTrue();
    });

    it('should show summary counts', () => {
      expect(component.totalValid()).toBe(2);
      expect(component.totalErrors()).toBe(1);
    });

    it('should count selected sites', () => {
      // Valid sites auto-selected: 2
      expect(component.selectedCount()).toBe(2);
    });
  });

  describe('Import', () => {
    beforeEach(fakeAsync(() => {
      const file = new File(['{}'], 'test.geojson', { type: 'application/json' });
      adminServiceSpy.bulkImportValidate.and.returnValue(of(mockValidationResult));
      const event = { target: { files: [file] } } as unknown as Event;
      component.onFileSelected(event);
      tick();
    }));

    it('should call bulkImportExecute on import', fakeAsync(() => {
      adminServiceSpy.bulkImportExecute.and.returnValue(of({
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

      expect(adminServiceSpy.bulkImportExecute).toHaveBeenCalled();
      expect(component.importResult()).toBeTruthy();
      expect(component.importResult()!.created).toBe(2);
    }));

    it('should show results after import completes', fakeAsync(() => {
      adminServiceSpy.bulkImportExecute.and.returnValue(of({
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
      expect(component.importing()).toBeFalse();
    }));

    it('should handle import errors', fakeAsync(() => {
      adminServiceSpy.bulkImportExecute.and.returnValue(throwError(() => new Error('Server error')));

      component.startImport();
      tick();

      expect(component.importing()).toBeFalse();
      expect(component.importResult()).toBeTruthy();
    }));
  });

  describe('Dialog close', () => {
    it('should close with null when no import was done', () => {
      component.close();
      expect(dialogRefSpy.close).toHaveBeenCalledWith(null);
    });

    it('should close with result when sites were imported', fakeAsync(() => {
      const file = new File(['{}'], 'test.geojson', { type: 'application/json' });
      adminServiceSpy.bulkImportValidate.and.returnValue(of(mockValidationResult));
      adminServiceSpy.bulkImportExecute.and.returnValue(of({
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
      expect(dialogRefSpy.close).toHaveBeenCalledWith({
        imported: true,
        created: 2,
      });
    }));
  });
});
