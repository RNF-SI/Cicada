"""
Sérialiseurs de l'exploration des données.

Les tuiles de résultat affichent le plan, ses sites, son gestionnaire principal
et sa période. Ces libellés ne sont **pas** dénormalisés dans l'index : ils sont
joints à la volée, une page ne contenant qu'une vingtaine de résultats. Une
donnée jointe ne peut pas devenir obsolète, contrairement à une copie.
"""

from django.db.models import Prefetch
from rest_framework import serializers

from apps.plans.models import CorSitePg, PlanGestion
from apps.users.models import CorOgSite

from .models import ContenuIndexe


def prefetch_sites():
    """
    Prefetch des sites d'un plan, avec leur gestionnaire principal.

    Sans ça, chaque tuile déclencherait une requête par site puis une par
    organisme — soit une cinquantaine de requêtes pour une page de résultats.

    Vit ici plutôt que dans les vues parce que la publication vers le hub
    (`push.py`) en a le même besoin : c'est ce prefetch qui alimente
    `_sites_du_plan`, et l'oublier ne casse rien visiblement — la liste des
    sites ressort simplement vide.
    """
    gestionnaires = Prefetch(
        'site__corogsite_set',
        queryset=CorOgSite.objects.filter(principal=True).select_related('uuid_og'),
        to_attr='gestionnaires_principaux',
    )
    return Prefetch(
        'sites',
        queryset=(
            CorSitePg.objects
            .select_related('site')
            .prefetch_related(gestionnaires)
            .order_by('rang', 'site__nom_site')
        ),
        to_attr='sites_ordonnes',
    )


def _gestionnaire_principal(site):
    """Nom de l'organisme gestionnaire principal d'un site, si prefetché."""
    liens = getattr(site, 'gestionnaires_principaux', None)
    if not liens:
        return None
    return liens[0].uuid_og.nom_organisme


def _sites_du_plan(plan):
    """Sites du plan, du principal (rang 1) au dernier."""
    return [lien.site for lien in getattr(plan, 'sites_ordonnes', [])]


class SiteResumeSerializer(serializers.Serializer):
    """Site tel qu'affiché sur une tuile de résultat."""

    id_site = serializers.IntegerField()
    nom_site = serializers.CharField()
    slug = serializers.CharField()


class PlanResumeSerializer(serializers.Serializer):
    """Bandeau « Plan de gestion / Gestionnaire / Période » d'une tuile."""

    id_pg = serializers.IntegerField()
    nom = serializers.CharField()
    slug = serializers.CharField()
    statut = serializers.CharField()
    annee_debut = serializers.IntegerField(allow_null=True)
    annee_fin = serializers.IntegerField(allow_null=True)
    type_document = serializers.SerializerMethodField()
    sites = serializers.SerializerMethodField()
    gestionnaire_principal = serializers.SerializerMethodField()

    def get_type_document(self, plan):
        return plan.id_type_document.label if plan.id_type_document_id else None

    def get_sites(self, plan):
        return SiteResumeSerializer(_sites_du_plan(plan), many=True).data

    def get_gestionnaire_principal(self, plan):
        # Le gestionnaire affiché est celui du site principal du plan.
        for site in _sites_du_plan(plan):
            nom = _gestionnaire_principal(site)
            if nom:
                return nom
        return None


class ContenuResultatSerializer(serializers.ModelSerializer):
    """Une tuile de résultat du mode « contenu d'un plan de gestion »."""

    plan = serializers.SerializerMethodField()

    class Meta:
        model = ContenuIndexe
        fields = [
            'id', 'type_contenu', 'id_objet',
            'titre', 'description',
            'parent_type', 'parent_libelle',
            'sous_type', 'sous_type_libelle',
            'instance_id', 'plan',
        ]

    def get_plan(self, contenu):
        """
        Bandeau du plan — joint pour un document local, recopié pour un distant.

        Un document reçu d'une autre instance (#636) n'a pas de plan dans cette
        base : `id_pg` est NULL et l'affichage vient du snapshot capturé à la
        publication. Les deux chemins produisent la même forme, pour que
        l'interface n'ait pas à distinguer les deux cas.
        """
        if contenu.id_pg_id is None:
            return contenu.plan_denorm or None
        return PlanResumeSerializer(contenu.id_pg).data


class PlanResultatSerializer(serializers.ModelSerializer):
    """Une tuile de résultat du mode « plan de gestion »."""

    type_document = serializers.SerializerMethodField()
    sites = serializers.SerializerMethodField()
    gestionnaire_principal = serializers.SerializerMethodField()

    class Meta:
        model = PlanGestion
        fields = [
            'id_pg', 'nom', 'slug', 'statut', 'rang',
            'annee_debut', 'annee_fin',
            'type_document', 'sites', 'gestionnaire_principal',
        ]

    def get_type_document(self, plan):
        return plan.id_type_document.label if plan.id_type_document_id else None

    def get_sites(self, plan):
        return SiteResumeSerializer(_sites_du_plan(plan), many=True).data

    def get_gestionnaire_principal(self, plan):
        for site in _sites_du_plan(plan):
            nom = _gestionnaire_principal(site)
            if nom:
                return nom
        return None
