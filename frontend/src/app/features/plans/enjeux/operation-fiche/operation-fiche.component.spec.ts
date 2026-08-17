/**
 * Tests unitaires — OperationFicheComponent (#516).
 *
 * Régression couverte : dans la fiche d'action, les métriques « en blocs » des
 * indicateurs État/Pression n'apparaissaient pas (seul leur nom était listé en
 * texte), alors que les indicateurs de réponse affichaient bien leur grille.
 * On vérifie ici que la fiche rend une grille (`app-metrique-grid-display`) pour
 * TOUS les indicateurs liés — réponse ET état/pression — et donc leurs blocs.
 */
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { MatDialog } from '@angular/material/dialog';

import { OperationFicheComponent } from './operation-fiche.component';
import { ProtocoleCampanuleDialogComponent } from '../../../../shared/components/modals/protocole-campanule-dialog/protocole-campanule-dialog.component';
import { ExportFicheActionDialogComponent } from '../../../../shared/components/modals/export-fiche-action-dialog/export-fiche-action-dialog.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { Operation } from '../../../../core/models/enjeu.model';

/** Métrique NUMERIQUE en grille avec 1 bloc complémentaire (ET/OU). */
function multiBlockMetrique(over: Record<string, unknown>): any {
  return {
    id_metrique: 1,
    nom_metrique: 'Métrique',
    type_metrique_mnemonique: 'NUMERIQUE',
    format_metrique_mnemonique: 'GRILLE',
    bloc_intitule: 'Bloc principal',
    unite: 'u',
    score_1_inf: 0, score_1_sup: 10,
    score_2_inf: 10, score_2_sup: 20,
    score_blocks: [
      {
        id_score_block: 9, position: 1, intitule: 'Bloc secondaire', unite: 'v',
        logical_op: 'OR', group_open: 0, group_close: 0, sens_variation: 'CROISSANT',
        score_1_inf: 0, score_1_sup: 5, score_2_inf: 5, score_2_sup: 10,
      },
    ],
    ...over,
  };
}

function operationWith(metriques: any[]): Operation {
  return {
    id_operation: 42,
    libelle: 'Action test',
    metriques,
    operation_annees: [],
    finances: [],
  } as unknown as Operation;
}

function setup(
  op: Operation,
  opts: { from?: string; fromEnjeu?: string; router?: { navigate: jest.Mock } } = {},
): ComponentFixture<OperationFicheComponent> {
  const enjeuService = {
    getOperation: jest.fn().mockReturnValue(of(op)),
    // #642 — export Excel de la fiche action.
    downloadOperationFicheXlsx: jest.fn().mockReturnValue(of(new Blob(['x']))),
  };
  const queryParamMap = new Map<string, string>();
  if (opts.from) queryParamMap.set('from', opts.from);
  if (opts.fromEnjeu) queryParamMap.set('fromEnjeu', opts.fromEnjeu);
  const route = {
    snapshot: {
      paramMap: new Map<string, string>([['operationId', '42'], ['slug', 'plan-x']]),
      queryParamMap,
    },
    parent: null,
  };
  // Map#get already matches ParamMap.get signature for our usage.
  TestBed.configureTestingModule({
    imports: [OperationFicheComponent, NoopAnimationsModule, TranslateModule.forRoot()],
    providers: [
      { provide: EnjeuService, useValue: enjeuService },
      { provide: ActivatedRoute, useValue: route },
      { provide: Router, useValue: opts.router ?? { navigate: jest.fn() } },
    ],
  });
  const fixture = TestBed.createComponent(OperationFicheComponent);
  fixture.detectChanges();
  return fixture;
}

describe('OperationFicheComponent — grilles/blocs des indicateurs (#516)', () => {
  it('sépare les indicateurs de réponse des indicateurs état/pression', () => {
    const fixture = setup(operationWith([
      multiBlockMetrique({ id_metrique: 1, indicateur_id: 100, indicateur_nom: 'Rép', indicateur_type: 'REPONSE' }),
      multiBlockMetrique({ id_metrique: 2, indicateur_id: 200, indicateur_nom: 'Pres', indicateur_type: 'PRESSION' }),
    ]));
    const c = fixture.componentInstance;
    expect(c.indicateursReponse().map(i => i.id)).toEqual([100]);
    expect(c.indicateursEtatPression().map(i => i.id)).toEqual([200]);
  });

  it('#613 — grille pour la réponse, mais liste (pas de grille) pour l\'état/pression', () => {
    const fixture = setup(operationWith([
      multiBlockMetrique({ id_metrique: 1, indicateur_id: 100, indicateur_nom: 'Rép', indicateur_type: 'REPONSE' }),
      multiBlockMetrique({ id_metrique: 2, indicateur_id: 200, indicateur_nom: 'Pres', indicateur_type: 'PRESSION' }),
    ]));
    // #613 — l'état/pression est résumé en liste d'intitulés en tête de fiche :
    // il ne reste qu'UNE grille (celle de l'indicateur de réponse).
    const grids = fixture.nativeElement.querySelectorAll('app-metrique-grid-display');
    expect(grids.length).toBe(1);
    expect(fixture.componentInstance.cadreIndicateurs()?.indicateurs).toContain('Pres');
  });

  it('#613 — résume l\'indicateur état/pression en liste d\'intitulés + métriques (unité), sans grille', () => {
    const fixture = setup(operationWith([
      multiBlockMetrique({ id_metrique: 2, indicateur_id: 200, indicateur_nom: 'Pres', indicateur_type: 'PRESSION' }),
    ]));
    const cadre = fixture.componentInstance.cadreIndicateurs();
    expect(cadre?.indicateurs).toContain('Pres');
    expect(cadre?.metriques).toContain('Métrique (u)');
    // plus aucune grille de blocs pour l'état/pression
    expect(fixture.nativeElement.querySelectorAll('app-metrique-grid-display').length).toBe(0);
  });
});

describe('OperationFicheComponent — programmation détaillée (#556)', () => {
  function operationWithAnnees(annees: any[]): Operation {
    return {
      id_operation: 42, libelle: 'Action test',
      metriques: [], operation_annees: annees, finances: [],
    } as unknown as Operation;
  }

  it('exprime le travail en jours (colonne « Jours », plus « ETP »)', () => {
    const fixture = setup(operationWithAnnees([{ annee: 2024, periodicite: true, budget: 100, etp: 3 }]));
    const text: string = fixture.nativeElement.textContent;
    expect(text).toContain('plans.suivis.actions.fiche.jours');
    expect(text).not.toContain('plans.suivis.actions.fiche.etp');
  });

  it('ventile le budget par type (fonctionnement / investissement) quand saisi', () => {
    const fixture = setup(operationWithAnnees([
      {
        annee: 2024, periodicite: true,
        budget_fonctionnement: 200, budget_investissement: 50,
        rh_lignes: [{ id_poste: 1, poste_libelle: 'Garde', jours: 2, finance: true }],
      },
    ]));
    const c = fixture.componentInstance;
    expect(c.hasBudgetTypes()).toBe(true);
    const row = c.programmation()[0];
    expect(row.fonctionnement).toBe(200);
    expect(row.investissement).toBe(50);
    expect(row.budget).toBe(250);
    expect(row.jours).toBe(2);
    expect(c.totalBudget()).toBe(250);
    expect(c.totalJours()).toBe(2);
  });

  // #581 — DRF sérialise les décimaux en chaînes ("200.00"). Sans coercition,
  // l'addition concatène les chaînes et le budget devient illisible dans la
  // fiche. On reproduit ici la forme réelle de la réponse API (chaînes).
  it('additionne le budget ventilé par type reçu en chaînes (#581)', () => {
    const fixture = setup(operationWithAnnees([
      {
        annee: 2024, periodicite: true,
        budget_fonctionnement: '200.00', budget_investissement: '50.00',
      },
    ]));
    const c = fixture.componentInstance;
    const row = c.programmation()[0];
    expect(row.fonctionnement).toBe(200);
    expect(row.investissement).toBe(50);
    expect(row.budget).toBe(250);        // et non "200.0050.00"
    expect(c.totalBudget()).toBe(250);   // et non NaN
  });

  it('affiche le budget total (mode direct) reçu en chaîne (#581)', () => {
    const fixture = setup(operationWithAnnees([
      { annee: 2024, periodicite: true, budget: '1234.50' },
    ]));
    const c = fixture.componentInstance;
    expect(c.programmation()[0].budget).toBe(1234.5);
    expect(c.totalBudget()).toBe(1234.5);
  });

  it('#613 — valorise TOUJOURS le coût salarial (jours × coût/jour) sans changer le budget', () => {
    const fixture = setup(operationWithAnnees([
      {
        annee: 2027, periodicite: true, budget: '1500.00',
        rh_lignes: [{
          id_poste: 1, jours: '4.00', categorie_depense: 'fonctionnement',
          poste_cout_jour: '300.00',
        }],
      },
    ]));
    const c = fixture.componentInstance;
    // mode « totaux directs » : le salarial n'est pas un mode « par poste »,
    // mais il est valorisé (4 × 300 = 1200) et affiché dans le détail…
    const sal = c.coutDetail().rows.find(r => r.key === 'coutSalarial');
    expect(sal?.fonct).toBe(1200);
    expect(c.hasCoutDetail()).toBe(true);
    // …sans modifier le budget total saisi (1500).
    expect(c.programmation()[0].budget).toBe(1500);
    expect(c.totalBudget()).toBe(1500);
  });

  it('agrège la répartition par organisme reçue en chaînes (#581)', () => {
    const fixture = setup(operationWithAnnees([
      {
        annee: 2024, periodicite: true,
        organismes: [
          { id_organisme: 1, organisme_nom: 'CEN', budget_fonctionnement: '100.00', budget_investissement: '0.00' },
          { id_organisme: 2, organisme_nom: 'RNF', budget_fonctionnement: '50.00', budget_investissement: '20.00' },
        ],
      },
    ]));
    const c = fixture.componentInstance;
    const cen = c.organismeBreakdown().find(o => o.nom === 'CEN')!;
    expect(cen.fonctionnement).toBe(100);
    expect(cen.budget).toBe(100);
    // Budget de l'année dérivé de la ventilation par organisme (chaînes).
    expect(c.programmation()[0].budget).toBe(170);
  });

  it('#600/#602 fiche : totaux fonct/invest par organisme (coûts inclus, salarial ventilé par catégorie)', () => {
    const fixture = setup(operationWithAnnees([
      {
        annee: 2024, periodicite: true,
        organismes: [
          {
            id_organisme: 1, organisme_nom: 'CEN',
            budget_fonctionnement: '100.00', budget_investissement: '0.00',
            cout_stage: '80.00', cout_prestataire: '120.00', autre_cout: '50.00',
            cout_prestataire_invest: '200.00', autre_cout_invest: '30.00',
          },
        ],
        rh_lignes: [
          // 10 j × 300 €/j en fonctionnement = 3000 €.
          { id_poste: 5, poste_id_organisme: 1, poste_cout_jour: '300.00', jours: 10, finance: true, categorie_depense: 'fonctionnement' },
          // 4 j × 300 €/j en investissement = 1200 €.
          { id_poste: 5, poste_id_organisme: 1, poste_cout_jour: '300.00', jours: 4, finance: true, categorie_depense: 'investissement' },
        ],
      },
    ]));
    const c = fixture.componentInstance;
    const cen = c.organismeBreakdown().find(o => o.nom === 'CEN')!;
    // Fonct = 100 + 80 + 120 + 50 + 3000 (salarial fonct) = 3350
    expect(cen.fonctionnement).toBe(3350);
    // Invest = 0 + 200 + 30 + 1200 (salarial invest) = 1430
    expect(cen.investissement).toBe(1430);
    expect(cen.budget).toBe(4780);
  });

  // #613 — en mode « + type de poste », les enveloppes fonctionnement /
  // investissement ne sont pas stockées (elles se recalculent depuis les
  // composants). La fiche affichait donc 0 € par année alors que la
  // répartition par organisme, elle, montrait le vrai montant.
  it('dérive le budget annuel des coûts saisis en mode « + type de poste » (#613)', () => {
    const op = operationWithAnnees([
      {
        annee: 2024, periodicite: true, budget: null,
        budget_fonctionnement: null, budget_investissement: null,
        organismes: [{
          id_organisme: 1, organisme_nom: 'RNF',
          budget_fonctionnement: null, budget_investissement: null,
          cout_stage: '200.00', cout_prestataire: '1000.00', autre_cout: '500.00',
          cout_prestataire_invest: '300.00', autre_cout_invest: '50.00',
        }],
        rh_lignes: [
          { id_poste: 5, poste_id_organisme: 1, poste_cout_jour: '300.00', jours: 10, finance: true, categorie_depense: 'fonctionnement' },
          { id_poste: 6, poste_id_organisme: 1, poste_cout_jour: '80.00', jours: 5, finance: true, categorie_depense: 'investissement' },
          { id_poste: 7, poste_id_organisme: 1, poste_cout_jour: '150.00', jours: 2, finance: false, categorie_depense: 'benevolat_partenariat' },
        ],
      },
    ]);
    (op as any).ventilation_mode = 'by_org_type_poste';
    const c = setup(op).componentInstance;

    const row = c.programmation()[0];
    expect(row.fonctionnement).toBe(4700);   // 3000 salarial + 200 + 1000 + 500
    expect(row.investissement).toBe(750);    // 400 salarial + 300 + 50
    expect(row.budget).toBe(5450);           // et non 0 €
    expect(row.jours).toBe(17);              // bénévolat compris
    // Le total de la fiche colle à la répartition par organisme.
    expect(c.totalBudget()).toBe(5450);
    expect(c.organismeBreakdown()[0].budget).toBe(5450);
  });

  // #613 — « la fiche doit être aussi précise que ce qui est saisi ».
  it('détaille les composants de coût (salarial, stage, prestataire, autres) (#613)', () => {
    const op = operationWithAnnees([
      {
        annee: 2024, periodicite: true,
        organismes: [{
          id_organisme: 1, organisme_nom: 'RNF',
          budget_fonctionnement: null, budget_investissement: null,
          cout_stage: '200.00', cout_prestataire: '1000.00', autre_cout: '500.00',
          cout_prestataire_invest: '300.00', autre_cout_invest: '50.00',
        }],
        rh_lignes: [
          { id_poste: 5, poste_id_organisme: 1, poste_cout_jour: '300.00', jours: 10, finance: true, categorie_depense: 'fonctionnement' },
        ],
      },
    ]);
    (op as any).ventilation_mode = 'by_org_type_poste';
    const fixture = setup(op);
    const c = fixture.componentInstance;

    expect(c.hasCoutDetail()).toBe(true);
    const rows = c.coutDetail().rows;
    expect(rows.map(r => r.key)).toEqual([
      'coutSalarial', 'coutStage', 'coutPrestataire', 'autresCouts',
    ]);
    expect(rows.find(r => r.key === 'coutSalarial')).toEqual(
      { key: 'coutSalarial', fonct: 3000, invest: 0 },
    );
    expect(rows.find(r => r.key === 'coutPrestataire')).toEqual(
      { key: 'coutPrestataire', fonct: 1000, invest: 300 },
    );
    expect(c.coutDetail().totalFonct).toBe(4700);
    expect(c.coutDetail().totalInvest).toBe(350);
    expect(fixture.nativeElement.textContent)
      .toContain('plans.suivis.actions.fiche.coutDetailTitle');
  });

  it('n’affiche pas le détail des coûts quand aucun composant n’est saisi (#613)', () => {
    const fixture = setup(operationWithAnnees([
      { annee: 2024, periodicite: true, budget: '1000.00' },
    ]));
    expect(fixture.componentInstance.hasCoutDetail()).toBe(false);
    expect(fixture.nativeElement.textContent)
      .not.toContain('plans.suivis.actions.fiche.coutDetailTitle');
  });

  // #560 — les jours viennent des lignes RH, plus du champ `etp` déprécié.
  it('ignore le champ etp déprécié pour le travail', () => {
    const fixture = setup(operationWithAnnees([
      { annee: 2024, periodicite: true, budget: 100, etp: 99 },
    ]));
    expect(fixture.componentInstance.programmation()[0].jours).toBeNull();
    expect(fixture.componentInstance.totalJours()).toBeNull();
  });

  it('détaille le temps de travail par poste et valorise le non financé (#560)', () => {
    const fixture = setup(operationWithAnnees([
      {
        annee: 2024, periodicite: true,
        rh_lignes: [
          { id_poste: 1, poste_libelle: 'Garde', poste_organisme_nom: 'RNF', jours: 8, finance: true },
          { id_poste: 2, poste_libelle: 'Bénévole', poste_organisme_nom: 'RNF', jours: 5, finance: false },
        ],
      },
      {
        annee: 2025, periodicite: true,
        rh_lignes: [
          { id_poste: 1, poste_libelle: 'Garde', poste_organisme_nom: 'RNF', jours: 4, finance: true },
        ],
      },
    ]));
    const c = fixture.componentInstance;
    const rows = c.rhBreakdown();
    expect(rows.length).toBe(2);
    // Les jours d'une même cible se cumulent sur les années.
    expect(rows.find(r => r.libelle === 'Garde')!.jours).toBe(12);
    expect(rows.find(r => r.libelle === 'Bénévole')!.organisme).toBe('RNF');
    expect(c.hasRhNonFinance()).toBe(true);
    expect(c.totalJoursFinance()).toBe(12);
    expect(c.totalJoursNonFinance()).toBe(5);
    expect(c.totalJours()).toBe(17);
  });

  it('sépare deux lots d\'une même cible selon leur financement (#560)', () => {
    const fixture = setup(operationWithAnnees([
      {
        annee: 2024, periodicite: true,
        rh_lignes: [
          { id_organisme: 1, organisme_nom: 'CEN', jours: 6, finance: true },
          { id_organisme: 1, organisme_nom: 'CEN', jours: 2, finance: false },
        ],
      },
    ]));
    const rows = fixture.componentInstance.rhBreakdown();
    expect(rows.length).toBe(2);
    expect(rows.map(r => r.finance).sort()).toEqual([false, true]);
  });

  it('n\'affiche pas les colonnes de type de budget en saisie à plat', () => {
    const fixture = setup(operationWithAnnees([{ annee: 2024, periodicite: true, budget: 100, etp: 3 }]));
    expect(fixture.componentInstance.hasBudgetTypes()).toBe(false);
  });

  it('agrège la répartition par organisme gestionnaire sur les années', () => {
    const fixture = setup(operationWithAnnees([
      {
        annee: 2024, periodicite: true,
        organismes: [
          { id_organisme: 1, organisme_nom: 'CEN', budget_fonctionnement: 100, budget_investissement: 0, etp: 2 },
          { id_organisme: 2, organisme_nom: 'RNF', budget_fonctionnement: 50, budget_investissement: 20, etp: 1 },
        ],
      },
      {
        annee: 2025, periodicite: true,
        organismes: [
          { id_organisme: 1, organisme_nom: 'CEN', budget_fonctionnement: 30, budget_investissement: 10, etp: 1 },
        ],
      },
    ]));
    const c = fixture.componentInstance;
    const cen = c.organismeBreakdown().find(o => o.nom === 'CEN')!;
    expect(cen.fonctionnement).toBe(130);
    expect(cen.investissement).toBe(10);
    expect(cen.budget).toBe(140);
    // Le budget agrégé au niveau année dérive de la ventilation par organisme.
    expect(c.programmation()[0].budget).toBe(170);
  });
});

describe('OperationFicheComponent — protocole & objectifs (actions CS, #557)', () => {
  function operationWithSuivi(suivi: any): Operation {
    return {
      id_operation: 42, libelle: 'Action CS',
      metriques: [], operation_annees: [], finances: [],
      suivi_inventaire: suivi,
    } as unknown as Operation;
  }

  it('n\'affiche pas la section protocole sans donnée de suivi', () => {
    const fixture = setup(operationWith([]));
    expect(fixture.componentInstance.hasProtocoleSection()).toBe(false);
  });

  it('expose le nom, la description et l\'objectif du protocole + les cibles', () => {
    const fixture = setup(operationWithSuivi({
      objectif_principal: 'Suivre la qualité de l\'eau',
      cibles_principales: 'Macro-invertébrés',
      protocole: {
        nom_protocole: 'IBGN',
        description_protocole: 'Prélèvements mensuels standardisés',
        objectif_protocole: 'Évaluer l\'état écologique',
      },
    }));
    const c = fixture.componentInstance;
    expect(c.hasProtocoleSection()).toBe(true);
    expect(c.protocoleNom()).toBe('IBGN');
    const text: string = fixture.nativeElement.textContent;
    expect(text).toContain('Prélèvements mensuels standardisés');
    expect(text).toContain('Évaluer l\'état écologique');
    expect(text).toContain('Suivre la qualité de l\'eau');
    expect(text).toContain('Macro-invertébrés');
  });

  it('reprend le nom CAMPanule si aucun nom libre n\'est saisi', () => {
    const fixture = setup(operationWithSuivi({
      protocole: { protocole_campanule_nom: 'Rhoméo — Piézométrie' },
    }));
    expect(fixture.componentInstance.protocoleNom()).toBe('Rhoméo — Piézométrie');
  });

  // #593 — lien vers le détail du/des protocole(s) depuis la fiche action.
  it('rend un lien de consultation par protocole CAMPanule', () => {
    const fixture = setup(operationWithSuivi({
      protocoles: [
        { protocole_campanule_nom: 'Rhoméo — Piézométrie', cd_protocole_campanule: 7 },
        { protocole_campanule_nom: 'STOC EPS', cd_protocole_campanule: 12 },
      ],
    }));
    const links = fixture.nativeElement.querySelectorAll('.protocole-link');
    expect(links.length).toBe(2);
    expect(links[0].textContent).toContain('Rhoméo — Piézométrie');
    expect(links[1].textContent).toContain('STOC EPS');
  });

  it('n\'affiche pas de lien pour un protocole libre (hors CAMPanule)', () => {
    const fixture = setup(operationWithSuivi({
      protocoles: [{ nom_protocole: 'Protocole maison' }],
    }));
    expect(fixture.nativeElement.querySelectorAll('.protocole-link').length).toBe(0);
    expect(fixture.nativeElement.textContent).toContain('Protocole maison');
  });

  it('ouvre la modale CAMPanule au clic sur le lien', () => {
    const fixture = setup(operationWithSuivi({
      protocoles: [{ protocole_campanule_nom: 'STOC EPS', cd_protocole_campanule: 12 }],
    }));
    const dialog = TestBed.inject(MatDialog);
    const openSpy = jest.spyOn(dialog, 'open').mockReturnValue({} as any);

    fixture.nativeElement.querySelector('.protocole-link').click();

    expect(openSpy).toHaveBeenCalledWith(
      ProtocoleCampanuleDialogComponent,
      expect.objectContaining({ data: { cdProtocole: 12 } }),
    );
  });

  it('n\'ouvre rien pour un protocole sans code CAMPanule', () => {
    const fixture = setup(operationWithSuivi({ protocoles: [{ nom_protocole: 'Maison' }] }));
    const dialog = TestBed.inject(MatDialog);
    const openSpy = jest.spyOn(dialog, 'open');

    fixture.componentInstance.consulterProtocole({ nom_protocole: 'Maison' } as any);

    expect(openSpy).not.toHaveBeenCalled();
  });
});

describe('OperationFicheComponent — personnalisation des sections de l\'export (#532)', () => {
  it('affiche toutes les sections par défaut (toutes cochées)', () => {
    const fixture = setup(operationWith([]));
    const c = fixture.componentInstance;
    expect(c.toggleableSections.every(s => c.sectionVisible(s.key))).toBe(true);
    // La section « Réalisation » (toujours présente) est rendue.
    expect(fixture.nativeElement.textContent).toContain('plans.suivis.actions.fiche.realisationGlobale');
  });

  it('retire du DOM une section décochée', () => {
    const fixture = setup(operationWith([]));
    const c = fixture.componentInstance;
    c.setSectionVisible('realisation', false);
    fixture.detectChanges();
    expect(c.sectionVisible('realisation')).toBe(false);
    expect(fixture.nativeElement.textContent).not.toContain('plans.suivis.actions.fiche.realisationGlobale');
  });

  it('#642 — le choix des sections a quitté la barre d\'actions pour la modale d\'export', () => {
    const fixture = setup(operationWith([]));
    expect(fixture.nativeElement.querySelector('.fiche-section-picker')).toBeNull();
    expect(fixture.nativeElement.querySelector('.btn-sections')).toBeNull();
  });
});

describe('OperationFicheComponent — modale « Exporter ou imprimer » (#642)', () => {
  /** Simule la fermeture de la modale sur un choix donné (ou une annulation). */
  function stubDialog(result: unknown): jest.SpyInstance {
    const dialog = TestBed.inject(MatDialog);
    return jest.spyOn(dialog, 'open').mockReturnValue({
      afterClosed: () => of(result),
    } as any);
  }

  beforeEach(() => {
    (URL as any).createObjectURL = jest.fn(() => 'blob:fiche');
    (URL as any).revokeObjectURL = jest.fn();
  });

  it('ouvre la modale au clic sur « Exporter ou imprimer », avec les sections courantes', () => {
    const fixture = setup(operationWith([]));
    fixture.componentInstance.setSectionVisible('emprise', false);
    const openSpy = stubDialog(undefined);

    fixture.nativeElement.querySelector('.btn-print').click();

    expect(openSpy).toHaveBeenCalledWith(
      ExportFicheActionDialogComponent,
      expect.objectContaining({
        data: expect.objectContaining({
          sections: fixture.componentInstance.toggleableSections,
          sectionVisibility: expect.objectContaining({ emprise: false }),
        }),
      }),
    );
  });

  it('format « impression » : applique les sections retenues puis imprime', fakeAsync(() => {
    const fixture = setup(operationWith([]));
    stubDialog({ format: 'print', sections: { realisation: false } });
    const printSpy = jest.spyOn(window, 'print').mockImplementation(() => {});

    fixture.componentInstance.openExportDialog();
    // Les sections sont appliquées avant l'ouverture de la fenêtre d'impression.
    expect(fixture.componentInstance.sectionVisible('realisation')).toBe(false);
    expect(printSpy).not.toHaveBeenCalled();

    tick();
    expect(printSpy).toHaveBeenCalled();
    printSpy.mockRestore();
  }));

  it('format « Excel » : télécharge le classeur de la fiche, sans imprimer', () => {
    const fixture = setup(operationWith([]));
    stubDialog({ format: 'xlsx', sections: {} });
    const printSpy = jest.spyOn(window, 'print').mockImplementation(() => {});
    const clickSpy = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    const service = TestBed.inject(EnjeuService) as any;

    fixture.componentInstance.openExportDialog();

    expect(service.downloadOperationFicheXlsx).toHaveBeenCalledWith(42);
    expect(clickSpy).toHaveBeenCalled();
    expect(printSpy).not.toHaveBeenCalled();
    expect(fixture.componentInstance.isExporting()).toBe(false);
    clickSpy.mockRestore();
    printSpy.mockRestore();
  });

  it('n\'exporte rien si la modale est annulée', () => {
    const fixture = setup(operationWith([]));
    stubDialog(undefined);
    const printSpy = jest.spyOn(window, 'print').mockImplementation(() => {});
    const service = TestBed.inject(EnjeuService) as any;

    fixture.componentInstance.openExportDialog();

    expect(service.downloadOperationFicheXlsx).not.toHaveBeenCalled();
    expect(printSpy).not.toHaveBeenCalled();
    printSpy.mockRestore();
  });

  it('explique le refus quand l\'utilisateur n\'est pas référent du plan (403)', () => {
    const fixture = setup(operationWith([]));
    stubDialog({ format: 'xlsx', sections: {} });
    const service = TestBed.inject(EnjeuService) as any;
    service.downloadOperationFicheXlsx.mockReturnValueOnce(throwError(() => ({ status: 403 })));
    // Le vrai MatSnackBar monterait un overlay : on espionne l'instance du
    // composant (le jeton injecté n'est pas identifiable depuis le spec).
    const snackSpy = jest
      .spyOn((fixture.componentInstance as any).snackBar, 'open')
      .mockImplementation(() => ({} as any));

    fixture.componentInstance.openExportDialog();

    expect(snackSpy).toHaveBeenCalledWith(
      'plans.exports.noPermission', expect.anything(), expect.anything(),
    );
    expect(fixture.componentInstance.isExporting()).toBe(false);
  });
});

describe('OperationFicheComponent — bouton retour vers la page d\'origine (#529, #531)', () => {
  it('retourne à la position de l\'action dans l\'architecture quand from=enjeux + fromEnjeu', () => {
    const router = { navigate: jest.fn() };
    const fixture = setup(operationWith([]), { from: 'enjeux', fromEnjeu: 'mon-enjeu', router });
    fixture.componentInstance.goBack();
    // #531 — op mock : id_operation = 42 → query param `expandOperation` que la
    // liste décode pour ouvrir le bon onglet, déplier l'OLT/OO et scroller.
    expect(router.navigate).toHaveBeenCalledWith(
      ['/plans', 'plan-x', 'enjeux', 'mon-enjeu'],
      { queryParams: { expandOperation: 42 } },
    );
  });

  it('retourne à la liste des enjeux quand from=enjeux sans fromEnjeu', () => {
    const router = { navigate: jest.fn() };
    const fixture = setup(operationWith([]), { from: 'enjeux', router });
    fixture.componentInstance.goBack();
    expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-x', 'enjeux']);
  });

  it('retourne au suivi des actions quand from=suivi', () => {
    const router = { navigate: jest.fn() };
    const fixture = setup(operationWith([]), { from: 'suivi', router });
    fixture.componentInstance.goBack();
    expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-x', 'suivi-actions']);
  });

  it('retourne au suivi des actions par défaut (aucun from)', () => {
    const router = { navigate: jest.fn() };
    const fixture = setup(operationWith([]), { router });
    fixture.componentInstance.goBack();
    expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-x', 'suivi-actions']);
  });
});

describe('OperationFicheComponent — bouton « Voir dans le plan de gestion » (#531)', () => {
  function operationWithEnjeu(enjeuSlug: string | null): Operation {
    return {
      id_operation: 42, libelle: 'Action test', enjeu_slug: enjeuSlug,
      metriques: [], operation_annees: [], finances: [],
    } as unknown as Operation;
  }

  it('navigue vers l\'enjeu parent avec expandOperation, quelle que soit l\'origine', () => {
    const router = { navigate: jest.fn() };
    // Ouverte depuis le suivi (from=suivi) : le bouton doit tout de même mener à l'architecture.
    const fixture = setup(operationWithEnjeu('mon-enjeu'), { from: 'suivi', router });
    fixture.componentInstance.goToArchitecture();
    expect(router.navigate).toHaveBeenCalledWith(
      ['/plans', 'plan-x', 'enjeux', 'mon-enjeu'],
      { queryParams: { expandOperation: 42 } },
    );
  });

  it('ne navigue pas si l\'enjeu parent est inconnu', () => {
    const router = { navigate: jest.fn() };
    const fixture = setup(operationWithEnjeu(null), { router });
    fixture.componentInstance.goToArchitecture();
    expect(router.navigate).not.toHaveBeenCalled();
  });
});
