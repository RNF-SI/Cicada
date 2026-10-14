/**
 * #672 — Dernière année d'un plan, prolongation (#250) comprise.
 *
 * La prolongation ajoute 1 ou 2 années (`annees_extension`) sans modifier
 * `annee_fin` : tout écran qui construit les années du plan (programmation,
 * suivi, tableau de bord) doit donc partir de l'échéance effective, sinon les
 * années ajoutées ne sont ni programmables ni suivies.
 */
export function planEndYear(plan: {
  annee_fin?: number | null;
  annee_fin_effective?: number | null;
  annees_extension?: number | null;
}): number | null {
  if (plan.annee_fin_effective != null) return plan.annee_fin_effective;
  if (plan.annee_fin == null) return null;
  return plan.annee_fin + (plan.annees_extension ?? 0);
}
