"""
Modèles pour les Enjeux, FCR (Facteurs Clés de Réussite) et Responsabilités.
"""
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Responsabilite(models.Model):
    """
    Modèle pour les responsabilités d'un site.
    Définit le type et le niveau de responsabilité du site
    (floristique, faunistique, habitat, géologique, paysager).
    """

    id_responsabilite = models.AutoField(primary_key=True)
    id_site = models.ForeignKey(
        'users.Site',
        on_delete=models.CASCADE,
        related_name='responsabilites',
        db_column='id_site',
        verbose_name=_("Site")
    )
    id_type_responsabilite = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        related_name='responsabilites_type',
        db_column='id_type_responsabilite',
        verbose_name=_("Type de responsabilité"),
        help_text=_("Floristique, Faunistique, Habitat, Géologique, Paysager"),
        limit_choices_to={'id_type__mnemonique': 'TYPE_RESPONSABILITE'}
    )
    id_niveau_responsabilite = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        related_name='responsabilites_niveau',
        db_column='id_niveau_responsabilite',
        verbose_name=_("Niveau de responsabilité"),
        help_text=_("Local, Régional, National, International"),
        limit_choices_to={'id_type__mnemonique': 'NIVEAU_RESPONSABILITE'}
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Description de la responsabilité")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_responsabilites"'
        db_table_comment = 'Responsabilités des sites'
        verbose_name = _("Responsabilité")
        verbose_name_plural = _("Responsabilités")
        ordering = ['id_type_responsabilite', 'id_niveau_responsabilite']

    def __str__(self):
        type_label = self.id_type_responsabilite.label if self.id_type_responsabilite else "?"
        niveau_label = self.id_niveau_responsabilite.label if self.id_niveau_responsabilite else "?"
        return f"{type_label} - {niveau_label} ({self.id_site})"


class Enjeu(models.Model):
    """
    Modèle unifié pour Enjeux et FCR (Facteurs Clés de Réussite).
    La distinction se fait via id_categorie (nomenclature CATEGORIE_ENJEU).
    Les champs spécifiques sont nullables selon le type.
    """

    id_enjeu = models.AutoField(primary_key=True)
    id_pg = models.ForeignKey(
        'plans.PlanGestion',
        on_delete=models.CASCADE,
        related_name='enjeux',
        db_column='id_pg',
        verbose_name=_("Plan de gestion")
    )

    # Type: Enjeu ou FCR (nomenclature CATEGORIE_ENJEU)
    id_categorie = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        related_name='enjeux_categorie',
        db_column='id_categorie',
        verbose_name=_("Catégorie"),
        help_text=_("Enjeu de conservation ou Facteur Clé de Réussite"),
        limit_choices_to={'id_type__mnemonique': 'CATEGORIE_ENJEU'}
    )

    # Champs communs
    libelle = models.CharField(
        _("Intitulé"),
        max_length=500,
        help_text=_("Intitulé de l'enjeu ou du FCR")
    )
    intitule_court = models.CharField(
        _("Intitulé court"),
        max_length=25,
        blank=True,
        null=True,
        help_text=_("Max 25 caractères pour affichage")
    )
    slug = models.SlugField(
        _("Slug"),
        max_length=300,
        help_text=_("Identifiant URL lisible, généré automatiquement")
    )
    description = models.TextField(
        _("Détails/Commentaires"),
        blank=True,
        null=True,
        help_text=_("Description détaillée de l'enjeu ou du FCR")
    )

    # ===== Champs spécifiques aux ENJEUX =====
    # Priorité (1, 2, 3) - Seulement pour Enjeux
    rang = models.IntegerField(
        _("Priorité"),
        default=None,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text=_("Priorité de l'enjeu (1=haute, 2=moyenne, 3=basse). "
                    "Null = priorité non définie (#441).")
    )
    # Catégorie de l'enjeu — exclusivité : un enjeu est soit lié à la
    # conservation du patrimoine naturel, soit socio-économique, mais pas
    # les deux (cf. #260 : retour utilisateur, choix binaire imposé).
    categorie_ecologique = models.BooleanField(
        _("Catégorie conservation du patrimoine naturel"),
        default=True,
        null=True,
        help_text=_("True=Conservation du patrimoine naturel, False=Socio-économique")
    )
    # Type d'enjeu écologique (checkboxes) - Seulement pour Enjeux écologiques
    habitat = models.BooleanField(
        _("Habitat"),
        default=False,
        help_text=_("Enjeu lié à un/des habitats")
    )
    espece = models.BooleanField(
        _("Espèce"),
        default=False,
        help_text=_("Enjeu lié à une/des espèces")
    )
    patrimoine_geologique = models.BooleanField(
        _("Patrimoine géologique"),
        default=False,
        help_text=_("Enjeu lié au patrimoine géologique")
    )
    fonctionnalite_ecosysteme = models.BooleanField(
        _("Fonctionnalité des écosystèmes"),
        default=False,
        help_text=_("Enjeu lié à une/des fonctionnalités des écosystèmes")
    )
    autre_ecologique = models.BooleanField(
        _("Autre (conservation du patrimoine naturel)"),
        default=False,
        help_text=_("Enjeu de conservation du patrimoine naturel de type autre")
    )
    autre_ecologique_precision = models.CharField(
        _("Précision autre (conservation du patrimoine naturel)"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Précision sur le type 'Autre' conservation du patrimoine naturel")
    )
    # Sous-champs patrimoine géologique (affichés quand patrimoine_geologique=True)
    geo_ex_situ = models.BooleanField(
        _("Patrimoine géologique ex-situ"),
        default=False,
        help_text=_("Patrimoine géologique de type ex-situ (collections, musées)")
    )
    geo_in_situ = models.BooleanField(
        _("Patrimoine géologique in-situ"),
        default=False,
        help_text=_("Patrimoine géologique de type in-situ (sites géologiques)")
    )
    # #237 — patrimoines géologiques supplémentaires (au même niveau que in/ex-situ)
    geo_documents = models.BooleanField(
        _("Patrimoine géologique - documents"),
        default=False,
        help_text=_("Patrimoine géologique de type documentaire (archives numériques ou papier)")
    )
    geo_autre = models.BooleanField(
        _("Patrimoine géologique - autre"),
        default=False,
        help_text=_("Patrimoine géologique de type autre")
    )
    geo_autre_precision = models.CharField(
        _("Précision patrimoine géologique - autre"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Précision sur le patrimoine géologique de type 'Autre'")
    )
    # Champ legacy conservé pour compatibilité (remplacé par fonctionnalite_ecosysteme)
    processus = models.BooleanField(
        _("Processus"),
        default=False,
        help_text=_("Enjeu lié à un processus écologique (legacy)")
    )

    # Type d'enjeu socio-économique (checkboxes) - Seulement pour Enjeux socio-économiques
    valeur_paysagere = models.BooleanField(
        _("Valeur paysagère"),
        default=False,
        help_text=_("Enjeu lié à la valeur paysagère")
    )
    patrimoine_culturel = models.BooleanField(
        _("Patrimoine culturel"),
        default=False,
        help_text=_("Enjeu lié au maintien du patrimoine culturel")
    )
    developpement_durable = models.BooleanField(
        _("Développement durable des ressources"),
        default=False,
        help_text=_("Enjeu lié au développement durable des ressources")
    )
    usages = models.BooleanField(
        _("Usages"),
        default=False,
        help_text=_("Enjeu lié aux usages")
    )
    valeur_ajoutee = models.BooleanField(
        _("Valeur ajoutée"),
        default=False,
        help_text=_("Enjeu lié à une/des valeurs ajoutées sociale, économique, scientifique ou éducative")
    )
    autre_socioeco = models.BooleanField(
        _("Autre (socio-économique)"),
        default=False,
        help_text=_("Enjeu socio-économique de type autre")
    )
    autre_socioeco_precision = models.CharField(
        _("Précision autre (socio-économique)"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Précision sur le type 'Autre' socio-économique")
    )
    # État de l'enjeu - Seulement pour Enjeux
    etat_enjeu = models.TextField(
        _("État de l'enjeu"),
        blank=True,
        null=True,
        help_text=_("Précisions sur l'état de l'enjeu")
    )

    # ===== Champs spécifiques aux FCR =====
    # Catégorie FCR (Connaissance, Ancrage territorial, Fonctionnement, Autre)
    id_categorie_fcr = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='enjeux_categorie_fcr',
        db_column='id_categorie_fcr',
        verbose_name=_("Catégorie de FCR"),
        help_text=_("Connaissance, Ancrage territorial, Fonctionnement, Autre"),
        limit_choices_to={'id_type__mnemonique': 'CATEGORIE_FCR'}
    )

    # ===== Champs optionnels =====
    id_importance = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='enjeux_importance',
        db_column='id_importance',
        verbose_name=_("Importance"),
        limit_choices_to={'id_type__mnemonique': 'IMPORTANCE_ENJEU'}
    )
    geom = models.MultiPolygonField(
        _("Géométrie"),
        srid=4326,
        null=True,
        blank=True,
        help_text=_("Emprise géographique de l'enjeu")
    )

    # #249 / #261 — Ordre d'affichage parmi les pairs (même parent).
    # Mis à jour côté frontend via drag-and-drop. 0 = en tête.
    ordre = models.PositiveIntegerField(
        _("Ordre"),
        default=0,
        db_index=True,
        help_text=_("Ordre d'affichage parmi les éléments d'un même parent (0 = haut)")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_enjeux"'
        db_table_comment = 'Enjeux et Facteurs Clés de Réussite des plans de gestion'
        verbose_name = _("Enjeu / FCR")
        verbose_name_plural = _("Enjeux / FCR")
        ordering = ['ordre', 'id_enjeu']
        unique_together = [('id_pg', 'slug'), ('id_pg', 'libelle')]

    @property
    def nb_facteurs_influence(self):
        """Retourne le nombre de facteurs d'influence."""
        return self.facteurs_influence.count()

    def __str__(self):
        return f"{self.libelle} ({self.id_pg})"

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self.id_pg

    def save(self, *args, **kwargs):
        """Auto-générer le slug depuis intitule_court ou libelle."""
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        """Génère un slug unique par plan à partir de intitule_court ou libelle."""
        source = self.intitule_court or self.libelle
        base_slug = slugify(source)
        if not base_slug:
            base_slug = 'enjeu'
        slug = base_slug
        counter = 2
        qs = Enjeu.objects.filter(id_pg=self.id_pg)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        while qs.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def is_enjeu(self) -> bool:
        """Retourne True si c'est un Enjeu (pas un FCR)."""
        return self.id_categorie.mnemonique == 'ENJEU' if self.id_categorie else True

    def is_fcr(self) -> bool:
        """Retourne True si c'est un FCR."""
        return self.id_categorie.mnemonique == 'FCR' if self.id_categorie else False

    @property
    def categorie_label(self):
        """Retourne le label de la catégorie (Enjeu ou FCR)."""
        return self.id_categorie.label if self.id_categorie else None


class FacteurInfluence(models.Model):
    """
    Facteur d'influence rattaché à un enjeu.
    Représente un facteur externe qui influence l'état de l'enjeu.
    Peut avoir des pressions comme enfants.
    """

    id_facteur_influence = models.AutoField(primary_key=True)
    id_enjeu = models.ForeignKey(
        Enjeu,
        on_delete=models.CASCADE,
        related_name='facteurs_influence',
        db_column='id_enjeu',
        verbose_name=_("Enjeu")
    )
    libelle = models.CharField(
        _("Intitulé"),
        max_length=500,
        help_text=_("Intitulé du facteur d'influence")
    )
    description = models.TextField(
        _("Détails/Commentaires"),
        blank=True,
        null=True,
        help_text=_("Description détaillée du facteur d'influence")
    )

    # #249 / #261 — Ordre d'affichage parmi les pairs (même parent).
    # Mis à jour côté frontend via drag-and-drop. 0 = en tête.
    ordre = models.PositiveIntegerField(
        _("Ordre"),
        default=0,
        db_index=True,
        help_text=_("Ordre d'affichage parmi les éléments d'un même parent (0 = haut)")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_facteurs_influence"'
        db_table_comment = "Facteurs d'influence des enjeux"
        verbose_name = _("Facteur d'influence")
        verbose_name_plural = _("Facteurs d'influence")
        ordering = ['ordre', 'id_facteur_influence']

    def __str__(self):
        return f"{self.libelle} ({self.id_enjeu})"

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self.id_enjeu.id_pg


class Pression(models.Model):
    """
    Pression rattachée à un facteur d'influence.
    Représente une pression concrète exercée sur l'enjeu via un facteur d'influence.
    """

    id_pression = models.AutoField(primary_key=True)
    id_facteur_influence = models.ForeignKey(
        FacteurInfluence,
        on_delete=models.CASCADE,
        related_name='pressions',
        db_column='id_facteur_influence',
        verbose_name=_("Facteur d'influence")
    )
    id_pressref = models.CharField(
        _("Référence pression"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Référence vers un référentiel de pressions (futur)")
    )
    id_type_pression = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pressions_type',
        db_column='id_type_pression',
        verbose_name=_("Type de pression (PressRef)"),
        help_text=_("Référence PressRef CARET V1"),
        limit_choices_to={'id_type__mnemonique': 'TYPE_PRESSION'}
    )
    libelle = models.CharField(
        _("Intitulé"),
        max_length=500,
        help_text=_("Intitulé de la pression")
    )
    description = models.TextField(
        _("Détails/Commentaires"),
        blank=True,
        null=True,
        help_text=_("Description détaillée de la pression")
    )

    # #249 / #261 — Ordre d'affichage parmi les pairs (même parent).
    # Mis à jour côté frontend via drag-and-drop. 0 = en tête.
    ordre = models.PositiveIntegerField(
        _("Ordre"),
        default=0,
        db_index=True,
        help_text=_("Ordre d'affichage parmi les éléments d'un même parent (0 = haut)")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_pressions"'
        db_table_comment = 'Pressions sur les facteurs d\'influence'
        verbose_name = _("Pression")
        verbose_name_plural = _("Pressions")
        ordering = ['ordre', 'id_pression']

    def __str__(self):
        return f"{self.libelle} ({self.id_facteur_influence})"

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self.id_facteur_influence.id_enjeu.id_pg


# ============================================
# TABLES DE CORRELATION POUR LES RESPONSABILITÉS
# ============================================

class ObjectifLongTerme(models.Model):
    """
    Objectif à long terme (OLT) rattaché directement à un enjeu.
    Traduit l'état souhaité à atteindre à l'issue du plan de gestion.
    Hiérarchie : Enjeu → OLT → NiveauExigence.
    """

    id_olt = models.AutoField(primary_key=True)
    id_enjeu = models.ForeignKey(
        Enjeu,
        on_delete=models.CASCADE,
        related_name='objectifs_long_terme',
        db_column='id_enjeu',
        verbose_name=_("Enjeu")
    )
    libelle = models.CharField(
        _("Intitulé"),
        max_length=500,
        help_text=_("Intitulé de l'objectif à long terme")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Description détaillée de l'objectif à long terme")
    )

    # #249 / #261 — Ordre d'affichage parmi les pairs (même parent).
    # Mis à jour côté frontend via drag-and-drop. 0 = en tête.
    ordre = models.PositiveIntegerField(
        _("Ordre"),
        default=0,
        db_index=True,
        help_text=_("Ordre d'affichage parmi les éléments d'un même parent (0 = haut)")
    )

    # #442 — Numéro global fixé manuellement par le gestionnaire.
    # NULL = numérotation automatique (dérivée de l'ordre). Quand renseigné,
    # ce numéro est réservé et l'auto-numérotation des autres OLT le saute.
    numero_manuel = models.PositiveIntegerField(
        _("Numéro fixé manuellement"),
        null=True,
        blank=True,
        help_text=_("Numéro global fixé manuellement (laisser vide pour la numérotation automatique)")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_objectifs_long_terme"'
        db_table_comment = "Objectifs à long terme des enjeux"
        verbose_name = _("Objectif à long terme")
        verbose_name_plural = _("Objectifs à long terme")
        ordering = ['ordre', 'id_olt']

    def __str__(self):
        return f"{self.libelle} ({self.id_enjeu})"

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self.id_enjeu.id_pg


class NiveauExigence(models.Model):
    """
    Niveau d'exigence rattaché à un objectif à long terme.
    Définit le niveau d'exigence attendu pour atteindre l'OLT.
    """

    id_ne = models.AutoField(primary_key=True)
    id_olt = models.ForeignKey(
        ObjectifLongTerme,
        on_delete=models.CASCADE,
        related_name='niveaux_exigence',
        db_column='id_olt',
        verbose_name=_("Objectif à long terme")
    )
    libelle = models.CharField(
        _("Intitulé"),
        max_length=500,
        help_text=_("Intitulé du niveau d'exigence")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Description détaillée du niveau d'exigence")
    )

    # #249 / #261 — Ordre d'affichage parmi les pairs (même parent).
    # Mis à jour côté frontend via drag-and-drop. 0 = en tête.
    ordre = models.PositiveIntegerField(
        _("Ordre"),
        default=0,
        db_index=True,
        help_text=_("Ordre d'affichage parmi les éléments d'un même parent (0 = haut)")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_niveaux_exigence"'
        db_table_comment = "Niveaux d'exigence des objectifs à long terme"
        verbose_name = _("Niveau d'exigence")
        verbose_name_plural = _("Niveaux d'exigence")
        ordering = ['ordre', 'id_ne']

    def __str__(self):
        return f"{self.libelle} ({self.id_olt})"

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self.id_olt.id_enjeu.id_pg


class ObjectifOperationnel(models.Model):
    """
    Objectif opérationnel (OO) lié à une ou plusieurs pressions (M2M).
    Décrit les résultats concrets attendus pendant la durée du plan de gestion.
    Hiérarchie : Enjeu → FacteurInfluence → Pression ↔ OO (M2M) → ResultatAttendu.

    #337 — Pour un FCR (qui n'a ni facteur d'influence ni pression), l'OO peut
    être rattaché directement à l'enjeu/FCR via ``id_enjeu`` (sans pression).
    Un OO a donc soit des pressions (cas Enjeu), soit un enjeu direct (cas FCR).
    """

    id_oo = models.AutoField(primary_key=True)
    pressions = models.ManyToManyField(
        Pression,
        through='CorOoPression',
        related_name='objectifs_operationnels',
        blank=True,
        verbose_name=_("Pressions"),
        help_text=_("Pressions liées à cet objectif opérationnel")
    )
    # #337 — Rattachement direct à un enjeu/FCR sans pression préalable.
    id_enjeu = models.ForeignKey(
        Enjeu,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='objectifs_operationnels_directs',
        db_column='id_enjeu',
        verbose_name=_("Enjeu (rattachement direct)"),
        help_text=_("Rattachement direct à un enjeu/FCR sans passer par une pression (#337)")
    )
    libelle = models.CharField(
        _("Intitulé"),
        max_length=500,
        help_text=_("Intitulé de l'objectif opérationnel")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Description détaillée de l'objectif opérationnel")
    )

    # #249 / #261 — Ordre d'affichage parmi les pairs (même parent).
    # Mis à jour côté frontend via drag-and-drop. 0 = en tête.
    ordre = models.PositiveIntegerField(
        _("Ordre"),
        default=0,
        db_index=True,
        help_text=_("Ordre d'affichage parmi les éléments d'un même parent (0 = haut)")
    )

    # #526 / #442 — Numéro fixé manuellement par le gestionnaire (comme l'OLT).
    # NULL = numérotation automatique (dérivée de l'ordre). Quand renseigné, ce
    # numéro est réservé et l'auto-numérotation des autres OO le saute.
    numero_manuel = models.PositiveIntegerField(
        _("Numéro fixé manuellement"),
        null=True,
        blank=True,
        help_text=_("Numéro fixé manuellement (laisser vide pour la numérotation automatique)")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_objectifs_operationnels"'
        db_table_comment = "Objectifs opérationnels liés à des pressions"
        verbose_name = _("Objectif opérationnel")
        verbose_name_plural = _("Objectifs opérationnels")
        ordering = ['ordre', 'id_oo']

    def __str__(self):
        return self.libelle

    def get_plan_de_gestion(self):
        """
        Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248).
        Un OO est rattaché à des pressions via M2M : on remonte au plan via
        la première pression rattachée. #337 — à défaut de pression (cas FCR),
        on remonte au plan via l'enjeu rattaché directement.
        """
        first_pression = self.pressions.first()
        if first_pression is not None:
            return first_pression.get_plan_de_gestion()
        if self.id_enjeu_id:
            return self.id_enjeu.id_pg
        return None


class ResultatAttendu(models.Model):
    """
    Résultat attendu rattaché à un objectif opérationnel.
    Définit le résultat concret attendu pour atteindre l'OO.
    Miroir de NiveauExigence pour la vision opérationnelle.
    """

    id_ra = models.AutoField(primary_key=True)
    id_oo = models.ForeignKey(
        ObjectifOperationnel,
        on_delete=models.CASCADE,
        related_name='resultats_attendus',
        db_column='id_oo',
        verbose_name=_("Objectif opérationnel")
    )
    libelle = models.CharField(
        _("Intitulé"),
        max_length=500,
        help_text=_("Intitulé du résultat attendu")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Description détaillée du résultat attendu")
    )

    # #249 / #261 — Ordre d'affichage parmi les pairs (même parent).
    # Mis à jour côté frontend via drag-and-drop. 0 = en tête.
    ordre = models.PositiveIntegerField(
        _("Ordre"),
        default=0,
        db_index=True,
        help_text=_("Ordre d'affichage parmi les éléments d'un même parent (0 = haut)")
    )

    # Audit
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_ajout = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        related_name='+',
        db_column='id_utilisateur_ajout',
        verbose_name=_("Créateur")
    )
    id_utilisateur_maj = models.ForeignKey(
        'users.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        db_column='id_utilisateur_maj',
        verbose_name=_("Dernier modificateur")
    )

    class Meta:
        db_table = '"general"."t_resultats_attendus"'
        db_table_comment = "Résultats attendus des objectifs opérationnels"
        verbose_name = _("Résultat attendu")
        verbose_name_plural = _("Résultats attendus")
        ordering = ['ordre', 'id_ra']

    def __str__(self):
        return f"{self.libelle} ({self.id_oo})"

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self.id_oo.get_plan_de_gestion()


class CorOoPression(models.Model):
    """
    Table de jointure M2M entre ObjectifOperationnel et Pression.
    Un OO peut être lié à plusieurs pressions, et une pression peut
    être liée à plusieurs OO.
    """

    id_oo = models.ForeignKey(
        ObjectifOperationnel,
        on_delete=models.CASCADE,
        db_column='id_oo',
        verbose_name=_("Objectif opérationnel")
    )
    id_pression = models.ForeignKey(
        Pression,
        on_delete=models.CASCADE,
        db_column='id_pression',
        verbose_name=_("Pression")
    )

    class Meta:
        db_table = '"general"."cor_oo_pression"'
        unique_together = [('id_oo', 'id_pression')]
        verbose_name = _("Lien OO-Pression")
        verbose_name_plural = _("Liens OO-Pression")

    def __str__(self):
        return f"OO {self.id_oo_id} ↔ Pression {self.id_pression_id}"


class CorResponsabiliteTaxon(models.Model):
    """
    Liaison entre une responsabilité et des taxons (référentiel TaxRef).
    cd_nom est l'identifiant du taxon dans TaxRef.
    """

    id = models.AutoField(primary_key=True)
    id_responsabilite = models.ForeignKey(
        Responsabilite,
        on_delete=models.CASCADE,
        related_name='taxons',
        db_column='id_responsabilite',
        verbose_name=_("Responsabilité")
    )
    cd_nom = models.IntegerField(
        _("cd_nom"),
        help_text=_("Identifiant TaxRef du taxon")
    )
    # Champs dénormalisés pour l'affichage (optionnels)
    nom_complet = models.CharField(
        _("Nom complet"),
        max_length=500,
        blank=True,
        null=True
    )
    nom_vern = models.CharField(
        _("Nom vernaculaire"),
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        db_table = '"general"."cor_responsabilite_taxon"'
        db_table_comment = 'Liaison responsabilités - taxons'
        verbose_name = _("Responsabilité - Taxon")
        verbose_name_plural = _("Responsabilités - Taxons")
        unique_together = ['id_responsabilite', 'cd_nom']

    def __str__(self):
        return f"Responsabilité {self.id_responsabilite_id} - Taxon {self.cd_nom}"


class CorResponsabiliteHabitat(models.Model):
    """
    Liaison entre une responsabilité et des habitats (référentiel HabRef).
    cd_hab est l'identifiant de l'habitat dans HabRef.
    """

    id = models.AutoField(primary_key=True)
    id_responsabilite = models.ForeignKey(
        Responsabilite,
        on_delete=models.CASCADE,
        related_name='habitats',
        db_column='id_responsabilite',
        verbose_name=_("Responsabilité")
    )
    cd_hab = models.CharField(
        _("cd_hab"),
        max_length=50,
        help_text=_("Identifiant HabRef de l'habitat")
    )
    # Champ dénormalisé pour l'affichage
    lb_hab_fr = models.CharField(
        _("Libellé habitat"),
        max_length=500,
        blank=True,
        null=True
    )

    class Meta:
        db_table = '"general"."cor_responsabilite_habitat"'
        db_table_comment = 'Liaison responsabilités - habitats'
        verbose_name = _("Responsabilité - Habitat")
        verbose_name_plural = _("Responsabilités - Habitats")
        unique_together = ['id_responsabilite', 'cd_hab']

    def __str__(self):
        return f"Responsabilité {self.id_responsabilite_id} - Habitat {self.cd_hab}"


class CorResponsabiliteGeologie(models.Model):
    """
    Liaison entre une responsabilité et des éléments géologiques (référentiel INPG).
    id_inpg est l'identifiant dans le référentiel géologique.
    """

    id = models.AutoField(primary_key=True)
    id_responsabilite = models.ForeignKey(
        Responsabilite,
        on_delete=models.CASCADE,
        related_name='geologies',
        db_column='id_responsabilite',
        verbose_name=_("Responsabilité")
    )
    id_inpg = models.CharField(
        _("id_inpg"),
        max_length=50,
        help_text=_("Identifiant INPG de l'élément géologique")
    )
    # Champ dénormalisé pour l'affichage
    nom = models.CharField(
        _("Nom"),
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        db_table = '"general"."cor_responsabilite_geologie"'
        db_table_comment = 'Liaison responsabilités - géologie'
        verbose_name = _("Responsabilité - Géologie")
        verbose_name_plural = _("Responsabilités - Géologie")
        unique_together = ['id_responsabilite', 'id_inpg']

    def __str__(self):
        return f"Responsabilité {self.id_responsabilite_id} - Géologie {self.id_inpg}"


class CorResponsabiliteEnjeu(models.Model):
    """
    Liaison entre une responsabilité et des enjeux.
    Permet de rattacher les responsabilités aux enjeux du plan de gestion.
    """

    id = models.AutoField(primary_key=True)
    id_responsabilite = models.ForeignKey(
        Responsabilite,
        on_delete=models.CASCADE,
        related_name='enjeux_lies',
        db_column='id_responsabilite',
        verbose_name=_("Responsabilité")
    )
    id_enjeu = models.ForeignKey(
        Enjeu,
        on_delete=models.CASCADE,
        related_name='responsabilites_liees',
        db_column='id_enjeu',
        verbose_name=_("Enjeu")
    )

    class Meta:
        db_table = '"general"."cor_responsabilite_enjeu"'
        db_table_comment = 'Liaison responsabilités - enjeux'
        verbose_name = _("Responsabilité - Enjeu")
        verbose_name_plural = _("Responsabilités - Enjeux")
        unique_together = ['id_responsabilite', 'id_enjeu']

    def __str__(self):
        return f"Responsabilité {self.id_responsabilite_id} - Enjeu {self.id_enjeu_id}"


# ============================================
# TABLES DE CORRELATION POUR LES ENJEUX
# ============================================

class CorEnjeuTaxon(models.Model):
    """
    Liaison entre un enjeu et des taxons (référentiel TaxRef).
    cd_nom est l'identifiant du taxon dans TaxRef.
    """

    id = models.AutoField(primary_key=True)
    id_enjeu = models.ForeignKey(
        Enjeu,
        on_delete=models.CASCADE,
        related_name='taxons',
        db_column='id_enjeu',
        verbose_name=_("Enjeu")
    )
    cd_nom = models.IntegerField(
        _("cd_nom"),
        help_text=_("Identifiant TaxRef du taxon")
    )
    # Champs dénormalisés pour l'affichage (optionnels)
    nom_complet = models.CharField(
        _("Nom complet"),
        max_length=500,
        blank=True,
        null=True
    )
    nom_vern = models.CharField(
        _("Nom vernaculaire"),
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        db_table = '"general"."cor_enjeu_taxon"'
        db_table_comment = 'Liaison enjeux - taxons'
        verbose_name = _("Enjeu - Taxon")
        verbose_name_plural = _("Enjeux - Taxons")
        unique_together = ['id_enjeu', 'cd_nom']

    def __str__(self):
        return f"Enjeu {self.id_enjeu_id} - Taxon {self.cd_nom}"


class CorEnjeuHabitat(models.Model):
    """
    Liaison entre un enjeu et des habitats (référentiel HabRef).
    cd_hab est l'identifiant de l'habitat dans HabRef.
    """

    id = models.AutoField(primary_key=True)
    id_enjeu = models.ForeignKey(
        Enjeu,
        on_delete=models.CASCADE,
        related_name='habitats',
        db_column='id_enjeu',
        verbose_name=_("Enjeu")
    )
    # #368 — cd_hab nullable : un habitat « libre » (hors HabRef, ex. Outre-mer)
    # est saisi sans code, seul `lb_hab_fr` est renseigné. Postgres autorise
    # plusieurs lignes à cd_hab NULL pour un même enjeu (NULL distincts dans la
    # contrainte d'unicité), donc plusieurs habitats libres sont possibles.
    cd_hab = models.CharField(
        _("cd_hab"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Identifiant HabRef de l'habitat (vide pour un habitat saisi librement, #368)")
    )
    # Champ dénormalisé pour l'affichage
    lb_hab_fr = models.CharField(
        _("Libellé habitat"),
        max_length=500,
        blank=True,
        null=True
    )

    class Meta:
        db_table = '"general"."cor_enjeu_habitat"'
        db_table_comment = 'Liaison enjeux - habitats'
        verbose_name = _("Enjeu - Habitat")
        verbose_name_plural = _("Enjeux - Habitats")
        unique_together = ['id_enjeu', 'cd_hab']

    def __str__(self):
        return f"Enjeu {self.id_enjeu_id} - Habitat {self.cd_hab}"


class CorEnjeuGeologie(models.Model):
    """
    Liaison entre un enjeu et des éléments géologiques (référentiel INPG).
    id_inpg est l'identifiant dans le référentiel géologique.
    """

    id = models.AutoField(primary_key=True)
    id_enjeu = models.ForeignKey(
        Enjeu,
        on_delete=models.CASCADE,
        related_name='geologies',
        db_column='id_enjeu',
        verbose_name=_("Enjeu")
    )
    id_inpg = models.CharField(
        _("id_inpg"),
        max_length=50,
        help_text=_("Identifiant INPG de l'élément géologique")
    )
    # Champ dénormalisé pour l'affichage
    nom = models.CharField(
        _("Nom"),
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        db_table = '"general"."cor_enjeu_geologie"'
        db_table_comment = 'Liaison enjeux - géologie'
        verbose_name = _("Enjeu - Géologie")
        verbose_name_plural = _("Enjeux - Géologie")
        unique_together = ['id_enjeu', 'id_inpg']

    def __str__(self):
        return f"Enjeu {self.id_enjeu_id} - Géologie {self.id_inpg}"


class CorEnjeuObjetGeologique(models.Model):
    """
    #237 — Objet(s) géologique(s) d'un enjeu, issus de la typologie PatriNat.
    L'objet référence désormais une nomenclature `TYPE_OBJET_GEOLOGIQUE`
    (référentiel centralisé) ; `precision` reste une saisie libre pour les
    objets de type « Autre ».
    """

    id = models.AutoField(primary_key=True)
    id_enjeu = models.ForeignKey(
        Enjeu,
        on_delete=models.CASCADE,
        related_name='objets_geologiques',
        db_column='id_enjeu',
        verbose_name=_("Enjeu")
    )
    id_objet_geologique = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.PROTECT,
        related_name='enjeux_objet_geologique',
        db_column='id_objet_geologique',
        verbose_name=_("Objet géologique"),
        help_text=_("Type d'objet géologique (nomenclature TYPE_OBJET_GEOLOGIQUE)"),
        limit_choices_to={'id_type__mnemonique': 'TYPE_OBJET_GEOLOGIQUE'},
    )
    # #237 — précision libre pour un objet de type « Autre »
    precision = models.CharField(
        _("Précision"),
        max_length=255,
        blank=True,
        default=''
    )

    class Meta:
        db_table = '"general"."cor_enjeu_objet_geologique"'
        db_table_comment = 'Liaison enjeux - objets géologiques (#237)'
        verbose_name = _("Enjeu - Objet géologique")
        verbose_name_plural = _("Enjeux - Objets géologiques")
        unique_together = ['id_enjeu', 'id_objet_geologique']

    def __str__(self):
        return f"Enjeu {self.id_enjeu_id} - Objet géologique {self.id_objet_geologique_id}"


class CorEnjeuFichier(models.Model):
    """
    #237 — Documents rattachés au patrimoine « Documents » d'un enjeu géologique.

    Un document est soit :
    - numérique (`support='numerique'`) : fichier téléversé et stocké sur le
      serveur (PDF, image, archive…) ;
    - papier (`support='papier'`) : simple référence décrite par un titre
      (aucun fichier stocké), pour les archives papier non numérisées.
    """

    SUPPORT_CHOICES = [
        ('numerique', _('Numérique')),
        ('papier', _('Papier')),
    ]

    id = models.AutoField(primary_key=True)
    id_enjeu = models.ForeignKey(
        Enjeu,
        on_delete=models.CASCADE,
        related_name='fichiers',
        db_column='id_enjeu',
        verbose_name=_("Enjeu")
    )
    support = models.CharField(
        _("Support"),
        max_length=10,
        choices=SUPPORT_CHOICES,
        default='numerique'
    )

    # Informations sur le fichier (vides pour un document papier)
    nom_fichier = models.CharField(_("Nom du fichier"), max_length=255, blank=True, default='')
    chemin_fichier = models.CharField(_("Chemin du fichier"), max_length=500, blank=True, default='')
    taille_fichier = models.BigIntegerField(_("Taille du fichier (bytes)"), null=True, blank=True)
    extension = models.CharField(_("Extension"), max_length=10, blank=True, default='')

    # Métadonnées descriptives
    titre = models.CharField(
        _("Titre / référence"),
        max_length=255,
        blank=True,
        default='',
        help_text=_("Titre du document numérique ou référence du document papier")
    )
    description = models.TextField(_("Description"), blank=True, default='')

    date_upload = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    id_utilisateur_upload = models.ForeignKey(
        'users.Role',
        on_delete=models.PROTECT,
        null=True, blank=True,
        db_column='id_utilisateur_upload',
        verbose_name=_("Utilisateur ayant ajouté")
    )
    ordre_affichage = models.IntegerField(_("Ordre d'affichage"), default=0)

    class Meta:
        db_table = '"fichiers"."t_enjeu_fichiers"'
        db_table_comment = 'Documents rattachés aux enjeux géologiques (#237)'
        verbose_name = _("Enjeu - Document")
        verbose_name_plural = _("Enjeux - Documents")
        ordering = ['ordre_affichage', 'nom_fichier']

    def __str__(self):
        return f"Enjeu {self.id_enjeu_id} - Document {self.titre or self.nom_fichier}"

    def get_plan_de_gestion(self):
        """Implémente l'interface utilisée par CanModifyOnlyDraftPlan (#248)."""
        return self.id_enjeu.get_plan_de_gestion()

    def get_file_size_human(self):
        if not self.taille_fichier:
            return None
        size = float(self.taille_fichier)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def handle_file_upload(self, uploaded_file):
        """Stocke un fichier téléversé sous `enjeux/{id_enjeu}/`."""
        import os
        from django.conf import settings
        from django.core.files.storage import default_storage

        self.support = 'numerique'
        if not self.nom_fichier:
            self.nom_fichier = uploaded_file.name
        _, ext = os.path.splitext(self.nom_fichier)
        self.extension = ext.lower()
        self.taille_fichier = uploaded_file.size

        upload_dir = f"enjeux/{self.id_enjeu_id}"
        os.makedirs(os.path.join(settings.MEDIA_ROOT, upload_dir), exist_ok=True)
        file_path = os.path.join(upload_dir, self.nom_fichier)
        self.chemin_fichier = default_storage.save(file_path, uploaded_file)
        self.save()
