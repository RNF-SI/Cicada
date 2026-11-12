/**
 * Planification annuelle ajustée (#794) — miroir de l'API
 * `/api/plans/planification-annuelle/`.
 *
 * Les montants arrivent en chaînes JSON (décimaux DRF) : `Number()` avant tout
 * calcul.
 */

export type StatutAnnuel = 'planifiee' | 'non_prevue' | 'reportee';

/** Totaux d'une année (plan de gestion ou ajusté), calculés par le serveur
 *  avec les règles des exports. */
export interface ResumeAnnuel {
  statut: StatutAnnuel;
  annee_report: number | null;
  report_de: number | null;
  mois: number[];
  budget: string;
  budget_fonctionnement: string;
  budget_investissement: string;
  /** Jours, bénévolat compris. */
  jours: string;
  jours_benevole: string;
  /** Somme des montants annuels par financeur. */
  financeurs: string;
}

export interface ReportEntrant {
  /** Année d'origine du report. */
  annee: number;
  partiel: boolean;
}

export interface RealiseAnnuel {
  saisi: boolean;
  /** Mnémonique NIVEAU_REALISATION. */
  niveau: string | null;
}

export interface LigneTableauAnnuel {
  id_operation: number;
  code: string;
  libelle: string;
  programmation_globale: boolean;
  pg: ResumeAnnuel;
  /** #735 — programmation globale : montants sur la période. */
  pg_global: ResumeAnnuel | null;
  /** Prévu effectif : l'ajustement, sinon le plan de gestion. */
  ajuste: ResumeAnnuel;
  ajustee: boolean;
  diverge: boolean;
  revue: boolean;
  date_revue: string | null;
  reports_entrants: ReportEntrant[];
  realise: RealiseAnnuel;
}

export interface TableauAnnuel {
  id_pg: number;
  annee: number;
  annees: number[];
  revues: number;
  total: number;
  peut_saisir: boolean;
  actions: LigneTableauAnnuel[];
}

export interface OrganismeAjuste {
  id_organisme: number;
  budget_fonctionnement?: string | null;
  budget_investissement?: string | null;
  cout_salarial?: string | null;
  cout_salarial_invest?: string | null;
  cout_stage?: string | null;
  cout_prestataire?: string | null;
  autre_cout?: string | null;
  autre_cout_commentaire?: string;
  cout_prestataire_invest?: string | null;
  autre_cout_invest?: string | null;
  autre_cout_invest_commentaire?: string;
  etp?: string | null;
}

export interface RhAjuste {
  id_poste?: number | null;
  id_organisme?: number | null;
  jours?: string | null;
  finance?: boolean;
  categorie_depense?: '' | 'fonctionnement' | 'investissement' | 'benevolat_partenariat';
}

export interface FinanceurAjuste {
  id_financeur: number;
  montant?: string | null;
}

/** Programmation d'une année : même forme que l'année d'une action. */
export interface ContenuAnnuel extends Omit<OrganismeAjuste, 'id_organisme'> {
  statut: StatutAnnuel;
  annee_report?: number | null;
  report_de?: number | null;
  budget?: string | null;
  periodicite_mensuelle?: Record<string, boolean>;
  commentaire?: string;
  organismes?: OrganismeAjuste[];
  rh_lignes?: RhAjuste[];
  financeurs?: FinanceurAjuste[];
}

export interface AjustementLu extends ContenuAnnuel {
  id_ajustement_annuel: number;
  date_revue: string | null;
  revue_par: string | null;
  date_maj: string;
}

export interface FinanceurPg {
  id_financeur: number | null;
  nom: string;
  /** Montant global sur l'action (#790). */
  montant: string | null;
}

export interface ReglagesAction {
  ventilation_mode: string;
  declinaison_par_poste: boolean;
  declinaison_par_type_cout: boolean;
  cout_salarial_auto: boolean;
  programmation_globale: boolean;
  temps_par_poste: boolean;
}

export interface DetailAnnuel {
  id_operation: number;
  code: string;
  libelle: string;
  annee: number;
  annees: number[];
  reglages: ReglagesAction;
  pg: ContenuAnnuel;
  pg_resume: ResumeAnnuel;
  pg_global: ContenuAnnuel | null;
  pg_global_resume: ResumeAnnuel | null;
  financeurs_pg: FinanceurPg[];
  ajustement: AjustementLu | null;
  effectif: ContenuAnnuel;
  effectif_resume: ResumeAnnuel;
  diverge: boolean;
  reports_entrants: ReportEntrant[];
  realise: RealiseAnnuel;
  /** Du réalisé est saisi : l'année ne se déplace pas lors d'un report. */
  fixe: boolean;
  peut_saisir: boolean;
}

export interface ReportDemande {
  annee_report: number;
  partiel?: boolean;
  apercu?: boolean;
}

export interface LigneApercuReport {
  annee: number;
  avant: ResumeAnnuel;
  apres: ResumeAnnuel;
  fixe: boolean;
  modifiee: boolean;
}

export interface ApercuReport {
  annee: number;
  annee_report: number;
  partiel: boolean;
  applique: boolean;
  annees: LigneApercuReport[];
  deplacements: { de: number; vers: number }[];
  abandonnees: { annee: number; resume: ResumeAnnuel }[];
}
