"""Serializers de la planification annuelle ajustée (#794).

Un « contenu » (voir ``apps/plans/planification_annuelle.py``) a la forme de
la programmation d'une année du plan : mêmes champs que ``OperationAnnee``,
organismes et lignes de temps, plus le statut, les mois et les financeurs.
"""
from rest_framework import serializers

from .models_operations import CategorieDepense
from .models_planification import StatutAnnuel


def _montant():
    return serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, min_value=0)


def _jours():
    return serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True, min_value=0)


def _commentaire():
    return serializers.CharField(required=False, allow_blank=True, max_length=255, default='')


class _CoutsSerializer(serializers.Serializer):
    budget_fonctionnement = _montant()
    budget_investissement = _montant()
    cout_salarial = _montant()
    cout_salarial_invest = _montant()
    cout_stage = _montant()
    cout_prestataire = _montant()
    autre_cout = _montant()
    autre_cout_commentaire = _commentaire()
    cout_prestataire_invest = _montant()
    autre_cout_invest = _montant()
    autre_cout_invest_commentaire = _commentaire()
    etp = _jours()


class OrganismeAjusteSerializer(_CoutsSerializer):
    id_organisme = serializers.IntegerField()


class RhAjusteSerializer(serializers.Serializer):
    id_poste = serializers.IntegerField(required=False, allow_null=True)
    id_organisme = serializers.IntegerField(required=False, allow_null=True)
    jours = _jours()
    finance = serializers.BooleanField(required=False, default=True)
    categorie_depense = serializers.ChoiceField(
        choices=CategorieDepense.CHOICES, required=False, allow_blank=True, default='')


class FinanceurAjusteSerializer(serializers.Serializer):
    id_financeur = serializers.IntegerField()
    montant = _montant()


class ContenuAnnuelSerializer(_CoutsSerializer):
    """Programmation d'une année : plan de gestion, ajustement ou prévu effectif.

    En écriture (``PUT``), ``statut`` vaut « planifiée » ou « non prévue » : un
    report passe par la route ``report/``. ``annee_report`` / ``report_de`` sont
    posés par le report et rendus en lecture."""
    statut = serializers.ChoiceField(choices=StatutAnnuel.CHOICES)
    annee_report = serializers.IntegerField(read_only=True, allow_null=True)
    report_de = serializers.IntegerField(read_only=True, allow_null=True)
    budget = _montant()
    periodicite_mensuelle = serializers.DictField(
        child=serializers.BooleanField(), required=False, default=dict,
        help_text='Mois de réalisation prévus : {"1": true, …, "12": true}.')
    commentaire = serializers.CharField(required=False, allow_blank=True, default='')
    organismes = OrganismeAjusteSerializer(many=True, required=False, default=list)
    rh_lignes = RhAjusteSerializer(many=True, required=False, default=list)
    financeurs = FinanceurAjusteSerializer(many=True, required=False, default=list)

    def validate_periodicite_mensuelle(self, valeur):
        inconnus = sorted(set(valeur) - {str(m) for m in range(1, 13)})
        if inconnus:
            raise serializers.ValidationError(f"Mois inconnus : {', '.join(inconnus)}.")
        return valeur


class ResumeAnnuelSerializer(serializers.Serializer):
    """Totaux d'un contenu, calculés par les règles des exports."""
    statut = serializers.ChoiceField(choices=StatutAnnuel.CHOICES)
    annee_report = serializers.IntegerField(allow_null=True)
    report_de = serializers.IntegerField(allow_null=True)
    mois = serializers.ListField(child=serializers.IntegerField())
    budget = serializers.DecimalField(max_digits=14, decimal_places=2)
    budget_fonctionnement = serializers.DecimalField(max_digits=14, decimal_places=2)
    budget_investissement = serializers.DecimalField(max_digits=14, decimal_places=2)
    jours = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Bénévolat compris.")
    jours_benevole = serializers.DecimalField(max_digits=10, decimal_places=2)
    financeurs = serializers.DecimalField(
        max_digits=14, decimal_places=2, help_text="Somme des montants annuels par financeur.")


class ReportEntrantSerializer(serializers.Serializer):
    annee = serializers.IntegerField(help_text="Année d'origine du report.")
    partiel = serializers.BooleanField()


class RealiseAnnuelSerializer(serializers.Serializer):
    saisi = serializers.BooleanField()
    niveau = serializers.CharField(allow_null=True, help_text="Mnémonique NIVEAU_REALISATION.")


class LigneTableauSerializer(serializers.Serializer):
    id_operation = serializers.IntegerField()
    code = serializers.CharField(allow_blank=True)
    libelle = serializers.CharField(allow_blank=True)
    programmation_globale = serializers.BooleanField()
    pg = ResumeAnnuelSerializer(help_text="Programmation du plan de gestion pour l'année.")
    pg_global = ResumeAnnuelSerializer(
        allow_null=True, help_text="Programmation globale (#735) : montants sur la période.")
    ajuste = ResumeAnnuelSerializer(help_text="Prévu effectif : l'ajustement, sinon le plan.")
    ajustee = serializers.BooleanField(help_text="Un ajustement est enregistré pour l'année.")
    diverge = serializers.BooleanField(help_text="L'ajustement s'écarte du plan de gestion.")
    revue = serializers.BooleanField()
    date_revue = serializers.DateTimeField(allow_null=True)
    reports_entrants = ReportEntrantSerializer(many=True)
    realise = RealiseAnnuelSerializer()


class TableauAnnuelSerializer(serializers.Serializer):
    id_pg = serializers.IntegerField()
    annee = serializers.IntegerField()
    annees = serializers.ListField(child=serializers.IntegerField())
    revues = serializers.IntegerField(help_text="Actions revues pour l'année.")
    total = serializers.IntegerField(help_text="Actions du plan.")
    peut_saisir = serializers.BooleanField()
    actions = LigneTableauSerializer(many=True)


class FinanceurPgSerializer(serializers.Serializer):
    id_financeur = serializers.IntegerField(allow_null=True)
    nom = serializers.CharField(allow_blank=True)
    montant = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True, help_text="Montant global sur l'action.")


class ReglagesActionSerializer(serializers.Serializer):
    ventilation_mode = serializers.CharField()
    declinaison_par_poste = serializers.BooleanField()
    declinaison_par_type_cout = serializers.BooleanField()
    cout_salarial_auto = serializers.BooleanField()
    programmation_globale = serializers.BooleanField()
    temps_par_poste = serializers.BooleanField()


class AjustementLuSerializer(ContenuAnnuelSerializer):
    id_ajustement_annuel = serializers.IntegerField()
    date_revue = serializers.DateTimeField(allow_null=True)
    revue_par = serializers.CharField(allow_null=True)
    date_maj = serializers.DateTimeField()


class DetailAnnuelSerializer(serializers.Serializer):
    id_operation = serializers.IntegerField()
    code = serializers.CharField(allow_blank=True)
    libelle = serializers.CharField(allow_blank=True)
    annee = serializers.IntegerField()
    annees = serializers.ListField(child=serializers.IntegerField())
    reglages = ReglagesActionSerializer()
    pg = ContenuAnnuelSerializer()
    pg_resume = ResumeAnnuelSerializer()
    pg_global = ContenuAnnuelSerializer(allow_null=True)
    pg_global_resume = ResumeAnnuelSerializer(allow_null=True)
    financeurs_pg = FinanceurPgSerializer(many=True)
    ajustement = AjustementLuSerializer(allow_null=True)
    effectif = ContenuAnnuelSerializer()
    effectif_resume = ResumeAnnuelSerializer()
    diverge = serializers.BooleanField()
    reports_entrants = ReportEntrantSerializer(many=True)
    realise = RealiseAnnuelSerializer()
    fixe = serializers.BooleanField(help_text="Du réalisé est saisi : l'année ne se déplace pas.")
    peut_saisir = serializers.BooleanField()


class ReportDemandeSerializer(serializers.Serializer):
    annee_report = serializers.IntegerField()
    partiel = serializers.BooleanField(
        required=False, default=False,
        help_text="Report partiel : l'année reste planifiée, la cible reçoit le reste à faire.")
    apercu = serializers.BooleanField(
        required=False, default=False, help_text="Rendre l'avant / après sans rien écrire.")


class LigneApercuSerializer(serializers.Serializer):
    annee = serializers.IntegerField()
    avant = ResumeAnnuelSerializer()
    apres = ResumeAnnuelSerializer()
    fixe = serializers.BooleanField(help_text="Réalisé saisi ou déjà reportée : ne bouge pas.")
    modifiee = serializers.BooleanField()


class DeplacementSerializer(serializers.Serializer):
    de = serializers.IntegerField()
    vers = serializers.IntegerField()


class AbandonSerializer(serializers.Serializer):
    annee = serializers.IntegerField()
    resume = ResumeAnnuelSerializer()


class ApercuReportSerializer(serializers.Serializer):
    annee = serializers.IntegerField()
    annee_report = serializers.IntegerField()
    partiel = serializers.BooleanField()
    applique = serializers.BooleanField()
    annees = LigneApercuSerializer(many=True)
    deplacements = DeplacementSerializer(many=True)
    abandonnees = AbandonSerializer(
        many=True, help_text="Programmation qui tomberait après la fin du plan : abandonnée.")
