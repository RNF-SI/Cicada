"""
#778 — page « Référentiels de données » : version en service et téléchargement
CSV de Gestref (types d'action), PressRef, TaxRef et HabRef.
"""
import csv
import io

import pytest

from apps.core.models import Nomenclature, TypeNomenclature
from apps.taxonomy.models import Taxref, TMetaTaxref
from tests.factories.users import RoleFactory


@pytest.fixture
def donnees(db):
    TMetaTaxref.objects.create(referential_name='TAXREF', version='18')
    for mnemo, code, label in (('TYPE_ACTION', 'IP1', 'Restauration'), ('TYPE_PRESSION', '1.1', 'Perte')):
        t, _ = TypeNomenclature.objects.get_or_create(mnemonique=mnemo, defaults={'label': mnemo})
        Nomenclature.objects.update_or_create(id_type=t, cd_nomenclature=code,
                                              defaults={'label': label, 'actif': True})
    Taxref.objects.create(cd_nom=4001, cd_ref=4001, nom_complet='Bufo bufo (Linnaeus, 1758)',
                          lb_nom='Bufo bufo', nom_vern='Crapaud commun')


def _csv(response):
    contenu = b''.join(response.streaming_content).decode('utf-8-sig')
    return list(csv.reader(io.StringIO(contenu), delimiter=';'))


@pytest.mark.django_db
def test_liste_et_telechargements(api_client, donnees):
    api_client.force_authenticate(user=RoleFactory())
    r = api_client.get('/api/plans/referentiels/donnees/')
    assert r.status_code == 200
    par_code = {x['code']: x for x in r.data['referentiels']}
    assert set(par_code) == {'TYPE_ACTION', 'PRESSREF', 'TAXREF', 'HABREF'}
    assert par_code['TAXREF']['version']['libelle'] == 'TaxRef v18'
    assert par_code['TYPE_ACTION']['version']['code'] == 'EDEN62'
    assert par_code['TAXREF']['source_url'].startswith('https://inpn.mnhn.fr')

    lignes = _csv(api_client.get('/api/plans/referentiels/donnees/TYPE_ACTION/csv/'))
    assert lignes[0][:2] == ['code', 'libelle'] and ['IP1', 'Restauration'] == lignes[1][:2]
    lignes = _csv(api_client.get('/api/plans/referentiels/donnees/TAXREF/csv/'))
    assert lignes[1][:3] == ['4001', '4001', 'Bufo bufo (Linnaeus, 1758)']
    r = api_client.get('/api/plans/referentiels/donnees/TAXREF/csv/')
    assert 'taxref_v18' in r['Content-Disposition'].lower()


@pytest.mark.django_db
def test_connexion_requise(api_client, donnees):
    assert api_client.get('/api/plans/referentiels/donnees/').status_code == 401
