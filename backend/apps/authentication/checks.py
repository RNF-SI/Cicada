"""
Vérifications au démarrage du mode de connexion (#689).

Une instance en mode GeoNature sans base UsersHub configurée n'a plus AUCUN
moyen de connexion (le mot de passe CICADA est coupé) : on le signale au
démarrage plutôt qu'à la première personne qui essaie de se connecter.
"""
import os

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
    from . import reglages
    r = reglages.actuels()
    if r.mode == reglages.GEONATURE:
        if not r.est_configuree():
            # Instance mise à jour depuis l'ancienne vérification par l'API
            # GeoNature (retirée, #764) : ses réglages ne servent plus.
            ancienne_api = bool(os.environ.get('GEONATURE_AUTH_URL', '').strip())
            problemes.append(Warning(
                "Connexion GeoNature activée, mais la base UsersHub ou le code de l'application "
                "n'est pas renseigné : personne ne peut se connecter."
                + (" La vérification par l'API GeoNature (GEONATURE_AUTH_URL) n'existe plus."
                   if ancienne_api else ""),
                hint="Créer le compte de lecture sur le serveur de la base (cicada-usershub-lecture), "
                     "puis renseigner la base et le code dans Administration > Paramètres > Connexion "
                     "(ou USERSHUB_DB_* et GEONATURE_AUTH_CODE_APPLICATION dans /var/lib/cicada/.env).",
                id='authentication.W004',
            ))
        elif r.db_sslmode in ('disable', 'allow', 'prefer') and not r.base_sur_ce_serveur():
            # Mots de passe vérifiés par CICADA : les empreintes traversent le
            # réseau. « prefer » se contente d'une connexion en clair.
            problemes.append(Warning(
                f"Base UsersHub distante ({r.db_host}) lue sans chiffrement exigé "
                f"(sslmode={r.db_sslmode}).",
                hint="Chiffrement « require » (ou verify-full avec USERSHUB_DB_SSLROOTCERT) dans "
                     "Administration > Paramètres > Connexion ou le .env, et ssl = on côté PostgreSQL.",
                id='authentication.W005',
            ))
    return problemes
