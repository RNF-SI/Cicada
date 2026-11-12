"""Planification annuelle ajustée (#794) : modèle, règles et API.

Le plan de gestion reste la référence : un ajustement se superpose à une année
sans jamais modifier la programmation de l'action. Report total (décalage de
la suite, années suivies intouchables, rien au-delà de la fin du plan),
report partiel (reste à faire), revue, droits du suivi.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.plans.access import plan_operation_ids
from apps.plans.models_operations import (
    FinanceOperation, OperationAnnee, OperationAnneeRH, RealisationOperationAnnee,
)
from apps.plans.models_planification import AjustementAnnuel
from apps.plans.planification_annuelle import Planification
from apps.plans.services import PlanDuplicationService
from apps.plans.services_export_finance import build_action_finance, poste_entry_factory
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, MetriqueFactory, NiveauExigenceFactory,
    NomenclatureNiveauRealisationFactory, ObjectifLongTermeFactory, OperationFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import (
    CorOgSiteFactory, CorRoleSiteFactory, OrganismeFactory, RoleFactory, SiteFactory,
)
from tests.integrite.socle import construire_plan_complet, ecarts, inventaire

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

Y = date.today().year
BASE = '/api/plans/planification-annuelle'


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


class Monde:
    """Un plan validé (Y-1 → Y+3) et une action « aucune ventilation »
    programmée en Y (1 000 €, avril-mai, 5 j) et Y+1 (2 000 €, juin, 8 j)."""

    PROGRAMME = ((Y, '1000.00', ['4', '5'], '5'), (Y + 1, '2000.00', ['6'], '8'))

    def __init__(self, statut='valide', annee_fin=Y + 3, programme=PROGRAMME):
        self.organisme = OrganismeFactory()
        self.site = SiteFactory()
        CorOgSiteFactory(id_site=self.site, uuid_og=self.organisme, principal=True)
        self.referent = RoleFactory(id_organisme=self.organisme)
        self.plan = PlanGestionFactory(
            statut=statut, sites=[self.site], referents=[self.referent],
            annee_debut=Y - 1, annee_fin=annee_fin)
        enjeu = EnjeuFactory(id_pg=self.plan)
        ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=enjeu))
        metrique = MetriqueFactory(id_indicateur=IndicateurFactory(id_ne=ne))
        self.action = OperationFactory(
            metriques=[metrique], code_operation='AN-01', libelle='Fauche tardive',
            annee_min=Y - 1, annee_max=annee_fin, ventilation_mode='none',
            declinaison_par_type_cout=False)
        for annee, budget, mois, jours in programme:
            oa = OperationAnnee.objects.create(
                id_operation=self.action, annee=annee, periodicite=True,
                budget=Decimal(budget), periodicite_mensuelle={m: True for m in mois})
            OperationAnneeRH.objects.create(id_operation_annee=oa, jours=Decimal(jours))

    @property
    def client(self):
        return _client(self.referent)

    def url(self, annee, suite=''):
        return f'{BASE}/operation/{self.action.pk}/{annee}/{suite}'

    def tableau(self, annee, client=None):
        reponse = (client or self.client).get(f'{BASE}/plan/{self.plan.pk}/', {'annee': annee})
        assert reponse.status_code == 200, reponse.content[:300]
        return reponse.json()

    def ligne(self, annee):
        return self.tableau(annee)['actions'][0]

    def realiser(self, annee, niveau='TERMINE', **champs):
        oa, _ = OperationAnnee.objects.get_or_create(
            id_operation=self.action, annee=annee, defaults={'periodicite': False})
        return RealisationOperationAnnee.objects.create(
            id_operation_annee=oa,
            id_niveau_realisation=NomenclatureNiveauRealisationFactory(mnemonique=niveau),
            **champs)

    def reporter(self, annee, annee_report, **options):
        return self.client.post(self.url(annee, 'report/'),
                                {'annee_report': annee_report, **options}, format='json')


def _programmation():
    """Photographie de la programmation du plan (OperationAnnee & co)."""
    photo = inventaire()
    return {cle: valeur for cle, valeur in photo.items()
            if cle.startswith('plans.OperationAnnee')}


@pytest.fixture
def monde():
    return Monde()


class TestTableau:
    def test_sans_ajustement_l_annee_suit_le_plan(self, monde):
        tableau = monde.tableau(Y)
        assert (tableau['revues'], tableau['total']) == (0, 1)
        ligne = tableau['actions'][0]
        assert ligne['pg'] == ligne['ajuste']
        assert ligne['pg']['statut'] == 'planifiee'
        assert Decimal(ligne['pg']['budget']) == Decimal('1000')
        assert Decimal(ligne['pg']['jours']) == Decimal('5')
        assert ligne['pg']['mois'] == [4, 5]
        assert (ligne['ajustee'], ligne['diverge'], ligne['revue']) == (False, False, False)

    def test_annee_hors_programmation_non_prevue(self, monde):
        assert monde.ligne(Y + 2)['pg']['statut'] == 'non_prevue'

    def test_annee_hors_plan_refusee(self, monde):
        reponse = monde.client.get(f'{BASE}/plan/{monde.plan.pk}/', {'annee': Y + 9})
        assert reponse.status_code == 400

    def test_les_totaux_sont_ceux_des_exports(self):
        """Prévu du plan : même calcul que les exports (by_org_type_poste,
        coût salarial calculé) ; ajusté : mêmes règles sur l'ajustement."""
        pc = construire_plan_complet(statut='valide')
        af = build_action_finance(pc.action, {}, defaultdict(poste_entry_factory))
        lignes = _client(pc.referent).get(
            f'{BASE}/plan/{pc.plan.pk}/', {'annee': pc.annee + 1}).json()['actions']
        ligne = next(x for x in lignes if x['id_operation'] == pc.action.pk)
        assert Decimal(ligne['pg']['budget']) == af.year_total(pc.annee + 1).tot == Decimal('9000')
        # Ajusté : stage 4 500 € (organisme A) + 14 j × 250 €.
        assert Decimal(ligne['ajuste']['budget']) == Decimal('8000')
        assert ligne['ajuste']['mois'] == [4, 5]
        assert ligne['diverge'] is True
        globale = next(x for x in lignes if x['id_operation'] == pc.action_globale.pk)
        assert globale['programmation_globale'] is True
        assert globale['pg_global'] is not None


class TestAjustement:
    def test_enregistrer_marque_revue_sans_toucher_au_plan(self, monde):
        avant = _programmation()
        pg = monde.client.get(monde.url(Y)).json()['pg']
        reponse = monde.client.put(monde.url(Y), pg, format='json')
        assert reponse.status_code == 200, reponse.content[:300]
        assert reponse.json()['diverge'] is False
        assert not ecarts(avant, _programmation())
        tableau = monde.tableau(Y)
        assert (tableau['revues'], tableau['total']) == (1, 1)
        assert tableau['actions'][0]['revue'] is True

    def test_ajuster_les_moyens_et_les_mois(self, monde):
        pg = monde.client.get(monde.url(Y)).json()['pg']
        pg.update(budget='1500.00', periodicite_mensuelle={'9': True})
        pg['rh_lignes'] = [{'jours': '7.00'}]
        assert monde.client.put(monde.url(Y), pg, format='json').status_code == 200
        ligne = monde.ligne(Y)
        assert Decimal(ligne['pg']['budget']) == Decimal('1000')
        assert Decimal(ligne['ajuste']['budget']) == Decimal('1500')
        assert Decimal(ligne['ajuste']['jours']) == Decimal('7')
        assert ligne['ajuste']['mois'] == [9]
        assert ligne['diverge'] is True
        assert OperationAnnee.objects.get(id_operation=monde.action, annee=Y).budget == Decimal('1000')

    def test_une_annee_non_prevue_n_a_pas_de_moyens(self, monde):
        reponse = monde.client.put(
            monde.url(Y), {'statut': 'non_prevue', 'budget': '900.00',
                           'periodicite_mensuelle': {'3': True}}, format='json')
        assert reponse.status_code == 200
        resume = reponse.json()['effectif_resume']
        assert (resume['statut'], Decimal(resume['budget']), resume['mois']) == (
            'non_prevue', Decimal('0'), [])

    def test_planifier_une_annee_hors_programmation(self, monde):
        """Réalisation en avance : l'année est planifiée, rien d'autre ne bouge."""
        reponse = monde.client.put(
            monde.url(Y + 2), {'statut': 'planifiee', 'budget': '700.00'}, format='json')
        assert reponse.status_code == 200
        assert AjustementAnnuel.objects.filter(id_operation=monde.action).count() == 1
        assert monde.ligne(Y + 1)['ajustee'] is False

    def test_supprimer_revient_au_plan(self, monde):
        monde.client.put(monde.url(Y), {'statut': 'non_prevue'}, format='json')
        assert monde.client.delete(monde.url(Y)).status_code == 204
        assert monde.ligne(Y)['ajuste']['statut'] == 'planifiee'

    def test_le_report_passe_par_sa_route(self, monde):
        reponse = monde.client.put(monde.url(Y), {'statut': 'reportee'}, format='json')
        assert reponse.status_code == 400
        assert reponse.json()['code'] == 'report_par_la_route_dediee'

    def test_poste_ou_financeur_d_un_autre_plan_refuse(self, monde):
        autre = construire_plan_complet(statut='valide')
        poste = monde.client.put(monde.url(Y), {
            'statut': 'planifiee', 'rh_lignes': [{'id_poste': autre.poste.pk, 'jours': '1'}]},
            format='json')
        financeur = monde.client.put(monde.url(Y), {
            'statut': 'planifiee', 'financeurs': [{'id_financeur': autre.financeur.pk}]},
            format='json')
        assert (poste.status_code, financeur.status_code) == (400, 400)
        assert not AjustementAnnuel.objects.filter(id_operation=monde.action).exists()


class TestReportTotal:
    def test_l_apercu_decale_la_suite_sans_rien_ecrire(self, monde):
        reponse = monde.reporter(Y, Y + 1, apercu=True)
        assert reponse.status_code == 200, reponse.content[:300]
        apercu = reponse.json()
        assert apercu['applique'] is False
        assert apercu['deplacements'] == [{'de': Y, 'vers': Y + 1}, {'de': Y + 1, 'vers': Y + 2}]
        apres = {x['annee']: x['apres'] for x in apercu['annees']}
        assert (apres[Y]['statut'], apres[Y]['annee_report']) == ('reportee', Y + 1)
        assert (Decimal(apres[Y + 1]['budget']), apres[Y + 1]['report_de']) == (Decimal('1000'), Y)
        assert (Decimal(apres[Y + 2]['budget']), apres[Y + 2]['mois']) == (Decimal('2000'), [6])
        assert not AjustementAnnuel.objects.exists()

    def test_le_report_s_applique_et_ne_touche_pas_au_plan(self, monde):
        avant = _programmation()
        assert monde.reporter(Y, Y + 1).json()['applique'] is True
        assert not ecarts(avant, _programmation())
        assert monde.ligne(Y)['ajuste']['statut'] == 'reportee'
        assert monde.ligne(Y)['revue'] is True
        cible = monde.ligne(Y + 1)
        assert Decimal(cible['ajuste']['budget']) == Decimal('1000')
        assert cible['reports_entrants'] == [{'annee': Y, 'partiel': False}]
        assert cible['revue'] is False
        assert Decimal(monde.ligne(Y + 2)['ajuste']['budget']) == Decimal('2000')
        # Rejouer le même report ne décale pas une seconde fois.
        assert monde.reporter(Y, Y + 1).status_code == 409

    def test_rien_au_dela_de_la_fin_du_plan(self):
        monde = Monde(annee_fin=Y + 1)
        apercu = monde.reporter(Y, Y + 1, apercu=True).json()
        assert [a['annee'] for a in apercu['abandonnees']] == [Y + 1]
        assert monde.reporter(Y, Y + 2, apercu=True).status_code == 400

    def test_la_prolongation_compte(self):
        monde = Monde(annee_fin=Y + 1)
        monde.plan.annees_extension = 1
        monde.plan.save()
        apercu = monde.reporter(Y, Y + 1, apercu=True).json()
        assert apercu['abandonnees'] == []
        assert {'de': Y + 1, 'vers': Y + 2} in apercu['deplacements']

    def test_une_annee_suivie_ne_bouge_pas(self, monde):
        monde.realiser(Y + 2, budget_realise=Decimal('300'))
        apercu = monde.reporter(Y, Y + 1, apercu=True).json()
        assert apercu['deplacements'] == [{'de': Y, 'vers': Y + 1}, {'de': Y + 1, 'vers': Y + 3}]
        ligne = next(x for x in apercu['annees'] if x['annee'] == Y + 2)
        assert (ligne['fixe'], ligne['modifiee']) == (True, False)
        assert monde.reporter(Y, Y + 2, apercu=True).status_code == 409

    def test_le_niveau_reporte_ne_fige_pas_l_annee(self, monde):
        monde.realiser(Y + 1, niveau='REPORTE')
        planif = Planification(monde.plan, [monde.action])
        assert planif.annee_fixee(monde.action.pk, Y + 1) is False


class TestReportPartiel:
    def test_la_cible_recoit_le_reste_a_faire(self, monde):
        monde.realiser(Y, niveau='EN_COURS', budget_realise=Decimal('600'))
        reponse = monde.reporter(Y, Y + 1, partiel=True)
        assert reponse.status_code == 200, reponse.content[:300]
        assert reponse.json()['deplacements'] == []
        source = monde.ligne(Y)
        assert (source['ajuste']['statut'], source['ajuste']['annee_report']) == ('planifiee', Y + 1)
        cible = monde.ligne(Y + 1)
        # 2 000 € prévus en Y+1, plus 1 000 − 600 € restant de Y ; 8 + 5 j.
        assert Decimal(cible['ajuste']['budget']) == Decimal('2400')
        assert Decimal(cible['ajuste']['jours']) == Decimal('13')
        assert cible['reports_entrants'] == [{'annee': Y, 'partiel': True}]
        assert monde.ligne(Y + 2)['ajustee'] is False
        assert monde.reporter(Y, Y + 1, partiel=True).status_code == 409


class TestDroits:
    def test_lecture_pour_un_membre_du_site_saisie_refusee(self, monde):
        membre = RoleFactory(id_organisme=monde.organisme)
        CorRoleSiteFactory(id_role=membre, id_site=monde.site)
        client = _client(membre)
        assert client.get(f'{BASE}/plan/{monde.plan.pk}/', {'annee': Y}).json()['peut_saisir'] is False
        assert client.put(monde.url(Y), {'statut': 'non_prevue'}, format='json').status_code == 403
        assert client.post(monde.url(Y, 'report/'), {'annee_report': Y + 1},
                           format='json').status_code == 403

    def test_ni_redacteur_externe_ni_etranger(self, monde):
        redacteur = RoleFactory(role_level='redacteur')
        monde.plan.referents.add(redacteur)
        for user in (redacteur, RoleFactory()):
            client = _client(user)
            assert client.get(f'{BASE}/plan/{monde.plan.pk}/').status_code == 403
            assert client.get(monde.url(Y)).status_code == 403

    def test_un_brouillon_ne_s_ajuste_pas(self):
        monde = Monde(statut='draft')
        assert monde.client.get(monde.url(Y)).status_code == 200
        reponse = monde.client.put(monde.url(Y), {'statut': 'non_prevue'}, format='json')
        assert (reponse.status_code, reponse.json()['code']) == (409, 'plan_non_valide')


class TestGardeFous:
    def test_poste_et_financeur_utilises_ne_se_suppriment_pas(self):
        pc = construire_plan_complet(statut='valide')
        # Sans suivi ni programmation sur ce poste / financeur : seul l'ajustement les retient.
        RealisationOperationAnnee.objects.all().delete()
        pc.plan.statut = 'draft'
        pc.plan.save()
        OperationAnneeRH.objects.all().delete()
        FinanceOperation.objects.all().delete()
        client = _client(pc.referent)
        assert client.delete(f'/api/plans/postes/{pc.poste.pk}/').status_code == 409
        assert client.delete(f'/api/plans/financeurs/{pc.financeur.pk}/').status_code == 409

    def test_une_nouvelle_version_ne_reprend_pas_les_ajustements(self):
        pc = construire_plan_complet(statut='valide')
        nouveau = PlanDuplicationService.duplicate_plan(source_plan=pc.plan, user=pc.admin)
        copies = plan_operation_ids(nouveau)
        assert copies
        assert not AjustementAnnuel.objects.filter(id_operation__in=copies).exists()
        assert AjustementAnnuel.objects.filter(id_operation=pc.action).count() == 1
