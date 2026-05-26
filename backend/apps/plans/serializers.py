"""
Serializers pour l'API REST Plans de Gestion.
"""
from rest_framework import serializers
from django.contrib.gis.serializers.geojson import Serializer as GeoJSONSerializer
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.utils.translation import gettext_lazy as _

from .models import PlanGestion, CorSitePg, CorPgFichier, CorRolePlan, CorRedacteurPlan
from apps.users.serializers import RoleBasicSerializer, SiteBasicSerializer


class CorSitePgSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Site-Plan de Gestion."""

    site = SiteBasicSerializer(read_only=True)
    site_id = serializers.IntegerField(write_only=True, source='site.id_site')

    class Meta:
        model = CorSitePg
        fields = [
            'id', 'site', 'site_id', 'rang', 'commentaire',
            'date_association'
        ]
        read_only_fields = ['id', 'date_association']


class CorPgFichierSerializer(serializers.ModelSerializer):
    """Serializer pour les fichiers de Plans de Gestion."""

    fichier = serializers.FileField(write_only=True, required=False)
    file_size_human = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()
    is_document = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = CorPgFichier
        fields = [
            'id', 'plan_de_gestion', 'nom_fichier', 'chemin_fichier', 'fichier', 'url',
            'type_fichier', 'titre', 'description', 'auteur', 'public',
            'ordre_affichage', 'taille_fichier', 'file_size_human', 'extension',
            'is_image', 'is_document', 'date_upload', 'date_document'
        ]
        read_only_fields = [
            'id', 'chemin_fichier', 'taille_fichier', 'extension',
            'date_upload'
        ]

    def get_file_size_human(self, obj):
        """Retourne la taille du fichier en format lisible."""
        if obj.taille_fichier:
            size = obj.taille_fichier
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        return None

    def get_is_image(self, obj):
        """Vérifie si le fichier est une image."""
        if obj.extension:
            ext = obj.extension.lower().lstrip('.')
            return ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']
        return False

    def get_is_document(self, obj):
        """Vérifie si le fichier est un document."""
        if obj.extension:
            ext = obj.extension.lower().lstrip('.')
            return ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'odt', 'ods']
        return False
    
    def get_url(self, obj):
        """URL de téléchargement du fichier."""
        if obj.chemin_fichier:
            return f"/media/plans/{obj.plan_de_gestion.id_pg}/{obj.nom_fichier}"
        return None
    
    def create(self, validated_data):
        """Créer un fichier avec upload."""
        fichier = validated_data.pop('fichier', None)
        instance = super().create(validated_data)
        
        if fichier:
            instance.handle_file_upload(fichier)
        
        return instance


class PlanSiteListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les sites dans la liste des plans."""
    id_site = serializers.IntegerField(source='site.id_site')
    nom_site = serializers.CharField(source='site.nom_site')
    slug = serializers.SlugField(source='site.slug', read_only=True)
    type_site_label = serializers.SerializerMethodField()
    type_site_mnemonique = serializers.SerializerMethodField()
    current_user_has_access = serializers.SerializerMethodField()
    organismes = serializers.SerializerMethodField()

    class Meta:
        model = CorSitePg
        fields = ['id_site', 'nom_site', 'slug', 'type_site_label', 'type_site_mnemonique',
                  'rang', 'current_user_has_access', 'organismes']

    def get_type_site_label(self, obj):
        """Récupérer le label du type de site depuis la nomenclature."""
        if obj.site and obj.site.id_type_site:
            return obj.site.id_type_site.label
        return None

    def get_type_site_mnemonique(self, obj):
        """Mnémonique du type de site (#281, pour contextualiser le badge d'extension)."""
        if obj.site and obj.site.id_type_site:
            return obj.site.id_type_site.mnemonique
        return None

    def get_current_user_has_access(self, obj):
        """Vérifie si l'utilisateur courant a accès au site.

        Retourne True uniquement pour l'accès direct (CorRoleSite),
        via organisme (CorOgSite), ou global (super_admin /
        rédacteur principal). L'appartenance à un plan de gestion
        qui couvre le site ne donne pas accès au site : dans ce cas
        le front affiche le site verrouillé avec un bouton
        « Se lier au site ».
        """
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return request.user.has_access_to_site(obj.site)

    def get_organismes(self, obj):
        """Retourne les organismes liés au site via CorOgSite."""
        from apps.users.models import CorOgSite
        return [
            {
                'id_organisme': cor.uuid_og.id_organisme,
                'nom_organisme': cor.uuid_og.nom_organisme if cor.uuid_og else '',
                'principal': cor.principal,
                'type_organisme_code': cor.uuid_og.id_type_organisme.cd_nomenclature if cor.uuid_og and cor.uuid_og.id_type_organisme else None,
            }
            for cor in CorOgSite.objects.filter(id_site=obj.site).select_related('uuid_og', 'uuid_og__id_type_organisme')
        ]


class PlanReferentListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les référents dans la liste des plans."""
    nom_complet = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = None  # Will be set to Role
        fields = ['id_role', 'email', 'nom_role', 'prenom_role', 'nom_complet']


# Set the model after import to avoid circular imports
from apps.users.models import Role
PlanReferentListSerializer.Meta.model = Role


class CorRolePlanSerializer(serializers.ModelSerializer):
    """Serializer pour les relations Utilisateur-Plan de Gestion (membres et référents)."""

    id_role = serializers.IntegerField(source='id_role.id_role', read_only=True)
    email = serializers.EmailField(source='id_role.email', read_only=True)
    nom_role = serializers.CharField(source='id_role.nom_role', read_only=True)
    prenom_role = serializers.CharField(source='id_role.prenom_role', read_only=True)
    nom_complet = serializers.CharField(source='id_role.get_full_name', read_only=True)

    class Meta:
        model = CorRolePlan
        fields = [
            'id_role', 'email', 'nom_role', 'prenom_role', 'nom_complet',
            'referent', 'date_association', 'commentaire'
        ]


class PlanSiteMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les sites dans la liste des plans (pas d'organismes ni access check)."""
    id_site = serializers.IntegerField(source='site.id_site')
    nom_site = serializers.CharField(source='site.nom_site')
    type_site_mnemonique = serializers.CharField(
        source='site.id_type_site.mnemonique', read_only=True, allow_null=True
    )

    class Meta:
        model = CorSitePg
        fields = ['id_site', 'nom_site', 'type_site_mnemonique']


class PlanGestionListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des Plans de Gestion.

    Optimisé pour le chargement rapide : pas d'organismes imbriqués,
    pas de vérification d'accès par site, juste les IDs nécessaires
    au filtrage côté frontend.
    """

    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    validation_step_display = serializers.CharField(source='get_validation_step_display', read_only=True, allow_null=True)
    is_in_csrpn_workflow = serializers.SerializerMethodField()
    is_extended = serializers.SerializerMethodField()
    is_in_revision = serializers.SerializerMethodField()
    is_mid_term = serializers.SerializerMethodField()
    has_draft_child = serializers.SerializerMethodField()
    can_create_modification = serializers.SerializerMethodField()

    # Version chain fields
    plan_parent_id = serializers.IntegerField(source='plan_parent.id_pg', read_only=True, allow_null=True)
    type_document_display = serializers.CharField(source='id_type_document.label', read_only=True, allow_null=True)
    children_count = serializers.IntegerField(read_only=True)
    next_rang_plan_id = serializers.IntegerField(source='next_rang_plan.id_pg', read_only=True, allow_null=True)
    next_rang_plan_slug = serializers.SlugField(source='next_rang_plan.slug', read_only=True, allow_null=True)
    enjeux_count = serializers.IntegerField(read_only=True)

    # Nested — minimal
    sites = PlanSiteMinimalSerializer(many=True, read_only=True)
    referents = serializers.SerializerMethodField()
    membres = serializers.SerializerMethodField()

    class Meta:
        model = PlanGestion
        fields = [
            'id_pg', 'nom', 'slug', 'statut', 'statut_display', 'version',
            'validation_step', 'validation_step_display', 'is_in_csrpn_workflow',
            'annee_debut', 'annee_fin', 'annees_extension', 'is_extended',
            'en_revision', 'is_in_revision',
            'is_mi_parcours', 'is_mid_term',
            'has_draft_child', 'can_create_modification',
            'next_rang_plan_id', 'next_rang_plan_slug',
            'plan_parent_id', 'type_document_display', 'children_count', 'enjeux_count',
            'sites', 'referents', 'membres',
        ]

    def get_is_extended(self, obj):
        return obj.is_extended()

    def get_is_in_revision(self, obj):
        return obj.is_in_revision()

    def get_is_mid_term(self, obj):
        return obj.is_mid_term()

    def get_is_in_csrpn_workflow(self, obj):
        return obj.is_in_csrpn_workflow()

    def get_has_draft_child(self, obj):
        return obj.has_draft_child()

    def get_can_create_modification(self, obj):
        return obj.can_have_new_draft_child()

    def get_referents(self, obj):
        return [
            {
                'id_role': r.id_role,
                'email': r.email,
                'nom_role': r.nom_role,
                'prenom_role': r.prenom_role,
                'nom_complet': r.get_full_name(),
            }
            for r in obj.referents.all()
        ]

    def get_membres(self, obj):
        return [
            {
                'id_role': m.id_role.id_role,
                'email': m.id_role.email,
                'nom_role': m.id_role.nom_role,
                'prenom_role': m.id_role.prenom_role,
                'nom_complet': m.id_role.get_full_name(),
                'referent': m.referent,
            }
            for m in obj.membres.all()
        ]


class PlanGestionDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour les Plans de Gestion."""

    # Relations - use simplified serializers for frontend compatibility
    sites = PlanSiteListSerializer(many=True, read_only=True)
    fichiers = CorPgFichierSerializer(many=True, read_only=True)
    referents = PlanReferentListSerializer(many=True, read_only=True)
    membres = CorRolePlanSerializer(many=True, read_only=True)

    # Champs calculés
    periode_gestion = serializers.CharField(source='get_periode_gestion', read_only=True)
    is_multi_sites = serializers.BooleanField(read_only=True)
    organismes_gestionnaires = serializers.SerializerMethodField()
    sites_list = serializers.SerializerMethodField()

    # #250 : éligibilité à l'extension de durée. Vrai si :
    #   - statut ∈ EXTENDABLE_STATUSES (valide / modifie / mi_parcours)
    #   - annees_extension == 0 (pas déjà étendu)
    #   - annee_fin renseignée
    #   - année courante ∈ [annee_fin - 1, annee_fin + 2]
    peut_etre_etendu = serializers.SerializerMethodField()
    annee_fin_effective = serializers.SerializerMethodField()
    is_extended = serializers.SerializerMethodField()
    is_in_revision = serializers.SerializerMethodField()
    is_mid_term = serializers.SerializerMethodField()
    is_in_csrpn_workflow = serializers.SerializerMethodField()
    has_draft_child = serializers.SerializerMethodField()
    can_create_modification = serializers.SerializerMethodField()
    next_rang_plan_id = serializers.IntegerField(source='next_rang_plan.id_pg', read_only=True, allow_null=True)
    next_rang_plan_nom = serializers.CharField(source='next_rang_plan.nom', read_only=True, allow_null=True)
    next_rang_plan_slug = serializers.SlugField(source='next_rang_plan.slug', read_only=True, allow_null=True)

    # Champs display
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    validation_step_display = serializers.CharField(source='get_validation_step_display', read_only=True, allow_null=True)
    evaluation_display = serializers.CharField(source='id_evaluation.label', read_only=True)
    redacteur_type_display = serializers.CharField(source='id_redacteur_type.label', read_only=True)

    # Version chain fields
    plan_parent_id = serializers.IntegerField(source='plan_parent.id_pg', read_only=True, allow_null=True)
    plan_parent_nom = serializers.CharField(source='plan_parent.nom', read_only=True, allow_null=True)
    plan_parent_slug = serializers.SlugField(source='plan_parent.slug', read_only=True, allow_null=True)
    type_document_display = serializers.CharField(source='id_type_document.label', read_only=True, allow_null=True)
    children_count = serializers.IntegerField(source='children.count', read_only=True)
    version_chain = serializers.SerializerMethodField()

    # Utilisateurs
    utilisateur_ajout = RoleBasicSerializer(source='id_utilisateur_ajout', read_only=True)
    utilisateur_maj = RoleBasicSerializer(source='id_utilisateur_maj', read_only=True)

    # IDs pour création/modification
    sites_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    referents_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    organismes_redacteurs_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    organismes_redacteurs_list = serializers.SerializerMethodField(read_only=True)

    def get_peut_etre_etendu(self, obj):
        """Indique si le plan est dans la fenêtre permettant l'extension (#250).

        L'extension est ouverte aux plans validés (valide / modifie /
        mi_parcours) qui ne sont pas déjà étendus. L'attribut `en_revision`
        peut cohabiter mais n'est pas requis.
        """
        from datetime import date
        if obj.statut not in PlanGestion.EXTENDABLE_STATUSES:
            return False
        if obj.annees_extension and obj.annees_extension > 0:
            return False
        if not obj.annee_fin:
            return False
        current_year = date.today().year
        return obj.annee_fin - 1 <= current_year <= obj.annee_fin + 2

    def get_annee_fin_effective(self, obj):
        """Année de fin effective (annee_fin + annees_extension si étendu)."""
        if obj.annee_fin is None:
            return None
        return obj.annee_fin + (obj.annees_extension or 0)

    def get_is_extended(self, obj):
        """#250 — Vrai si le plan a été prolongé (annees_extension > 0)."""
        return obj.is_extended()

    def get_is_in_revision(self, obj):
        """#278 — Vrai si le plan est en cours de révision."""
        return obj.is_in_revision()

    def get_is_mid_term(self, obj):
        """#276 — Vrai si cette version est l'évaluation mi-parcours du plan."""
        return obj.is_mid_term()

    def get_is_in_csrpn_workflow(self, obj):
        """#277 — Vrai si le plan est dans le workflow CSRPN (validation_step renseigné)."""
        return obj.is_in_csrpn_workflow()

    def get_has_draft_child(self, obj):
        """Vrai si le plan a déjà au moins un brouillon enfant.

        Utilisé côté frontend pour griser les actions « créer un nouveau
        brouillon » (duplicate, create-evaluation, create-next-rang).
        """
        return obj.has_draft_child()

    def get_can_create_modification(self, obj):
        """Vrai si on peut créer une nouvelle version (brouillon) de ce plan.

        Combine : statut validé/modifié/archivé ET pas de brouillon enfant.
        """
        return obj.can_have_new_draft_child()

    def get_organismes_gestionnaires(self, obj):
        """Retourne la liste des noms des organismes gestionnaires."""
        organismes = []
        for site in obj.get_sites():
            for cor_og_site in site.corogsite_set.select_related('uuid_og', 'uuid_og__id_type_organisme'):
                if cor_og_site.uuid_og:
                    org = cor_og_site.uuid_og
                    organismes.append({
                        'id_organisme': org.id_organisme,
                        'nom_organisme': org.nom_organisme,
                        'type_organisme_code': org.id_type_organisme.cd_nomenclature if org.id_type_organisme else None
                    })
        # Remove duplicates by id
        seen = set()
        unique = []
        for org in organismes:
            if org['id_organisme'] not in seen:
                seen.add(org['id_organisme'])
                unique.append(org)
        return unique

    def get_sites_list(self, obj):
        """Retourne la liste simplifiée des sites."""
        return [
            {'id_site': site.id_site, 'nom_site': site.nom_site}
            for site in obj.get_sites()
        ]

    def get_version_chain(self, obj):
        """Retourne la chaîne complète de versions."""
        return obj.get_version_chain()

    def get_organismes_redacteurs_list(self, obj):
        """Retourne la liste des organismes rédacteurs du plan."""
        from apps.plans.models import CorRedacteurPlan
        return [
            {
                'id_organisme': cor.uuid_og.id_organisme,
                'nom_organisme': cor.uuid_og.nom_organisme,
            }
            for cor in CorRedacteurPlan.objects.filter(
                plan_de_gestion=obj
            ).select_related('uuid_og')
        ]

    class Meta:
        model = PlanGestion
        fields = [
            'id_pg', 'nom', 'slug', 'id_cdr', 'rang',
            'annee_debut', 'annee_fin', 'periode_gestion',
            'annees_extension', 'peut_etre_etendu', 'annee_fin_effective', 'is_extended',
            'en_revision', 'is_in_revision',
            'is_mi_parcours', 'is_mid_term',
            'validation_step', 'validation_step_display', 'is_in_csrpn_workflow',
            'date_validation_comite', 'date_arrete_pref', 'numero_arrete_pref',
            'has_draft_child', 'can_create_modification',
            'next_rang_plan_id', 'next_rang_plan_nom', 'next_rang_plan_slug',
            'surface', 'gestion_partagee', 'ct88', 'risque_incendie',
            'date_avis_csrpn', 'id_docgestion_fcen',
            'id_evaluation', 'evaluation_display', 'id_redacteur_type', 'redacteur_type_display',
            'redacteur_nom', 'redacteurs', 'relecteurs', 'autres_contributeurs',
            'commentaire', 'statut', 'statut_display', 'version',
            'plan_parent_id', 'plan_parent_nom', 'plan_parent_slug',
            'type_document_display', 'children_count', 'version_chain',
            'geometrie', 'is_multi_sites', 'organismes_gestionnaires', 'sites_list',
            'organismes_redacteurs_list', 'organismes_redacteurs_ids',
            'sites', 'fichiers', 'referents', 'membres', 'sites_ids', 'referents_ids',
            'utilisateur_ajout', 'utilisateur_maj',
            'date_ajout', 'date_maj'
        ]
        read_only_fields = [
            'id_pg', 'slug', 'date_ajout', 'date_maj',
            'peut_etre_etendu', 'annee_fin_effective', 'is_extended',
            'is_in_revision', 'is_mid_term',
            'has_draft_child', 'can_create_modification',
            'next_rang_plan_id', 'next_rang_plan_nom', 'next_rang_plan_slug',
        ]
    
    def validate(self, data):
        """Validation spécifique à la création (sites obligatoires)."""
        if not self.instance and not data.get('sites_ids'):
            raise serializers.ValidationError({'sites_ids': _("Au moins un site est requis.")})
        return data

    def create(self, validated_data):
        """Créer un plan avec ses relations."""
        sites_ids = validated_data.pop('sites_ids', [])
        referents_ids = validated_data.pop('referents_ids', [])
        organismes_redacteurs_ids = validated_data.pop('organismes_redacteurs_ids', [])

        plan = super().create(validated_data)

        # Ajouter les sites
        if sites_ids:
            from apps.users.models import Site
            for i, site_id in enumerate(sites_ids, 1):
                site = Site.objects.get(id_site=site_id)
                CorSitePg.objects.create(
                    plan_de_gestion=plan,
                    site=site,
                    rang=i
                )

        # Ajouter les référents
        if referents_ids:
            from apps.users.models import Role
            referents = Role.objects.filter(id_role__in=referents_ids)
            plan.referents.set(referents)

        # Ajouter les organismes rédacteurs
        if organismes_redacteurs_ids:
            from apps.users.models import BibOrganismes
            for org_id in organismes_redacteurs_ids:
                org = BibOrganismes.objects.get(id_organisme=org_id)
                CorRedacteurPlan.objects.get_or_create(plan_de_gestion=plan, uuid_og=org)

        return plan

    def update(self, instance, validated_data):
        """Mettre à jour un plan avec ses relations."""
        sites_ids = validated_data.pop('sites_ids', None)
        referents_ids = validated_data.pop('referents_ids', None)
        organismes_redacteurs_ids = validated_data.pop('organismes_redacteurs_ids', None)

        plan = super().update(instance, validated_data)

        # Mettre à jour les sites si fournis
        if sites_ids is not None:
            from apps.users.models import Site
            # Supprimer les anciennes associations
            CorSitePg.objects.filter(plan_de_gestion=plan).delete()
            # Créer les nouvelles associations
            for i, site_id in enumerate(sites_ids, 1):
                site = Site.objects.get(id_site=site_id)
                CorSitePg.objects.create(
                    plan_de_gestion=plan,
                    site=site,
                    rang=i
                )

        # Mettre à jour les référents si fournis
        if referents_ids is not None:
            from apps.users.models import Role
            referents = Role.objects.filter(id_role__in=referents_ids)
            plan.referents.set(referents)

        # Mettre à jour les organismes rédacteurs si fournis
        if organismes_redacteurs_ids is not None:
            from apps.users.models import BibOrganismes
            CorRedacteurPlan.objects.filter(plan_de_gestion=plan).delete()
            for org_id in organismes_redacteurs_ids:
                org = BibOrganismes.objects.get(id_organisme=org_id)
                CorRedacteurPlan.objects.create(plan_de_gestion=plan, uuid_og=org)

        return plan


class PlanDuplicateOptionsSerializer(serializers.Serializer):
    """Serializer pour les options de duplication d'un plan."""

    copy_sites = serializers.BooleanField(default=True)
    copy_referents = serializers.BooleanField(default=True)
    copy_fichiers = serializers.BooleanField(default=False)
    copy_enjeux = serializers.BooleanField(default=True)
    copy_sub_elements = serializers.BooleanField(default=True)


class PlanGestionGeoJSONSerializer(serializers.ModelSerializer):
    """Serializer GeoJSON pour les Plans de Gestion."""
    
    periode_gestion = serializers.CharField(source='get_periode_gestion', read_only=True)
    nb_sites = serializers.IntegerField(source='sites.count', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    
    class Meta:
        model = PlanGestion
        geo_field = 'geometrie'
        fields = [
            'id_pg', 'nom', 'slug', 'periode_gestion', 'gestion_partagee',
            'statut', 'statut_display', 'nb_sites'
        ]


class PlanGestionCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création simplifiée de Plans de Gestion."""

    sites_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=True, min_length=1)
    referents_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    organismes_redacteurs_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)

    class Meta:
        model = PlanGestion
        fields = [
            'id_pg', 'nom', 'slug', 'id_cdr', 'rang', 'annee_debut', 'annee_fin',
            'surface', 'gestion_partagee', 'ct88', 'risque_incendie',
            'date_avis_csrpn', 'id_docgestion_fcen',
            'id_evaluation', 'id_redacteur_type', 'redacteur_nom',
            'redacteurs', 'relecteurs', 'autres_contributeurs',
            'commentaire', 'statut', 'version', 'geometrie',
            'sites_ids', 'referents_ids', 'organismes_redacteurs_ids'
        ]
        read_only_fields = ['id_pg', 'slug']
        extra_kwargs = {
            'nom': {'required': True},
            'rang': {'required': True},
            'annee_debut': {'required': True},
            'annee_fin': {'required': True},
        }

    def create(self, validated_data):
        """Créer un plan avec sites, référents et organisme rédacteur."""
        sites_ids = validated_data.pop('sites_ids', [])
        referents_ids = validated_data.pop('referents_ids', [])
        organismes_redacteurs_ids = validated_data.pop('organismes_redacteurs_ids', [])

        # Créer le plan
        plan = super().create(validated_data)

        # Associer les sites
        if sites_ids:
            from apps.users.models import Site
            for i, site_id in enumerate(sites_ids, 1):
                site = Site.objects.get(id_site=site_id)
                CorSitePg.objects.create(
                    plan_de_gestion=plan,
                    site=site,
                    rang=i
                )

        # Associer les référents
        if referents_ids:
            from apps.users.models import Role
            referents = Role.objects.filter(id_role__in=referents_ids)
            plan.referents.set(referents)

        # Associer l'organisme rédacteur
        if organismes_redacteurs_ids:
            from apps.users.models import BibOrganismes
            for org_id in organismes_redacteurs_ids:
                org = BibOrganismes.objects.get(id_organisme=org_id)
                CorRedacteurPlan.objects.get_or_create(plan_de_gestion=plan, uuid_og=org)

        return plan