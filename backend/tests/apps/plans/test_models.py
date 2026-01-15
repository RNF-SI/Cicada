"""
Unit tests for Plans app models.
Tests PlanGestion, CorSitePg, CorPgFichier models.
"""
import pytest
from datetime import datetime
from django.db import IntegrityError

from apps.plans.models import PlanGestion, CorSitePg, CorPgFichier
from tests.factories.users import RoleFactory, SiteFactory, OrganismeFactory
from tests.factories.plans import (
    PlanGestionFactory, PlanGestionValideFactory, PlanGestionArchiveFactory,
    CorSitePgFactory, CorPgFichierFactory, CorPgFichierImageFactory
)


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionModel:
    """Tests for the PlanGestion model."""

    def test_create_plan(self):
        """Test creating a basic plan."""
        plan = PlanGestionFactory()
        assert plan.id_pg is not None
        assert plan.nom is not None
        assert plan.statut == 'draft'

    def test_plan_str_method(self):
        """Test Plan __str__ method."""
        plan = PlanGestionFactory(nom='Test Plan Name')
        assert str(plan) == 'Test Plan Name'

    def test_plan_default_values(self):
        """Test plan default values."""
        plan = PlanGestionFactory()
        assert plan.gestion_partagee is False
        assert plan.ct88 is False
        assert plan.risque_incendie is False
        assert plan.version == '1.0'

    def test_plan_statut_choices(self):
        """Test plan status choices."""
        draft = PlanGestionFactory(statut='draft')
        valide = PlanGestionValideFactory()
        archive = PlanGestionArchiveFactory()

        assert draft.statut == 'draft'
        assert valide.statut == 'valide'
        assert archive.statut == 'archive'

    def test_plan_dates_auto_set(self):
        """Test that date_ajout and date_maj are auto-set."""
        plan = PlanGestionFactory()
        assert plan.date_ajout is not None
        assert plan.date_maj is not None

    def test_plan_with_years(self):
        """Test plan with year range."""
        plan = PlanGestionFactory(annee_debut=2024, annee_fin=2034)
        assert plan.annee_debut == 2024
        assert plan.annee_fin == 2034

    def test_plan_creator_association(self):
        """Test plan is associated with creator."""
        user = RoleFactory()
        plan = PlanGestionFactory(id_utilisateur_ajout=user)
        assert plan.id_utilisateur_ajout == user


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionMethods:
    """Tests for PlanGestion helper methods."""

    def test_get_sites_empty(self):
        """Test get_sites returns empty list for plan with no sites."""
        plan = PlanGestionFactory()
        sites = plan.get_sites()
        assert sites == []

    def test_get_sites_with_sites(self):
        """Test get_sites returns associated sites."""
        plan = PlanGestionFactory()
        site1 = SiteFactory(nom_site='Site 1')
        site2 = SiteFactory(nom_site='Site 2')
        CorSitePgFactory(plan_de_gestion=plan, site=site1)
        CorSitePgFactory(plan_de_gestion=plan, site=site2)

        sites = plan.get_sites()
        site_names = [s.nom_site for s in sites]
        assert 'Site 1' in site_names
        assert 'Site 2' in site_names

    def test_is_multi_sites_false_for_single_site(self):
        """Test is_multi_sites returns False for single site plan."""
        plan = PlanGestionFactory()
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        assert plan.is_multi_sites() is False

    def test_is_multi_sites_true_for_multiple_sites(self):
        """Test is_multi_sites returns True for multi-site plan."""
        plan = PlanGestionFactory()
        site1 = SiteFactory()
        site2 = SiteFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site1)
        CorSitePgFactory(plan_de_gestion=plan, site=site2)

        assert plan.is_multi_sites() is True

    def test_get_periode_gestion_full(self):
        """Test get_periode_gestion with both years."""
        plan = PlanGestionFactory(annee_debut=2020, annee_fin=2030)
        assert plan.get_periode_gestion() == '2020-2030'

    def test_get_periode_gestion_start_only(self):
        """Test get_periode_gestion with only start year."""
        plan = PlanGestionFactory(annee_debut=2020, annee_fin=None)
        assert plan.get_periode_gestion() == 'À partir de 2020'

    def test_get_periode_gestion_end_only(self):
        """Test get_periode_gestion with only end year."""
        plan = PlanGestionFactory(annee_debut=None, annee_fin=2030)
        assert plan.get_periode_gestion() == "Jusqu'en 2030"

    def test_get_periode_gestion_none(self):
        """Test get_periode_gestion with no years."""
        plan = PlanGestionFactory(annee_debut=None, annee_fin=None)
        assert plan.get_periode_gestion() == 'Période non définie'


@pytest.mark.django_db
@pytest.mark.unit
class TestCorSitePgModel:
    """Tests for the CorSitePg model (plan-site relationship)."""

    def test_create_cor_site_pg(self):
        """Test creating a plan-site relationship."""
        plan = PlanGestionFactory()
        site = SiteFactory()
        cor = CorSitePgFactory(plan_de_gestion=plan, site=site)

        assert cor.plan_de_gestion == plan
        assert cor.site == site

    def test_cor_site_pg_str_method(self):
        """Test CorSitePg __str__ method."""
        plan = PlanGestionFactory(nom='Test Plan')
        site = SiteFactory(nom_site='Test Site')
        cor = CorSitePgFactory(plan_de_gestion=plan, site=site, rang=1)

        expected = 'Test Site - Test Plan (rang 1)'
        assert str(cor) == expected

    def test_cor_site_pg_str_method_no_rang(self):
        """Test CorSitePg __str__ method without rang."""
        plan = PlanGestionFactory(nom='Test Plan')
        site = SiteFactory(nom_site='Test Site')
        cor = CorSitePgFactory(plan_de_gestion=plan, site=site, rang=None)

        expected = 'Test Site - Test Plan'
        assert str(cor) == expected

    def test_cor_site_pg_unique_constraint(self):
        """Test unique constraint on plan-site pair."""
        plan = PlanGestionFactory()
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        with pytest.raises(IntegrityError):
            CorSitePgFactory(plan_de_gestion=plan, site=site)

    def test_cor_site_pg_date_auto_set(self):
        """Test that date_association is auto-set."""
        cor = CorSitePgFactory()
        assert cor.date_association is not None


@pytest.mark.django_db
@pytest.mark.unit
class TestCorPgFichierModel:
    """Tests for the CorPgFichier model (plan files)."""

    def test_create_cor_pg_fichier(self):
        """Test creating a plan file."""
        fichier = CorPgFichierFactory()
        assert fichier.nom_fichier is not None
        assert fichier.chemin_fichier is not None

    def test_cor_pg_fichier_str_method(self):
        """Test CorPgFichier __str__ method."""
        plan = PlanGestionFactory(nom='Test Plan')
        fichier = CorPgFichierFactory(
            plan_de_gestion=plan,
            titre='Document Title'
        )
        assert str(fichier) == 'Document Title (Test Plan)'

    def test_cor_pg_fichier_str_method_no_titre(self):
        """Test CorPgFichier __str__ fallback to nom_fichier."""
        plan = PlanGestionFactory(nom='Test Plan')
        fichier = CorPgFichierFactory(
            plan_de_gestion=plan,
            nom_fichier='document.pdf',
            titre=None
        )
        assert str(fichier) == 'document.pdf (Test Plan)'

    def test_is_image_true_for_images(self):
        """Test is_image returns True for image extensions."""
        fichier = CorPgFichierImageFactory()
        assert fichier.is_image() is True

    def test_is_image_false_for_documents(self):
        """Test is_image returns False for document extensions."""
        fichier = CorPgFichierFactory(extension='.pdf')
        assert fichier.is_image() is False

    def test_is_document_true_for_documents(self):
        """Test is_document returns True for document extensions."""
        fichier = CorPgFichierFactory(extension='.pdf')
        assert fichier.is_document() is True

    def test_is_document_false_for_images(self):
        """Test is_document returns False for image extensions."""
        fichier = CorPgFichierFactory(extension='.jpg')
        assert fichier.is_document() is False

    def test_get_file_size_human_bytes(self):
        """Test get_file_size_human for small files."""
        fichier = CorPgFichierFactory(taille_fichier=500)
        assert 'B' in fichier.get_file_size_human()

    def test_get_file_size_human_kb(self):
        """Test get_file_size_human for KB files."""
        fichier = CorPgFichierFactory(taille_fichier=5000)
        assert 'KB' in fichier.get_file_size_human()

    def test_get_file_size_human_mb(self):
        """Test get_file_size_human for MB files."""
        fichier = CorPgFichierFactory(taille_fichier=5000000)
        assert 'MB' in fichier.get_file_size_human()

    def test_get_file_size_human_none(self):
        """Test get_file_size_human when size is None."""
        fichier = CorPgFichierFactory(taille_fichier=None)
        assert fichier.get_file_size_human() == 'Taille inconnue'

    def test_type_fichier_choices(self):
        """Test file type choices."""
        fichier_doc = CorPgFichierFactory(type_fichier='document')
        fichier_carte = CorPgFichierFactory(type_fichier='carte')
        fichier_photo = CorPgFichierFactory(type_fichier='photo')

        assert fichier_doc.type_fichier == 'document'
        assert fichier_carte.type_fichier == 'carte'
        assert fichier_photo.type_fichier == 'photo'

    def test_date_upload_auto_set(self):
        """Test that date_upload is auto-set."""
        fichier = CorPgFichierFactory()
        assert fichier.date_upload is not None
