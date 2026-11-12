"""Socle du filet « perte de données » : un plan complet et son inventaire.

``construire_plan_complet()`` crée un plan qui contient **un exemplaire de chaque
donnée saisie** : programmation annuelle et globale ventilée par organisme et
par poste, suivi saisi sur deux années (organismes, temps, financeurs,
commentaires), planification annuelle ajustée (#794), financeurs, mesures,
suivi-inventaire et protocoles, document.

``inventaire()`` photographie toutes les lignes des applications métier. Deux
inventaires égaux garantissent qu'aucune ligne n'a disparu et qu'aucune valeur
saisie n'a changé. La clé primaire de chaque ligne est ignorée (une liaison
recréée à l'identique ne perd rien), mais une ligne recréée fait disparaître ce
qui la référençait : c'est ce que l'inventaire voit.
"""
from collections import Counter
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.apps import apps

from apps.plans.models_operations import (
    Financeur, FinanceOperation, OperationAnnee, OperationAnneeOrganisme, OperationAnneeRH,
    Poste, RealisationFinanceur, RealisationOperationAnnee, RealisationOperationAnneeOrganisme,
    RealisationOperationAnneeRH,
)
from apps.plans.models_planification import (
    AjustementAnnuel, AjustementAnnuelFinanceur, AjustementAnnuelOrganisme, AjustementAnnuelRH,
)
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, MesureFactory, MetriqueFactory, NiveauExigenceFactory,
    NomenclatureNiveauRealisationFactory, ObjectifLongTermeFactory, OperationFactory,
    ProtocoleFactory, SuiviInventaireFactory,
)
from tests.factories.plans import CorPgFichierFactory, PlanGestionFactory
from tests.factories.users import OrganismeFactory, RoleFactory, SiteFactory, SuperAdminFactory

# Applications dont les lignes forment « les données » d'une instance.
APPLICATIONS_METIER = ('plans', 'users', 'core')

# Journaux et traces : ils grossissent légitimement à chaque écriture.
MODELES_HORS_INVENTAIRE = {
    'core.activitylog', 'core.errorlog', 'users.impersonationlog',
}

# Champs qui changent légitimement à chaque enregistrement.
CHAMPS_VOLATILS = {
    'date_maj', 'id_utilisateur_maj', 'date_modification', 'updated_at',
    'derniere_activite', 'last_login', 'actualise_le', 'actualise_par',
    # Copie à l'écriture (protocoles d'un suivi) : la copie a pour auteur celui
    # qui enregistre ; le contenu, lui, est comparé.
    'id_utilisateur_ajout',
}


def _modeles():
    for label in APPLICATIONS_METIER:
        for modele in apps.get_app_config(label).get_models():
            if modele._meta.label_lower in MODELES_HORS_INVENTAIRE:
                continue
            if modele._meta.proxy or not modele._meta.managed:
                continue
            yield modele


def _champs_stables(modele):
    for champ in modele._meta.concrete_fields:
        if champ.primary_key or champ.name in CHAMPS_VOLATILS:
            continue
        if getattr(champ, 'auto_now', False) or getattr(champ, 'auto_now_add', False):
            continue
        yield champ


def inventaire():
    """{modèle: Counter(lignes)} pour toutes les données métier de la base."""
    photo = {}
    for modele in _modeles():
        champs = [c.attname for c in _champs_stables(modele)]
        gestionnaire = modele._base_manager
        lignes = gestionnaire.values_list(*champs) if champs else gestionnaire.values_list('pk')
        photo[modele._meta.label] = Counter(
            tuple(str(v) for v in ligne) for ligne in lignes)
    return photo


def ecarts(avant, apres):
    """Différences lisibles entre deux inventaires (vide si identiques)."""
    messages = []
    for modele in sorted(set(avant) | set(apres)):
        a, b = avant.get(modele, Counter()), apres.get(modele, Counter())
        if a == b:
            continue
        perdues, ajoutees = a - b, b - a
        messages.append(
            f"{modele} : {sum(a.values())} → {sum(b.values())} lignes, "
            f"{sum(perdues.values())} perdue(s) ou modifiée(s), {sum(ajoutees.values())} nouvelle(s)"
            + (f" ; ex. perdue {next(iter(perdues))}" if perdues else "")
            + (f" ; ex. nouvelle {next(iter(ajoutees))}" if ajoutees else ""))
    return messages


def _metrique(plan):
    enjeu = EnjeuFactory(id_pg=plan)
    ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=enjeu))
    return MetriqueFactory(id_indicateur=IndicateurFactory(id_ne=ne))


def construire_plan_complet(statut='draft'):
    """Un plan avec un exemplaire de chaque donnée saisie (voir le module)."""
    annee = date.today().year
    org_a = OrganismeFactory(nom_organisme='Organisme A')
    org_b = OrganismeFactory(nom_organisme='Organisme B')
    site = SiteFactory()
    referent = RoleFactory(id_organisme=org_a)
    plan = PlanGestionFactory(
        statut=statut, sites=[site], referents=[referent],
        annee_debut=annee - 2, annee_fin=annee + 3)
    metrique = _metrique(plan)
    MesureFactory(id_metrique=metrique, valeur='112', date_mesure=date(annee - 1, 6, 1))
    MesureFactory(id_metrique=metrique, valeur='116', date_mesure=date(annee, 6, 1))
    poste = Poste.objects.create(
        id_pg=plan, id_organisme=org_a, nom_local='Garde technicien', nombre=1,
        cout_jour=Decimal('250.00'))
    financeur = Financeur.objects.create(id_pg=plan, nom='Agence de l’eau')
    termine = NomenclatureNiveauRealisationFactory(mnemonique='TERMINE')

    suivi = SuiviInventaireFactory(intitule='Suivi des prairies')
    suivi.protocoles.add(
        ProtocoleFactory(nom_protocole='Transects'), ProtocoleFactory(nom_protocole='Quadrats'))

    def _action(code, globale=False):
        action = OperationFactory(
            metriques=[metrique], code_operation=code, libelle=f'Action {code}',
            annee_min=annee - 1, annee_max=annee + 1,
            ventilation_mode='by_org_type_poste', declinaison_par_poste=True,
            declinaison_par_type_cout=True, programmation_globale=globale,
            id_suivi=None if globale else suivi)
        FinanceOperation.objects.create(
            id_operation=action, id_financeur=financeur, libelle=financeur.nom,
            montant=Decimal('6000.00'))
        lignes = [annee - 1, annee, annee + 1] + ([None] if globale else [])
        for an in lignes:
            oa = OperationAnnee.tous.create(
                id_operation=action, annee=an, periodicite=an is not None,
                budget=None if (globale and an is not None) else Decimal('10000.00'))
            for org, montant in ((org_a, '4000.00'), (org_b, '2000.00')):
                OperationAnneeOrganisme.objects.create(
                    id_operation_annee=oa, id_organisme=org,
                    cout_stage=None if (globale and an is not None) else Decimal(montant),
                    autre_cout_commentaire='Frais de déplacement')
            rh = OperationAnneeRH.objects.create(
                id_operation_annee=oa, id_poste=poste, jours=Decimal('12.00'))
            if an is not None and an < annee + 1:
                real = RealisationOperationAnnee.objects.create(
                    id_operation_annee=oa, id_niveau_realisation=termine,
                    periodicite_realisee=True, commentaires=f'Suivi {code} {an}',
                    budget_realise=Decimal('9000.00'), etp_realise=Decimal('10.00'))
                for org_oa in oa.organismes.all():
                    RealisationOperationAnneeOrganisme.objects.create(
                        id_operation_annee_organisme=org_oa,
                        budget_fonctionnement_realise=Decimal('1500.00'),
                        etp_realise=Decimal('5.00'))
                RealisationOperationAnneeRH.objects.create(
                    id_realisation_operation_annee=real, id_operation_annee_rh=rh,
                    id_poste=poste, jours=Decimal('11.00'))
                RealisationFinanceur.objects.create(
                    id_realisation_operation_annee=real, id_financeur=financeur,
                    montant=Decimal('3000.00'))
        return action

    action = _action('PC-01')
    action_globale = _action('PC-02', globale=True)
    # #794 — planification annuelle ajustée : l'année qui suit, sans suivi.
    ajustement = AjustementAnnuel.objects.create(
        id_operation=action, annee=annee + 1, statut='planifiee',
        periodicite_mensuelle={'4': True, '5': True}, budget=Decimal('11000.00'),
        commentaire='Coûts réévalués')
    AjustementAnnuelOrganisme.objects.create(
        id_ajustement_annuel=ajustement, id_organisme=org_a, cout_stage=Decimal('4500.00'),
        autre_cout_commentaire='Frais de déplacement')
    AjustementAnnuelRH.objects.create(
        id_ajustement_annuel=ajustement, id_poste=poste, jours=Decimal('14.00'))
    AjustementAnnuelFinanceur.objects.create(
        id_ajustement_annuel=ajustement, id_financeur=financeur, montant=Decimal('2500.00'))
    document = CorPgFichierFactory(plan_de_gestion=plan)
    return SimpleNamespace(
        plan=plan, site=site, referent=referent, org_a=org_a, org_b=org_b, poste=poste,
        financeur=financeur, metrique=metrique, suivi=suivi, action=action,
        action_globale=action_globale, ajustement=ajustement, document=document,
        admin=SuperAdminFactory(),
        annee=annee)
