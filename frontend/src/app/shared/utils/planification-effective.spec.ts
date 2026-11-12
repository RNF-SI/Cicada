import { operationAjustee, ranger } from './planification-effective';
import { yearBudgetPrev, yearBudgetReal } from './operation-budget';
import { getActionStatusForYear } from '../../features/plans/suivis/action-status.util';
import { Operation } from '../../core/models/enjeu.model';
import { AjustementDuPlan } from '../../core/models/planification-annuelle.model';

/** #794 — le suivi lit la programmation ajustée, le réalisé reste celui saisi. */
const op = {
  id_operation: 1, ventilation_mode: 'by_org', declinaison_par_type_cout: false,
  cout_salarial_auto: true, declinaison_par_poste: false,
  operation_annees: [
    {
      annee: 2026, periodicite: true, periodicite_mensuelle: { '5': true },
      organismes: [
        { id_organisme: 10, budget_fonctionnement: '1000.00',
          realisation: { budget_fonctionnement_realise: '400.00' } },
        { id_organisme: 11, budget_fonctionnement: '500.00',
          realisation: { budget_fonctionnement_realise: '200.00' } },
      ],
      rh_lignes: [],
      realisation: { id_niveau_realisation: 1, niveau_realisation_mnemonique: 'PARTIEL' },
    },
    { annee: 2027, periodicite: true, periodicite_mensuelle: { '6': true }, organismes: [], rh_lignes: [] },
  ],
} as unknown as Operation;

function ajustement(partiel: Partial<AjustementDuPlan>): AjustementDuPlan {
  return {
    id_operation: 1, annee: 2026, statut: 'planifiee', revue: true,
    periodicite_mensuelle: {}, organismes: [], rh_lignes: [], financeurs: [], ...partiel,
  } as AjustementDuPlan;
}

describe('Programmation effective (#794)', () => {
  it('sans ajustement, l\'action est rendue telle quelle', () => {
    expect(operationAjustee(op, ranger([]))).toBe(op);
  });

  it('prévu et mois ajustés, réalisé par organisme conservé', () => {
    const ajustee = operationAjustee(op, ranger([ajustement({
      periodicite_mensuelle: { '9': true },
      organismes: [{ id_organisme: 10, budget_fonctionnement: '1200.00' }],
    })]));
    const oa = ajustee.operation_annees!.find(a => a.annee === 2026)!;
    expect(oa.periodicite_mensuelle).toEqual({ '9': true });
    expect(yearBudgetPrev(ajustee, oa).total).toBe(1200);
    // L'organisme 11, retiré pour l'année, garde son réalisé (sans prévu).
    expect(yearBudgetReal(ajustee, oa).total).toBe(600);
    // L'action d'origine n'est pas touchée.
    expect(yearBudgetPrev(op, op.operation_annees![0]).total).toBe(1500);
  });

  it('une année reportée n\'est plus prévue : le réalisé devient « non prévu »', () => {
    const ajustee = operationAjustee(op, ranger([ajustement({ statut: 'reportee', annee_report: 2027 })]));
    const oa = ajustee.operation_annees!.find(a => a.annee === 2026)!;
    expect(oa.periodicite).toBe(false);
    expect(yearBudgetPrev(ajustee, oa).total ?? 0).toBe(0);
    expect(getActionStatusForYear(ajustee, 2026)).not.toBe(getActionStatusForYear(op, 2026));
  });

  it('une année planifiée hors du plan de gestion s\'ajoute', () => {
    const ajustee = operationAjustee(op, ranger([ajustement({
      annee: 2028, organismes: [{ id_organisme: 10, budget_fonctionnement: '300.00' }],
    })]));
    expect(ajustee.operation_annees!.map(a => a.annee)).toEqual([2026, 2027, 2028]);
    expect(getActionStatusForYear(ajustee, 2028)).toBe('planned');
  });
});
