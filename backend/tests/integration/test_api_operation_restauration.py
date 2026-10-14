"""
#663 — « Action de restauration » (oui / non) sur une action.

Le champ est tri-état : NULL tant que le gestionnaire n'a pas répondu (actions
antérieures, brouillons), jamais précoché. L'obligation est portée par le
formulaire à la validation.
"""
import pytest
from rest_framework import status

from tests.integration.test_api_operation_code import (  # noqa: F401 (fixtures)
    cat_reserve_nomenclatures, plan_with_actions, type_action_nomenclatures,
)


@pytest.mark.django_db
@pytest.mark.integration
class TestOperationActionRestauration:
    def _url(self, op):
        return f'/api/plans/operations/{op.pk}/'

    def test_non_renseigne_par_defaut(self, api_client, plan_with_actions):
        op = plan_with_actions['op_cs']
        assert op.action_restauration is None
        api_client.force_authenticate(user=plan_with_actions['referent'])
        response = api_client.get(self._url(op))
        assert response.status_code == status.HTTP_200_OK
        assert response.json()['action_restauration'] is None

    @pytest.mark.parametrize('valeur', [True, False])
    def test_enregistre_la_reponse(self, api_client, plan_with_actions, valeur):
        op = plan_with_actions['op_cs']
        api_client.force_authenticate(user=plan_with_actions['referent'])
        response = api_client.patch(self._url(op), {'action_restauration': valeur}, format='json')
        assert response.status_code == status.HTTP_200_OK, response.content
        op.refresh_from_db()
        assert op.action_restauration is valeur
        assert api_client.get(self._url(op)).json()['action_restauration'] is valeur

    def test_reponse_effacable(self, api_client, plan_with_actions):
        op = plan_with_actions['op_cs']
        op.action_restauration = True
        op.save(update_fields=['action_restauration'])
        api_client.force_authenticate(user=plan_with_actions['referent'])
        response = api_client.patch(self._url(op), {'action_restauration': None}, format='json')
        assert response.status_code == status.HTTP_200_OK, response.content
        op.refresh_from_db()
        assert op.action_restauration is None
