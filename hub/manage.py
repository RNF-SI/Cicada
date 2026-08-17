#!/usr/bin/env python
"""Utilitaire en ligne de commande du hub d'exploration."""

import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django est introuvable. L'environnement virtuel est-il activé ?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
