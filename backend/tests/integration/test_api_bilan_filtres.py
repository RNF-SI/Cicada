"""
#753 — filtres et repères du Bilan.

- filtre Enjeux / FCR à choix multiple, qui suit les deux branches
  (NE → OLT → enjeu, RA → OO → FCR) ; la répartition par enjeu ne montre que
  les enjeux choisis ;
- liste stable des enjeux du plan, numérotés « Enjeu n » / « FCR n » ;
- filtre Organismes : actions ventilées à l'organisme, budget de sa seule part ;
- filtre Type d'indicateur (État / Pression), indicateurs de pression compris.
"""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework import status

from apps.core.models import Nomenclature, TypeNomenclature
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, MesureFactory, MetriqueFactory,
    NiveauExigenceFactory, NomenclatureNiveauRealisationFactory,
    ObjectifLongTermeFactory, ObjectifOperationnelFactory, OperationAnneeFactory,
    OperationAnneeOrganismeFactory, OperationFactory, RealisationOperationAnneeFactory,
    ResultatAttenduFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import OrganismeFactory, SuperAdminFactory


def _nomenclature(type_mnemo, mnemo, label=None):
    t, _ = TypeNomenclature.objects.get_or_create(mnemonique=type_mnemo,
                                                  defaults={'label': type_mnemo})
    n, _ = Nomenclature.objects.get_or_create(
        id_type=t, mnemonique=mnemo,
        defaults={'cd_nomenclature': mnemo[:10], 'label': label or mnemo})
    return n


@pytest.fixture
def plan_bilan(db):
    """Deux enjeux (branche état) et un FCR (branche pression / OO), une action
    sur chacun ; l'action A est partagée entre les enjeux 1 et 2. Actions A et B
    ventilées à deux organismes, l'action FCR à aucun."""
    plan = PlanGestionFactory(annee_debut=2024, annee_fin=2025, statut='valide')
    cat_enjeu = _nomenclature('CATEGORIE_ENJEU', 'ENJEU', 'Enjeu')
    cat_fcr = _nomenclature('CATEGORIE_ENJEU', 'FCR', 'FCR')
    etat = _nomenclature('TYPE_INDICATEUR', 'ETAT', 'État')
    press = _nomenclature('TYPE_INDICATEUR', 'PRESSION', 'Pression')
    numerique = _nomenclature('TYPE_METRIQUE', 'NUMERIQUE')
    termine = NomenclatureNiveauRealisationFactory(mnemonique='TERMINE')

    def enjeu_etat(libelle, ordre):
        e = EnjeuFactory(id_pg=plan, id_categorie=cat_enjeu, libelle=libelle, ordre=ordre)
        ind = IndicateurFactory(id_ne=NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=e)),
                                type_indicateur=etat, nom_indicateur=f'État {libelle}')
        met = MetriqueFactory(id_indicateur=ind, type_metrique=numerique,
                              score_1_sup=10, score_5_inf=90)
        MesureFactory(id_metrique=met, valeur='95', date_mesure=date(2024, 6, 1))
        return e, met

    e1, met1 = enjeu_etat('Prairies', 0)
    e2, met2 = enjeu_etat('Tourbières', 1)
    fcr = EnjeuFactory(id_pg=plan, id_categorie=cat_fcr, libelle='Gouvernance', ordre=0)
    ind_press = IndicateurFactory(
        id_ne=None, type_indicateur=press, nom_indicateur='Pression gouvernance',
        id_resultat_attendu=ResultatAttenduFactory(id_oo=ObjectifOperationnelFactory(id_enjeu=fcr)))
    met_fcr = MetriqueFactory(id_indicateur=ind_press, type_metrique=numerique,
                              score_1_sup=10, score_5_inf=90)
    MesureFactory(id_metrique=met_fcr, valeur='5', date_mesure=date(2024, 6, 1))

    org_a, org_b = OrganismeFactory(nom_organisme='RNF'), OrganismeFactory(nom_organisme='OFB')

    def action(code, metriques, ventilation):
        op = OperationFactory(code_operation=code, metriques=metriques,
                              ventilation_mode='by_org' if ventilation else 'none',
                              annee_min=2024, annee_max=2024)
        oa = OperationAnneeFactory(id_operation=op, annee=2024, periodicite=True,
                                   budget=Decimal('0') if ventilation else Decimal('700'))
        for org, montant in ventilation:
            OperationAnneeOrganismeFactory(id_operation_annee=oa, id_organisme=org,
                                           budget_fonctionnement=Decimal(montant),
                                           budget_investissement=Decimal('0'))
        RealisationOperationAnneeFactory(id_operation_annee=oa, id_niveau_realisation=termine)
        return op

    action('A', [met1, met2], [(org_a, '1000'), (org_b, '500')])
    action('B', [met2], [(org_b, '300')])
    action('F', [met_fcr], [])
    return {'plan': plan, 'e1': e1, 'e2': e2, 'fcr': fcr, 'org_a': org_a, 'org_b': org_b}


@pytest.fixture
def client(api_client):
    api_client.force_authenticate(user=SuperAdminFactory())
    return api_client


def _bilan(client, plan, **params):
    r = client.get(f'/api/plans/realisations/bilan/{plan.pk}/', params)
    assert r.status_code == status.HTTP_200_OK, r.content
    return r.data


@pytest.mark.django_db
class TestEnjeux:
    def test_liste_stable_numerotee(self, client, plan_bilan):
        d = _bilan(client, plan_bilan['plan'], enjeu_id=plan_bilan['e1'].pk)
        codes = {e['enjeu_id']: e['code'] for e in d['enjeux']}
        assert codes == {plan_bilan['e1'].pk: 'Enjeu 1', plan_bilan['e2'].pk: 'Enjeu 2',
                         plan_bilan['fcr'].pk: 'FCR 1'}

    def test_par_enjeu_porte_le_code_et_compte_le_fcr(self, client, plan_bilan):
        d = _bilan(client, plan_bilan['plan'])
        par = {e['code']: e['total'] for e in d['by_enjeu']}
        # A compte pour les enjeux 1 et 2, B pour le 2, F pour le FCR (branche OO).
        assert par == {'Enjeu 1': 1, 'Enjeu 2': 2, 'FCR 1': 1}

    def test_filtre_un_enjeu_ne_montre_que_lui(self, client, plan_bilan):
        d = _bilan(client, plan_bilan['plan'], enjeu_id=plan_bilan['e1'].pk)
        assert [e['code'] for e in d['by_enjeu']] == ['Enjeu 1']
        assert d['taux_realisation']['total'] == 1

    def test_filtre_plusieurs_enjeux(self, client, plan_bilan):
        p = plan_bilan
        d = _bilan(client, p['plan'], enjeu_id=f"{p['e1'].pk},{p['fcr'].pk}")
        assert sorted(e['code'] for e in d['by_enjeu']) == ['Enjeu 1', 'FCR 1']
        assert d['taux_realisation']['total'] == 2   # A et F


@pytest.mark.django_db
class TestOrganismes:
    def test_liste_des_organismes(self, client, plan_bilan):
        d = _bilan(client, plan_bilan['plan'])
        assert [o['nom'] for o in d['organismes']] == ['OFB', 'RNF']

    def test_filtre_un_organisme(self, client, plan_bilan):
        d = _bilan(client, plan_bilan['plan'], organisme_id=plan_bilan['org_a'].pk)
        assert d['taux_realisation']['total'] == 1           # seule l'action A
        assert d['budget']['total']['previsionnel'] == 1000.0  # sa part de A

    def test_filtre_deux_organismes(self, client, plan_bilan):
        p = plan_bilan
        d = _bilan(client, p['plan'], organisme_id=f"{p['org_a'].pk},{p['org_b'].pk}")
        assert d['taux_realisation']['total'] == 2
        assert d['budget']['total']['previsionnel'] == 1800.0


@pytest.mark.django_db
class TestIndicateurs:
    def _indic(self, client, plan, **params):
        r = client.get(f'/api/plans/realisations/bilan-indicateurs/{plan.pk}/', params)
        assert r.status_code == status.HTTP_200_OK, r.content
        return r.data

    def test_etat_et_pression_par_defaut(self, client, plan_bilan):
        d = self._indic(client, plan_bilan['plan'])
        assert d['total_indicateurs'] == 3
        assert {e['code'] for e in d['by_enjeu']} == {'Enjeu 1', 'Enjeu 2', 'FCR 1'}

    def test_type_etat_seul(self, client, plan_bilan):
        d = self._indic(client, plan_bilan['plan'], types='ETAT')
        assert d['total_indicateurs'] == 2
        assert 'FCR 1' not in {e['code'] for e in d['by_enjeu']}

    def test_type_pression_et_enjeux_multiples(self, client, plan_bilan):
        p = plan_bilan
        d = self._indic(client, p['plan'], types='PRESSION',
                        enjeu_id=f"{p['e1'].pk},{p['fcr'].pk}")
        assert d['total_indicateurs'] == 1
        assert [e['code'] for e in d['by_enjeu']] == ['FCR 1']

    def test_series_suivent_les_filtres(self, client, plan_bilan):
        p = plan_bilan
        r = client.get(f'/api/plans/realisations/bilan-series/{p["plan"].pk}/',
                       {'types': 'PRESSION'})
        assert r.status_code == status.HTTP_200_OK
        # Seule la mesure de pression (5 → score 1) en 2024.
        assert r.data['indicateurs_evolution']['mean'][0] == 1.0
