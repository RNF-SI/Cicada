"""Réponses HTTP des documents déposés (plans, enjeux, adresse publique).

Un document déposé est un contenu **non sûr** : il vient d'un utilisateur, et
s'ouvre dans le navigateur sur l'origine de l'application. Une image SVG ou une
page HTML peuvent y exécuter du script, avec l'accès à la session de qui les
ouvre. Règles communes aux trois points de service :

- ne s'ouvrent dans le navigateur que les types listés ici (PDF et images
  matricielles) ; tout le reste, SVG compris, est téléchargé ;
- le type annoncé vient de l'extension **enregistrée au dépôt**, pas du nom du
  fichier, que l'on peut renommer ensuite ;
- ``X-Content-Type-Options: nosniff`` empêche le navigateur de deviner un autre
  type ; ``Content-Security-Policy: sandbox`` isole tout ce qui n'est pas un
  PDF (la visionneuse PDF de Chrome refuse de s'afficher sous ``sandbox``).
"""
import mimetypes

EXTENSIONS_EN_LIGNE = frozenset({'pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'})


def extension_normalisee(extension):
    return (extension or '').lower().lstrip('.')


def type_du_document(extension):
    """Type MIME déduit de l'extension enregistrée au dépôt."""
    ext = extension_normalisee(extension)
    return (mimetypes.guess_type(f'document.{ext}')[0] if ext else None) or 'application/octet-stream'


def s_ouvre_en_ligne(extension):
    return extension_normalisee(extension) in EXTENSIONS_EN_LIGNE


def securiser(reponse, extension):
    """Pose les en-têtes qui empêchent un document d'agir sur l'application."""
    reponse['X-Content-Type-Options'] = 'nosniff'
    if extension_normalisee(extension) != 'pdf':
        reponse['Content-Security-Policy'] = "sandbox; default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'"
    return reponse
