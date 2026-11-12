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


# --- Deuxième passe : root n'écrit jamais là où le conteneur peut poser un lien ---

from cicada_maintenance import Chemins, Instance, JOURNAUX_ROOT, nettoyer  # noqa: E402


def test_les_journaux_root_ne_sont_pas_dans_le_dossier_des_conteneurs(tmp_path):
    c = Chemins(racine=tmp_path)
    assert c.journaux == tmp_path / JOURNAUX_ROOT
    assert 'var/log/cicada/' not in str(c.journaux) + '/'


def test_le_journal_de_mise_a_jour_ne_suit_pas_un_lien(tmp_path):
    cible = tmp_path / 'root' / '.ssh' / 'authorized_keys'
    cible.parent.mkdir(parents=True)
    cible.write_text('')
    instance = Instance(chemins=Chemins(racine=tmp_path), sortie=open(os.devnull, 'w'))
    instance.c.journaux.mkdir(parents=True)
    (instance.c.journaux / 'updater.log').symlink_to(cible)
    instance.dire('Mise à jour demandée par x\nssh-ed25519 AAAA… attaquant')
    assert cible.read_text() == ''


def test_une_ligne_de_journal_n_en_fabrique_pas_une_autre(tmp_path):
    instance = Instance(chemins=Chemins(racine=tmp_path), sortie=open(os.devnull, 'w'))
    instance.dire('demandée par x\n* * * * * root sh -c evil')
    lignes = (instance.c.journaux / 'updater.log').read_text().splitlines()
    assert len(lignes) == 1
    assert nettoyer('a\r\nb\x00c', 3) == 'a  '


def test_la_lecture_refuse_un_fifo_sans_bloquer(tmp_path):
    fifo = tmp_path / 'update_trigger.json'
    os.mkfifo(fifo)
    with pytest.raises(OSError):
        lire_echange(fifo)


def test_la_lecture_refuse_un_fichier_demesure(tmp_path):
    gros = tmp_path / 'check_trigger.json'
    gros.write_bytes(b'x' * (1024 * 1024))
    with pytest.raises(OSError):
        lire_echange(gros)
