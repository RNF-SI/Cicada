"""
Sérialiseurs de la fiche publique d'un plan de gestion.

**Ces sérialiseurs sont volontairement écrits à la main, sans réutiliser ceux
de `apps.plans`.** La fiche est consultable par tout utilisateur connecté, y
compris hors de l'organisme gestionnaire : c'est le seul endroit du projet où
le contenu d'un plan sort de son périmètre de lecture (#610). Hériter des
sérialiseurs internes ferait entrer ici, à la première évolution de ceux-ci,
des champs que personne n'aurait décidé de publier.

Périmètre publié : la **structure** du plan — enjeux, facteurs d'influence,
pressions, objectifs, niveaux d'exigence, résultats attendus, indicateurs,
métriques et actions programmées.

Périmètre exclu, et la liste est exhaustive :

- budget et financement (``OperationAnnee``, ``FinanceOperation``,
  ``Operation.financeurs``) ;
- ressources humaines (``Poste``, ``Fonction``, ``OperationAnneeRH``) ;
- données empiriques : mesures d'indicateurs (``Mesure``) et réalisations
  annuelles (``RealisationOperationAnnee``) ;
- traçabilité interne : auteurs et dates de modification.

Le test `TestFichePubliqueCloisonnement` vérifie ces exclusions champ par champ.
"""

from rest_framework import serializers


def _label(nomenclature):
    return nomenclature.label if nomenclature else None


#: Libellés des 5 paliers de la grille de lecture, dans l'ordre des scores.
NIVEAUX_GRILLE = {
    1: "Très mauvais", 2: "Mauvais", 3: "Moyen", 4: "Bon", 5: "Très bon",
}


class MetriquePubliqueSerializer(serializers.Serializer):
    """Définition d'une métrique — ce qui est mesuré, jamais les mesures."""

    id_metrique = serializers.IntegerField()
    nom_metrique = serializers.CharField()
    unite = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    grille = serializers.SerializerMethodField()

    def get_grille(self, metrique):
        """
        Grille de lecture 5 paliers, ou `None` si la métrique n'en a pas (#634).

        C'est le barème d'évaluation — ce qui fait qu'une mesure vaut « bon »
        plutôt que « moyen ». Il est publié parce qu'une valeur seule ne se lit
        pas sans lui ; les mesures, elles, restent internes.

        Le rendu textuel des paliers (intervalles, bornes incluses, blocs ET/OU)
        vient de l'export de fiche action : c'est la source de vérité de cette
        notation, et deux implémentations divergeraient (#619).
        """
        from apps.plans.services_export_fiche_action import _grid_cell, _is_grille

        if not _is_grille(metrique):
            return None
        paliers = [
            {'niveau': niveau, 'libelle': libelle,
             'valeur': _grid_cell(metrique, niveau) or None}
            for niveau, libelle in NIVEAUX_GRILLE.items()
        ]
        # Une grille dont aucun palier n'est renseigné n'apprend rien : on la
        # tait plutôt que d'afficher cinq cases vides.
        return paliers if any(p['valeur'] for p in paliers) else None


class IndicateurPublicSerializer(serializers.Serializer):
    id_indicateur = serializers.IntegerField()
    nom_indicateur = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    type_indicateur = serializers.SerializerMethodField()
    est_standardise = serializers.BooleanField()
    metriques = MetriquePubliqueSerializer(many=True)

    def get_type_indicateur(self, indicateur):
        return _label(indicateur.type_indicateur)


class ActionPubliqueSerializer(serializers.Serializer):
    """
    Action de gestion, sans sa dimension financière ni sa réalisation.

    `annee_min`/`annee_max` disent quand l'action est programmée ; le détail
    annuel (budget, ETP, ventilation par organisme) reste interne.
    """

    id_operation = serializers.IntegerField()
    libelle = serializers.CharField()
    code_operation = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    categorie = serializers.SerializerMethodField()
    type_action = serializers.SerializerMethodField()
    priorite = serializers.SerializerMethodField()
    annee_min = serializers.IntegerField(allow_null=True)
    annee_max = serializers.IntegerField(allow_null=True)
    operateurs = serializers.CharField(allow_null=True)
    partenaires = serializers.CharField(allow_null=True)
    # Cadre de l'action : ce qu'elle sert à suivre (#634). Sans lui, la fiche
    # action se réduit à un libellé et une période, et le lien avec
    # l'arborescence — la raison d'être de l'action — reste invisible.
    #: Rattachement à l'arborescence : permet d'afficher l'action **sous**
    #: l'indicateur qu'elle sert, et pas seulement dans une liste à plat.
    id_indicateur = serializers.IntegerField(
        source='id_indicateur_id', allow_null=True)
    indicateur = serializers.SerializerMethodField()
    metriques = serializers.SerializerMethodField()

    def get_indicateur(self, operation):
        indicateur = operation.id_indicateur
        return indicateur.nom_indicateur if indicateur else None

    def get_metriques(self, operation):
        return [
            {'id_metrique': metrique.pk,
             'nom_metrique': metrique.nom_metrique,
             'unite': metrique.unite or None}
            for metrique in operation.metriques.all()
        ]

    def get_categorie(self, operation):
        categorie = operation.id_categorie_action_reserve
        if not categorie:
            return None
        return f"{categorie.mnemonique} - {categorie.label}"

    def get_type_action(self, operation):
        return _label(operation.id_type_action)

    def get_priorite(self, operation):
        return _label(operation.id_priorite)


class NiveauExigencePublicSerializer(serializers.Serializer):
    id_ne = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    indicateurs = IndicateurPublicSerializer(many=True, source='indicateurs_pub')


class ObjectifLongTermePublicSerializer(serializers.Serializer):
    id_olt = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    niveaux_exigence = NiveauExigencePublicSerializer(many=True, source='niveaux_pub')


class ResultatAttenduPublicSerializer(serializers.Serializer):
    id_ra = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    indicateurs = IndicateurPublicSerializer(many=True, source='indicateurs_pub')


class ObjectifOperationnelPublicSerializer(serializers.Serializer):
    id_oo = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    resultats_attendus = ResultatAttenduPublicSerializer(many=True, source='resultats_pub')


class PressionPubliqueSerializer(serializers.Serializer):
    id_pression = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    type_pression = serializers.SerializerMethodField()

    def get_type_pression(self, pression):
        return _label(pression.id_type_pression)


class FacteurInfluencePublicSerializer(serializers.Serializer):
    id_facteur_influence = serializers.IntegerField()
    libelle = serializers.CharField()
    description = serializers.CharField(allow_null=True)
    pressions = PressionPubliqueSerializer(many=True, source='pressions_pub')


class EnjeuPublicSerializer(serializers.Serializer):
    id_enjeu = serializers.IntegerField()
    libelle = serializers.CharField()
    intitule_court = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)
    etat_enjeu = serializers.CharField(allow_null=True)
    rang = serializers.IntegerField(allow_null=True)
    categorie = serializers.SerializerMethodField()
    categorie_ecologique = serializers.BooleanField(allow_null=True)
    taxons = serializers.SerializerMethodField()
    habitats = serializers.SerializerMethodField()
    facteurs = FacteurInfluencePublicSerializer(many=True, source='facteurs_pub')
    objectifs_long_terme = ObjectifLongTermePublicSerializer(many=True, source='olt_pub')
    objectifs_operationnels = ObjectifOperationnelPublicSerializer(many=True, source='oo_pub')

    def get_categorie(self, enjeu):
        return _label(enjeu.id_categorie)

    def get_taxons(self, enjeu):
        return [
            {'cd_nom': taxon.cd_nom, 'nom_complet': taxon.nom_complet,
             'nom_vern': taxon.nom_vern}
            for taxon in enjeu.taxons.all()
        ]

    def get_habitats(self, enjeu):
        return [
            {'cd_hab': habitat.cd_hab, 'lb_hab_fr': habitat.lb_hab_fr}
            for habitat in enjeu.habitats.all()
        ]


class FichePubliqueSerializer(serializers.Serializer):
    """Un plan de gestion et sa structure, en lecture seule."""

    id_pg = serializers.IntegerField()
    nom = serializers.CharField()
    slug = serializers.CharField()
    statut = serializers.CharField()
    rang = serializers.IntegerField()
    annee_debut = serializers.IntegerField(allow_null=True)
    annee_fin = serializers.IntegerField(allow_null=True)
    surface = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True,
    )
    type_document = serializers.SerializerMethodField()
    sites = serializers.SerializerMethodField()
    gestionnaire_principal = serializers.SerializerMethodField()
    enjeux = EnjeuPublicSerializer(many=True, source='enjeux_pub')
    actions = ActionPubliqueSerializer(many=True, source='actions_pub')

    def get_type_document(self, plan):
        return _label(plan.id_type_document)

    def get_sites(self, plan):
        return [
            {
                'id_site': lien.site.id_site,
                'nom_site': lien.site.nom_site,
                'slug': lien.site.slug,
                'type_site': (
                    lien.site.id_type_site.mnemonique
                    if lien.site.id_type_site_id else None
                ),
            }
            for lien in plan.sites_ordonnes
        ]

    def get_gestionnaire_principal(self, plan):
        for lien in plan.sites_ordonnes:
            gestionnaires = getattr(lien.site, 'gestionnaires_principaux', [])
            if gestionnaires:
                return gestionnaires[0].uuid_og.nom_organisme
        return None
