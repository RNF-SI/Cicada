"""
Connexion par un GeoNature / UsersHub (#689, #691, #764).

Déroulé d'une connexion :

1. ``usershub_base.authentifier()`` lit la base UsersHub en lecture seule,
   comme pypnusershub le fait pour GeoNature : identifiant, mot de passe
   (bcrypt, sinon md5), compte actif, profil sur l'application CICADA
   (``GEONATURE_AUTH_CODE_APPLICATION``, direct ou par un groupe), fiche de
   l'organisme.
2. Le compte CICADA est retrouvé par ``usershub_id_role``, sinon par email,
   sinon créé ; l'organisme est retrouvé par ``uuid_organisme`` (clé commune
   aux deux bases, les ``id_organisme`` étant des séquences locales), sinon
   créé.

Rien n'est synchronisé en dehors des connexions : un nouvel organisme UsersHub
apparaît dans CICADA à la première connexion d'un de ses membres.

L'ancienne vérification par l'API GeoNature (``POST /auth/login``) a été
retirée : GeoNature n'y contrôle jamais le droit sur CICADA.
"""
import logging
from dataclasses import dataclass, field

from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from apps.users.models import BibOrganismes, Role

from .. import reglages

logger = logging.getLogger(__name__)


class UsersHubErreur(Exception):
    """Échec de connexion à présenter tel quel à l'utilisateur."""

    def __init__(self, message, status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UsersHubIndisponible(UsersHubErreur):
    """Base UsersHub injoignable, ou pas comme prévu."""

    def __init__(self, message=None):
        super().__init__(
            message or _("Le service de connexion %(libelle)s est indisponible. "
                         "Réessayez plus tard ou connectez-vous avec votre email.")
            % {'libelle': reglages.actuels().libelle},
            status_code=502,
        )


def est_active():
    """Mode 'geonature' choisi ET base UsersHub configurée."""
    r = reglages.actuels()
    return r.mode == reglages.GEONATURE and r.est_configuree()


def verifier(login, password):
    """Vérifie le compte dans la base UsersHub ; rend une IdentiteUsersHub."""
    from . import usershub_base
    return usershub_base.authentifier(login, password)


@dataclass
class IdentiteUsersHub:
    id_role: int
    email: str
    identifiant: str = ''
    nom: str = ''
    prenom: str = ''
    id_organisme: int | None = None
    # Fiche lue dans la base UsersHub (None si absente ou exclue).
    fiche_organisme: dict | None = field(default=None, repr=False)


def verifier_email(identite):
    """Un compte UsersHub sans email ne peut pas devenir un compte CICADA."""
    if not identite.email or '@' not in identite.email:
        raise UsersHubErreur(
            _("Votre compte %(libelle)s n'a pas d'adresse email : il ne peut pas être "
              "utilisé pour se connecter à CICADA. Contactez l'administrateur de %(libelle)s.")
            % {'libelle': reglages.actuels().libelle},
            status_code=403,
        )


# ---------------------------------------------------------------------------
# Rattachement côté CICADA
# ---------------------------------------------------------------------------

CHAMPS_ORGANISME = (
    'adresse_organisme', 'cp_organisme', 'ville_organisme', 'tel_organisme',
    'fax_organisme', 'email_organisme', 'url_organisme',
)


def organisme_pour(identite):
    """
    Organisme CICADA correspondant à l'organisme UsersHub de la personne.

    Retrouvé par uuid, créé s'il n'existe pas. None si la personne n'a pas
    d'organisme, si c'est un pseudo-organisme exclu, ou si sa fiche est absente.
    """
    id_organisme = identite.id_organisme
    if id_organisme is None or int(id_organisme) in reglages.actuels().organismes_exclus:
        return None

    fiche = identite.fiche_organisme
    if fiche is None:
        return None

    organisme = BibOrganismes.objects.filter(uuid_organisme=fiche['uuid_organisme']).first()
    if organisme is not None:
        return organisme

    nom = (fiche.get('nom_organisme') or '').strip()
    if not nom:
        return None
    valeurs = {c: (fiche.get(c) or None) for c in CHAMPS_ORGANISME}
    # Champs à longueur bornée côté CICADA : on tronque plutôt que d'échouer.
    for champ, longueur in (('cp_organisme', 10), ('ville_organisme', 100),
                            ('tel_organisme', 20), ('fax_organisme', 20),
                            ('email_organisme', 254), ('url_organisme', 200)):
        if valeurs[champ]:
            valeurs[champ] = str(valeurs[champ])[:longueur]
    try:
        with transaction.atomic():
            organisme = BibOrganismes.objects.create(
                uuid_organisme=fiche['uuid_organisme'],
                nom_organisme=nom[:255],
                additional_data={'source': 'usershub', 'id_organisme_usershub': int(id_organisme)},
                **valeurs,
            )
    except IntegrityError:
        # Créé entre-temps par une connexion simultanée d'un collègue.
        organisme = BibOrganismes.objects.filter(uuid_organisme=fiche['uuid_organisme']).first()
    else:
        logger.info("Connexion GeoNature : organisme « %s » créé (UsersHub n° %s)", nom, id_organisme)
    return organisme


def _verifier_adoption(compte, organisme, identite):
    """Un compte local n'est relié à UsersHub par son seul email que s'il n'ouvre
    pas plus de droits que ce qu'UsersHub atteste.

    Quiconque peut créer dans UsersHub un compte portant l'adresse d'un
    administrateur CICADA (et lui donner le profil CICADA) entrerait sinon avec
    ses droits. Super administrateur et rédacteur principal : jamais par
    l'email — sauf celui qui a activé la connexion GeoNature ; les autres se
    connectent d'abord, puis sont promus. Administrateur d'organisme :
    seulement si UsersHub le rattache au même organisme.
    """
    # Le super administrateur qui a activé la connexion GeoNature a vérifié
    # lui-même que ce compte UsersHub est le sien (garde-fou « enfermement ») :
    # c'est le rapprochement attendu, pas une usurpation.
    if compte.pk == getattr(reglages.ligne().modifie_par, 'pk', None):
        return
    if compte.is_superuser or compte.role_level in ('super_admin', 'redacteur_principal'):
        refus = True
    elif compte.role_level == 'admin_og':
        # Comparer les objets : la clé de Role.id_organisme n'est pas forcément la clé primaire.
        refus = organisme is None or compte.id_organisme is None or organisme.pk != compte.id_organisme.pk
    else:
        refus = False
    if refus:
        logger.warning(
            "Connexion GeoNature : rapprochement refusé entre le compte UsersHub %s et un "
            "compte CICADA à droits d'administration (%s)", identite.id_role, compte.role_level,
        )
        raise UsersHubErreur(
            _("Cette adresse est celle d'un compte CICADA à droits d'administration : il ne "
              "peut pas être relié automatiquement à un compte UsersHub. Contactez un "
              "super administrateur."),
            status_code=409,
        )


def compte_pour(identite):
    """
    Compte CICADA de la personne : retrouvé par id UsersHub, sinon par email,
    sinon créé. Lève UsersHubErreur si le compte ne peut pas être utilisé.

    Les droits locaux (rôle, référents, sites, plans) ne sont jamais touchés :
    seuls l'identité et l'organisme viennent de UsersHub.
    """
    email = Role.objects.normalize_email(identite.email)

    with transaction.atomic():
        compte = (
            Role.objects.select_for_update().filter(usershub_id_role=identite.id_role).first()
            or Role.objects.select_for_update().filter(
                email__iexact=email, usershub_id_role__isnull=True, is_anonymized=False,
            ).first()
        )
        if compte is None and Role.objects.filter(email__iexact=email).exists():
            # Même email qu'un compte déjà relié à un AUTRE compte UsersHub.
            logger.error(
                "Connexion GeoNature : l'email du compte UsersHub %s est déjà relié "
                "à un autre compte UsersHub", identite.id_role,
            )
            raise UsersHubErreur(
                _("Un autre compte CICADA utilise déjà cette adresse email. "
                  "Contactez un administrateur."),
                status_code=409,
            )

        organisme = organisme_pour(identite)

        if compte is not None and compte.usershub_id_role is None:
            _verifier_adoption(compte, organisme, identite)

        if compte is None:
            compte = Role(
                email=email,
                usershub_id_role=identite.id_role,
                nom_role=identite.nom[:50] or None,
                prenom_role=identite.prenom[:50] or None,
                identifiant=identite.identifiant[:100] or None,
                id_organisme=organisme,
                role_level='utilisateur',
                active=True,
                pending_validation=False,
            )
            # Connexion par UsersHub seulement, jusqu'à ce que la personne
            # choisisse un mot de passe CICADA (« mot de passe oublié »).
            compte.set_unusable_password()
            compte.save()
            logger.info("Connexion GeoNature : compte créé (UsersHub n° %s)", identite.id_role)
            return compte

        if not compte.active or not compte.is_active:
            raise UsersHubErreur(_("Ce compte est désactivé."), status_code=403)
        if compte.pending_validation:
            raise UsersHubErreur(
                _("Votre compte est en attente de validation par un administrateur. "
                  "Vous recevrez un email lorsque votre compte sera activé."),
                status_code=403,
            )

        compte.usershub_id_role = identite.id_role
        if identite.nom:
            compte.nom_role = identite.nom[:50]
        if identite.prenom:
            compte.prenom_role = identite.prenom[:50]
        if compte.email.lower() != email.lower():
            if Role.objects.filter(email__iexact=email).exclude(pk=compte.pk).exists():
                logger.warning(
                    "Connexion GeoNature : nouvel email du compte UsersHub %s déjà pris "
                    "par un autre compte — email CICADA conservé", identite.id_role,
                )
            else:
                compte.email = email
        # UsersHub fait foi sur l'organisme, mais une fiche absente ne retire
        # pas celui déjà connu.
        if organisme is not None and organisme.uuid_organisme != compte.id_organisme_id:
            if compte.rang() >= 1 and compte.id_organisme_id:
                # Un administrateur déplacé dans UsersHub deviendrait
                # administrateur de l'autre organisme sans que personne ne l'ait
                # décidé dans CICADA (ce que _verifier_adoption refuse déjà au
                # premier rattachement) : son organisme ne change qu'ici.
                logger.warning(
                    "Connexion GeoNature : organisme UsersHub changé pour le compte élevé %s "
                    "— organisme CICADA conservé", compte.pk,
                )
            else:
                compte.id_organisme = organisme
        compte.save()
        return compte
