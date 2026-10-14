"""
Vérifications au démarrage du mode de connexion (#689).

Une instance en mode GeoNature sans adresse ni application n'a plus AUCUN
moyen de connexion (le mot de passe CICADA est coupé) : on le signale au
démarrage plutôt qu'à la première personne qui essaie de se connecter.
"""
from django.conf import settings
from django.core.checks import Warning, register

MODES = ('local', 'geonature', 'keycloak')


@register()
def verifier_mode_connexion(app_configs, **kwargs):
    problemes = []
    mode = settings.AUTH_PROVIDER
    if mode not in MODES:
        problemes.append(Warning(
            f"AUTH_PROVIDER={mode!r} inconnu : connexion CICADA (email + mot de passe) utilisée.",
            hint=f"Valeurs possibles : {', '.join(MODES)}.",
            id='authentication.W001',
        ))
    if mode == 'geonature' and not (settings.GEONATURE_AUTH_URL and settings.GEONATURE_AUTH_ID_APPLICATION):
        # Avertissement et pas erreur : une erreur bloquerait migrate et le
        # démarrage, donc tout le site (pages publiques comprises).
        problemes.append(Warning(
            "AUTH_PROVIDER=geonature mais GEONATURE_AUTH_URL ou GEONATURE_AUTH_ID_APPLICATION est vide : "
            "personne ne peut se connecter.",
            hint="Renseigner les deux dans /var/lib/cicada/.env, ou revenir à AUTH_PROVIDER=local.",
            id='authentication.W002',
        ))
    return problemes
