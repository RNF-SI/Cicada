"""
Modèle pour l'Inventaire National du Patrimoine Géologique (INPG).

Schema PostgreSQL : ref_inpg
Données provenant du projet socle (base INPG de l'INPN).
"""

from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


class Inpg(models.Model):
    """Site géologique de l'INPG."""

    id_inpg = models.IntegerField(_("ID INPG"), primary_key=True)
    geom = models.MultiPolygonField(_("Géométrie"), srid=4326, null=True, blank=True)
    id_metier = models.CharField(_("ID métier"), max_length=50, null=True, blank=True)
    surface = models.CharField(_("Surface"), max_length=100, null=True, blank=True)
    lb_site = models.TextField(_("Nom du site"), null=True, blank=True)
    typologie_1 = models.CharField(_("Typologie 1"), max_length=255, null=True, blank=True)
    typologie_2 = models.CharField(_("Typologie 2"), max_length=255, null=True, blank=True)
    typologie_3 = models.CharField(_("Typologie 3"), max_length=255, null=True, blank=True)
    accessibilite_1 = models.CharField(_("Accessibilité 1"), max_length=255, null=True, blank=True)
    accessibilite_2 = models.CharField(_("Accessibilité 2"), max_length=255, null=True, blank=True)
    region = models.CharField(_("Région"), max_length=255, null=True, blank=True)
    departements = models.TextField(_("Départements"), null=True, blank=True)
    communes = models.TextField(_("Communes"), null=True, blank=True)
    niveau_de_diffusion = models.CharField(_("Niveau de diffusion"), max_length=50, null=True, blank=True)
    organismes_contacts = models.TextField(_("Organismes contacts"), null=True, blank=True)
    superficie_saisie = models.FloatField(_("Superficie saisie"), null=True, blank=True)
    justification_de_superficie = models.TextField(_("Justification de superficie"), null=True, blank=True)
    unite_de_superficie = models.CharField(_("Unité de superficie"), max_length=50, null=True, blank=True)
    etat_de_conservation = models.CharField(_("État de conservation"), max_length=255, null=True, blank=True)
    presentation_succinte = models.TextField(_("Présentation succincte"), null=True, blank=True)
    description_physique = models.TextField(_("Description physique"), null=True, blank=True)
    description_geologique = models.TextField(_("Description géologique"), null=True, blank=True)
    itineraire_dacces = models.TextField(_("Itinéraire d'accès"), null=True, blank=True)
    code_gilges = models.TextField(_("Code GILGES"), null=True, blank=True)
    phenomene_geologique = models.TextField(_("Phénomène géologique"), null=True, blank=True)
    interet_geol_principal = models.CharField(_("Intérêt géologique principal"), max_length=255, null=True, blank=True)
    justification_interet_geologique_principal = models.TextField(_("Justification intérêt géologique principal"), null=True, blank=True)
    interets_geologiques_secondaires = models.TextField(_("Intérêts géologiques secondaires"), null=True, blank=True)
    interets_geologiques_secondaires_avec_justification = models.TextField(_("Intérêts géologiques secondaires avec justification"), null=True, blank=True)
    interets_pedagogiques = models.TextField(_("Intérêts pédagogiques"), null=True, blank=True)
    justification_interets_pedagogiques = models.TextField(_("Justification intérêts pédagogiques"), null=True, blank=True)
    interets_annexes = models.TextField(_("Intérêts annexes"), null=True, blank=True)
    interets_annexes_avec_justification = models.TextField(_("Intérêts annexes avec justification"), null=True, blank=True)
    interet_histoire_sciences_geologiques = models.TextField(_("Intérêt histoire sciences géologiques"), null=True, blank=True)
    rarete = models.CharField(_("Rareté"), max_length=255, null=True, blank=True)
    informateurs = models.TextField(_("Informateurs"), null=True, blank=True)
    stratigraphie_age_le_plus_ancien_du_phenomene = models.TextField(
        _("Stratigraphie âge le plus ancien du phénomène"), null=True, blank=True,
        db_column='stratigraphie__ge_le_plus_ancien_du_phenomene',
    )
    stratigraphie_age_le_plus_recent_du_phenomene = models.TextField(
        _("Stratigraphie âge le plus récent du phénomène"), null=True, blank=True,
        db_column='stratigraphie__ge_le_plus_recent_du_phenomene',
    )
    stratigraphie_age_le_plus_ancien_du_terrain = models.TextField(
        _("Stratigraphie âge le plus ancien du terrain"), null=True, blank=True,
        db_column='stratigraphie__ge_le_plus_ancien_du_terrain',
    )
    stratigraphie_age_le_plus_recent_du_terrain = models.TextField(
        _("Stratigraphie âge le plus récent du terrain"), null=True, blank=True,
        db_column='stratigraphie__ge_le_plus_recent_du_terrain',
    )
    commentaire_sur_levaluation_du_site = models.TextField(_("Commentaire sur l'évaluation du site"), null=True, blank=True)
    vulnerabilite_naturelle = models.TextField(_("Vulnérabilité naturelle"), null=True, blank=True)
    menace_anthropique = models.TextField(_("Menace anthropique"), null=True, blank=True)
    commentaire_besoin_de_protection = models.TextField(_("Commentaire besoin de protection"), null=True, blank=True)
    commentaire_general_sur_les_menaces = models.TextField(_("Commentaire général sur les menaces"), null=True, blank=True)
    note_geologique_principale = models.IntegerField(_("Note géologique principale"), null=True, blank=True)
    note_geologique_secondaire = models.IntegerField(_("Note géologique secondaire"), null=True, blank=True)
    note_pedagogique = models.IntegerField(_("Note pédagogique"), null=True, blank=True)
    note_histoire_des_sciences = models.IntegerField(_("Note histoire des sciences"), null=True, blank=True)
    note_rarete = models.IntegerField(_("Note rareté"), null=True, blank=True)
    note_etat_conservation = models.IntegerField(_("Note état conservation"), null=True, blank=True)
    note_interet_patrimonial = models.IntegerField(_("Note intérêt patrimonial"), null=True, blank=True)
    nombre_etoiles = models.IntegerField(_("Nombre d'étoiles"), null=True, blank=True)
    note_vulnerabilite_naturelle = models.IntegerField(_("Note vulnérabilité naturelle"), null=True, blank=True)
    note_menace_anthropique = models.IntegerField(_("Note menace anthropique"), null=True, blank=True)
    note_protection_effective = models.IntegerField(_("Note protection effective"), null=True, blank=True)
    note_besoin_de_protection = models.IntegerField(_("Note besoin de protection"), null=True, blank=True)
    lieudit = models.TextField(_("Lieu-dit"), null=True, blank=True)
    nombre_de_documentations = models.IntegerField(_("Nombre de documentations"), null=True, blank=True)
    legendes_figures = models.TextField(_("Légendes figures"), null=True, blank=True)
    cartes_geologiques_associees = models.TextField(_("Cartes géologiques associées"), null=True, blank=True)
    cartes_ign_associees = models.TextField(_("Cartes IGN associées"), null=True, blank=True)
    cartes_marines_associees = models.TextField(_("Cartes marines associées"), null=True, blank=True)
    zonages_de_reference = models.TextField(_("Zonages de référence"), null=True, blank=True)
    bibliographies_associees = models.TextField(_("Bibliographies associées"), null=True, blank=True)
    collections_associees = models.TextField(_("Collections associées"), null=True, blank=True)
    associations_avec_dautres_sites = models.TextField(_("Associations avec d'autres sites"), null=True, blank=True)
    date_de_premiere_visite = models.CharField(_("Date de première visite"), max_length=50, null=True, blank=True)
    date_de_derniere_visite = models.CharField(_("Date de dernière visite"), max_length=50, null=True, blank=True)
    date_creation_du_site = models.CharField(_("Date création du site"), max_length=50, null=True, blank=True)
    statut_actuel_de_la_fiche = models.CharField(_("Statut actuel de la fiche"), max_length=255, null=True, blank=True)
    ancien_statut_de_la_fiche = models.CharField(_("Ancien statut de la fiche"), max_length=255, null=True, blank=True)
    statut_de_validation_metier = models.CharField(_("Statut validation métier"), max_length=50, null=True, blank=True)
    statut_de_validation_crpg = models.CharField(_("Statut validation CRPG"), max_length=50, null=True, blank=True)
    statut_de_validation_regionale = models.CharField(_("Statut validation régionale"), max_length=50, null=True, blank=True)
    statut_de_validation_nationale = models.CharField(_("Statut validation nationale"), max_length=50, null=True, blank=True)
    statut_de_dept_sig = models.CharField(_("Statut dept SIG"), max_length=50, null=True, blank=True)
    statut_de_validation_sig = models.CharField(_("Statut validation SIG"), max_length=50, null=True, blank=True)
    statut_de_diffusion_inpn = models.CharField(_("Statut diffusion INPN"), max_length=50, null=True, blank=True)
    derniere_date_de_modification_de_la_fiche = models.CharField(_("Dernière date de modification"), max_length=50, null=True, blank=True)
    date_de_validation_metier = models.CharField(_("Date validation métier"), max_length=50, null=True, blank=True)
    date_de_validation_crpg_actuelle = models.CharField(_("Date validation CRPG actuelle"), max_length=50, null=True, blank=True)
    date_de_premiere_validation_regionale = models.CharField(_("Date première validation régionale"), max_length=50, null=True, blank=True)
    date_de_validation_regionale_actuelle = models.CharField(_("Date validation régionale actuelle"), max_length=50, null=True, blank=True)
    date_de_premiere_validation_nationale = models.CharField(_("Date première validation nationale"), max_length=50, null=True, blank=True)
    date_de_validation_nationale_actuelle = models.CharField(_("Date validation nationale actuelle"), max_length=50, null=True, blank=True)
    date_de_premiere_diffusion = models.CharField(_("Date première diffusion"), max_length=50, null=True, blank=True)
    date_de_diffusion_actuelle = models.CharField(_("Date diffusion actuelle"), max_length=50, null=True, blank=True)

    class Meta:
        db_table = '"ref_inpg"."inpg"'
        managed = True
        verbose_name = _("Site géologique INPG")
        verbose_name_plural = _("Sites géologiques INPG")
        ordering = ['id_inpg']

    def __str__(self):
        return f"{self.id_metier} - {self.lb_site}"
