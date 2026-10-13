"""
Mode de connexion de l'instance (#689).

Un seul mode à la fois (``AUTH_PROVIDER``) : soit les comptes CICADA, soit un
système externe (GeoNature / UsersHub, plus tard OIDC). Un mode externe vérifie
l'identité ailleurs puis rattache la personne à un compte CICADA ; la session
reste celle de CICADA (mêmes JWT).
"""
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

LOCAL = 'local'
GEONATURE = 'geonature'


def mode_connexion():
    """'geonature' si l'instance se connecte par GeoNature, 'local' sinon."""
    return GEONATURE if settings.AUTH_PROVIDER == GEONATURE else LOCAL


def connexion_locale_active():
    return mode_connexion() == LOCAL


def message_connexion_externe():
    return _("Sur cette instance, la connexion se fait uniquement avec votre compte %(libelle)s. "
             "Si vous n'en avez pas, demandez-en un avec l'adresse email de votre compte CICADA.") % {
        'libelle': settings.GEONATURE_AUTH_LIBELLE}


class ConnexionLocaleActive(BasePermission):
    """
    Ouvert à tous tant que l'instance est en connexion locale ; fermé en mode
    externe (connexion par mot de passe, inscription, mot de passe oublié).
    """

    def has_permission(self, request, view):
        if connexion_locale_active():
            return True
        # Levée ici plutôt que « return False » : pour un visiteur anonyme, DRF
        # répondrait 401, que le frontend lit comme une session expirée.
        raise PermissionDenied(message_connexion_externe())
