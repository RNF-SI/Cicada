import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
// Données de langue française (format des nombres « 1 500 € ») : la version
// « global » s'enregistre d'elle-même et se charge sans module ESM.
import '@angular/common/locales/global/fr';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import { readFileSync } from 'fs';
import { join } from 'path';
import { Observable, firstValueFrom, of } from 'rxjs';

import {
  PlanPlanificationAnnuelleComponent, correspondAuFiltre, statutAnnuelKey,
} from './plan-planification-annuelle.component';
import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../../core/services/admin.service';
import { PlanificationAnnuelleService } from '../../../../core/services/planification-annuelle.service';
import {
  LigneTableauAnnuel, ResumeAnnuel, TableauAnnuel,
} from '../../../../core/models/planification-annuelle.model';

/** Les vrais libellés : un libellé manquant se verrait dans les assertions. */
class FrLoader implements TranslateLoader {
  getTranslation(): Observable<any> {
    return of(JSON.parse(readFileSync(
      join(__dirname, '../../../../../assets/i18n/fr.json'), 'utf8')));
  }
}

function resume(partiel: Partial<ResumeAnnuel> = {}): ResumeAnnuel {
  return {
    statut: 'planifiee', annee_report: null, report_de: null, mois: [],
    budget: '0.00', budget_fonctionnement: '0.00', budget_investissement: '0.00',
    jours: '0.00', jours_benevole: '0.00', financeurs: '0.00', ...partiel,
  };
}

function ligne(partiel: Partial<LigneTableauAnnuel>): LigneTableauAnnuel {
  return {
    id_operation: 1, code: 'CS1', libelle: 'Action', programmation_globale: false,
    pg: resume(), pg_global: null, ajuste: resume(), ajustee: false, diverge: false,
    revue: false, date_revue: null, reports_entrants: [],
    realise: { saisi: false, niveau: null }, ...partiel,
  };
}

const ANNEE = 2026;

/** Trois actions : une ajustée (revue, budget en hausse), une reportée en
 *  2027 qui reçoit le reste de 2025, une programmée globalement. */
function tableau(partiel: Partial<TableauAnnuel> = {}): TableauAnnuel {
  return {
    id_pg: 10, annee: ANNEE, annees: [2025, 2026, 2027], revues: 1, total: 3, peut_saisir: true,
    actions: [
      ligne({
        id_operation: 1, code: 'CS1', libelle: 'Suivi des prairies',
        pg: resume({ budget: '1000.00', jours: '5.00', mois: [4, 5] }),
        ajuste: resume({ budget: '1500.00', jours: '5.00', mois: [6] }),
        ajustee: true, diverge: true, revue: true, date_revue: '2026-03-02T10:00:00Z',
      }),
      ligne({
        id_operation: 2, code: 'IP1', libelle: 'Fauche tardive',
        pg: resume({ budget: '2000.00', jours: '8.00' }),
        ajuste: resume({ statut: 'reportee', annee_report: 2027 }),
        ajustee: true, diverge: true,
        reports_entrants: [{ annee: 2025, partiel: true }],
      }),
      ligne({
        id_operation: 3, code: 'PA1', libelle: 'Animation', programmation_globale: true,
        pg: resume({ budget: '300.00' }),
        pg_global: resume({ budget: '9000.00', jours: '30.00' }),
        ajuste: resume({ budget: '700.00', jours: '2.00' }),
      }),
    ],
    ...partiel,
  };
}

describe('Planification annuelle — règles d\'affichage (#794)', () => {
  it('un report partiel garde l\'année planifiée mais se signale', () => {
    expect(statutAnnuelKey(resume({ annee_report: 2027 }))).toBe('reportee_partiel');
    expect(statutAnnuelKey(resume({ statut: 'reportee', annee_report: 2027 }))).toBe('reportee');
    expect(statutAnnuelKey(resume({ statut: 'non_prevue' }))).toBe('non_prevue');
  });

  it('filtre par statut ajusté, revue et divergence', () => {
    const [a, b, c] = tableau().actions;
    expect([a, b, c].filter(l => correspondAuFiltre(l, 'reportee'))).toEqual([b]);
    expect([a, b, c].filter(l => correspondAuFiltre(l, 'a_revoir'))).toEqual([b, c]);
    expect([a, b, c].filter(l => correspondAuFiltre(l, 'diverge'))).toEqual([a, b]);
    expect([a, b, c].filter(l => correspondAuFiltre(l, 'planifiee'))).toEqual([a, c]);
  });
});

describe('PlanPlanificationAnnuelleComponent (#794)', () => {
  let fixture: ComponentFixture<PlanPlanificationAnnuelleComponent>;
  let service: { tableau: jest.Mock };
  let router: { navigate: jest.Mock };

  async function rendre(t: TableauAnnuel, statut = 'valide') {
    service = { tableau: jest.fn().mockReturnValue(of(t)) };
    router = { navigate: jest.fn() };
    await TestBed.configureTestingModule({
      imports: [
        PlanPlanificationAnnuelleComponent, NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FrLoader } }),
      ],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: {
          paramMap: { get: () => 'plan-test' }, queryParamMap: { get: () => null } } } },
        { provide: Router, useValue: router },
        { provide: AdminService, useValue: {
          getPlanBySlug: () => of({ id_pg: 10, nom: 'Plan test', statut }) } },
        { provide: PlanificationAnnuelleService, useValue: service },
      ],
    })
      .overrideComponent(PlanPlanificationAnnuelleComponent, {
        remove: { imports: [HeaderComponent, PlanSidebarComponent] },
        add: { schemas: [CUSTOM_ELEMENTS_SCHEMA] },
      })
      .compileComponents();
    await firstValueFrom(TestBed.inject(TranslateService).use('fr'));
    fixture = TestBed.createComponent(PlanPlanificationAnnuelleComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  const texte = (el: Element | null) => (el?.textContent ?? '').replace(/\s+/g, ' ').trim();

  afterEach(() => TestBed.resetTestingModule());

  it('annonce l\'avancement de la revue de l\'année', async () => {
    const el = await rendre(tableau());
    expect(service.tableau).toHaveBeenCalledWith(10, null);
    expect(texte(el.querySelector('[data-testid="planification-revue"]')))
      .toContain('1 / 3 actions revues pour 2026');
  });

  it('distingue le plan de gestion de l\'ajusté, avec l\'écart', async () => {
    const el = await rendre(tableau());
    const ligneA = texte(el.querySelector('[data-testid="planification-ligne-1"]'));
    expect(ligneA).toContain('1 000 €');
    expect(ligneA).toContain('1 500 €');
    expect(ligneA).toContain('+500 €');
    expect(ligneA).toContain('juin');
    expect(ligneA).toContain('Plan de gestion : avr., mai');
  });

  it('affiche le report et les reports reçus', async () => {
    const el = await rendre(tableau());
    const ligneB = texte(el.querySelector('[data-testid="planification-ligne-2"]'));
    expect(ligneB).toContain('Reportée en 2027');
    expect(ligneB).toContain('Reste de 2025');
    expect(ligneB).toContain('À revoir');
  });

  it('une action programmée globalement montre ses moyens sur la période', async () => {
    const el = await rendre(tableau());
    const ligneC = texte(el.querySelector('[data-testid="planification-ligne-3"]'));
    expect(ligneC).toContain('9 000 € · 30 j sur la période');
    // Total du plan de gestion : sans l'action globale (pas de montant annuel).
    const total = texte(el.querySelector('tfoot'));
    expect(total).toContain('3 000 €');
    expect(total).toContain('2 200 €');
  });

  it('filtre les actions à revoir', async () => {
    const el = await rendre(tableau());
    fixture.componentInstance.filtre.set('a_revoir');
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="planification-ligne-1"]')).toBeNull();
    expect(el.querySelector('[data-testid="planification-ligne-2"]')).not.toBeNull();
  });

  it('annonce la consultation seule sans droit de saisie', async () => {
    const el = await rendre(tableau({ peut_saisir: false }));
    expect(el.querySelector('[data-testid="planification-lecture-seule"]')).not.toBeNull();
  });

  it('change d\'année en rechargeant le tableau', async () => {
    await rendre(tableau());
    fixture.componentInstance.choisirAnnee(2027);
    expect(service.tableau).toHaveBeenLastCalledWith(10, 2027);
    expect(router.navigate).toHaveBeenCalledWith([], expect.objectContaining({
      queryParams: { annee: 2027 } }));
  });
});
