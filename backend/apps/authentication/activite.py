"""
#771 — « Dernière activité » d'un utilisateur.

La session JWT se rafraîchit seule pendant 7 jours : `last_login` ne dit plus
si quelqu'un est revenu sur CICADA. On note donc le dernier passage à chaque
requête API authentifiée, au plus une écriture par quart d'heure (une page en
déclenche des dizaines), et jamais sous impersonation (un super admin qui se
fait passer pour l'utilisateur ne doit pas le faire paraître actif).
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

INTERVALLE = timedelta(minutes=15)


def noter_activite(user) -> None:
    maintenant = timezone.now()
    derniere = getattr(user, 'derniere_activite', None)
    if derniere is not None and maintenant - derniere < INTERVALLE:
        return
    # update() : ni signal, ni `date_update`, ni journal d'activité.
    type(user).objects.filter(pk=user.pk).update(derniere_activite=maintenant)
    user.derniere_activite = maintenant


#: Écritures permises sous impersonation : en sortir, renouveler son jeton.
ECRITURES_EN_IMPERSONATION = ('/api/auth/stop-impersonation/', '/api/auth/refresh/', '/api/auth/logout/')


def refuser_ecriture_en_impersonation(request):
    """L'impersonation est une consultation : le serveur refuse les écritures.

    La règle n'existait que dans l'interface (``impersonation.interceptor.ts``) ;
    un appel direct avec le jeton d'impersonation écrivait au nom de la
    personne, sans que rien ne le distingue de ses propres actions.
    ``IMPERSONATION_ECRITURE`` la lève (développement, comme l'interface).
    """
    from django.conf import settings
    from rest_framework.exceptions import PermissionDenied

    if getattr(settings, 'IMPERSONATION_ECRITURE', False):
        return
    if request.method in ('GET', 'HEAD', 'OPTIONS'):
        return
    if request.path in ECRITURES_EN_IMPERSONATION:
        return
    raise PermissionDenied(
        "Mode consultation : les modifications sont désactivées pendant l'impersonation.")


class JWTAuthentificationActivite(JWTAuthentication):
    """Authentification JWT de l'API qui note la dernière activité."""

    def get_user(self, validated_token):
        """Refuse dès la requête suivante un compte désactivé dans CICADA.

        simplejwt ne contrôle que ``is_active`` ; la désactivation écrit
        ``active`` (cf. :func:`apps.authentication.regles.compte_autorise`).
        """
        from rest_framework_simplejwt.exceptions import AuthenticationFailed

        from .regles import compte_autorise

        user = super().get_user(validated_token)
        if not compte_autorise(user):
            raise AuthenticationFailed("Ce compte est désactivé.", code='user_inactive')
        return user

    def authenticate(self, request):
        resultat = super().authenticate(request)
        if resultat is not None:
            user, token = resultat
            from apps.core.middleware.logging import set_utilisateur_courant
            set_utilisateur_courant(user)
            if not token.get('is_impersonating'):
                noter_activite(user)
            else:
                from rest_framework_simplejwt.exceptions import AuthenticationFailed
                from .sessions import impersonation_refusee
                motif = impersonation_refusee(token)
                if motif:
                    raise AuthenticationFailed(motif, code='impersonation_terminee')
                refuser_ecriture_en_impersonation(request)
        return resultat


try:
    from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme

    class JWTAuthentificationActiviteScheme(SimpleJWTScheme):
        """Même schéma OpenAPI (« jwtAuth ») que l'authentification simplejwt :
        sans lui, drf-spectacular ne reconnaît pas la sous-classe et la
        documentation de l'API perd son bouton « Authorize »."""
        target_class = 'apps.authentication.activite.JWTAuthentificationActivite'
        name = 'jwtAuth'
except ImportError:  # pragma: no cover — drf-spectacular absent
    pass
