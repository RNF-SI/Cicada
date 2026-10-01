"""Les contrôles de santé locaux passent quel que soit ALLOWED_HOSTS."""
import importlib
import os
from unittest import mock

from config import settings as reglages


def test_noms_locaux_toujours_admis():
    with mock.patch.dict(os.environ, {'ALLOWED_HOSTS': 'hub.cicada.example.org'}):
        module = importlib.reload(reglages)
    try:
        assert module.ALLOWED_HOSTS == ['hub.cicada.example.org', 'localhost', '127.0.0.1']
    finally:
        importlib.reload(reglages)
