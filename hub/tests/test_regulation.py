"""
#701 — Régulation des dépôts : toutes les instances publient la nuit, et le
hub doit pouvoir dire « revenez plus tard » plutôt que de subir un pic.

- au-delà de ``HUB_LOTS_CONCURRENTS_MAX`` lots ouverts, l'ouverture d'un lot
  répond 429 avec ``Retry-After`` ;
- un lot ouvert depuis plus de ``HUB_LOT_DUREE_MAX_MINUTES`` (dépôt interrompu,
  jamais basculé ni abandonné) ne compte plus : sans cela, il bloquerait sa
  place pour toujours ;
- le registre signale les instances dont la dernière publication réussie date
  de plus de 48 h.
"""
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.index.models import LotPublication

JETONS = {'rnf': 'jeton-rnf', 'cen': 'jeton-cen', 'dreal': 'jeton-dreal'}

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def reglages(settings):
    settings.HUB_FEDERATION_TOKENS = JETONS
    settings.HUB_LOTS_CONCURRENTS_MAX = 2
    settings.HUB_LOT_DUREE_MAX_MINUTES = 180
    settings.HUB_RETRY_AFTER_SECONDES = 600


def ouvrir(client, instance):
    return client.post(
        '/api/federation/lots/', {'format_version': 1},
        content_type='application/json',
        HTTP_X_FEDERATION_TOKEN=JETONS[instance],
    )


class TestLimiteDesLotsConcurrents:

    def test_au_dela_de_la_limite_le_hub_demande_de_revenir_plus_tard(self, client):
        assert ouvrir(client, 'rnf').status_code == 201
        assert ouvrir(client, 'cen').status_code == 201

        reponse = ouvrir(client, 'dreal')

        assert reponse.status_code == 429
        assert reponse['Retry-After'] == '600'
        assert reponse.json()['retry_after'] == 600
        assert not LotPublication.objects.filter(instance_id='dreal').exists()

    def test_une_bascule_libere_la_place(self, client):
        ouvrir(client, 'rnf')
        lot = ouvrir(client, 'cen').json()['lot_id']
        LotPublication.objects.filter(pk=lot).update(etat=LotPublication.ETAT_BASCULE)

        assert ouvrir(client, 'dreal').status_code == 201

    def test_un_lot_abandonne_libere_la_place(self, client):
        ouvrir(client, 'rnf')
        lot = ouvrir(client, 'cen').json()['lot_id']
        client.delete(f'/api/federation/lots/{lot}/', HTTP_X_FEDERATION_TOKEN=JETONS['cen'])

        assert ouvrir(client, 'dreal').status_code == 201

    def test_un_lot_interrompu_expire_et_ne_bloque_plus(self, client):
        """Un dépôt coupé en route laisse un lot ouvert : il ne doit pas
        occuper sa place indéfiniment."""
        ouvrir(client, 'rnf')
        lot = ouvrir(client, 'cen').json()['lot_id']
        LotPublication.objects.filter(pk=lot).update(
            date_ouverture=timezone.now() - timedelta(minutes=181))

        assert ouvrir(client, 'dreal').status_code == 201


class TestRetardDePublication:

    def _registre(self, client):
        reponse = client.get('/api/federation/instances/', HTTP_X_FEDERATION_TOKEN=JETONS['rnf'])
        assert reponse.status_code == 200
        return {i['instance_id']: i for i in reponse.json()['instances']}

    def _bascule(self, instance, il_y_a):
        lot = LotPublication.objects.create(instance_id=instance, etat=LotPublication.ETAT_BASCULE)
        LotPublication.objects.filter(pk=lot.pk).update(date_bascule=timezone.now() - il_y_a)

    def test_une_instance_sans_publication_depuis_48h_est_signalee(self, client):
        self._bascule('rnf', timedelta(hours=2))
        self._bascule('cen', timedelta(hours=49))

        registre = self._registre(client)

        assert registre['rnf']['en_retard'] is False
        assert registre['cen']['en_retard'] is True
