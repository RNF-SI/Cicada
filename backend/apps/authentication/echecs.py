"""Limite des essais de mot de passe **par compte**.

La limite par adresse (``AuthRateThrottle``) ne résiste pas à des essais
répartis sur beaucoup d'adresses ; celle-ci compte les échecs de chaque compte.
Elle ne doit pas, pour autant, permettre de tenir un compte dehors : refuser le
bon mot de passe à tout le monde après dix échecs venus de n'importe où
donnait à quiconque connaît une adresse e-mail le moyen d'enfermer dehors un
super admin, y compris pendant un incident. D'où deux compteurs :

- **compte × adresse** : au-delà de ``LIMITE_ADRESSE`` échecs en ``FENETRE``
  secondes, cette adresse ne peut plus essayer ce compte ;
- **compte** : au-delà de ``LIMITE_COMPTE`` échecs (essais répartis), seules les
  adresses qui ont déjà échoué sur ce compte sont refusées. Le titulaire, depuis
  une adresse sans échec, entre toujours.

Le compte est désigné par sa clé primaire quand l'identifiant saisi le désigne
(un compte n'a donc qu'un compteur, qu'on tape son e-mail ou son identifiant),
sinon par la saisie elle-même. La réinitialisation du mot de passe efface les
compteurs du compte (``effacer_compte``), comme le message l'annonce.

Les compteurs vivent dans le cache partagé (Redis) ; s'il est indisponible, la
connexion n'est pas bloquée (même choix que les limites de débit).
"""
import hashlib
import logging

from django.core.cache import cache
from rest_framework.throttling import BaseThrottle

logger = logging.getLogger('apps')

LIMITE_ADRESSE = 10
LIMITE_COMPTE = 30
FENETRE = 15 * 60


def adresse(request):
    """Adresse du client telle que la lisent les limites de débit (``NUM_PROXIES``) :
    jamais le premier élément de ``X-Forwarded-For``, que le client choisit.
    Toujours une adresse IP valable (ou ``None``), pour les champs d'adresse."""
    import ipaddress
    ident = (BaseThrottle().get_ident(request) or '').split(',')[-1].strip()
    for candidat in (ident, request.META.get('REMOTE_ADDR')):
        try:
            return str(ipaddress.ip_address((candidat or '').strip()))
        except ValueError:
            continue
    return None


def compte_vise(saisie):
    """Clé stable du compte désigné par la saisie (e-mail ou identifiant)."""
    from apps.users.models import Role
    saisie = (saisie or '').strip()
    if saisie:
        pk = (Role.objects.filter(email__iexact=saisie).values_list('pk', flat=True).first()
              or Role.objects.filter(identifiant__iexact=saisie).values_list('pk', flat=True).first())
        if pk is not None:
            return f'role:{pk}'
    return 'saisie:' + hashlib.sha256(saisie.lower().encode()).hexdigest()


def _generation(compte):
    return cache.get(f'echecs-gen:{compte}') or 0


def _cles(compte, ip):
    gen = _generation(compte)
    base = hashlib.sha256(f'{compte}|{gen}'.encode()).hexdigest()
    ip_h = hashlib.sha256((ip or '').encode()).hexdigest()[:32]
    return f'echecs-connexion:{base}', f'echecs-connexion:{base}:{ip_h}'


def bloque(compte, ip):
    try:
        cle_compte, cle_adresse = _cles(compte, ip)
        par_adresse = cache.get(cle_adresse) or 0
        if par_adresse >= LIMITE_ADRESSE:
            return True
        return par_adresse > 0 and (cache.get(cle_compte) or 0) >= LIMITE_COMPTE
    except Exception:
        logger.warning('Cache indisponible pour la limite des essais par compte')
        return False


def _incr(cle):
    cache.add(cle, 0, FENETRE)
    return cache.incr(cle)


def noter_echec(compte, ip):
    try:
        cle_compte, cle_adresse = _cles(compte, ip)
        _incr(cle_adresse)
        total = _incr(cle_compte)
        if total == LIMITE_COMPTE:
            logger.warning(
                'Connexion : %s échecs en %s min sur le compte %s, depuis plusieurs adresses',
                total, FENETRE // 60, compte)
    except Exception:
        logger.warning('Cache indisponible pour la limite des essais par compte')


def effacer(compte, ip):
    """Connexion réussie : les compteurs de ce compte repartent de zéro."""
    effacer_compte(compte)


def effacer_compte(compte):
    """Tous les compteurs du compte (toutes adresses) : on change de génération."""
    try:
        # Sans expiration : un entier par compte ayant échoué, et une génération
        # qui retomberait à zéro ferait revivre ses anciens compteurs.
        cache.set(f'echecs-gen:{compte}', _generation(compte) + 1, None)
    except Exception:
        pass


MESSAGE_BLOQUE = (
    "Trop de tentatives de connexion sur ce compte depuis cette adresse. Réessayez "
    "dans 15 minutes, ou réinitialisez votre mot de passe."
)

MESSAGE_BLOQUE_USERSHUB = (
    "Trop de tentatives de connexion sur ce compte depuis cette adresse. Réessayez "
    "dans 15 minutes."
)
