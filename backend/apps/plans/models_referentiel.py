"""
Versions du référentiel des types d'action et passages de l'une à l'autre (#751).

Le référentiel des types d'action (nomenclatures TYPE_ACTION et
CATEGORIE_ACTION_RESERVE) change de version : codification Eden 62, puis
Gestref V1, puis les versions suivantes de Gestref. Un **passage** applique une
table de correspondance aux actions et aux suivis déjà saisis :

- correspondance sûre ou probable → l'objet prend le nouveau type ;
- correspondance à arbitrer → son type est vidé, l'objet est « à actualiser »
  et les référents du plan sont prévenus ;
- chaque objet touché est consigné (`PassageReferentielObjet`), ce qui permet
  d'annuler le passage et de suivre qui a actualisé quoi.

Règles et traitements : `apps/plans/referentiel_actions.py`.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class VersionReferentielActions(models.Model):
    """Une version du référentiel : les lignes de nomenclature qui la composent.

    `lignes` garde, pour chaque nomenclature de la version, son état propre
    (libellé, hiérarchie, définition) : une catégorie partagée par deux
    versions (CS, IP, SP) change de libellé de l'une à l'autre, et l'import
    des nomenclatures (`import_nomenclatures --force`) ne doit pas remettre
    celui d'une version qui n'est plus la courante.
    """

    id_version = models.AutoField(primary_key=True)
    code = models.CharField(_("Code"), max_length=50, unique=True)
    libelle = models.CharField(_("Libellé"), max_length=255)
    # [{"id": 900, "nomenclature": "TYPE_ACTION" | "CATEGORIE_ACTION_RESERVE",
    #   "code": "IP1", "libelle": "…", "hierarchy": "…", "definition": "…"}]
    lignes = models.JSONField(_("Lignes"), default=list)
    courante = models.BooleanField(_("Version courante"), default=False)
    date_creation = models.DateTimeField(_("Date de création"), auto_now_add=True)

    class Meta:
        db_table = '"general"."t_referentiel_action_versions"'
        db_table_comment = "Versions du référentiel des types d'action (#751)"
        verbose_name = _("Version du référentiel des types d'action")
        verbose_name_plural = _("Versions du référentiel des types d'action")

    def __str__(self):
        return self.libelle or self.code


class PassageReferentielActions(models.Model):
    """Application d'une table de correspondance entre deux versions."""

    STATUT_APPLIQUE = 'applique'
    STATUT_ANNULE = 'annule'
    STATUTS = [
        (STATUT_APPLIQUE, _("Appliqué")),
        (STATUT_ANNULE, _("Annulé")),
    ]

    id_passage = models.AutoField(primary_key=True)
    source = models.ForeignKey(
        VersionReferentielActions, on_delete=models.PROTECT,
        related_name='passages_depart', verbose_name=_("Version de départ"),
    )
    cible = models.ForeignKey(
        VersionReferentielActions, on_delete=models.PROTECT,
        related_name='passages_arrivee', verbose_name=_("Version d'arrivée"),
    )
    statut = models.CharField(_("Statut"), max_length=20, choices=STATUTS,
                              default=STATUT_APPLIQUE)
    date_application = models.DateTimeField(_("Appliqué le"), auto_now_add=True)
    date_annulation = models.DateTimeField(_("Annulé le"), null=True, blank=True)
    resume = models.JSONField(_("Résumé"), default=dict)

    class Meta:
        db_table = '"general"."t_referentiel_action_passages"'
        db_table_comment = "Passages d'une version du référentiel des types d'action à une autre (#751)"
        ordering = ['-date_application']
        verbose_name = _("Passage de référentiel des types d'action")
        verbose_name_plural = _("Passages de référentiel des types d'action")

    def __str__(self):
        return f"{self.source.code} → {self.cible.code}"


class PassageReferentielObjet(models.Model):
    """Une action ou un suivi touché par un passage, et ce qu'il en est advenu."""

    CONFIANCE_SURE = 'sure'
    CONFIANCE_PROBABLE = 'probable'
    CONFIANCE_A_ARBITRER = 'a_arbitrer'
    CONFIANCES = [
        (CONFIANCE_SURE, _("Sûre")),
        (CONFIANCE_PROBABLE, _("Probable")),
        (CONFIANCE_A_ARBITRER, _("À arbitrer")),
    ]

    # applique : nouveau type posé par le passage ;
    # a_actualiser : type vidé, en attente d'un choix ;
    # actualise : type choisi depuis, par `actualise_par`.
    STATUT_APPLIQUE = 'applique'
    STATUT_A_ACTUALISER = 'a_actualiser'
    STATUT_ACTUALISE = 'actualise'
    STATUTS = [
        (STATUT_APPLIQUE, _("Changé automatiquement")),
        (STATUT_A_ACTUALISER, _("À actualiser")),
        (STATUT_ACTUALISE, _("Actualisé")),
    ]

    id_passage_objet = models.AutoField(primary_key=True)
    passage = models.ForeignKey(PassageReferentielActions, on_delete=models.CASCADE,
                                related_name='objets')
    operation = models.ForeignKey('plans.Operation', on_delete=models.CASCADE,
                                  null=True, blank=True, related_name='passages_referentiel')
    suivi = models.ForeignKey('plans.SuiviInventaire', on_delete=models.CASCADE,
                              null=True, blank=True, related_name='passages_referentiel')
    # Plan de l'objet au moment du passage (destinataires, liste « à actualiser »).
    plan = models.ForeignKey('plans.PlanGestion', on_delete=models.SET_NULL,
                             null=True, blank=True, related_name='+')
    ancien_type = models.ForeignKey('core.Nomenclature', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='+')
    ancien_code = models.CharField(_("Ancien code"), max_length=50, blank=True, default='')
    ancien_libelle = models.CharField(_("Ancien libellé"), max_length=255, blank=True, default='')
    ancienne_categorie = models.ForeignKey('core.Nomenclature', on_delete=models.SET_NULL,
                                           null=True, blank=True, related_name='+')
    nouveau_type = models.ForeignKey('core.Nomenclature', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='+')
    nouvelle_categorie = models.ForeignKey('core.Nomenclature', on_delete=models.SET_NULL,
                                           null=True, blank=True, related_name='+')
    # Code proposé par la table, posé (sûre / probable) ou seulement suggéré.
    suggestion_code = models.CharField(_("Code proposé"), max_length=50, blank=True, default='')
    confiance = models.CharField(_("Confiance"), max_length=20, choices=CONFIANCES)
    note = models.TextField(_("Note"), blank=True, default='')
    statut = models.CharField(_("Statut"), max_length=20, choices=STATUTS)
    actualise_par = models.ForeignKey('users.Role', on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='+')
    actualise_le = models.DateTimeField(_("Actualisé le"), null=True, blank=True)
    type_choisi = models.ForeignKey('core.Nomenclature', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='+')

    class Meta:
        db_table = '"general"."t_referentiel_action_passage_objets"'
        db_table_comment = "Actions et suivis touchés par un passage de référentiel (#751)"
        indexes = [
            models.Index(fields=['operation', 'statut']),
            models.Index(fields=['passage', 'statut']),
        ]
        verbose_name = _("Objet d'un passage de référentiel")
        verbose_name_plural = _("Objets d'un passage de référentiel")
