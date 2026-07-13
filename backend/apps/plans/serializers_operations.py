"""
Serializers pour l'API REST Opérations (Actions).
"""
from rest_framework import serializers

from .models_operations import (
    Protocole, SuiviInventaire,
    Operation, CorOperationSite, CorOperationMetrique,
    OperationAnnee, OperationAnneeOrganisme, FinanceOperation,
    RealisationOperationAnnee, RealisationOperationAnneeOrganisme,
)


# =============================================================================
# Helpers — code d'affichage des opérations (#228 / 2026-05-12)
# =============================================================================

def compute_operation_codes_for_plan(plan_id):
    """
    Calcule pour chaque Operation rattachée au plan son code d'affichage
    `<prefix><rang>` (ex: 'CS1', 'SP2'), basé sur l'ordre de lecture naturel
    du plan (#228, version du 2026-05-12) :

      Enjeu → OLT → NE → Indicateur → Métrique → Action
              (puis branche OO/RA en parallèle)
              Facteur → Pression → OO → RA → Indicateur → Métrique → Action

    À chaque niveau, le tri se fait par `(ordre, id)`. Une Operation
    rattachée à plusieurs métriques (M2M) est comptée **une seule fois**
    selon sa PREMIÈRE occurrence dans le parcours. Le DnD intra-métrique
    décale donc le rang d'une action localement (typiquement de ±1) et
    n'affecte pas les actions des autres branches/métriques.

    Retour : dict {id_operation: 'CS1', ...}.
    """
    # Import local pour éviter les cycles d'import.
    from django.db.models import Prefetch
    from .models import PlanGestion
    from .models_enjeux import (
        Enjeu, FacteurInfluence, Pression,
        ObjectifLongTerme, NiveauExigence,
        ObjectifOperationnel, ResultatAttendu,
    )
    from .models_indicateurs import Indicateur, Metrique

    plan = PlanGestion.objects.filter(pk=plan_id).first()
    if plan is None:
        return {}

    # Tout le sous-arbre est précháargé en quelques requêtes via Prefetch
    # (au lieu d'une cascade de queries lazy par niveau). Chaque niveau
    # impose son tri pour qu'on puisse parcourir sans re-requêter.
    operations_qs = (
        Operation.objects
        .select_related('id_type_action', 'id_categorie_action_reserve')
        .order_by('ordre', 'id_operation')
    )
    metriques_qs = (
        Metrique.objects
        .order_by('ordre', 'id_metrique')
        .prefetch_related(Prefetch('operations', queryset=operations_qs))
    )
    indicateurs_qs = (
        Indicateur.objects
        .order_by('ordre', 'id_indicateur')
        .prefetch_related(
            Prefetch('metriques', queryset=metriques_qs),
            # #367 — actions rattachées directement à l'indicateur (sans métrique)
            Prefetch('operations', queryset=operations_qs),
        )
    )
    ne_qs = (
        NiveauExigence.objects
        .order_by('ordre', 'id_ne')
        .prefetch_related(Prefetch('indicateurs', queryset=indicateurs_qs))
    )
    olt_qs = (
        ObjectifLongTerme.objects
        .order_by('ordre', 'id_olt')
        .prefetch_related(Prefetch('niveaux_exigence', queryset=ne_qs))
    )
    ra_qs = (
        ResultatAttendu.objects
        .order_by('ordre', 'id_ra')
        .prefetch_related(Prefetch('indicateurs', queryset=indicateurs_qs))
    )
    oo_qs = (
        ObjectifOperationnel.objects
        .order_by('ordre', 'id_oo')
        .prefetch_related(Prefetch('resultats_attendus', queryset=ra_qs))
    )
    pression_qs = (
        Pression.objects
        .order_by('ordre', 'id_pression')
        .prefetch_related(Prefetch('objectifs_operationnels', queryset=oo_qs))
    )
    facteur_qs = (
        FacteurInfluence.objects
        .order_by('ordre', 'id_facteur_influence')
        .prefetch_related(Prefetch('pressions', queryset=pression_qs))
    )
    enjeux = (
        Enjeu.objects
        .filter(id_pg=plan)
        .order_by('ordre', 'id_enjeu')
        .prefetch_related(
            Prefetch('objectifs_long_terme', queryset=olt_qs),
            Prefetch('facteurs_influence', queryset=facteur_qs),
        )
    )

    seen_op_ids = []
    operations_by_id = {}
    seen_oos = set()

    def visit_indicateur_metriques(indicateur):
        # `metriques.all()` et `operations.all()` puisent dans le prefetch
        # (déjà trié au niveau de la queryset) — aucune nouvelle requête.
        for metrique in indicateur.metriques.all():
            for op in metrique.operations.all():
                if op.pk in operations_by_id:
                    continue
                operations_by_id[op.pk] = op
                seen_op_ids.append(op.pk)
        # #367 — actions rattachées directement à l'indicateur (sans métrique)
        for op in indicateur.operations.all():
            if op.pk in operations_by_id:
                continue
            operations_by_id[op.pk] = op
            seen_op_ids.append(op.pk)

    for enjeu in enjeux:
        # Branche NE : Enjeu → OLT → NE → Indicateur → Métrique → Action
        for olt in enjeu.objectifs_long_terme.all():
            for ne in olt.niveaux_exigence.all():
                for indicateur in ne.indicateurs.all():
                    visit_indicateur_metriques(indicateur)

        # Branche OO/RA : Enjeu → Facteur → Pression → OO → RA → Indic → Met → Action
        for facteur in enjeu.facteurs_influence.all():
            for pression in facteur.pressions.all():
                for oo in pression.objectifs_operationnels.all():
                    if oo.pk in seen_oos:
                        continue
                    seen_oos.add(oo.pk)
                    for ra in oo.resultats_attendus.all():
                        for indicateur in ra.indicateurs.all():
                            visit_indicateur_metriques(indicateur)

    # Calcul des rangs par préfixe dans l'ordre rencontré.
    # #485 — Un numéro fixé manuellement (`numero_manuel`) est réservé pour son
    # préfixe : l'action garde ce numéro quel que soit l'ordre (drag & drop),
    # et l'auto-numérotation des autres actions du même préfixe saute cet indice.
    reserved = {}
    for op_id in seen_op_ids:
        op = operations_by_id[op_id]
        if op.numero_manuel:
            reserved.setdefault(op.code_prefix, set()).add(op.numero_manuel)

    counters = {}
    codes = {}
    for op_id in seen_op_ids:
        op = operations_by_id[op_id]
        prefix = op.code_prefix
        if op.numero_manuel:
            codes[op_id] = f"{prefix}{op.numero_manuel}"
            continue
        # Prochain indice automatique libre (non réservé) pour ce préfixe.
        n = counters.get(prefix, 0) + 1
        while n in reserved.get(prefix, ()):
            n += 1
        counters[prefix] = n
        codes[op_id] = f"{prefix}{n}"
    return codes


def _compute_operation_code_affichage(op):
    """Fallback : calcule le code pour UNE operation (potentiellement coûteux)."""
    plan = op.get_plan_de_gestion()
    if not plan:
        return f"{op.code_prefix}?"
    codes = compute_operation_codes_for_plan(plan.pk)
    return codes.get(op.id_operation, f"{op.code_prefix}?")


def _response_metrique_grid(m):
    """#452 — Format + grille de scoring d'une métrique d'indicateur de réponse.

    Exposé à part (uniquement pour les métriques REPONSE) pour permettre une
    saisie/visu *type-aware* : select des libellés pour TEXTE (#464), valeurs
    numériques pour CHIFFRE (#465), seuils + score auto pour NUMERIQUE.
    """
    grid = {
        'format_metrique_id': m.format_metrique_id,
        'format_metrique_mnemonique': getattr(m.format_metrique, 'mnemonique', None) if m.format_metrique_id else None,
        'type_metrique_mnemonique': getattr(m.type_metrique, 'mnemonique', None) if m.type_metrique_id else None,
        # #452 — unité et pondération de la métrique de réponse (éditées dans la
        # grille) : exposées pour que le formulaire les ré-affiche et que la
        # sauvegarde ne les perde pas.
        'unite': m.unite or '',
        'ponderation': m.ponderation,
        'sens_variation': m.sens_variation,
        'has_borne_score1': m.has_borne_score1,
        'has_borne_score5': m.has_borne_score5,
        'inactive_levels': m.inactive_levels or [],
        # #247/#452 — bloc principal (intitulé + parenthésage) et blocs de scoring
        # complémentaires (ET/OU) exposés pour que la fiche d'action affiche la
        # grille multi-blocs des indicateurs de réponse NUMERIQUE, à l'identique de
        # l'arborescence des enjeux (MetriqueGridDisplayComponent lit `score_blocks`).
        'bloc_intitule': m.bloc_intitule or '',
        'group_open': m.group_open,
        'group_close': m.group_close,
        'score_blocks': [_score_block_grid(b) for b in m.score_blocks.all()],
    }
    for i in range(1, 6):
        grid[f'score_{i}_inf'] = getattr(m, f'score_{i}_inf')
        grid[f'score_{i}_sup'] = getattr(m, f'score_{i}_sup')
        grid[f'score_{i}_val'] = getattr(m, f'score_{i}_val')
        grid[f'score_{i}_label'] = getattr(m, f'score_{i}_label')
    for i in range(1, 5):
        grid[f'score_{i}_sup_inclusive'] = getattr(m, f'score_{i}_sup_inclusive')
    return grid


def _score_block_grid(b):
    """#247 — Bloc de scoring complémentaire (ET/OU) d'une métrique numérique,
    sérialisé pour la grille (mêmes champs que MetriqueScoreBlockSerializer,
    construits inline pour éviter un import croisé serializers_indicateurs)."""
    block = {
        'id_score_block': b.id_score_block,
        'position': b.position,
        'intitule': b.intitule,
        'unite': b.unite,
        'logical_op': b.logical_op,
        'group_open': b.group_open,
        'group_close': b.group_close,
        'sens_variation': b.sens_variation,
        'has_borne_score1': b.has_borne_score1,
        'has_borne_score5': b.has_borne_score5,
        'inactive_levels': b.inactive_levels or [],
    }
    for i in range(1, 6):
        block[f'score_{i}_inf'] = getattr(b, f'score_{i}_inf')
        block[f'score_{i}_sup'] = getattr(b, f'score_{i}_sup')
    for i in range(1, 5):
        block[f'score_{i}_sup_inclusive'] = getattr(b, f'score_{i}_sup_inclusive')
    return block


# =============================================================================
# Serializers pour les entités nested
# =============================================================================

class RealisationOperationAnneeOrganismeSerializer(serializers.ModelSerializer):
    """Réalisation ventilée par organisme (1-1 avec OperationAnneeOrganisme)."""

    class Meta:
        model = RealisationOperationAnneeOrganisme
        fields = [
            'id_realisation_op_annee_organisme',
            'id_operation_annee_organisme',
            'budget_fonctionnement_realise',
            'budget_investissement_realise',
            'etp_realise',
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_realisation_op_annee_organisme', 'date_ajout', 'date_maj']


class GeoJSONGeometryField(serializers.Field):
    """
    Champ DRF pour les `GeometryField` exposés et acceptés en GeoJSON.
    Sérialise la géométrie en GeoJSON (dict) ; accepte en entrée soit un
    dict GeoJSON, soit une string GeoJSON / WKT.
    """

    def to_representation(self, value):
        if not value:
            return None
        import json as _json
        try:
            return _json.loads(value.geojson)
        except (AttributeError, ValueError, TypeError):
            return None

    def to_internal_value(self, data):
        if data is None:
            return None
        import json as _json
        from django.contrib.gis.geos import GEOSGeometry
        try:
            data_str = data if isinstance(data, str) else _json.dumps(data)
            return GEOSGeometry(data_str)
        except Exception as e:
            raise serializers.ValidationError(f"GeoJSON invalide: {e}")


class RealisationOperationAnneeSerializer(serializers.ModelSerializer):
    """Réalisation annuelle d'une opération (1-1 avec OperationAnnee)."""
    niveau_realisation_label = serializers.CharField(
        source='id_niveau_realisation.label', read_only=True
    )
    niveau_realisation_mnemonique = serializers.CharField(
        source='id_niveau_realisation.mnemonique', read_only=True
    )
    # Emprise réalisée exposée et acceptée en GeoJSON (cohérent avec
    # `OperationSerializer.geom_geojson`). Lecture + écriture.
    geom_realisee = GeoJSONGeometryField(required=False, allow_null=True)

    class Meta:
        model = RealisationOperationAnnee
        fields = [
            'id_realisation_operation_annee',
            'id_operation_annee',
            'id_niveau_realisation', 'niveau_realisation_label', 'niveau_realisation_mnemonique',
            'periodicite_realisee', 'periodicite_mensuelle_realisee',
            'commentaires', 'geom_realisee',
            'budget_realise',
            'budget_fonctionnement_realise', 'budget_investissement_realise',
            'etp_realise',
            'operateurs_realises', 'financeurs_realises',
            'date_ajout', 'date_maj', 'id_utilisateur_maj',
        ]
        read_only_fields = [
            'id_realisation_operation_annee', 'date_ajout', 'date_maj', 'id_utilisateur_maj',
        ]


class OperationAnneeOrganismeSerializer(serializers.ModelSerializer):
    """Serializer pour la ventilation budget/travail par organisme."""
    organisme_nom = serializers.CharField(source='id_organisme.nom_organisme', read_only=True)
    realisation = RealisationOperationAnneeOrganismeSerializer(read_only=True)

    class Meta:
        model = OperationAnneeOrganisme
        fields = [
            'id_operation_annee_organisme',
            'id_organisme', 'organisme_nom',
            'budget_fonctionnement', 'budget_investissement', 'etp',
            'realisation',
        ]
        read_only_fields = ['id_operation_annee_organisme']


class OperationAnneeSerializer(serializers.ModelSerializer):
    """Serializer pour la programmation annuelle d'une opération."""
    organismes = OperationAnneeOrganismeSerializer(many=True, read_only=True)
    realisation = RealisationOperationAnneeSerializer(read_only=True)

    class Meta:
        model = OperationAnnee
        fields = [
            'id_operation_annee', 'annee', 'periodicite',
            'budget', 'etp', 'budget_fonctionnement', 'budget_investissement',
            'periodicite_mensuelle', 'geom', 'organismes',
            'realisation',
        ]
        read_only_fields = ['id_operation_annee']


class FinanceOperationSerializer(serializers.ModelSerializer):
    """Serializer pour une source de financement d'opération."""
    categorie_label = serializers.CharField(source='id_categorie.label', read_only=True)

    class Meta:
        model = FinanceOperation
        fields = [
            'id_finance_operation', 'libelle',
            'id_categorie', 'categorie_label'
        ]
        read_only_fields = ['id_finance_operation']


class ProtocoleSerializer(serializers.ModelSerializer):
    """Serializer pour un protocole."""

    class Meta:
        model = Protocole
        fields = [
            'id_protocole',
            'protocole_dans_campanule', 'protocole_campanule_nom',
            'cd_protocole_campanule', 'nb_etp_cycle',
            'nom_protocole', 'mode_validation',
            'respect_protocole', 'justification_non_respect', 'differences_protocole',
            'description_protocole', 'objectif_protocole', 'periode_echantillonnage',
            'periode_suivi', 'documentation_disponible', 'url_documentation',
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_protocole', 'date_ajout', 'date_maj']


class SuiviInventaireSerializer(serializers.ModelSerializer):
    """Serializer pour un suivi/inventaire (lecture)."""
    protocole = ProtocoleSerializer(source='id_protocole', read_only=True)
    bancarisation_label = serializers.SerializerMethodField()
    outil_saisie_label = serializers.SerializerMethodField()

    class Meta:
        model = SuiviInventaire
        fields = [
            'id_suivi_inventaire',
            'intitule', 'actif',
            # Détails
            'objectif_principal', 'objectif_secondaire',
            'cibles_principales', 'cible_secondaire',
            'taxon_taxref', 'habitat_ref', 'habitats',
            'date_lancement_suivi',
            # Protocole (nested)
            'protocole',
            # Bancarisation
            'outil_bancarisation', 'bancarisation_label',
            'outil_saisie', 'outil_saisie_label',
            'transmission_donnee',
            # Audit
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_suivi_inventaire', 'date_ajout', 'date_maj']

    def _resolve_nomenclature_label(self, mnemonique, type_mnemonique):
        if not mnemonique:
            return None
        from apps.core.models import Nomenclature
        nom = Nomenclature.objects.filter(
            mnemonique=mnemonique,
            id_type__mnemonique=type_mnemonique
        ).first()
        return nom.label if nom else mnemonique

    def get_bancarisation_label(self, obj):
        return self._resolve_nomenclature_label(obj.outil_bancarisation, 'BANCARISATION_STOCKAGE')

    def get_outil_saisie_label(self, obj):
        return self._resolve_nomenclature_label(obj.outil_saisie, 'OUTIL_SAISIE')


class SuiviInventaireWriteSerializer(serializers.ModelSerializer):
    """Serializer pour un suivi/inventaire (écriture, accepte protocole nested)."""
    protocole = ProtocoleSerializer(required=False, allow_null=True)

    class Meta:
        model = SuiviInventaire
        fields = [
            'id_suivi_inventaire',
            'intitule', 'actif',
            # Détails
            'objectif_principal', 'objectif_secondaire',
            'cibles_principales', 'cible_secondaire',
            'taxon_taxref', 'habitat_ref', 'habitats',
            'date_lancement_suivi',
            # Protocole (nested writable)
            'protocole',
            # Bancarisation
            'outil_bancarisation', 'outil_saisie', 'transmission_donnee',
        ]
        read_only_fields = ['id_suivi_inventaire']


# =============================================================================
# Serializer détaillé
# =============================================================================

def _operation_enjeu_slug(obj):
    """Slug du premier enjeu atteint via les métriques de l'action.

    Chemins possibles : Indicateur → NE → OLT → Enjeu, ou
    Indicateur → RA → OO → Pression (M2M) → FI → Enjeu.
    Sert à ramener l'utilisateur à la position de l'action dans l'architecture
    du plan depuis la fiche action (#531).
    """
    for met in obj.metriques.all():
        if not met.id_indicateur_id:
            continue
        indicateur = met.id_indicateur
        # Chemin NE (onglet OLT)
        try:
            ne = indicateur.id_ne
            if ne and ne.id_olt and ne.id_olt.id_enjeu:
                return ne.id_olt.id_enjeu.slug
        except AttributeError:
            pass
        # Chemin RA (onglet Opérations)
        try:
            ra = indicateur.id_resultat_attendu
            if ra and ra.id_oo:
                pression = ra.id_oo.pressions.select_related(
                    'id_facteur_influence__id_enjeu').first()
                if pression and pression.id_facteur_influence and pression.id_facteur_influence.id_enjeu:
                    return pression.id_facteur_influence.id_enjeu.slug
        except AttributeError:
            pass
    return None


class OperationSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une Opération."""
    priorite_label = serializers.CharField(source='id_priorite.label', read_only=True)
    type_action_label = serializers.SerializerMethodField()
    categorie_action_reserve_label = serializers.SerializerMethodField()
    categorie_action_reserve_code = serializers.SerializerMethodField()
    code_prefix = serializers.CharField(read_only=True)
    code_affichage = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    metriques = serializers.SerializerMethodField()
    metrique_ids = serializers.SerializerMethodField()
    site_ids = serializers.SerializerMethodField()
    nb_sites = serializers.SerializerMethodField()
    # #531 — slug de l'enjeu parent, pour naviguer vers la position de l'action
    # dans l'architecture du plan depuis la fiche action.
    enjeu_slug = serializers.SerializerMethodField()
    operation_annees = OperationAnneeSerializer(many=True, read_only=True)
    finances = FinanceOperationSerializer(many=True, read_only=True)
    suivi_inventaire = SuiviInventaireSerializer(source='id_suivi', read_only=True)
    geom_geojson = serializers.SerializerMethodField()
    # #355/#379 — statut de réalisation global (sur la période)
    niveau_realisation_global_mnemonique = serializers.SerializerMethodField()
    niveau_realisation_global_label = serializers.SerializerMethodField()
    niveau_realisation_global_manuel = serializers.SerializerMethodField()
    niveau_realisation_global_commentaire = serializers.SerializerMethodField()

    def get_niveau_realisation_global_mnemonique(self, obj):
        return obj.get_niveau_realisation_global()

    def get_niveau_realisation_global_label(self, obj):
        return obj.get_niveau_realisation_global_label()

    def get_niveau_realisation_global_manuel(self, obj):
        return obj.is_niveau_realisation_global_manuel()

    def get_niveau_realisation_global_commentaire(self, obj):
        return obj.get_niveau_realisation_global_commentaire()

    class Meta:
        model = Operation
        fields = [
            'id_operation', 'libelle', 'ordre', 'statut',
            'id_priorite', 'priorite_label',
            'id_type_action', 'type_action_label',
            'id_categorie_action_reserve', 'categorie_action_reserve_label',
            'categorie_action_reserve_code',
            'code_prefix', 'code_affichage', 'numero_manuel',
            'id_referentiel_operations', 'code_operation',
            'description',
            'annee_min', 'annee_max',
            # Suivi/inventaire
            'est_suivi_existant', 'id_suivi', 'suivi_inventaire',
            # Fréquence & acteurs
            'frequence_nombre', 'frequence_unite',
            'operateurs', 'partenaires', 'financeurs',
            'programmation_annuelle', 'programmation_mensuelle',
            'programmation_mensuelle_defaut',
            'ventilation_mode',
            'geom', 'geom_geojson',
            'id_indicateur',
            'metriques', 'metrique_ids',
            'site_ids', 'nb_sites', 'enjeu_slug',
            'operation_annees', 'finances',
            'niveau_realisation_global_mnemonique',
            'niveau_realisation_global_label',
            'niveau_realisation_global_manuel',
            'niveau_realisation_global_commentaire',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_operation', 'date_ajout', 'date_maj']

    def get_enjeu_slug(self, obj):
        return _operation_enjeu_slug(obj)

    def get_geom_geojson(self, obj):
        """Emprise spatiale au format GeoJSON (consommable par Leaflet)."""
        if not obj.geom:
            return None
        import json
        try:
            return json.loads(obj.geom.geojson)
        except (AttributeError, ValueError, TypeError):
            return None

    def get_type_action_label(self, obj):
        if obj.id_type_action:
            return obj.id_type_action.label
        return None

    def get_categorie_action_reserve_label(self, obj):
        if obj.id_categorie_action_reserve_id:
            return obj.id_categorie_action_reserve.label
        return None

    def get_categorie_action_reserve_code(self, obj):
        if obj.id_categorie_action_reserve_id:
            return obj.id_categorie_action_reserve.cd_nomenclature
        return None

    def get_code_affichage(self, obj):
        cache = self.context.get('operation_codes') if self.context else None
        if cache is not None:
            return cache.get(obj.id_operation)
        return _compute_operation_code_affichage(obj)

    def get_metriques(self, obj):
        # Use prefetched data if available — avoids extra query
        result = []
        for m in obj.metriques.all():
            ind_type = getattr(getattr(m.id_indicateur, 'type_indicateur', None), 'mnemonique', None) if m.id_indicateur_id else None
            data = {
                'id_metrique': m.id_metrique,
                'nom_metrique': m.nom_metrique,
                'indicateur_id': m.id_indicateur_id,
                'indicateur_nom': getattr(m.id_indicateur, 'nom_indicateur', None) if m.id_indicateur_id else None,
                # #347/réponse — type de l'indicateur (ETAT/PRESSION/REPONSE) pour
                # distinguer les indicateurs de réponse des métriques associées.
                'indicateur_type': ind_type,
                'etat_reference': m.etat_reference or '',
                'type_metrique_id': m.type_metrique_id,
                'type_metrique_label': getattr(m.type_metrique, 'label', None) if m.type_metrique_id else None,
            }
            # #452/#464/#465 — grille + format exposés pour TOUTES les métriques en
            # grille (indicateurs de réponse ET métriques d'état/pression associées) :
            # la saisie du résultat propose alors un select des options de la grille
            # (libellés TEXTE / valeurs CHIFFRE) au lieu d'un champ texte libre.
            data.update(_response_metrique_grid(m))
            result.append(data)
        return result

    def get_metrique_ids(self, obj):
        # #398 — n'expose QUE les métriques État/Pression « associées » à l'action.
        # Les métriques d'indicateurs de réponse appartiennent à leur indicateur de
        # réponse et sont gérées à part : elles ne doivent pas transiter par cette
        # liste, qui pilote la (re)synchronisation des liens op↔métrique au save.
        return [
            m.id_metrique for m in obj.metriques.all()
            if getattr(getattr(m.id_indicateur, 'type_indicateur', None), 'mnemonique', None) != 'REPONSE'
        ]

    def get_site_ids(self, obj):
        return [s.id_site for s in obj.sites.all()]

    def get_nb_sites(self, obj):
        return len(obj.sites.all()) if hasattr(obj, '_prefetched_objects_cache') and 'sites' in obj._prefetched_objects_cache else obj.sites.count()


# =============================================================================
# Serializer léger (pour listes et imbrication dans IndicateurSerializer)
# =============================================================================

class OperationListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Opérations."""
    priorite_label = serializers.CharField(source='id_priorite.label', read_only=True)
    type_action_label = serializers.SerializerMethodField()
    categorie_action_reserve_label = serializers.SerializerMethodField()
    categorie_action_reserve_code = serializers.SerializerMethodField()
    code_prefix = serializers.CharField(read_only=True)
    code_affichage = serializers.SerializerMethodField()
    createur_nom = serializers.CharField(source='id_utilisateur_ajout.get_full_name', read_only=True)
    metriques = serializers.SerializerMethodField()
    metrique_ids = serializers.SerializerMethodField()
    nb_sites = serializers.SerializerMethodField()
    nb_operation_annees = serializers.SerializerMethodField()
    nb_finances = serializers.SerializerMethodField()
    enjeu_slug = serializers.SerializerMethodField()
    oo_id = serializers.SerializerMethodField()
    # #355 — Niveau de réalisation GLOBAL (sur la période) : surcharge si présente,
    # sinon calcul automatique sur les années programmées.
    niveau_realisation_global_mnemonique = serializers.SerializerMethodField()
    niveau_realisation_global_label = serializers.SerializerMethodField()
    niveau_realisation_global_manuel = serializers.SerializerMethodField()

    class Meta:
        model = Operation
        fields = [
            'id_operation', 'libelle', 'ordre', 'statut',
            'id_priorite', 'priorite_label',
            'id_type_action', 'type_action_label',
            'id_categorie_action_reserve', 'categorie_action_reserve_label',
            'categorie_action_reserve_code',
            'code_prefix', 'code_affichage', 'numero_manuel',
            'id_referentiel_operations', 'code_operation',
            'description',
            'annee_min', 'annee_max',
            # Suivi/inventaire
            'est_suivi_existant', 'id_suivi',
            # Fréquence & acteurs
            'frequence_nombre', 'frequence_unite',
            'operateurs', 'partenaires', 'financeurs',
            'programmation_annuelle', 'programmation_mensuelle',
            'programmation_mensuelle_defaut',
            'id_indicateur',
            'metriques', 'metrique_ids',
            'nb_sites',
            'nb_operation_annees', 'nb_finances',
            'enjeu_slug', 'oo_id',
            'niveau_realisation_global_mnemonique',
            'niveau_realisation_global_label',
            'niveau_realisation_global_manuel',
            'date_ajout', 'date_maj', 'createur_nom'
        ]
        read_only_fields = ['id_operation', 'date_ajout', 'date_maj']

    def get_niveau_realisation_global_mnemonique(self, obj):
        return obj.get_niveau_realisation_global()

    def get_niveau_realisation_global_label(self, obj):
        return obj.get_niveau_realisation_global_label()

    def get_niveau_realisation_global_manuel(self, obj):
        return obj.is_niveau_realisation_global_manuel()

    def get_type_action_label(self, obj):
        if obj.id_type_action:
            return obj.id_type_action.label
        return None

    def get_categorie_action_reserve_label(self, obj):
        if obj.id_categorie_action_reserve_id:
            return obj.id_categorie_action_reserve.label
        return None

    def get_categorie_action_reserve_code(self, obj):
        if obj.id_categorie_action_reserve_id:
            return obj.id_categorie_action_reserve.cd_nomenclature
        return None

    def get_code_affichage(self, obj):
        cache = self.context.get('operation_codes') if self.context else None
        if cache is not None:
            return cache.get(obj.id_operation)
        return _compute_operation_code_affichage(obj)

    def get_metriques(self, obj):
        result = []
        for m in obj.metriques.all():
            ind_type = getattr(getattr(m.id_indicateur, 'type_indicateur', None), 'mnemonique', None) if m.id_indicateur_id else None
            data = {
                'id_metrique': m.id_metrique,
                'nom_metrique': m.nom_metrique,
                'indicateur_id': m.id_indicateur_id,
                'indicateur_nom': getattr(m.id_indicateur, 'nom_indicateur', None) if m.id_indicateur_id else None,
                'indicateur_type': ind_type,
            }
            # #452/#464/#465 — grille + format exposés pour TOUTES les métriques en
            # grille (indicateurs de réponse ET métriques d'état/pression associées) :
            # la saisie du résultat propose alors un select des options de la grille
            # (libellés TEXTE / valeurs CHIFFRE) au lieu d'un champ texte libre.
            data.update(_response_metrique_grid(m))
            result.append(data)
        return result

    def get_metrique_ids(self, obj):
        # #398 — n'expose QUE les métriques État/Pression « associées » à l'action.
        # Les métriques d'indicateurs de réponse appartiennent à leur indicateur de
        # réponse et sont gérées à part : elles ne doivent pas transiter par cette
        # liste, qui pilote la (re)synchronisation des liens op↔métrique au save.
        return [
            m.id_metrique for m in obj.metriques.all()
            if getattr(getattr(m.id_indicateur, 'type_indicateur', None), 'mnemonique', None) != 'REPONSE'
        ]

    def get_nb_sites(self, obj):
        return len(obj.sites.all()) if hasattr(obj, '_prefetched_objects_cache') and 'sites' in obj._prefetched_objects_cache else obj.sites.count()

    def get_nb_operation_annees(self, obj):
        return len(obj.operation_annees.all()) if hasattr(obj, '_prefetched_objects_cache') and 'operation_annees' in obj._prefetched_objects_cache else obj.operation_annees.count()

    def get_nb_finances(self, obj):
        return len(obj.finances.all()) if hasattr(obj, '_prefetched_objects_cache') and 'finances' in obj._prefetched_objects_cache else obj.finances.count()

    def _get_enjeu_via_ne(self, indicateur):
        """Traverse NE path: Indicateur → NE → OLT → Enjeu."""
        try:
            ne = indicateur.id_ne
            if ne and ne.id_olt and ne.id_olt.id_enjeu:
                return ne.id_olt.id_enjeu
        except AttributeError:
            pass
        return None

    def _get_enjeu_and_oo_via_ra(self, indicateur):
        """Traverse RA path: Indicateur → RA → OO → Pressions (M2M) → FI → Enjeu."""
        try:
            ra = indicateur.id_resultat_attendu
            if ra and ra.id_oo:
                pression = ra.id_oo.pressions.select_related('id_facteur_influence__id_enjeu').first()
                if pression and pression.id_facteur_influence and pression.id_facteur_influence.id_enjeu:
                    return pression.id_facteur_influence.id_enjeu, ra.id_oo.id_oo
        except AttributeError:
            pass
        return None, None

    def get_enjeu_slug(self, obj):
        """Retourne le slug du premier enjeu trouvé via les métriques."""
        for met in obj.metriques.all():
            if not met.id_indicateur_id:
                continue
            indicateur = met.id_indicateur
            enjeu = self._get_enjeu_via_ne(indicateur)
            if enjeu:
                return enjeu.slug
            enjeu, _ = self._get_enjeu_and_oo_via_ra(indicateur)
            if enjeu:
                return enjeu.slug
        return None

    def get_oo_id(self, obj):
        """Retourne l'id du premier OO trouvé via les métriques."""
        for met in obj.metriques.all():
            if not met.id_indicateur_id:
                continue
            indicateur = met.id_indicateur
            _, oo_id = self._get_enjeu_and_oo_via_ra(indicateur)
            if oo_id:
                return oo_id
        return None


class OperationNestedSerializer(OperationListSerializer):
    """Serializer pour les opérations imbriquées dans les métriques.

    Étend OperationListSerializer avec operation_annees et finances
    pour afficher les données de programmation dans la vue détail,
    sans les champs coûteux (enjeu_slug, oo_id) du serializer complet.

    #263 — `enjeu_slug` et `oo_id` étaient effectivement listés dans
    Meta.fields hérités → ils déclenchaient un N+1 massif (traversée
    métrique → indicateur → NE/RA → OLT/OO → enjeu/pression) à chaque
    opération nichée. On les exclut explicitement.
    """
    operation_annees = OperationAnneeSerializer(many=True, read_only=True)
    finances = FinanceOperationSerializer(many=True, read_only=True)

    class Meta(OperationListSerializer.Meta):
        fields = [
            f for f in OperationListSerializer.Meta.fields
            if f not in ('nb_operation_annees', 'nb_finances', 'enjeu_slug', 'oo_id')
        ] + ['operation_annees', 'finances', 'ventilation_mode']


# =============================================================================
# Serializer de création/modification
# =============================================================================

class OperationAnneeOrganismeWriteSerializer(serializers.Serializer):
    """Write serializer for organisme budget data within an operation year."""
    id_organisme = serializers.IntegerField()
    budget_fonctionnement = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    budget_investissement = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    etp = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)


class OperationAnneeWriteSerializer(serializers.Serializer):
    """Write serializer for operation year with nested organismes."""
    annee = serializers.IntegerField()
    periodicite = serializers.BooleanField(default=False)
    budget = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    etp = serializers.DecimalField(max_digits=8, decimal_places=2, required=False, allow_null=True)
    budget_fonctionnement = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    budget_investissement = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    periodicite_mensuelle = serializers.JSONField(default=dict, required=False)
    geom = serializers.JSONField(required=False, allow_null=True, default=None)
    organismes = OperationAnneeOrganismeWriteSerializer(many=True, required=False, default=[])


class OperationCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création/modification d'une Opération."""
    site_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=[]
    )
    metrique_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=[]
    )
    operation_annees = OperationAnneeWriteSerializer(many=True, required=False, default=[])
    finances = FinanceOperationSerializer(many=True, required=False, default=[])
    suivi_inventaire = SuiviInventaireWriteSerializer(required=False, allow_null=True, write_only=True)
    # Emprise spatiale acceptée en GeoJSON (cohérent avec `geom_realisee` de la
    # réalisation et `geom_geojson` du serializer de lecture).
    geom_geojson = GeoJSONGeometryField(source='geom', required=False, allow_null=True)

    class Meta:
        model = Operation
        fields = [
            'id_operation', 'libelle', 'ordre', 'statut',
            'id_priorite', 'id_type_action',
            'id_categorie_action_reserve',
            'id_indicateur',
            'id_referentiel_operations', 'code_operation', 'numero_manuel',
            'description',
            'annee_min', 'annee_max',
            # Suivi/inventaire
            'est_suivi_existant', 'id_suivi', 'suivi_inventaire',
            # Fréquence & acteurs
            'frequence_nombre', 'frequence_unite',
            'operateurs', 'partenaires', 'financeurs',
            'programmation_annuelle', 'programmation_mensuelle',
            'programmation_mensuelle_defaut',
            'ventilation_mode',
            'geom_geojson',
            'metrique_ids', 'site_ids',
            'operation_annees', 'finances'
        ]
        read_only_fields = ['id_operation']
        extra_kwargs = {
            'id_suivi': {'required': False, 'allow_null': True},
            'id_categorie_action_reserve': {'required': False, 'allow_null': True},
            # #367 — rattachement direct à un indicateur (optionnel)
            'id_indicateur': {'required': False, 'allow_null': True},
        }

    def to_representation(self, instance):
        """Use the read serializer for the response."""
        return OperationSerializer(instance, context=self.context).data

    def _create_operation_annees(self, operation, annees_data):
        """Create OperationAnnee objects with nested organismes."""
        if not annees_data:
            return
        for annee_data in annees_data:
            organismes_data = annee_data.pop('organismes', [])
            annee_obj = OperationAnnee.objects.create(id_operation=operation, **annee_data)
            if organismes_data:
                OperationAnneeOrganisme.objects.bulk_create([
                    OperationAnneeOrganisme(
                        id_operation_annee=annee_obj,
                        id_organisme_id=org['id_organisme'],
                        budget_fonctionnement=org.get('budget_fonctionnement'),
                        budget_investissement=org.get('budget_investissement'),
                        etp=org.get('etp'),
                    )
                    for org in organismes_data
                ])

    def _create_finances(self, operation, finances_data):
        """Create FinanceOperation objects in bulk."""
        if not finances_data:
            return
        FinanceOperation.objects.bulk_create([
            FinanceOperation(id_operation=operation, **finance)
            for finance in finances_data
        ])

    def create(self, validated_data):
        site_ids = validated_data.pop('site_ids', [])
        metrique_ids = validated_data.pop('metrique_ids', [])
        annees_data = validated_data.pop('operation_annees', [])
        finances_data = validated_data.pop('finances', [])
        suivi_data = validated_data.pop('suivi_inventaire', None)

        # #398 — garantir le rattachement à un indicateur : si aucun
        # `id_indicateur` n'est fourni mais des métriques le sont, on déduit
        # l'indicateur de la première métrique. Une action sans indicateur
        # n'apparaît sous aucun indicateur (orpheline).
        if not validated_data.get('id_indicateur') and metrique_ids:
            from .models_indicateurs import Metrique
            first_met = Metrique.objects.filter(id_metrique__in=metrique_ids).first()
            if first_met and first_met.id_indicateur_id:
                validated_data['id_indicateur'] = first_met.id_indicateur

        # Create SuiviInventaire if provided
        if suivi_data:
            user = validated_data.get('id_utilisateur_ajout')
            protocole_data = suivi_data.pop('protocole', None)

            # Create Protocole if provided
            protocole = None
            if protocole_data:
                protocole = Protocole.objects.create(
                    id_utilisateur_ajout=user,
                    **protocole_data
                )

            suivi = SuiviInventaire.objects.create(
                id_utilisateur_ajout=user,
                id_protocole=protocole,
                **suivi_data
            )
            validated_data['id_suivi'] = suivi

        operation = Operation.objects.create(**validated_data)

        # M2M sites
        if site_ids:
            from apps.users.models import Site
            sites = Site.objects.filter(id_site__in=site_ids)
            for site in sites:
                CorOperationSite.objects.create(
                    id_operation=operation,
                    id_site=site
                )

        # M2M metriques
        if metrique_ids:
            from .models_indicateurs import Metrique
            for met in Metrique.objects.filter(id_metrique__in=metrique_ids):
                CorOperationMetrique.objects.create(
                    id_operation=operation,
                    id_metrique=met
                )

        # Nested: operation_annees and finances
        self._create_operation_annees(operation, annees_data)
        self._create_finances(operation, finances_data)

        return operation

    def update(self, instance, validated_data):
        site_ids = validated_data.pop('site_ids', None)
        metrique_ids = validated_data.pop('metrique_ids', None)
        annees_data = validated_data.pop('operation_annees', None)
        finances_data = validated_data.pop('finances', None)
        suivi_data = validated_data.pop('suivi_inventaire', None)

        # Handle nested suivi_inventaire
        if suivi_data is not None:
            user = validated_data.get('id_utilisateur_maj') or instance.id_utilisateur_ajout
            protocole_data = suivi_data.pop('protocole', None)

            if instance.id_suivi:
                # Handle protocole nested in suivi
                if protocole_data is not None:
                    if instance.id_suivi.id_protocole:
                        # Update existing Protocole
                        for attr, value in protocole_data.items():
                            setattr(instance.id_suivi.id_protocole, attr, value)
                        instance.id_suivi.id_protocole.id_utilisateur_maj = user
                        instance.id_suivi.id_protocole.save()
                    else:
                        # Create new Protocole
                        protocole = Protocole.objects.create(
                            id_utilisateur_ajout=user,
                            **protocole_data
                        )
                        instance.id_suivi.id_protocole = protocole

                # Update existing SuiviInventaire
                for attr, value in suivi_data.items():
                    setattr(instance.id_suivi, attr, value)
                instance.id_suivi.id_utilisateur_maj = user
                instance.id_suivi.save()
            else:
                # Create new Protocole if provided
                protocole = None
                if protocole_data:
                    protocole = Protocole.objects.create(
                        id_utilisateur_ajout=user,
                        **protocole_data
                    )

                # Create new SuiviInventaire
                suivi = SuiviInventaire.objects.create(
                    id_utilisateur_ajout=user,
                    id_protocole=protocole,
                    **suivi_data
                )
                validated_data['id_suivi'] = suivi

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Replace M2M sites
        if site_ids is not None:
            CorOperationSite.objects.filter(id_operation=instance).delete()
            from apps.users.models import Site
            sites = Site.objects.filter(id_site__in=site_ids)
            for site in sites:
                CorOperationSite.objects.create(
                    id_operation=instance,
                    id_site=site
                )

        # Replace M2M metriques — UNIQUEMENT les liens vers des métriques
        # État/Pression. Les liens vers les métriques d'indicateurs de réponse
        # sont gérés séparément (create-indicator / suppression de l'indicateur)
        # et ne doivent pas être réécrits ici (#398).
        if metrique_ids is not None:
            CorOperationMetrique.objects.filter(
                id_operation=instance,
            ).exclude(
                id_metrique__id_indicateur__type_indicateur__mnemonique='REPONSE',
            ).delete()
            from .models_indicateurs import Metrique
            for met in Metrique.objects.filter(id_metrique__in=metrique_ids):
                CorOperationMetrique.objects.get_or_create(
                    id_operation=instance,
                    id_metrique=met,
                )

        # Replace nested operation_annees (delete + recreate)
        if annees_data is not None:
            OperationAnnee.objects.filter(id_operation=instance).delete()
            self._create_operation_annees(instance, annees_data)

        # Replace nested finances (delete + recreate)
        if finances_data is not None:
            FinanceOperation.objects.filter(id_operation=instance).delete()
            self._create_finances(instance, finances_data)

        return instance
