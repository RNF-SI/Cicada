"""
Factories for plans app models.
Uses Factory Boy for test data generation.
"""
import factory
from factory.django import DjangoModelFactory
from datetime import datetime

from apps.plans.models import PlanGestion, CorSitePg, CorRolePlan, CorPgFichier
from tests.factories.users import RoleFactory, SiteFactory


class PlanGestionFactory(DjangoModelFactory):
    """Factory for PlanGestion model."""

    class Meta:
        model = PlanGestion

    nom = factory.Sequence(lambda n: f'Plan de Gestion Test {n}')
    statut = 'draft'
    annee_debut = factory.LazyFunction(lambda: datetime.now().year)
    annee_fin = factory.LazyFunction(lambda: datetime.now().year + 10)
    gestion_partagee = False
    ct88 = False
    risque_incendie = False
    version = '1.0'
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)

    @factory.post_generation
    def sites(self, create, extracted, **kwargs):
        """Allow adding sites via: PlanGestionFactory(sites=[site1, site2])"""
        if not create:
            return
        if extracted:
            for site in extracted:
                CorSitePg.objects.create(plan_de_gestion=self, site=site)

    @factory.post_generation
    def referents(self, create, extracted, **kwargs):
        """Allow adding referents via: PlanGestionFactory(referents=[user1, user2])"""
        if not create:
            return
        if extracted:
            for referent in extracted:
                self.referents.add(referent)


class PlanGestionValideFactory(PlanGestionFactory):
    """Factory for validated plans."""

    statut = 'valide'


class PlanGestionArchiveFactory(PlanGestionFactory):
    """Factory for archived plans."""

    statut = 'archive'


class CorSitePgFactory(DjangoModelFactory):
    """Factory for CorSitePg (plan-site relationship)."""

    class Meta:
        model = CorSitePg

    plan_de_gestion = factory.SubFactory(PlanGestionFactory)
    site = factory.SubFactory(SiteFactory)
    rang = factory.Sequence(lambda n: n)
    commentaire = ''


class CorRolePlanFactory(DjangoModelFactory):
    """Factory for CorRolePlan (user-plan relationship)."""

    class Meta:
        model = CorRolePlan

    id_role = factory.SubFactory(RoleFactory)
    plan_de_gestion = factory.SubFactory(PlanGestionFactory)
    referent = False
    commentaire = ''


class CorPgFichierFactory(DjangoModelFactory):
    """Factory for CorPgFichier (plan files)."""

    class Meta:
        model = CorPgFichier

    plan_de_gestion = factory.SubFactory(PlanGestionFactory)
    nom_fichier = factory.Sequence(lambda n: f'document_{n}.pdf')
    chemin_fichier = factory.LazyAttribute(
        lambda obj: f'/media/plans/{obj.plan_de_gestion.id_pg}/{obj.nom_fichier}'
    )
    type_fichier = 'document'
    extension = '.pdf'
    taille_fichier = 1024
    public = False
    id_utilisateur_upload = factory.SubFactory(RoleFactory)


class CorPgFichierImageFactory(CorPgFichierFactory):
    """Factory for image files."""

    nom_fichier = factory.Sequence(lambda n: f'image_{n}.jpg')
    type_fichier = 'photo'
    extension = '.jpg'


class CorPgFichierCarteFactory(CorPgFichierFactory):
    """Factory for map files."""

    nom_fichier = factory.Sequence(lambda n: f'carte_{n}.pdf')
    type_fichier = 'carte'
    extension = '.pdf'
