"""
Version de l'application CICADA.

Deux sources, dans cet ordre :
1. CICADA_APP_VERSION — injectée dans l'image au build (#646). Le contexte de
   build du backend est ``./backend`` : version.txt, qui vit à la racine du
   dépôt, n'entre donc jamais dans l'image de production.
2. version.txt — en dev (monté par docker-compose) et hors conteneur.
"""
import os
from pathlib import Path


def _read_version():
    """Version de l'instance, ou "0.0.0" si aucune source n'est disponible."""
    from_env = os.environ.get("CICADA_APP_VERSION", "").strip()
    if from_env:
        return from_env

    for path in [
        Path(__file__).resolve().parent.parent.parent / "version.txt",  # dev: backend/../version.txt
        Path("/app/version.txt"),  # Docker (monté en dev, copié si présent)
    ]:
        if path.exists():
            return path.read_text().strip()
    return "0.0.0"


__version__ = _read_version()
