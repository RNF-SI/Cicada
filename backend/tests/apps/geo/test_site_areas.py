"""
Tests du rattachement administratif des sites (apps.geo).

La logique de rattachement est testée sur un référentiel synthétique (deux
départements carrés dans une région), ce qui rend les assertions lisibles et
les tests rapides. Un unique test — marqué `slow` — rejoue l'import réel pour
vérifier que le GeoJSON embarqué est exploitable.
"""

from unittest.mock import patch

import pytest
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.core.management import call_command

from apps.geo.models import AreaType, CorSiteArea, LArea
from apps.geo.services import compute_areas_for_site, refresh_site_areas
from tests.factories.users import SiteFactory


def carre(xmin, ymin, xmax, ymax):
    """MultiPolygon rectangulaire en EPSG:4326."""
    return MultiPolygon(
        Polygon.from_bbox((xmin, ymin, xmax, ymax)), srid=4326
    )


@pytest.fixture
def referentiel(db):
    """Une région couvrant deux départements accolés, de 0° à 10°."""
    type_dep = AreaType.objects.create(
        type_code=AreaType.DEPARTEMENT, type_name='Département'
    )
    type_reg = AreaType.objects.create(
        type_code=AreaType.REGION, type_name='Région'
    )
    region = LArea.objects.create(
        id_type=type_reg, area_code='R1', area_name='Région Un',
        geom=carre(0, 0, 10, 10),
    )
    ouest = LArea.objects.create(
        id_type=type_dep, area_code='D1', area_name='Département Ouest',
        geom=carre(0, 0, 5, 10), parent=region,
    )
    est = LArea.objects.create(
        id_type=type_dep, area_code='D2', area_name='Département Est',
        geom=carre(5, 0, 10, 10), parent=region,
    )
    return {'region': region, 'ouest': ouest, 'est': est}


def codes(site):
    """Codes des zones rattachées à un site."""
    return set(
        CorSiteArea.objects.filter(id_site=site)
        .values_list('id_area__area_code', flat=True)
    )


@pytest.mark.unit
class TestRattachementParIntersection:

    def test_site_dans_un_seul_departement(self, referentiel):
        site = SiteFactory(geom=carre(1, 1, 2, 2), geom_pt=Point(1.5, 1.5, srid=4326))

        assert codes(site) == {'D1', 'R1'}

    def test_site_a_cheval_sur_deux_departements(self, referentiel):
        site = SiteFactory(geom=carre(4, 1, 6, 2), geom_pt=Point(5, 1.5, srid=4326))

        # Les deux départements, mais la région une seule fois.
        assert codes(site) == {'D1', 'D2', 'R1'}
        assert CorSiteArea.objects.filter(
            id_site=site, id_area__area_code='R1'
        ).count() == 1

    def test_toutes_les_lignes_sont_marquees_intersect(self, referentiel):
        site = SiteFactory(geom=carre(1, 1, 2, 2), geom_pt=Point(1.5, 1.5, srid=4326))

        sources = set(
            CorSiteArea.objects.filter(id_site=site)
            .values_list('source', flat=True)
        )
        assert sources == {CorSiteArea.SOURCE_INTERSECT}

    def test_site_sans_polygone_utilise_son_point(self, referentiel):
        site = SiteFactory(geom=None, geom_pt=Point(7, 3, srid=4326))

        assert codes(site) == {'D2', 'R1'}

    def test_site_sans_geometrie_nest_pas_rattache(self, referentiel):
        site = SiteFactory(geom=None, geom_pt=None)

        assert compute_areas_for_site(site) == []
        assert codes(site) == set()


@pytest.mark.unit
class TestRattachementDeProximite:
    """Cas des sites marins, sans intersection terrestre."""

    def test_site_au_large_rattache_au_departement_le_plus_proche(self, referentiel):
        # Juste à l'ouest du référentiel : hors de tout département.
        site = SiteFactory(
            geom=carre(-0.5, 1, -0.1, 2), geom_pt=Point(-0.3, 1.5, srid=4326),
            marin=True,
        )

        assert codes(site) == {'D1', 'R1'}
        assert set(
            CorSiteArea.objects.filter(id_site=site).values_list('source', flat=True)
        ) == {CorSiteArea.SOURCE_NEAREST}

    def test_site_trop_eloigne_nest_pas_rattache(self, referentiel):
        # Au-delà de NEAREST_MAX_DEGREES (1°) du référentiel.
        site = SiteFactory(
            geom=carre(-20, 1, -19, 2), geom_pt=Point(-19.5, 1.5, srid=4326),
            marin=True,
        )

        assert codes(site) == set()


@pytest.mark.unit
class TestSignalGeometrie:

    def test_deplacer_un_site_recalcule_son_rattachement(self, referentiel):
        site = SiteFactory(geom=carre(1, 1, 2, 2), geom_pt=Point(1.5, 1.5, srid=4326))
        assert codes(site) == {'D1', 'R1'}

        site.geom = carre(7, 1, 8, 2)
        site.geom_pt = Point(7.5, 1.5, srid=4326)
        site.save()

        assert codes(site) == {'D2', 'R1'}

    def test_modifier_un_autre_champ_ne_declenche_pas_de_recalcul(self, referentiel):
        site = SiteFactory(geom=carre(1, 1, 2, 2), geom_pt=Point(1.5, 1.5, srid=4326))

        with patch('apps.geo.signals.refresh_site_areas') as recalcul:
            site.nom_site = 'Nouveau nom'
            site.save()

        recalcul.assert_not_called()
        assert codes(site) == {'D1', 'R1'}

    def test_echec_du_recalcul_nempeche_pas_lenregistrement(self, referentiel):
        site = SiteFactory(geom=carre(1, 1, 2, 2), geom_pt=Point(1.5, 1.5, srid=4326))

        with patch(
            'apps.geo.signals.refresh_site_areas', side_effect=RuntimeError('boom')
        ):
            site.geom = carre(7, 1, 8, 2)
            site.save()

        site.refresh_from_db()
        assert site.geom is not None


@pytest.mark.unit
class TestRattachementManuel:

    def test_un_rattachement_manuel_survit_au_recalcul(self, referentiel):
        site = SiteFactory(geom=carre(1, 1, 2, 2), geom_pt=Point(1.5, 1.5, srid=4326))
        CorSiteArea.objects.create(
            id_site=site, id_area=referentiel['est'],
            source=CorSiteArea.SOURCE_MANUAL,
        )

        refresh_site_areas(site)

        assert codes(site) == {'D1', 'D2', 'R1'}
        assert CorSiteArea.objects.get(
            id_site=site, id_area=referentiel['est']
        ).source == CorSiteArea.SOURCE_MANUAL

    def test_le_recalcul_est_idempotent(self, referentiel):
        site = SiteFactory(geom=carre(4, 1, 6, 2), geom_pt=Point(5, 1.5, srid=4326))

        refresh_site_areas(site)
        refresh_site_areas(site)

        assert CorSiteArea.objects.filter(id_site=site).count() == 3


@pytest.mark.slow
@pytest.mark.integration
class TestImportReel:
    """Vérifie que le GeoJSON embarqué produit un référentiel exploitable."""

    def test_import_du_referentiel_francais(self, db):
        call_command('import_ref_geo', '--force', '--no-link', verbosity=0)

        deps = LArea.objects.filter(id_type__type_code=AreaType.DEPARTEMENT)
        regions = LArea.objects.filter(id_type__type_code=AreaType.REGION)

        assert deps.count() == 109
        assert regions.count() == 26
        # Métropole, Corse et outre-mer sont présents.
        for code in ('01', '2A', '75', '971', '974', '988'):
            assert deps.filter(area_code=code).exists(), code
        # Tout département est rattaché à une région.
        assert not deps.filter(parent__isnull=True).exists()

    def test_un_site_parisien_est_rattache_a_paris(self, db):
        call_command('import_ref_geo', '--force', '--no-link', verbosity=0)

        site = SiteFactory(geom=None, geom_pt=Point(2.3488, 48.8534, srid=4326))

        assert '75' in codes(site)
        assert '11' in codes(site)  # Île-de-France
