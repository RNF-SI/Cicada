"""
#780 — l'index porte les codes de référentiel des objets, et l'exploration
relie les versions : une action publiée « EI3 » (Eden 62) compte dans la
catégorie Gestref « CS » si EI3 devient CS.1 ; `types_action=CS.1` la retrouve.
Même calcul que le hub (parité de `filters.py`).
"""
import csv
import json

import pytest
from django.http import QueryDict

from apps.search import equivalences
from apps.search.filters import q_sous_types
from apps.search.indexing import index_plan
from apps.search.models import ContenuIndexe
from tests.factories.core import NomenclatureFactory, TypeNomenclatureFactory
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, MetriqueFactory, NiveauExigenceFactory,
    ObjectifLongTermeFactory, OperationFactory,
)
from tests.factories.plans import PlanGestionFactory


@pytest.fixture
def donnees(tmp_path, monkeypatch):
    d = tmp_path / 'referentiels_types_action' / 'gestref_v1'
    d.mkdir(parents=True)
    (d / 'version.json').write_text(json.dumps({'code': 'GESTREF_V1', 'libelle': 'Gestref V1',
                                                'depuis': 'EDEN62'}), encoding='utf-8')
    with open(d / 'correspondance.csv', 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([['ancien_code', 'nouveau_code', 'confiance', 'options', 'note'],
                                 ['EI3', 'CS.1', 'a_arbitrer', 'CS.1|CS.10', ''],
                                 ['IP1', 'IP.2', 'sure', '', '']])
    monkeypatch.setattr(equivalences, 'DONNEES', tmp_path)
    equivalences._graphe.cache_clear()
    yield tmp_path
    equivalences._graphe.cache_clear()


def test_equivalences(donnees):
    # CS.1 retrouve EI3 (qui peut devenir CS.1), pas CS.10, autre type Gestref.
    assert equivalences.equivalents('TYPE_ACTION', ['CS.1']) == {'CS.1', 'EI3'}
    assert equivalences.codes_des_categories(['CS']) == {'EI3'}
    assert equivalences.codes_des_categories(['EI']) == {'CS.1', 'CS.10'}


@pytest.mark.django_db
def test_index_porte_le_code_du_type(donnees):
    t = TypeNomenclatureFactory(mnemonique='TYPE_ACTION')
    type_ei3 = NomenclatureFactory(id_type=t, cd_nomenclature='EI3', mnemonique='EI3', label='Étude')
    plan = PlanGestionFactory(statut='valide')
    met = MetriqueFactory(id_indicateur=IndicateurFactory(id_ne=NiveauExigenceFactory(
        id_olt=ObjectifLongTermeFactory(id_enjeu=EnjeuFactory(id_pg=plan)))))
    op = OperationFactory(metriques=[met], id_type_action=type_ei3)
    index_plan(plan)
    doc = ContenuIndexe.objects.get(type_contenu=ContenuIndexe.TYPE_ACTION, id_objet=op.pk)
    assert doc.codes_referentiel == ['TYPE_ACTION:EI3']

    # Le filtre « catégorie CS » (Gestref) la retrouve, comme le type CS.1.
    assert ContenuIndexe.objects.filter(
        q_sous_types(QueryDict('categories_action=CS')), pk=doc.pk).exists()
    assert ContenuIndexe.objects.filter(
        q_sous_types(QueryDict('types_action=CS.1')), pk=doc.pk).exists()
    assert not ContenuIndexe.objects.filter(
        q_sous_types(QueryDict('categories_action=IP')), pk=doc.pk).exists()
