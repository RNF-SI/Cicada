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

from .models import ContenuIndexe, PlanIndexe


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


class PlanResumeSerializer(serializers.ModelSerializer):
    """Bandeau « Plan de gestion / Gestionnaire / Période » d'une tuile."""

    reference = serializers.SerializerMethodField()

    class Meta:
        model = PlanIndexe
        fields = [
            'reference', 'instance_id', 'id_pg', 'nom', 'slug', 'statut',
            'annee_debut', 'annee_fin', 'type_document', 'sites',
            'gestionnaire_principal', 'url_instance',
        ]

    def get_reference(self, plan):
        return reference_plan(plan)


class ContenuResultatSerializer(serializers.ModelSerializer):
    """Une tuile de résultat du mode « contenu d'un plan de gestion »."""

    plan = PlanResumeSerializer(read_only=True)

    class Meta:
        model = ContenuIndexe
        fields = [
            'id', 'type_contenu', 'id_objet',
            'titre', 'description',
            'parent_type', 'parent_libelle',
            'sous_type', 'sous_type_libelle',
            'instance_id', 'plan',
        ]


class PlanResultatSerializer(serializers.ModelSerializer):
    """Une tuile de résultat du mode « plan de gestion »."""

    reference = serializers.SerializerMethodField()

    class Meta:
        model = PlanIndexe
        fields = [
            'reference', 'instance_id', 'id_pg', 'nom', 'slug', 'statut', 'rang',
            'annee_debut', 'annee_fin',
            'type_document', 'sites', 'gestionnaire_principal', 'url_instance',
        ]

    def get_reference(self, plan):
        return reference_plan(plan)
