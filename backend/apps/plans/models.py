"""
Modèles pour la gestion des Plans de Gestion.
"""
import uuid

from django.conf import settings
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from datetime import datetime

# Import des modèles Enjeux et Responsabilités pour exposition
from .models_enjeux import (
    Enjeu,
    FacteurInfluence,
    Pression,
    Responsabilite,
    ObjectifLongTerme,
    NiveauExigence,
    ObjectifOperationnel,
    ResultatAttendu,
    CorOoPression,
    CorFacteurEnjeu,
    CorResponsabiliteTaxon,
    CorResponsabiliteHabitat,
    CorResponsabiliteGeologie,
    CorResponsabiliteEnjeu,
    CorEnjeuTaxon,
    CorEnjeuHabitat,
    CorEnjeuGeologie,
)
from .models_indicateurs import (
    Indicateur,
    CorIndicateurGeologie,
    Metrique,
    Mesure,
    IndicateurMesure,
    IndicateurRealisationGlobale,
)
from .models_operations import (
    Protocole,
    SuiviInventaire,
    Operation,
    CorOperationSite,
    OperationAnnee,
    FinanceOperation,
    OperationRealisationGlobale,
    Fonction,
    Poste,
    PosteFonction,
    OperationAnneeRH,
    RealisationOperationAnneeRH,
)


class PlanGestion(models.Model):
    """
    Modèle principal pour les Plans de Gestion.
    Basé sur t_plan_gestion du schéma general.
    """

    # Statuts possibles. Cf. note interne "Cycle de vie plan de gestion".
    # - `draft`               : brouillon (éditable).
    # - `valide`              : original validé (plan_parent IS NULL).
    # - `modifie`             : modification d'un plan validé (#275). Le drapeau
    #                           `is_mi_parcours` indique si cette modification
    #                           est l'évaluation mi-parcours du plan.
    # - `archive`             : terminé, conservé pour historique.
    #
    # Le workflow CSRPN (#277, anciennement statuts avis_csrpn / comite_consultatif /
    # arrete_pref) est désormais un attribut ORTHOGONAL `validation_step` rattaché
    # au statut `draft` : un plan en cours de validation reste un brouillon avec
    # une étape de validation en cours.
    #
    # Autres attributs orthogonaux au statut (un plan validé peut les cumuler) :
    # - « Étendu » (#250) : `annees_extension > 0`.
    # - « En cours de révision » (#278) : `en_revision = True`. Indique
    #   qu'on rédige le rang suivant ; le plan reste fonctionnellement validé.
    #   Ne dépend PAS du dépassement de la période — la révision peut être
    #   lancée avant ou après `annee_fin`.
    # - « Mi-parcours » (#276) : `is_mi_parcours = True`. Indique que cette
    #   version est l'évaluation mi-parcours du plan. Unique par chaîne.
    #
    # Tous les statuts hors `draft` verrouillent l'édition (#248).
    STATUT_CHOICES = [
        ('draft', _('Brouillon')),
        ('valide', _('Validé')),
        ('modifie', _('Modifié')),
        ('archive', _('Terminé')),
    ]

    # #277 — Étapes du workflow de validation CSRPN. Attribut orthogonal au
    # statut : ne peut être présent que sur un plan `draft`. La séquence
    # avis_csrpn → comite_consultatif → [arrete_pref si RNN] → valide(modifie/mi_parcours)
    # se déroule via l'action API `csrpn-step`. Au passage en `valide`/`modifie`/
    # `mi_parcours`, le champ est remis à NULL.
    VALIDATION_STEP_CHOICES = [
        ('avis_csrpn', _('Avis CSRPN demandé')),
        ('comite_consultatif', _('Validation comité consultatif')),
        ('arrete_pref', _('Arrêté préfectoral')),
    ]
    VALIDATION_STEPS = frozenset({'avis_csrpn', 'comite_consultatif', 'arrete_pref'})
    
    id_pg = models.AutoField(primary_key=True)

    # #645 — Identifiant stable du plan, destiné aux applications tierces
    # (DOCenCEN côté CEN). `id_pg` est une séquence tirée localement : deux
    # instances CICADA produisent couramment le même numéro, et le `slug` suit
    # le nom, donc change quand le plan est renommé. Ni l'un ni l'autre ne peut
    # servir de clé de rapprochement durable dans une application externe.
    uuid_plan = models.UUIDField(
        _("Identifiant unique"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text=_("Identifiant stable du plan, exposé aux applications tierces.")
    )

    id_cdr = models.IntegerField(_("Identifiant CDR"), null=True, blank=True)
    nom = models.CharField(_("Nom du plan de gestion"), max_length=255, unique=True)
    slug = models.SlugField(
        _("Slug"),
        max_length=300,
        unique=True,
        help_text=_("Identifiant URL lisible, généré automatiquement depuis le nom")
    )

    # Gestion multi-sites
    gestion_partagee = models.BooleanField(
        _("Gestion partagée"),
        default=False,
        help_text=_("Ce plan concerne-t-il plusieurs sites ?")
    )

    # Période de validité
    annee_debut = models.IntegerField(
        _("Année de début"),
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        null=True, blank=True
    )
    annee_fin = models.IntegerField(
        _("Année de fin"),
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        null=True, blank=True
    )

    # Rang du plan de gestion
    rang = models.IntegerField(
        _("Rang du plan"),
        default=1,
        validators=[MinValueValidator(1)],
        help_text=_("Numéro du plan (1er, 2ème, 3ème...)")
    )

    # Surface totale concernée
    surface = models.DecimalField(
        _("Surface totale concernée"),
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text=_("Surface en hectares")
    )

    # Contraintes réglementaires
    ct88 = models.BooleanField(
        _("Méthode de rédaction CT88"),
        default=False,
        help_text=_("Plan rédigé selon la méthode CT88")
    )
    risque_incendie = models.BooleanField(
        _("Risque incendie pris en compte"),
        default=False,
        help_text=_("Le risque incendie est-il pris en compte dans le plan ?")
    )

    # Workflow de validation CSRPN (#277). Champs renseignés au fil des étapes.
    # Anciennement `date_validation_cspn` (renommé pour cohérence terminologique).
    date_avis_csrpn = models.DateField(
        _("Date d'avis CSRPN"),
        null=True, blank=True,
        help_text=_("Date à laquelle l'avis du CSRPN a été rendu.")
    )
    date_validation_comite = models.DateField(
        _("Date de validation comité consultatif"),
        null=True, blank=True,
        help_text=_("Date de validation par le comité consultatif de gestion.")
    )
    date_arrete_pref = models.DateField(
        _("Date d'arrêté préfectoral"),
        null=True, blank=True,
        help_text=_("Date de l'arrêté préfectoral (RNN uniquement).")
    )
    numero_arrete_pref = models.CharField(
        _("Numéro d'arrêté préfectoral"),
        max_length=100,
        null=True, blank=True,
        help_text=_("Numéro de référence de l'arrêté préfectoral.")
    )

    # Identifiant Doc'Gestion FCEN
    id_docgestion_fcen = models.CharField(
        _("ID Doc'Gestion FCEN"),
        max_length=100,
        null=True, blank=True
    )

    # Rédacteurs et relecteurs
    redacteurs = models.TextField(
        _("Rédacteurs"),
        null=True, blank=True
    )

    relecteurs = models.TextField(
        _("Relecteurs"),
        null=True, blank=True
    )

    autres_contributeurs = models.TextField(
        _("Autres contributeurs"),
        null=True, blank=True,
        help_text=_("Autres contributeurs au plan de gestion")
    )

    # Relations vers nomenclatures
    id_evaluation = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='plans_evaluation',
        verbose_name=_("Type d'évaluation"),
        help_text=_("Type d'évaluation du plan (ex: évaluation intermédiaire, finale...)")
    )

    id_redacteur_type = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='plans_redacteur_type',
        verbose_name=_("Type de rédacteur"),
        help_text=_("Type de rédacteur (ex: bureau d'étude, gestionnaire, autre...)")
    )

    redacteur_nom = models.CharField(
        _("Nom du rédacteur"),
        max_length=255,
        null=True, blank=True,
        help_text=_("Nom de la personne ou structure ayant rédigé le plan")
    )

    # Contenu
    commentaire = models.TextField(_("Commentaire"), null=True, blank=True)

    # Statut et versioning
    statut = models.CharField(
        _("Statut"),
        max_length=20,
        choices=STATUT_CHOICES,
        default='draft'
    )

    # #277 — Étape du workflow CSRPN (orthogonale au statut). NULL = pas dans
    # le workflow. Renseignée uniquement sur les plans `draft` au moment où
    # le workflow CSRPN est lancé.
    validation_step = models.CharField(
        _("Étape de validation CSRPN"),
        max_length=30,
        choices=VALIDATION_STEP_CHOICES,
        null=True, blank=True,
        help_text=_("Étape du workflow CSRPN en cours (avis CSRPN, comité consultatif, arrêté préfectoral).")
    )

    version = models.CharField(
        _("Version"),
        max_length=20,
        default='1',
        help_text=_("Version du plan dans la chaîne (entier : 1, 2, 3...)")
    )

    plan_parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='children',
        verbose_name=_("Plan parent"),
        help_text=_("Plan dont celui-ci est dérivé")
    )

    # Extension de durée (#250) — 0 (pas d'extension), 1 ou 2 années ajoutées
    # au plan en fin de vie pour la transition avec le rang suivant. Attribut
    # indépendant du statut : un plan validé peut être étendu.
    annees_extension = models.PositiveSmallIntegerField(
        _("Années d'extension"),
        default=0,
        validators=[MaxValueValidator(2)],
        help_text=_("Nombre d'années ajoutées au plan. 0, 1 ou 2.")
    )

    # En cours de révision (#278) — attribut orthogonal au statut. Indique
    # qu'un plan validé est en cours d'élaboration du rang suivant. La
    # révision peut être lancée avant ou après le dépassement de `annee_fin`.
    # Le plan reste fonctionnellement validé (verrou édition #248 inchangé).
    en_revision = models.BooleanField(
        _("En cours de révision"),
        default=False,
        help_text=_("Indique qu'une nouvelle version (rang suivant) est en cours de rédaction.")
    )

    # Évaluation à mi-parcours (#276) — attribut orthogonal au statut.
    # Indique que cette version est l'évaluation mi-parcours du plan.
    # Unique par chaîne plan_parent.
    is_mi_parcours = models.BooleanField(
        _("Évaluation mi-parcours"),
        default=False,
        help_text=_("Indique que cette version est l'évaluation à mi-parcours du plan. Unique par chaîne.")
    )

    # Lien explicite vers le brouillon du rang suivant (#278). Permet d'afficher
    # « Voir le brouillon du rang suivant » depuis le plan en révision.
    next_rang_plan = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='previous_rang_plans',
        verbose_name=_("Plan du rang suivant"),
        help_text=_("Plan correspondant au rang suivant (en cours d'élaboration).")
    )

    id_type_document = models.ForeignKey(
        'core.Nomenclature', on_delete=models.PROTECT,
        null=True, blank=True, related_name='plans_type_document',
        verbose_name=_("Type de document"),
        help_text=_("Plan initial, évaluation mi-parcours, plan révisé...")
    )

    # Géométrie (optionnelle, peut être calculée depuis les sites)
    geometrie = models.MultiPolygonField(
        _("Géométrie du plan"),
        srid=4326,
        null=True, blank=True,
        help_text=_("Emprise géographique du plan (calculée automatiquement si vide)")
    )

    # Métadonnées de traçabilité
    date_ajout = models.DateTimeField(
        _("Date de création"),
        auto_now_add=True
    )
    date_maj = models.DateTimeField(
        _("Date de modification"),
        auto_now=True
    )
    last_update = models.DateTimeField(
        _("Dernière mise à jour"),
        auto_now=True
    )

    # Utilisateurs responsables
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='plans_crees',
        verbose_name=_("Créateur"),
        help_text=_("Utilisateur ayant créé le plan")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='plans_modifies',
        verbose_name=_("Dernier modificateur"),
        help_text=_("Utilisateur ayant effectué la dernière modification")
    )

    # Référents du plan (Many-to-Many)
    referents = models.ManyToManyField(
        'users.Role',
        blank=True,
        related_name='plans_referents',
        verbose_name=_("Référents du plan"),
        help_text=_("Utilisateurs référents pour ce plan")
    )

    class Meta:
        db_table = '"general"."t_plan_gestion"'
        db_table_comment = 'Plans de gestion des espaces naturels'
        verbose_name = _("Plan de gestion")
        verbose_name_plural = _("Plans de gestion")
        ordering = ['-date_maj', 'nom']

    def __str__(self):
        return self.nom

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self

    @property
    def reference(self):
        """
        Référence du plan pour une application tierce (#645).

        Forme « cicada:<instance>:<uuid> ». Le préfixe `cicada` dit de quel
        outil vient l'identifiant — DOCenCEN agrège plusieurs sources et doit
        pouvoir le reconnaître sans table de correspondance. L'identité de
        l'instance suit, parce qu'un déploiement CEN et un déploiement RNF sont
        deux bases distinctes qui peuvent alimenter la même GED.
        """
        return f"cicada:{settings.CICADA_INSTANCE_ID}:{self.uuid_plan}"

    def save(self, *args, **kwargs):
        """Override save pour mettre à jour automatiquement certains champs."""
        # Mettre à jour l'utilisateur modificateur
        if hasattr(self, '_current_user') and self._current_user:
            if not self.pk:  # Création
                self.id_utilisateur_ajout = self._current_user
            self.id_utilisateur_maj = self._current_user

        # Auto-générer le slug depuis le nom
        if not self.slug:
            self.slug = self._generate_unique_slug()

        super().save(*args, **kwargs)

        # Mettre à jour la géométrie si nécessaire
        if not self.geometrie:
            self.update_geometrie()

    def _generate_unique_slug(self):
        """Génère un slug unique à partir du nom."""
        base_slug = slugify(self.nom)
        if not base_slug:
            base_slug = 'plan'
        slug = base_slug
        counter = 2
        qs = PlanGestion.objects.all()
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def update_geometrie(self):
        """Calcule et met à jour la géométrie du plan basée sur ses sites."""
        from django.contrib.gis.geos import MultiPolygon
        from django.db.models import Q
        
        # Récupérer toutes les géométries des sites liés
        sites_geom = []
        for cor_site_pg in self.sites.select_related('site'):
            if cor_site_pg.site.geom:
                if isinstance(cor_site_pg.site.geom, MultiPolygon):
                    sites_geom.extend(list(cor_site_pg.site.geom))
                else:
                    sites_geom.append(cor_site_pg.site.geom)
        
        if sites_geom:
            # Créer une MultiPolygon avec toutes les géométries
            self.geometrie = MultiPolygon(sites_geom)
            # Ne pas déclencher save() pour éviter la récursion
            PlanGestion.objects.filter(pk=self.pk).update(geometrie=self.geometrie)

    def get_sites(self):
        """Retourne la liste des sites associés au plan."""
        return [cor.site for cor in self.sites.select_related('site')]

    def get_organismes_gestionnaires(self):
        """Retourne la liste des organismes gestionnaires des sites du plan."""
        organismes = set()
        for site in self.get_sites():
            for cor_og_site in site.corogsite_set.select_related('uuid_og'):
                organismes.add(cor_og_site.uuid_og)
        return list(organismes)

    def is_multi_sites(self):
        """Vérifie si le plan concerne plusieurs sites."""
        return self.sites.count() > 1

    def get_periode_gestion(self):
        """Retourne la période de gestion sous forme de chaîne."""
        if self.annee_debut and self.annee_fin:
            return f"{self.annee_debut}-{self.annee_fin}"
        elif self.annee_debut:
            return f"À partir de {self.annee_debut}"
        elif self.annee_fin:
            return f"Jusqu'en {self.annee_fin}"
        return "Période non définie"

    def get_root_plan(self):
        """Remonte la chaîne de versions jusqu'au plan racine."""
        plan = self
        visited = {self.pk}
        while plan.plan_parent_id:
            if plan.plan_parent_id in visited:
                break
            visited.add(plan.plan_parent_id)
            plan = plan.plan_parent
        return plan

    def get_version_chain(self):
        """
        Retourne la chaîne complète de versions ordonnée chronologiquement.
        Remonte au root puis collecte tous les descendants.
        """
        root = self.get_root_plan()

        chain = []
        queue = [root]
        visited = set()
        while queue:
            current = queue.pop(0)
            if current.pk in visited:
                continue
            visited.add(current.pk)
            chain.append({
                'id_pg': current.id_pg,
                'nom': current.nom,
                'slug': current.slug,
                'version': current.version,
                'statut': current.statut,
                'rang': current.rang,
                'annee_debut': current.annee_debut,
                'annee_fin': current.annee_fin,
                'annees_extension': current.annees_extension or 0,
                'en_revision': bool(current.en_revision),
                'is_mi_parcours': bool(current.is_mi_parcours),
                'next_rang_plan_id': current.next_rang_plan_id,
                'type_document': current.id_type_document.label if current.id_type_document else None,
                'type_document_mnemonique': current.id_type_document.mnemonique if current.id_type_document else None,
                'is_current': current.pk == self.pk,
            })
            for child in current.children.all().order_by('date_ajout'):
                queue.append(child)

        # Tri final : rang ascendant, puis version (entier si possible),
        # puis date_ajout en fallback. Cohérent avec la sémantique #ND
        # « rang = autre plan, version = itération du même rang ».
        def _sort_key(item):
            try:
                ver_int = int(item.get('version') or 0)
            except (TypeError, ValueError):
                ver_int = 0
            return (item.get('rang') or 0, ver_int)
        chain.sort(key=_sort_key)
        return chain

    # Statuts indiquant qu'un plan a déjà été (ou est) à l'état validé. Sert
    # à savoir si un draft enfant doit être validé en `modifie` plutôt qu'en
    # `valide` (#275).
    VALIDATED_STATUSES = frozenset({
        'valide', 'modifie', 'archive',
    })

    # Statuts qui autorisent l'extension de durée (#250), le lancement de la
    # révision (#278) et le lancement de la mi-parcours (#276). Le plan doit
    # être à un état post-validation actif (mais pas archivé).
    EXTENDABLE_STATUSES = frozenset({
        'valide', 'modifie',
    })

    # Statuts d'un plan qui peuvent accueillir un nouveau brouillon enfant
    # (règle métier #ND : un brouillon ne peut être construit que sur un plan
    # qui a été validé à un moment donné — actif ou archivé). Utilisé par
    # `duplicate`, `create-evaluation`, `create-next-rang`.
    DRAFTABLE_PARENT_STATUSES = frozenset({
        'valide', 'modifie', 'archive',
    })

    def is_extended(self):
        """#250 — Vrai si le plan a été prolongé (1 ou 2 années ajoutées)."""
        return bool(self.annees_extension and self.annees_extension > 0)

    def is_in_revision(self):
        """#278 — Vrai si le plan est en cours de révision."""
        return bool(self.en_revision)

    def is_mid_term(self):
        """#276 — Vrai si cette version est l'évaluation mi-parcours du plan."""
        return bool(self.is_mi_parcours)

    def is_in_csrpn_workflow(self):
        """#277 — Vrai si le plan est dans le workflow CSRPN (validation_step non NULL)."""
        return bool(self.validation_step)

    def has_draft_child(self):
        """Vrai si ce plan a déjà au moins un enfant direct en brouillon.

        Règle métier : un parent ne peut avoir qu'un seul brouillon enfant en
        même temps. Utilisé par `duplicate`, `create-evaluation`,
        `create-next-rang` pour refuser la création d'un nouveau brouillon si
        un autre est déjà en cours.
        """
        return self.children.filter(statut='draft').exists()

    def can_have_new_draft_child(self):
        """Vrai si on peut créer un nouveau brouillon enfant de ce plan.

        Combine : statut dans DRAFTABLE_PARENT_STATUSES ET pas de brouillon
        enfant déjà présent.
        """
        return (
            self.statut in self.DRAFTABLE_PARENT_STATUSES
            and not self.has_draft_child()
        )

    def is_modification(self):
        """#275 — Vrai si ce plan est une modification d'un plan déjà validé
        au sein du **même rang**.

        Un changement de rang correspond à un nouveau plan de gestion (et non
        à une modification du précédent) : la première version d'un nouveau
        rang doit donc être routée vers `valide`, pas `modifie`, même si elle
        succède à un plan archivé/validé du rang précédent.
        """
        if not self.plan_parent_id:
            return False
        if self.plan_parent.rang != self.rang:
            return False
        return self.plan_parent.statut in self.VALIDATED_STATUSES

    def chain_has_mi_parcours(self, exclude_self=True):
        """#276 — Vrai si un autre plan de la chaîne porte le drapeau is_mi_parcours."""
        for item in self.get_version_chain():
            if exclude_self and item['id_pg'] == self.id_pg:
                continue
            if item.get('is_mi_parcours'):
                return True
        return False

    def get_principal_site(self):
        """#277 / #281 — Site principal du plan (premier par rang).

        Renvoie le `Site` (ou None si le plan n'a pas de site). Permet de
        détecter si le plan concerne une RNN pour bypasser l'arrêté
        préfectoral, et de contextualiser les libellés (#281).
        """
        first = (
            self.sites.select_related('site__id_type_site')
            .order_by('rang')
            .first()
        )
        return first.site if first else None

    def is_rnn(self):
        """#277 — Vrai si le site principal est une Réserve Naturelle
        Nationale. Conditionne le passage par l'étape `arrete_pref`.
        """
        site = self.get_principal_site()
        if not site or not site.id_type_site:
            return False
        return site.id_type_site.mnemonique == 'RNN'

    def is_reserve_naturelle(self):
        """#406 — Vrai si le site principal est une réserve naturelle
        (RNN, RNR ou RNC). Conditionne l'accès au workflow de validation
        administrative (avis CSRPN, comité consultatif, arrêté préfectoral).
        """
        site = self.get_principal_site()
        if not site or not site.id_type_site:
            return False
        return site.id_type_site.mnemonique in ('RNN', 'RNR', 'RNC')

    def get_next_version(self):
        """
        Calcule la prochaine version pour une modification du MÊME rang (#279).

        Les versions sont scopées au rang : un changement de rang correspond
        à un NOUVEAU plan de gestion, dont la numérotation repart de v1.
        Cf. note interne *Cycle de vie d'un plan de gestion* — un rang est
        un plan distinct, pas une version.

        Renvoie max(versions du même rang dans la chaîne) + 1, ou '1' si
        aucune version du rang n'existe encore.
        """
        target_rang = self.rang or 1
        chain = self.get_version_chain()
        max_int = 0
        for item in chain:
            if item.get('rang') != target_rang:
                continue
            try:
                v = int(item['version'])
                if v > max_int:
                    max_int = v
            except (TypeError, ValueError):
                continue
        return str(max_int + 1) if max_int > 0 else '1'

    def get_first_version_for_next_rang(self):
        """Première version pour le rang suivant — toujours '1' (nouveau plan)."""
        return '1'

    @staticmethod
    def renumber_versions_per_rang(plans):
        """
        Renumérote les versions d'un ensemble de plans, par rang, de façon
        contiguë (1..N) selon l'ordre chronologique (date_ajout puis id_pg).

        Utilisé après la suppression d'une version (#348) pour conserver une
        numérotation cohérente : les versions sont scopées au rang (cf. #279),
        donc on regroupe par rang avant de réindexer. Ne sauvegarde que les
        plans dont la version change réellement.
        """
        from collections import defaultdict

        by_rang = defaultdict(list)
        for plan in plans:
            by_rang[plan.rang or 1].append(plan)

        for group in by_rang.values():
            group.sort(key=lambda p: (p.date_ajout, p.id_pg))
            for index, plan in enumerate(group, start=1):
                new_version = str(index)
                if plan.version != new_version:
                    plan.version = new_version
                    plan.save(update_fields=['version'])


class CorSitePg(models.Model):
    """
    Table de liaison entre Sites et Plans de Gestion.
    Un plan peut concerner plusieurs sites, et un site peut avoir plusieurs plans.
    """

    site = models.ForeignKey(
        'users.Site',
        on_delete=models.CASCADE,
        verbose_name=_("Site")
    )
    plan_de_gestion = models.ForeignKey(
        PlanGestion,
        on_delete=models.CASCADE,
        related_name='sites',
        verbose_name=_("Plan de gestion")
    )
    rang = models.IntegerField(
        _("Rang"),
        null=True, blank=True,
        help_text=_("Ordre d'importance du site dans le plan (1=principal)")
    )

    # Métadonnées
    date_association = models.DateTimeField(
        _("Date d'association"),
        auto_now_add=True
    )
    commentaire = models.TextField(
        _("Commentaire"),
        null=True, blank=True,
        help_text=_("Précisions sur le lien entre ce site et le plan")
    )

    class Meta:
        db_table = '"general"."cor_ep_pg"'
        db_table_comment = 'Liaison entre espaces protégés et plans de gestion'
        verbose_name = _("Espace protégé - Plan de gestion")
        verbose_name_plural = _("Espaces protégés - Plans de gestion")
        unique_together = ['site', 'plan_de_gestion']
        ordering = ['rang', 'site__nom_site']

    def __str__(self):
        rang_str = f" (rang {self.rang})" if self.rang else ""
        return f"{self.site.nom_site} - {self.plan_de_gestion.nom}{rang_str}"


class CorRolePlan(models.Model):
    """
    Table de liaison entre Utilisateurs et Plans de Gestion.
    Permet de définir les membres et référents d'un plan.
    Similaire à CorRoleSite pour les sites.
    """

    id_role = models.ForeignKey(
        'users.Role',
        on_delete=models.CASCADE,
        verbose_name=_("Utilisateur"),
        related_name='plan_associations'
    )
    plan_de_gestion = models.ForeignKey(
        PlanGestion,
        on_delete=models.CASCADE,
        verbose_name=_("Plan de gestion"),
        related_name='membres'
    )
    referent = models.BooleanField(
        _("Référent"),
        default=False,
        help_text=_("L'utilisateur est-il référent de ce plan ?")
    )

    # Métadonnées
    date_association = models.DateTimeField(
        _("Date d'association"),
        auto_now_add=True
    )
    commentaire = models.TextField(
        _("Commentaire"),
        null=True, blank=True,
        help_text=_("Précisions sur le rôle de l'utilisateur dans le plan")
    )

    class Meta:
        db_table = '"general"."cor_role_plan"'
        db_table_comment = 'Liaison entre utilisateurs et plans de gestion'
        verbose_name = _("Utilisateur - Plan de gestion")
        verbose_name_plural = _("Utilisateurs - Plans de gestion")
        unique_together = ['id_role', 'plan_de_gestion']
        ordering = ['-referent', 'id_role__nom_role']

    def __str__(self):
        role_type = "Référent" if self.referent else "Membre"
        return f"{self.id_role.email} - {self.plan_de_gestion.nom} ({role_type})"


class CorRedacteurPlan(models.Model):
    """
    Table de liaison entre Plans de Gestion et Organismes Rédacteurs.
    Un organisme rédacteur peut éditer le plan mais n'apparaît pas
    dans la ventilation budgétaire (réservée aux organismes gestionnaires).
    """

    plan_de_gestion = models.ForeignKey(
        PlanGestion,
        on_delete=models.CASCADE,
        verbose_name=_("Plan de gestion"),
        related_name='organismes_redacteurs'
    )
    uuid_og = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.CASCADE,
        to_field='uuid_organisme',
        db_column='uuid_og',
        verbose_name=_("Organisme rédacteur")
    )
    date_association = models.DateTimeField(
        _("Date d'association"),
        auto_now_add=True
    )

    class Meta:
        db_table = '"general"."cor_redacteur_plan"'
        db_table_comment = 'Organismes rédacteurs des plans de gestion'
        verbose_name = _("Organisme rédacteur - Plan")
        verbose_name_plural = _("Organismes rédacteurs - Plans")
        unique_together = ['plan_de_gestion', 'uuid_og']

    def __str__(self):
        return f"{self.uuid_og.nom_organisme} - {self.plan_de_gestion.nom}"


class CorPgFichier(models.Model):
    """
    Table de liaison entre Plans de Gestion et fichiers joints.
    Gestion des pièces jointes et documents associés aux plans.
    """

    TYPE_FICHIER_CHOICES = [
        ('document', _('Document principal')),
        ('annexe', _('Annexe')),
        ('carte', _('Carte')),
        ('photo', _('Photographie')),
        ('rapport', _("Rapport d'étude")),
        ('autre', _('Autre')),
    ]

    plan_de_gestion = models.ForeignKey(
        PlanGestion,
        on_delete=models.CASCADE,
        related_name='fichiers',
        verbose_name=_("Plan de gestion")
    )

    # Informations sur le fichier
    nom_fichier = models.CharField(
        _("Nom du fichier"),
        max_length=255,
        help_text=_("Nom original du fichier uploadé")
    )
    chemin_fichier = models.CharField(
        _("Chemin du fichier"),
        max_length=500,
        help_text=_("Chemin d'accès au fichier sur le serveur")
    )
    type_fichier = models.CharField(
        _("Type de fichier"),
        max_length=20,
        choices=TYPE_FICHIER_CHOICES,
        default='document'
    )
    taille_fichier = models.BigIntegerField(
        _("Taille du fichier (bytes)"),
        null=True, blank=True
    )
    extension = models.CharField(
        _("Extension"),
        max_length=10,
        null=True, blank=True
    )

    # Métadonnées descriptives
    titre = models.CharField(
        _("Titre"),
        max_length=255,
        null=True, blank=True,
        help_text=_("Titre descriptif du document")
    )
    description = models.TextField(
        _("Description"),
        null=True, blank=True
    )
    auteur = models.CharField(
        _("Auteur"),
        max_length=255,
        null=True, blank=True
    )
    date_document = models.DateField(
        _("Date du document"),
        null=True, blank=True,
        help_text=_("Date de création/rédaction du document")
    )

    # Métadonnées techniques
    date_upload = models.DateTimeField(
        _("Date d'upload"),
        auto_now_add=True
    )
    id_utilisateur_upload = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        verbose_name=_("Utilisateur ayant uploadé"),
        help_text=_("Utilisateur ayant ajouté ce fichier")
    )

    # Options d'affichage
    public = models.BooleanField(
        _("Fichier public"),
        default=False,
        help_text=_("Le fichier est-il accessible publiquement ?")
    )
    ordre_affichage = models.IntegerField(
        _("Ordre d'affichage"),
        default=0,
        help_text=_("Ordre d'affichage dans la liste des fichiers")
    )

    class Meta:
        db_table = '"fichiers"."t_fichiers"'
        db_table_comment = 'Fichiers associés aux plans de gestion'
        verbose_name = _("Fichier plan de gestion")
        verbose_name_plural = _("Fichiers plans de gestion")
        ordering = ['ordre_affichage', 'nom_fichier']

    def __str__(self):
        return f"{self.titre or self.nom_fichier} ({self.plan_de_gestion.nom})"

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self.plan_de_gestion

    def get_file_size_human(self):
        """Retourne la taille du fichier dans un format lisible."""
        if not self.taille_fichier:
            return "Taille inconnue"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.taille_fichier < 1024.0:
                return f"{self.taille_fichier:.1f} {unit}"
            self.taille_fichier /= 1024.0
        return f"{self.taille_fichier:.1f} TB"

    def is_image(self):
        """Vérifie si le fichier est une image."""
        if self.extension:
            return self.extension.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']
        return False

    def is_document(self):
        """Vérifie si le fichier est un document.""" 
        if self.extension:
            return self.extension.lower() in ['.pdf', '.doc', '.docx', '.odt', '.txt']
        return False
    
    def handle_file_upload(self, uploaded_file):
        """Gère l'upload d'un fichier."""
        import os
        from django.conf import settings
        from django.core.files.storage import default_storage
        
        # Déterminer le nom du fichier s'il n'est pas déjà défini
        if not self.nom_fichier:
            self.nom_fichier = uploaded_file.name
        
        # Déterminer l'extension
        _, ext = os.path.splitext(self.nom_fichier)
        self.extension = ext.lower()
        
        # Déterminer la taille
        self.taille_fichier = uploaded_file.size
        
        # Déterminer le type de fichier automatiquement
        if self.is_image():
            self.type_fichier = 'image'
        elif self.extension in ['.pdf']:
            self.type_fichier = 'document'
        elif self.extension in ['.jpg', '.jpeg', '.png', '.gif'] and 'carte' in self.nom_fichier.lower():
            self.type_fichier = 'carte'
        
        # Définir le chemin de stockage
        upload_dir = f"plans/{self.plan_de_gestion.id_pg}"
        
        # Créer le répertoire s'il n'existe pas
        full_upload_dir = os.path.join(settings.MEDIA_ROOT, upload_dir)
        os.makedirs(full_upload_dir, exist_ok=True)
        
        # Sauvegarder le fichier
        file_path = os.path.join(upload_dir, self.nom_fichier)
        self.chemin_fichier = default_storage.save(file_path, uploaded_file)
        
        # Sauvegarder les métadonnées
        self.save()