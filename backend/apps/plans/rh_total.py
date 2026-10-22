"""
#759 — « aucune ventilation » : un seul « Temps de travail total » par année.

Quand une action n'est ni ventilée (par organisme ou par type de budget) ni
déclinée par poste, son temps de travail n'a pas de cible : il n'y a alors plus
de distinction agent / partenaire. Les lots sans cible d'une même année
fusionnent en une seule ligne financée, au prévisionnel comme au réalisé.

Les fonctions n'utilisent que les gestionnaires liés (`rh_lignes`,
`realisation`) : la migration 0137 les applique aux modèles historiques.
"""

from .services_export_finance import temps_par_poste

FONCTIONNEMENT = 'fonctionnement'


def est_temps_total_unique(operation) -> bool:
    """Pendant de `rhTotalUnique()` (fiche action / saisie du suivi)."""
    return (operation.ventilation_mode or 'none') == 'none' and not temps_par_poste(operation)


def _sans_cible(lignes):
    return [l for l in lignes if l.id_poste_id is None and l.id_organisme_id is None]


def _fusionner(lignes, **champs):
    """Garde la première ligne (jours cumulés, financée), supprime les autres.
    Renvoie la ligne gardée, ou None s'il n'y a rien à fusionner."""
    if not lignes:
        return None
    gardee, autres = lignes[0], lignes[1:]
    jours = [l.jours for l in lignes if l.jours is not None]
    gardee.jours = sum(jours) if jours else None
    gardee.finance = True
    gardee.categorie_depense = FONCTIONNEMENT
    for nom, valeur in champs.items():
        setattr(gardee, nom, valeur)
    gardee.save()
    for l in autres:
        l.delete()
    return gardee


def fusionner_annee(annee):
    """Fusionne les lots sans cible d'une `OperationAnnee` (prévu et réalisé)."""
    prevus = _sans_cible(annee.rh_lignes.order_by('pk'))
    # Les réalisés rattachés à un lot prévu qui va disparaître perdraient leur
    # lien (SET_NULL) : ils sont fusionnés sur la ligne prévue gardée.
    prevu = _fusionner(prevus)
    realisation = getattr(annee, 'realisation', None) if _a_realisation(annee) else None
    if realisation is not None:
        reels = _sans_cible(realisation.rh_lignes.order_by('pk'))
        lien = {'id_operation_annee_rh_id': prevu.pk} if prevu is not None else {}
        _fusionner(reels, **lien)


def _a_realisation(annee) -> bool:
    try:
        return annee.realisation is not None
    except Exception:  # RelatedObjectDoesNotExist (modèle courant ou historique)
        return False


def fusionner_temps_total(operation, annees=None):
    """Applique la règle à toutes les années de l'action, ligne de la période
    (#735) comprise. Sans effet dans les autres modes."""
    if not est_temps_total_unique(operation):
        return
    if annees is None:
        from .models_operations import OperationAnnee
        annees = OperationAnnee.tous.filter(id_operation=operation)
    for annee in annees:
        fusionner_annee(annee)
