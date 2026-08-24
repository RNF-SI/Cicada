"""
Sérialiseurs de l'API publique des métadonnées des plans (#645).

Cette API est un **contrat avec une application tierce** (DOCenCEN côté CEN),
pas une vue interne : sa forme ne doit pas suivre les remaniements de
l'interface. D'où des sérialiseurs dédiés plutôt qu'une réutilisation de
`PlanGestionSerializer`, dont les champs bougent au fil des écrans.

Périmètre : **les métadonnées uniquement** — ce que l'on saisit au premier
formulaire de création d'un plan. Le contenu du plan (enjeux, objectifs,
indicateurs, actions), le budget, les ressources humaines et le suivi ne
passent jamais par ici : une GED documente des documents, elle n'a pas besoin
de leur substance, et l'endpoint est ouvert.
"""

from django.conf import settings
from django.db.models import Prefetch
from rest_framework import serializers

from apps.users.models import CorOgSite

from .models import CorSitePg, PlanGestion


def prefetch_sites_publics():
    """
    Sites d'un plan, avec leur type et leur gestionnaire principal.

    Sans ce prefetch, une page de résultats déclenche une requête par site puis
    une par organisme. L'exploration a le même besoin (`apps.search`), mais son
    prefetch ne charge pas le type de site : le dupliquer ici garde le contrat
    public indépendant des besoins d'affichage de l'exploration, qui bougent.
    """
    gestionnaires = Prefetch(
        'site__corogsite_set',
        queryset=CorOgSite.objects.filter(principal=True).select_related('uuid_og'),
        to_attr='gestionnaires_principaux_publics',
    )
    return Prefetch(
        'sites',
        queryset=(
            CorSitePg.objects
            .select_related('site', 'site__id_type_site')
            .prefetch_related(gestionnaires)
            .order_by('rang', 'site__nom_site')
        ),
        to_attr='sites_publics',
    )


def _sites_du_plan(plan):
    """Sites du plan, du principal (rang 1) au dernier."""
    return [lien.site for lien in getattr(plan, 'sites_publics', [])]


def _gestionnaire_principal(site):
    """Nom de l'organisme gestionnaire principal d'un site, si prefetché."""
    liens = getattr(site, 'gestionnaires_principaux_publics', None)
    return liens[0].uuid_og.nom_organisme if liens else None


def _libelle_nomenclature(nomenclature):
    return nomenclature.label if nomenclature else None


class SitePublicSerializer(serializers.Serializer):
    """
    Site rattaché au plan.

    `id_inpn` est le seul identifiant national d'un site : c'est lui, et non
    `id_site` (une séquence locale), qui permet à une application tierce de
    rapprocher le site d'une autre source. Il est nullable — tous les sites
    n'ont pas de code INPN — donc exposé tel quel, sans repli silencieux.
    """

    id_inpn = serializers.CharField(allow_null=True)
    nom = serializers.CharField(source='nom_site')
    slug = serializers.CharField()
    type_site = serializers.SerializerMethodField()
    surface = serializers.FloatField(source='surf_off', allow_null=True)
    gestionnaire_principal = serializers.SerializerMethodField()

    def get_type_site(self, site) -> str | None:
        return _libelle_nomenclature(getattr(site, 'id_type_site', None))

    def get_gestionnaire_principal(self, site) -> str | None:
        return _gestionnaire_principal(site)


class PlanPublicSerializer(serializers.ModelSerializer):
    """Métadonnées d'un plan de gestion, telles que servies à une GED."""

    reference = serializers.CharField(read_only=True)
    uuid = serializers.UUIDField(source='uuid_plan', read_only=True)
    instance_id = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    type_document = serializers.SerializerMethodField()
    type_evaluation = serializers.SerializerMethodField()
    type_redacteur = serializers.SerializerMethodField()

    plan_parent_uuid = serializers.SerializerMethodField()
    plan_parent_reference = serializers.SerializerMethodField()

    sites = serializers.SerializerMethodField()
    gestionnaire_principal = serializers.SerializerMethodField()

    date_creation = serializers.DateTimeField(source='date_ajout', read_only=True)
    date_modification = serializers.DateTimeField(source='date_maj', read_only=True)

    class Meta:
        model = PlanGestion
        fields = [
            # Identité
            'reference', 'uuid', 'instance_id', 'id_pg', 'slug', 'url',
            # Ce que l'on saisit au premier formulaire de création
            'nom', 'rang', 'version', 'annee_debut', 'annee_fin', 'surface',
            'ct88', 'risque_incendie',
            'type_evaluation', 'type_redacteur', 'redacteur_nom',
            'redacteurs', 'relecteurs', 'autres_contributeurs',
            'commentaire',
            # Identifiants d'autres outils déjà portés par le plan
            'id_docgestion_fcen', 'id_cdr',
            # Cycle de vie
            'statut', 'validation_step', 'is_mi_parcours', 'en_revision',
            'annees_extension', 'type_document',
            'date_avis_csrpn', 'date_validation_comite',
            'date_arrete_pref', 'numero_arrete_pref',
            'plan_parent_uuid', 'plan_parent_reference',
            # Rattachements
            'sites', 'gestionnaire_principal',
            # Traçabilité — `date_modification` est la borne du rattrapage
            # incrémental (`modifie_depuis`).
            'date_creation', 'date_modification',
        ]

    def get_instance_id(self, plan) -> str:
        return settings.CICADA_INSTANCE_ID

    def get_url(self, plan) -> str | None:
        """
        Adresse du plan dans CICADA, si l'instance déclare son URL publique.

        Sans `CICADA_PUBLIC_URL`, on renvoie None plutôt qu'une URL construite
        sur l'hôte de la requête : derrière un reverse proxy, celle-ci serait
        souvent l'adresse interne du conteneur, et la GED enregistrerait un
        lien mort sans que rien ne le signale.
        """
        base = (settings.CICADA_PUBLIC_URL or '').rstrip('/')
        if not base:
            return None
        return f"{base}/plans/{plan.slug}"

    def get_type_document(self, plan) -> str | None:
        return _libelle_nomenclature(plan.id_type_document)

    def get_type_evaluation(self, plan) -> str | None:
        return _libelle_nomenclature(plan.id_evaluation)

    def get_type_redacteur(self, plan) -> str | None:
        return _libelle_nomenclature(plan.id_redacteur_type)

    def get_plan_parent_uuid(self, plan) -> str | None:
        return str(plan.plan_parent.uuid_plan) if plan.plan_parent_id else None

    def get_plan_parent_reference(self, plan) -> str | None:
        return plan.plan_parent.reference if plan.plan_parent_id else None

    def get_sites(self, plan) -> list:
        return SitePublicSerializer(_sites_du_plan(plan), many=True).data

    def get_gestionnaire_principal(self, plan) -> str | None:
        for site in _sites_du_plan(plan):
            nom = _gestionnaire_principal(site)
            if nom:
                return nom
        return None
