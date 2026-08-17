/**
 * Tests unitaires — ExportFicheActionDialogComponent (#642).
 *
 * La fiche action se prête à deux sorties très différentes : l'impression/PDF
 * (mise en page de la fiche affichée, sections choisies) et le classeur Excel
 * au modèle CICADA (structure fixe). La modale porte ce choix ; on vérifie ici
 * qu'elle le restitue fidèlement à l'appelant.
 */
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { TranslateModule } from '@ngx-translate/core';

import {
  ExportFicheActionDialogComponent,
  ExportFicheActionDialogData,
} from './export-fiche-action-dialog.component';

const SECTIONS = [
  { key: 'description', labelKey: 'plans.suivis.actions.fiche.description' },
  { key: 'realisation', labelKey: 'plans.suivis.actions.fiche.realisation' },
];

function setup(over: Partial<ExportFicheActionDialogData> = {}): {
  fixture: ComponentFixture<ExportFicheActionDialogComponent>;
  close: jest.Mock;
} {
  const close = jest.fn();
  const data: ExportFicheActionDialogData = {
    actionLabel: 'CS1 Suivi des oiseaux',
    sections: SECTIONS,
    sectionVisibility: { description: true, realisation: true },
    ...over,
  };
  TestBed.configureTestingModule({
    imports: [ExportFicheActionDialogComponent, NoopAnimationsModule, TranslateModule.forRoot()],
    providers: [
      { provide: MatDialogRef, useValue: { close } },
      { provide: MAT_DIALOG_DATA, useValue: data },
    ],
  });
  const fixture = TestBed.createComponent(ExportFicheActionDialogComponent);
  fixture.detectChanges();
  return { fixture, close };
}

describe('ExportFicheActionDialogComponent (#642)', () => {
  it('propose les deux formats, impression sélectionnée par défaut', () => {
    const { fixture } = setup();
    const cards = fixture.nativeElement.querySelectorAll('.format-card');
    expect(cards.length).toBe(2);
    expect(cards[0].classList).toContain('selected');
    expect(cards[1].classList).not.toContain('selected');
  });

  it('renvoie le format Excel et masque alors le choix des sections', () => {
    const { fixture, close } = setup();
    const c = fixture.componentInstance;

    c.selectFormat('xlsx');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.sections-block')).toBeNull();

    c.confirm();
    expect(close).toHaveBeenCalledWith(
      expect.objectContaining({ format: 'xlsx' }),
    );
  });

  it('renvoie les sections retenues pour l\'impression', () => {
    const { fixture, close } = setup();
    const c = fixture.componentInstance;
    expect(fixture.nativeElement.querySelectorAll('.sections-list app-checkbox').length).toBe(2);

    c.setSectionVisible('realisation', false);
    c.confirm();

    expect(close).toHaveBeenCalledWith({
      format: 'print',
      sections: { description: true, realisation: false },
    });
  });

  it('ferme sans résultat à l\'annulation', () => {
    const { fixture, close } = setup();
    fixture.componentInstance.cancel();
    expect(close).toHaveBeenCalledWith();
  });
});
