"""
Modèles pour les Indicateurs, Métriques et Mesures.
Hiérarchie : NiveauExigence → Indicateur(s) → Métrique(s) → Mesure(s)
             ResultatAttendu → Indicateur(s) → Métrique(s) → Mesure(s)
"""
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class Indicateur(models.Model):
    """
    Indicateur rattaché à un niveau d'exigence (OLT) ou un résultat attendu (OO).
    Types : état, pression, réponse.
    Peut avoir des liens taxonomiques (taxon, habitat, géologie).
    Exactement un des deux parents (id_ne ou id_resultat_attendu) doit être défini.
    """

    id_indicateur = models.AutoField(primary_key=True)
    id_ne = models.ForeignKey(
        'plans.NiveauExigence',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='indicateurs',
        db_column='id_ne',
        verbose_name=_("Niveau d'exigence")
    )
    id_resultat_attendu = models.ForeignKey(
        'plans.ResultatAttendu',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='indicateurs',
        db_column='id_resultat_attendu',
        verbose_name=_("Résultat attendu")
    )
    nom_indicateur = models.CharField(
        _("Nom de l'indicateur"),
        max_length=500,
        help_text=_("Intitulé de l'indicateur")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Description détaillée de l'indicateur")
    )
    type_indicateur = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='indicateurs_type',
        db_column='type_indicateur',
        verbose_name=_("Type d'indicateur"),
        help_text=_("État, Pression ou Réponse"),
        limit_choices_to={'id_type__mnemonique': 'TYPE_INDICATEUR'}
    )
    est_standardise = models.BooleanField(
        _("Indicateur standardisé"),
        default=False,
        help_text=_("L'indicateur est-il standardisé ?")
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
        db_table = '"general"."t_indicateurs"'
        db_table_comment = "Indicateurs des niveaux d'exigence et résultats attendus"
        verbose_name = _("Indicateur")
        verbose_name_plural = _("Indicateurs")
        ordering = ['nom_indicateur']

    def clean(self):
        """Valider qu'au moins un parent est défini."""
        if not self.id_ne and not self.id_resultat_attendu:
            raise ValidationError(
                _("Un indicateur doit être rattaché à un niveau d'exigence ou un résultat attendu.")
            )
        if self.id_ne and self.id_resultat_attendu:
            raise ValidationError(
                _("Un indicateur ne peut être rattaché qu'à un seul parent (niveau d'exigence OU résultat attendu).")
            )

    def __str__(self):
        parent = self.id_ne or self.id_resultat_attendu
        return f"{self.nom_indicateur} ({parent})"


class CorIndicateurTaxon(models.Model):
    """
    Liaison entre un indicateur et des taxons (référentiel TaxRef).
    """

    id = models.AutoField(primary_key=True)
    id_indicateur = models.ForeignKey(
        Indicateur,
        on_delete=models.CASCADE,
        related_name='taxons',
        db_column='id_indicateur',
        verbose_name=_("Indicateur")
    )
    cd_nom = models.IntegerField(
        _("cd_nom"),
        help_text=_("Identifiant TaxRef du taxon")
    )
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
        db_table = '"general"."cor_indicateur_taxon"'
        db_table_comment = 'Liaison indicateurs - taxons'
        verbose_name = _("Indicateur - Taxon")
        verbose_name_plural = _("Indicateurs - Taxons")
        unique_together = ['id_indicateur', 'cd_nom']

    def __str__(self):
        return f"Indicateur {self.id_indicateur_id} - Taxon {self.cd_nom}"


class CorIndicateurHabitat(models.Model):
    """
    Liaison entre un indicateur et des habitats (référentiel HabRef).
    """

    id = models.AutoField(primary_key=True)
    id_indicateur = models.ForeignKey(
        Indicateur,
        on_delete=models.CASCADE,
        related_name='habitats',
        db_column='id_indicateur',
        verbose_name=_("Indicateur")
    )
    cd_hab = models.CharField(
        _("cd_hab"),
        max_length=50,
        help_text=_("Identifiant HabRef de l'habitat")
    )
    lb_hab_fr = models.CharField(
        _("Libellé habitat"),
        max_length=500,
        blank=True,
        null=True
    )

    class Meta:
        db_table = '"general"."cor_indicateur_habitat"'
        db_table_comment = 'Liaison indicateurs - habitats'
        verbose_name = _("Indicateur - Habitat")
        verbose_name_plural = _("Indicateurs - Habitats")
        unique_together = ['id_indicateur', 'cd_hab']

    def __str__(self):
        return f"Indicateur {self.id_indicateur_id} - Habitat {self.cd_hab}"


class CorIndicateurGeologie(models.Model):
    """
    Liaison entre un indicateur et des éléments géologiques (référentiel INPG).
    """

    id = models.AutoField(primary_key=True)
    id_indicateur = models.ForeignKey(
        Indicateur,
        on_delete=models.CASCADE,
        related_name='geologies',
        db_column='id_indicateur',
        verbose_name=_("Indicateur")
    )
    id_inpg = models.CharField(
        _("id_inpg"),
        max_length=50,
        help_text=_("Identifiant INPG de l'élément géologique")
    )
    nom = models.CharField(
        _("Nom"),
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        db_table = '"general"."cor_indicateur_geologie"'
        db_table_comment = 'Liaison indicateurs - géologie'
        verbose_name = _("Indicateur - Géologie")
        verbose_name_plural = _("Indicateurs - Géologie")
        unique_together = ['id_indicateur', 'id_inpg']

    def __str__(self):
        return f"Indicateur {self.id_indicateur_id} - Géologie {self.id_inpg}"


class Metrique(models.Model):
    """
    Métrique rattachée à un indicateur.
    Contient des seuils de scores (5 niveaux) et des labels qualitatifs.
    """

    id_metrique = models.AutoField(primary_key=True)
    id_indicateur = models.ForeignKey(
        Indicateur,
        on_delete=models.CASCADE,
        related_name='metriques',
        db_column='id_indicateur',
        verbose_name=_("Indicateur")
    )
    nom_metrique = models.CharField(
        _("Nom de la métrique"),
        max_length=500,
        help_text=_("Intitulé de la métrique")
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        null=True,
        help_text=_("Description détaillée de la métrique")
    )
    type_metrique = models.ForeignKey(
        'core.Nomenclature',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='metriques_type',
        db_column='type_metrique',
        verbose_name=_("Type de métrique"),
        help_text=_("Numérique, Qualitatif ou Booléen"),
        limit_choices_to={'id_type__mnemonique': 'TYPE_METRIQUE'}
    )
    unite = models.CharField(
        _("Unité"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Unité de mesure (ex: %, m², individus)")
    )
    ponderation = models.DecimalField(
        _("Pondération"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Pondération de la métrique dans l'indicateur")
    )
    etat_reference = models.TextField(
        _("État de référence"),
        blank=True,
        null=True,
        help_text=_("Description de l'état de référence")
    )

    # Seuils de scores (5 niveaux, bornes inf et sup)
    score_1_inf = models.DecimalField(
        _("Score 1 - Borne inférieure"),
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_1_sup = models.DecimalField(
        _("Score 1 - Borne supérieure"),
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_2_inf = models.DecimalField(
        _("Score 2 - Borne inférieure"),
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_2_sup = models.DecimalField(
        _("Score 2 - Borne supérieure"),
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_3_inf = models.DecimalField(
        _("Score 3 - Borne inférieure"),
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_3_sup = models.DecimalField(
        _("Score 3 - Borne supérieure"),
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_4_inf = models.DecimalField(
        _("Score 4 - Borne inférieure"),
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_4_sup = models.DecimalField(
        _("Score 4 - Borne supérieure"),
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_5_inf = models.DecimalField(
        _("Score 5 - Borne inférieure"),
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_5_sup = models.DecimalField(
        _("Score 5 - Borne supérieure"),
        max_digits=12, decimal_places=4, null=True, blank=True
    )

    # Valeurs simples (type CHIFFRE)
    score_1_val = models.DecimalField(
        _("Score 1 - Valeur"), max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_2_val = models.DecimalField(
        _("Score 2 - Valeur"), max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_3_val = models.DecimalField(
        _("Score 3 - Valeur"), max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_4_val = models.DecimalField(
        _("Score 4 - Valeur"), max_digits=12, decimal_places=4, null=True, blank=True
    )
    score_5_val = models.DecimalField(
        _("Score 5 - Valeur"), max_digits=12, decimal_places=4, null=True, blank=True
    )

    # Labels qualitatifs pour chaque niveau de score
    score_1_label = models.CharField(
        _("Label score 1"), max_length=255, blank=True, null=True,
        help_text=_("Label qualitatif pour le score 1 (Très mauvais)")
    )
    score_2_label = models.CharField(
        _("Label score 2"), max_length=255, blank=True, null=True,
        help_text=_("Label qualitatif pour le score 2 (Mauvais)")
    )
    score_3_label = models.CharField(
        _("Label score 3"), max_length=255, blank=True, null=True,
        help_text=_("Label qualitatif pour le score 3 (Moyen)")
    )
    score_4_label = models.CharField(
        _("Label score 4"), max_length=255, blank=True, null=True,
        help_text=_("Label qualitatif pour le score 4 (Bon)")
    )
    score_5_label = models.CharField(
        _("Label score 5"), max_length=255, blank=True, null=True,
        help_text=_("Label qualitatif pour le score 5 (Très bon)")
    )

    # Direction des intervalles
    sens_variation = models.CharField(
        _("Sens de variation"),
        max_length=20,
        choices=[('CROISSANT', _('Croissant')), ('DECROISSANT', _('Décroissant'))],
        default='CROISSANT',
        help_text=_("Croissant = plus c'est haut mieux c'est, Décroissant = plus c'est bas mieux c'est")
    )

    # Inclusivité des bornes entre niveaux (4 frontières pour 5 niveaux)
    score_1_sup_inclusive = models.BooleanField(
        _("Borne sup score 1 inclusive"), default=True,
        help_text=_("True: score 1 ≤ seuil, score 2 > seuil. False: score 1 < seuil, score 2 ≥ seuil")
    )
    score_2_sup_inclusive = models.BooleanField(
        _("Borne sup score 2 inclusive"), default=True
    )
    score_3_sup_inclusive = models.BooleanField(
        _("Borne sup score 3 inclusive"), default=True
    )
    score_4_sup_inclusive = models.BooleanField(
        _("Borne sup score 4 inclusive"), default=True
    )

    # Bornes extrêmes optionnelles (persiste l'état des checkboxes)
    has_borne_score1 = models.BooleanField(
        _("Borne extrême score 1 active"), default=False,
        help_text=_("Croissant: borne inf score 1 active. Décroissant: borne sup score 1 active.")
    )
    has_borne_score5 = models.BooleanField(
        _("Borne extrême score 5 active"), default=False,
        help_text=_("Croissant: borne sup score 5 active. Décroissant: borne inf score 5 active.")
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
        db_table = '"general"."t_metriques"'
        db_table_comment = "Métriques des indicateurs"
        verbose_name = _("Métrique")
        verbose_name_plural = _("Métriques")
        ordering = ['nom_metrique']

    def __str__(self):
        return f"{self.nom_metrique} ({self.id_indicateur})"


class Mesure(models.Model):
    """
    Mesure datée rattachée à une métrique.
    La valeur est stockée en varchar pour flexibilité (numérique ou qualitatif).
    """

    id_mesure = models.AutoField(primary_key=True)
    id_metrique = models.ForeignKey(
        Metrique,
        on_delete=models.CASCADE,
        related_name='mesures',
        db_column='id_metrique',
        verbose_name=_("Métrique")
    )
    valeur = models.CharField(
        _("Valeur"),
        max_length=500,
        help_text=_("Valeur de la mesure (numérique ou qualitative)")
    )
    date_mesure = models.DateField(
        _("Date de mesure"),
        null=True,
        blank=True,
        help_text=_("Date à laquelle la mesure a été effectuée")
    )
    commentaire = models.TextField(
        _("Commentaire"),
        blank=True,
        null=True,
        help_text=_("Commentaire sur la mesure")
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
        db_table = '"general"."t_mesures"'
        db_table_comment = "Mesures des métriques"
        verbose_name = _("Mesure")
        verbose_name_plural = _("Mesures")
        ordering = ['-date_mesure', '-date_ajout']

    def __str__(self):
        date_str = self.date_mesure.isoformat() if self.date_mesure else "?"
        return f"{self.valeur} ({date_str}) - {self.id_metrique}"
