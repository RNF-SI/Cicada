"""
Tests for PlanDuplicationService and the duplicate API endpoint.
Covers: basic duplication, unique name generation, site/referent/fichier copy,
enjeux hierarchy, OO FK remap, M2M tables, mesure/operation exclusion,
activity logging, and API endpoint behavior.
"""
import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework import status

from apps.plans.models import PlanGestion, CorSitePg, CorPgFichier
from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, Pression,
    ObjectifLongTerme, NiveauExigence,
    ObjectifOperationnel, ResultatAttendu,
    CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
)
from apps.plans.models_indicateurs import (
    Indicateur, Metrique, Mesure,
    CorIndicateurTaxon, CorIndicateurHabitat, CorIndicateurGeologie,
)
from apps.plans.models import CorRolePlan
from apps.plans.services import PlanDuplicationService
from apps.core.models import ActivityLog

from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, SiteFactory, CorRoleSiteFactory, OrganismeFactory,
    CorOgSiteFactory,
)
from tests.factories.plans import (
    PlanGestionFactory, CorSitePgFactory, CorPgFichierFactory,
)
from tests.factories.enjeux import (
    EnjeuFactory, FcrFactory,
    FacteurInfluenceFactory, PressionFactory,
    ObjectifLongTermeFactory, NiveauExigenceFactory,
    ObjectifOperationnelFactory, ResultatAttenduFactory,
    CorEnjeuTaxonFactory, CorEnjeuHabitatFactory, CorEnjeuGeologieFactory,
    IndicateurFactory, IndicateurPressionFactory, MetriqueFactory, MesureFactory,
    CorIndicateurTaxonFactory,
)


@pytest.fixture
def user(db):
    return RoleFactory()


@pytest.fixture
def source_plan(db, user):
    return PlanGestionFactory(
        nom='Plan Original',
        statut='valide',
        version='2',
        annee_debut=2020,
        annee_fin=2030,
        id_utilisateur_ajout=user,
    )


@pytest.fixture
def api_client():
    return APIClient()


# =============================================================================
# Service: Basic duplication
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestDuplicatePlanBasic:
    """Tests for basic plan duplication (metadata)."""

    def test_duplicate_creates_new_plan(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert new_plan.id_pg is not None
        assert new_plan.id_pg != source_plan.id_pg

    def test_duplicate_name_prefixed(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert new_plan.nom == '[En cours d\'élaboration] Plan Original'

    def test_duplicate_statut_is_draft(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert new_plan.statut == 'draft'

    def test_duplicate_version_is_next(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert new_plan.version == '3'

    def test_duplicate_plan_parent_set(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert new_plan.plan_parent == source_plan

    def test_duplicate_preserves_years(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert new_plan.annee_debut == 2020
        assert new_plan.annee_fin == 2030

    def test_duplicate_geometry_is_none(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert new_plan.geometrie is None

    def test_duplicate_audit_fields_set_to_user(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert new_plan.id_utilisateur_ajout == user
        assert new_plan.id_utilisateur_maj == user

    def test_duplicate_slug_auto_generated(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        # Slug should be set (either auto or empty string handled by model save)
        assert new_plan.slug is not None


# =============================================================================
# Service: Unique name generation
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestUniqueName:
    """Tests for unique name generation with [En cours d'élaboration] prefix."""

    def test_first_copy_uses_copie_prefix(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert new_plan.nom == '[En cours d\'élaboration] Plan Original'

    def test_second_copy_increments(self, source_plan, user):
        # Create first copy
        PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        # Create second copy
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert new_plan.nom == '[En cours d\'élaboration 2] Plan Original'

    def test_copy_of_copy_strips_prefix(self, source_plan, user):
        """Duplicating a plan that already has [En cours d'élaboration] prefix strips it."""
        first_copy = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert first_copy.nom == '[En cours d\'élaboration] Plan Original'

        second_copy = PlanDuplicationService.duplicate_plan(
            source_plan=first_copy, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        # Should strip existing [En cours d'élaboration] and re-add it, resulting in increment
        assert second_copy.nom == '[En cours d\'élaboration 2] Plan Original'

    def test_long_name_truncated(self, user):
        # Use max-length name (255 chars) - DB won't accept longer
        long_name = 'A' * 255
        plan = PlanGestionFactory(nom=long_name, id_utilisateur_ajout=user)
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )
        assert len(new_plan.nom) <= 255
        assert new_plan.nom.startswith('[En cours d\'élaboration] ')


# =============================================================================
# Service: Copy sites
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestCopySites:
    """Tests for site duplication on/off."""

    def test_copy_sites_true(self, source_plan, user):
        site1 = SiteFactory()
        site2 = SiteFactory()
        CorSitePgFactory(plan_de_gestion=source_plan, site=site1, rang=1, commentaire='Premier')
        CorSitePgFactory(plan_de_gestion=source_plan, site=site2, rang=2, commentaire='Second')

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=True, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )

        new_sites = CorSitePg.objects.filter(plan_de_gestion=new_plan)
        assert new_sites.count() == 2
        assert set(new_sites.values_list('site_id', flat=True)) == {site1.pk, site2.pk}
        # Check rang and commentaire are copied
        first = new_sites.get(site=site1)
        assert first.rang == 1
        assert first.commentaire == 'Premier'

    def test_copy_sites_false(self, source_plan, user):
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=source_plan, site=site)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )

        assert CorSitePg.objects.filter(plan_de_gestion=new_plan).count() == 0


# =============================================================================
# Service: Copy referents
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestCopyReferents:
    """Tests for referent duplication on/off."""

    def test_copy_referents_true(self, source_plan, user):
        ref1 = RoleFactory()
        ref2 = RoleFactory()
        source_plan.referents.set([ref1, ref2])

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=True,
            copy_fichiers=False, copy_enjeux=False,
        )

        assert set(new_plan.referents.values_list('pk', flat=True)) == {ref1.pk, ref2.pk}

    def test_copy_referents_false(self, source_plan, user):
        ref = RoleFactory()
        source_plan.referents.set([ref])

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )

        assert new_plan.referents.count() == 0


# =============================================================================
# Service: Copy fichiers
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestCopyFichiers:
    """Tests for file duplication on/off."""

    def test_copy_fichiers_true_metadata(self, source_plan, user):
        """Test fichier metadata is copied (without physical file)."""
        CorPgFichierFactory(
            plan_de_gestion=source_plan,
            nom_fichier='doc.pdf',
            type_fichier='document',
            titre='Mon document',
            chemin_fichier='',  # No physical file
            id_utilisateur_upload=user,
        )

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=True, copy_enjeux=False,
        )

        new_fichiers = CorPgFichier.objects.filter(plan_de_gestion=new_plan)
        assert new_fichiers.count() == 1
        f = new_fichiers.first()
        assert f.nom_fichier == 'doc.pdf'
        assert f.type_fichier == 'document'
        assert f.titre == 'Mon document'
        assert f.id_utilisateur_upload == user

    def test_copy_fichiers_false(self, source_plan, user):
        CorPgFichierFactory(plan_de_gestion=source_plan, id_utilisateur_upload=user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )

        assert CorPgFichier.objects.filter(plan_de_gestion=new_plan).count() == 0


# =============================================================================
# Service: Copy enjeux with M2M
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestCopyEnjeux:
    """Tests for enjeux/FCR duplication including M2M tables."""

    def test_copy_enjeux_true(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, libelle='Enjeu A', rang=1, id_utilisateur_ajout=user)
        fcr = FcrFactory(id_pg=source_plan, libelle='FCR A', id_utilisateur_ajout=user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=False,
        )

        new_enjeux = Enjeu.objects.filter(id_pg=new_plan)
        assert new_enjeux.count() == 2
        assert new_enjeux.filter(libelle='Enjeu A').exists()
        assert new_enjeux.filter(libelle='FCR A').exists()

    def test_copy_enjeux_false(self, source_plan, user):
        EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )

        assert Enjeu.objects.filter(id_pg=new_plan).count() == 0

    def test_enjeu_m2m_taxon_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        CorEnjeuTaxonFactory(id_enjeu=enjeu, cd_nom=12345, nom_complet='Taxon A')

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=False,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        taxons = CorEnjeuTaxon.objects.filter(id_enjeu=new_enjeu)
        assert taxons.count() == 1
        assert taxons.first().cd_nom == 12345

    def test_enjeu_m2m_habitat_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        CorEnjeuHabitatFactory(id_enjeu=enjeu, cd_hab='HAB_001', lb_hab_fr='Forêt')

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=False,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        habitats = CorEnjeuHabitat.objects.filter(id_enjeu=new_enjeu)
        assert habitats.count() == 1
        assert habitats.first().cd_hab == 'HAB_001'

    def test_enjeu_m2m_geologie_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        CorEnjeuGeologieFactory(id_enjeu=enjeu, id_inpg='GEO_001', nom='Calcaire')

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=False,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        geos = CorEnjeuGeologie.objects.filter(id_enjeu=new_enjeu)
        assert geos.count() == 1
        assert geos.first().id_inpg == 'GEO_001'


# =============================================================================
# Service: Copy full hierarchy (sub-elements)
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestCopySubElements:
    """Tests for full hierarchy duplication: FacteurInfluence, Pression, OLT, NE, OO, RA, Indicateur, Metrique."""

    def test_facteur_influence_and_pression_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        fi = FacteurInfluenceFactory(id_enjeu=enjeu, libelle='Facteur A', id_utilisateur_ajout=user)
        PressionFactory(id_facteur_influence=fi, libelle='Pression A', id_utilisateur_ajout=user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=True,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        new_fis = FacteurInfluence.objects.filter(id_enjeu=new_enjeu)
        assert new_fis.count() == 1
        assert new_fis.first().libelle == 'Facteur A'

        new_pressions = Pression.objects.filter(id_facteur_influence=new_fis.first())
        assert new_pressions.count() == 1
        assert new_pressions.first().libelle == 'Pression A'

    def test_olt_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu, libelle='OLT A', id_utilisateur_ajout=user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=True,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        new_olt = ObjectifLongTerme.objects.get(id_enjeu=new_enjeu)
        assert new_olt.libelle == 'OLT A'
        assert new_olt.id_olt != olt.id_olt

    def test_niveau_exigence_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        NiveauExigenceFactory(id_olt=olt, libelle='NE A', id_utilisateur_ajout=user)
        NiveauExigenceFactory(id_olt=olt, libelle='NE B', id_utilisateur_ajout=user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=True,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        new_olt = ObjectifLongTerme.objects.get(id_enjeu=new_enjeu)
        nes = NiveauExigence.objects.filter(id_olt=new_olt)
        assert nes.count() == 2

    def test_indicateur_on_ne_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        ne = NiveauExigenceFactory(id_olt=olt, id_utilisateur_ajout=user)
        ind = IndicateurFactory(id_ne=ne, nom_indicateur='Ind A', id_utilisateur_ajout=user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=True,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        new_olt = ObjectifLongTerme.objects.get(id_enjeu=new_enjeu)
        new_ne = NiveauExigence.objects.get(id_olt=new_olt)
        inds = Indicateur.objects.filter(id_ne=new_ne)
        assert inds.count() == 1
        assert inds.first().nom_indicateur == 'Ind A'
        assert inds.first().id_indicateur != ind.id_indicateur

    def test_metrique_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        ne = NiveauExigenceFactory(id_olt=olt, id_utilisateur_ajout=user)
        ind = IndicateurFactory(id_ne=ne, id_utilisateur_ajout=user)
        MetriqueFactory(
            id_indicateur=ind, nom_metrique='Met A',
            sens_variation='DECROISSANT',
            score_1_sup_inclusive=False,
            score_2_sup_inclusive=True,
            score_3_sup_inclusive=False,
            score_4_sup_inclusive=True,
            id_utilisateur_ajout=user,
        )

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=True,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        new_olt = ObjectifLongTerme.objects.get(id_enjeu=new_enjeu)
        new_ne = NiveauExigence.objects.get(id_olt=new_olt)
        new_ind = Indicateur.objects.get(id_ne=new_ne)
        mets = Metrique.objects.filter(id_indicateur=new_ind)
        assert mets.count() == 1
        new_met = mets.first()
        assert new_met.nom_metrique == 'Met A'
        # Verify direction and inclusivity fields are copied
        assert new_met.sens_variation == 'DECROISSANT'
        assert new_met.score_1_sup_inclusive is False
        assert new_met.score_2_sup_inclusive is True
        assert new_met.score_3_sup_inclusive is False
        assert new_met.score_4_sup_inclusive is True

    def test_indicateur_m2m_taxon_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        ne = NiveauExigenceFactory(id_olt=olt, id_utilisateur_ajout=user)
        ind = IndicateurFactory(id_ne=ne, id_utilisateur_ajout=user)
        CorIndicateurTaxonFactory(id_indicateur=ind, cd_nom=99999, nom_complet='Taxon Ind')

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=True,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        new_olt = ObjectifLongTerme.objects.get(id_enjeu=new_enjeu)
        new_ne = NiveauExigence.objects.get(id_olt=new_olt)
        new_ind = Indicateur.objects.get(id_ne=new_ne)
        taxons = CorIndicateurTaxon.objects.filter(id_indicateur=new_ind)
        assert taxons.count() == 1
        assert taxons.first().cd_nom == 99999


# =============================================================================
# Service: OO FK remap
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestOOPressionRemap:
    """Tests for ObjectifOperationnel under Pression duplication."""

    def test_oo_with_pression_remapped(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        fi = FacteurInfluenceFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        pression = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)
        ObjectifOperationnelFactory(
            libelle='OO linked',
            id_utilisateur_ajout=user,
            pressions=[pression],
        )

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=True,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        new_fi = FacteurInfluence.objects.get(id_enjeu=new_enjeu)
        new_pression = Pression.objects.get(id_facteur_influence=new_fi)
        new_oo = new_pression.objectifs_operationnels.first()
        assert new_oo is not None
        assert new_oo.libelle == 'OO linked'
        assert new_pression in new_oo.pressions.all()
        assert pression not in new_oo.pressions.all()

    def test_oo_resultat_attendu_indicateur_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        fi = FacteurInfluenceFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        pression = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)
        oo = ObjectifOperationnelFactory(id_utilisateur_ajout=user, pressions=[pression])
        ra = ResultatAttenduFactory(id_oo=oo, libelle='RA A', id_utilisateur_ajout=user)
        ind = IndicateurPressionFactory(id_resultat_attendu=ra, nom_indicateur='Ind OO', id_utilisateur_ajout=user)
        MetriqueFactory(id_indicateur=ind, nom_metrique='Met OO', id_utilisateur_ajout=user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=True,
        )

        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        new_fi = FacteurInfluence.objects.get(id_enjeu=new_enjeu)
        new_pression = Pression.objects.get(id_facteur_influence=new_fi)
        new_oo = new_pression.objectifs_operationnels.first()
        assert new_oo is not None
        new_ra = ResultatAttendu.objects.get(id_oo=new_oo)
        assert new_ra.libelle == 'RA A'

        new_ind = Indicateur.objects.get(id_resultat_attendu=new_ra)
        assert new_ind.nom_indicateur == 'Ind OO'

        new_met = Metrique.objects.get(id_indicateur=new_ind)
        assert new_met.nom_metrique == 'Met OO'


# =============================================================================
# Service: Exclusions (Mesure, Operation)
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestExclusions:
    """Tests that Mesure and Operation are NOT copied."""

    def test_mesures_not_copied(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        ne = NiveauExigenceFactory(id_olt=olt, id_utilisateur_ajout=user)
        ind = IndicateurFactory(id_ne=ne, id_utilisateur_ajout=user)
        met = MetriqueFactory(id_indicateur=ind, id_utilisateur_ajout=user)
        MesureFactory(id_metrique=met, valeur='42', id_utilisateur_ajout=user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=True,
        )

        # Metrique should be copied, but Mesure should not
        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        new_olt = ObjectifLongTerme.objects.get(id_enjeu=new_enjeu)
        new_ne = NiveauExigence.objects.get(id_olt=new_olt)
        new_ind = Indicateur.objects.get(id_ne=new_ne)
        new_met = Metrique.objects.get(id_indicateur=new_ind)

        # Mesure linked to new_met should not exist
        assert Mesure.objects.filter(id_metrique=new_met).count() == 0
        # Original mesure still exists
        assert Mesure.objects.filter(id_metrique=met).count() == 1


# =============================================================================
# Service: sub_elements depends on enjeux
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestSubElementsDependency:
    """Tests that copy_sub_elements is ignored if copy_enjeux is False."""

    def test_sub_elements_ignored_without_enjeux(self, source_plan, user):
        enjeu = EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=user)
        FacteurInfluenceFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False, copy_sub_elements=True,
        )

        # Neither enjeux nor sub-elements should be copied
        assert Enjeu.objects.filter(id_pg=new_plan).count() == 0
        assert FacteurInfluence.objects.filter(
            id_enjeu__id_pg=new_plan
        ).count() == 0


# =============================================================================
# Service: Plan without content
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanWithoutContent:
    """Tests duplication of a plan with no enjeux/sites/referents."""

    def test_empty_plan_duplicated(self, user):
        empty_plan = PlanGestionFactory(
            nom='Plan vide',
            id_utilisateur_ajout=user,
        )

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=empty_plan, user=user,
        )

        assert new_plan.id_pg is not None
        assert new_plan.nom == '[En cours d\'élaboration] Plan vide'
        assert Enjeu.objects.filter(id_pg=new_plan).count() == 0
        assert CorSitePg.objects.filter(plan_de_gestion=new_plan).count() == 0


# =============================================================================
# Service: Activity logging
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestActivityLogging:
    """Tests for activity log on duplication."""

    def test_activity_log_created(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )

        # A create activity log should exist for the new plan
        log = ActivityLog.objects.filter(
            entity_type='plan',
            entity_id=new_plan.id_pg,
            action='create',
        ).first()
        assert log is not None
        assert log.actor == user
        assert log.metadata.get('duplication') is True

    def test_activity_log_references_source(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )

        log = ActivityLog.objects.filter(
            entity_type='plan',
            entity_id=new_plan.id_pg,
            action='create',
        ).first()
        assert log is not None
        assert log.metadata.get('source_plan_id') == source_plan.id_pg
        assert log.metadata.get('source_plan_nom') == 'Plan Original'
        assert log.metadata.get('duplication') is True

    def test_no_double_activity_signal(self, source_plan, user):
        """Ensure _skip_activity_signal prevents double logging."""
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )

        # Count create logs for the new plan
        create_logs = ActivityLog.objects.filter(
            entity_type='plan',
            entity_id=new_plan.id_pg,
            action='create',
        )
        assert create_logs.count() == 1


# =============================================================================
# Service: Full hierarchy integration test
# =============================================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestFullHierarchyDuplication:
    """Integration test: duplicate a plan with complete hierarchy."""

    def test_complete_hierarchy(self, user):
        """Test duplicating a plan with: enjeu -> FI -> pression, OLT -> NE -> Ind -> Met, OO (linked to FI) -> RA -> Ind -> Met."""
        source = PlanGestionFactory(nom='Plan Complet', id_utilisateur_ajout=user)

        # Sites
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=source, site=site)

        # Referents
        ref = RoleFactory()
        source.referents.add(ref)

        # Enjeu with M2M
        enjeu = EnjeuFactory(id_pg=source, libelle='Enjeu Complet', id_utilisateur_ajout=user)
        CorEnjeuTaxonFactory(id_enjeu=enjeu, cd_nom=11111)

        # Facteur + Pression
        fi = FacteurInfluenceFactory(id_enjeu=enjeu, libelle='FI', id_utilisateur_ajout=user)
        PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)

        # OLT + NE + Indicateur (on NE) + Metrique
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        ne = NiveauExigenceFactory(id_olt=olt, id_utilisateur_ajout=user)
        ind_ne = IndicateurFactory(id_ne=ne, id_utilisateur_ajout=user)
        MetriqueFactory(id_indicateur=ind_ne, id_utilisateur_ajout=user)
        CorIndicateurTaxonFactory(id_indicateur=ind_ne, cd_nom=22222)

        # OO linked to Pression under FI + RA + Indicateur (on RA) + Metrique
        pression = Pression.objects.filter(id_facteur_influence=fi).first()
        oo = ObjectifOperationnelFactory(
            id_utilisateur_ajout=user, pressions=[pression]
        )
        ra = ResultatAttenduFactory(id_oo=oo, id_utilisateur_ajout=user)
        ind_ra = IndicateurPressionFactory(id_resultat_attendu=ra, id_utilisateur_ajout=user)
        MetriqueFactory(id_indicateur=ind_ra, id_utilisateur_ajout=user)

        # Mesure (should NOT be copied)
        met_source = Metrique.objects.filter(id_indicateur=ind_ne).first()
        MesureFactory(id_metrique=met_source, id_utilisateur_ajout=user)

        # Duplicate with all options
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source, user=user,
            copy_sites=True, copy_referents=True,
            copy_fichiers=False, copy_enjeux=True, copy_sub_elements=True,
        )

        # Verify plan metadata
        assert new_plan.nom == '[En cours d\'élaboration] Plan Complet'
        assert new_plan.statut == 'draft'
        assert new_plan.version == '2'
        assert new_plan.plan_parent == source

        # Verify sites copied
        assert CorSitePg.objects.filter(plan_de_gestion=new_plan).count() == 1

        # Verify referents copied
        assert new_plan.referents.count() == 1

        # Verify enjeu
        new_enjeu = Enjeu.objects.get(id_pg=new_plan)
        assert new_enjeu.libelle == 'Enjeu Complet'
        assert CorEnjeuTaxon.objects.filter(id_enjeu=new_enjeu).count() == 1

        # Verify facteur + pression
        new_fi = FacteurInfluence.objects.get(id_enjeu=new_enjeu)
        assert Pression.objects.filter(id_facteur_influence=new_fi).count() == 1

        # Verify OLT chain
        new_olt = ObjectifLongTerme.objects.get(id_enjeu=new_enjeu)
        new_ne = NiveauExigence.objects.get(id_olt=new_olt)
        new_ind_ne = Indicateur.objects.get(id_ne=new_ne)
        assert Metrique.objects.filter(id_indicateur=new_ind_ne).count() == 1
        assert CorIndicateurTaxon.objects.filter(id_indicateur=new_ind_ne).count() == 1

        # Verify OO chain under pression (M2M)
        new_pression = Pression.objects.filter(id_facteur_influence=new_fi).first()
        new_oo = new_pression.objectifs_operationnels.first()
        assert new_oo is not None
        new_ra = ResultatAttendu.objects.get(id_oo=new_oo)
        new_ind_ra = Indicateur.objects.get(id_resultat_attendu=new_ra)
        assert Metrique.objects.filter(id_indicateur=new_ind_ra).count() == 1

        # Verify mesures NOT copied
        for met in Metrique.objects.filter(id_indicateur=new_ind_ne):
            assert Mesure.objects.filter(id_metrique=met).count() == 0

        # Verify activity log
        log = ActivityLog.objects.filter(
            entity_type='plan',
            entity_id=new_plan.id_pg,
            action='create',
        ).first()
        assert log is not None
        assert log.metadata.get('duplication') is True
        assert log.metadata.get('source_plan_id') == source.id_pg


# =============================================================================
# API Endpoint tests
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestDuplicateAPIEndpoint:
    """Tests for POST /api/plans/plans/{id}/duplicate/ endpoint."""

    def test_duplicate_unauthenticated(self, api_client, source_plan):
        response = api_client.post(
            f'/api/plans/plans/{source_plan.id_pg}/duplicate/',
            data={},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_duplicate_as_super_admin(self, api_client, source_plan):
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        response = api_client.post(
            f'/api/plans/plans/{source_plan.id_pg}/duplicate/',
            data={},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom'] == '[En cours d\'élaboration] Plan Original'
        assert response.data['statut'] == 'draft'

    def test_duplicate_nonexistent_plan(self, api_client):
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        response = api_client.post(
            '/api/plans/plans/99999/duplicate/',
            data={},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_duplicate_with_custom_options(self, api_client, source_plan):
        admin = SuperAdminFactory()
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=source_plan, site=site)
        EnjeuFactory(id_pg=source_plan, id_utilisateur_ajout=admin)

        api_client.force_authenticate(user=admin)

        response = api_client.post(
            f'/api/plans/plans/{source_plan.id_pg}/duplicate/',
            data={
                'copy_sites': False,
                'copy_referents': False,
                'copy_fichiers': False,
                'copy_enjeux': True,
                'copy_sub_elements': False,
            },
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        new_plan_id = response.data['id_pg']
        # Sites should not be copied
        assert CorSitePg.objects.filter(plan_de_gestion_id=new_plan_id).count() == 0
        # Enjeux should be copied
        assert Enjeu.objects.filter(id_pg_id=new_plan_id).count() == 1

    def test_duplicate_defaults(self, api_client, source_plan):
        """Test that default options (empty body) apply correctly."""
        admin = SuperAdminFactory()
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=source_plan, site=site)
        ref = RoleFactory()
        source_plan.referents.add(ref)

        api_client.force_authenticate(user=admin)

        response = api_client.post(
            f'/api/plans/plans/{source_plan.id_pg}/duplicate/',
            data={},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        new_plan_id = response.data['id_pg']
        # Default: copy_sites=True, copy_referents=True
        assert CorSitePg.objects.filter(plan_de_gestion_id=new_plan_id).count() == 1
        new_plan = PlanGestion.objects.get(id_pg=new_plan_id)
        assert new_plan.referents.count() == 1

    def test_duplicate_as_referent(self, api_client, source_plan):
        """Test that a referent can duplicate a plan they have access to."""
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
        CorSitePgFactory(plan_de_gestion=source_plan, site=site)

        api_client.force_authenticate(user=referent)

        response = api_client.post(
            f'/api/plans/plans/{source_plan.id_pg}/duplicate/',
            data={},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_duplicate_non_valide_plan_rejected(self, api_client):
        """Only plans with statut='valide' can be duplicated via API."""
        admin = SuperAdminFactory()
        draft_plan = PlanGestionFactory(
            nom='Plan Brouillon',
            statut='draft',
            id_utilisateur_ajout=admin,
        )

        api_client.force_authenticate(user=admin)

        response = api_client.post(
            f'/api/plans/plans/{draft_plan.id_pg}/duplicate/',
            data={},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# Service: Auto-access after duplication
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestAutoAccess:
    """Tests that the duplicating user is auto-added as member of the new plan."""

    def test_user_added_as_member(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )

        membership = CorRolePlan.objects.filter(
            id_role=user, plan_de_gestion=new_plan
        )
        assert membership.exists()
        assert membership.first().referent is True

    def test_user_member_is_referent(self, source_plan, user):
        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=False,
            copy_fichiers=False, copy_enjeux=False,
        )

        member = CorRolePlan.objects.get(id_role=user, plan_de_gestion=new_plan)
        assert member.referent is True
        assert 'duplication' in member.commentaire.lower()

    def test_no_duplicate_membership_with_copy_referents(self, source_plan, user):
        """If user is also a referent of the source plan, no conflict."""
        source_plan.referents.add(user)

        new_plan = PlanDuplicationService.duplicate_plan(
            source_plan=source_plan, user=user,
            copy_sites=False, copy_referents=True,
            copy_fichiers=False, copy_enjeux=False,
        )

        # User should appear as member (via CorRolePlan) - no duplicate error
        assert CorRolePlan.objects.filter(
            id_role=user, plan_de_gestion=new_plan
        ).count() == 1

    def test_api_returns_membre_data(self, api_client, source_plan):
        """Test that the API response includes the user's membership."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        response = api_client.post(
            f'/api/plans/plans/{source_plan.id_pg}/duplicate/',
            data={},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED

        new_plan_id = response.data['id_pg']
        assert CorRolePlan.objects.filter(
            id_role=admin, plan_de_gestion_id=new_plan_id
        ).exists()


# =============================================================================
# API: scope=mine filter
# =============================================================================


@pytest.mark.django_db
@pytest.mark.unit
class TestScopeMineFilter:
    """Tests for ?scope=mine query parameter on plan list endpoint."""

    def test_scope_mine_excludes_org_only_plans(self, api_client):
        """A regular user with scope=mine should not see org-level plans they can't access directly."""
        org = OrganismeFactory()
        user = RoleFactory(id_organisme=org)

        # Site linked to user's org but user NOT assigned to the site
        site_org = SiteFactory()
        CorOgSiteFactory(id_site=site_org, uuid_og=org)

        # Plan linked to that site (org-level, user can only request access)
        plan_org = PlanGestionFactory(nom='Plan Org Only')
        CorSitePgFactory(plan_de_gestion=plan_org, site=site_org)

        # Site assigned directly to the user
        site_mine = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site_mine)

        # Plan linked to user's direct site
        plan_mine = PlanGestionFactory(nom='Plan Direct')
        CorSitePgFactory(plan_de_gestion=plan_mine, site=site_mine)

        api_client.force_authenticate(user=user)

        # Without scope=mine: should see both plans
        response = api_client.get('/api/plans/plans/')
        assert response.status_code == status.HTTP_200_OK
        names = [p['nom'] for p in response.data['results']]
        assert 'Plan Direct' in names
        assert 'Plan Org Only' in names

        # With scope=mine: should only see direct plan
        response = api_client.get('/api/plans/plans/?scope=mine')
        assert response.status_code == status.HTTP_200_OK
        names = [p['nom'] for p in response.data['results']]
        assert 'Plan Direct' in names
        assert 'Plan Org Only' not in names

    def test_scope_mine_keeps_referent_plans(self, api_client):
        """scope=mine should still include plans where user is a referent."""
        user = RoleFactory()
        plan = PlanGestionFactory(nom='Plan Referent')
        plan.referents.add(user)

        api_client.force_authenticate(user=user)

        response = api_client.get('/api/plans/plans/?scope=mine')
        assert response.status_code == status.HTTP_200_OK
        names = [p['nom'] for p in response.data['results']]
        assert 'Plan Referent' in names

    def test_scope_mine_keeps_member_plans(self, api_client):
        """scope=mine should still include plans where user is a member via CorRolePlan."""
        user = RoleFactory()
        plan = PlanGestionFactory(nom='Plan Member')
        CorRolePlan.objects.create(id_role=user, plan_de_gestion=plan)

        api_client.force_authenticate(user=user)

        response = api_client.get('/api/plans/plans/?scope=mine')
        assert response.status_code == status.HTTP_200_OK
        names = [p['nom'] for p in response.data['results']]
        assert 'Plan Member' in names

    def test_scope_mine_no_effect_for_super_admin(self, api_client):
        """scope=mine has no effect for super admins (they see everything)."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Any Plan')

        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/plans/plans/?scope=mine')
        assert response.status_code == status.HTTP_200_OK
        names = [p['nom'] for p in response.data['results']]
        assert 'Any Plan' in names
