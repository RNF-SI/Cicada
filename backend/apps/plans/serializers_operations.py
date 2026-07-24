"""
Serializers pour l'API REST Opérations (Actions).
"""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models_operations import (
    Protocole, SuiviInventaire,
    Operation, CorOperationSite, CorOperationMetrique,
    OperationAnnee, OperationAnneeOrganisme, FinanceOperation,
    RealisationOperationAnnee, RealisationOperationAnneeOrganisme,
    Fonction, Poste, PosteFonction,
    OperationAnneeRH, RealisationOperationAnneeRH,
    CategorieDepense,
)


# =============================================================================
# Helpers — code d'affichage des opérations (#228 / 2026-05-12)
# =============================================================================

# #486 — Clé sous laquelle le code d'une action *pas encore enregistrée* est
# renvoyé par `compute_operation_codes_for_plan(..., pending=...)`. Volontairement
# non entière pour ne jamais entrer en collision avec un `id_operation`.
PENDING_OPERATION_KEY = '__pending__'


def compute_operation_codes_for_plan(plan_id, overrides=None, pending=None):
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

    #486 — Prévisualisation avant enregistrement. Deux paramètres optionnels
    permettent de simuler l'état du formulaire sans rien persister :

      - `overrides` : {id_operation: {'code_prefix': 'CS', 'numero_manuel': 3}}
        remplace, pour l'action en cours d'édition, les valeurs en base. Une
        clé présente à None est honorée (retour à la numérotation auto).
      - `pending` : {'code_prefix': 'CS', 'numero_manuel': None,
        'id_metrique': X} ou {'…', 'id_indicateur': Y} — action pas encore
        créée, insérée en FIN de la liste d'actions de son parent (c'est la
        position que lui donnera la création). Son code est renvoyé sous la
        clé `PENDING_OPERATION_KEY`.

    Retour : dict {id_operation: 'CS1', ...}.
    """
    overrides = overrides or {}
    # Import local pour éviter les cycles d'import.
    from django.db.models import Prefetch
    from .models import PlanGestion
    from .models_enjeux import (
        Enjeu, CorFacteurEnjeu, Pression,
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
    # #552 — Un facteur peut être partagé entre plusieurs enjeux : son ordre
    # d'affichage est propre à chaque enjeu et porté par la table de liaison
    # CorFacteurEnjeu (et non plus par le facteur). On parcourt donc les liens
    # triés par `ordre`, en préchargeant le facteur et ses pressions.
    cor_facteur_qs = (
        CorFacteurEnjeu.objects
        .order_by('ordre', 'id')
        .select_related('id_facteur_influence')
        .prefetch_related(
            Prefetch('id_facteur_influence__pressions', queryset=pression_qs)
        )
    )
    enjeux = (
        Enjeu.objects
        .filter(id_pg=plan)
        .order_by('ordre', 'id_enjeu')
        .prefetch_related(
            Prefetch('objectifs_long_terme', queryset=olt_qs),
            Prefetch('cor_facteurs', queryset=cor_facteur_qs),
        )
    )

    seen_op_ids = []
    operations_by_id = {}
    seen_oos = set()

    # #486 — parent de l'action en cours de création (non enregistrée).
    pending_metrique_id = (pending or {}).get('id_metrique')
    pending_indicateur_id = (pending or {}).get('id_indicateur')

    def append_pending_if_parent(kind, parent_id):
        """Insère l'action pending en fin de liste de son parent (#486)."""
        if pending is None or PENDING_OPERATION_KEY in operations_by_id:
            return
        expected = pending_metrique_id if kind == 'metrique' else pending_indicateur_id
        if expected is not None and expected == parent_id:
            operations_by_id[PENDING_OPERATION_KEY] = None
            seen_op_ids.append(PENDING_OPERATION_KEY)

    def visit_indicateur_metriques(indicateur):
        # `metriques.all()` et `operations.all()` puisent dans le prefetch
        # (déjà trié au niveau de la queryset) — aucune nouvelle requête.
        for metrique in indicateur.metriques.all():
            for op in metrique.operations.all():
                if op.pk in operations_by_id:
                    continue
                operations_by_id[op.pk] = op
                seen_op_ids.append(op.pk)
            append_pending_if_parent('metrique', metrique.pk)
        # #367 — actions rattachées directement à l'indicateur (sans métrique)
        for op in indicateur.operations.all():
            if op.pk in operations_by_id:
                continue
            operations_by_id[op.pk] = op
            seen_op_ids.append(op.pk)
        append_pending_if_parent('indicateur', indicateur.pk)

    for enjeu in enjeux:
        # Branche NE : Enjeu → OLT → NE → Indicateur → Métrique → Action
        for olt in enjeu.objectifs_long_terme.all():
            for ne in olt.niveaux_exigence.all():
                for indicateur in ne.indicateurs.all():
                    visit_indicateur_metriques(indicateur)

        # Branche OO/RA : Enjeu → Facteur → Pression → OO → RA → Indic → Met → Action
        # (#552 — via CorFacteurEnjeu, trié par l'ordre propre à cet enjeu)
        for cor_facteur in enjeu.cor_facteurs.all():
            facteur = cor_facteur.id_facteur_influence
            for pression in facteur.pressions.all():
                for oo in pression.objectifs_operationnels.all():
                    if oo.pk in seen_oos:
                        continue
                    seen_oos.add(oo.pk)
                    for ra in oo.resultats_attendus.all():
                        for indicateur in ra.indicateurs.all():
                            visit_indicateur_metriques(indicateur)

    # #486 — L'action en création dont le parent n'a pas été atteint (métrique
    # orpheline, indicateur hors arbre…) est tout de même numérotée, en fin de
    # parcours, pour ne jamais laisser le formulaire sans aperçu.
    if pending is not None and PENDING_OPERATION_KEY not in operations_by_id:
        operations_by_id[PENDING_OPERATION_KEY] = None
        seen_op_ids.append(PENDING_OPERATION_KEY)

    def resolve(op_id):
        """(prefix, numero_manuel) effectifs, overrides #486 appliqués."""
        if op_id == PENDING_OPERATION_KEY:
            return pending.get('code_prefix') or 'AC', pending.get('numero_manuel')
        op = operations_by_id[op_id]
        override = overrides.get(op_id)
        if override is None:
            return op.code_prefix, op.numero_manuel
        prefix = override['code_prefix'] if 'code_prefix' in override else op.code_prefix
        numero = override['numero_manuel'] if 'numero_manuel' in override else op.numero_manuel
        return prefix or 'AC', numero

    # Calcul des rangs par préfixe dans l'ordre rencontré.
    # #485 — Un numéro fixé manuellement (`numero_manuel`) est réservé pour son
    # préfixe : l'action garde ce numéro quel que soit l'ordre (drag & drop),
    # et l'auto-numérotation des autres actions du même préfixe saute cet indice.
    reserved = {}
    for op_id in seen_op_ids:
        prefix, numero_manuel = resolve(op_id)
        if numero_manuel:
            reserved.setdefault(prefix, set()).add(numero_manuel)

    counters = {}
    codes = {}
    for op_id in seen_op_ids:
        prefix, numero_manuel = resolve(op_id)
        if numero_manuel:
            codes[op_id] = f"{prefix}{numero_manuel}"
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
            # #600 (Q2b) — coût stage réalisé (miroir du prévisionnel).
            'cout_stage_realise',
            # #608 — détail des coûts réalisés (ventilation maximale).
            'cout_prestataire_realise', 'autre_cout_realise', 'autre_cout_commentaire_realise',
            'cout_prestataire_invest_realise', 'autre_cout_invest_realise',
            'autre_cout_invest_commentaire_realise',
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_realisation_op_annee_organisme', 'date_ajout', 'date_maj']


# =============================================================================
# Ressources humaines (#560) — fonctions, postes du PG, lignes RH
# =============================================================================

class FonctionSerializer(serializers.ModelSerializer):
    """Fonction / poste du référentiel global (#560, #596)."""
    type_poste_display = serializers.CharField(
        source='get_type_poste_display', read_only=True
    )

    class Meta:
        model = Fonction
        fields = [
            'id_fonction', 'libelle', 'type_poste', 'type_poste_display',
            'finance_par_defaut', 'is_socle', 'actif',
        ]
        read_only_fields = ['id_fonction', 'is_socle', 'type_poste_display']


class PosteFonctionSerializer(serializers.ModelSerializer):
    """Fonction portée par un poste (lecture)."""
    fonction_libelle = serializers.CharField(source='id_fonction.libelle', read_only=True)
    finance_par_defaut = serializers.BooleanField(
        source='id_fonction.finance_par_defaut', read_only=True
    )
    type_poste = serializers.CharField(source='id_fonction.type_poste', read_only=True)

    class Meta:
        model = PosteFonction
        fields = [
            'id_poste_fonction', 'id_fonction', 'fonction_libelle',
            'finance_par_defaut', 'type_poste', 'pourcentage',
        ]
        read_only_fields = ['id_poste_fonction']


class PosteFonctionWriteSerializer(serializers.Serializer):
    """Fonction portée par un poste (écriture imbriquée)."""
    id_fonction = serializers.IntegerField()
    pourcentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )


class PosteSerializer(serializers.ModelSerializer):
    """Poste d'un plan de gestion (lecture). Aucun nominatif (RGPD)."""
    fonctions = PosteFonctionSerializer(many=True, read_only=True)
    organisme_nom = serializers.CharField(source='id_organisme.nom_organisme', read_only=True)
    organisme_affichage = serializers.CharField(read_only=True)
    libelle = serializers.CharField(read_only=True)
    finance_par_defaut = serializers.SerializerMethodField()

    class Meta:
        model = Poste
        fields = [
            'id_poste', 'id_pg', 'libelle',
            'id_organisme', 'organisme_nom', 'organisme_libre', 'organisme_affichage',
            'nombre', 'etp', 'cout_jour', 'fonctions', 'finance_par_defaut',
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_poste', 'libelle', 'organisme_affichage', 'date_ajout', 'date_maj']

    def get_finance_par_defaut(self, obj):
        return obj.is_finance_par_defaut()


class PosteWriteSerializer(serializers.ModelSerializer):
    """Poste d'un plan de gestion (écriture, fonctions imbriquées)."""
    fonctions = PosteFonctionWriteSerializer(many=True, required=False, default=[])

    class Meta:
        model = Poste
        fields = [
            'id_poste', 'id_pg', 'id_organisme', 'organisme_libre',
            'nombre', 'etp', 'cout_jour', 'fonctions',
        ]
        read_only_fields = ['id_poste']
        extra_kwargs = {'id_organisme': {'required': False, 'allow_null': True}}

    def validate_fonctions(self, value):
        """
        Un poste se décrit de deux façons, pas d'un mélange des deux :

        - toutes les quotités vides → poste combiné (« garde animateur ») :
          chaque fonction s'applique à l'ensemble du temps ;
        - toutes renseignées → répartition explicite, dont la somme fait 100 %.
        """
        if not value:
            raise serializers.ValidationError(
                _("Un poste doit porter au moins une fonction.")
            )
        renseignees = [f for f in value if f.get('pourcentage') is not None]
        if not renseignees:
            return value
        if len(renseignees) != len(value):
            raise serializers.ValidationError(
                _("Renseignez la quotité de toutes les fonctions, ou d'aucune "
                  "(poste cumulant les fonctions sur tout son temps).")
            )
        total = sum(f['pourcentage'] for f in renseignees)
        if total != 100:
            raise serializers.ValidationError(
                _("La somme des quotités doit faire 100 %% (actuellement %(total)s %%).")
                % {'total': total}
            )
        return value

    def to_representation(self, instance):
        return PosteSerializer(instance, context=self.context).data

    def _set_fonctions(self, poste, fonctions_data):
        PosteFonction.objects.filter(id_poste=poste).delete()
        PosteFonction.objects.bulk_create([
            PosteFonction(
                id_poste=poste,
                id_fonction_id=f['id_fonction'],
                pourcentage=f.get('pourcentage'),
            )
            for f in fonctions_data
        ])

    def create(self, validated_data):
        fonctions_data = validated_data.pop('fonctions', [])
        poste = Poste.objects.create(**validated_data)
        self._set_fonctions(poste, fonctions_data)
        return poste

    def update(self, instance, validated_data):
        fonctions_data = validated_data.pop('fonctions', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if fonctions_data is not None:
            self._set_fonctions(instance, fonctions_data)
        return instance


class OperationAnneeRHSerializer(serializers.ModelSerializer):
    """Ligne RH prévisionnelle d'une année d'opération (lecture)."""
    poste_libelle = serializers.CharField(source='id_poste.libelle', read_only=True)
    organisme_nom = serializers.CharField(
        source='id_organisme.nom_organisme', read_only=True
    )
    # Organisme du poste : affiché sous le libellé du poste en déclinaison.
    poste_organisme_nom = serializers.CharField(
        source='id_poste.id_organisme.nom_organisme', read_only=True
    )
    # #600 — coût jour et organisme du poste, pour le calcul du coût salarial
    # (jours × coût jour) attribué à l'organisme, notamment dans la fiche action.
    poste_cout_jour = serializers.SerializerMethodField()
    poste_id_organisme = serializers.SerializerMethodField()
    categorie_depense_display = serializers.CharField(
        source='get_categorie_depense_display', read_only=True
    )

    class Meta:
        model = OperationAnneeRH
        fields = [
            'id_operation_annee_rh',
            'id_poste', 'poste_libelle', 'poste_organisme_nom',
            'poste_cout_jour', 'poste_id_organisme',
            'id_organisme', 'organisme_nom',
            'jours', 'finance', 'categorie_depense', 'categorie_depense_display',
        ]
        read_only_fields = ['id_operation_annee_rh']

    def get_poste_cout_jour(self, obj):
        return obj.id_poste.cout_jour if obj.id_poste_id else None

    def get_poste_id_organisme(self, obj):
        return obj.id_poste.id_organisme_id if obj.id_poste_id else None


class OperationAnneeRHWriteSerializer(serializers.Serializer):
    """Ligne RH prévisionnelle (écriture imbriquée dans operation_annees)."""
    id_poste = serializers.IntegerField(required=False, allow_null=True)
    id_organisme = serializers.IntegerField(required=False, allow_null=True)
    jours = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True
    )
    finance = serializers.BooleanField(required=False, default=True)
    categorie_depense = serializers.ChoiceField(
        choices=CategorieDepense.CHOICES, required=False, allow_blank=True, default=''
    )


class RealisationOperationAnneeRHSerializer(serializers.ModelSerializer):
    """Ligne RH réalisée d'une année d'opération (lecture + écriture imbriquée)."""
    poste_libelle = serializers.CharField(source='id_poste.libelle', read_only=True)
    organisme_nom = serializers.CharField(
        source='id_organisme.nom_organisme', read_only=True
    )
    poste_organisme_nom = serializers.CharField(
        source='id_poste.id_organisme.nom_organisme', read_only=True
    )
    categorie_depense_display = serializers.CharField(
        source='get_categorie_depense_display', read_only=True
    )

    class Meta:
        model = RealisationOperationAnneeRH
        fields = [
            'id_realisation_operation_annee_rh',
            # Lien vers la ligne prévisionnelle réalisée : permet au suivi de
            # ré-attribuer le temps (« c'est en fait ce poste-là qui l'a
            # fait ») sans que le prévu et le réel se retrouvent dissociés.
            'id_operation_annee_rh',
            'id_poste', 'poste_libelle', 'poste_organisme_nom',
            'id_organisme', 'organisme_nom',
            'jours', 'finance', 'categorie_depense', 'categorie_depense_display',
        ]
        read_only_fields = ['id_realisation_operation_annee_rh', 'categorie_depense_display']


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
    # #560 — lignes RH réalisées (écriture imbriquée, remplacement complet)
    rh_lignes = RealisationOperationAnneeRHSerializer(many=True, required=False)

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
            'rh_lignes',
            'date_ajout', 'date_maj', 'id_utilisateur_maj',
        ]
        read_only_fields = [
            'id_realisation_operation_annee', 'date_ajout', 'date_maj', 'id_utilisateur_maj',
        ]

    # #609 — mnémoniques des niveaux « réalisé » qui impliquent une périodicité
    # réalisée cochée. « Non réalisé » (ou vide) → périodicité décochée.
    _PERIODICITE_NIVEAUX = {'TERMINE', 'PARTIEL'}

    def validate(self, attrs):
        """
        #609 — La périodicité réalisée est DÉRIVÉE du niveau de réalisation :
        « réalisé » ou « partiellement réalisé » ⇒ cochée, « non réalisé » ⇒
        décochée. Le client ne saisit plus la case (supprimée de l'UI).
        """
        if 'id_niveau_realisation' in attrs:
            niveau = attrs.get('id_niveau_realisation')
            mnem = getattr(niveau, 'mnemonique', None)
            attrs['periodicite_realisee'] = mnem in self._PERIODICITE_NIVEAUX
        return attrs

    def _set_rh_lignes(self, instance, rh_data):
        RealisationOperationAnneeRH.objects.filter(
            id_realisation_operation_annee=instance
        ).delete()
        RealisationOperationAnneeRH.objects.bulk_create([
            RealisationOperationAnneeRH(
                id_realisation_operation_annee=instance,
                id_operation_annee_rh=rh.get('id_operation_annee_rh'),
                id_poste=rh.get('id_poste'),
                id_organisme=rh.get('id_organisme'),
                jours=rh.get('jours'),
                # bulk_create contourne save() : on réconcilie ici (#597).
                **dict(zip(
                    ('categorie_depense', 'finance'),
                    CategorieDepense.resolve(rh.get('categorie_depense'), rh.get('finance')),
                )),
            )
            for rh in rh_data
        ])

    def create(self, validated_data):
        rh_data = validated_data.pop('rh_lignes', None)
        instance = super().create(validated_data)
        if rh_data is not None:
            self._set_rh_lignes(instance, rh_data)
        return instance

    def update(self, instance, validated_data):
        rh_data = validated_data.pop('rh_lignes', None)
        instance = super().update(instance, validated_data)
        if rh_data is not None:
            self._set_rh_lignes(instance, rh_data)
        return instance


class OperationAnneeOrganismeSerializer(serializers.ModelSerializer):
    """Serializer pour la ventilation budget/travail par organisme."""
    organisme_nom = serializers.CharField(source='id_organisme.nom_organisme', read_only=True)
    realisation = RealisationOperationAnneeOrganismeSerializer(read_only=True)

    class Meta:
        model = OperationAnneeOrganisme
        fields = [
            'id_operation_annee_organisme',
            'id_organisme', 'organisme_nom',
            'budget_fonctionnement', 'budget_investissement',
            'cout_stage', 'cout_prestataire', 'autre_cout', 'autre_cout_commentaire',
            'cout_prestataire_invest', 'autre_cout_invest', 'autre_cout_invest_commentaire',
            'etp',
            'realisation',
        ]
        read_only_fields = ['id_operation_annee_organisme']


class OperationAnneeSerializer(serializers.ModelSerializer):
    """Serializer pour la programmation annuelle d'une opération."""
    organismes = OperationAnneeOrganismeSerializer(many=True, read_only=True)
    realisation = RealisationOperationAnneeSerializer(read_only=True)
    rh_lignes = OperationAnneeRHSerializer(many=True, read_only=True)

    class Meta:
        model = OperationAnnee
        fields = [
            'id_operation_annee', 'annee', 'periodicite',
            'budget', 'etp', 'budget_fonctionnement', 'budget_investissement',
            'periodicite_mensuelle', 'geom', 'organismes',
            'rh_lignes',
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


def pop_protocoles_data(data):
    """
    Extrait la liste de protocoles d'un payload de suivi (#252).

    Accepte `protocoles` (canonique, liste) et `protocole` (singulier, déprécié —
    conservé pour les clients qui n'envoient qu'un protocole). Retourne None quand
    aucune des deux clés n'est fournie, ce qui signifie « ne touche pas à la liste ».
    """
    protocoles_data = data.pop('protocoles', None)
    protocole_data = data.pop('protocole', None)

    if protocoles_data is not None:
        return protocoles_data
    if protocole_data is not None:
        return [protocole_data] if protocole_data else []
    return None


def sync_suivi_protocoles(suivi, protocoles_data, user):
    """
    Réécrit la liste des protocoles d'un suivi (#252).

    Sémantique « copy-on-write » : la liste reçue fait foi. Les protocoles sont
    recréés pour ce suivi, puis les lignes devenues orphelines (plus référencées
    par aucun suivi) sont supprimées. Deux suivis peuvent donc pointer le même
    protocole, mais éditer l'un ne modifie jamais l'autre — cf. « chaque protocole
    reste rattaché individuellement (pas de fusion conceptuelle) ».
    """
    if protocoles_data is None:
        return

    anciens = list(suivi.protocoles.all())
    nouveaux = [
        Protocole.objects.create(id_utilisateur_ajout=user, **data)
        for data in protocoles_data
    ]
    suivi.protocoles.set(nouveaux)

    # Purge des protocoles devenus orphelins (évite les lignes mortes dans
    # general.t_protocoles, qui s'accumulaient déjà avec l'ancienne FK).
    for ancien in anciens:
        if not ancien.suivis.exists():
            ancien.delete()


class SuiviInventaireSerializer(serializers.ModelSerializer):
    """Serializer pour un suivi/inventaire (lecture)."""
    protocoles = ProtocoleSerializer(many=True, read_only=True)
    protocole = serializers.SerializerMethodField()
    bancarisation_label = serializers.SerializerMethodField()
    outil_saisie_label = serializers.SerializerMethodField()
    # #571 — libellés lisibles des nomenclatures objectif/cible (les champs bruts
    # stockent le mnémonique, ex. OBJ_PHYSICO_CHIMIQUES / ABIOTIQUE).
    objectif_principal_label = serializers.SerializerMethodField()
    objectif_secondaire_label = serializers.SerializerMethodField()
    cibles_principales_label = serializers.SerializerMethodField()
    cible_secondaire_label = serializers.SerializerMethodField()

    class Meta:
        model = SuiviInventaire
        fields = [
            'id_suivi_inventaire',
            'intitule', 'actif',
            # Détails
            'objectif_principal', 'objectif_principal_label',
            'objectif_secondaire', 'objectif_secondaire_label',
            'cibles_principales', 'cibles_principales_label',
            'cible_secondaire', 'cible_secondaire_label',
            'taxon_taxref', 'habitat_ref', 'habitats',
            'date_lancement_suivi',
            # Protocoles (#252 — `protocole` = premier de la liste, déprécié)
            'protocoles', 'protocole',
            # Bancarisation
            'outil_bancarisation', 'bancarisation_label',
            'outil_saisie', 'outil_saisie_label',
            'transmission_donnee',
            # Audit
            'date_ajout', 'date_maj',
        ]
        read_only_fields = ['id_suivi_inventaire', 'date_ajout', 'date_maj']

    def get_protocole(self, obj):
        """Premier protocole, pour les clients antérieurs à #252."""
        premier = obj.protocoles.first()
        return ProtocoleSerializer(premier).data if premier else None

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

    def get_objectif_principal_label(self, obj):
        return self._resolve_nomenclature_label(obj.objectif_principal, 'OBJECTIF_SUIVI')

    def get_objectif_secondaire_label(self, obj):
        return self._resolve_nomenclature_label(obj.objectif_secondaire, 'OBJECTIF_SUIVI')

    def get_cibles_principales_label(self, obj):
        return self._resolve_nomenclature_label(obj.cibles_principales, 'CIBLE_SUIVI')

    def get_cible_secondaire_label(self, obj):
        return self._resolve_nomenclature_label(obj.cible_secondaire, 'CIBLE_SUIVI')


class SuiviInventaireWriteSerializer(serializers.ModelSerializer):
    """Serializer pour un suivi/inventaire (écriture, accepte protocoles nested)."""
    protocoles = ProtocoleSerializer(many=True, required=False)
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
            # Protocoles (nested writable) — `protocole` singulier déprécié (#252)
            'protocoles', 'protocole',
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

    #552 — le facteur d'influence est partagé entre plusieurs enjeux (M2M via
    CorFacteurEnjeu) et ne porte plus de FK `id_enjeu` : on retient le premier
    enjeu lié, cohérent avec la sémantique « premier enjeu trouvé ».
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
                    'id_facteur_influence').first()
                if pression and pression.id_facteur_influence:
                    enjeu = pression.id_facteur_influence.enjeux.first()
                    if enjeu:
                        return enjeu.slug
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
            'ventilation_mode', 'declinaison_par_poste',
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
        """Traverse RA path: Indicateur → RA → OO → Pressions (M2M) → FI → Enjeu.

        #552 — le facteur d'influence est désormais partagé entre plusieurs
        enjeux (M2M via CorFacteurEnjeu) et ne porte plus de FK `id_enjeu`.
        On retient le premier enjeu lié, cohérent avec la sémantique
        « premier enjeu trouvé » de `get_enjeu_slug`.
        """
        try:
            ra = indicateur.id_resultat_attendu
            if ra and ra.id_oo:
                pression = ra.id_oo.pressions.select_related('id_facteur_influence').first()
                if pression and pression.id_facteur_influence:
                    enjeu = pression.id_facteur_influence.enjeux.first()
                    if enjeu:
                        return enjeu, ra.id_oo.id_oo
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
        ] + ['operation_annees', 'finances', 'ventilation_mode',
             'declinaison_par_poste']


# =============================================================================
# Serializer de création/modification
# =============================================================================

class OperationAnneeOrganismeWriteSerializer(serializers.Serializer):
    """Write serializer for organisme budget data within an operation year."""
    id_organisme = serializers.IntegerField()
    budget_fonctionnement = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    budget_investissement = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    # #600 — coûts additionnels par organisme/année.
    cout_stage = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    cout_prestataire = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    autre_cout = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    autre_cout_commentaire = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    # #602 — détail investissement (mode « par organisme + type budget + type poste »).
    cout_prestataire_invest = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    autre_cout_invest = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    autre_cout_invest_commentaire = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
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
    rh_lignes = OperationAnneeRHWriteSerializer(many=True, required=False, default=[])


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
            'ventilation_mode', 'declinaison_par_poste',
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
            rh_lignes_data = annee_data.pop('rh_lignes', [])
            annee_obj = OperationAnnee.objects.create(id_operation=operation, **annee_data)
            if organismes_data:
                OperationAnneeOrganisme.objects.bulk_create([
                    OperationAnneeOrganisme(
                        id_operation_annee=annee_obj,
                        id_organisme_id=org['id_organisme'],
                        budget_fonctionnement=org.get('budget_fonctionnement'),
                        budget_investissement=org.get('budget_investissement'),
                        cout_stage=org.get('cout_stage'),
                        cout_prestataire=org.get('cout_prestataire'),
                        autre_cout=org.get('autre_cout'),
                        autre_cout_commentaire=org.get('autre_cout_commentaire', '') or '',
                        cout_prestataire_invest=org.get('cout_prestataire_invest'),
                        autre_cout_invest=org.get('autre_cout_invest'),
                        autre_cout_invest_commentaire=org.get('autre_cout_invest_commentaire', '') or '',
                        etp=org.get('etp'),
                    )
                    for org in organismes_data
                ])
            # #560 — lignes RH prévisionnelles (poste/organisme × jours × financé)
            if rh_lignes_data:
                OperationAnneeRH.objects.bulk_create([
                    OperationAnneeRH(
                        id_operation_annee=annee_obj,
                        id_poste_id=rh.get('id_poste'),
                        id_organisme_id=rh.get('id_organisme'),
                        jours=rh.get('jours'),
                        # bulk_create contourne save() : on réconcilie ici (#597).
                        **dict(zip(
                            ('categorie_depense', 'finance'),
                            CategorieDepense.resolve(rh.get('categorie_depense'), rh.get('finance')),
                        )),
                    )
                    for rh in rh_lignes_data
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
            protocoles_data = pop_protocoles_data(suivi_data)

            suivi = SuiviInventaire.objects.create(
                id_utilisateur_ajout=user,
                **suivi_data
            )
            sync_suivi_protocoles(suivi, protocoles_data, user)
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
            protocoles_data = pop_protocoles_data(suivi_data)

            if instance.id_suivi:
                # Update existing SuiviInventaire
                for attr, value in suivi_data.items():
                    setattr(instance.id_suivi, attr, value)
                instance.id_suivi.id_utilisateur_maj = user
                instance.id_suivi.save()
                sync_suivi_protocoles(instance.id_suivi, protocoles_data, user)
            else:
                # Create new SuiviInventaire
                suivi = SuiviInventaire.objects.create(
                    id_utilisateur_ajout=user,
                    **suivi_data
                )
                sync_suivi_protocoles(suivi, protocoles_data, user)
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
