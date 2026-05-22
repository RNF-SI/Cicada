"""
Unit tests for Plans app models.
Tests PlanGestion, CorSitePg, CorPgFichier models.
"""
import pytest
from datetime import datetime
from django.db import IntegrityError

from apps.plans.models import PlanGestion, CorSitePg, CorPgFichier
from apps.core.models import Nomenclature, TypeNomenclature
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
        assert plan.version == '1'

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


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionVersionChain:
    """Tests for PlanGestion version chain methods: get_root_plan, get_version_chain, get_next_version."""

    # ==================== get_root_plan ====================

    def test_get_root_plan_no_parent(self):
        """Plan without parent returns itself as root."""
        plan = PlanGestionFactory()
        assert plan.get_root_plan() == plan

    def test_get_root_plan_single_parent(self):
        """Child plan returns its parent as root."""
        root = PlanGestionFactory(nom='Root Plan')
        child = PlanGestionFactory(nom='Child Plan', plan_parent=root)
        assert child.get_root_plan() == root

    def test_get_root_plan_deep_chain(self):
        """Deep chain A→B→C: C.get_root_plan() returns A."""
        plan_a = PlanGestionFactory(nom='Plan A')
        plan_b = PlanGestionFactory(nom='Plan B', plan_parent=plan_a)
        plan_c = PlanGestionFactory(nom='Plan C', plan_parent=plan_b)
        assert plan_c.get_root_plan() == plan_a

    def test_get_root_plan_handles_circular_ref(self):
        """Self-referencing plan doesn't cause infinite loop."""
        plan = PlanGestionFactory()
        # Force a self-reference at DB level
        PlanGestion.objects.filter(pk=plan.pk).update(plan_parent=plan)
        plan.refresh_from_db()
        # Should terminate without error
        root = plan.get_root_plan()
        assert root == plan

    def test_get_root_plan_handles_mutual_circular(self):
        """Mutual circular reference A↔B terminates without error."""
        plan_a = PlanGestionFactory(nom='Plan A')
        plan_b = PlanGestionFactory(nom='Plan B', plan_parent=plan_a)
        # Force circular reference at DB level
        PlanGestion.objects.filter(pk=plan_a.pk).update(plan_parent=plan_b)
        plan_a.refresh_from_db()
        # Should terminate without error
        root = plan_a.get_root_plan()
        assert root is not None

    # ==================== get_version_chain ====================

    def test_version_chain_single_plan(self):
        """Single plan returns chain of length 1 with is_current=True."""
        plan = PlanGestionFactory(nom='Solo Plan')
        chain = plan.get_version_chain()
        assert len(chain) == 1
        assert chain[0]['id_pg'] == plan.id_pg
        assert chain[0]['is_current'] is True

    def test_version_chain_linear_two(self):
        """root→child chain has 2 items, child is_current when called on child."""
        root = PlanGestionFactory(nom='Root', version='1')
        child = PlanGestionFactory(nom='Child', version='2', plan_parent=root)
        chain = child.get_version_chain()
        assert len(chain) == 2
        # Root is first
        assert chain[0]['id_pg'] == root.id_pg
        assert chain[0]['is_current'] is False
        # Child is second and current
        assert chain[1]['id_pg'] == child.id_pg
        assert chain[1]['is_current'] is True

    def test_version_chain_linear_three(self):
        """A→B→C called on B returns 3 items, B is_current."""
        plan_a = PlanGestionFactory(nom='A', version='1')
        plan_b = PlanGestionFactory(nom='B', version='2', plan_parent=plan_a)
        plan_c = PlanGestionFactory(nom='C', version='3', plan_parent=plan_b)
        chain = plan_b.get_version_chain()
        assert len(chain) == 3
        current_items = [item for item in chain if item['is_current']]
        assert len(current_items) == 1
        assert current_items[0]['id_pg'] == plan_b.id_pg

    def test_version_chain_branching(self):
        """Root with 2 children returns chain of 3 items."""
        root = PlanGestionFactory(nom='Root')
        child1 = PlanGestionFactory(nom='Child 1', plan_parent=root)
        child2 = PlanGestionFactory(nom='Child 2', plan_parent=root)
        chain = root.get_version_chain()
        assert len(chain) == 3
        chain_ids = {item['id_pg'] for item in chain}
        assert chain_ids == {root.id_pg, child1.id_pg, child2.id_pg}

    def test_version_chain_includes_type_document(self):
        """Plan with id_type_document has type_document_mnemonique in chain."""
        ntype = TypeNomenclature.objects.create(
            mnemonique='TYPE_DOCUMENT_PLAN',
            label='Type document plan',
        )
        nomenclature = Nomenclature.objects.create(
            id_type=ntype,
            mnemonique='EVAL_MI_PARCOURS',
            label='Évaluation mi-parcours',
            cd_nomenclature='EVAL',
        )
        plan = PlanGestionFactory(id_type_document=nomenclature)
        chain = plan.get_version_chain()
        assert chain[0]['type_document_mnemonique'] == 'EVAL_MI_PARCOURS'
        assert chain[0]['type_document'] == 'Évaluation mi-parcours'

    def test_version_chain_null_type_document(self):
        """Plan without type_document has None in chain."""
        plan = PlanGestionFactory(id_type_document=None)
        chain = plan.get_version_chain()
        assert chain[0]['type_document_mnemonique'] is None
        assert chain[0]['type_document'] is None

    def test_version_chain_exposes_rang(self):
        """#280 — `rang` est inclus dans l'élément chaîne pour distinguer le rang suivant."""
        root = PlanGestionFactory(nom='Rang 1', rang=1)
        next_rang = PlanGestionFactory(nom='Rang 2 brouillon', rang=2, plan_parent=root)
        chain = root.get_version_chain()
        ranks = {item['id_pg']: item['rang'] for item in chain}
        assert ranks[root.id_pg] == 1
        assert ranks[next_rang.id_pg] == 2

    # ==================== get_next_version (entiers, #279) ====================

    def test_next_version_solo_plan(self):
        """Plan seul de version '1' → prochaine version '2'."""
        plan = PlanGestionFactory(version='1')
        assert plan.get_next_version() == '2'

    def test_next_version_in_chain(self):
        """Dans une chaîne root(1) → child(2), la prochaine version est '3'."""
        root = PlanGestionFactory(nom='Root', version='1')
        child = PlanGestionFactory(nom='Child', version='2', plan_parent=root)
        assert child.get_next_version() == '3'
        # Idempotent : appeler depuis le root donne la même valeur (chaîne complète prise en compte).
        assert root.get_next_version() == '3'

    def test_next_version_skips_non_integer_legacy(self):
        """Versions historiques non entières ignorées : fallback à '1' (#279)."""
        root = PlanGestionFactory(nom='Root', version='1.0')
        child = PlanGestionFactory(nom='Child', version='1.1', plan_parent=root)
        # Aucune version entière du même rang → fallback = '1'
        assert child.get_next_version() == '1'

    def test_next_version_empty_fallback(self):
        """Plan avec version vide → fallback à '1' (aucune version entière) (#279)."""
        plan = PlanGestionFactory(version='')
        assert plan.get_next_version() == '1'
