"""#784 — migration 0143 : intitulé d'action repris du type, sans son code."""

import importlib

import pytest
from django.apps import apps

from tests.factories.core import NomenclatureFactory, TypeNomenclatureFactory
from tests.factories.enjeux import OperationFactory

migration = importlib.import_module('apps.plans.migrations.0143_libelle_action_sans_code_type')


@pytest.mark.django_db
def test_retire_le_code_du_type_et_garde_les_intitules_saisis():
    t = TypeNomenclatureFactory(mnemonique='TYPE_ACTION')
    veille = NomenclatureFactory(id_type=t, cd_nomenclature='SP.1.5', mnemonique='SP.1.5',
                                 label='Veille juridique')
    # Ancien référentiel (Eden 62), type depuis remplacé : motif reconnu aussi.
    NomenclatureFactory(id_type=t, cd_nomenclature='SP3', mnemonique='SP3', label='Veille')
    auto = OperationFactory(libelle='SP.1.5 - Veille juridique', id_type_action=veille)
    ancien = OperationFactory(libelle='SP3 - Veille', id_type_action=veille)
    saisi = OperationFactory(libelle='SP.1.5 - Veille juridique du site', id_type_action=veille)

    migration.retirer_code(apps, None)

    for op in (auto, ancien, saisi):
        op.refresh_from_db()
    assert auto.libelle == 'Veille juridique'
    assert ancien.libelle == 'Veille'
    assert saisi.libelle == 'SP.1.5 - Veille juridique du site'
