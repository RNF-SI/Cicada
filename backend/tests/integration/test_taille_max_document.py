"""
#745 — Taille maximale d'un document déposé dans un plan de gestion.

Réglée par l'administrateur de l'instance (Administration > Paramètres),
20 Mo par défaut. Elle s'applique aux documents du plan et à ceux d'un
enjeu : tout ce qui se dépose dans un plan.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.core.models import SiteConfiguration
from tests.factories.enjeux import EnjeuFactory
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import AdminOrganismeFactory, SuperAdminFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

MO = 1024 * 1024


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def client(user=None):
    c = APIClient()
    if user:
        c.force_authenticate(user=user)
    return c


def limite(mo):
    config = SiteConfiguration.get_instance()
    config.taille_max_document_mo = mo
    config.save()


def fichier(taille, nom='doc.pdf'):
    return SimpleUploadedFile(nom, b'x' * taille, content_type='application/pdf')


def test_20_mo_par_defaut_et_public():
    assert client().get('/api/settings/').json()['taille_max_document_mo'] == 20


def test_reglable_par_le_super_admin():
    reponse = client(SuperAdminFactory()).patch(
        '/api/settings/', {'taille_max_document_mo': 50}, format='json')
    assert reponse.status_code == 200
    assert SiteConfiguration.get_instance().taille_max_document_mo == 50


def test_reservee_au_super_admin():
    reponse = client(AdminOrganismeFactory()).patch(
        '/api/settings/', {'taille_max_document_mo': 50}, format='json')
    assert reponse.status_code == 403


@pytest.mark.parametrize('valeur', [0, -1, 1025])
def test_bornes(valeur):
    reponse = client(SuperAdminFactory()).patch(
        '/api/settings/', {'taille_max_document_mo': valeur}, format='json')
    assert reponse.status_code == 400


def test_document_du_plan_au_dela_de_la_limite_refuse():
    limite(1)
    plan = PlanGestionFactory(statut='draft')
    reponse = client(SuperAdminFactory()).post('/api/plans/fichiers/', {
        'plan_de_gestion': plan.id_pg, 'nom_fichier': 'doc.pdf', 'fichier': fichier(MO + 1),
    }, format='multipart')
    assert reponse.status_code == 400
    assert '1 Mo' in str(reponse.json()['fichier'])


def test_document_du_plan_dans_la_limite_accepte():
    limite(1)
    plan = PlanGestionFactory(statut='draft')
    reponse = client(SuperAdminFactory()).post('/api/plans/fichiers/', {
        'plan_de_gestion': plan.id_pg, 'nom_fichier': 'doc.pdf', 'fichier': fichier(MO),
    }, format='multipart')
    assert reponse.status_code == 201, reponse.content


def test_document_d_enjeu_au_dela_de_la_limite_refuse():
    limite(1)
    enjeu = EnjeuFactory(id_pg=PlanGestionFactory(statut='draft'))
    reponse = client(SuperAdminFactory()).post('/api/plans/enjeux-fichiers/', {
        'id_enjeu': enjeu.pk, 'support': 'numerique', 'fichier': fichier(MO + 1),
    }, format='multipart')
    assert reponse.status_code == 400
    assert 'fichier' in reponse.json()
