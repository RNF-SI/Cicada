"""
Réglages effectifs de la connexion GeoNature / UsersHub (#769).

Deux sources : le ``.env`` (``settings``) et la ligne ``ConnexionGeoNature``
saisie dans Administration > Paramètres. Règles, sur le modèle du
raccordement au hub (#695) :

- le **mode** (``local`` / ``geonature``) choisi à l'écran prime sur
  ``AUTH_PROVIDER`` : l'installeur écrit toujours ``AUTH_PROVIDER=local``,
  l'écran n'aurait sinon jamais d'effet. Secours en ligne de commande :
  ``manage.py connexion_locale`` ;
- les **autres réglages** viennent du ``.env`` quand ils y sont renseignés
  (autre chose que la valeur par défaut) : le champ est alors verrouillé à
  l'écran. Sinon, de la base.

Tout est relu à chaque appel (``actuels()``, une requête) : un réglage modifié
vaut sans redémarrage, Celery compris.

Le mot de passe du compte de lecture est chiffré en base et n'est **jamais**
renvoyé par l'API ni journalisé.
"""
import base64
import hashlib
import logging
import re
from dataclasses import dataclass, field, replace

from django.conf import settings
from django.db import DatabaseError

logger = logging.getLogger(__name__)

LOCAL = 'local'
GEONATURE = 'geonature'
MODES = (LOCAL, GEONATURE)

ORIGINE_ENVIRONNEMENT = 'environnement'
ORIGINE_BASE = 'base'

SSLMODES = ('prefer', 'require', 'verify-ca', 'verify-full')
# Base UsersHub sur le serveur de CICADA : rien ne passe sur le réseau. Vue
# d'un conteneur, « localhost » est le conteneur lui-même : on écrit
# host.docker.internal (comme l'installateur).
BASES_SUR_LE_SERVEUR = ('host.docker.internal', 'localhost', '127.0.0.1', '::1')
HOTE_DOCKER = 'host.docker.internal'

# champ de l'écran -> (réglage du .env, valeur par défaut : non « renseignée »)
CHAMPS = {
    'libelle': ('GEONATURE_AUTH_LIBELLE', 'GeoNature'),
    'organismes_exclus': ('GEONATURE_AUTH_ORGANISMES_EXCLUS', set()),
    'code_application': ('GEONATURE_AUTH_CODE_APPLICATION', ''),
    'db_host': ('USERSHUB_DB_HOST', ''),
    'db_port': ('USERSHUB_DB_PORT', 5432),
    'db_name': ('USERSHUB_DB_NAME', ''),
    'db_user': ('USERSHUB_DB_USER', ''),
    'db_sslmode': ('USERSHUB_DB_SSLMODE', 'prefer'),
}


class ErreurReglage(Exception):
    """Refus à présenter tel quel : code stable, message, statut HTTP, détail."""

    def __init__(self, code, message, status_code=400, detail=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class Reglages:
    mode: str
    libelle: str
    organismes_exclus: frozenset
    code_application: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str = field(repr=False)
    db_sslmode: str
    db_sslrootcert: str
    timeout: int
    schema: str

    def est_configuree(self):
        return bool(self.code_application and self.db_host and self.db_name and self.db_user)

    def base_sur_ce_serveur(self):
        return self.db_host in BASES_SUR_LE_SERVEUR


# --------------------------------------------------------------------------- #
# Chiffrement du mot de passe
# --------------------------------------------------------------------------- #

def _fernet():
    from cryptography.fernet import Fernet

    cle = base64.urlsafe_b64encode(
        hashlib.sha256((settings.SECRET_KEY + ':cicada-usershub-lecture').encode('utf-8')).digest()
    )
    return Fernet(cle)


def chiffrer(texte):
    return _fernet().encrypt(texte.encode('utf-8')).decode('ascii')


def dechiffrer(texte):
    """Le mot de passe en clair, ou '' s'il est absent ou indéchiffrable (SECRET_KEY changée)."""
    if not texte:
        return ''
    from cryptography.fernet import InvalidToken
    try:
        return _fernet().decrypt(texte.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError):
        logger.error("Connexion GeoNature : mot de passe du compte de lecture indéchiffrable "
                     "(SECRET_KEY modifiée ?) — à ressaisir dans les paramètres")
        return ''


# --------------------------------------------------------------------------- #
# Lecture
# --------------------------------------------------------------------------- #

def ligne():
    from .models import ConnexionGeoNature
    return ConnexionGeoNature.charger()


def _ligne_ou_vierge():
    """La ligne en base ; vierge si la table n'existe pas encore (avant migrate)."""
    from .models import ConnexionGeoNature
    try:
        return ConnexionGeoNature.charger()
    except DatabaseError:
        return ConnexionGeoNature(pk=1)


def lire_organismes(texte):
    return frozenset(int(x) for x in (texte or '').split(',') if x.strip().lstrip('-').isdigit())


def _environnement(champ):
    """Valeur du .env si elle y est renseignée (autre que le défaut), sinon None."""
    reglage, defaut = CHAMPS[champ]
    valeur = getattr(settings, reglage)
    if champ == 'organismes_exclus':
        valeur = frozenset(valeur or ())
        return valeur or None
    if valeur in ('', None) or valeur == defaut:
        return None
    return valeur


def _base(champ, enregistrement):
    valeur = getattr(enregistrement, champ)
    if champ == 'organismes_exclus':
        return lire_organismes(valeur) or None
    return valeur if valeur not in ('', None) else None


def actuels(enregistrement=None):
    """Réglages effectifs, lus maintenant (une requête)."""
    enregistrement = enregistrement or _ligne_ou_vierge()
    valeurs = {}
    for champ, (_reglage, defaut) in CHAMPS.items():
        env = _environnement(champ)
        base = _base(champ, enregistrement)
        valeurs[champ] = env if env is not None else (base if base is not None else defaut)
    mode = enregistrement.mode or (settings.AUTH_PROVIDER or LOCAL)
    return Reglages(
        mode=GEONATURE if mode == GEONATURE else LOCAL,
        libelle=valeurs['libelle'],
        organismes_exclus=frozenset(valeurs['organismes_exclus']),
        code_application=valeurs['code_application'],
        db_host=valeurs['db_host'],
        db_port=int(valeurs['db_port'] or 5432),
        db_name=valeurs['db_name'],
        db_user=valeurs['db_user'],
        db_password=settings.USERSHUB_DB_PASSWORD or dechiffrer(enregistrement.db_password_chiffre),
        db_sslmode=valeurs['db_sslmode'],
        db_sslrootcert=settings.USERSHUB_DB_SSLROOTCERT,
        timeout=settings.GEONATURE_AUTH_TIMEOUT,
        schema=settings.USERSHUB_DB_SCHEMA,
    )


def origines(enregistrement=None):
    """D'où vient chaque valeur : `environnement`, `base` ou None (défaut)."""
    enregistrement = enregistrement or _ligne_ou_vierge()
    resultat = {}
    for champ in CHAMPS:
        if _environnement(champ) is not None:
            resultat[champ] = ORIGINE_ENVIRONNEMENT
        else:
            resultat[champ] = ORIGINE_BASE if _base(champ, enregistrement) is not None else None
    if settings.USERSHUB_DB_PASSWORD:
        resultat['db_password'] = ORIGINE_ENVIRONNEMENT
    else:
        resultat['db_password'] = ORIGINE_BASE if enregistrement.db_password_chiffre else None
    resultat['mode'] = ORIGINE_BASE if enregistrement.mode else ORIGINE_ENVIRONNEMENT
    return resultat


def etat():
    """Ce que l'écran affiche. Jamais le mot de passe : seulement s'il est défini."""
    enregistrement = _ligne_ou_vierge()
    r = actuels(enregistrement)
    return {
        'mode': r.mode,
        'configuree': r.est_configuree(),
        'base_sur_ce_serveur': r.base_sur_ce_serveur(),
        'valeurs': {
            'libelle': r.libelle,
            'organismes_exclus': ','.join(str(i) for i in sorted(r.organismes_exclus)),
            'code_application': r.code_application,
            'db_host': r.db_host,
            'db_port': r.db_port,
            'db_name': r.db_name,
            'db_user': r.db_user,
            'db_sslmode': r.db_sslmode,
        },
        'mot_de_passe_defini': bool(r.db_password),
        'origines': origines(enregistrement),
        'modifie_le': enregistrement.modifie_le if enregistrement.pk and enregistrement.modifie_le else None,
        'modifie_par': getattr(enregistrement.modifie_par, 'email', None) if enregistrement.modifie_par_id else None,
    }


# --------------------------------------------------------------------------- #
# Saisie
# --------------------------------------------------------------------------- #

def _valider(champ, valeur):
    if champ == 'db_port':
        if valeur in ('', None):
            return None
        try:
            port = int(valeur)
        except (TypeError, ValueError):
            port = 0
        if not 1 <= port <= 65535:
            raise ErreurReglage('invalide', "Port invalide (1 à 65535).")
        return port
    if not isinstance(valeur, str):
        raise ErreurReglage('invalide', f"Valeur invalide pour « {champ} ».")
    valeur = valeur.strip()
    if champ == 'db_host':
        if re.search(r'[,\s]', valeur) or len(valeur) > 255:
            raise ErreurReglage('invalide', "Hôte de la base UsersHub : une seule adresse.")
        return HOTE_DOCKER if valeur in BASES_SUR_LE_SERVEUR else valeur
    if champ == 'db_sslmode':
        if valeur and valeur not in SSLMODES:
            raise ErreurReglage('invalide', "Chiffrement invalide (prefer, require, verify-ca, verify-full).")
        return valeur
    if champ == 'organismes_exclus':
        morceaux = [m.strip() for m in valeur.split(',') if m.strip()]
        if any(not m.lstrip('-').isdigit() for m in morceaux):
            raise ErreurReglage('invalide', "Organismes à ignorer : des id_organisme séparés par des virgules.")
        return ','.join(morceaux)
    if champ in ('code_application', 'db_name', 'db_user') and re.search(r'\s', valeur):
        raise ErreurReglage('invalide', f"« {champ} » ne contient pas d'espace.")
    longueur = {'libelle': 100, 'code_application': 100, 'db_name': 100, 'db_user': 100}.get(champ, 255)
    if len(valeur) > longueur:
        raise ErreurReglage('invalide', f"« {champ} » trop long.")
    return valeur


def configurer(donnees, utilisateur):
    """
    Enregistre les réglages saisis par un super admin.

    Champs facultatifs : ceux de ``CHAMPS``, ``db_password`` (remplace le mot de
    passe en place, jamais relu) et ``effacer_mot_de_passe``. Un champ fourni
    par le .env est refusé (409 ``valeur_environnement``).

    Connexion GeoNature déjà active : la nouvelle configuration est d'abord
    testée, et refusée si elle couperait la connexion (y compris celle de qui
    la modifie). Sinon, une faute de frappe enfermerait tout le monde dehors.
    """
    if not isinstance(donnees, dict):
        raise ErreurReglage('invalide', "Corps de requête invalide.")
    enregistrement = ligne()
    env = origines(enregistrement)
    for champ in (*CHAMPS, 'db_password'):
        if champ in donnees and env.get(champ) == ORIGINE_ENVIRONNEMENT:
            reglage = CHAMPS[champ][0] if champ in CHAMPS else 'USERSHUB_DB_PASSWORD'
            raise ErreurReglage(
                'valeur_environnement',
                f"« {champ} » est fourni par la configuration du serveur ({reglage}) : retirez-le de "
                "/var/lib/cicada/.env et recréez les conteneurs pour le régler ici.", 409,
            )

    modifies = []
    for champ in CHAMPS:
        if champ in donnees:
            nouvelle = _valider(champ, donnees[champ])
            setattr(enregistrement, champ, nouvelle if nouvelle is not None else (None if champ == 'db_port' else ''))
            modifies.append(champ)
    if donnees.get('effacer_mot_de_passe'):
        enregistrement.db_password_chiffre = ''
        modifies.append('effacer_mot_de_passe')
    elif donnees.get('db_password'):
        if not isinstance(donnees['db_password'], str) or len(donnees['db_password']) > 200:
            raise ErreurReglage('invalide', "Mot de passe invalide.")
        enregistrement.db_password_chiffre = chiffrer(donnees['db_password'])
        modifies.append('db_password')

    if actuels(enregistrement).mode == GEONATURE and modifies:
        resultat = tester(actuels(enregistrement), utilisateur)
        _exiger_acces(resultat)

    enregistrement.modifie_par = utilisateur
    enregistrement.save()
    # Jamais les valeurs : seulement les noms des champs (le mot de passe en est un).
    logger.info("Connexion GeoNature modifiée depuis les paramètres : %s.", ', '.join(modifies) or 'rien')
    return enregistrement


# --------------------------------------------------------------------------- #
# Test, activation
# --------------------------------------------------------------------------- #

def tester(r, utilisateur=None):
    """
    Essaie la configuration ``r`` sans rien écrire : connexion (chiffrée ?),
    application, puis bilan des comptes CICADA actifs. ``vous`` dit si
    ``utilisateur`` pourra se connecter.
    """
    from .providers import usershub_base

    resultat = {'ok': False, 'erreur': None, 'message': '', 'chiffree': None,
                'application': None, 'bilan': None, 'vous': None}
    if not r.est_configuree():
        resultat.update(erreur='non_configuree',
                        message="Indiquez l'hôte, la base, le compte de lecture et le code de l'application.")
        return resultat
    try:
        diagnostic = usershub_base.diagnostiquer(r)
    except usershub_base.ErreurDiagnostic as exc:
        resultat.update(erreur=exc.code, message=exc.message)
        return resultat
    resultat['chiffree'] = diagnostic['chiffree']
    resultat['application'] = diagnostic['application']
    if not diagnostic['application']:
        resultat.update(erreur='application_absente',
                        message=f"Aucune application « {r.code_application} » dans UsersHub "
                                "(colonne code_application).")
        return resultat
    bilan = usershub_base.bilan_des_comptes(r)
    resultat['bilan'] = bilan
    if utilisateur is not None:
        resultat['vous'] = next(
            ({'autorise': c['motif'] is None, 'motif': c['motif']}
             for c in bilan['comptes'] if c['id'] == utilisateur.pk),
            {'autorise': False, 'motif': 'absent'},
        )
    resultat['ok'] = True
    return resultat


def _exiger_acces(resultat):
    if not resultat['ok']:
        raise ErreurReglage('test_echoue', resultat['message'] or "Le test de la base UsersHub a échoué.",
                            400, resultat)
    if resultat['vous'] is not None and not resultat['vous']['autorise']:
        raise ErreurReglage(
            'enfermement',
            "Votre propre compte ne pourrait pas se connecter (pas de compte UsersHub avec votre email, "
            "compte désactivé ou pas de profil sur l'application) : vous seriez enfermé dehors. "
            "Donnez-vous le profil dans UsersHub, puis recommencez.", 409, resultat)


def activer(utilisateur, confirmer=False):
    """Passe l'instance en connexion GeoNature, après test et garde-fous."""
    enregistrement = ligne()
    r = replace(actuels(enregistrement), mode=GEONATURE)
    resultat = tester(r, utilisateur)
    _exiger_acces(resultat)
    refuses = resultat['bilan']['refuses']
    if refuses and not confirmer:
        raise ErreurReglage(
            'confirmation_requise',
            f"{refuses} compte(s) CICADA actif(s) ne pourront plus se connecter. Confirmez pour activer.",
            409, resultat)
    enregistrement.mode = GEONATURE
    enregistrement.modifie_par = utilisateur
    enregistrement.save()
    _journaliser(utilisateur, 'activate', "Connexion GeoNature / UsersHub activée",
                 {'refuses': refuses, 'autorises': resultat['bilan']['autorises']})
    return resultat


def desactiver(utilisateur, confirmer=False):
    """Revient aux comptes CICADA (email + mot de passe)."""
    if not utilisateur.has_usable_password() and not confirmer:
        raise ErreurReglage(
            'mot_de_passe_requis',
            "Votre compte n'a pas de mot de passe CICADA : après le retour aux comptes CICADA, il faudra "
            "passer par « Mot de passe oublié ». Confirmez pour continuer.", 409)
    enregistrement = ligne()
    enregistrement.mode = LOCAL
    enregistrement.modifie_par = utilisateur
    enregistrement.save()
    _journaliser(utilisateur, 'deactivate', "Retour à la connexion par comptes CICADA", {})


def _journaliser(utilisateur, action, description, metadata):
    from apps.core.services import ActivityService
    try:
        ActivityService.log_activity(
            entity_type='instance', entity_id=1, entity_name="Connexion GeoNature", action=action,
            actor=utilisateur, description=description, metadata=metadata, visibility='system',
        )
    except Exception:  # noqa: BLE001 — le journal ne doit pas annuler la bascule
        logger.exception("Connexion GeoNature : journalisation impossible")
