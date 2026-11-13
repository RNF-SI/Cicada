"""Adresses Redis déduites de l'environnement.

Le cache Django vit dans la base Redis 2 (broker Celery en 0, résultats en 1).
Son adresse doit porter le mot de passe de Redis : sans lui, chaque opération
de cache échoue (NOAUTH) — et, `IGNORE_EXCEPTIONS` aidant, en silence.

Les compose de production transmettent `REDIS_URL` (avec le mot de passe) mais
pas toujours `REDIS_CACHE_URL` : l'adresse du cache se déduit donc de la
première quand la seconde manque, au lieu de dépendre d'une variable de plus.
"""
from urllib.parse import urlsplit, urlunsplit

BASE_CACHE = 2
DEFAUT = f'redis://redis:6379/{BASE_CACHE}'


def url_cache(environ):
    explicite = (environ.get('REDIS_CACHE_URL') or '').strip()
    if explicite:
        return explicite
    commune = (environ.get('REDIS_URL') or '').strip()
    if not commune:
        return DEFAUT
    morceaux = urlsplit(commune)
    return urlunsplit(morceaux._replace(path=f'/{BASE_CACHE}', query='', fragment=''))
