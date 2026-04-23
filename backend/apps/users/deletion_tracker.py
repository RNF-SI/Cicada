"""Suivi des sites en cours de suppression.

Pendant `site.delete()`, Django exécute d'abord les suppressions en CASCADE des
enfants (CorRoleSite, CorSitePg, ...) avant de supprimer le site lui-même. Les
signaux `post_delete` des enfants peuvent alors tenter de créer des
`ActivityLog` ou `Notification` avec `related_site=site` — lignes non prévues
par le Collector Django, qui violeront la FK au moment où le site est
effectivement supprimé.

Ce module fournit un marqueur léger pour permettre aux signaux `post_delete`
des enfants de détecter qu'ils s'exécutent dans le cadre d'une suppression en
cascade, et de sauter leur journalisation en conséquence.
"""

_sites_being_deleted: set = set()


def mark_site_deleting(site_pk: int) -> None:
    _sites_being_deleted.add(site_pk)


def unmark_site_deleting(site_pk: int) -> None:
    _sites_being_deleted.discard(site_pk)


def is_site_deleting(site_pk) -> bool:
    return site_pk in _sites_being_deleted
