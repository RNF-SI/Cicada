"""
Package des seeders modulaires pour la commande seed_testdata.

Ce package contient:
- BaseSeeder: Classe de base pour tous les seeders
- SeederContext: Contexte de partage de donnees entre seeders
- signals_disabled: Context manager pour gerer les signaux
- SEEDER_CLASSES: Liste ordonnee des seeders par dependances

Usage:
    from seeders import SEEDER_CLASSES, SeederContext, signals_disabled

    context = SeederContext()
    for seeder_class in SEEDER_CLASSES:
        seeder = seeder_class(stdout, style, context, verbosity)
        seeder.seed()
"""
from typing import List, Type

from .base import BaseSeeder
from .context import SeederContext
from .signals import signals_disabled, disconnect_all_signals, reconnect_all_signals

# Import des seeders individuels
from .modules_seeder import ModulesSeeder
from .groups_seeder import GroupsSeeder
from .organismes_seeder import OrganismesSeeder
from .sites_seeder import SitesSeeder
from .users_seeder import UsersSeeder
from .plans_seeder import PlansSeeder
from .enjeux_seeder import EnjeuxSeeder
from .pending_users_seeder import PendingUsersSeeder
from .validation_requests_seeder import ValidationRequestsSeeder
from .notifications_seeder import NotificationsSeeder
from .error_logs_seeder import ErrorLogsSeeder
from .activity_logs_seeder import ActivityLogsSeeder


# Liste ordonnee des seeders par dependances (tri topologique)
# Les seeders sans dependances sont en premier
SEEDER_CLASSES: List[Type[BaseSeeder]] = [
    # Phase 1: Seeders independants
    ModulesSeeder,
    GroupsSeeder,
    OrganismesSeeder,

    # Phase 2: Seeders avec dependances simples
    SitesSeeder,         # deps: organismes
    UsersSeeder,         # deps: organismes, sites, groups
    PlansSeeder,         # deps: users, sites
    EnjeuxSeeder,        # deps: plans
    PendingUsersSeeder,  # deps: organismes

    # Phase 3: Seeders complexes
    ValidationRequestsSeeder,  # deps: users, sites, plans, organismes
    NotificationsSeeder,       # deps: users, sites, plans, organismes, validation_requests
    ErrorLogsSeeder,           # deps: users
    ActivityLogsSeeder,        # deps: users, sites, plans, organismes, validation_requests
]

# Mapping nom -> classe pour --only
SEEDER_REGISTRY = {seeder.name: seeder for seeder in SEEDER_CLASSES}


def validate_dependencies() -> bool:
    """
    Verifie que toutes les dependances sont satisfaites.

    Returns:
        True si toutes les dependances sont valides

    Raises:
        ValueError: Si une dependance manque ou forme un cycle
    """
    available = set()

    for seeder_class in SEEDER_CLASSES:
        for dep in seeder_class.dependencies:
            if dep not in available:
                raise ValueError(
                    f"Seeder '{seeder_class.name}' depend de '{dep}' "
                    f"qui n'est pas disponible. "
                    f"Ordre des seeders incorrect ou dependance manquante."
                )
        available.add(seeder_class.name)

    return True


def get_seeder_by_name(name: str) -> Type[BaseSeeder]:
    """
    Recupere une classe de seeder par son nom.

    Args:
        name: Nom du seeder

    Returns:
        Classe du seeder

    Raises:
        KeyError: Si le seeder n'existe pas
    """
    if name not in SEEDER_REGISTRY:
        available = ', '.join(SEEDER_REGISTRY.keys())
        raise KeyError(
            f"Seeder '{name}' non trouve. "
            f"Seeders disponibles: {available}"
        )
    return SEEDER_REGISTRY[name]


def get_seeders_with_dependencies(names: List[str]) -> List[Type[BaseSeeder]]:
    """
    Recupere les seeders demandes avec leurs dependances dans le bon ordre.

    Args:
        names: Liste des noms de seeders demandes

    Returns:
        Liste ordonnee des classes de seeders incluant les dependances
    """
    # Ensemble des seeders requis (incluant les dependances)
    required = set()

    def add_with_deps(name: str):
        if name in required:
            return
        seeder_class = get_seeder_by_name(name)
        for dep in seeder_class.dependencies:
            add_with_deps(dep)
        required.add(name)

    for name in names:
        add_with_deps(name)

    # Filtrer SEEDER_CLASSES pour garder l'ordre
    return [s for s in SEEDER_CLASSES if s.name in required]


__all__ = [
    'BaseSeeder',
    'SeederContext',
    'signals_disabled',
    'disconnect_all_signals',
    'reconnect_all_signals',
    'SEEDER_CLASSES',
    'SEEDER_REGISTRY',
    'validate_dependencies',
    'get_seeder_by_name',
    'get_seeders_with_dependencies',
    # Seeders individuels
    'ModulesSeeder',
    'GroupsSeeder',
    'OrganismesSeeder',
    'SitesSeeder',
    'UsersSeeder',
    'PlansSeeder',
    'EnjeuxSeeder',
    'PendingUsersSeeder',
    'ValidationRequestsSeeder',
    'NotificationsSeeder',
    'ErrorLogsSeeder',
    'ActivityLogsSeeder',
]
