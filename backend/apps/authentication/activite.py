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


class JWTAuthentificationActivite(JWTAuthentication):
    """Authentification JWT de l'API qui note la dernière activité."""

    def authenticate(self, request):
        resultat = super().authenticate(request)
        if resultat is not None:
            user, token = resultat
            if not token.get('is_impersonating'):
                noter_activite(user)
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
