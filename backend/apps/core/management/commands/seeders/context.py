"""
Contexte partage entre les seeders.

SeederContext permet aux seeders de partager des donnees
(ex: les organismes crees par OrganismesSeeder sont utilises par SitesSeeder).
"""
from typing import Any, Dict, Optional


class SeederContext:
    """
    Contexte de partage de donnees entre seeders.

    Permet de stocker et recuperer des objets crees par les seeders
    pour les reutiliser dans d'autres seeders dependants.

    Example:
        context = SeederContext()
        context.set('organismes', [org1, org2, org3])
        orgs = context.get('organismes')
        org_rnf = context.require('organismes')[0]
    """

    def __init__(self):
        """Initialise le contexte vide."""
        self._data: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """
        Stocke une valeur dans le contexte.

        Args:
            key: Cle de stockage
            value: Valeur a stocker
        """
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Recupere une valeur du contexte.

        Args:
            key: Cle de la valeur
            default: Valeur par defaut si la cle n'existe pas

        Returns:
            Valeur stockee ou valeur par defaut
        """
        return self._data.get(key, default)

    def require(self, key: str) -> Any:
        """
        Recupere une valeur requise du contexte.

        Args:
            key: Cle de la valeur

        Returns:
            Valeur stockee

        Raises:
            KeyError: Si la cle n'existe pas dans le contexte
        """
        if key not in self._data:
            raise KeyError(
                f"Cle '{key}' non trouvee dans le contexte. "
                f"Le seeder dependant doit etre execute avant celui-ci. "
                f"Cles disponibles: {list(self._data.keys())}"
            )
        return self._data[key]

    def has(self, key: str) -> bool:
        """
        Verifie si une cle existe dans le contexte.

        Args:
            key: Cle a verifier

        Returns:
            True si la cle existe
        """
        return key in self._data

    def keys(self) -> list:
        """
        Retourne toutes les cles du contexte.

        Returns:
            Liste des cles
        """
        return list(self._data.keys())

    def clear(self) -> None:
        """Vide le contexte."""
        self._data.clear()

    def __repr__(self) -> str:
        return f"SeederContext({list(self._data.keys())})"
