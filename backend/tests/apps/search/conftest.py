"""Décor commun des tests de l'exploration et de la fédération (#636)."""

import pytest


@pytest.fixture(autouse=True)
def instance_nommee(settings):
    """
    Donne un nom à l'instance, comme l'installeur l'impose désormais.

    `push_federation` refuse de publier sans `CICADA_INSTANCE_LABEL` : c'est ce
    nom qui s'affiche chez les autres structures comme provenance. En dev, le
    `.env` le renseigne ; en CI il est vide, et tous les tests de publication
    échouaient sur ce refus au lieu de vérifier ce qu'ils visent. Un test qui
    porte précisément sur le nom absent le vide lui-même.
    """
    if not (settings.CICADA_INSTANCE_LABEL or '').strip():
        settings.CICADA_INSTANCE_LABEL = 'Instance de test'
