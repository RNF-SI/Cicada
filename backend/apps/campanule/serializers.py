"""Serializers pour l'API CAMPanule."""

from rest_framework import serializers

from .models import (
    AutocompleteProtocole,
    CampanuleProtocole,
    CampanuleMethode,
    CampanuleTechnique,
    CampanuleProtEchantillonnage,
    CampanuleProtMethRel,
    CampanuleProtTechRel,
)


class CampanuleAutocompleteSerializer(serializers.ModelSerializer):
    """Serializer pour l'autocomplete des protocoles."""

    class Meta:
        model = AutocompleteProtocole
        fields = [
            'cd_protocole', 'search_name',
            'lb_protocole_court', 'lb_protocole_complet',
            'cible', 'categorie_prot', 'prot_auteur',
        ]


class CampanuleEchantillonnageSerializer(serializers.ModelSerializer):
    """Serializer pour les plans d'échantillonnage d'un protocole."""

    class Meta:
        model = CampanuleProtEchantillonnage
        fields = [
            'cd_prot_echantillonnage', 'cd_protocole',
            'unite', 'nb_unite', 'duree', 'taille',
            'passages_an', 'periode_an', 'plan_ech',
            'commentaire', 'niveau',
        ]


class CampanuleMethodeSerializer(serializers.ModelSerializer):
    """Serializer pour les méthodes."""

    class Meta:
        model = CampanuleMethode
        fields = [
            'cd_methode', 'lb_methode_court', 'lb_methode_complet',
            'descr_methode',
        ]


class CampanuleTechniqueSerializer(serializers.ModelSerializer):
    """Serializer pour les techniques."""

    class Meta:
        model = CampanuleTechnique
        fields = [
            'cd_technique', 'lb_technique_fr', 'lb_tech_complet_fr',
            'descr_technique', 'categorie_tech',
        ]


class CampanuleProtocoleDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un protocole CAMPanule."""

    echantillonnages = serializers.SerializerMethodField()
    methodes = serializers.SerializerMethodField()
    techniques = serializers.SerializerMethodField()

    class Meta:
        model = CampanuleProtocole
        fields = [
            'cd_protocole', 'lb_protocole_court', 'lb_protocole_complet',
            'lb_protocole_en', 'description',
            'cible', 'categorie_prot', 'prot_auteur',
            'descr_cible_prot', 'descr_objectif_prot',
            'date_publi', 'version', 'obsolete',
            'url_perm', 'url', 'url_complementaire',
            'echelle_restit', 'saisie', 'biologie', 'abiotique',
            'nature_donnees', 'analyse_reference',
            'guide_sinp_donnees', 'norme', 'indicateur',
            'uuid',
            # Nested
            'echantillonnages', 'methodes', 'techniques',
        ]

    def get_echantillonnages(self, obj):
        echs = CampanuleProtEchantillonnage.objects.filter(
            cd_protocole=obj.cd_protocole
        )
        return CampanuleEchantillonnageSerializer(echs, many=True).data

    def get_methodes(self, obj):
        rels = CampanuleProtMethRel.objects.filter(
            cd_protocole=obj.cd_protocole
        ).values_list('cd_methode', flat=True)
        methodes = CampanuleMethode.objects.filter(cd_methode__in=rels)
        return CampanuleMethodeSerializer(methodes, many=True).data

    def get_techniques(self, obj):
        rels = CampanuleProtTechRel.objects.filter(
            cd_protocole=obj.cd_protocole
        ).values_list('cd_technique', flat=True)
        techniques = CampanuleTechnique.objects.filter(cd_technique__in=rels)
        return CampanuleTechniqueSerializer(techniques, many=True).data
