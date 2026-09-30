"""Contrat entre l'API de suivi et le paquet cicada (installateur, heartbeat).

Les appels reproduisent exactement ceux de
packaging/debian/usr/share/cicada/install/install_service.py (register) et
packaging/debian/usr/bin/cicada-heartbeat (heartbeat).
"""
import uuid

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from . import views


class ContratInstanceTest(TestCase):
    def setUp(self):
        cache.clear()  # compteurs de throttling
        self.client = APIClient()
        self.token = str(uuid.uuid4())

    def register(self, version='0.1.49'):
        return self.client.post('/api/instances/register/',
                                {'token': self.token, 'version': version, 'rgpd_consent': False},
                                format='json')

    def heartbeat(self, token=None, version='0.1.49'):
        return self.client.post('/api/instances/heartbeat/', {'version': version}, format='json',
                                HTTP_X_INSTANCE_TOKEN=token or self.token)

    def test_enregistrement_puis_heartbeat(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.heartbeat()
        # Régression #226 : l'instance authentifiée n'avait pas is_authenticated → 500
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_heartbeat', response.json())

    def test_heartbeat_jeton_inconnu_refuse(self):
        self.assertIn(self.heartbeat(token=str(uuid.uuid4())).status_code, (401, 403))

    def test_heartbeat_sans_jeton_refuse(self):
        response = self.client.post('/api/instances/heartbeat/', {'version': '0.1.49'}, format='json')
        self.assertIn(response.status_code, (401, 403))

    def test_instance_me(self):
        self.register()
        response = self.client.get('/api/instances/me/', HTTP_X_INSTANCE_TOKEN=self.token)
        self.assertEqual(response.status_code, 200)

    def test_reenregistrement_met_a_jour(self):
        self.register('0.1.47')
        self.assertEqual(self.register('0.1.49').status_code, 200)


class VersionTest(TestCase):
    def test_pas_de_mise_a_jour_sans_version_publiee(self):
        views.LATEST_VERSION = ''
        self.assertFalse(views.is_update_available('0.1.49'))

    def test_comparaison_numerique(self):
        views.LATEST_VERSION = '0.1.50'
        try:
            self.assertTrue(views.is_update_available('0.1.49'))
            self.assertTrue(views.is_update_available('0.1.9'))   # 9 < 50, pas un tri de chaînes
            self.assertFalse(views.is_update_available('0.1.50'))
            self.assertFalse(views.is_update_available('0.2.0'))  # instance en avance
            self.assertFalse(views.is_update_available('unknown'))
        finally:
            views.LATEST_VERSION = ''
