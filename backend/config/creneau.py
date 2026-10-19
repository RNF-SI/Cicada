"""
Créneau de publication de nuit d'une instance (#701).

Toutes les instances publiaient leur index sur le hub à 2h30 : avec le parc
visé, ce pic de dépôts simultanés saturerait le hub. Chaque instance reçoit
donc « son » créneau, dérivé de son identifiant : stable d'une nuit à l'autre
et d'un redémarrage à l'autre, réparti sans aucune coordination entre
instances.

Module sans dépendance à Django : il est lu par les réglages, avant le
chargement des applications.
"""

import hashlib

#: Fenêtre de nuit, en minutes depuis minuit : de 1h00 à 5h00 (exclu).
FENETRE_DEBUT = 60
FENETRE_FIN = 300


def creneau_publication(instance_id: str) -> tuple[int, int]:
    """(heure, minute) de la publication de nuit de cette instance.

    Un hachage et non ``hash()`` : celui de Python change à chaque lancement
    (``PYTHONHASHSEED``), le créneau changerait à chaque redémarrage.
    """
    empreinte = hashlib.sha256((instance_id or '').encode('utf-8')).digest()
    decalage = int.from_bytes(empreinte[:4], 'big') % (FENETRE_FIN - FENETRE_DEBUT)
    minutes = FENETRE_DEBUT + decalage
    return minutes // 60, minutes % 60
