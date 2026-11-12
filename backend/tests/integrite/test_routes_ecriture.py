"""Garde de complétude des **routes** d'écriture.

La matrice des droits (``test_droits_ecriture.py``) teste des gestes ; les
failles de la deuxième passe étaient à côté : une autre route, un lien entre
plans, une clé imbriquée. Ce test parcourt toutes les routes de l'API qui
écrivent (POST, PUT, PATCH, DELETE) et exige, pour chacune :

- soit une permission DRF qui contrôle le droit sur l'objet visé
  (``GARDES_RECONNUES`` : écrire dans CE plan, gérer CE site, administrer CE
  compte, super admin…) ;
- soit une ligne dans ``routes_ecriture_relues.txt`` qui dit **où** se fait le
  contrôle (dans la vue, dans le service) — relue par un humain.

Une route nouvelle sans garde reconnue fait échouer ce test tant qu'elle n'a
pas été relue et ajoutée à la liste avec son contrôle.
"""
from pathlib import Path

from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

FICHIER = Path(__file__).with_name('routes_ecriture_relues.txt')
METHODES = ('post', 'put', 'patch', 'delete')

#: Permissions qui contrôlent le droit sur l'objet (ou réservent la route à un
#: rôle global qui a tous les droits).
GARDES_RECONNUES = {
    'IsReferentOrReadOnly', 'PeutEcrireLePlan', 'CanCreatePlan', 'PeutGererLeSite',
    'PeutModifierLeCompte', 'IsSuperAdmin',
}


def _parcourir(motifs, prefixe=''):
    for motif in motifs:
        if isinstance(motif, URLResolver):
            yield from _parcourir(motif.url_patterns, prefixe + str(motif.pattern))
        elif isinstance(motif, URLPattern):
            yield prefixe + str(motif.pattern), motif.callback


def _permissions(cls, action, methode):
    vue = cls()
    vue.action = action
    vue.format_kwarg = None
    vue.kwargs = {}
    vue.args = ()
    vue.request = Request(APIRequestFactory().generic(methode.upper(), '/'))
    vue.headers = {}
    try:
        return {type(p).__name__ for p in vue.get_permissions()}
    except Exception:
        return {c.__name__ for c in getattr(cls, 'permission_classes', [])}


def routes_d_ecriture():
    """{« MÉTHODE Classe.action » : permissions} pour toute écriture sous /api/."""
    routes = {}
    for chemin, rappel in _parcourir(get_resolver().url_patterns):
        if not chemin.startswith('api/'):
            continue
        cls = getattr(rappel, 'cls', None)
        if cls is None:
            routes[f"FONCTION {getattr(rappel, '__module__', '')}.{getattr(rappel, '__name__', rappel)}"] = set()
            continue
        actions = getattr(rappel, 'actions', None)
        ouvertes = {m.lower() for m in getattr(cls, 'http_method_names', METHODES)}
        if actions:
            for methode, action in actions.items():
                if methode in METHODES and methode in ouvertes:
                    routes[f"{methode.upper()} {cls.__name__}.{action}"] = _permissions(cls, action, methode)
        else:
            nom = cls.__name__
            for methode in METHODES:
                if methode in [m.lower() for m in getattr(cls, 'http_method_names', [])] and hasattr(cls, methode):
                    routes[f"{methode.upper()} {nom}"] = _permissions(cls, None, methode)
    return routes


def sans_garde_reconnue():
    return {cle for cle, perms in routes_d_ecriture().items() if not perms & GARDES_RECONNUES}


def liste_relue():
    return {
        ligne.split('#', 1)[0].strip()
        for ligne in FICHIER.read_text(encoding='utf-8').splitlines()
        if ligne.split('#', 1)[0].strip()
    }


def test_chaque_route_d_ecriture_a_une_garde():
    nouvelles = sorted(sans_garde_reconnue() - liste_relue())
    assert not nouvelles, (
        "Route d'écriture sans permission qui contrôle le droit sur l'objet visé : "
        "ajouter une garde (PeutEcrireLePlan, IsReferentOrReadOnly, PeutGererLeSite…) "
        f"ou, si le contrôle est fait dans la vue, l'ajouter à {FICHIER.name} en "
        "disant lequel :\n" + "\n".join(nouvelles))


def test_la_liste_relue_ne_garde_pas_de_route_disparue():
    disparues = sorted(liste_relue() - sans_garde_reconnue())
    assert not disparues, "À retirer de la liste relue :\n" + "\n".join(disparues)
