"""
Factories for users app models.
Uses Factory Boy for test data generation.
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.gis.geos import Point, MultiPolygon, Polygon

from apps.users.models import Role, BibOrganismes, Site, CorRoleSite, CorOgSite


class OrganismeFactory(DjangoModelFactory):
    """Factory for BibOrganismes model."""

    class Meta:
        model = BibOrganismes

    nom_organisme = factory.Sequence(lambda n: f'Organisme Test {n}')
    email_organisme = factory.LazyAttribute(
        lambda obj: f'{obj.nom_organisme.lower().replace(" ", ".")}@test.fr'
    )
    adresse_organisme = factory.Faker('address', locale='fr_FR')
    cp_organisme = factory.Faker('postcode', locale='fr_FR')
    ville_organisme = factory.Faker('city', locale='fr_FR')


class RoleFactory(DjangoModelFactory):
    """
    Factory for Role (User) model.
    Creates a basic 'utilisateur' level user by default.
    """

    class Meta:
        model = Role

    email = factory.Sequence(lambda n: f'user{n}@test.fr')
    nom_role = factory.Faker('last_name', locale='fr_FR')
    prenom_role = factory.Faker('first_name', locale='fr_FR')
    identifiant = factory.LazyAttribute(lambda obj: obj.email.split('@')[0])
    role_level = 'utilisateur'
    active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set password after user creation."""
        self.set_password(extracted or 'TestPassword123!')
        if create:
            self.save()


# Alias for clarity
UserFactory = RoleFactory


class SuperAdminFactory(RoleFactory):
    """Factory for super admin users."""

    role_level = 'super_admin'
    is_staff = True
    is_superuser = True
    email = factory.Sequence(lambda n: f'superadmin{n}@test.fr')


class AdminOrganismeFactory(RoleFactory):
    """Factory for organisme admin users."""

    role_level = 'admin_og'
    is_staff = True
    id_organisme = factory.SubFactory(OrganismeFactory)
    email = factory.Sequence(lambda n: f'adminog{n}@test.fr')


class ReferentFactory(RoleFactory):
    """Factory for referent users."""

    role_level = 'referent'
    id_organisme = factory.SubFactory(OrganismeFactory)
    email = factory.Sequence(lambda n: f'referent{n}@test.fr')


class SiteFactory(DjangoModelFactory):
    """Factory for Site model."""

    class Meta:
        model = Site

    nom_site = factory.Sequence(lambda n: f'Site Test {n}')
    id_local = factory.Sequence(lambda n: f'SITE{n:04d}')
    surf_off = factory.Faker('pyfloat', min_value=10.0, max_value=10000.0)
    active = True
    marin = False
    outre_mer = False

    @factory.lazy_attribute
    def geom_pt(self):
        """Generate a random point in France."""
        # Random point near center of France
        import random
        lon = random.uniform(2.0, 3.0)
        lat = random.uniform(46.0, 47.0)
        return Point(lon, lat, srid=4326)

    @factory.lazy_attribute
    def geom(self):
        """Generate a simple polygon geometry."""
        # Create a small square polygon around a point
        import random
        center_lon = random.uniform(2.0, 3.0)
        center_lat = random.uniform(46.0, 47.0)
        offset = 0.01  # ~1km

        coords = [
            (center_lon - offset, center_lat - offset),
            (center_lon + offset, center_lat - offset),
            (center_lon + offset, center_lat + offset),
            (center_lon - offset, center_lat + offset),
            (center_lon - offset, center_lat - offset),  # Close the ring
        ]
        polygon = Polygon(coords, srid=4326)
        return MultiPolygon(polygon, srid=4326)


class SiteWithoutGeomFactory(SiteFactory):
    """Factory for Site without geometry (for simpler tests)."""

    geom = None
    geom_pt = None


class CorRoleSiteFactory(DjangoModelFactory):
    """Factory for CorRoleSite (user-site relationship)."""

    class Meta:
        model = CorRoleSite

    id_role = factory.SubFactory(RoleFactory)
    id_site = factory.SubFactory(SiteFactory)
    referent = False
    referent_valid = False
    conservateur = False


class CorOgSiteFactory(DjangoModelFactory):
    """Factory for CorOgSite (organisme-site relationship)."""

    class Meta:
        model = CorOgSite

    id_site = factory.SubFactory(SiteFactory)
    uuid_og = factory.SubFactory(OrganismeFactory)
    principal = False
