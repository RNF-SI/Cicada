"""Un document déposé ne s'exécute jamais dans l'application.

Une image SVG peut porter du script ; ouverte « en ligne » sur l'origine de
l'application, elle s'exécute avec la session de qui l'ouvre. Les trois points
de service (documents du plan, d'un enjeu, adresse publique) la font
télécharger, isolent tout ce qui n'est pas un PDF (``CSP: sandbox``) et
interdisent au navigateur de deviner un autre type (``nosniff``). Le type vient
de l'extension enregistrée au dépôt, pas du nom du fichier, renommable.
"""
import pytest
from rest_framework.test import APIClient

from apps.core.models import SiteConfiguration
from tests.factories.plans import CorPgFichierFactory, PlanGestionFactory
from tests.factories.users import SuperAdminFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

SVG_PIEGE = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


@pytest.fixture
def fichiers(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    (tmp_path / 'carte.svg').write_bytes(SVG_PIEGE)
    (tmp_path / 'arrete.pdf').write_bytes(b'%PDF-1.4')
    plan = PlanGestionFactory(statut='valide')
    SiteConfiguration.objects.create(federation_partage=True)
    svg = CorPgFichierFactory(
        plan_de_gestion=plan, nom_fichier='carte.svg', chemin_fichier='carte.svg',
        extension='.svg', type_fichier='document', public=True)
    pdf = CorPgFichierFactory(
        plan_de_gestion=plan, nom_fichier='arrete.pdf', chemin_fichier='arrete.pdf',
        extension='.pdf', type_fichier='document', public=True)
    return svg, pdf


def _admin():
    client = APIClient()
    client.force_authenticate(SuperAdminFactory())
    return client


@pytest.mark.parametrize('url', [
    lambda f: f'/api/plans/fichiers/{f.pk}/download/',
    lambda f: f'/api/public/documents/{f.uuid_public}/',
])
def test_un_svg_se_telecharge_et_reste_isole(fichiers, url):
    svg, _ = fichiers
    reponse = _admin().get(url(svg))
    assert reponse.status_code == 200
    assert reponse['Content-Disposition'].startswith('attachment')
    assert reponse['X-Content-Type-Options'] == 'nosniff'
    assert 'sandbox' in reponse['Content-Security-Policy']


def test_un_pdf_s_ouvre_toujours_en_ligne(fichiers):
    _, pdf = fichiers
    reponse = _admin().get(f'/api/plans/fichiers/{pdf.pk}/download/')
    assert reponse['Content-Disposition'].startswith('inline')
    assert reponse['Content-Type'] == 'application/pdf'


def test_renommer_un_svg_en_png_ne_l_ouvre_pas_en_ligne(fichiers):
    svg, _ = fichiers
    svg.nom_fichier = 'carte.png'
    svg.save()
    reponse = _admin().get(f'/api/plans/fichiers/{svg.pk}/download/')
    assert reponse['Content-Disposition'].startswith('attachment')
    assert reponse['Content-Type'] == 'image/svg+xml'
