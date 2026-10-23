"""
Vérifications au démarrage du mode de connexion (#689).

Une instance en mode GeoNature sans adresse ni application n'a plus AUCUN
moyen de connexion (le mot de passe CICADA est coupé) : on le signale au
démarrage plutôt qu'à la première personne qui essaie de se connecter.
"""
from django.conf import settings
from django.core.checks import Warning, register

MODES = ('local', 'geonature', 'keycloak')
# Base UsersHub sur le serveur de CICADA : rien ne passe sur le réseau.
BASES_SUR_LE_SERVEUR = ('host.docker.internal', 'localhost', '127.0.0.1', '::1')


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
    source = settings.GEONATURE_AUTH_SOURCE
    if mode == 'geonature' and source not in ('api', 'base'):
        problemes.append(Warning(
            f"GEONATURE_AUTH_SOURCE={source!r} inconnue : personne ne peut se connecter.",
            hint="Valeurs possibles : api (par l'API GeoNature), base (par la base UsersHub, #764).",
            id='authentication.W003',
        ))
    if mode == 'geonature' and source == 'base':
        from .providers import usershub_base
        if not usershub_base.est_configuree():
            problemes.append(Warning(
                "AUTH_PROVIDER=geonature, GEONATURE_AUTH_SOURCE=base, mais la base UsersHub ou le code "
                "de l'application n'est pas renseigné : personne ne peut se connecter.",
                hint="Renseigner USERSHUB_DB_HOST, USERSHUB_DB_NAME, USERSHUB_DB_USER, USERSHUB_DB_PASSWORD "
                     "et GEONATURE_AUTH_CODE_APPLICATION dans /var/lib/cicada/.env.",
                id='authentication.W004',
            ))
        elif (settings.USERSHUB_DB_SSLMODE in ('disable', 'allow', 'prefer')
              and settings.USERSHUB_DB_HOST not in BASES_SUR_LE_SERVEUR):
            # Mots de passe vérifiés par CICADA : les empreintes traversent le
            # réseau. « prefer » se contente d'une connexion en clair.
            problemes.append(Warning(
                f"Base UsersHub distante ({settings.USERSHUB_DB_HOST}) lue sans chiffrement exigé "
                f"(USERSHUB_DB_SSLMODE={settings.USERSHUB_DB_SSLMODE}).",
                hint="USERSHUB_DB_SSLMODE=require (ou verify-full avec USERSHUB_DB_SSLROOTCERT) "
                     "dans /var/lib/cicada/.env, et ssl = on côté PostgreSQL.",
                id='authentication.W005',
            ))
    elif mode == 'geonature' and not (settings.GEONATURE_AUTH_URL and settings.GEONATURE_AUTH_ID_APPLICATION):
        # Avertissement et pas erreur : une erreur bloquerait migrate et le
        # démarrage, donc tout le site (pages publiques comprises).
        problemes.append(Warning(
            "AUTH_PROVIDER=geonature mais GEONATURE_AUTH_URL ou GEONATURE_AUTH_ID_APPLICATION est vide : "
            "personne ne peut se connecter.",
            hint="Renseigner les deux dans /var/lib/cicada/.env, ou revenir à AUTH_PROVIDER=local.",
            id='authentication.W002',
        ))
    return problemes
