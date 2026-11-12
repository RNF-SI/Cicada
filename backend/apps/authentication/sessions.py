"""Durée et révocation des sessions JWT.

Une session commence à la connexion (claim ``session_debut``, recopié par la
rotation et dans chaque jeton d'accès). Au rafraîchissement, on refuse :

- une session plus vieille que ``JWT_SESSION_DUREE_MAX_JOURS`` : la rotation
  repoussait sinon l'échéance de 30 jours à chaque passage, sans fin ;
- un jeton émis avant un changement de mot de passe (``CHECK_REVOKE_TOKEN`` ne
  joue que sur les jetons d'accès : le rafraîchissement en produisait encore) ;
- un compte désactivé ;
- en mode GeoNature, un compte retiré ou désactivé dans UsersHub (le mot de
  passe local y est inutilisable, donc constant : rien d'autre ne le voit) ;
- une impersonation arrêtée, de plus d'une heure, ou dont l'auteur n'est plus
  super admin actif — contrôlé aussi à chaque requête (``impersonation_refusee``).
"""
import logging
import time
from datetime import timedelta

from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings

logger = logging.getLogger('apps')

CLAIM_DEBUT = 'session_debut'
DUREE_IMPERSONATION = timedelta(hours=1)


def duree_max():
    return timedelta(days=int(getattr(settings, 'JWT_SESSION_DUREE_MAX_JOURS', 7)))


def ouvrir(jeton, debut=None):
    """Pose le début de la session sur un jeton neuf (connexion, impersonation)."""
    jeton[CLAIM_DEBUT] = int(debut if debut is not None else time.time())
    return jeton


def _age(claims):
    debut = claims.get(CLAIM_DEBUT)
    if debut is None:
        return None
    return time.time() - float(debut)


def impersonation_refusee(claims):
    """Motif de refus d'un jeton d'impersonation, ou ``None`` s'il vaut encore."""
    from .models import ImpersonationLog
    from .regles import compte_autorise

    age = _age(claims)
    if age is None or age > DUREE_IMPERSONATION.total_seconds():
        return _("La session d'impersonation a expiré.")
    log = (ImpersonationLog.objects.select_related('impersonator')
           .filter(pk=claims.get('impersonation_log_id')).first())
    if log is None or log.ended_at is not None:
        return _("La session d'impersonation est terminée.")
    auteur = log.impersonator
    if (auteur is None or auteur.pk != claims.get('impersonator_id')
            or not compte_autorise(auteur) or not auteur.is_super_admin()):
        return _("La session d'impersonation n'est plus autorisée.")
    return None


def _usershub_refuse(user):
    """En mode GeoNature : le compte UsersHub relié a-t-il encore accès ?"""
    from .providers import GEONATURE, mode_connexion
    if mode_connexion() != GEONATURE or not getattr(user, 'usershub_id_role', None):
        return False
    from .providers import usershub_base
    from .providers.usershub import UsersHubIndisponible
    try:
        lignes = usershub_base.acces_des_comptes([user.usershub_id_role], [])
    except UsersHubIndisponible:
        # Base injoignable : la session continue (la durée absolue la borne) ;
        # personne ne pourrait de toute façon se reconnecter.
        logger.warning('Rafraîchissement : UsersHub injoignable, compte %s non revérifié', user.pk)
        return False
    for id_role, _email, actif, droit in lignes:
        if id_role == user.usershub_id_role:
            return actif is False or not droit
    return True


class RafraichissementSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        from apps.users.models import Role
        from rest_framework_simplejwt.utils import get_md5_hash_password
        from .regles import compte_autorise

        jeton = self.token_class(attrs['refresh'])  # signature, échéance, liste noire
        claims = jeton.payload
        age = _age(claims)
        if age is None or age > duree_max().total_seconds():
            raise InvalidToken(_('Session expirée : reconnectez-vous.'))

        user = Role.objects.filter(pk=claims.get(api_settings.USER_ID_CLAIM)).first()
        if user is None or not compte_autorise(user):
            raise InvalidToken(_('Ce compte a ete desactive. Veuillez contacter un administrateur.'))
        if api_settings.CHECK_REVOKE_TOKEN and claims.get(api_settings.REVOKE_TOKEN_CLAIM) != \
                get_md5_hash_password(user.password):
            raise InvalidToken(_('Le mot de passe a changé : reconnectez-vous.'))

        if claims.get('is_impersonating'):
            motif = impersonation_refusee(claims)
            if motif:
                raise InvalidToken(motif)
        elif _usershub_refuse(user):
            raise InvalidToken(_("Ce compte n'a plus accès à CICADA."))

        return super().validate(attrs)
