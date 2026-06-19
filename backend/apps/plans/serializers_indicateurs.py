"""
Serializers pour l'API REST Indicateurs, Métriques et Mesures.
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from .serializers_enjeux import _prefetched_count

from .models_indicateurs import (
    Indicateur, CorIndicateurTaxon, CorIndicateurHabitat, CorIndicateurGeologie,
    Metrique, MetriqueScoreBlock, Mesure, IndicateurMesure,
)


# =============================================================================
# Serializers pour les tables de corrélation
# =============================================================================

class CorIndicateurTaxonSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Indicateur-Taxon."""

    class Meta:
        model = CorIndicateurTaxon
        fields = ['id', 'id_indicateur', 'cd_nom', 'nom_complet', 'nom_vern']
        read_only_fields = ['id']


class CorIndicateurHabitatSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Indicateur-Habitat."""

    class Meta:
        model = CorIndicateurHabitat
        fields = ['id', 'id_indicateur', 'cd_hab', 'lb_hab_fr']
        read_only_fields = ['id']


class CorIndicateurGeologieSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Indicateur-Géologie."""

    class Meta:
        model = CorIndicateurGeologie
        fields = ['id', 'id_indicateur', 'id_inpg', 'nom']
        read_only_fields = ['id']


# =============================================================================
# Serializers pour les Mesures
# =============================================================================

class MesureSerializer(serializers.ModelSerializer):
    """Serializer pour la lecture d'une Mesure."""
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)

    class Meta:
        model = Mesure
        fields = [
            'id_mesure', 'id_metrique',
            'valeur', 'date_mesure', 'commentaire',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_mesure', 'date_ajout', 'date_maj']


class MesureCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une Mesure."""

    class Meta:
        model = Mesure
        fields = [
            'id_mesure', 'id_metrique',
            'valeur', 'date_mesure', 'commentaire'
        ]
        read_only_fields = ['id_mesure']


# =============================================================================
# Serializers pour les Métriques
# =============================================================================

class MetriqueScoreBlockSerializer(serializers.ModelSerializer):
    """
    Bloc de scoring complémentaire d'une métrique numérique (#247).

    Même structure qu'un bloc principal (5 paliers, sens de variation,
    inclusivités, bornes extrêmes). Combiné aux blocs précédents via
    `logical_op` (OR par défaut).
    """

    class Meta:
        model = MetriqueScoreBlock
        fields = [
            'id_score_block',
            'position',
            'intitule',
            'unite',
            'logical_op',
            'group_open',
            'group_close',
            'sens_variation',
            'score_1_inf', 'score_1_sup',
            'score_2_inf', 'score_2_sup',
            'score_3_inf', 'score_3_sup',
            'score_4_inf', 'score_4_sup',
            'score_5_inf', 'score_5_sup',
            'score_1_sup_inclusive',
            'score_2_sup_inclusive',
            'score_3_sup_inclusive',
            'score_4_sup_inclusive',
            'has_borne_score1',
            'has_borne_score5',
            'inactive_levels',
        ]
        read_only_fields = ['id_score_block']


class MetriqueSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une Métrique avec mesures et opérations imbriquées."""
    mesures = MesureSerializer(many=True, read_only=True)
    nb_mesures = serializers.SerializerMethodField()
    operations = serializers.SerializerMethodField()
    nb_operations = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    type_metrique_label = serializers.CharField(source='type_metrique.label', read_only=True)
    type_metrique_mnemonique = serializers.CharField(source='type_metrique.mnemonique', read_only=True)
    score_blocks = MetriqueScoreBlockSerializer(many=True, read_only=True)

    class Meta:
        model = Metrique
        fields = [
            'id_metrique', 'id_indicateur',
            'nom_metrique', 'description', 'ordre',
            'type_metrique', 'type_metrique_label', 'type_metrique_mnemonique',
            'unite', 'bloc_intitule', 'ponderation', 'etat_reference',
            # Seuils de scores
            'score_1_inf', 'score_1_sup', 'score_1_val', 'score_1_label',
            'score_2_inf', 'score_2_sup', 'score_2_val', 'score_2_label',
            'score_3_inf', 'score_3_sup', 'score_3_val', 'score_3_label',
            'score_4_inf', 'score_4_sup', 'score_4_val', 'score_4_label',
            'score_5_inf', 'score_5_sup', 'score_5_val', 'score_5_label',
            # Direction et inclusivité des bornes
            'sens_variation',
            'score_1_sup_inclusive', 'score_2_sup_inclusive',
            'score_3_sup_inclusive', 'score_4_sup_inclusive',
            'has_borne_score1', 'has_borne_score5',
            'inactive_levels',
            'group_open', 'group_close',
            # Blocs complémentaires (#247) — même structure que le bloc principal
            'score_blocks',
            # Relations
            'mesures', 'nb_mesures',
            'operations', 'nb_operations',
            # Audit
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_metrique', 'date_ajout', 'date_maj']

    def get_nb_mesures(self, obj):
        # Use prefetched data if available (avoids COUNT query)
        if hasattr(obj, '_prefetched_objects_cache') and 'mesures' in obj._prefetched_objects_cache:
            return len(obj.mesures.all())
        return _prefetched_count(obj, 'mesures')

    def get_operations(self, obj):
        from .serializers_operations import OperationNestedSerializer
        # #263 — Propager le contexte (notamment `operation_codes` pré-calculé
        # dans `by-plan`) au serializer niché. Sans ça, chaque opération
        # déclenchait un fallback `_compute_operation_code_affichage` qui
        # traverse RA → OO → FI → Enjeu et fait sauter le prefetch.
        return OperationNestedSerializer(
            obj.operations.all(), many=True, context=self.context,
        ).data

    def get_nb_operations(self, obj):
        # Use prefetched data if available (avoids COUNT query)
        if hasattr(obj, '_prefetched_objects_cache') and 'operations' in obj._prefetched_objects_cache:
            return len(obj.operations.all())
        return _prefetched_count(obj, 'operations')


class MetriqueListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Métriques."""
    nb_mesures = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    type_metrique_label = serializers.CharField(source='type_metrique.label', read_only=True)

    class Meta:
        model = Metrique
        fields = [
            'id_metrique', 'id_indicateur',
            'nom_metrique', 'description',
            'type_metrique', 'type_metrique_label',
            'unite', 'ponderation',
            'nb_mesures',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_metrique', 'date_ajout', 'date_maj']

    def get_nb_mesures(self, obj):
        return _prefetched_count(obj, 'mesures')


class MetriqueCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une Métrique."""

    # #247 — Blocs de scoring complémentaires (même structure que le bloc principal,
    # combinés en ET/OU). Le client envoie la liste complète à chaque update.
    score_blocks = MetriqueScoreBlockSerializer(many=True, required=False)

    class Meta:
        model = Metrique
        fields = [
            'id_metrique', 'id_indicateur',
            'nom_metrique', 'description', 'ordre',
            'type_metrique', 'unite', 'bloc_intitule', 'ponderation', 'etat_reference',
            # Seuils de scores
            'score_1_inf', 'score_1_sup', 'score_1_val', 'score_1_label',
            'score_2_inf', 'score_2_sup', 'score_2_val', 'score_2_label',
            'score_3_inf', 'score_3_sup', 'score_3_val', 'score_3_label',
            'score_4_inf', 'score_4_sup', 'score_4_val', 'score_4_label',
            'score_5_inf', 'score_5_sup', 'score_5_val', 'score_5_label',
            # Direction et inclusivité des bornes
            'sens_variation',
            'score_1_sup_inclusive', 'score_2_sup_inclusive',
            'score_3_sup_inclusive', 'score_4_sup_inclusive',
            'has_borne_score1', 'has_borne_score5',
            'inactive_levels',
            'group_open', 'group_close',
            # Blocs complémentaires
            'score_blocks',
        ]
        read_only_fields = ['id_metrique']
        extra_kwargs = {
            # #339 — l'intitulé peut être vide pour une métrique « Indéterminé ».
            # Le caractère obligatoire est appliqué conditionnellement dans validate().
            'nom_metrique': {'required': False, 'allow_blank': True},
        }

    def create(self, validated_data):
        blocks = validated_data.pop('score_blocks', [])
        metrique = super().create(validated_data)
        for block in blocks:
            MetriqueScoreBlock.objects.create(id_metrique=metrique, **block)
        return metrique

    def update(self, instance, validated_data):
        # Stratégie simple : on remplace l'ensemble des blocs à chaque update.
        # Le client doit envoyer la liste complète des blocs complémentaires
        # à conserver. Évite la complexité d'un diff partiel.
        blocks = validated_data.pop('score_blocks', None)
        instance = super().update(instance, validated_data)
        if blocks is not None:
            instance.score_blocks.all().delete()
            for block in blocks:
                MetriqueScoreBlock.objects.create(id_metrique=instance, **block)
        return instance

    def validate(self, attrs):
        """Validate metric name requirement (#339) and interval consistency for NUMERIQUE metrics."""
        type_met = attrs.get('type_metrique', getattr(self.instance, 'type_metrique', None) if self.instance else None)

        # #339 — L'intitulé n'est obligatoire que si le type n'est pas « Indéterminé ».
        is_indetermine = bool(type_met) and getattr(type_met, 'mnemonique', None) == 'INDETERMINE'
        nom = attrs.get(
            'nom_metrique',
            getattr(self.instance, 'nom_metrique', '') if self.instance else '',
        )
        if not is_indetermine and not (nom or '').strip():
            raise serializers.ValidationError({
                'nom_metrique': _("L'intitulé de la métrique est obligatoire.")
            })

        # Mnémonique du type (NUMERIQUE / CHIFFRE / TEXTE / INDETERMINE).
        mnemo = getattr(type_met, 'mnemonique', None)
        if mnemo is None and type_met and hasattr(type_met, 'pk'):
            from apps.core.models import Nomenclature
            try:
                mnemo = Nomenclature.objects.get(pk=type_met.pk).mnemonique
            except Nomenclature.DoesNotExist:
                mnemo = None
        # Par défaut (type absent), on traite comme NUMERIQUE (comportement historique).
        is_numerique = mnemo is None or mnemo == 'NUMERIQUE'

        # Chiffre / Texte : chaque niveau ACTIF (non « non utilisé ») doit avoir
        # une valeur (val pour Chiffre, label pour Texte) — évite une grille
        # incomplète qui fausserait le scoring.
        if mnemo in ('CHIFFRE', 'TEXTE'):
            inactive_raw = attrs.get(
                'inactive_levels',
                getattr(self.instance, 'inactive_levels', None) if self.instance else None,
            ) or []
            try:
                inactive_set = {int(x) for x in inactive_raw}
            except (TypeError, ValueError):
                inactive_set = set()
            field = 'val' if mnemo == 'CHIFFRE' else 'label'
            for level in range(1, 6):
                if level in inactive_set:
                    continue
                attr_name = f'score_{level}_{field}'
                value = attrs.get(
                    attr_name,
                    getattr(self.instance, attr_name, None) if self.instance else None,
                )
                missing = value is None if mnemo == 'CHIFFRE' else not (value or '').strip()
                if missing:
                    raise serializers.ValidationError({
                        attr_name: _("Chaque niveau actif doit avoir une valeur (ou être marqué « non utilisé »).")
                    })
            return attrs

        if not is_numerique:
            return attrs

        sens = attrs.get(
            'sens_variation',
            getattr(self.instance, 'sens_variation', 'CROISSANT') if self.instance else 'CROISSANT'
        )

        # Niveaux désactivés : sautés par les validateurs de bornes / continuité.
        inactive = attrs.get(
            'inactive_levels',
            getattr(self.instance, 'inactive_levels', None) if self.instance else None
        ) or []
        try:
            inactive_set = {int(x) for x in inactive}
        except (TypeError, ValueError):
            inactive_set = set()

        # Validate inf < sup for each level (always true regardless of direction)
        for level in range(1, 6):
            if level in inactive_set:
                continue
            inf_val = attrs.get(f'score_{level}_inf')
            sup_val = attrs.get(f'score_{level}_sup')
            if inf_val is not None and sup_val is not None and inf_val >= sup_val:
                raise serializers.ValidationError({
                    f'score_{level}_sup': _("La borne sup doit être strictement supérieure à la borne inf.")
                })

        # Validate continuity between adjacent levels — en sautant les niveaux
        # inactifs (un niveau marqué « non utilisé » casse volontairement la
        # continuité avec ses voisins).
        # Ascending: score_N_sup == score_(N+1)_inf (boundary = upper end of N)
        # Descending: score_N_inf == score_(N+1)_sup (boundary = lower end of N)
        for n in range(1, 5):
            if n in inactive_set or (n + 1) in inactive_set:
                continue
            if sens == 'DECROISSANT':
                val_n = attrs.get(f'score_{n}_inf')
                val_next = attrs.get(f'score_{n + 1}_sup')
            else:
                val_n = attrs.get(f'score_{n}_sup')
                val_next = attrs.get(f'score_{n + 1}_inf')

            if val_n is not None and val_next is not None and val_n != val_next:
                raise serializers.ValidationError(
                    _("Les bornes entre les scores %(n)s et %(next)s doivent être égales pour assurer la continuité.")
                    % {'n': n, 'next': n + 1}
                )

        return attrs


# =============================================================================
# Serializers pour les Indicateurs
# =============================================================================

class IndicateurSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un Indicateur avec métriques et corrélations imbriquées.
    Les opérations sont désormais imbriquées sous chaque métrique (Métrique → Opérations)."""
    metriques = MetriqueSerializer(many=True, read_only=True)
    # #367 — actions rattachées directement à l'indicateur (sans métrique)
    operations = serializers.SerializerMethodField()
    taxons = CorIndicateurTaxonSerializer(many=True, read_only=True)
    habitats = CorIndicateurHabitatSerializer(many=True, read_only=True)
    geologies = CorIndicateurGeologieSerializer(many=True, read_only=True)
    nb_metriques = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    type_indicateur_label = serializers.CharField(source='type_indicateur.label', read_only=True)
    type_indicateur_mnemonique = serializers.CharField(source='type_indicateur.mnemonique', read_only=True)
    # #420 — slug de l'enjeu, pour le deep-link « Modifier l'indicateur » depuis
    # la page de saisie du suivi vers le détail de l'enjeu (arborescence).
    enjeu_slug = serializers.SerializerMethodField()

    class Meta:
        model = Indicateur
        fields = [
            'id_indicateur', 'id_ne', 'id_resultat_attendu',
            'nom_indicateur', 'description', 'ordre',
            'type_indicateur', 'type_indicateur_label', 'type_indicateur_mnemonique',
            'est_standardise',
            # Relations
            'metriques', 'nb_metriques',
            'operations',
            'taxons', 'habitats', 'geologies',
            # Navigation
            'enjeu_slug',
            # Audit
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_indicateur', 'date_ajout', 'date_maj']

    def get_nb_metriques(self, obj):
        return _prefetched_count(obj, 'metriques')

    def get_enjeu_slug(self, obj):
        """#420 — Remonte au slug de l'enjeu de l'indicateur.
        Deux chemins possibles : via NE (Indicateur → NE → OLT → Enjeu) ou
        via RA (Indicateur → RA → OO → Pression → Facteur → Enjeu)."""
        # Chemin NE
        try:
            ne = obj.id_ne
            if ne and ne.id_olt and ne.id_olt.id_enjeu:
                return ne.id_olt.id_enjeu.slug
        except AttributeError:
            pass
        # Chemin RA (via pression)
        try:
            ra = obj.id_resultat_attendu
            if ra and ra.id_oo:
                oo = ra.id_oo
                pression = oo.pressions.select_related(
                    'id_facteur_influence__id_enjeu'
                ).first()
                if (pression and pression.id_facteur_influence
                        and pression.id_facteur_influence.id_enjeu):
                    return pression.id_facteur_influence.id_enjeu.slug
                # #337 — OO rattaché directement à un enjeu (FCR)
                if getattr(oo, 'id_enjeu', None):
                    return oo.id_enjeu.slug
        except AttributeError:
            pass
        return None

    def get_operations(self, obj):
        """#227/#367 — TOUTES les actions de l'indicateur, dédupliquées :
        rattachées directement (id_indicateur) OU via l'une de ses métriques.
        Sophie : les actions sont listées une seule fois sous l'indicateur, et
        les métriques associées sont rappelées dans le bandeau de chaque action
        (plus de regroupement « Métrique : … » au-dessus des actions)."""
        from .serializers_operations import OperationNestedSerializer
        seen = {}
        for op in obj.operations.all():            # actions sans métrique (#367)
            seen[op.id_operation] = op
        for met in obj.metriques.all():            # actions liées à une métrique
            for op in met.operations.all():
                seen.setdefault(op.id_operation, op)
        ops = sorted(seen.values(), key=lambda o: (o.ordre, o.id_operation))
        return OperationNestedSerializer(ops, many=True, context=self.context).data


class IndicateurListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Indicateurs."""
    nb_metriques = serializers.SerializerMethodField()
    nb_operations = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    type_indicateur_label = serializers.CharField(source='type_indicateur.label', read_only=True)

    class Meta:
        model = Indicateur
        fields = [
            'id_indicateur', 'id_ne', 'id_resultat_attendu',
            'nom_indicateur', 'description', 'ordre',
            'type_indicateur', 'type_indicateur_label',
            'est_standardise',
            'nb_metriques', 'nb_operations',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_indicateur', 'date_ajout', 'date_maj']

    def get_nb_metriques(self, obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'metriques' in obj._prefetched_objects_cache:
            return len(obj.metriques.all())
        return _prefetched_count(obj, 'metriques')

    def get_nb_operations(self, obj):
        # Use prefetched data if available to avoid N+1
        if hasattr(obj, '_prefetched_objects_cache') and 'metriques' in obj._prefetched_objects_cache:
            seen = set()
            for met in obj.metriques.all():
                if hasattr(met, '_prefetched_objects_cache') and 'operations' in met._prefetched_objects_cache:
                    for op in met.operations.all():
                        seen.add(op.id_operation)
            return len(seen)
        from .models_operations import Operation
        return Operation.objects.filter(metriques__id_indicateur=obj).distinct().count()


class IndicateurCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'un Indicateur."""

    class Meta:
        model = Indicateur
        fields = [
            'id_indicateur', 'id_ne', 'id_resultat_attendu',
            'nom_indicateur', 'description', 'ordre',
            'type_indicateur', 'est_standardise'
        ]
        read_only_fields = ['id_indicateur']

    def validate(self, attrs):
        id_ne = attrs.get('id_ne', getattr(self.instance, 'id_ne', None) if self.instance else None)
        id_ra = attrs.get('id_resultat_attendu', getattr(self.instance, 'id_resultat_attendu', None) if self.instance else None)

        if not id_ne and not id_ra:
            raise serializers.ValidationError(
                "Un indicateur doit être rattaché à un niveau d'exigence ou un résultat attendu."
            )
        if id_ne and id_ra:
            raise serializers.ValidationError(
                "Un indicateur ne peut être rattaché qu'à un seul parent."
            )
        return attrs


# =============================================================================
# IndicateurMesure (saisie au niveau indicateur, avec override manuel)
# =============================================================================

class IndicateurMesureSerializer(serializers.ModelSerializer):
    """Saisie annuelle au niveau Indicateur."""

    class Meta:
        model = IndicateurMesure
        fields = [
            'id_indicateur_mesure',
            'id_indicateur',
            'annee',
            'score_override',
            'commentaire_override',
            'date_ajout',
            'date_maj',
            'id_utilisateur_maj',
        ]
        read_only_fields = [
            'id_indicateur_mesure', 'date_ajout', 'date_maj', 'id_utilisateur_maj',
        ]
