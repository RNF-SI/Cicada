import {
  dispositionAjustement, reglagesDeLAnnee, salaireCalcule, totauxBudget, totauxSaisis,
} from './ajustement-layout';
import { ChoixAjustement, ReglagesAction } from '../../../../core/models/planification-annuelle.model';

/** #794 — le formulaire d'ajustement suit les réglages de l'action, comme la fiche. */
function reglages(partiel: Partial<ReglagesAction>): ReglagesAction {
  return {
    ventilation_mode: 'none', declinaison_par_poste: false, declinaison_par_type_cout: false,
    cout_salarial_auto: true, programmation_globale: false, temps_par_poste: false, ...partiel,
  };
}

const champs = (r: Partial<ReglagesAction>) => dispositionAjustement(reglages(r)).lignes.map(l => l.champ);

describe('Disposition du formulaire d\'ajustement (#794)', () => {
  it('aucune ventilation : un budget total, un temps total', () => {
    const d = dispositionAjustement(reglages({}));
    expect(champs({})).toEqual(['budget']);
    expect([d.parOrganisme, d.typeBudget, d.rhMode, d.categorieTemps]).toEqual([false, false, 'global', false]);
  });

  it('par organisme : un budget par organisme, le temps par organisme', () => {
    const d = dispositionAjustement(reglages({ ventilation_mode: 'by_org' }));
    expect(d.lignes.map(l => l.champ)).toEqual(['budget_fonctionnement']);
    expect([d.parOrganisme, d.rhMode]).toEqual([true, 'organismes']);
  });

  it('par type de budget : fonctionnement et investissement, catégorie du temps', () => {
    const d = dispositionAjustement(reglages({ ventilation_mode: 'by_type' }));
    expect(d.lignes.map(l => l.champ)).toEqual(['budget_fonctionnement', 'budget_investissement']);
    expect([d.parOrganisme, d.categorieTemps, d.rhMode]).toEqual([false, true, 'global']);
  });

  it('par organisme et type de budget', () => {
    expect(champs({ ventilation_mode: 'by_org_type' }))
      .toEqual(['budget_fonctionnement', 'budget_investissement']);
    expect(dispositionAjustement(reglages({ ventilation_mode: 'by_org_type' })).parOrganisme).toBe(true);
  });

  it('+ type de poste : coûts détaillés, temps par poste, salarial calculé', () => {
    const d = dispositionAjustement(reglages({
      ventilation_mode: 'by_type_poste', declinaison_par_type_cout: true }));
    expect(d.lignes.map(l => l.champ)).toEqual([
      'cout_salarial', 'cout_stage', 'cout_prestataire', 'autre_cout',
      'cout_salarial_invest', 'cout_prestataire_invest', 'autre_cout_invest']);
    expect([d.rhMode, d.salaireCalcule]).toEqual(['postes', true]);
    expect(d.lignes.filter(l => l.calcule).map(l => l.champ)).toEqual(['cout_salarial', 'cout_salarial_invest']);
  });

  it('ventilation maximale à coût salarial saisi', () => {
    const d = dispositionAjustement(reglages({
      ventilation_mode: 'by_org_type_poste', declinaison_par_type_cout: true, cout_salarial_auto: false }));
    expect([d.parOrganisme, d.salaireCalcule]).toEqual([true, false]);
    expect(d.lignes.some(l => l.calcule)).toBe(false);
  });

  it('coûts détaillés sans type de budget : pas d\'investissement (#735)', () => {
    expect(champs({ declinaison_par_type_cout: true }))
      .toEqual(['cout_salarial', 'cout_stage', 'cout_prestataire', 'autre_cout']);
  });
});

describe('Totaux de la saisie (#794)', () => {
  const choix: ChoixAjustement = {
    organismes: [{ id_organisme: 1, nom: 'RNF' }],
    postes: [{ id_poste: 7, libelle: 'Garde', id_organisme: 1, cout_jour: '250.00', finance_par_defaut: true }],
    financeurs: [],
  };

  it('aucune ventilation : le budget saisi et le temps total', () => {
    const t = totauxSaisis(
      { statut: 'planifiee', budget: '1500', rh_lignes: [{ jours: '5' }] }, choix, reglages({}));
    expect(t).toEqual({ budget: 1500, jours: 5 });
  });

  it('coût salarial calculé : jours × coût jour, par organisme', () => {
    const contenu = {
      statut: 'planifiee' as const,
      organismes: [{ id_organisme: 1, cout_stage: '400' }],
      rh_lignes: [{ id_poste: 7, jours: '4', categorie_depense: 'fonctionnement' as const }],
    };
    const r = reglages({ ventilation_mode: 'by_org_type_poste', declinaison_par_type_cout: true });
    expect(salaireCalcule(contenu, choix, false, 1)).toBe(1000);
    expect(totauxSaisis(contenu, choix, r)).toEqual({ budget: 1400, jours: 4 });
  });

  it('une année non prévue ne pèse rien', () => {
    expect(totauxSaisis({ statut: 'non_prevue', budget: '900' }, choix, reglages({})))
      .toEqual({ budget: 0, jours: 0 });
  });
});

describe('Réglages propres à l\'année (#794, retour 13/11)', () => {
  const choix: ChoixAjustement = {
    organismes: [{ id_organisme: 1, nom: 'RNF' }, { id_organisme: 2, nom: 'OFB' }],
    postes: [{ id_poste: 7, libelle: 'Garde', id_organisme: 1, cout_jour: '250.00', finance_par_defaut: true }],
    financeurs: [],
  };

  it('l\'année ajoute une déclinaison que la fiche action n\'a pas', () => {
    const r = reglagesDeLAnnee(reglages({}), { statut: 'planifiee', declinaison_par_type_cout: true,
      declinaison_par_poste: true });
    expect([r.declinaison_par_type_cout, r.declinaison_par_poste, r.temps_par_poste]).toEqual([true, true, true]);
    expect(dispositionAjustement(r).rhMode).toBe('postes');
    expect(dispositionAjustement(r).lignes.map(l => l.champ)).toContain('cout_stage');
  });

  it('les déclinaisons de la fiche action s\'imposent, pas le coût salarial calculé', () => {
    const action = reglages({ ventilation_mode: 'by_org_type_poste', declinaison_par_type_cout: true,
      temps_par_poste: true });
    const r = reglagesDeLAnnee(action, { statut: 'planifiee', declinaison_par_type_cout: false,
      declinaison_par_poste: false, cout_salarial_auto: false });
    expect([r.declinaison_par_type_cout, r.temps_par_poste, r.cout_salarial_auto]).toEqual([true, true, false]);
    expect(dispositionAjustement(r).salaireCalcule).toBe(false);
  });

  it('coût salarial saisi pour l\'année : il remplace le calcul', () => {
    const contenu = {
      statut: 'planifiee' as const, cout_salarial_auto: false,
      organismes: [{ id_organisme: 1, cout_stage: '400', cout_salarial: '2000' }],
      rh_lignes: [{ id_poste: 7, jours: '4', categorie_depense: 'fonctionnement' as const }],
    };
    const action = reglages({ ventilation_mode: 'by_org_type_poste', declinaison_par_type_cout: true,
      temps_par_poste: true });
    expect(totauxSaisis(contenu, choix, reglagesDeLAnnee(action, contenu)).budget).toBe(2400);
  });

  it('totaux du budget par organisme et pour l\'année', () => {
    const contenu = {
      statut: 'planifiee' as const,
      organismes: [
        { id_organisme: 1, cout_stage: '400', cout_prestataire_invest: '300' },
        { id_organisme: 2, autre_cout: '100' },
      ],
      rh_lignes: [{ id_poste: 7, jours: '4', categorie_depense: 'fonctionnement' as const }],
    };
    const r = reglages({ ventilation_mode: 'by_org_type_poste', declinaison_par_type_cout: true,
      temps_par_poste: true });
    expect(totauxBudget(contenu, choix, r, 1)).toEqual({ fonctionnement: 1400, investissement: 300, total: 1700 });
    expect(totauxBudget(contenu, choix, r, 2)).toEqual({ fonctionnement: 100, investissement: 0, total: 100 });
    expect(totauxBudget(contenu, choix, r)).toEqual({ fonctionnement: 1500, investissement: 300, total: 1800 });
  });
});
