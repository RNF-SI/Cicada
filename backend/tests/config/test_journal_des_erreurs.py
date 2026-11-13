"""La page « Logs d'erreur » est alimentée en production (#848).

Les réglages de production remplaçaient les listes de handlers des loggers
`apps` et `django.request` : le handler qui écrit la table ErrorLog
disparaissait, et la page de l'administration restait vide.
"""
import importlib
import os
import sys
import threading

import pytest

from apps.core.logging_handlers import DatabaseLogHandler


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'cle-de-test-uniquement')
    sys.modules.pop('config.settings.production', None)
    module = importlib.import_module('config.settings.production')
    yield module
    sys.modules.pop('config.settings.production', None)


@pytest.mark.parametrize('logger', ['apps', 'django.request', 'celery'])
def test_les_erreurs_vont_aussi_en_base_en_production(production, logger):
    assert 'db_errors' in production.LOGGING['loggers'][logger]['handlers']


def test_le_fil_d_ecriture_renait_dans_un_processus_enfant(monkeypatch):
    """Le worker Celery (prefork) configure les journaux AVANT de créer ses
    processus : le fil d'écriture du parent n'existe pas dans les enfants, et
    leurs erreurs s'empilaient sans jamais être écrites."""
    handler = DatabaseLogHandler()
    fil_du_parent = handler._worker_thread
    monkeypatch.setattr(os, 'getpid', lambda: -1)   # « après le fork »
    monkeypatch.setattr(handler, '_write_to_db', lambda data: None)

    handler._assurer_le_fil()

    assert handler._worker_thread is not fil_du_parent
    assert handler._worker_thread.is_alive()
    assert handler._pid == -1
    assert isinstance(handler._worker_thread, threading.Thread)
