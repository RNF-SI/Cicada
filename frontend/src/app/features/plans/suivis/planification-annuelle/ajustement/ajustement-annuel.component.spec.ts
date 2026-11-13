import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { MatDialog, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import { readFileSync } from 'fs';
import { join } from 'path';
import { Observable, firstValueFrom, of, throwError } from 'rxjs';
// Format des nombres en français (« 1 500 € ») sans module ESM.
import '@angular/common/locales/global/fr';

import { AjustementAnnuelComponent } from './ajustement-annuel.component';
import { ReportAjustementDialogComponent } from '../report-dialog/report-ajustement-dialog.component';
import { HeaderComponent } from '../../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../../../core/services/admin.service';
import { PlanificationAnnuelleService } from '../../../../../core/services/planification-annuelle.service';
import { DetailAnnuel, ResumeAnnuel } from '../../../../../core/models/planification-annuelle.model';

class FrLoader implements TranslateLoader {
  getTranslation(): Observable<any> {
    return of(JSON.parse(readFileSync(
      join(__dirname, '../../../../../../assets/i18n/fr.json'), 'utf8')));
  }
}

function resume(partiel: Partial<ResumeAnnuel> = {}): ResumeAnnuel {
  return {
    statut: 'planifiee', annee_report: null, report_de: null, mois: [],
    budget: '0.00', budget_fonctionnement: '0.00', budget_investissement: '0.00',
    jours: '0.00', jours_benevole: '0.00', financeurs: '0.00', ...partiel,
  };
}

/** Action « aucune ventilation » : 1 000 € et 5 j en avril-mai au plan de gestion. */
function detail(partiel: Partial<DetailAnnuel> = {}): DetailAnnuel {
  const pg = {
    statut: 'planifiee' as const, budget: '1000.00', periodicite_mensuelle: { '4': true, '5': true },
    organismes: [], rh_lignes: [{ id_poste: null, id_organisme: null, jours: '5.00', finance: true,
      categorie_depense: 'fonctionnement' as const }], financeurs: [], commentaire: '',
  };
  return {
    id_operation: 12, code: 'CS1', libelle: 'Suivi des prairies', annee: 2026, annees: [2025, 2026, 2027],
    reglages: {
      ventilation_mode: 'none', declinaison_par_poste: false, declinaison_par_type_cout: false,
      cout_salarial_auto: true, programmation_globale: false, temps_par_poste: false,
    },
    pg, pg_resume: resume({ budget: '1000.00', jours: '5.00', mois: [4, 5] }),
    pg_global: null, pg_global_resume: null,
    financeurs_pg: [{ id_financeur: 3, nom: 'Région', montant: '6000.00' }],
    ajustement: null, effectif: pg, effectif_resume: resume({ budget: '1000.00', jours: '5.00', mois: [4, 5] }),
    effectif_reglages: { declinaison_par_type_cout: false, cout_salarial_auto: true, declinaison_par_poste: false },
    diverge: false, reports_entrants: [], realise: { saisi: false, niveau: null }, fixe: false,
    peut_saisir: true,
    choix: { organismes: [], postes: [], financeurs: [{ id_financeur: 3, nom: 'Région' }] },
    ...partiel,
  };
}

describe('AjustementAnnuelComponent (#794)', () => {
  let fixture: ComponentFixture<AjustementAnnuelComponent>;
  let service: {
    detail: jest.Mock; tableau: jest.Mock; enregistrer: jest.Mock; revenirAuPlan: jest.Mock;
    convertir: jest.Mock;
  };
  let router: { navigate: jest.Mock };
  let dialog: { open: jest.Mock };

  async function rendre(d: DetailAnnuel) {
    service = {
      detail: jest.fn().mockReturnValue(of(d)),
      tableau: jest.fn().mockReturnValue(of({ actions: [{ id_operation: 12 }, { id_operation: 13 }] })),
      enregistrer: jest.fn().mockReturnValue(of(d)),
      revenirAuPlan: jest.fn().mockReturnValue(of(undefined)),
      convertir: jest.fn(),
    };
    router = { navigate: jest.fn() };
    dialog = { open: jest.fn().mockReturnValue({ afterClosed: () => of(true) }) };
    const params = convertToParamMap({ slug: 'plan-test', operation_id: '12', annee: '2026' });
    await TestBed.configureTestingModule({
      imports: [
        AjustementAnnuelComponent, NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FrLoader } }),
      ],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: params }, paramMap: of(params) } },
        { provide: Router, useValue: router },
        { provide: AdminService, useValue: { getPlanBySlug: () => of({ id_pg: 10, nom: 'Plan', statut: 'valide' }) } },
        { provide: PlanificationAnnuelleService, useValue: service },
        { provide: MatSnackBar, useValue: { open: jest.fn() } },
        { provide: MatDialog, useValue: dialog },
      ],
    })
      .overrideComponent(AjustementAnnuelComponent, {
        remove: { imports: [HeaderComponent, PlanSidebarComponent] },
        add: { schemas: [CUSTOM_ELEMENTS_SCHEMA] },
      })
      .compileComponents();
    await firstValueFrom(TestBed.inject(TranslateService).use('fr'));
    fixture = TestBed.createComponent(AjustementAnnuelComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  const texte = (el: Element | null) => (el?.textContent ?? '').replace(/\s+/g, ' ').trim();

  afterEach(() => TestBed.resetTestingModule());

  it('rappelle le plan de gestion et propose de saisir l\'ajusté', async () => {
    const el = await rendre(detail());
    expect(texte(el.querySelector('[data-testid="ajustement-synthese"]'))).toContain('1 000 € · 5 j');
    const budget = el.querySelector<HTMLInputElement>('[data-testid="champ-budget"]')!;
    expect(budget).not.toBeNull();
    expect(texte(el.querySelector('[data-testid="ajustement-temps"]'))).toContain('Temps de travail total');
  });

  it('le total ajusté suit la saisie', async () => {
    const el = await rendre(detail());
    fixture.componentInstance.contenu.budget = '1500';
    fixture.detectChanges();
    expect(texte(el.querySelector('[data-testid="ajustement-total"]'))).toContain('1 500 € · 5 j');
  });

  it('une année non prévue n\'a ni mois ni moyens à saisir', async () => {
    const el = await rendre(detail());
    fixture.componentInstance.choisirStatut('non_prevue');
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="ajustement-mois"]')).toBeNull();
    expect(el.querySelector('[data-testid="ajustement-budget"]')).toBeNull();
  });

  it('enregistre sans les lignes vides et passe à l\'action suivante', async () => {
    await rendre(detail());
    const c = fixture.componentInstance;
    c.contenu.rh_lignes!.push({ id_poste: null, id_organisme: null, jours: null });
    c.ajouterFinanceur(3);
    c.contenu.financeurs![0].montant = '2500';
    c.enregistrer(true);
    const [op, annee, envoye] = service.enregistrer.mock.calls[0];
    expect([op, annee]).toEqual([12, 2026]);
    expect(envoye.rh_lignes).toHaveLength(1);
    expect(envoye.financeurs).toEqual([{ id_financeur: 3, montant: '2500' }]);
    expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-test', 'planification-annuelle', 13, 2026]);
  });

  it('le report attend que la saisie soit enregistrée', async () => {
    const el = await rendre(detail());
    const bouton = () => el.querySelector<HTMLButtonElement>('[data-testid="ajustement-reporter"]')!;
    expect(bouton().disabled).toBe(false);
    fixture.componentInstance.contenu.budget = '1200';
    fixture.detectChanges();
    expect(bouton().disabled).toBe(true);
  });

  it('la synthèse date la programmation du plan de gestion (retour 13/11)', async () => {
    const el = await rendre(detail());
    expect(texte(el.querySelector('[data-testid="ajustement-synthese"]'))).toContain('Plan de gestion pour 2026');
  });

  it('le budget a sa ligne de total, plan de gestion et ajusté (retour 13/11)', async () => {
    const el = await rendre(detail());
    fixture.componentInstance.contenu.budget = '1500';
    fixture.detectChanges();
    const total = texte(el.querySelector('[data-testid="budget-total"]'));
    expect(total).toContain('1 000 €');
    expect(total).toContain('1 500 €');
  });

  it('une action revue s\'ouvre en lecture ; « Modifier » rouvre la saisie (retour 13/11)', async () => {
    const revue = {
      ...detail().effectif, id_ajustement_annuel: 5, date_revue: '2026-11-13T10:00:00Z',
      revue_par: 'Sophie', date_maj: '2026-11-13T10:00:00Z',
    };
    const el = await rendre(detail({ ajustement: revue }));
    const champ = () => el.querySelector<HTMLInputElement>('[data-testid="champ-budget"]')!;
    expect(champ().disabled).toBe(true);
    expect(el.querySelector('[data-testid="ajustement-enregistrer"]')).toBeNull();
    el.querySelector<HTMLButtonElement>('[data-testid="ajustement-modifier"]')!.click();
    fixture.detectChanges();
    await fixture.whenStable();
    expect(champ().disabled).toBe(false);
    expect(el.querySelector('[data-testid="ajustement-enregistrer"]')).not.toBeNull();
  });

  it('« Annuler les modifications » revient au plan de gestion (retour 13/11)', async () => {
    const revue = {
      ...detail().effectif, id_ajustement_annuel: 5, date_revue: '2026-11-13T10:00:00Z',
      revue_par: 'Sophie', date_maj: '2026-11-13T10:00:00Z',
    };
    const el = await rendre(detail({ ajustement: revue }));
    el.querySelector<HTMLButtonElement>('[data-testid="ajustement-revenir"]')!.click();
    expect(service.revenirAuPlan).toHaveBeenCalledWith(12, 2026);
  });

  it('cocher la déclinaison par type de coût réécrit la saisie (retour 13/11)', async () => {
    const el = await rendre(detail());
    service.convertir.mockReturnValue(of({
      contenu: { ...detail().effectif, budget: null, autre_cout: '1000.00', declinaison_par_type_cout: true },
      reglages: { declinaison_par_type_cout: true, cout_salarial_auto: true, declinaison_par_poste: false },
      resume: resume({ budget: '1000.00' }),
    }));
    fixture.componentInstance.changerReglage('declinaison_par_type_cout', true);
    fixture.detectChanges();
    const [op, annee, contenu, reglages] = service.convertir.mock.calls[0];
    expect([op, annee, contenu.budget, reglages]).toEqual([12, 2026, '1000.00', { declinaison_par_type_cout: true }]);
    expect(el.querySelector<HTMLInputElement>('[data-testid="champ-autre_cout"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="champ-budget"]')).toBeNull();
  });

  it('consultation seule : rien ne se saisit', async () => {
    const el = await rendre(detail({ peut_saisir: false }));
    expect(el.querySelector('[data-testid="ajustement-lecture-seule"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="ajustement-enregistrer"]')).toBeNull();
    expect(el.querySelector<HTMLInputElement>('[data-testid="champ-budget"]')!.disabled).toBe(true);
  });
});

describe('ReportAjustementDialogComponent (#794)', () => {
  let component: ReportAjustementDialogComponent;
  let service: { reporter: jest.Mock };
  let ref: { close: jest.Mock };
  const apercu = {
    annee: 2026, annee_report: 2027, partiel: false, applique: false,
    annees: [], deplacements: [{ de: 2026, vers: 2027 }], abandonnees: [{ annee: 2028, resume: resume() }],
  };

  beforeEach(() => {
    service = { reporter: jest.fn().mockReturnValue(of(apercu)) };
    ref = { close: jest.fn() };
    TestBed.configureTestingModule({
      providers: [
        { provide: MAT_DIALOG_DATA, useValue: { operationId: 12, annee: 2026, annees: [2027, 2028], libelle: 'CS1' } },
        { provide: MatDialogRef, useValue: ref },
        { provide: PlanificationAnnuelleService, useValue: service },
        { provide: TranslateService, useValue: { instant: (k: string) => k } },
      ],
    });
    component = TestBed.runInInjectionContext(() => new ReportAjustementDialogComponent());
  });

  it('montre l\'aperçu sans rien écrire, puis confirme', () => {
    component.voirApercu();
    expect(service.reporter).toHaveBeenCalledWith(12, 2026, { annee_report: 2027, partiel: false, apercu: true });
    expect(component.apercu()).toBe(apercu);
    expect(component.anneesAbandonnees(apercu)).toBe('2028');
    component.confirmer();
    expect(service.reporter).toHaveBeenLastCalledWith(12, 2026, { annee_report: 2027, partiel: false, apercu: false });
    expect(ref.close).toHaveBeenCalledWith(apercu);
  });

  it('changer d\'année ou de type rend l\'aperçu périmé', () => {
    component.voirApercu();
    component.choixModifie();
    expect(component.apercu()).toBeNull();
  });

  it('affiche le refus du serveur', () => {
    service.reporter.mockReturnValue(throwError(() => ({ error: { detail: 'Déjà reportée', code: 'deja_reportee' } })));
    component.voirApercu();
    expect(component.erreur()).toBe('Déjà reportée');
    expect(ref.close).not.toHaveBeenCalled();
  });
});
