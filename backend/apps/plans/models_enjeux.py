"""
Modèles pour les Enjeux, FCR (Facteurs Clés de Réussite) et Responsabilités.
"""
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
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
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Max 25 caractères pour affichage")
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
        default=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text=_("Priorité de l'enjeu (1=haute, 2=moyenne, 3=basse)")
    )
    # Catégorie écologique/socio-économique - Seulement pour Enjeux
    categorie_ecologique = models.BooleanField(
        _("Catégorie écologique"),
        default=True,
        null=True,
        help_text=_("True=Écologique, False=Socio-économique")
    )
    # Type d'enjeu (checkboxes) - Seulement pour Enjeux
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
    processus = models.BooleanField(
        _("Processus"),
        default=False,
        help_text=_("Enjeu lié à un processus écologique")
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
        ordering = ['rang', 'libelle']

    @property
    def nb_facteurs_influence(self):
        """Retourne le nombre de facteurs d'influence."""
        return self.facteurs_influence.count()

    def __str__(self):
        return f"{self.libelle} ({self.id_pg})"

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
        ordering = ['libelle']

    def __str__(self):
        return f"{self.libelle} ({self.id_enjeu})"


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
        ordering = ['libelle']

    def __str__(self):
        return f"{self.libelle} ({self.id_facteur_influence})"


# ============================================
# TABLES DE CORRELATION POUR LES RESPONSABILITÉS
# ============================================

class ObjectifLongTerme(models.Model):
    """
    Objectif à long terme (OLT) rattaché à un enjeu.
    Traduit l'état souhaité de l'enjeu à l'issue du plan de gestion.
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
        ordering = ['libelle']

    def __str__(self):
        return f"{self.libelle} ({self.id_enjeu})"


class EtatActuel(models.Model):
    """
    État actuel d'un OLT (relation 1:1).
    Décrit l'état de conservation actuel associé à un objectif à long terme.
    """

    id_etat_actuel = models.AutoField(primary_key=True)
    id_olt = models.OneToOneField(
        ObjectifLongTerme,
        on_delete=models.CASCADE,
        related_name='etat_actuel',
        db_column='id_olt',
        verbose_name=_("Objectif à long terme")
    )
    libelle = models.CharField(
        _("Intitulé"),
        max_length=500,
        help_text=_("Intitulé de l'état actuel")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Description détaillée de l'état actuel")
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
        db_table = '"general"."t_etat_actuel"'
        db_table_comment = "États actuels des objectifs à long terme (1:1)"
        verbose_name = _("État actuel")
        verbose_name_plural = _("États actuels")
        ordering = ['libelle']

    def __str__(self):
        return f"{self.libelle} ({self.id_olt})"


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
        ordering = ['libelle']

    def __str__(self):
        return f"{self.libelle} ({self.id_olt})"


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
