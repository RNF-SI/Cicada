/**
 * #613/#616 — dérivation du budget et du temps de travail d'une année, quel
 * que soit le mode de ventilation.
 *
 * Les décimaux arrivent en chaînes DRF (« 500.00 ») : les cas de test les
 * reproduisent tels quels.
 */
import {
  fonctDetailPrev, investDetailPrev, fonctDetailReal, investDetailReal,
  salarialCost, sumJours, yearBudgetPrev, yearBudgetReal,
  yearJoursPrev, yearJoursReal, yearJoursAgentsPrev, yearJoursAgentsReal,
  salaryOptionAvailable, salaryIsComputed, salaryIsComputedReal, prevAnnees, tempsParPoste, rhModeFor,
} from './operation-budget';

const OP = (mode: string) => ({ ventilation_mode: mode }) as any;

/** Année en ventilation maximale : détail des coûts porté par l'organisme. */
function anneeOrgPoste(): any {
  return {
    annee: 2027, periodicite: true, budget: null, etp: null,
    budget_fonctionnement: null, budget_investissement: null,
    periodicite_mensuelle: {},
    organismes: [{
      id_organisme: 100, budget_fonctionnement: null, budget_investissement: null,
      cout_stage: '200.00', cout_prestataire: '1000.00', autre_cout: '500.00',
      cout_prestataire_invest: '300.00', autre_cout_invest: '50.00', etp: null,
    }],
    rh_lignes: [
      { id_poste: 1, jours: '10.00', finance: true, categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' },
      { id_poste: 2, jours: '5.00', finance: true, categorie_depense: 'investissement', poste_cout_jour: '80.00' },
      { id_poste: 3, jours: '2.00', finance: false, categorie_depense: 'benevolat_partenariat', poste_cout_jour: '150.00' },
    ],
  };
}

/** Même action, mais détail des coûts porté par l'ANNÉE (#624). */
function anneeTypePoste(): any {
  const oa = anneeOrgPoste();
  const org = oa.organismes[0];
  return {
    ...oa,
    organismes: [],
    cout_stage: org.cout_stage, cout_prestataire: org.cout_prestataire,
    autre_cout: org.autre_cout, cout_prestataire_invest: org.cout_prestataire_invest,
    autre_cout_invest: org.autre_cout_invest,
  };
}

describe('salarialCost / sumJours', () => {
  it('valorise les jours au coût jour du poste, par catégorie', () => {
    const lignes = anneeOrgPoste().rh_lignes;
    expect(salarialCost(lignes, 'fonctionnement')).toBe(3000);
    expect(salarialCost(lignes, 'investissement')).toBe(400);
  });

  it('ne valorise pas le bénévolat en euros, mais le compte en jours', () => {
    const lignes = anneeOrgPoste().rh_lignes;
    // 2 j × 150 € ne pèsent ni en fonctionnement ni en investissement.
    expect(salarialCost(lignes, 'fonctionnement') + salarialCost(lignes, 'investissement'))
      .toBe(3400);
    expect(sumJours(lignes)).toBe(17);
  });
});

describe('yearBudgetPrev (#613)', () => {
  it('mode none : total direct, sans ventilation', () => {
    const oa: any = { annee: 2027, budget: '1500.00', rh_lignes: [] };
    expect(yearBudgetPrev(OP('none'), oa)).toEqual({
      fonctionnement: null, investissement: null, total: 1500,
    });
  });

  it('mode by_type : enveloppes saisies', () => {
    const oa: any = {
      annee: 2027, budget_fonctionnement: '10000.00', budget_investissement: '9000.00',
      rh_lignes: [],
    };
    expect(yearBudgetPrev(OP('by_type'), oa)).toEqual({
      fonctionnement: 10000, investissement: 9000, total: 19000,
    });
  });

  // Le cœur de #613 : ces modes ne stockent pas d'enveloppe, l'ancienne
  // lecture de `budget_fonctionnement` renvoyait 0 € alors que des coûts
  // étaient saisis.
  it('mode by_org_type_poste : somme salarial + stage + prestataire + autres', () => {
    const split = yearBudgetPrev(OP('by_org_type_poste'), anneeOrgPoste());
    expect(split.fonctionnement).toBe(4700);  // 3000 + 200 + 1000 + 500
    expect(split.investissement).toBe(750);   // 400 + 300 + 50
    expect(split.total).toBe(5450);
  });

  it('mode by_type_poste : même total, détail porté par l’année (#624)', () => {
    expect(yearBudgetPrev(OP('by_type_poste'), anneeTypePoste()))
      .toEqual(yearBudgetPrev(OP('by_org_type_poste'), anneeOrgPoste()));
  });

  // #600 (retour 08/2026) — les deux réglages du tableau de programmation.
  it('déclinaison par type de coût décochée : seules les enveloppes comptent', () => {
    const oa = anneeOrgPoste();
    oa.organismes[0].budget_fonctionnement = '4000.00';
    oa.organismes[0].budget_investissement = '1000.00';
    oa.organismes[0].cout_stage = null;
    oa.organismes[0].cout_prestataire = null;
    oa.organismes[0].autre_cout = null;
    oa.organismes[0].cout_prestataire_invest = null;
    oa.organismes[0].autre_cout_invest = null;
    const op = { ventilation_mode: 'by_org_type', declinaison_par_type_cout: false } as any;
    // Le coût salarial des lignes RH n'est PAS ajouté : l'enveloppe l'inclut.
    expect(yearBudgetPrev(op, oa)).toEqual({
      fonctionnement: 4000, investissement: 1000, total: 5000,
    });
  });

  it('coût salarial saisi manuellement : c’est le montant saisi qui compte', () => {
    const oa = anneeOrgPoste();
    oa.organismes[0].cout_salarial = '1800.00';
    oa.organismes[0].cout_salarial_invest = '450.00';
    const op = {
      ventilation_mode: 'by_org_type_poste', cout_salarial_auto: false,
    } as any;
    const f = fonctDetailPrev(op, oa);
    expect(f.salarial).toBe(1800);            // et non 10 j × 300 €
    expect(f.total).toBe(3500);               // 1800 + 200 + 1000 + 500
    const i = investDetailPrev(op, oa);
    expect(i.salarial).toBe(450);
    expect(i.total).toBe(800);                // 450 + 300 + 50
  });

  it('expose le détail des composants pour la fiche action', () => {
    const f = fonctDetailPrev(OP('by_org_type_poste'), anneeOrgPoste());
    expect(f).toEqual({ salarial: 3000, stage: 200, prestataire: 1000, autres: 500, total: 4700 });
    const i = investDetailPrev(OP('by_org_type_poste'), anneeOrgPoste());
    expect(i).toEqual({ salarial: 400, stage: 0, prestataire: 300, autres: 50, total: 750 });
  });

  it('année non programmée : aucune valeur (affichée « — »)', () => {
    const oa: any = { annee: 2030, budget: null, organismes: [], rh_lignes: [] };
    expect(yearBudgetPrev(OP('by_org_type_poste'), oa)).toEqual({
      fonctionnement: null, investissement: null, total: null,
    });
  });

  it('mode by_org : le budget total de l’organisme reste compté', () => {
    const oa: any = {
      annee: 2027, organismes: [{ id_organisme: 1, budget_fonctionnement: '800.00', budget_investissement: null }],
      rh_lignes: [],
    };
    expect(yearBudgetPrev(OP('by_org'), oa).total).toBe(800);
  });
});

describe('yearBudgetReal (#616)', () => {
  it('agrège le détail des coûts réalisés + le salarial réalisé', () => {
    const oa: any = {
      annee: 2027,
      organismes: [{
        id_organisme: 100,
        realisation: {
          cout_stage_realise: '150.00', cout_prestataire_realise: '800.00',
          autre_cout_realise: '50.00', cout_prestataire_invest_realise: '100.00',
        },
      }],
      realisation: {
        rh_lignes: [
          { id_poste: 1, jours: '8.00', finance: true, categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' },
        ],
      },
    };
    const split = yearBudgetReal(OP('by_org_type_poste'), oa);
    expect(fonctDetailReal(OP('by_org_type_poste'), oa).salarial).toBe(2400);
    expect(split.fonctionnement).toBe(3400);   // 2400 + 150 + 800 + 50
    expect(split.investissement).toBe(100);
    expect(split.total).toBe(3500);
    expect(split.hasValue).toBe(true);
  });

  it('#722 — coût salarial saisi : le salarial RÉALISÉ est le montant saisi', () => {
    const op = { ventilation_mode: 'by_org_type_poste', cout_salarial_auto: false } as any;
    const oa: any = {
      annee: 2027,
      organismes: [{
        id_organisme: 100,
        realisation: {
          cout_salarial_realise: '1500.00', cout_salarial_invest_realise: '300.00',
          cout_prestataire_realise: '800.00',
        },
      }],
      realisation: {
        rh_lignes: [
          { id_poste: 1, jours: '8.00', finance: true, categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' },
        ],
      },
    };
    expect(fonctDetailReal(op, oa).salarial).toBe(1500);   // et non 8 j × 300 €
    expect(investDetailReal(op, oa).salarial).toBe(300);
    expect(yearBudgetReal(op, oa).total).toBe(2600);       // 1500 + 800 + 300
  });

  it('#722 — coût salarial saisi sur l’année (sans organisme) : compté seul', () => {
    const op = { ventilation_mode: 'by_type_poste', cout_salarial_auto: false } as any;
    const oa: any = { annee: 2027, organismes: [], realisation: { cout_salarial_realise: '1200.00' } };
    const split = yearBudgetReal(op, oa);
    expect(split.hasValue).toBe(true);
    expect(split.total).toBe(1200);
  });

  it('distingue « aucun suivi » de « suivi à 0 € »', () => {
    const vide: any = { annee: 2027, organismes: [], realisation: null };
    expect(yearBudgetReal(OP('by_type_poste'), vide).hasValue).toBe(false);

    const zero: any = {
      annee: 2027, organismes: [],
      realisation: { cout_prestataire_realise: '0.00', rh_lignes: [] },
    };
    const split = yearBudgetReal(OP('by_type_poste'), zero);
    expect(split.hasValue).toBe(true);
    expect(split.total).toBe(0);
  });

  it('mode none : budget réalisé direct', () => {
    const oa: any = { annee: 2027, realisation: { budget_realise: '950.00' } };
    expect(yearBudgetReal(OP('none'), oa).total).toBe(950);
  });
});

describe('jours prévus / réalisés (#616)', () => {
  it('somme les lignes RH plutôt que le champ etp déprécié', () => {
    expect(yearJoursPrev(anneeOrgPoste())).toBe(17);
  });

  it('ne retombe sur etp que si l’appelant le demande', () => {
    const oa: any = { annee: 2027, etp: '4.50', rh_lignes: [] };
    // Fiche action : le champ `etp` est explicitement ignoré (#560).
    expect(yearJoursPrev(oa)).toBeNull();
    // Vues de suivi : repli pour les données antérieures à #560.
    expect(yearJoursPrev(oa, true)).toBe(4.5);
    expect(yearJoursPrev({ annee: 2027, etp: null, rh_lignes: [] } as any, true)).toBeNull();
  });

  it('jours réalisés : lignes RH réalisées, puis replis historiques', () => {
    const oa: any = {
      annee: 2027, organismes: [],
      realisation: { rh_lignes: [{ jours: '8.00', finance: true }, { jours: '2.00', finance: false }] },
    };
    expect(yearJoursReal(oa)).toBe(10);

    const parOrg: any = {
      annee: 2027,
      organismes: [{ id_organisme: 1, realisation: { etp_realise: '3.00' } }],
      realisation: { rh_lignes: [] },
    };
    expect(yearJoursReal(parOrg)).toBe(3);

    const global: any = { annee: 2027, organismes: [], realisation: { etp_realise: '5.00' } };
    expect(yearJoursReal(global)).toBe(5);

    expect(yearJoursReal({ annee: 2027, organismes: [], realisation: null } as any)).toBeNull();
  });
});

describe('#775 — jours des agents seuls (synthèses du suivi)', () => {
  it('écarte le bénévolat / partenariat, prévu et réalisé', () => {
    const oa: any = {
      annee: 2027, organismes: [],
      rh_lignes: [{ jours: '10.00', finance: true }, { jours: '5.00', finance: false }],
      realisation: { rh_lignes: [{ jours: '8.00', finance: true }, { jours: '2.00', finance: false }] },
    };
    expect(yearJoursAgentsPrev(oa, true)).toBe(10);
    expect(yearJoursAgentsReal(oa)).toBe(8);
  });

  it('une année de bénévolat seul compte 0 j, sans repli sur etp', () => {
    const oa: any = {
      annee: 2027, etp: '4.00', organismes: [],
      rh_lignes: [{ jours: '5.00', finance: false }],
      realisation: { etp_realise: '3.00', rh_lignes: [{ jours: '2.00', finance: false }] },
    };
    expect(yearJoursAgentsPrev(oa, true)).toBe(0);
    expect(yearJoursAgentsReal(oa)).toBe(0);
  });

  it('garde les replis historiques sans lignes RH', () => {
    const oa: any = { annee: 2027, etp: '4.00', rh_lignes: [], organismes: [],
      realisation: { etp_realise: '3.00', rh_lignes: [] } };
    expect(yearJoursAgentsPrev(oa, true)).toBe(4);
    expect(yearJoursAgentsReal(oa)).toBe(3);
  });
});

// ===========================================================================
// #600 (retour 08/2026) — le coût salarial ne se CALCULE que par type de poste
// ===========================================================================

describe('coût salarial : calculé ou saisi', () => {
  it('ne propose l\'option que pour des coûts détaillés ET un temps par poste', () => {
    expect(salaryOptionAvailable(true, true)).toBe(true);
    // Sans poste, aucun coût jour à multiplier : le coût salarial se saisit.
    expect(salaryOptionAvailable(true, false)).toBe(false);
    // Sans détail des coûts, il n'y a même pas de ligne « coût salarial ».
    expect(salaryOptionAvailable(false, true)).toBe(false);
  });

  it('suit le choix du gestionnaire quand le temps est décliné par poste', () => {
    expect(salaryIsComputed(true, true, true)).toBe(true);
    expect(salaryIsComputed(true, true, false)).toBe(false);
  });

  it('coûts détaillés sans poste : toujours saisi', () => {
    expect(salaryIsComputed(true, false, true)).toBe(false);
  });

  it('laisse les actions sans détail des coûts en calcul (comportement historique)', () => {
    // L'enveloppe saisie contient déjà tout : le drapeau ne doit pas basculer
    // ces actions en « coût salarial saisi » côté serveur (totaux inchangés).
    expect(salaryIsComputed(false, false, true)).toBe(true);
    expect(salaryIsComputed(false, true, true)).toBe(true);
  });
});

describe('temps par poste : modes « + type de poste » ou case dédiée', () => {
  it('la déclinaison par type de coût ne l\'impose plus (retour 28/10)', () => {
    expect(tempsParPoste({ ventilation_mode: 'none', declinaison_par_type_cout: true } as any)).toBe(false);
    expect(tempsParPoste({ ventilation_mode: 'by_org', declinaison_par_type_cout: true } as any)).toBe(false);
    expect(tempsParPoste({ ventilation_mode: 'none', declinaison_par_poste: true } as any)).toBe(true);
    expect(tempsParPoste({ ventilation_mode: 'by_type_poste', declinaison_par_poste: false } as any)).toBe(true);
  });

  it('lignes du tableau de temps de travail', () => {
    expect(rhModeFor('none', true)).toBe('postes');
    expect(rhModeFor('by_org', true)).toBe('postes');
    expect(rhModeFor('none', false)).toBe('global');
    expect(rhModeFor('by_org', false)).toBe('organismes');
    expect(rhModeFor('by_org_type', false)).toBe('organismes');
    expect(rhModeFor('by_type_poste', false)).toBe('postes');
  });

  it('calcule le coût salarial en mode « aucune ventilation » (jours × coût jour)', () => {
    const op = {
      ventilation_mode: 'none', declinaison_par_type_cout: true, declinaison_par_poste: true,
      cout_salarial_auto: true,
    } as any;
    const oa: any = {
      annee: 2027, budget: null, organismes: [], cout_stage: '200.00',
      rh_lignes: [{ id_poste: 1, jours: '10.00', categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' }],
    };
    expect(fonctDetailPrev(op, oa).salarial).toBe(3000);
    // Pas de type de budget : rien côté investissement, un seul total.
    expect(yearBudgetPrev(op, oa)).toEqual({ fonctionnement: null, investissement: null, total: 3200 });
  });
});

describe('#735 — détail des coûts sans type de budget', () => {
  it('additionne les types de coût saisis en mode « aucune ventilation »', () => {
    const op = { ventilation_mode: 'none', declinaison_par_type_cout: true, cout_salarial_auto: false } as any;
    const oa: any = {
      annee: 2027, budget: '1700.00', cout_salarial: '1000.00', cout_stage: '200.00',
      cout_prestataire: '400.00', autre_cout: '100.00', organismes: [], rh_lignes: [],
    };
    expect(fonctDetailPrev(op, oa)).toEqual(
      { salarial: 1000, stage: 200, prestataire: 400, autres: 100, total: 1700 });
    expect(yearBudgetPrev(op, oa).total).toBe(1700);
  });

  it('additionne les types de coût de chaque organisme en mode « par organisme »', () => {
    const op = { ventilation_mode: 'by_org', declinaison_par_type_cout: true, cout_salarial_auto: false } as any;
    const oa: any = {
      annee: 2027, budget: null, organismes: [
        { id_organisme: 1, cout_salarial: '500.00', autre_cout: '50.00' },
        { id_organisme: 2, cout_prestataire: '300.00' },
      ], rh_lignes: [],
    };
    expect(yearBudgetPrev(op, oa).total).toBe(850);
  });
});

describe('#735 — programmation globale', () => {
  const annuelle: any = { annee: 2028, budget: null, organismes: [], rh_lignes: [] };
  const globale: any = { annee: null, budget: '20000.00', organismes: [], rh_lignes: [] };

  it('porte le prévu sur la seule ligne globale', () => {
    const op: any = { programmation_globale: true, operation_annees: [annuelle], operation_annee_globale: globale };
    expect(prevAnnees(op)).toEqual([globale]);
  });

  it('garde les années pour une action annuelle', () => {
    const op: any = { programmation_globale: false, operation_annees: [annuelle], operation_annee_globale: null };
    expect(prevAnnees(op)).toEqual([annuelle]);
  });
});

describe('#741 — réglages propres au suivi (réalisé)', () => {
  const anneeReal = (): any => ({
    annee: 2027, budget: null, organismes: [],
    rh_lignes: [{ id_poste: 1, jours: '10.00', categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' }],
    realisation: {
      cout_salarial_realise: '2000.00', cout_stage_realise: '500.00',
      rh_lignes: [{ id_poste: 1, jours: '8.00', categorie_depense: 'fonctionnement', poste_cout_jour: '300.00' }],
    },
  });

  it('coût salarial réalisé saisi alors que le prévu est calculé', () => {
    const op: any = {
      ventilation_mode: 'by_type_poste', declinaison_par_type_cout: true, cout_salarial_auto: true,
      declinaison_par_type_cout_realise: true, cout_salarial_auto_realise: false,
    };
    expect(fonctDetailPrev(op, anneeReal()).salarial).toBe(3000);
    expect(fonctDetailReal(op, anneeReal()).salarial).toBe(2000);
    expect(salaryIsComputedReal(op)).toBe(false);
  });

  it('réalisé détaillé alors que le prévu ne l\'est pas', () => {
    // #735 — hors mode « + type de poste », la migration 0134 fige ce réglage
    // en coût salarial saisi (il l'était implicitement jusque-là).
    const op: any = {
      ventilation_mode: 'by_type', declinaison_par_type_cout: false, cout_salarial_auto: true,
      declinaison_par_type_cout_realise: true, cout_salarial_auto_realise: false,
    };
    const oa = anneeReal();
    oa.rh_lignes = [];
    oa.realisation.rh_lignes = [];
    expect(yearBudgetReal(op, oa).total).toBe(2500);
  });

  it('sans réglage du suivi, reprend ceux de la programmation', () => {
    const op: any = { ventilation_mode: 'by_type_poste', declinaison_par_type_cout: true, cout_salarial_auto: true };
    expect(fonctDetailReal(op, anneeReal()).salarial).toBe(2400);
    expect(salaryIsComputedReal(op)).toBe(true);
  });
});
