import { TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { IndicateurGlobalComponent } from './indicateur-global.component';
import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { EnjeuService } from '../../../../core/services/enjeu.service';

/**
 * #572 — L'icône du résultat doit refléter le score arrondi au niveau le plus
 * proche : une moyenne de 2,1 → « mauvais » (bad), pas « très mauvais ».
 */
describe('IndicateurGlobalComponent — mapping score → niveau (#572)', () => {
  let component: IndicateurGlobalComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [IndicateurGlobalComponent, NoopAnimationsModule, HttpClientTestingModule, TranslateModule.forRoot()],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: { get: () => null } } } },
        { provide: AdminService, useValue: {} },
        { provide: AuthService, useValue: { isSuperAdmin: () => false, isAdminOrganisme: () => false } },
        { provide: EnjeuService, useValue: { getIndicateurGlobal: () => of(null) } },
        { provide: MatSnackBar, useValue: { open: jest.fn() } },
      ],
    });
    component = TestBed.createComponent(IndicateurGlobalComponent).componentInstance;
  });

  it('arrondit au niveau le plus proche (2,1 → mauvais, pas très mauvais)', () => {
    expect(component.scoreToLevel(2.1)).toBe('bad');
    expect(component.scoreToLevel(2.4)).toBe('bad');
    expect(component.scoreToLevel(2.5)).toBe('neutral');
    expect(component.scoreToLevel(1.4)).toBe('very-bad');
    expect(component.scoreToLevel(4.6)).toBe('very-good');
  });

  it('renvoie no-data pour null/0', () => {
    expect(component.scoreToLevel(null)).toBe('no-data');
    expect(component.scoreToLevel(undefined)).toBe('no-data');
  });

  it('getScoreBadge pointe vers le badge du niveau arrondi', () => {
    expect(component.getScoreBadge(2.1)).toContain('bad');
    expect(component.getScoreBadge(2.1)).not.toContain('very-bad');
  });
});
