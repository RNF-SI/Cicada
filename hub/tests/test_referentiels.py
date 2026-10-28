"""
#780 — le hub garde toutes les versions des référentiels et leurs
correspondances, et relie les codes d'une version à l'autre dans la recherche :
une action publiée « EI3 » (Eden 62) par une instance compte dans la catégorie
Gestref « CS » ; filtrer le type « CS.1 » la retrouve aussi.
"""
import csv
import json

import pytest

from apps.index import equivalences
from apps.index.models import ContenuIndexe
from apps.nomenclatures.management.commands.import_referentiels import importer
from apps.nomenclatures.models import CorrespondanceReferentiel, VersionReferentiel
from tests.test_exploration import lecture_autorisee, lire, publier_plan  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.fixture
def referentiels(tmp_path):
    d = tmp_path / 'referentiels_types_action' / 'gestref_v1'
    d.mkdir(parents=True)
    (d / 'version.json').write_text(json.dumps(
        {'code': 'GESTREF_V1', 'libelle': 'Gestref V1', 'depuis': 'EDEN62'}), encoding='utf-8')
    with open(d / 'referentiel.csv', 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([['code', 'libelle'], ['CS', 'Connaissance'], ['CS.1', 'Études'],
                                 ['IP', 'Interventions'], ['IP.2', 'Habitats']])
    with open(d / 'correspondance.csv', 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([['ancien_code', 'nouveau_code', 'confiance', 'options', 'note'],
                                 ['EI3', 'CS.1', 'a_arbitrer', '', ''],
                                 ['IP1', 'IP.2', 'sure', '', '']])
    importer(tmp_path)
    return tmp_path


def test_import_garde_les_versions(referentiels):
    v = VersionReferentiel.objects.get(referentiel='TYPE_ACTION', code='GESTREF_V1')
    assert v.depuis == 'EDEN62' and v.lignes.count() == 4
    assert CorrespondanceReferentiel.objects.count() == 2
    # Réimporter ne duplique rien ; une version absente d'une livraison reste.
    importer(referentiels)
    assert CorrespondanceReferentiel.objects.count() == 2


def test_equivalences(referentiels):
    assert equivalences.equivalents('TYPE_ACTION', ['CS.1']) == {'CS.1', 'EI3'}
    assert equivalences.codes_des_categories(['CS']) == {'EI3'}


def _action(code, categorie, titre):
    return {'type_contenu': ContenuIndexe.TYPE_ACTION, 'titre': titre, 'sous_type': categorie,
            'codes_referentiel': [f'TYPE_ACTION:{code}']}


def test_recherche_transverse_entre_versions(referentiels, lire):
    publier_plan('rnf', 1, contenus=[_action('CS.1', 'CS', 'Étude Gestref')])
    publier_plan('cen', 2, contenus=[_action('EI3', 'EI', 'Étude Eden 62'),
                                     _action('IP1', 'IP', 'Restauration Eden 62')])
    titres = {r['titre'] for r in lire('/api/exploration/contenus/', categories_action='CS')['results']}
    assert titres == {'Étude Gestref', 'Étude Eden 62'}
    titres = {r['titre'] for r in lire('/api/exploration/contenus/', types_action='CS.1')['results']}
    assert titres == {'Étude Gestref', 'Étude Eden 62'}
