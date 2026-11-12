"""Plans visés par une écriture : celui de l'objet modifié et ceux de chaque clé reçue.

Le droit d'écrire se contrôle **plan par plan** (``user_can_write_plan``). Il ne
suffit pas de le vérifier sur le plan de l'objet modifié : une écriture peut
désigner un autre plan par une clé étrangère (``id_pg``, ``id_olt``,
``id_metrique``…) ou une liste d'identifiants (``pression_ids``,
``metrique_ids``…). Déplacer un enjeu dans le plan validé d'un autre organisme,
ou créer un objet sous le parent d'un plan où l'on n'est que lecteur, passait
ainsi les contrôles. Ce module retrouve tous ces plans, à partir du modèle de la
vue et des données reçues, sans dépendre de la forme de chaque serializer.
"""
from django.apps import apps

from .models import PlanGestion

#: Listes d'identifiants déclarées par les serializers (champs non modèles).
LISTES_D_IDENTIFIANTS = {
    'pression_ids': 'plans.Pression',
    'metrique_ids': 'plans.Metrique',
    'ne_ids': 'plans.NiveauExigence',
    'oo_ids': 'plans.ObjectifOperationnel',
    'olt_ids': 'plans.ObjectifLongTerme',
    'enjeu_ids': 'plans.Enjeu',
    'facteur_ids': 'plans.FacteurInfluence',
    'resultat_ids': 'plans.ResultatAttendu',
    'indicateur_ids': 'plans.Indicateur',
    'operation_ids': 'plans.Operation',
    'ra_ids': 'plans.ResultatAttendu',
    # Actions qui relient l'objet à une cible désignée par son identifiant.
    'metrique_id': 'plans.Metrique',
    # Déplacements (glisser-déposer) : la cible est dans le plan d'arrivée.
    'new_indicateur_id': 'plans.Indicateur',
    'from_indicateur_id': 'plans.Indicateur',
    'new_facteur_id': 'plans.FacteurInfluence',
    # Saisie du suivi par action et par année.
    'id_operation': 'plans.Operation',
}


def plan_de(objet):
    """Le plan auquel un objet se rattache (``None`` s'il n'en a pas)."""
    if objet is None:
        return None
    if isinstance(objet, PlanGestion):
        return objet
    getter = getattr(objet, 'get_plan_de_gestion', None)
    if not callable(getter):
        return None
    try:
        return getter()
    except Exception:
        return None


def _rattache_a_un_plan(modele):
    return modele is PlanGestion or callable(getattr(modele, 'get_plan_de_gestion', None))


def _valeurs(donnees, cle):
    if hasattr(donnees, 'getlist'):
        valeurs = donnees.getlist(cle)
    else:
        valeurs = donnees.get(cle)
    if valeurs in (None, '', []):
        return []
    if not isinstance(valeurs, (list, tuple)):
        valeurs = [valeurs]
    identifiants = []
    for valeur in valeurs:
        if isinstance(valeur, dict):
            valeur = valeur.get('id') or valeur.get('pk')
        try:
            identifiants.append(int(valeur))
        except (TypeError, ValueError):
            continue
    return identifiants


def _cles_relations(modele):
    """(clé de la donnée reçue, modèle visé) pour chaque relation vers un objet d'un plan."""
    for champ in modele._meta.get_fields():
        if not champ.is_relation or champ.auto_created and not champ.concrete:
            continue
        if not (champ.many_to_one or champ.one_to_one or champ.many_to_many):
            continue
        cible = champ.related_model
        if cible is None or not _rattache_a_un_plan(cible):
            continue
        # Un plan qui désigne un autre plan (version parente, rang suivant) ne
        # le modifie pas : ces liens ont leurs propres règles (même site, rang).
        if modele is PlanGestion and cible is PlanGestion:
            continue
        yield champ.name, cible
        attname = getattr(champ, 'attname', None)
        if attname and attname != champ.name:
            yield attname, cible


def plans_vises(modele, donnees):
    """Tous les plans désignés par ``donnees`` pour une écriture sur ``modele``."""
    if modele is None or not hasattr(donnees, 'get'):
        return set()
    plans = set()
    cles = list(_cles_relations(modele))
    cles += [(cle, apps.get_model(label)) for cle, label in LISTES_D_IDENTIFIANTS.items()]
    for cle, cible in cles:
        identifiants = _valeurs(donnees, cle)
        if not identifiants:
            continue
        for objet in cible._base_manager.filter(pk__in=identifiants):
            plan = plan_de(objet)
            if plan is not None:
                plans.add(plan)
    return plans


def modele_de_la_vue(view):
    queryset = getattr(view, 'queryset', None)
    if queryset is not None:
        return queryset.model
    try:
        return view.get_serializer_class().Meta.model
    except Exception:
        return None

