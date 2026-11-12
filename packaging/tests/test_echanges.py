"""Fichiers d'échange avec le conteneur : root ne suit jamais un lien qui y serait posé.

Le dossier /var/lib/cicada/updates appartient à l'utilisateur du conteneur web.
Un code exécuté dans le conteneur pouvait y remplacer « update_result.json »
par un lien vers un fichier système, que cicada-update (root) écrasait alors.
"""
import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'debian/usr/share/cicada/maintenance'))

from cicada_maintenance import ecrire_echange, lire_echange  # noqa: E402


def test_un_lien_pose_dans_le_dossier_n_est_pas_suivi(tmp_path):
    cible = tmp_path / 'systeme' / 'shadow'
    cible.parent.mkdir()
    cible.write_text('secret')
    echanges = tmp_path / 'updates'
    echanges.mkdir()
    (echanges / 'update_result.json').symlink_to(cible)

    ecrire_echange(echanges / 'update_result.json', '{"statut": "reussie"}')

    assert cible.read_text() == 'secret'
    assert not (echanges / 'update_result.json').is_symlink()
    assert (echanges / 'update_result.json').read_text() == '{"statut": "reussie"}'
    assert oct(os.stat(echanges / 'update_result.json').st_mode & 0o777) == '0o644'


def test_la_lecture_refuse_un_lien(tmp_path):
    cible = tmp_path / 'shadow'
    cible.write_text('secret')
    lien = tmp_path / 'update_trigger.json'
    lien.symlink_to(cible)
    with pytest.raises(OSError):
        lire_echange(lien)


def test_aucun_fichier_temporaire_ne_reste(tmp_path):
    ecrire_echange(tmp_path / 'backups.json', '{}')
    assert sorted(p.name for p in tmp_path.iterdir()) == ['backups.json']
