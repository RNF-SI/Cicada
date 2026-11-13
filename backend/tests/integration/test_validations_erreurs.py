"""Approbation / rejet d'une demande : une erreur imprévue n'est plus un 400 muet (#837).

Tout était rattrapé par un `except Exception` qui renvoyait `str(e)` en 400,
sans rien journaliser : une erreur de code passait pour un refus, et un
commentaire manquant revenait comme un texte Python.
"""
import logging
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.notifications.models import ValidationRequest
from tests.factories.users import CorRoleSiteFactory, RoleFactory, SiteFactory, SuperAdminFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture
def demande():
    site, demandeur = SiteFactory(), RoleFactory()
    CorRoleSiteFactory(id_role=demandeur, id_site=site, referent=False)
    return ValidationRequest.objects.create(
        request_type='referent_validation', status='pending',
        requester=demandeur, target_site=site)


@pytest.fixture
def client():
    c = APIClient(raise_request_exception=False)
    c.force_authenticate(SuperAdminFactory())
    return c


def test_un_commentaire_manquant_revient_comme_une_erreur_de_champ(client, demande):
    reponse = client.post(f'/api/validations/{demande.pk}/reject/', {}, format='json')
    assert reponse.status_code == 400
    assert 'comment' in reponse.json()


@pytest.mark.parametrize('geste, cible', [
    ('reject', 'apps.notifications.views.ValidationService.reject_request'),
    ('approve', 'apps.notifications.views.ValidationService.approve_referent_validation'),
])
def test_une_erreur_imprevue_est_journalisee_et_n_est_pas_un_refus(client, demande, geste, cible, caplog):
    with patch(cible, side_effect=RuntimeError('bogue interne')), \
            caplog.at_level(logging.ERROR):
        reponse = client.post(f'/api/validations/{demande.pk}/{geste}/',
                              {'comment': 'motif'}, format='json')
    assert reponse.status_code == 500
    assert 'bogue interne' not in reponse.content.decode()
    assert any(r.exc_info and 'bogue interne' in str(r.exc_info[1]) for r in caplog.records)
    demande.refresh_from_db()
    assert demande.status == 'pending'


def test_un_refus_metier_reste_un_400_explicite(client, demande):
    with patch('apps.notifications.views.ValidationService.approve_referent_validation',
               side_effect=ValueError("Cette demande n'est pas applicable")):
        reponse = client.post(f'/api/validations/{demande.pk}/approve/', {}, format='json')
    assert reponse.status_code == 400
    assert "n'est pas applicable" in reponse.json()['error']
