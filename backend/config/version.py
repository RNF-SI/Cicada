"""
Version de l'application CICADA
Lue depuis version.txt à la racine du projet.
"""
from pathlib import Path

def _read_version():
    """Lit la version depuis version.txt (racine du projet ou /app en Docker)."""
    # En Docker, le code est dans /app, version.txt est copié à la racine
    for path in [
        Path(__file__).resolve().parent.parent.parent / "version.txt",  # dev: backend/../version.txt
        Path("/app/version.txt"),  # Docker prod
    ]:
        if path.exists():
            return path.read_text().strip()
    return "0.0.0"

__version__ = _read_version()
