"""
Serializers pour l'API REST Enjeux, FCR et Responsabilités.
"""
from rest_framework import serializers
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Max
from django.utils.translation import gettext_lazy as _

from .models_enjeux import (
    Enjeu, FacteurInfluence, Pression, Responsabilite,
    ObjectifLongTerme, NiveauExigence,
    ObjectifOperationnel, ResultatAttendu,
    CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie, CorEnjeuObjetGeologique,
    CorEnjeuFichier, CorFacteurEnjeu,
    CorResponsabiliteTaxon, CorResponsabiliteHabitat, CorResponsabiliteGeologie,
    CorResponsabiliteEnjeu
)
from apps.core.models import Nomenclature


def _prefetched_count(obj, attr):
    """#263 — Compte les objets liés sans déclencher de requête COUNT si le
    related manager a déjà été prefetché. Évite N+1 sur les `nb_*` exposés
    par les serializers imbriqués dans `by-plan`."""
    cache = getattr(obj, '_prefetched_objects_cache', None)
    if cache is not None and attr in cache:
        return len(cache[attr])
    return getattr(obj, attr).count()


def _prefetched_list(obj, attr):
    """#263 — Récupère la liste des objets liés depuis le cache prefetch
    si disponible, sinon depuis le manager. Sert à `pression_ids` etc."""
    cache = getattr(obj, '_prefetched_objects_cache', None)
    if cache is not None and attr in cache:
        return list(cache[attr])
    return list(getattr(obj, attr).all())


# =============================================================================
# Serializers pour les relations taxonomiques
# =============================================================================

class TaxonRefSerializer(serializers.Serializer):
    """Serializer pour les références taxonomiques."""
    cd_nom = serializers.IntegerField()
    nom_complet = serializers.CharField(max_length=500, required=False, allow_blank=True)
    nom_vern = serializers.CharField(max_length=255, required=False, allow_blank=True)


class HabitatRefSerializer(serializers.Serializer):
    """Serializer pour les références habitats.

    #368 — `cd_hab` est optionnel : un habitat « libre » (hors HabRef, ex.
    Outre-mer) n'a pas de code, seul `lb_hab_fr` est renseigné.
    """
    cd_hab = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    lb_hab_fr = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, attrs):
        if not (attrs.get('cd_hab') or '').strip() and not (attrs.get('lb_hab_fr') or '').strip():
            raise serializers.ValidationError(
                _("Un habitat doit avoir un code HabRef ou un libellé saisi.")
            )
        return attrs


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


class ObjetGeologiqueRefSerializer(serializers.Serializer):
    """#237 — Payload d'un objet géologique sélectionné : référence la
    nomenclature TYPE_OBJET_GEOLOGIQUE (par id), + précision libre pour « Autre »."""
    id_objet_geologique = serializers.IntegerField()
    precision = serializers.CharField(max_length=255, required=False, allow_blank=True)


class CorEnjeuObjetGeologiqueSerializer(serializers.ModelSerializer):
    """#237 — Serializer (lecture) d'une relation Enjeu-Objet géologique.
    Expose la nomenclature (code + libellé dénormalisés pour l'affichage)."""
    code = serializers.CharField(source='id_objet_geologique.cd_nomenclature', read_only=True)
    libelle = serializers.CharField(source='id_objet_geologique.label', read_only=True)

    class Meta:
        model = CorEnjeuObjetGeologique
        fields = ['id', 'id_objet_geologique', 'code', 'libelle', 'precision']
        read_only_fields = ['id', 'code', 'libelle']


class CorEnjeuFichierSerializer(serializers.ModelSerializer):
    """#237 — Serializer pour les documents (numériques/papier) d'un enjeu."""

    fichier = serializers.FileField(write_only=True, required=False)
    file_size_human = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = CorEnjeuFichier
        fields = [
            'id', 'id_enjeu', 'support', 'nom_fichier', 'fichier', 'url',
            'titre', 'description', 'taille_fichier', 'file_size_human',
            'extension', 'ordre_affichage', 'date_upload',
        ]
        read_only_fields = [
            'id', 'nom_fichier', 'taille_fichier', 'extension', 'date_upload',
        ]

    def get_file_size_human(self, obj):
        return obj.get_file_size_human()

    def get_url(self, obj):
        if obj.chemin_fichier:
            return f"/media/enjeux/{obj.id_enjeu_id}/{obj.nom_fichier}"
        return None

    def validate(self, attrs):
        """Un document numérique exige un fichier (à la création) ;
        un document papier exige un titre/référence."""
        support = attrs.get('support') or (self.instance.support if self.instance else 'numerique')
        if support == 'papier':
            titre = attrs.get('titre') if 'titre' in attrs else (self.instance.titre if self.instance else '')
            if not (titre or '').strip():
                raise serializers.ValidationError(
                    {'titre': _("Une référence (titre) est requise pour un document papier.")}
                )
        elif self.instance is None and not attrs.get('fichier'):
            raise serializers.ValidationError(
                {'fichier': _("Un fichier est requis pour un document numérique.")}
            )
        return attrs

    def create(self, validated_data):
        fichier = validated_data.pop('fichier', None)
        instance = super().create(validated_data)
        if fichier:
            instance.handle_file_upload(fichier)
        return instance


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
            'libelle', 'description', 'ordre',
            'indicateurs', 'nb_indicateurs',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_ne', 'date_ajout', 'date_maj']

    def get_nb_indicateurs(self, obj):
        return _prefetched_count(obj, 'indicateurs')


class NiveauExigenceCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Niveau d'Exigence."""

    class Meta:
        model = NiveauExigence
        fields = [
            'id_ne', 'id_olt',
            'libelle', 'description', 'ordre'
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
            'libelle', 'description', 'ordre',
            'indicateurs', 'nb_indicateurs',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_ra', 'date_ajout', 'date_maj']

    def get_nb_indicateurs(self, obj):
        return _prefetched_count(obj, 'indicateurs')


class ResultatAttenduCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Résultat Attendu."""

    class Meta:
        model = ResultatAttendu
        fields = [
            'id_ra', 'id_oo',
            'libelle', 'description', 'ordre'
        ]
        read_only_fields = ['id_ra']


# =============================================================================
# Serializers pour les Objectifs Opérationnels
# =============================================================================

class PressionLightSerializer(serializers.Serializer):
    """Serializer léger pour les pressions liées à un OO (M2M)."""
    id_pression = serializers.IntegerField()
    libelle = serializers.CharField()
    facteur_influence_libelle = serializers.SerializerMethodField()

    def get_facteur_influence_libelle(self, obj):
        try:
            return obj.id_facteur_influence.libelle
        except AttributeError:
            return None


def _oo_shared_enjeu_ids(obj):
    """#552 — IDs distincts des enjeux sous lesquels cet OO apparaît.

    Un OO est partagé quand il est rattaché (via ses pressions → facteur →
    enjeux) à plus d'un enjeu ; on ajoute aussi le rattachement direct FCR
    (``id_enjeu``). Utilisé pour le bandeau « élément lié » (partagé si > 1).
    """
    ids = set()
    for p in _prefetched_list(obj, 'pressions'):
        fi = getattr(p, 'id_facteur_influence', None)
        if fi is not None:
            ids.update(e.pk for e in fi.enjeux.all())
    if getattr(obj, 'id_enjeu_id', None):
        ids.add(obj.id_enjeu_id)
    return sorted(ids)


class ObjectifOperationnelSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un Objectif Opérationnel avec résultats attendus imbriqués."""
    resultats_attendus = ResultatAttenduSerializer(many=True, read_only=True)
    nb_resultats_attendus = serializers.SerializerMethodField()
    pressions = PressionLightSerializer(many=True, read_only=True)
    pression_ids = serializers.SerializerMethodField()
    shared_enjeu_ids = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = ObjectifOperationnel
        fields = [
            'id_oo', 'pressions', 'pression_ids', 'id_enjeu', 'shared_enjeu_ids',
            'libelle', 'description', 'ordre', 'numero_manuel',
            'resultats_attendus', 'nb_resultats_attendus',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_oo', 'date_ajout', 'date_maj']

    def get_nb_resultats_attendus(self, obj):
        return _prefetched_count(obj, 'resultats_attendus')

    def get_pression_ids(self, obj):
        return [p.pk for p in _prefetched_list(obj, 'pressions')]

    def get_shared_enjeu_ids(self, obj):
        return _oo_shared_enjeu_ids(obj)


class ObjectifOperationnelListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Objectifs Opérationnels."""
    nb_resultats_attendus = serializers.SerializerMethodField()
    pressions = PressionLightSerializer(many=True, read_only=True)
    pression_ids = serializers.SerializerMethodField()
    shared_enjeu_ids = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = ObjectifOperationnel
        fields = [
            'id_oo', 'pressions', 'pression_ids', 'id_enjeu', 'shared_enjeu_ids',
            'libelle', 'description', 'ordre', 'numero_manuel',
            'nb_resultats_attendus',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_oo', 'date_ajout', 'date_maj']

    def get_nb_resultats_attendus(self, obj):
        return _prefetched_count(obj, 'resultats_attendus')

    def get_pression_ids(self, obj):
        return [p.pk for p in _prefetched_list(obj, 'pressions')]

    def get_shared_enjeu_ids(self, obj):
        return _oo_shared_enjeu_ids(obj)


class ObjectifOperationnelCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Objectif Opérationnel.

    Un OO est rattaché soit à des pressions (cas Enjeu), soit directement à un
    enjeu/FCR via ``id_enjeu`` (cas FCR sans pression, #337).
    """
    pression_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        help_text="Liste des IDs de pressions à lier"
    )

    class Meta:
        model = ObjectifOperationnel
        fields = [
            'id_oo', 'pression_ids', 'id_enjeu',
            'libelle', 'description', 'ordre', 'numero_manuel'
        ]
        read_only_fields = ['id_oo']

    def validate(self, attrs):
        """Contrôle d'intégrité du rattachement d'un OO selon la catégorie du parent.

        Le mode de rattachement d'un OO dépend de la nature de l'enjeu parent :

        - Enjeu « classique » : la chaîne Enjeu → Facteur d'influence → Pression
          est STRUCTURANTE. Un OO descend obligatoirement d'au moins une pression
          (``pression_ids``) et n'est JAMAIS rattaché directement à l'enjeu.

        - FCR (Facteur Clé de Réussite) : la chaîne facteur/pression est
          FACULTATIVE et purement DESCRIPTIVE. Un OO de FCR est TOUJOURS rattaché
          directement au FCR via ``id_enjeu`` (sans pression), même si le FCR
          porte par ailleurs des facteurs/pressions.

        On verrouille donc les croisements interdits pour garantir l'intégrité du
        modèle (cf. évolution FCR / #337) :
          1. un OO doit être ancré quelque part (pression OU enjeu direct) ;
          2. le rattachement direct (``id_enjeu``) est réservé aux FCR ;
          3. un OO de FCR ne peut pas être rattaché à une pression.

        Ces règles ne s'appliquent qu'à la création : en modification, le
        rattachement initial n'est pas remis en cause.
        """
        if self.instance is not None:
            return attrs

        pression_ids = attrs.get('pression_ids') or []
        enjeu = attrs.get('id_enjeu')  # instance Enjeu (FK résolue par DRF) ou None

        # (1) Un OO doit être ancré : au moins une pression OU un enjeu direct.
        if not pression_ids and not enjeu:
            raise serializers.ValidationError(
                _("Un objectif opérationnel doit être rattaché à au moins une pression ou à un FCR.")
            )

        # (2) Rattachement direct via id_enjeu → réservé aux FCR.
        if enjeu is not None:
            if not enjeu.is_fcr():
                raise serializers.ValidationError(
                    _("Le rattachement direct d'un objectif opérationnel est réservé aux FCR. "
                      "Pour un enjeu classique, rattachez l'objectif à une ou plusieurs pressions.")
                )
            # #474 — un OO de FCR est rattaché AU FCR (id_enjeu), et PEUT EN PLUS être
            # lié, de façon facultative, à une ou plusieurs pressions (issues des
            # enjeux écologiques du plan). On n'interdit donc plus la présence
            # simultanée de `id_enjeu` (FCR) et de `pression_ids` : les deux
            # rattachements coexistent (FK directe + M2M descriptive).

        # (3) Rattachement par pressions → l'enjeu parent (remonté via la chaîne
        #     Pression → Facteur → Enjeu) ne doit PAS être un FCR.
        else:  # pression_ids non vide (sinon bloqué en (1))
            parent_pression = (
                Pression.objects
                .filter(pk__in=pression_ids)
                .select_related('id_facteur_influence')
                .prefetch_related('id_facteur_influence__enjeux__id_categorie')
                .first()
            )
            if parent_pression is not None:
                # #552 — le facteur peut être partagé entre plusieurs enjeux ;
                # une pression ne doit remonter à AUCUN FCR (les OO de FCR se
                # rattachent directement au FCR, cf. #337).
                facteur = parent_pression.id_facteur_influence
                if any(e.is_fcr() for e in facteur.enjeux.all()):
                    raise serializers.ValidationError(
                        _("Un objectif opérationnel de FCR doit être rattaché directement au FCR, "
                          "pas à une pression.")
                    )

        return attrs

    def create(self, validated_data):
        pression_ids = validated_data.pop('pression_ids', [])
        oo = super().create(validated_data)
        if pression_ids:
            oo.pressions.set(pression_ids)
        return oo

    def update(self, instance, validated_data):
        pression_ids = validated_data.pop('pression_ids', None)
        oo = super().update(instance, validated_data)
        if pression_ids is not None:
            oo.pressions.set(pression_ids)
        return oo


# =============================================================================
# Serializers pour les Objectifs à Long Terme
# =============================================================================

class ObjectifLongTermeSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un Objectif à Long Terme avec niveaux d'exigence imbriqués."""
    niveaux_exigence = NiveauExigenceSerializer(many=True, read_only=True)
    nb_niveaux_exigence = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = ObjectifLongTerme
        fields = [
            'id_olt', 'id_enjeu',
            'libelle', 'description', 'ordre', 'numero_manuel',
            'niveaux_exigence', 'nb_niveaux_exigence',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_olt', 'date_ajout', 'date_maj']

    def get_nb_niveaux_exigence(self, obj):
        return _prefetched_count(obj, 'niveaux_exigence')


class ObjectifLongTermeListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Objectifs à Long Terme."""
    nb_niveaux_exigence = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = ObjectifLongTerme
        fields = [
            'id_olt', 'id_enjeu',
            'libelle', 'description', 'ordre', 'numero_manuel',
            'nb_niveaux_exigence',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_olt', 'date_ajout', 'date_maj']

    def get_nb_niveaux_exigence(self, obj):
        return _prefetched_count(obj, 'niveaux_exigence')


class ObjectifLongTermeCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Objectif à Long Terme."""

    class Meta:
        model = ObjectifLongTerme
        fields = [
            'id_olt', 'id_enjeu',
            'libelle', 'description', 'ordre', 'numero_manuel'
        ]
        read_only_fields = ['id_olt']


# =============================================================================
# Serializers pour les Pressions
# =============================================================================

class PressionSerializer(serializers.ModelSerializer):
    """Serializer pour la lecture d'une Pression avec OO imbriqués."""
    objectifs_operationnels = ObjectifOperationnelSerializer(many=True, read_only=True)
    nb_objectifs_operationnels = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    pressref_code = serializers.CharField(source='id_type_pression.cd_nomenclature', read_only=True, default=None)
    pressref_label = serializers.CharField(source='id_type_pression.label', read_only=True, default=None)
    pressref_definition = serializers.CharField(source='id_type_pression.definition', read_only=True, default=None)

    class Meta:
        model = Pression
        fields = [
            'id_pression', 'id_facteur_influence', 'id_pressref',
            'id_type_pression', 'pressref_code', 'pressref_label', 'pressref_definition',
            'libelle', 'description', 'ordre',
            'objectifs_operationnels', 'nb_objectifs_operationnels',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_pression', 'date_ajout', 'date_maj']

    def get_nb_objectifs_operationnels(self, obj):
        return _prefetched_count(obj, 'objectifs_operationnels')


class PressionCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une Pression."""

    class Meta:
        model = Pression
        fields = [
            'id_pression', 'id_facteur_influence', 'id_pressref',
            'id_type_pression', 'libelle', 'description', 'ordre'
        ]
        read_only_fields = ['id_pression']


# =============================================================================
# Serializers pour les Facteurs d'Influence
# =============================================================================

def _facteur_enjeu_ids(obj):
    """#552 — IDs des enjeux auxquels ce facteur est rattaché (partagé si > 1)."""
    return [e.pk for e in obj.enjeux.all()]


def _facteur_ordre(obj):
    """#552 — Ordre du facteur DANS l'enjeu courant.

    Injecté par le serializer parent (``_enjeu_ordre``) quand le facteur est
    rendu dans le contexte d'un enjeu ; 0 par défaut hors contexte.
    """
    return getattr(obj, '_enjeu_ordre', 0)


class FacteurInfluenceSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un Facteur d'Influence avec pressions (et OO imbriqués sous pressions)."""
    pressions = PressionSerializer(many=True, read_only=True)
    nb_pressions = serializers.SerializerMethodField()
    enjeu_ids = serializers.SerializerMethodField()
    ordre = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = FacteurInfluence
        fields = [
            'id_facteur_influence', 'enjeu_ids',
            'libelle', 'description', 'ordre',
            'pressions', 'nb_pressions',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_facteur_influence', 'date_ajout', 'date_maj']

    def get_nb_pressions(self, obj):
        return _prefetched_count(obj, 'pressions')

    def get_enjeu_ids(self, obj):
        return _facteur_enjeu_ids(obj)

    def get_ordre(self, obj):
        return _facteur_ordre(obj)


class FacteurInfluenceListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Facteurs d'Influence."""
    nb_pressions = serializers.SerializerMethodField()
    enjeu_ids = serializers.SerializerMethodField()
    ordre = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = FacteurInfluence
        fields = [
            'id_facteur_influence', 'enjeu_ids',
            'libelle', 'description', 'ordre',
            'nb_pressions',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_facteur_influence', 'date_ajout', 'date_maj']

    def get_nb_pressions(self, obj):
        return _prefetched_count(obj, 'pressions')

    def get_enjeu_ids(self, obj):
        return _facteur_enjeu_ids(obj)

    def get_ordre(self, obj):
        return _facteur_ordre(obj)


class FacteurInfluenceCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Facteur d'Influence.

    #552 — Un facteur est rattaché à un enjeu via la table de liaison
    ``CorFacteurEnjeu``. À la création on reçoit ``enjeu_id`` (write-only) et on
    crée la liaison (ordre = dernier de l'enjeu + 1). Le déplacement d'un
    facteur entre enjeux passe par les actions ``link``/``unlink``, pas par un
    ``update`` de ce champ.
    """
    enjeu_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = FacteurInfluence
        fields = [
            'id_facteur_influence', 'enjeu_id',
            'libelle', 'description'
        ]
        read_only_fields = ['id_facteur_influence']

    def validate_enjeu_id(self, value):
        if not Enjeu.objects.filter(pk=value).exists():
            raise serializers.ValidationError(_("L'enjeu indiqué n'existe pas."))
        return value

    def create(self, validated_data):
        enjeu_id = validated_data.pop('enjeu_id', None)
        if enjeu_id is None:
            raise serializers.ValidationError({'enjeu_id': _("Ce champ est requis.")})
        facteur = super().create(validated_data)
        max_ordre = CorFacteurEnjeu.objects.filter(id_enjeu_id=enjeu_id).aggregate(m=Max('ordre'))['m']
        CorFacteurEnjeu.objects.create(
            id_facteur_influence=facteur,
            id_enjeu_id=enjeu_id,
            ordre=(max_ordre + 1) if max_ordre is not None else 0,
        )
        return facteur

    def update(self, instance, validated_data):
        # Le rattachement aux enjeux se gère via link/unlink (#552), pas ici.
        validated_data.pop('enjeu_id', None)
        return super().update(instance, validated_data)


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
            'id_enjeu', 'id_pg', 'plan_nom', 'slug',
            'id_categorie', 'categorie_label', 'categorie_mnemonique',
            'libelle', 'intitule_court', 'ordre', 'numero_manuel',
            # Champs Enjeu
            'rang', 'categorie_ecologique',
            'habitat', 'espece', 'patrimoine_geologique', 'geo_ex_situ', 'geo_in_situ', 'geo_documents', 'geo_autre', 'geo_autre_precision', 'fonctionnalite_ecosysteme', 'autre_ecologique', 'autre_ecologique_precision', 'processus',
            'valeur_paysagere', 'patrimoine_culturel', 'developpement_durable', 'usages', 'valeur_ajoutee', 'autre_socioeco', 'autre_socioeco_precision',
            # Champs FCR
            'id_categorie_fcr', 'categorie_fcr_label',
            # Optionnels
            'id_importance', 'importance_label',
            # Compteurs
            'nb_taxons', 'nb_habitats', 'nb_geologies', 'nb_facteurs_influence',
            # Audit
            'date_ajout', 'date_maj'
        ]
        read_only_fields = ['id_enjeu', 'slug', 'date_ajout', 'date_maj']

    def get_nb_taxons(self, obj):
        return _prefetched_count(obj, 'taxons')

    def get_nb_habitats(self, obj):
        return _prefetched_count(obj, 'habitats')

    def get_nb_geologies(self, obj):
        return _prefetched_count(obj, 'geologies')

    def get_nb_facteurs_influence(self, obj):
        return _prefetched_count(obj, 'facteurs_influence')


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
    # #237 — objets géologiques (typologie Corentin)
    objets_geologiques = CorEnjeuObjetGeologiqueSerializer(many=True, read_only=True)
    # #237 — documents du patrimoine « Documents » (numériques + références papier)
    documents = CorEnjeuFichierSerializer(source='fichiers', many=True, read_only=True)

    # Facteurs d'influence (nested). #552 — un facteur peut être partagé entre
    # plusieurs enjeux ; l'ordre d'affichage est propre à cet enjeu (porté par
    # CorFacteurEnjeu). On sérialise via les lignes de liaison ``cor_facteurs``
    # (préchargées, ordonnées) en injectant l'ordre contextuel sur chaque facteur.
    facteurs_influence = serializers.SerializerMethodField()
    nb_facteurs_influence = serializers.SerializerMethodField()

    # Objectifs à long terme (nested, avec NE inclus)
    objectifs_long_terme = ObjectifLongTermeSerializer(many=True, read_only=True)
    nb_objectifs_long_terme = serializers.SerializerMethodField()

    # #337 — Objectifs opérationnels rattachés directement à l'enjeu/FCR
    # (sans pression). Pour un Enjeu classique, les OO transitent par les
    # pressions ; pour un FCR, ils sont exposés ici.
    objectifs_operationnels = ObjectifOperationnelSerializer(
        source='objectifs_operationnels_directs', many=True, read_only=True
    )
    nb_objectifs_operationnels = serializers.SerializerMethodField()

    # Créateur
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = Enjeu
        fields = [
            'id_enjeu', 'id_pg', 'plan_nom', 'slug',
            'id_categorie', 'categorie_label', 'categorie_mnemonique',
            'libelle', 'intitule_court', 'description', 'ordre', 'numero_manuel',
            # Champs Enjeu
            'rang', 'categorie_ecologique',
            'habitat', 'espece', 'patrimoine_geologique', 'geo_ex_situ', 'geo_in_situ', 'geo_documents', 'geo_autre', 'geo_autre_precision', 'fonctionnalite_ecosysteme', 'autre_ecologique', 'autre_ecologique_precision', 'processus',
            'valeur_paysagere', 'patrimoine_culturel', 'developpement_durable', 'usages', 'valeur_ajoutee', 'autre_socioeco', 'autre_socioeco_precision',
            'etat_enjeu',
            # Champs FCR
            'id_categorie_fcr', 'categorie_fcr_label',
            # Optionnels
            'id_importance', 'importance_label', 'geom',
            # Relations
            'taxons', 'habitats', 'geologies', 'objets_geologiques', 'documents',
            # Facteurs d'influence
            'facteurs_influence', 'nb_facteurs_influence',
            # Objectifs à long terme (avec NE inclus)
            'objectifs_long_terme', 'nb_objectifs_long_terme',
            # #337 — OO rattachés directement (FCR)
            'objectifs_operationnels', 'nb_objectifs_operationnels',
            # Audit
            'date_ajout', 'date_maj', 'id_utilisateur_ajout', 'createur_nom'
        ]
        read_only_fields = ['id_enjeu', 'slug', 'date_ajout', 'date_maj', 'id_utilisateur_ajout']

    def get_facteurs_influence(self, obj):
        """#552 — Sérialise les facteurs de cet enjeu via les lignes de liaison
        ``cor_facteurs`` (préchargées + ordonnées par ``ordre``), en injectant
        l'ordre contextuel de l'enjeu sur chaque facteur. Le format de sortie
        est identique à l'ancien ``FacteurInfluenceSerializer(many=True)``.
        """
        facteurs = []
        for cor in obj.cor_facteurs.all():
            fi = cor.id_facteur_influence
            fi._enjeu_ordre = cor.ordre
            facteurs.append(fi)
        return FacteurInfluenceSerializer(facteurs, many=True, context=self.context).data

    def get_nb_facteurs_influence(self, obj):
        return len(obj.cor_facteurs.all())

    def get_nb_objectifs_long_terme(self, obj):
        return _prefetched_count(obj, 'objectifs_long_terme')

    def get_nb_objectifs_operationnels(self, obj):
        return _prefetched_count(obj, 'objectifs_operationnels_directs')


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
    # #237 — objets géologiques sélectionnés (code + libellé de la typologie)
    objets_geologiques_data = serializers.ListField(
        child=ObjetGeologiqueRefSerializer(),
        write_only=True,
        required=False,
        default=list
    )

    class Meta:
        model = Enjeu
        fields = [
            'id_enjeu', 'id_pg', 'slug', 'id_categorie',
            'libelle', 'intitule_court', 'description', 'ordre', 'numero_manuel',
            # Champs Enjeu
            'rang', 'categorie_ecologique',
            'habitat', 'espece', 'patrimoine_geologique', 'geo_ex_situ', 'geo_in_situ', 'geo_documents', 'geo_autre', 'geo_autre_precision', 'fonctionnalite_ecosysteme', 'autre_ecologique', 'autre_ecologique_precision', 'processus',
            'valeur_paysagere', 'patrimoine_culturel', 'developpement_durable', 'usages', 'valeur_ajoutee', 'autre_socioeco', 'autre_socioeco_precision',
            'etat_enjeu',
            # Champs FCR
            'id_categorie_fcr',
            # Optionnels
            'id_importance', 'geom',
            # Relations (write-only)
            'taxon_ids', 'habitat_ids', 'geologie_ids',
            'taxons_data', 'habitats_data', 'geologies_data',
            'objets_geologiques_data',
        ]
        read_only_fields = ['id_enjeu', 'slug']

    def validate(self, attrs):
        """Validation métier selon le type (Enjeu ou FCR)."""
        id_categorie = attrs.get('id_categorie')
        id_categorie_fcr = attrs.get('id_categorie_fcr')

        if id_categorie:
            mnemonique = id_categorie.mnemonique if hasattr(id_categorie, 'mnemonique') else None

            if mnemonique == 'ENJEU':
                # #441 : la priorité d'un enjeu est facultative. Beaucoup de PG
                # (CEN notamment) ne priorisent pas leurs enjeux ; on ne force
                # donc plus la valeur 1 par défaut. Une valeur absente/null
                # signifie « priorité non définie ».
                pass

            elif mnemonique == 'FCR':
                # Pour un FCR, la catégorie FCR est recommandée
                # On ne force pas la validation pour permettre la flexibilité
                pass

        # Si id_categorie_fcr est fourni, s'assurer que id_categorie est bien FCR
        if id_categorie_fcr and id_categorie:
            mnemonique = id_categorie.mnemonique if hasattr(id_categorie, 'mnemonique') else None
            if mnemonique != 'FCR':
                # Corriger automatiquement : chercher la nomenclature FCR
                from apps.core.models import Nomenclature
                try:
                    fcr_nomenclature = Nomenclature.objects.get(
                        id_type__mnemonique='CATEGORIE_ENJEU',
                        mnemonique='FCR'
                    )
                    attrs['id_categorie'] = fcr_nomenclature
                except Nomenclature.DoesNotExist:
                    raise serializers.ValidationError(
                        {"id_categorie": _("Catégorie FCR introuvable dans les nomenclatures.")}
                    )

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
        objets_geologiques_data = validated_data.pop('objets_geologiques_data', [])

        # Si les IDs ne sont pas fournis, les extraire depuis les données
        if not taxon_ids and taxons_data:
            taxon_ids = [t['cd_nom'] for t in taxons_data]
        if not habitat_ids and habitats_data:
            # #368 — un habitat libre n'a pas de cd_hab ; on filtre les vides ici
            # (l'itération réelle se fait sur habitats_data dans _create_habitat_relations).
            habitat_ids = [h.get('cd_hab') for h in habitats_data if h.get('cd_hab')]
        if not geologie_ids and geologies_data:
            geologie_ids = [g['id_inpg'] for g in geologies_data]

        # Créer l'enjeu
        enjeu = Enjeu.objects.create(**validated_data)

        # Créer les relations taxonomiques
        self._create_taxon_relations(enjeu, taxon_ids, taxons_data)
        self._create_habitat_relations(enjeu, habitat_ids, habitats_data)
        self._create_geologie_relations(enjeu, geologie_ids, geologies_data)
        self._create_objet_geologique_relations(enjeu, objets_geologiques_data)

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
        objets_geologiques_data = validated_data.pop('objets_geologiques_data', None)

        # Si les IDs ne sont pas fournis, les extraire depuis les données
        if taxon_ids is None and taxons_data is not None:
            taxon_ids = [t['cd_nom'] for t in taxons_data]
        if habitat_ids is None and habitats_data is not None:
            # #368 — habitats libres (cd_hab vide) filtrés ici ; liste reste
            # non-None pour déclencher le remplacement (delete + recreate).
            habitat_ids = [h.get('cd_hab') for h in habitats_data if h.get('cd_hab')]
        if geologie_ids is None and geologies_data is not None:
            geologie_ids = [g['id_inpg'] for g in geologies_data]

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

        # #237 — remplacement complet des objets géologiques si fournis
        if objets_geologiques_data is not None:
            instance.objets_geologiques.all().delete()
            self._create_objet_geologique_relations(instance, objets_geologiques_data)

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
        """Créer les relations avec les habitats.

        #368 — Si `habitats_data` est fourni, on l'itère directement (un habitat
        par entrée) pour supporter les habitats « libres » (cd_hab vide → None,
        plusieurs possibles). Sinon, fallback historique sur `habitat_ids`.
        """
        if habitats_data:
            for data in habitats_data:
                cd = (data.get('cd_hab') or '').strip() or None
                CorEnjeuHabitat.objects.create(
                    id_enjeu=enjeu,
                    cd_hab=cd,
                    lb_hab_fr=data.get('lb_hab_fr', '') or ''
                )
            return

        for cd_hab in habitat_ids:
            CorEnjeuHabitat.objects.create(
                id_enjeu=enjeu,
                cd_hab=cd_hab,
                lb_hab_fr=''
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

    def _create_objet_geologique_relations(self, enjeu, objets_data):
        """#237 — Créer les relations avec les objets géologiques sélectionnés.
        Chaque entrée référence une nomenclature TYPE_OBJET_GEOLOGIQUE (par id) ;
        `precision` complète un objet de type « Autre »."""
        valid_ids = set(
            Nomenclature.objects
            .filter(id_type__mnemonique='TYPE_OBJET_GEOLOGIQUE')
            .values_list('id_nomenclature', flat=True)
        )
        seen = set()
        for obj in objets_data or []:
            nid = obj.get('id_objet_geologique')
            if not nid or nid in seen or nid not in valid_ids:
                continue
            seen.add(nid)
            CorEnjeuObjetGeologique.objects.create(
                id_enjeu=enjeu,
                id_objet_geologique_id=nid,
                precision=obj.get('precision', '') or '',
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
        return _prefetched_count(obj, 'taxons')

    def get_nb_habitats(self, obj):
        return _prefetched_count(obj, 'habitats')

    def get_nb_enjeux_lies(self, obj):
        return _prefetched_count(obj, 'enjeux_lies')


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

        # Si les IDs ne sont pas fournis, les extraire depuis les données
        if not taxon_ids and taxons_data:
            taxon_ids = [t['cd_nom'] for t in taxons_data]
        if not habitat_ids and habitats_data:
            habitat_ids = [h.get('cd_hab') for h in habitats_data if h.get('cd_hab')]
        if not geologie_ids and geologies_data:
            geologie_ids = [g['id_inpg'] for g in geologies_data]

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

        # Si les IDs ne sont pas fournis, les extraire depuis les données
        if taxon_ids is None and taxons_data is not None:
            taxon_ids = [t['cd_nom'] for t in taxons_data]
        if habitat_ids is None and habitats_data is not None:
            # #368 — habitats libres (cd_hab vide) filtrés ici ; liste reste
            # non-None pour déclencher le remplacement (delete + recreate).
            habitat_ids = [h.get('cd_hab') for h in habitats_data if h.get('cd_hab')]
        if geologie_ids is None and geologies_data is not None:
            geologie_ids = [g['id_inpg'] for g in geologies_data]

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
        # #368 — clé sûre (un habitat libre peut ne pas avoir de cd_hab).
        data_dict = {h.get('cd_hab'): h for h in habitats_data if h.get('cd_hab')}

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
