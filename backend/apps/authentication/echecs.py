"""Limite des essais de mot de passe **par compte**.

La limite par adresse (``AuthRateThrottle``) ne résiste pas à des essais
répartis sur beaucoup d'adresses. Celle-ci compte les échecs de chaque
identifiant, quelle que soit l'adresse : au-delà de ``LIMITE`` échecs en
``FENETRE`` secondes, ce compte refuse toute tentative jusqu'à la fin de la
fenêtre. Les mots de passe essayés en mode GeoNature sont ceux des comptes
UsersHub, valables sur d'autres applications.

Le compteur vit dans le cache partagé (Redis) ; s'il est indisponible, la
connexion n'est pas bloquée (même choix que les limites de débit).
"""
import hashlib
import logging

from django.core.cache import cache

logger = logging.getLogger('apps')

LIMITE = 10
FENETRE = 15 * 60


def _cle(identifiant):
    empreinte = hashlib.sha256((identifiant or '').strip().lower().encode()).hexdigest()
    return f'echecs-connexion:{empreinte}'


def bloque(identifiant):
    try:
        return (cache.get(_cle(identifiant)) or 0) >= LIMITE
    except Exception:
        logger.warning('Cache indisponible pour la limite des essais par compte')
        return False


def noter_echec(identifiant):
    try:
        cle = _cle(identifiant)
        cache.add(cle, 0, FENETRE)
        cache.incr(cle)
    except Exception:
        logger.warning('Cache indisponible pour la limite des essais par compte')


def effacer(identifiant):
    try:
        cache.delete(_cle(identifiant))
    except Exception:
        pass


MESSAGE_BLOQUE = (
    "Trop de tentatives de connexion sur ce compte. Réessayez dans 15 minutes, "
    "ou réinitialisez votre mot de passe."
)
