/**
 * Catalogue des exports d'un plan de gestion, partagé par la page « Exports »
 * (#617) et le bouton « Générer » des pages du plan (#795).
 *
 * Un export est désigné par sa clé (`PlanExportKey`) : la page Exports les
 * range en groupes, chaque page du plan en propose quelques-uns dans son menu
 * « Générer ». Les droits sont ceux des endpoints `export-*` (référents du
 * plan et gestionnaires, `peut_exporter` du détail du plan).
 */
import { Observable } from 'rxjs';

import { AdminService } from '../../../core/services/admin.service';

/** Un export téléchargeable du plan. */
export interface PlanExportItem {
  /** Identifiant interne (clé de l'indicateur de chargement). */
  key: PlanExportKey;
  /** `data-testid` du bouton (stable pour les tests E2E). */
  testId: string;
  /** Classe d'icône Flaticon. */
  icon: string;
  labelKey: string;
  hintKey: string;
  request: (planId: number, annee: number) => Observable<Blob>;
  filename: (slug: string, annee: number) => string;
  /** #727 — export d'une année du plan, choisie à côté du bouton. */
  parAnnee?: boolean;
}

export type PlanExportKey =
  | 'docx'
  | 'presentation'
  | 'fiches'
  | 'fiches-docx'
  | 'budget-prev'
  | 'budget-suivi'
  | 'rh-prev'
  | 'rh-suivi'
  | 'fiches-suivi'
  | 'planification-annuelle'
  | 'arborescence'
  | 'actions';

/** Groupes de la page Exports, dans l'ordre d'affichage. */
export const PLAN_EXPORT_GROUPS: { titleKey: string; keys: PlanExportKey[] }[] = [
  {
    titleKey: 'plans.exports.groups.documents',
    keys: ['docx', 'presentation', 'fiches', 'fiches-docx'],
  },
  {
    titleKey: 'plans.exports.groups.finance',
    keys: ['budget-prev', 'budget-suivi', 'rh-prev', 'rh-suivi', 'fiches-suivi', 'planification-annuelle'],
  },
  {
    titleKey: 'plans.exports.groups.data',
    keys: ['arborescence', 'actions'],
  },
];

/** Les exports du plan, par clé. */
export function planExportCatalog(admin: AdminService): Record<PlanExportKey, PlanExportItem> {
  const items: PlanExportItem[] = [
    {
      key: 'docx',
      testId: 'plan-docx-export',
      icon: 'fi-rr-file-word',
      labelKey: 'plans.exports.docx',
      hintKey: 'plans.exports.docxHint',
      request: id => admin.downloadPlanDocx(id),
      filename: slug => `plan-de-gestion-${slug}.docx`,
    },
    {
      key: 'presentation',
      testId: 'arbo-export-presentation',
      icon: 'fi-rr-file-spreadsheet',
      labelKey: 'plans.exports.presentation',
      hintKey: 'plans.exports.presentationHint',
      request: id => admin.downloadArborescencePresentation(id),
      filename: slug => `arborescence-presentation-${slug}.xlsx`,
    },
    {
      key: 'fiches',
      testId: 'fiches-actions-export',
      icon: 'fi-rr-clipboard-list',
      labelKey: 'plans.exports.fichesActions',
      hintKey: 'plans.exports.fichesActionsHint',
      request: id => admin.downloadFichesActions(id),
      filename: slug => `fiches-actions-${slug}.xlsx`,
    },
    {
      key: 'fiches-docx',
      testId: 'fiches-actions-docx-export',
      icon: 'fi-rr-file-word',
      labelKey: 'plans.exports.fichesActionsDocx',
      hintKey: 'plans.exports.fichesActionsDocxHint',
      request: id => admin.downloadFichesActionsDocx(id),
      filename: slug => `fiches-actions-${slug}.docx`,
    },
    {
      key: 'budget-prev',
      testId: 'budget-prev-export',
      icon: 'fi-rr-coins',
      labelKey: 'plans.exports.budgetPrev',
      hintKey: 'plans.exports.budgetPrevHint',
      request: id => admin.downloadBudgetPrevisionnel(id),
      filename: slug => `budget-previsionnel-${slug}.xlsx`,
    },
    {
      key: 'budget-suivi',
      testId: 'budget-suivi-export',
      icon: 'fi-rr-coins',
      labelKey: 'plans.exports.budgetSuivi',
      hintKey: 'plans.exports.budgetSuiviHint',
      request: id => admin.downloadBudgetSuivi(id),
      filename: slug => `budget-suivi-${slug}.xlsx`,
    },
    {
      key: 'rh-prev',
      testId: 'rh-prev-export',
      icon: 'fi-rr-users',
      labelKey: 'plans.exports.rhPrev',
      hintKey: 'plans.exports.rhPrevHint',
      request: id => admin.downloadRhPrevisionnel(id),
      filename: slug => `rh-previsionnel-${slug}.xlsx`,
    },
    {
      key: 'rh-suivi',
      testId: 'rh-suivi-export',
      icon: 'fi-rr-users',
      labelKey: 'plans.exports.rhSuivi',
      hintKey: 'plans.exports.rhSuiviHint',
      request: id => admin.downloadRhSuivi(id),
      filename: slug => `rh-suivi-${slug}.xlsx`,
    },
    {
      // #727 — fiche de suivi de chaque action suivie l'année choisie.
      key: 'fiches-suivi',
      testId: 'fiches-suivi-export',
      icon: 'fi-rr-memo-circle-check',
      labelKey: 'plans.exports.fichesSuivi',
      hintKey: 'plans.exports.fichesSuiviHint',
      request: (id, annee) => admin.downloadFichesSuivi(id, annee),
      filename: (slug, annee) => `fiches-suivi-${slug}-${annee}.xlsx`,
      parAnnee: true,
    },
    {
      // #794 — planification annuelle ajustée de l'année choisie.
      key: 'planification-annuelle',
      testId: 'planification-annuelle-export',
      icon: 'fi-rr-calendar',
      labelKey: 'plans.exports.planificationAnnuelle',
      hintKey: 'plans.exports.planificationAnnuelleHint',
      request: (id, annee) => admin.downloadPlanificationAnnuelle(id, annee),
      filename: (slug, annee) => `planification-annuelle-${slug}-${annee}.xlsx`,
      parAnnee: true,
    },
    {
      key: 'arborescence',
      testId: 'arbo-export-prefilled',
      icon: 'fi-rr-download',
      labelKey: 'plans.exports.arborescence',
      hintKey: 'plans.exports.arborescenceHint',
      request: id => admin.downloadArborescenceTemplate(id, false),
      filename: slug => `arborescence-${slug}.xlsx`,
    },
    {
      // #786 — actions de gestion dans le classeur d'import des actions,
      // réimportable dans un autre plan ou sur une autre instance.
      key: 'actions',
      testId: 'actions-export-reimportable',
      icon: 'fi-rr-download',
      labelKey: 'plans.exports.actions',
      hintKey: 'plans.exports.actionsHint',
      request: id => admin.downloadActionsTemplate(id),
      filename: slug => `actions-${slug}.xlsx`,
    },
  ];
  return Object.fromEntries(items.map(i => [i.key, i])) as Record<PlanExportKey, PlanExportItem>;
}

/** Enregistre un fichier téléchargé sous le nom donné. */
export function enregistrerFichier(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
