"""
Documents des plans dans l'exploration (#747).

Le hub ne stocke que l'**adresse** d'un document, jamais le fichier : recopier
les pièces jointes de toutes les instances le rendrait énorme et dupliquerait
des documents qui vivent déjà quelque part. La fiche publiée porte donc, pour
chaque document, un lien vers l'instance d'origine, qui le sert **sans
connexion** — le lecteur vient d'une autre instance et n'a pas de compte ici.

Trois règles en découlent :

- l'adresse repose sur un identifiant tiré au sort (`uuid_public`), pas sur la
  clé du fichier en base : quiconque la connaît peut télécharger le document,
  elle ne doit pas se deviner en incrémentant un numéro ;
- l'accès anonyme fait partie du consentement au partage
  (`SiteConfiguration.federation_partage`) : décocher le partage le coupe,
  comme il retire les plans du hub. Sans partage, l'exploration reste locale et
  ne montre que les documents de cette instance, à ses utilisateurs connectés ;
- un brouillon n'est pas explorable : ses documents ne sortent pas.
"""

import mimetypes
import os

from django.conf import settings
from django.http import FileResponse, Http404

from apps.core.models import SiteConfiguration
from apps.plans.models import CorPgFichier
from apps.plans.models_enjeux import CorEnjeuFichier

from .indexing import INDEXED_STATUSES

#: Ouverts dans le navigateur plutôt que téléchargés.
EXTENSIONS_EN_LIGNE = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'}


def chemin_document(uuid_public):
    """Chemin relatif à la racine de l'API de l'adresse publique d'un document."""
    return f'/api/public/documents/{uuid_public}/'


def url_document(uuid_public):
    """
    Adresse publique d'un document, absolue dès que l'instance connaît la sienne.

    Absolue parce que la fiche voyage : servie par le hub, elle est ouverte
    depuis une autre instance, où une adresse relative pointerait chez le
    lecteur et non chez l'instance d'origine.
    """
    racine = (settings.CICADA_PUBLIC_URL or '').rstrip('/')
    return f'{racine}{chemin_document(uuid_public)}'


def trouver_document(uuid_public):
    """
    `(nom_fichier, chemin, extension)` du document explorable portant cet
    identifiant, ou `Http404`.

    Le document doit appartenir à un plan explorable (validé, modifié,
    archivé). Un document papier d'enjeu n'a pas de fichier : 404.
    """
    fichier = (
        CorPgFichier.objects
        .filter(uuid_public=uuid_public, plan_de_gestion__statut__in=INDEXED_STATUSES)
        .first()
    )
    if fichier is None:
        fichier = (
            CorEnjeuFichier.objects
            .filter(
                uuid_public=uuid_public, support='numerique',
                id_enjeu__id_pg__statut__in=INDEXED_STATUSES,
            )
            .first()
        )
    if fichier is None or not fichier.chemin_fichier:
        raise Http404
    return fichier.nom_fichier, fichier.chemin_fichier, fichier.extension


def acces_autorise(user):
    """Anonyme si la structure partage ses plans ; connecté à l'instance sinon."""
    if user is not None and user.is_authenticated:
        return True
    configuration = SiteConfiguration.objects.first()
    return bool(configuration and configuration.federation_partage)


def servir(nom_fichier, chemin, extension):
    if not os.path.isabs(chemin):
        chemin = os.path.join(settings.MEDIA_ROOT, chemin)
    if not os.path.exists(chemin):
        raise Http404
    content_type = mimetypes.guess_type(nom_fichier)[0] or 'application/octet-stream'
    en_ligne = (extension or '').lower().lstrip('.') in EXTENSIONS_EN_LIGNE
    return FileResponse(
        open(chemin, 'rb'),
        content_type=content_type,
        as_attachment=not en_ligne,
        filename=nom_fichier,
    )
