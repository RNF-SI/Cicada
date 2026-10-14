"""
Lecture d'exploration des écrans réels d'un plan (#683).

L'exploration des données ouvrait un résultat sur une **fiche publique**
distincte des écrans du plan. Les utilisateurs veulent arriver sur ce qu'ils
connaissent : la page du plan, son arborescence, sa fiche action. Pour un plan
validé — le seul explorable — ces écrans doivent donc s'ouvrir à tout
utilisateur connecté, **mais sans les données sensibles** : mesures,
réalisations, budget, RH, fichiers, personnes. C'est le même périmètre que la
fiche publique (cf. ``apps/search/serializers_fiche.py``), servi cette fois
par l'API normale.

Le mécanisme tient dans :class:`LectureExplorationMixin`, à poser sur un
ViewSet de **structure** :

1. pour les seules actions listées dans ``actions_exploration`` (lecture d'un
   objet, lecture « par parent »), le périmètre de lecture s'élargit aux plans
   validés (:func:`apps.plans.access.q_exploration`) ;
2. l'action **ancre** la réponse sur un plan (:meth:`ancrer`, automatique pour
   ``retrieve``) ;
3. si le lecteur ne voit ce plan *que* par l'exploration, la réponse est
   **élaguée** de ses clés sensibles avant d'être rendue
   (:func:`elaguer`), et porte ``acces_exploration: true``.

L'élagage se fait sur la réponse rendue et non sérialiseur par sérialiseur :
les données sensibles sont imbriquées profondément (un enjeu → ses indicateurs
→ leurs métriques → leurs mesures ; une action → ses années → leur budget et
leurs réalisations) et une trentaine de sérialiseurs portent `createur_nom`.
En nommer la liste **une fois**, ici, est ce qui rend le cloisonnement
vérifiable — c'est l'approche de ``TestFichePubliqueCloisonnement``.

Les listes « à plat » (``list``) ne sont **pas** ouvertes à l'exploration :
elles mêlent des plans de périmètres différents et servent les écrans de
gestion. Les ViewSets de suivi (mesures, réalisations, postes, bilan…) ne
portent pas ce mixin et gardent leur périmètre strict. Les écritures restent
soumises à ``IsReferentOrReadOnly`` et ``CanModifyOnlyDraftPlan``.
"""

from rest_framework.permissions import SAFE_METHODS

from .access import lecture_exploration
from .models import PlanGestion

#: Clés retirées d'une réponse servie à un lecteur d'exploration, où qu'elles
#: soient dans l'arbre. Chaque entrée nomme ce qu'elle protège.
CLES_SENSIBLES = frozenset({
    # Personnes
    'createur_nom', 'id_utilisateur_ajout', 'id_utilisateur_maj',
    'utilisateur_ajout', 'utilisateur_maj',
    'referents', 'membres', 'referents_ids',
    'redacteur_nom', 'redacteurs', 'relecteurs', 'autres_contributeurs',
    # Fichiers et commentaires internes
    'fichiers', 'documents', 'nb_fichiers', 'commentaire',
    # Mesures et évaluations d'indicateurs
    'mesures', 'nb_mesures', 'score_overrides', 'global_score_override',
    'annual_mesures',
    # Programmation, budget, RH, financement
    'operation_annees', 'nb_operation_annees', 'finances', 'nb_finances',
    'financeurs', 'ventilation_mode', 'declinaison_par_poste',
    'declinaison_par_type_cout', 'cout_salarial_auto',
    'rh_lignes', 'organismes_annee',
    # Réalisations
    'realisation', 'realisations',
    'niveau_realisation_global_mnemonique', 'niveau_realisation_global_label',
    'niveau_realisation_global_manuel', 'niveau_realisation_global_commentaire',
})

CLE_ACCES = 'acces_exploration'


def elaguer(donnees):
    """Retire récursivement les clés sensibles d'une structure JSON-like."""
    if isinstance(donnees, dict):
        return {
            cle: elaguer(valeur)
            for cle, valeur in donnees.items()
            if cle not in CLES_SENSIBLES
        }
    if isinstance(donnees, list):
        return [elaguer(element) for element in donnees]
    return donnees


def plan_de(objet):
    """Le plan auquel un objet de l'arborescence se rattache."""
    if isinstance(objet, PlanGestion):
        return objet
    getter = getattr(objet, 'get_plan_de_gestion', None)
    return getter() if getter else None


class LectureExplorationMixin:
    """
    Élargit la lecture d'un ViewSet de structure aux plans validés (#683), et
    élague la réponse quand le lecteur n'est là que par l'exploration.

    ``actions_exploration`` : noms des actions concernées. ``retrieve`` s'ancre
    seul (via ``get_object``) ; une action « par parent » appelle
    ``self.ancrer(parent)`` après l'avoir résolu.
    """

    actions_exploration = ('retrieve',)

    def lecture_exploration(self):
        """Vrai si cette requête peut bénéficier du périmètre d'exploration."""
        return (
            self.request.method in SAFE_METHODS
            and getattr(self, 'action', None) in self.actions_exploration
        )

    def ancrer(self, objet):
        """Désigne le plan sur lequel la réponse porte."""
        self._plan_ancre = plan_de(objet)

    def get_object(self):
        objet = super().get_object()
        if self.lecture_exploration():
            self.ancrer(objet)
        return objet

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        plan = getattr(self, '_plan_ancre', None)
        if (
            plan is None
            or not self.lecture_exploration()
            or not 200 <= response.status_code < 300
            or response.data is None
        ):
            return response
        exploration = lecture_exploration(request.user, plan)
        if exploration:
            response.data = elaguer(response.data)
        if isinstance(response.data, dict):
            # Dit au client dans quel mode il lit : c'est lui qui masque les
            # entrées (suivis, exports, fichiers…) dont l'API ne répondrait
            # de toute façon pas.
            response.data[CLE_ACCES] = exploration
        return response
