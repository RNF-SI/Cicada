"""
Classe de base pour les seeders modulaires.

Chaque seeder doit heriter de BaseSeeder et implementer:
- seed(): Cree les donnees et retourne les objets crees
- reset(): Supprime les donnees de test
- get_dry_run_summary(): Retourne un resume pour le mode --dry-run
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from django.core.management.base import OutputWrapper


class BaseSeeder(ABC):
    """
    Classe abstraite de base pour tous les seeders.

    Attributs:
        name: Nom du seeder (ex: 'modules', 'users')
        dependencies: Liste des noms de seeders dont celui-ci depend
    """

    name: str = ''
    dependencies: List[str] = []

    def __init__(
        self,
        stdout: OutputWrapper,
        style: Any,
        context: 'SeederContext',
        verbosity: int = 1,
        dry_run: bool = False
    ):
        """
        Initialise le seeder.

        Args:
            stdout: Wrapper pour la sortie standard
            style: Helper Django pour le style de sortie
            context: Contexte partage entre seeders
            verbosity: Niveau de verbosité (0-3)
            dry_run: Mode simulation (aucune modification)
        """
        self.stdout = stdout
        self.style = style
        self.context = context
        self.verbosity = verbosity
        self.dry_run = dry_run
        self._created_count = 0
        self._updated_count = 0

    def log(self, message: str, style_type: Optional[str] = None) -> None:
        """
        Affiche un message sur la sortie standard.

        Args:
            message: Message a afficher
            style_type: Type de style ('SUCCESS', 'WARNING', 'ERROR', 'MIGRATE_HEADING')
        """
        if style_type:
            style_func = getattr(self.style, style_type, None)
            if style_func:
                self.stdout.write(style_func(message))
                return
        self.stdout.write(message)

    def log_verbose(self, message: str) -> None:
        """
        Affiche un message uniquement si verbosity >= 2.

        Args:
            message: Message a afficher
        """
        if self.verbosity >= 2:
            self.stdout.write(message)

    def log_header(self, title: str) -> None:
        """
        Affiche un header de section.

        Args:
            title: Titre de la section
        """
        self.log(f'\n--- {title} ---')

    def log_item(self, status: str, description: str) -> None:
        """
        Affiche un item avec son statut.

        Args:
            status: Statut ('CREE', 'EXISTANT', 'MISE A JOUR', etc.)
            description: Description de l'item
        """
        self.log_verbose(f"  [{status.upper()}] {description}")

    def log_summary(self, count: int, item_name: str) -> None:
        """
        Affiche un resume du nombre d'items crees.

        Args:
            count: Nombre d'items
            item_name: Nom des items (pluriel)
        """
        self.log(f'  {count} {item_name}', 'SUCCESS')

    @abstractmethod
    def seed(self) -> Any:
        """
        Cree les donnees de test.

        Returns:
            Objets crees (liste, dict, ou objet unique selon le seeder)
        """
        pass

    @abstractmethod
    def reset(self) -> int:
        """
        Supprime les donnees de test.

        Returns:
            Nombre d'objets supprimes
        """
        pass

    @abstractmethod
    def get_dry_run_summary(self) -> List[str]:
        """
        Retourne un resume des donnees qui seraient creees.

        Returns:
            Liste de lignes a afficher
        """
        pass

    def print_dry_run_summary(self) -> None:
        """
        Affiche le resume du mode dry-run.
        """
        for line in self.get_dry_run_summary():
            self.stdout.write(line)


# Import SeederContext ici pour eviter l'import circulaire
from .context import SeederContext
