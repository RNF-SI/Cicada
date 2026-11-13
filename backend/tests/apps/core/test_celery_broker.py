"""
Le transport Redis de kombu accepte-t-il le client redis-py installé ? (#827)

celery ne borne kombu qu'à < 6.0 : une image construite après la sortie de
kombu 5.7.0 l'a tiré avec redis-py 5.0.1, que ce kombu refuse. Le worker
sortait alors en code 1 dès la connexion au broker, l'erreur (VersionMismatch)
partant dans une journalisation que personne ne lisait, et le conteneur
redémarrait en boucle sur toutes les instances. Ce test fait l'appel où le
worker échouait, sans serveur Redis.
"""
from types import SimpleNamespace

import pytest
from kombu.transport.redis import Channel


@pytest.mark.unit
def test_le_transport_redis_accepte_le_client_installe():
    # Lève kombu.exceptions.VersionMismatch si redis-py est trop ancien pour kombu
    client = Channel._get_client(SimpleNamespace(global_keyprefix=None))
    assert client is not None
