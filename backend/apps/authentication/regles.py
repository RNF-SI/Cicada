"""Règles d'accès d'un compte, communes à la connexion et à chaque requête."""


def compte_autorise(user):
    """Un compte n'entre que s'il est actif pour Django **et** pour CICADA.

    Toutes les désactivations de l'application (administrateur, RGPD,
    workflow de validation) écrivent ``Role.active = False`` ; Django et
    simplejwt ne lisaient que ``is_active``. Un compte désactivé gardait donc
    son accès jusqu'à l'expiration de son jeton.
    """
    return (
        user is not None
        and user.is_active
        and getattr(user, 'active', True)
    )
