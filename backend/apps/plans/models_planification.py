"""
Ajustement de la planification annuelle des actions (#794).

Le plan de gestion programme ses actions sur toute sa durée (``OperationAnnee``
et ses organismes / lignes de temps) : c'est la **référence**, figée à la
validation. Chaque année, le gestionnaire revoit chaque action et ajuste sa
programmation de l'année (moyens, mois, report…) sans toucher au plan.

Un ajustement est une **surcouche** : une ligne par action et par année, qui
porte les mêmes champs que la programmation du plan. Sans ligne, l'année suit
le plan de gestion. Les règles (prévu effectif, report, décalage) vivent dans
``apps/plans/planification_annuelle.py``.

Ces données relèvent du suivi : elles ne sortent jamais vers l'exploration ni
vers le hub, et ne sont pas copiées dans une nouvelle version du plan.
"""
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _

from .models_operations import Financeur, Operation, Poste, _RhLigneBase


class StatutAnnuel:
    """Statut de programmation d'une action pour une année (#794)."""
    PLANIFIEE = 'planifiee'
    NON_PREVUE = 'non_prevue'
    REPORTEE = 'reportee'
    CHOICES = [
        (PLANIFIEE, _("Planifiée")),
        (NON_PREVUE, _("Non prévue")),
        (REPORTEE, _("Reportée")),
    ]


def _montant(label):
    return models.DecimalField(label, max_digits=12, decimal_places=2, null=True, blank=True)


class _CoutsAjustes(models.Model):
    """Composants de coût et temps, mêmes noms que ``OperationAnneeOrganisme``
    (et donc que ``OperationAnnee``) : les règles de calcul du plan de gestion
    s'appliquent telles quelles au prévu ajusté."""

    budget_fonctionnement = _montant(_("Budget fonctionnement (€)"))
    budget_investissement = _montant(_("Budget investissement (€)"))
    cout_salarial = _montant(_("Coût salarial saisi — fonctionnement (€)"))
    cout_salarial_invest = _montant(_("Coût salarial saisi — investissement (€)"))
    cout_stage = _montant(_("Coût stage (€)"))
    cout_prestataire = _montant(_("Coût prestataire — fonctionnement (€)"))
    autre_cout = _montant(_("Autre coût — fonctionnement (€)"))
    autre_cout_commentaire = models.CharField(
        _("Commentaire autre coût — fonctionnement"), max_length=255, blank=True, default='')
    cout_prestataire_invest = _montant(_("Coût prestataire — investissement (€)"))
    autre_cout_invest = _montant(_("Autre coût — investissement (€)"))
    autre_cout_invest_commentaire = models.CharField(
        _("Commentaire autre coût — investissement"), max_length=255, blank=True, default='')
    etp = models.DecimalField(
        _("Travail prévisionnel (jours)"), max_digits=8, decimal_places=2, null=True, blank=True)

    class Meta:
        abstract = True


#: Champs de montant et de temps portés par une année (ajustement ou plan).
CHAMPS_COUTS_ORGANISME = (
    'budget_fonctionnement', 'budget_investissement', 'cout_salarial', 'cout_salarial_invest',
    'cout_stage', 'cout_prestataire', 'autre_cout', 'cout_prestataire_invest',
    'autre_cout_invest', 'etp',
)
CHAMPS_COUTS_ANNEE = ('budget',) + CHAMPS_COUTS_ORGANISME
CHAMPS_COMMENTAIRES_COUTS = ('autre_cout_commentaire', 'autre_cout_invest_commentaire')
#: Réglages de saisie propres à une année ajustée (null : ceux de l'action).
REGLAGES_ANNUELS = ('declinaison_par_type_cout', 'cout_salarial_auto', 'declinaison_par_poste')


class AjustementAnnuel(_CoutsAjustes):
    """
    Programmation ajustée d'une action pour une année (#794).

    - ``statut`` : planifiée, non prévue ou reportée l'année ``annee`` ;
    - ``annee_report`` : année vers laquelle l'action est reportée — en totalité
      (statut « reportée ») ou en partie (statut « planifiée », réalisation
      partielle finalisée plus tard) ;
    - ``report_de`` : année d'origine quand l'action reçoit un report ;
    - ``date_revue`` : l'action a été revue pour l'année (enregistrer
      l'ajustement, même sans rien changer, la marque revue).
    """

    id_ajustement_annuel = models.AutoField(primary_key=True)
    id_operation = models.ForeignKey(
        Operation, on_delete=models.CASCADE, related_name='ajustements_annuels',
        db_column='id_operation', verbose_name=_("Opération"))
    annee = models.IntegerField(_("Année"))
    statut = models.CharField(
        _("Statut de programmation"), max_length=20, choices=StatutAnnuel.CHOICES,
        default=StatutAnnuel.PLANIFIEE)
    annee_report = models.IntegerField(
        _("Reportée en"), null=True, blank=True,
        help_text=_("Année vers laquelle l'action est reportée (en totalité ou en partie)."))
    report_de = models.IntegerField(
        _("Reportée de"), null=True, blank=True,
        help_text=_("Année d'origine d'un report reçu."))
    budget = _montant(_("Budget prévisionnel (€)"))
    periodicite_mensuelle = models.JSONField(
        _("Mois de réalisation prévus"), default=dict, blank=True,
        help_text=_('Format: {"1": true, "2": false, ..., "12": true}'))
    commentaire = models.TextField(_("Commentaire de l'ajustement"), blank=True, default='')
    # Réglages de saisie de l'année, comme ceux du suivi (#741) : null = ceux
    # de l'action. Les déclinaisons du plan de gestion s'imposent ; l'année
    # peut en ajouter, et saisir son coût salarial plutôt que le calculer.
    declinaison_par_type_cout = models.BooleanField(
        _("Déclinaison par type de coût (année)"), null=True, blank=True)
    cout_salarial_auto = models.BooleanField(
        _("Coût salarial calculé automatiquement (année)"), null=True, blank=True)
    declinaison_par_poste = models.BooleanField(
        _("Déclinaison par type de poste (année)"), null=True, blank=True)
    date_revue = models.DateTimeField(_("Revue le"), null=True, blank=True)
    id_utilisateur_revue = models.ForeignKey(
        'users.Role', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        db_column='id_utilisateur_revue', verbose_name=_("Revue par"))
    date_ajout = models.DateTimeField(_("Date d'ajout"), auto_now_add=True)
    date_maj = models.DateTimeField(_("Date de modification"), auto_now=True)
    id_utilisateur_maj = models.ForeignKey(
        'users.Role', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
        db_column='id_utilisateur_maj', verbose_name=_("Dernier modificateur"))

    class Meta:
        db_table = '"general"."t_ajustements_annuels"'
        db_table_comment = "Planification annuelle ajustée d'une action (#794)"
        verbose_name = _("Ajustement annuel d'une action")
        verbose_name_plural = _("Ajustements annuels des actions")
        ordering = ['annee']
        constraints = [
            models.UniqueConstraint(
                fields=['id_operation', 'annee'], name='uniq_ajustement_annuel'),
        ]

    def __str__(self):
        return f"Ajustement {self.id_operation_id} - {self.annee}"

    def get_plan_de_gestion(self):
        return self.id_operation.get_plan_de_gestion() if self.id_operation_id else None


class AjustementAnnuelOrganisme(_CoutsAjustes):
    """Ventilation par organisme du prévu ajusté d'une année (#794)."""

    id_ajustement_annuel_organisme = models.AutoField(primary_key=True)
    id_ajustement_annuel = models.ForeignKey(
        AjustementAnnuel, on_delete=models.CASCADE, related_name='organismes',
        db_column='id_ajustement_annuel')
    id_organisme = models.ForeignKey(
        'users.BibOrganismes',
        on_delete=models.PROTECT,  # supprimer l'organisme effacerait sa ventilation ajustée
        related_name='ajustements_annuels', db_column='id_organisme',
        verbose_name=_("Organisme"))

    class Meta:
        db_table = '"general"."t_ajustement_annuel_organismes"'
        db_table_comment = "Ventilation par organisme d'un ajustement annuel (#794)"
        ordering = ['id_organisme__nom_organisme']
        constraints = [
            models.UniqueConstraint(
                fields=['id_ajustement_annuel', 'id_organisme'],
                name='uniq_ajustement_annuel_organisme'),
        ]

    def get_plan_de_gestion(self):
        return (self.id_ajustement_annuel.get_plan_de_gestion()
                if self.id_ajustement_annuel_id else None)


class AjustementAnnuelRH(_RhLigneBase):
    """Ligne de temps de travail du prévu ajusté d'une année (#794), même cible
    que ``OperationAnneeRH`` (poste, organisme ou temps global)."""

    id_ajustement_annuel_rh = models.AutoField(primary_key=True)
    id_ajustement_annuel = models.ForeignKey(
        AjustementAnnuel, on_delete=models.CASCADE, related_name='rh_lignes',
        db_column='id_ajustement_annuel')
    id_poste = models.ForeignKey(
        Poste, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rh_lignes_ajustees', db_column='id_poste', verbose_name=_("Poste"))
    id_organisme = models.ForeignKey(
        'users.BibOrganismes', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='rh_lignes_ajustees', db_column='id_organisme',
        verbose_name=_("Organisme"))
    jours = models.DecimalField(
        _("Nombre de jours"), max_digits=8, decimal_places=2, null=True, blank=True)
    finance = models.BooleanField(_("Financé"), default=True)

    class Meta:
        db_table = '"general"."t_ajustement_annuel_rh"'
        db_table_comment = "Lignes de temps d'un ajustement annuel (#794)"
        ordering = ['id_ajustement_annuel_rh']

    def get_plan_de_gestion(self):
        return (self.id_ajustement_annuel.get_plan_de_gestion()
                if self.id_ajustement_annuel_id else None)


class AjustementAnnuelFinanceur(models.Model):
    """Montant prévu d'un financeur pour l'année ajustée (#794). Le plan de
    gestion ne prévoit qu'un montant global sur l'action (#790)."""

    id_ajustement_annuel_financeur = models.AutoField(primary_key=True)
    id_ajustement_annuel = models.ForeignKey(
        AjustementAnnuel, on_delete=models.CASCADE, related_name='financeurs',
        db_column='id_ajustement_annuel')
    id_financeur = models.ForeignKey(
        Financeur, on_delete=models.CASCADE, related_name='ajustements_annuels',
        db_column='id_financeur')
    montant = _montant(_("Montant prévu (€)"))

    class Meta:
        db_table = '"general"."t_ajustement_annuel_financeurs"'
        db_table_comment = "Montants prévus par financeur d'un ajustement annuel (#794)"
        ordering = ['id_ajustement_annuel_financeur']
        constraints = [
            models.UniqueConstraint(
                fields=['id_ajustement_annuel', 'id_financeur'],
                name='uniq_ajustement_annuel_financeur'),
        ]

    def get_plan_de_gestion(self):
        return self.id_financeur.id_pg if self.id_financeur_id else None
