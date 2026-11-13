"""Adresse du cache Django en production (config/redis_urls.py)."""
import pytest

from config.redis_urls import DEFAUT, url_cache


@pytest.mark.parametrize('environ, attendu', [
    # Les compose de production ne transmettent que REDIS_URL : le mot de
    # passe doit passer dans l'adresse du cache, en base 2.
    ({'REDIS_URL': 'redis://:secret@redis:6379/0'}, 'redis://:secret@redis:6379/2'),
    ({'REDIS_URL': 'redis://:s%40c@redis:6379'}, 'redis://:s%40c@redis:6379/2'),
    ({'REDIS_URL': 'rediss://:secret@cache.exemple:6380/0?ssl_cert_reqs=none'},
     'rediss://:secret@cache.exemple:6380/2'),
    # Une adresse explicite prime.
    ({'REDIS_URL': 'redis://:a@redis:6379/0', 'REDIS_CACHE_URL': 'redis://:b@autre:6379/5'},
     'redis://:b@autre:6379/5'),
    ({'REDIS_CACHE_URL': '  '}, DEFAUT),
    ({}, DEFAUT),
])
def test_url_cache(environ, attendu):
    assert url_cache(environ) == attendu

