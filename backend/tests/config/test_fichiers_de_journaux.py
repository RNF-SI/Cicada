"""#846 — fichiers de journaux partagés entre processus.

Les 3 processus gunicorn et les conteneurs Celery écrivent les mêmes fichiers
(/var/log/cicada). Avec RotatingFileHandler, chacun faisait sa propre rotation :
la profondeur gardée était divisée d'autant. La rotation se fait sur l'hôte
(logrotate, posé par le paquet) ; les processus se contentent d'écrire.
"""
from config.settings import base


def test_aucun_processus_ne_fait_tourner_les_fichiers_lui_meme():
    for nom in ('file', 'error_file', 'audit_file'):
        assert base.LOGGING['handlers'][nom]['class'] == 'logging.handlers.WatchedFileHandler', nom
