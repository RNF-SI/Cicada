/**
 * #794 — Disposition du formulaire d'ajustement d'une année, selon les réglages
 * de l'action (mode de ventilation, détail des coûts, coût salarial, temps par
 * poste). Mêmes règles que la fiche action : `shared/utils/operation-budget.ts`.
 */
import {
  hasTypeBudget, rhModeFor, salaryIsComputed, yearBudgetPrev,
} from '../../../../shared/utils/operation-budget';
import { Operation, OperationAnnee } from '../../../../core/models/enjeu.model';
import {
  ChoixAjustement, ContenuAnnuel, ReglagesAction, RhAjuste,
} from '../../../../core/models/planification-annuelle.model';

export type ChampCout =
  | 'budget' | 'budget_fonctionnement' | 'budget_investissement'
  | 'cout_salarial' | 'cout_salarial_invest' | 'cout_stage' | 'cout_prestataire'
  | 'autre_cout' | 'cout_prestataire_invest' | 'autre_cout_invest';

/** Une ligne du tableau budgétaire. */
export interface LigneBudget {
  champ: ChampCout;
  /** Clé i18n sous `plans.suivis.planificationAnnuelle.ajustement.budget.` */
  libelle: string;
  invest: boolean;
  /** Coût salarial calculé (jours × coût jour) : affiché, pas saisi. */
  calcule: boolean;
  commentaire?: 'autre_cout_commentaire' | 'autre_cout_invest_commentaire';
}

export interface DispositionAjustement {
  /** Montants saisis par organisme (sinon sur l'année). */
  parOrganisme: boolean;
  /** Fonctionnement / investissement distingués. */
  typeBudget: boolean;
  /** Coûts détaillés (salarial, stage, prestataire, autres). */
  detail: boolean;
  salaireCalcule: boolean;
  /** Lignes du temps de travail : par poste, par organisme, ou un total. */
  rhMode: 'postes' | 'organismes' | 'global';
  /** Catégorie de dépense du temps (fonctionnement / investissement / bénévolat). */
  categorieTemps: boolean;
  lignes: LigneBudget[];
}

const ORG_MODES = ['by_org', 'by_org_type', 'by_org_type_poste'];

export function dispositionAjustement(reglages: ReglagesAction): DispositionAjustement {
  const mode = reglages.ventilation_mode || 'none';
  const parOrganisme = ORG_MODES.includes(mode);
  const typeBudget = hasTypeBudget(mode);
  const detail = reglages.declinaison_par_type_cout;
  const rhMode = rhModeFor(mode, reglages.declinaison_par_poste);
  const salaireCalcule = salaryIsComputed(detail, rhMode === 'postes', reglages.cout_salarial_auto);
  const lignes: LigneBudget[] = [];
  if (detail) {
    lignes.push(
      { champ: 'cout_salarial', libelle: 'salarial', invest: false, calcule: salaireCalcule },
      { champ: 'cout_stage', libelle: 'stage', invest: false, calcule: false },
      { champ: 'cout_prestataire', libelle: 'prestataire', invest: false, calcule: false },
      { champ: 'autre_cout', libelle: 'autres', invest: false, calcule: false,
        commentaire: 'autre_cout_commentaire' },
    );
    if (typeBudget) {
      lignes.push(
        { champ: 'cout_salarial_invest', libelle: 'salarial', invest: true, calcule: salaireCalcule },
        { champ: 'cout_prestataire_invest', libelle: 'prestataire', invest: true, calcule: false },
        { champ: 'autre_cout_invest', libelle: 'autres', invest: true, calcule: false,
          commentaire: 'autre_cout_invest_commentaire' },
      );
    }
  } else if (typeBudget) {
    lignes.push(
      { champ: 'budget_fonctionnement', libelle: 'fonctionnement', invest: false, calcule: false },
      { champ: 'budget_investissement', libelle: 'investissement', invest: true, calcule: false },
    );
  } else {
    lignes.push({
      champ: parOrganisme ? 'budget_fonctionnement' : 'budget', libelle: 'total',
      invest: false, calcule: false,
    });
  }
  return {
    parOrganisme, typeBudget, detail, salaireCalcule, rhMode,
    categorieTemps: typeBudget, lignes,
  };
}

function nombre(valeur: string | number | null | undefined): number {
  const n = Number(valeur ?? 0);
  return Number.isFinite(n) ? n : 0;
}

/** Organisme auquel se rattache une ligne de temps (celui du poste s'il y en a un). */
export function organismeDeLaLigne(ligne: RhAjuste, choix: ChoixAjustement): number | null {
  if (ligne.id_poste != null) {
    return choix.postes.find(p => p.id_poste === ligne.id_poste)?.id_organisme ?? null;
  }
  return ligne.id_organisme ?? null;
}

/** Coût salarial calculé (Σ jours × coût jour) d'une catégorie, pour un
 *  organisme ou pour toute l'année (`organisme` non fourni). */
export function salaireCalcule(
  contenu: ContenuAnnuel, choix: ChoixAjustement, invest: boolean, organisme?: number,
): number {
  const categorie = invest ? 'investissement' : 'fonctionnement';
  return (contenu.rh_lignes ?? []).reduce((total, ligne) => {
    if ((ligne.categorie_depense || 'fonctionnement') !== categorie) return total;
    if (organisme !== undefined && organismeDeLaLigne(ligne, choix) !== organisme) return total;
    const poste = choix.postes.find(p => p.id_poste === ligne.id_poste);
    return total + nombre(ligne.jours) * nombre(poste?.cout_jour);
  }, 0);
}

/** L'année sous la forme qu'attend `yearBudgetPrev()` (coût jour des postes compris). */
function commeAnneeDAction(contenu: ContenuAnnuel, choix: ChoixAjustement): OperationAnnee {
  return {
    ...contenu,
    organismes: contenu.organismes ?? [],
    rh_lignes: (contenu.rh_lignes ?? []).map(l => ({
      ...l,
      poste_cout_jour: choix.postes.find(p => p.id_poste === l.id_poste)?.cout_jour ?? null,
    })),
  } as unknown as OperationAnnee;
}

/** Totaux de l'année en cours de saisie, par les règles de la fiche action. */
export function totauxSaisis(
  contenu: ContenuAnnuel, choix: ChoixAjustement, reglages: ReglagesAction,
): { budget: number; jours: number } {
  if (contenu.statut !== 'planifiee') return { budget: 0, jours: 0 };
  const op = reglages as unknown as Operation;
  const budget = yearBudgetPrev(op, commeAnneeDAction(contenu, choix)).total ?? 0;
  const jours = (contenu.rh_lignes ?? []).reduce((total, l) => total + nombre(l.jours), 0);
  return { budget, jours };
}
