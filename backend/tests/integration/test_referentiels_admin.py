"""
#777 — page super-admin « Référentiels » : état des versions, simulation,
application, annulation ; réservée au super-admin.
"""
import pytest

from apps.plans import referentiel_actions as ra
from tests.factories.users import AdminOrganismeFactory, SuperAdminFactory
from tests.integration.test_referentiel_types_action import (  # noqa: F401 — fixtures
    plans, referentiel,
)


@pytest.mark.django_db
class TestPageReferentiels:
    def test_reservee_au_super_admin(self, api_client, referentiel):
        api_client.force_authenticate(user=AdminOrganismeFactory())
        assert api_client.get('/api/plans/referentiels/admin/').status_code == 403

    def test_etat_simuler_appliquer_annuler(self, api_client, referentiel, plans):
        api_client.force_authenticate(user=SuperAdminFactory())
        etat = {r['code']: r for r in api_client.get('/api/plans/referentiels/admin/').data['referentiels']}
        assert set(etat) == {'TYPE_ACTION', 'PRESSREF', 'TAXREF', 'HABREF'}
        ta = etat['TYPE_ACTION']
        assert ta['en_service']['code'] == 'EDEN62'
        assert ta['versions'] == [{'nom': 'test_v1', 'code': 'TEST_V1', 'libelle': 'Test V1',
                                   'depuis': 'EDEN62', 'applicable': True, 'en_service': False}]
        assert ta['passage'] is None

        base = '/api/plans/referentiels/admin/TYPE_ACTION'
        r = api_client.post(f'{base}/simuler/', {'version': 'test_v1'}, format='json')
        assert r.status_code == 200 and r.data['rapport']['actions']['a_arbitrer'] == 3

        r = api_client.post(f'{base}/appliquer/', {'version': 'test_v1', 'sans_email': True}, format='json')
        assert r.status_code == 200, r.content
        ta = {x['code']: x for x in r.data['referentiels']}['TYPE_ACTION']
        assert ta['en_service']['code'] == 'TEST_V1'
        assert ta['passage']['a_actualiser'] == 3 and ta['passage']['automatiques'] == 3

        # Une version qui ne part pas de la version en service est refusée, lisiblement.
        r = api_client.post(f'{base}/appliquer/', {'version': 'test_v1'}, format='json')
        assert r.status_code == 400 and 'part de' in r.data['detail']

        r = api_client.post(f'{base}/annuler/', {'version': 'test_v1'}, format='json')
        assert r.status_code == 200
        assert ra.version_courante().code == 'EDEN62'
