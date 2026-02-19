"""
Serializers pour l'API REST Enjeux, FCR et Responsabilités.
"""
from rest_framework import serializers
from django.contrib.gis.geos import GEOSGeometry

from .models_enjeux import (
    Enjeu, FacteurInfluence, Pression, Responsabilite,
    EtatActuel, ObjectifLongTerme, NiveauExigence,
    ObjectifOperationnel, ResultatAttendu,
    CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
    CorResponsabiliteTaxon, CorResponsabiliteHabitat, CorResponsabiliteGeologie,
    CorResponsabiliteEnjeu
)
from apps.core.models import Nomenclature


# =============================================================================
# Serializers pour les relations taxonomiques
# =============================================================================

class TaxonRefSerializer(serializers.Serializer):
    """Serializer pour les références taxonomiques."""
    cd_nom = serializers.IntegerField()
    nom_complet = serializers.CharField(max_length=500, required=False, allow_blank=True)
    nom_vern = serializers.CharField(max_length=255, required=False, allow_blank=True)


class HabitatRefSerializer(serializers.Serializer):
    """Serializer pour les références habitats."""
    cd_hab = serializers.CharField(max_length=50)
    lb_hab_fr = serializers.CharField(max_length=500, required=False, allow_blank=True)


class GeologieRefSerializer(serializers.Serializer):
    """Serializer pour les références géologiques."""
    id_inpg = serializers.CharField(max_length=50)
    nom = serializers.CharField(max_length=255, required=False, allow_blank=True)


class CorEnjeuTaxonSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Enjeu-Taxon."""

    class Meta:
        model = CorEnjeuTaxon
        fields = ['id', 'cd_nom', 'nom_complet', 'nom_vern']
        read_only_fields = ['id']


class CorEnjeuHabitatSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Enjeu-Habitat."""

    class Meta:
        model = CorEnjeuHabitat
        fields = ['id', 'cd_hab', 'lb_hab_fr']
        read_only_fields = ['id']


class CorEnjeuGeologieSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Enjeu-Géologie."""

    class Meta:
        model = CorEnjeuGeologie
        fields = ['id', 'id_inpg', 'nom']
        read_only_fields = ['id']


class CorResponsabiliteTaxonSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Responsabilité-Taxon."""

    class Meta:
        model = CorResponsabiliteTaxon
        fields = ['id', 'cd_nom', 'nom_complet', 'nom_vern']
        read_only_fields = ['id']


class CorResponsabiliteHabitatSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Responsabilité-Habitat."""

    class Meta:
        model = CorResponsabiliteHabitat
        fields = ['id', 'cd_hab', 'lb_hab_fr']
        read_only_fields = ['id']


class CorResponsabiliteGeologieSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Responsabilité-Géologie."""

    class Meta:
        model = CorResponsabiliteGeologie
        fields = ['id', 'id_inpg', 'nom']
        read_only_fields = ['id']


# =============================================================================
# Serializers pour les Niveaux d'Exigence
# =============================================================================

class NiveauExigenceSerializer(serializers.ModelSerializer):
    """Serializer pour la lecture d'un Niveau d'Exigence."""
    from .serializers_indicateurs import IndicateurSerializer as _IndicateurSerializer

    indicateurs = _IndicateurSerializer(many=True, read_only=True)
    nb_indicateurs = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = NiveauExigence
        fields = [
            'id_ne', 'id_olt',
            'libelle', 'description',
            'indicateurs', 'nb_indicateurs',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_ne', 'date_ajout', 'date_maj']

    def get_nb_indicateurs(self, obj):
        return obj.indicateurs.count()


class NiveauExigenceCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Niveau d'Exigence."""

    class Meta:
        model = NiveauExigence
        fields = [
            'id_ne', 'id_olt',
            'libelle', 'description'
        ]
        read_only_fields = ['id_ne']


# =============================================================================
# Serializers pour les Résultats Attendus (OO)
# =============================================================================

class ResultatAttenduSerializer(serializers.ModelSerializer):
    """Serializer pour la lecture d'un Résultat Attendu."""
    from .serializers_indicateurs import IndicateurSerializer as _IndicateurSerializer

    indicateurs = _IndicateurSerializer(many=True, read_only=True)
    nb_indicateurs = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = ResultatAttendu
        fields = [
            'id_ra', 'id_oo',
            'libelle', 'description',
            'indicateurs', 'nb_indicateurs',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_ra', 'date_ajout', 'date_maj']

    def get_nb_indicateurs(self, obj):
        return obj.indicateurs.count()


class ResultatAttenduCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Résultat Attendu."""

    class Meta:
        model = ResultatAttendu
        fields = [
            'id_ra', 'id_oo',
            'libelle', 'description'
        ]
        read_only_fields = ['id_ra']


# =============================================================================
# Serializers pour les Objectifs Opérationnels
# =============================================================================

class ObjectifOperationnelSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un Objectif Opérationnel avec résultats attendus imbriqués."""
    resultats_attendus = ResultatAttenduSerializer(many=True, read_only=True)
    nb_resultats_attendus = serializers.SerializerMethodField()
    facteur_influence_libelle = serializers.CharField(
        source='id_facteur_influence.libelle', read_only=True
    )
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = ObjectifOperationnel
        fields = [
            'id_oo', 'id_enjeu',
            'libelle', 'description',
            'id_facteur_influence', 'facteur_influence_libelle',
            'resultats_attendus', 'nb_resultats_attendus',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_oo', 'date_ajout', 'date_maj']

    def get_nb_resultats_attendus(self, obj):
        return obj.resultats_attendus.count()


class ObjectifOperationnelListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Objectifs Opérationnels."""
    nb_resultats_attendus = serializers.SerializerMethodField()
    facteur_influence_libelle = serializers.CharField(
        source='id_facteur_influence.libelle', read_only=True
    )
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = ObjectifOperationnel
        fields = [
            'id_oo', 'id_enjeu',
            'libelle', 'description',
            'id_facteur_influence', 'facteur_influence_libelle',
            'nb_resultats_attendus',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_oo', 'date_ajout', 'date_maj']

    def get_nb_resultats_attendus(self, obj):
        return obj.resultats_attendus.count()


class ObjectifOperationnelCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Objectif Opérationnel."""

    class Meta:
        model = ObjectifOperationnel
        fields = [
            'id_oo', 'id_enjeu',
            'libelle', 'description',
            'id_facteur_influence'
        ]
        read_only_fields = ['id_oo']


# =============================================================================
# Serializers pour les Objectifs à Long Terme
# =============================================================================

class ObjectifLongTermeSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un Objectif à Long Terme avec état actuel et niveaux d'exigence imbriqués."""
    niveaux_exigence = NiveauExigenceSerializer(many=True, read_only=True)
    nb_niveaux_exigence = serializers.SerializerMethodField()
    etat_actuel = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = ObjectifLongTerme
        fields = [
            'id_olt', 'id_enjeu',
            'libelle', 'description',
            'etat_actuel',
            'niveaux_exigence', 'nb_niveaux_exigence',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_olt', 'date_ajout', 'date_maj']

    def get_nb_niveaux_exigence(self, obj):
        return obj.niveaux_exigence.count()

    def get_etat_actuel(self, obj):
        """Retourne l'état actuel nested (relation 1:1)."""
        try:
            etat = obj.etat_actuel
        except EtatActuel.DoesNotExist:
            return None
        return {
            'id_etat_actuel': etat.id_etat_actuel,
            'id_olt': etat.id_olt_id,
            'libelle': etat.libelle,
            'description': etat.description,
            'date_ajout': etat.date_ajout,
            'date_maj': etat.date_maj,
            'createur_nom': etat.id_utilisateur_ajout.get_full_name() if etat.id_utilisateur_ajout else None,
        }


class ObjectifLongTermeListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Objectifs à Long Terme."""
    nb_niveaux_exigence = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = ObjectifLongTerme
        fields = [
            'id_olt', 'id_enjeu',
            'libelle', 'description',
            'nb_niveaux_exigence',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_olt', 'date_ajout', 'date_maj']

    def get_nb_niveaux_exigence(self, obj):
        return obj.niveaux_exigence.count()


class ObjectifLongTermeCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Objectif à Long Terme."""

    class Meta:
        model = ObjectifLongTerme
        fields = [
            'id_olt', 'id_enjeu',
            'libelle', 'description'
        ]
        read_only_fields = ['id_olt']


# =============================================================================
# Serializers pour les États Actuels
# =============================================================================

class EtatActuelSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un État Actuel (lié 1:1 à un OLT)."""
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = EtatActuel
        fields = [
            'id_etat_actuel', 'id_olt',
            'libelle', 'description',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_etat_actuel', 'date_ajout', 'date_maj']


class EtatActuelListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des États Actuels."""
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = EtatActuel
        fields = [
            'id_etat_actuel', 'id_olt',
            'libelle', 'description',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_etat_actuel', 'date_ajout', 'date_maj']


class EtatActuelCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un État Actuel."""

    class Meta:
        model = EtatActuel
        fields = [
            'id_etat_actuel', 'id_olt',
            'libelle', 'description'
        ]
        read_only_fields = ['id_etat_actuel']


# =============================================================================
# Serializers pour les Pressions
# =============================================================================

class PressionSerializer(serializers.ModelSerializer):
    """Serializer pour la lecture d'une Pression."""
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = Pression
        fields = [
            'id_pression', 'id_facteur_influence', 'id_pressref',
            'libelle', 'description',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_pression', 'date_ajout', 'date_maj']


class PressionCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une Pression."""

    class Meta:
        model = Pression
        fields = [
            'id_pression', 'id_facteur_influence', 'id_pressref',
            'libelle', 'description'
        ]
        read_only_fields = ['id_pression']


# =============================================================================
# Serializers pour les Facteurs d'Influence
# =============================================================================

class FacteurInfluenceSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un Facteur d'Influence avec pressions imbriquées."""
    pressions = PressionSerializer(many=True, read_only=True)
    nb_pressions = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = FacteurInfluence
        fields = [
            'id_facteur_influence', 'id_enjeu',
            'libelle', 'description',
            'pressions', 'nb_pressions',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_facteur_influence', 'date_ajout', 'date_maj']

    def get_nb_pressions(self, obj):
        return obj.pressions.count()


class FacteurInfluenceListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Facteurs d'Influence."""
    nb_pressions = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = FacteurInfluence
        fields = [
            'id_facteur_influence', 'id_enjeu',
            'libelle', 'description',
            'nb_pressions',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_facteur_influence', 'date_ajout', 'date_maj']

    def get_nb_pressions(self, obj):
        return obj.pressions.count()


class FacteurInfluenceCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Facteur d'Influence."""

    class Meta:
        model = FacteurInfluence
        fields = [
            'id_facteur_influence', 'id_enjeu',
            'libelle', 'description'
        ]
        read_only_fields = ['id_facteur_influence']


# =============================================================================
# Serializers pour les Enjeux
# =============================================================================

class EnjeuListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des Enjeux/FCR."""

    # Labels des nomenclatures
    categorie_label = serializers.CharField(source='id_categorie.label', read_only=True)
    categorie_mnemonique = serializers.CharField(source='id_categorie.mnemonique', read_only=True)
    categorie_fcr_label = serializers.CharField(source='id_categorie_fcr.label', read_only=True)
    importance_label = serializers.CharField(source='id_importance.label', read_only=True)
    plan_nom = serializers.CharField(source='id_pg.nom', read_only=True)

    # Compteurs
    nb_taxons = serializers.SerializerMethodField()
    nb_habitats = serializers.SerializerMethodField()
    nb_geologies = serializers.SerializerMethodField()
    nb_facteurs_influence = serializers.SerializerMethodField()

    class Meta:
        model = Enjeu
        fields = [
            'id_enjeu', 'id_pg', 'plan_nom',
            'id_categorie', 'categorie_label', 'categorie_mnemonique',
            'libelle', 'intitule_court',
            # Champs Enjeu
            'rang', 'categorie_ecologique', 'habitat', 'espece', 'processus',
            # Champs FCR
            'id_categorie_fcr', 'categorie_fcr_label',
            # Optionnels
            'id_importance', 'importance_label',
            # Compteurs
            'nb_taxons', 'nb_habitats', 'nb_geologies', 'nb_facteurs_influence',
            # Audit
            'date_ajout', 'date_maj'
        ]
        read_only_fields = ['id_enjeu', 'date_ajout', 'date_maj']

    def get_nb_taxons(self, obj):
        return obj.taxons.count()

    def get_nb_habitats(self, obj):
        return obj.habitats.count()

    def get_nb_geologies(self, obj):
        return obj.geologies.count()

    def get_nb_facteurs_influence(self, obj):
        return obj.facteurs_influence.count()


class EnjeuDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un Enjeu/FCR."""

    # Labels des nomenclatures
    categorie_label = serializers.CharField(source='id_categorie.label', read_only=True)
    categorie_mnemonique = serializers.CharField(source='id_categorie.mnemonique', read_only=True)
    categorie_fcr_label = serializers.CharField(source='id_categorie_fcr.label', read_only=True)
    importance_label = serializers.CharField(source='id_importance.label', read_only=True)
    plan_nom = serializers.CharField(source='id_pg.nom', read_only=True)

    # Relations taxonomiques (nested)
    taxons = CorEnjeuTaxonSerializer(many=True, read_only=True)
    habitats = CorEnjeuHabitatSerializer(many=True, read_only=True)
    geologies = CorEnjeuGeologieSerializer(many=True, read_only=True)

    # Facteurs d'influence (nested)
    facteurs_influence = FacteurInfluenceSerializer(many=True, read_only=True)
    nb_facteurs_influence = serializers.SerializerMethodField()

    # OLT (nested, avec état actuel inclus)
    objectifs_long_terme = ObjectifLongTermeSerializer(many=True, read_only=True)
    nb_olt = serializers.SerializerMethodField()

    # OO (nested, avec résultats attendus inclus)
    objectifs_operationnels = ObjectifOperationnelSerializer(many=True, read_only=True)
    nb_oo = serializers.SerializerMethodField()

    # Créateur
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = Enjeu
        fields = [
            'id_enjeu', 'id_pg', 'plan_nom',
            'id_categorie', 'categorie_label', 'categorie_mnemonique',
            'libelle', 'intitule_court', 'description',
            # Champs Enjeu
            'rang', 'categorie_ecologique', 'habitat', 'espece', 'processus', 'etat_enjeu',
            # Champs FCR
            'id_categorie_fcr', 'categorie_fcr_label',
            # Optionnels
            'id_importance', 'importance_label', 'geom',
            # Relations
            'taxons', 'habitats', 'geologies',
            # Facteurs d'influence
            'facteurs_influence', 'nb_facteurs_influence',
            # OLT (avec état actuel inclus)
            'objectifs_long_terme', 'nb_olt',
            # OO (avec résultats attendus inclus)
            'objectifs_operationnels', 'nb_oo',
            # Audit
            'date_ajout', 'date_maj', 'id_utilisateur_ajout', 'createur_nom'
        ]
        read_only_fields = ['id_enjeu', 'date_ajout', 'date_maj', 'id_utilisateur_ajout']

    def get_nb_facteurs_influence(self, obj):
        return obj.facteurs_influence.count()

    def get_nb_olt(self, obj):
        return obj.objectifs_long_terme.count()

    def get_nb_oo(self, obj):
        return obj.objectifs_operationnels.count()


class EnjeuCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Enjeu/FCR."""

    # IDs pour les relations taxonomiques (write-only)
    taxon_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list
    )
    habitat_ids = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        default=list
    )
    geologie_ids = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        default=list
    )

    # Données complètes des taxons/habitats (optionnel, pour dénormalisation)
    taxons_data = serializers.ListField(
        child=TaxonRefSerializer(),
        write_only=True,
        required=False,
        default=list
    )
    habitats_data = serializers.ListField(
        child=HabitatRefSerializer(),
        write_only=True,
        required=False,
        default=list
    )
    geologies_data = serializers.ListField(
        child=GeologieRefSerializer(),
        write_only=True,
        required=False,
        default=list
    )

    class Meta:
        model = Enjeu
        fields = [
            'id_enjeu', 'id_pg', 'id_categorie',
            'libelle', 'intitule_court', 'description',
            # Champs Enjeu
            'rang', 'categorie_ecologique', 'habitat', 'espece', 'processus', 'etat_enjeu',
            # Champs FCR
            'id_categorie_fcr',
            # Optionnels
            'id_importance', 'geom',
            # Relations (write-only)
            'taxon_ids', 'habitat_ids', 'geologie_ids',
            'taxons_data', 'habitats_data', 'geologies_data'
        ]
        read_only_fields = ['id_enjeu']

    def validate(self, attrs):
        """Validation métier selon le type (Enjeu ou FCR)."""
        id_categorie = attrs.get('id_categorie')

        if id_categorie:
            mnemonique = id_categorie.mnemonique if hasattr(id_categorie, 'mnemonique') else None

            if mnemonique == 'ENJEU':
                # Pour un Enjeu, la priorité est requise
                if not attrs.get('rang'):
                    attrs['rang'] = 1  # Valeur par défaut

            elif mnemonique == 'FCR':
                # Pour un FCR, la catégorie FCR est recommandée
                # On ne force pas la validation pour permettre la flexibilité
                pass

        return attrs

    def create(self, validated_data):
        """Créer un enjeu avec ses relations taxonomiques."""
        # Extraire les IDs et données des relations
        taxon_ids = validated_data.pop('taxon_ids', [])
        habitat_ids = validated_data.pop('habitat_ids', [])
        geologie_ids = validated_data.pop('geologie_ids', [])
        taxons_data = validated_data.pop('taxons_data', [])
        habitats_data = validated_data.pop('habitats_data', [])
        geologies_data = validated_data.pop('geologies_data', [])

        # Créer l'enjeu
        enjeu = Enjeu.objects.create(**validated_data)

        # Créer les relations taxonomiques
        self._create_taxon_relations(enjeu, taxon_ids, taxons_data)
        self._create_habitat_relations(enjeu, habitat_ids, habitats_data)
        self._create_geologie_relations(enjeu, geologie_ids, geologies_data)

        return enjeu

    def update(self, instance, validated_data):
        """Mettre à jour un enjeu avec ses relations taxonomiques."""
        # Extraire les IDs et données des relations
        taxon_ids = validated_data.pop('taxon_ids', None)
        habitat_ids = validated_data.pop('habitat_ids', None)
        geologie_ids = validated_data.pop('geologie_ids', None)
        taxons_data = validated_data.pop('taxons_data', None)
        habitats_data = validated_data.pop('habitats_data', None)
        geologies_data = validated_data.pop('geologies_data', None)

        # Mettre à jour les champs de l'enjeu
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Mettre à jour les relations si fournies
        if taxon_ids is not None:
            instance.taxons.all().delete()
            self._create_taxon_relations(instance, taxon_ids, taxons_data or [])

        if habitat_ids is not None:
            instance.habitats.all().delete()
            self._create_habitat_relations(instance, habitat_ids, habitats_data or [])

        if geologie_ids is not None:
            instance.geologies.all().delete()
            self._create_geologie_relations(instance, geologie_ids, geologies_data or [])

        return instance

    def _create_taxon_relations(self, enjeu, taxon_ids, taxons_data):
        """Créer les relations avec les taxons."""
        # Créer un dictionnaire des données pour lookup rapide
        data_dict = {t['cd_nom']: t for t in taxons_data}

        for cd_nom in taxon_ids:
            data = data_dict.get(cd_nom, {})
            CorEnjeuTaxon.objects.create(
                id_enjeu=enjeu,
                cd_nom=cd_nom,
                nom_complet=data.get('nom_complet', ''),
                nom_vern=data.get('nom_vern', '')
            )

    def _create_habitat_relations(self, enjeu, habitat_ids, habitats_data):
        """Créer les relations avec les habitats."""
        data_dict = {h['cd_hab']: h for h in habitats_data}

        for cd_hab in habitat_ids:
            data = data_dict.get(cd_hab, {})
            CorEnjeuHabitat.objects.create(
                id_enjeu=enjeu,
                cd_hab=cd_hab,
                lb_hab_fr=data.get('lb_hab_fr', '')
            )

    def _create_geologie_relations(self, enjeu, geologie_ids, geologies_data):
        """Créer les relations avec les éléments géologiques."""
        data_dict = {g['id_inpg']: g for g in geologies_data}

        for id_inpg in geologie_ids:
            data = data_dict.get(id_inpg, {})
            CorEnjeuGeologie.objects.create(
                id_enjeu=enjeu,
                id_inpg=id_inpg,
                nom=data.get('nom', '')
            )


# =============================================================================
# Serializers pour les Responsabilités
# =============================================================================

class ResponsabiliteListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des Responsabilités."""

    # Labels des nomenclatures
    type_label = serializers.CharField(source='id_type_responsabilite.label', read_only=True)
    niveau_label = serializers.CharField(source='id_niveau_responsabilite.label', read_only=True)
    site_nom = serializers.CharField(source='id_site.nom_site', read_only=True)

    # Compteurs
    nb_taxons = serializers.SerializerMethodField()
    nb_habitats = serializers.SerializerMethodField()
    nb_enjeux_lies = serializers.SerializerMethodField()

    class Meta:
        model = Responsabilite
        fields = [
            'id_responsabilite', 'id_site', 'site_nom',
            'id_type_responsabilite', 'type_label',
            'id_niveau_responsabilite', 'niveau_label',
            'description',
            'nb_taxons', 'nb_habitats', 'nb_enjeux_lies',
            'date_ajout', 'date_maj'
        ]
        read_only_fields = ['id_responsabilite', 'date_ajout', 'date_maj']

    def get_nb_taxons(self, obj):
        return obj.taxons.count()

    def get_nb_habitats(self, obj):
        return obj.habitats.count()

    def get_nb_enjeux_lies(self, obj):
        return obj.enjeux_lies.count()


class ResponsabiliteDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une Responsabilité."""

    # Labels des nomenclatures
    type_label = serializers.CharField(source='id_type_responsabilite.label', read_only=True)
    niveau_label = serializers.CharField(source='id_niveau_responsabilite.label', read_only=True)
    site_nom = serializers.CharField(source='id_site.nom_site', read_only=True)

    # Relations taxonomiques (nested)
    taxons = CorResponsabiliteTaxonSerializer(many=True, read_only=True)
    habitats = CorResponsabiliteHabitatSerializer(many=True, read_only=True)
    geologies = CorResponsabiliteGeologieSerializer(many=True, read_only=True)

    # Enjeux liés
    enjeux_lies = serializers.SerializerMethodField()

    # Créateur
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = Responsabilite
        fields = [
            'id_responsabilite', 'id_site', 'site_nom',
            'id_type_responsabilite', 'type_label',
            'id_niveau_responsabilite', 'niveau_label',
            'description',
            'taxons', 'habitats', 'geologies', 'enjeux_lies',
            'date_ajout', 'date_maj', 'id_utilisateur_ajout', 'createur_nom'
        ]
        read_only_fields = ['id_responsabilite', 'date_ajout', 'date_maj', 'id_utilisateur_ajout']

    def get_enjeux_lies(self, obj):
        """Retourner les enjeux liés."""
        return [
            {'id_enjeu': cor.id_enjeu.id_enjeu, 'libelle': cor.id_enjeu.libelle}
            for cor in obj.enjeux_lies.select_related('id_enjeu')
        ]


class ResponsabiliteCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une Responsabilité."""

    # IDs pour les relations (write-only)
    taxon_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list
    )
    habitat_ids = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        default=list
    )
    geologie_ids = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        default=list
    )
    enjeu_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list
    )

    # Données complètes (optionnel)
    taxons_data = serializers.ListField(
        child=TaxonRefSerializer(),
        write_only=True,
        required=False,
        default=list
    )
    habitats_data = serializers.ListField(
        child=HabitatRefSerializer(),
        write_only=True,
        required=False,
        default=list
    )
    geologies_data = serializers.ListField(
        child=GeologieRefSerializer(),
        write_only=True,
        required=False,
        default=list
    )

    class Meta:
        model = Responsabilite
        fields = [
            'id_responsabilite', 'id_site',
            'id_type_responsabilite', 'id_niveau_responsabilite',
            'description',
            'taxon_ids', 'habitat_ids', 'geologie_ids', 'enjeu_ids',
            'taxons_data', 'habitats_data', 'geologies_data'
        ]
        read_only_fields = ['id_responsabilite']

    def create(self, validated_data):
        """Créer une responsabilité avec ses relations."""
        # Extraire les IDs et données des relations
        taxon_ids = validated_data.pop('taxon_ids', [])
        habitat_ids = validated_data.pop('habitat_ids', [])
        geologie_ids = validated_data.pop('geologie_ids', [])
        enjeu_ids = validated_data.pop('enjeu_ids', [])
        taxons_data = validated_data.pop('taxons_data', [])
        habitats_data = validated_data.pop('habitats_data', [])
        geologies_data = validated_data.pop('geologies_data', [])

        # Créer la responsabilité
        responsabilite = Responsabilite.objects.create(**validated_data)

        # Créer les relations
        self._create_taxon_relations(responsabilite, taxon_ids, taxons_data)
        self._create_habitat_relations(responsabilite, habitat_ids, habitats_data)
        self._create_geologie_relations(responsabilite, geologie_ids, geologies_data)
        self._create_enjeu_relations(responsabilite, enjeu_ids)

        return responsabilite

    def update(self, instance, validated_data):
        """Mettre à jour une responsabilité avec ses relations."""
        taxon_ids = validated_data.pop('taxon_ids', None)
        habitat_ids = validated_data.pop('habitat_ids', None)
        geologie_ids = validated_data.pop('geologie_ids', None)
        enjeu_ids = validated_data.pop('enjeu_ids', None)
        taxons_data = validated_data.pop('taxons_data', None)
        habitats_data = validated_data.pop('habitats_data', None)
        geologies_data = validated_data.pop('geologies_data', None)

        # Mettre à jour les champs
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Mettre à jour les relations si fournies
        if taxon_ids is not None:
            instance.taxons.all().delete()
            self._create_taxon_relations(instance, taxon_ids, taxons_data or [])

        if habitat_ids is not None:
            instance.habitats.all().delete()
            self._create_habitat_relations(instance, habitat_ids, habitats_data or [])

        if geologie_ids is not None:
            instance.geologies.all().delete()
            self._create_geologie_relations(instance, geologie_ids, geologies_data or [])

        if enjeu_ids is not None:
            instance.enjeux_lies.all().delete()
            self._create_enjeu_relations(instance, enjeu_ids)

        return instance

    def _create_taxon_relations(self, responsabilite, taxon_ids, taxons_data):
        """Créer les relations avec les taxons."""
        data_dict = {t['cd_nom']: t for t in taxons_data}

        for cd_nom in taxon_ids:
            data = data_dict.get(cd_nom, {})
            CorResponsabiliteTaxon.objects.create(
                id_responsabilite=responsabilite,
                cd_nom=cd_nom,
                nom_complet=data.get('nom_complet', ''),
                nom_vern=data.get('nom_vern', '')
            )

    def _create_habitat_relations(self, responsabilite, habitat_ids, habitats_data):
        """Créer les relations avec les habitats."""
        data_dict = {h['cd_hab']: h for h in habitats_data}

        for cd_hab in habitat_ids:
            data = data_dict.get(cd_hab, {})
            CorResponsabiliteHabitat.objects.create(
                id_responsabilite=responsabilite,
                cd_hab=cd_hab,
                lb_hab_fr=data.get('lb_hab_fr', '')
            )

    def _create_geologie_relations(self, responsabilite, geologie_ids, geologies_data):
        """Créer les relations avec les éléments géologiques."""
        data_dict = {g['id_inpg']: g for g in geologies_data}

        for id_inpg in geologie_ids:
            data = data_dict.get(id_inpg, {})
            CorResponsabiliteGeologie.objects.create(
                id_responsabilite=responsabilite,
                id_inpg=id_inpg,
                nom=data.get('nom', '')
            )

    def _create_enjeu_relations(self, responsabilite, enjeu_ids):
        """Créer les relations avec les enjeux."""
        for enjeu_id in enjeu_ids:
            CorResponsabiliteEnjeu.objects.create(
                id_responsabilite=responsabilite,
                id_enjeu_id=enjeu_id
            )
