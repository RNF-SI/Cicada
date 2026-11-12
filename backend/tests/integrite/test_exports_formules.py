"""Un libellé saisi ne devient jamais une formule active dans un export Excel.

openpyxl range en formule toute chaîne qui commence par « = » : « =HYPERLINK(…) »
saisi comme nom d'enjeu s'exécutait à l'ouverture de l'export par un autre.
"""
import io

import pytest
from openpyxl import load_workbook

from apps.plans.export_theme import neutraliser_formules
from apps.plans.services_export_arbo import build_presentation_workbook
from apps.plans.services_import import build_arborescence_workbook
from tests.factories.enjeux import EnjeuFactory
from tests.factories.plans import PlanGestionFactory

pytestmark = [pytest.mark.django_db]

PIEGE = '=HYPERLINK("http://exemple.invalid","Cliquez")'


def _formules(contenu):
    classeur = load_workbook(io.BytesIO(contenu))
    return [
        (feuille.title, cellule.coordinate)
        for feuille in classeur.worksheets
        for ligne in feuille.iter_rows()
        for cellule in ligne
        if cellule.data_type == 'f'
    ]


@pytest.mark.parametrize('construire', [build_arborescence_workbook, build_presentation_workbook])
def test_un_libelle_piege_reste_du_texte(construire):
    plan = PlanGestionFactory()
    EnjeuFactory(id_pg=plan, libelle=PIEGE)
    contenu = construire(plan)
    assert _formules(contenu) == []
    # Le libellé reste lisible, en texte.
    assert any(
        'HYPERLINK' in str(cellule.value or '')
        for feuille in load_workbook(io.BytesIO(contenu)).worksheets
        for ligne in feuille.iter_rows() for cellule in ligne
    )


def test_neutraliser_formules_repasse_en_texte():
    from openpyxl import Workbook
    classeur = Workbook()
    classeur.active['A1'] = '=1+1'
    assert classeur.active['A1'].data_type == 'f'
    neutraliser_formules(classeur)
    assert classeur.active['A1'].data_type == 's'
