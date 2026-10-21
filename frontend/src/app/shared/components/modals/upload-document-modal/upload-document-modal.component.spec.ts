import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule } from '@ngx-translate/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { of } from 'rxjs';
import { UploadDocumentModalComponent } from './upload-document-modal.component';
import { AdminService } from '../../../../core/services/admin.service';
import { SettingsService } from '../../../../core/services/settings.service';

const MO = 1024 * 1024;

/** Fichier factice d'une taille donnée, sans allouer son contenu. */
function fichier(taille: number): File {
  const f = new File(['x'], 'plan.pdf', { type: 'application/pdf' });
  Object.defineProperty(f, 'size', { value: taille });
  return f;
}

function selectionner(component: UploadDocumentModalComponent, f: File): void {
  component.onFileSelected({ target: { files: [f] } } as unknown as Event);
}

describe('UploadDocumentModalComponent — taille maximale (#745)', () => {
  let component: UploadDocumentModalComponent;
  const adminService = { uploadFichier: jest.fn().mockReturnValue(of({})) };
  const config = signal<{ taille_max_document_mo: number } | null>({ taille_max_document_mo: 2 });

  beforeEach(() => {
    adminService.uploadFichier.mockClear();
    TestBed.configureTestingModule({
      imports: [UploadDocumentModalComponent, TranslateModule.forRoot(), NoopAnimationsModule],
      providers: [
        { provide: MatDialogRef, useValue: { close: jest.fn() } },
        { provide: MAT_DIALOG_DATA, useValue: { planId: 1 } },
        { provide: AdminService, useValue: adminService },
        { provide: SettingsService, useValue: { config } },
      ],
    });
    component = TestBed.createComponent(UploadDocumentModalComponent).componentInstance;
  });

  it('expose la limite de l\'instance', () => {
    expect(component.tailleMaxMo()).toBe(2);
  });

  it('refuse un fichier plus lourd que la limite, sans l\'envoyer', () => {
    selectionner(component, fichier(2 * MO + 1));
    expect(component.selectedFile()).toBeNull();
    expect(component.errorMessage()).toBeTruthy();
    component.submit();
    expect(adminService.uploadFichier).not.toHaveBeenCalled();
  });

  it('accepte un fichier dans la limite', () => {
    selectionner(component, fichier(2 * MO));
    expect(component.selectedFile()).not.toBeNull();
    expect(component.errorMessage()).toBeNull();
  });

  it('retombe sur 20 Mo tant que la configuration n\'est pas chargée', () => {
    config.set(null);
    expect(component.tailleMaxMo()).toBe(20);
  });
});
