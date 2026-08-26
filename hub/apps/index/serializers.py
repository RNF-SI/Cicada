"""
Sérialiseurs de l'exploration.

Forme de sortie identique à celle de CICADA : pendant la transition, une même
page d'interface peut être servie par un index local ou par le hub, et le
frontend ne doit pas avoir à distinguer les deux.

Une différence assumée : chaque résultat porte son ``instance_id`` et une
``reference`` — CICADA n'en a pas l'usage, un index local n'ayant qu'une seule
provenance, mais le champ y existe déjà et vaut simplement toujours la même
chose.
"""

from rest_framework import serializers

from .filters import CHAMPS_CORRESPONDANCE
from .identites import identites
from .models import ContenuIndexe, PlanIndexe


def contexte_provenance(plans):
    """
    Contexte de sérialisation portant le nom des instances d'origine.

    Résolu **une fois par page de résultats**, pas une fois par tuile : une
    recherche transverse en aligne vingt, venues d'une poignée d'instances.

    :param plans: les :class:`PlanIndexe` de la page (ou les contenus, dont on
        lit `instance_id`).
    """
    return {
        'identites_instances': identites(
            {objet.instance_id for objet in plans if objet.instance_id}
        )
    }


class ProvenanceMixin:
    """
    Ajoute le **nom** de l'instance d'origine à côté de son identifiant.

    L'identifiant technique suffit à tracer une ligne d'index ; il ne suffit pas
    à l'afficher. « rnf » ne dit pas à un gestionnaire de quelle structure vient
    le plan qu'il lit, et un résultat dont on ignore la provenance se lit comme
    un résultat local — c'est-à-dire faux.
    """

    def get_instance_libelle(self, objet):
        identite = (self.context.get('identites_instances') or {}).get(
            objet.instance_id
        )
        # Repli sur l'identifiant plutôt que sur du vide : mieux vaut une
        # provenance laide qu'une provenance absente.
        return (identite or {}).get('libelle') or objet.instance_id


def reference_plan(plan):
    """
    Référence stable d'un plan, tous déploiements confondus.

    Ni l'identifiant du plan chez l'émetteur ni son slug ne sont uniques ici :
    deux instances peuvent produire les mêmes. L'identifiant interne du hub,
    lui, serait unique mais pas *durable* — un plan dépublié puis republié en
    obtiendrait un nouveau, cassant les liens.

    Le couple instance + slug est unique et durable, et se lit.
    """
    return f"{plan.instance_id}:{plan.slug}"


class PlanResumeSerializer(ProvenanceMixin, serializers.ModelSerializer):
    """Bandeau « Plan de gestion / Gestionnaire / Période » d'une tuile."""

    reference = serializers.SerializerMethodField()
    instance_libelle = serializers.SerializerMethodField()

    class Meta:
        model = PlanIndexe
        fields = [
            'reference', 'instance_id', 'instance_libelle', 'id_pg', 'nom',
            'slug', 'statut', 'annee_debut', 'annee_fin', 'type_document',
            'sites', 'gestionnaire_principal', 'url_instance',
        ]

    def get_reference(self, plan):
        return reference_plan(plan)


class ContenuResultatSerializer(ProvenanceMixin, serializers.ModelSerializer):
    """Une tuile de résultat du mode « contenu d'un plan de gestion »."""

    plan = PlanResumeSerializer(read_only=True)
    instance_libelle = serializers.SerializerMethodField()

    correspondances = serializers.SerializerMethodField()
    extrait_rattachements = serializers.SerializerMethodField()

    class Meta:
        model = ContenuIndexe
        fields = [
            'id', 'type_contenu', 'id_objet',
            'titre', 'description',
            'parent_type', 'parent_libelle',
            'sous_type', 'sous_type_libelle',
            'instance_id', 'instance_libelle',
            # #650 — pourquoi ce résultat est là.
            'correspondances', 'extrait_rattachements', 'plan',
        ]


    def get_correspondances(self, contenu):
        """
        Champs ayant répondu à la recherche (#650).

        Vide quand la requête ne porte pas de mot-clé : il n'y a alors rien à
        expliquer. Les objets rattachés — espèces, habitats, protocoles — sont
        interrogés mais jamais affichés sur la tuile : sans cette liste, un
        résultat dont le titre n'a aucun rapport visible avec la requête paraît
        arbitraire alors qu'il est pertinent.
        """
        return [
            champ for champ in CHAMPS_CORRESPONDANCE
            if getattr(contenu, f'correspond_{champ}', False)
        ]

    def get_extrait_rattachements(self, contenu):
        """
        Fragment de l'objet rattaché qui a répondu, sans balisage.

        Le champ est un bloc de texte sans séparateur : seul `ts_headline` sait
        y isoler le passage utile. Le surlignage est laissé à l'interface, pour
        ne pas faire transiter du HTML depuis la base.
        """
        if not getattr(contenu, 'correspond_rattachements', False):
            return None
        return getattr(contenu, 'extrait_rattachements', None) or None


class PlanResultatSerializer(ProvenanceMixin, serializers.ModelSerializer):
    """Une tuile de résultat du mode « plan de gestion »."""

    reference = serializers.SerializerMethodField()
    instance_libelle = serializers.SerializerMethodField()

    class Meta:
        model = PlanIndexe
        fields = [
            'reference', 'instance_id', 'instance_libelle', 'id_pg', 'nom',
            'slug', 'statut', 'rang', 'annee_debut', 'annee_fin',
            'type_document', 'sites', 'gestionnaire_principal', 'url_instance',
        ]

    def get_reference(self, plan):
        return reference_plan(plan)
