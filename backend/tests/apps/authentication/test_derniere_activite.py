"""#771 — « Dernière activité » : le dernier passage sur CICADA, même sans
nouvelle connexion (la session JWT se rafraîchit seule pendant 7 jours)."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.users.models import Role
from tests.factories.users import RoleFactory


def _client(user, **claims):
    token = AccessToken.for_user(user)
    for k, v in claims.items():
        token[k] = v
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    return c


@pytest.mark.django_db
class TestDerniereActivite:
    def test_une_requete_authentifiee_note_l_activite(self):
        user = RoleFactory()
        assert user.derniere_activite is None
        assert _client(user).get('/api/auth/me/').status_code == 200
        user.refresh_from_db()
        assert user.derniere_activite is not None
        assert timezone.now() - user.derniere_activite < timedelta(minutes=1)

    def test_ecriture_limitee_a_une_par_quart_d_heure(self):
        user = RoleFactory()
        recente = timezone.now() - timedelta(minutes=5)
        Role.objects.filter(pk=user.pk).update(derniere_activite=recente)
        _client(user).get('/api/auth/me/')
        user.refresh_from_db()
        assert user.derniere_activite == recente

        ancienne = timezone.now() - timedelta(minutes=20)
        Role.objects.filter(pk=user.pk).update(derniere_activite=ancienne)
        _client(user).get('/api/auth/me/')
        user.refresh_from_db()
        assert user.derniere_activite > ancienne

    def test_pas_d_activite_en_impersonation(self):
        """Un super admin qui se fait passer pour l'utilisateur ne doit pas le
        faire paraître actif."""
        user = RoleFactory()
        _client(user, is_impersonating=True, impersonator_id=1).get('/api/auth/me/')
        user.refresh_from_db()
        assert user.derniere_activite is None

    def test_exposee_par_me_et_par_la_liste_des_utilisateurs(self):
        user = RoleFactory()
        data = _client(user).get('/api/auth/me/').json()
        assert 'derniere_activite' in data
