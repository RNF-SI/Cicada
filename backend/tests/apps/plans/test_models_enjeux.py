"""
Tests unitaires pour les modèles Enjeux, FCR, Facteurs d'Influence et Pressions.
"""
import pytest
from django.db import IntegrityError
from django.core.exceptions import ValidationError

from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, Pression,
    ObjectifLongTerme, NiveauExigence,
    CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
)
from tests.factories.enjeux import (
    EnjeuFactory, FcrFactory,
    FacteurInfluenceFactory, PressionFactory,
    ObjectifLongTermeFactory, NiveauExigenceFactory,
    CorEnjeuTaxonFactory, CorEnjeuHabitatFactory, CorEnjeuGeologieFactory,
    NomenclatureEnjeuFactory, NomenclatureFcrFactory,
    IndicateurFactory, MetriqueFactory, MesureFactory, CorIndicateurTaxonFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import RoleFactory


# =============================================================================
# TestEnjeuModel
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestEnjeuModel:
    """Tests for the Enjeu model."""

    def test_create_enjeu_with_required_fields(self):
        """Test creating an enjeu with required fields."""
        enjeu = EnjeuFactory()
        assert enjeu.id_enjeu is not None
        assert enjeu.libelle is not None
        assert enjeu.id_pg is not None
        assert enjeu.id_categorie is not None

    def test_str_returns_libelle_and_plan(self):
        """Test __str__ returns libelle with plan info."""
        plan = PlanGestionFactory(nom='Mon Plan')
        enjeu = EnjeuFactory(libelle='Protection des zones humides', id_pg=plan)
        assert 'Protection des zones humides' in str(enjeu)
        assert str(plan) in str(enjeu)

    def test_is_enjeu_true_for_enjeu_category(self):
        """Test is_enjeu() returns True for ENJEU category."""
        enjeu = EnjeuFactory()
        assert enjeu.is_enjeu() is True

    def test_is_enjeu_false_for_fcr_category(self):
        """Test is_enjeu() returns False for FCR category."""
        fcr = FcrFactory()
        assert fcr.is_enjeu() is False

    def test_is_fcr_true_for_fcr_category(self):
        """Test is_fcr() returns True for FCR category."""
        fcr = FcrFactory()
        assert fcr.is_fcr() is True

    def test_is_fcr_false_for_enjeu_category(self):
        """Test is_fcr() returns False for ENJEU category."""
        enjeu = EnjeuFactory()
        assert enjeu.is_fcr() is False

    def test_nb_facteurs_influence_zero(self):
        """Test nb_facteurs_influence returns 0 when no facteurs."""
        enjeu = EnjeuFactory()
        assert enjeu.nb_facteurs_influence == 0

    def test_nb_facteurs_influence_after_adding(self):
        """Test nb_facteurs_influence returns correct count after adding facteurs."""
        enjeu = EnjeuFactory()
        FacteurInfluenceFactory(id_enjeu=enjeu)
        FacteurInfluenceFactory(id_enjeu=enjeu)
        assert enjeu.nb_facteurs_influence == 2

    def test_cascade_delete_facteurs_influence(self):
        """Test deleting enjeu cascades to facteurs_influence."""
        enjeu = EnjeuFactory()
        FacteurInfluenceFactory(id_enjeu=enjeu)
        FacteurInfluenceFactory(id_enjeu=enjeu)
        enjeu_id = enjeu.id_enjeu
        enjeu.delete()
        assert not FacteurInfluence.objects.filter(id_enjeu_id=enjeu_id).exists()

    def test_cascade_delete_taxons(self):
        """Test deleting enjeu cascades to cor_enjeu_taxon."""
        enjeu = EnjeuFactory()
        CorEnjeuTaxonFactory(id_enjeu=enjeu)
        enjeu_id = enjeu.id_enjeu
        enjeu.delete()
        assert not CorEnjeuTaxon.objects.filter(id_enjeu_id=enjeu_id).exists()

    def test_cascade_delete_habitats(self):
        """Test deleting enjeu cascades to cor_enjeu_habitat."""
        enjeu = EnjeuFactory()
        CorEnjeuHabitatFactory(id_enjeu=enjeu)
        enjeu_id = enjeu.id_enjeu
        enjeu.delete()
        assert not CorEnjeuHabitat.objects.filter(id_enjeu_id=enjeu_id).exists()

    def test_default_boolean_values(self):
        """Test default values for habitat, espece, processus."""
        enjeu = EnjeuFactory()
        assert enjeu.habitat is False
        assert enjeu.espece is False
        assert enjeu.processus is False

    def test_audit_date_ajout_auto(self):
        """Test date_ajout is auto-populated on creation."""
        enjeu = EnjeuFactory()
        assert enjeu.date_ajout is not None

    def test_audit_date_maj_auto(self):
        """Test date_maj is auto-populated on save."""
        enjeu = EnjeuFactory()
        assert enjeu.date_maj is not None

    def test_rang_validator_min(self):
        """Test rang validator rejects values below 1."""
        enjeu = EnjeuFactory.build(rang=0)
        with pytest.raises(ValidationError):
            enjeu.full_clean()

    def test_rang_validator_max(self):
        """Test rang validator rejects values above 3."""
        enjeu = EnjeuFactory.build(rang=4)
        with pytest.raises(ValidationError):
            enjeu.full_clean()

    def test_rang_valid_values(self):
        """Test rang accepts valid values 1, 2, 3."""
        for rang in [1, 2, 3]:
            enjeu = EnjeuFactory(rang=rang)
            assert enjeu.rang == rang

    def test_categorie_label_property(self):
        """Test categorie_label returns the nomenclature label."""
        enjeu = EnjeuFactory()
        assert enjeu.categorie_label is not None

    def test_fcr_with_categorie_fcr(self):
        """Test FCR can have a categorie_fcr."""
        fcr = FcrFactory()
        assert fcr.id_categorie_fcr is not None

    def test_ordering_by_rang_and_libelle(self):
        """Test default ordering is by rang then libelle."""
        plan = PlanGestionFactory()
        cat = NomenclatureEnjeuFactory()
        user = RoleFactory()
        EnjeuFactory(id_pg=plan, rang=3, libelle='Zzz', id_categorie=cat, id_utilisateur_ajout=user)
        EnjeuFactory(id_pg=plan, rang=1, libelle='Aaa', id_categorie=cat, id_utilisateur_ajout=user)
        EnjeuFactory(id_pg=plan, rang=1, libelle='Bbb', id_categorie=cat, id_utilisateur_ajout=user)

        enjeux = list(Enjeu.objects.filter(id_pg=plan).order_by('rang', 'libelle'))
        assert enjeux[0].libelle == 'Aaa'
        assert enjeux[1].libelle == 'Bbb'
        assert enjeux[2].libelle == 'Zzz'


# =============================================================================
# TestFacteurInfluenceModel
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestFacteurInfluenceModel:
    """Tests for the FacteurInfluence model."""

    def test_create_with_required_fields(self):
        """Test creating a facteur d'influence with required fields."""
        facteur = FacteurInfluenceFactory()
        assert facteur.id_facteur_influence is not None
        assert facteur.libelle is not None
        assert facteur.id_enjeu is not None

    def test_str_returns_libelle_and_enjeu(self):
        """Test __str__ returns libelle with enjeu info."""
        enjeu = EnjeuFactory(libelle='Mon Enjeu')
        facteur = FacteurInfluenceFactory(libelle='Changement climatique', id_enjeu=enjeu)
        assert 'Changement climatique' in str(facteur)

    def test_fk_enjeu_cascade_delete(self):
        """Test FK to Enjeu is CASCADE."""
        enjeu = EnjeuFactory()
        facteur = FacteurInfluenceFactory(id_enjeu=enjeu)
        facteur_id = facteur.id_facteur_influence
        enjeu.delete()
        assert not FacteurInfluence.objects.filter(id_facteur_influence=facteur_id).exists()

    def test_reverse_relation_pressions(self):
        """Test reverse relation 'pressions' works."""
        facteur = FacteurInfluenceFactory()
        PressionFactory(id_facteur_influence=facteur)
        PressionFactory(id_facteur_influence=facteur)
        assert facteur.pressions.count() == 2

    def test_cascade_delete_pressions(self):
        """Test deleting facteur cascades to pressions."""
        facteur = FacteurInfluenceFactory()
        PressionFactory(id_facteur_influence=facteur)
        facteur_id = facteur.id_facteur_influence
        facteur.delete()
        assert not Pression.objects.filter(id_facteur_influence_id=facteur_id).exists()

    def test_description_optional(self):
        """Test description is optional (null=True, blank=True)."""
        facteur = FacteurInfluenceFactory(description=None)
        assert facteur.description is None

    def test_audit_dates_auto(self):
        """Test audit dates are auto-populated."""
        facteur = FacteurInfluenceFactory()
        assert facteur.date_ajout is not None
        assert facteur.date_maj is not None

    def test_ordering_by_libelle(self):
        """Test default ordering is by libelle."""
        enjeu = EnjeuFactory()
        user = RoleFactory()
        FacteurInfluenceFactory(id_enjeu=enjeu, libelle='Zzz', id_utilisateur_ajout=user)
        FacteurInfluenceFactory(id_enjeu=enjeu, libelle='Aaa', id_utilisateur_ajout=user)

        facteurs = list(FacteurInfluence.objects.filter(id_enjeu=enjeu).order_by('libelle'))
        assert facteurs[0].libelle == 'Aaa'
        assert facteurs[1].libelle == 'Zzz'


# =============================================================================
# TestPressionModel
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestPressionModel:
    """Tests for the Pression model."""

    def test_create_with_required_fields(self):
        """Test creating a pression with required fields."""
        pression = PressionFactory()
        assert pression.id_pression is not None
        assert pression.libelle is not None
        assert pression.id_facteur_influence is not None

    def test_str_returns_libelle_and_facteur(self):
        """Test __str__ returns libelle with facteur info."""
        facteur = FacteurInfluenceFactory(libelle='Mon Facteur')
        pression = PressionFactory(libelle='Pollution', id_facteur_influence=facteur)
        assert 'Pollution' in str(pression)

    def test_fk_facteur_cascade_delete(self):
        """Test FK to FacteurInfluence is CASCADE."""
        facteur = FacteurInfluenceFactory()
        pression = PressionFactory(id_facteur_influence=facteur)
        pression_id = pression.id_pression
        facteur.delete()
        assert not Pression.objects.filter(id_pression=pression_id).exists()

    def test_id_pressref_optional(self):
        """Test id_pressref is optional."""
        pression = PressionFactory(id_pressref=None)
        assert pression.id_pressref is None

    def test_id_pressref_with_value(self):
        """Test id_pressref can have a value."""
        pression = PressionFactory(id_pressref='PRESS_001')
        assert pression.id_pressref == 'PRESS_001'

    def test_description_optional(self):
        """Test description is optional."""
        pression = PressionFactory(description=None)
        assert pression.description is None

    def test_audit_dates_auto(self):
        """Test audit dates are auto-populated."""
        pression = PressionFactory()
        assert pression.date_ajout is not None
        assert pression.date_maj is not None

    def test_ordering_by_libelle(self):
        """Test default ordering is by libelle."""
        facteur = FacteurInfluenceFactory()
        user = RoleFactory()
        PressionFactory(id_facteur_influence=facteur, libelle='Zzz', id_utilisateur_ajout=user)
        PressionFactory(id_facteur_influence=facteur, libelle='Aaa', id_utilisateur_ajout=user)

        pressions = list(Pression.objects.filter(id_facteur_influence=facteur).order_by('libelle'))
        assert pressions[0].libelle == 'Aaa'
        assert pressions[1].libelle == 'Zzz'


# =============================================================================
# TestObjectifLongTermeModel
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestObjectifLongTermeModel:
    """Tests for the ObjectifLongTerme model (OLT links directly to Enjeu via id_enjeu)."""

    def test_create_with_required_fields(self):
        """Test creating an OLT with required fields."""
        olt = ObjectifLongTermeFactory()
        assert olt.id_olt is not None
        assert olt.libelle is not None
        assert olt.id_enjeu is not None

    def test_str_returns_libelle(self):
        """Test __str__ returns libelle with enjeu info."""
        enjeu = EnjeuFactory(libelle='Mon Enjeu')
        olt = ObjectifLongTermeFactory(libelle='Restaurer les habitats', id_enjeu=enjeu)
        assert 'Restaurer les habitats' in str(olt)

    def test_fk_enjeu_cascade_delete(self):
        """Test FK to Enjeu is CASCADE: deleting enjeu cascades to OLT."""
        enjeu = EnjeuFactory()
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu)
        olt_id = olt.id_olt
        enjeu.delete()
        assert not ObjectifLongTerme.objects.filter(id_olt=olt_id).exists()

    def test_reverse_relation_niveaux_exigence(self):
        """Test reverse relation 'niveaux_exigence' works."""
        olt = ObjectifLongTermeFactory()
        NiveauExigenceFactory(id_olt=olt)
        NiveauExigenceFactory(id_olt=olt)
        assert olt.niveaux_exigence.count() == 2

    def test_cascade_delete_niveaux(self):
        """Test deleting OLT cascades to niveaux d'exigence."""
        olt = ObjectifLongTermeFactory()
        NiveauExigenceFactory(id_olt=olt)
        olt_id = olt.id_olt
        olt.delete()
        assert not NiveauExigence.objects.filter(id_olt_id=olt_id).exists()

    def test_delete_olt_does_not_cascade_to_enjeu(self):
        """Test deleting OLT does NOT cascade to parent Enjeu."""
        enjeu = EnjeuFactory()
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu)
        enjeu_id = enjeu.id_enjeu
        olt.delete()
        assert Enjeu.objects.filter(id_enjeu=enjeu_id).exists()

    def test_description_optional(self):
        """Test description is optional."""
        olt = ObjectifLongTermeFactory(description=None)
        assert olt.description is None

    def test_audit_dates_auto(self):
        """Test audit dates are auto-populated."""
        olt = ObjectifLongTermeFactory()
        assert olt.date_ajout is not None
        assert olt.date_maj is not None

    def test_full_cascade_from_enjeu(self):
        """Test deleting enjeu cascades through OLT and OLT → NE."""
        enjeu = EnjeuFactory()
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu)
        NiveauExigenceFactory(id_olt=olt)
        enjeu_id = enjeu.id_enjeu
        enjeu.delete()
        assert not ObjectifLongTerme.objects.filter(id_enjeu_id=enjeu_id).exists()
        assert not NiveauExigence.objects.filter(id_olt=olt.id_olt).exists()


# =============================================================================
# TestNiveauExigenceModel
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestNiveauExigenceModel:
    """Tests for the NiveauExigence model."""

    def test_create_with_required_fields(self):
        """Test creating a niveau d'exigence with required fields."""
        ne = NiveauExigenceFactory()
        assert ne.id_ne is not None
        assert ne.libelle is not None
        assert ne.id_olt is not None

    def test_str_returns_libelle(self):
        """Test __str__ returns libelle with OLT info."""
        olt = ObjectifLongTermeFactory(libelle='Mon OLT')
        ne = NiveauExigenceFactory(libelle='Surface ≥ 70%', id_olt=olt)
        assert 'Surface ≥ 70%' in str(ne)

    def test_fk_olt_cascade_delete(self):
        """Test FK to ObjectifLongTerme is CASCADE."""
        olt = ObjectifLongTermeFactory()
        ne = NiveauExigenceFactory(id_olt=olt)
        ne_id = ne.id_ne
        olt.delete()
        assert not NiveauExigence.objects.filter(id_ne=ne_id).exists()

    def test_description_optional(self):
        """Test description is optional."""
        ne = NiveauExigenceFactory(description=None)
        assert ne.description is None

    def test_audit_dates_auto(self):
        """Test audit dates are auto-populated."""
        ne = NiveauExigenceFactory()
        assert ne.date_ajout is not None
        assert ne.date_maj is not None


# =============================================================================
# TestCorrelationModels
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestCorEnjeuTaxon:
    """Tests for the CorEnjeuTaxon model."""

    def test_create(self):
        """Test creating a cor_enjeu_taxon."""
        cor = CorEnjeuTaxonFactory()
        assert cor.id is not None
        assert cor.cd_nom is not None

    def test_unique_together(self):
        """Test unique_together constraint on (id_enjeu, cd_nom)."""
        enjeu = EnjeuFactory()
        CorEnjeuTaxonFactory(id_enjeu=enjeu, cd_nom=12345)
        with pytest.raises(IntegrityError):
            CorEnjeuTaxonFactory(id_enjeu=enjeu, cd_nom=12345)

    def test_cascade_delete_on_enjeu(self):
        """Test cascade delete when enjeu is deleted."""
        enjeu = EnjeuFactory()
        CorEnjeuTaxonFactory(id_enjeu=enjeu)
        enjeu_id = enjeu.id_enjeu
        enjeu.delete()
        assert not CorEnjeuTaxon.objects.filter(id_enjeu_id=enjeu_id).exists()

    def test_str(self):
        """Test __str__ method."""
        cor = CorEnjeuTaxonFactory(cd_nom=99999)
        assert '99999' in str(cor)


@pytest.mark.django_db
@pytest.mark.unit
class TestCorEnjeuHabitat:
    """Tests for the CorEnjeuHabitat model."""

    def test_create(self):
        """Test creating a cor_enjeu_habitat."""
        cor = CorEnjeuHabitatFactory()
        assert cor.id is not None
        assert cor.cd_hab is not None

    def test_unique_together(self):
        """Test unique_together constraint on (id_enjeu, cd_hab)."""
        enjeu = EnjeuFactory()
        CorEnjeuHabitatFactory(id_enjeu=enjeu, cd_hab='HAB_001')
        with pytest.raises(IntegrityError):
            CorEnjeuHabitatFactory(id_enjeu=enjeu, cd_hab='HAB_001')

    def test_cascade_delete_on_enjeu(self):
        """Test cascade delete when enjeu is deleted."""
        enjeu = EnjeuFactory()
        CorEnjeuHabitatFactory(id_enjeu=enjeu)
        enjeu_id = enjeu.id_enjeu
        enjeu.delete()
        assert not CorEnjeuHabitat.objects.filter(id_enjeu_id=enjeu_id).exists()


@pytest.mark.django_db
@pytest.mark.unit
class TestCorEnjeuGeologie:
    """Tests for the CorEnjeuGeologie model."""

    def test_create(self):
        """Test creating a cor_enjeu_geologie."""
        cor = CorEnjeuGeologieFactory()
        assert cor.id is not None
        assert cor.id_inpg is not None

    def test_unique_together(self):
        """Test unique_together constraint on (id_enjeu, id_inpg)."""
        enjeu = EnjeuFactory()
        CorEnjeuGeologieFactory(id_enjeu=enjeu, id_inpg='GEO_001')
        with pytest.raises(IntegrityError):
            CorEnjeuGeologieFactory(id_enjeu=enjeu, id_inpg='GEO_001')

    def test_cascade_delete_on_enjeu(self):
        """Test cascade delete when enjeu is deleted."""
        enjeu = EnjeuFactory()
        CorEnjeuGeologieFactory(id_enjeu=enjeu)
        enjeu_id = enjeu.id_enjeu
        enjeu.delete()
        assert not CorEnjeuGeologie.objects.filter(id_enjeu_id=enjeu_id).exists()


# =============================================================================
# TestIndicateurModel
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestIndicateurModel:
    """Tests for Indicateur model."""

    def test_create_indicateur(self):
        """Test creating an indicateur."""
        indicateur = IndicateurFactory()
        assert indicateur.id_indicateur is not None
        assert indicateur.nom_indicateur.startswith('Indicateur Test')

    def test_indicateur_str(self):
        """Test string representation."""
        indicateur = IndicateurFactory(nom_indicateur='Test Indicateur')
        assert 'Test Indicateur' in str(indicateur)

    def test_cascade_delete_from_niveau_exigence(self):
        """Test cascade deletion from NiveauExigence."""
        from apps.plans.models_indicateurs import Indicateur
        indicateur = IndicateurFactory()
        ne = indicateur.id_ne
        ne.delete()
        assert not Indicateur.objects.filter(id_indicateur=indicateur.id_indicateur).exists()

    def test_description_optional(self):
        """Test description is optional (null=True, blank=True)."""
        indicateur = IndicateurFactory(description=None)
        assert indicateur.description is None

    def test_audit_dates_auto(self):
        """Test audit dates are auto-populated."""
        indicateur = IndicateurFactory()
        assert indicateur.date_ajout is not None
        assert indicateur.date_maj is not None

    def test_est_standardise_default_false(self):
        """Test est_standardise defaults to False."""
        indicateur = IndicateurFactory()
        assert indicateur.est_standardise is False

    def test_reverse_relation_metriques(self):
        """Test reverse relation 'metriques' works."""
        indicateur = IndicateurFactory()
        MetriqueFactory(id_indicateur=indicateur)
        MetriqueFactory(id_indicateur=indicateur)
        assert indicateur.metriques.count() == 2

    def test_ordering_by_nom(self):
        """Test default ordering is by nom_indicateur."""
        from apps.plans.models_indicateurs import Indicateur
        ne = NiveauExigenceFactory()
        user = RoleFactory()
        IndicateurFactory(id_ne=ne, nom_indicateur='Zzz Indicateur', id_utilisateur_ajout=user)
        IndicateurFactory(id_ne=ne, nom_indicateur='Aaa Indicateur', id_utilisateur_ajout=user)
        indicateurs = list(Indicateur.objects.filter(id_ne=ne).order_by('nom_indicateur'))
        assert indicateurs[0].nom_indicateur == 'Aaa Indicateur'
        assert indicateurs[1].nom_indicateur == 'Zzz Indicateur'


# =============================================================================
# TestMetriqueModel
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestMetriqueModel:
    """Tests for Metrique model."""

    def test_create_metrique(self):
        """Test creating a metrique."""
        metrique = MetriqueFactory()
        assert metrique.id_metrique is not None
        assert metrique.nom_metrique.startswith('Métrique Test')

    def test_metrique_str(self):
        """Test string representation."""
        metrique = MetriqueFactory(nom_metrique='Test Métrique')
        assert 'Test Métrique' in str(metrique)

    def test_cascade_delete_from_indicateur(self):
        """Test cascade deletion from Indicateur."""
        from apps.plans.models_indicateurs import Metrique
        metrique = MetriqueFactory()
        indicateur = metrique.id_indicateur
        indicateur.delete()
        assert not Metrique.objects.filter(id_metrique=metrique.id_metrique).exists()

    def test_description_optional(self):
        """Test description is optional (null=True, blank=True)."""
        metrique = MetriqueFactory(description=None)
        assert metrique.description is None

    def test_unite_optional(self):
        """Test unite is optional (null=True, blank=True)."""
        metrique = MetriqueFactory(unite=None)
        assert metrique.unite is None

    def test_audit_dates_auto(self):
        """Test audit dates are auto-populated."""
        metrique = MetriqueFactory()
        assert metrique.date_ajout is not None
        assert metrique.date_maj is not None

    def test_reverse_relation_mesures(self):
        """Test reverse relation 'mesures' works."""
        metrique = MetriqueFactory()
        MesureFactory(id_metrique=metrique)
        MesureFactory(id_metrique=metrique)
        assert metrique.mesures.count() == 2

    def test_ordering_by_nom(self):
        """Test default ordering is by nom_metrique."""
        from apps.plans.models_indicateurs import Metrique
        indicateur = IndicateurFactory()
        user = RoleFactory()
        MetriqueFactory(id_indicateur=indicateur, nom_metrique='Zzz Métrique', id_utilisateur_ajout=user)
        MetriqueFactory(id_indicateur=indicateur, nom_metrique='Aaa Métrique', id_utilisateur_ajout=user)
        metriques = list(Metrique.objects.filter(id_indicateur=indicateur).order_by('nom_metrique'))
        assert metriques[0].nom_metrique == 'Aaa Métrique'
        assert metriques[1].nom_metrique == 'Zzz Métrique'


# =============================================================================
# TestMesureModel
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestMesureModel:
    """Tests for Mesure model."""

    def test_create_mesure(self):
        """Test creating a mesure."""
        mesure = MesureFactory()
        assert mesure.id_mesure is not None

    def test_mesure_str(self):
        """Test string representation."""
        mesure = MesureFactory(valeur='42.5')
        assert '42.5' in str(mesure)

    def test_cascade_delete_from_metrique(self):
        """Test cascade deletion from Metrique."""
        from apps.plans.models_indicateurs import Mesure
        mesure = MesureFactory()
        metrique = mesure.id_metrique
        metrique.delete()
        assert not Mesure.objects.filter(id_mesure=mesure.id_mesure).exists()

    def test_commentaire_optional(self):
        """Test commentaire is optional (null=True, blank=True)."""
        mesure = MesureFactory(commentaire=None)
        assert mesure.commentaire is None

    def test_date_mesure_optional(self):
        """Test date_mesure is optional (null=True, blank=True)."""
        mesure = MesureFactory(date_mesure=None)
        assert mesure.date_mesure is None

    def test_audit_dates_auto(self):
        """Test audit dates are auto-populated."""
        mesure = MesureFactory()
        assert mesure.date_ajout is not None
        assert mesure.date_maj is not None


# =============================================================================
# TestCorIndicateurTaxon
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestCorIndicateurTaxon:
    """Tests for CorIndicateurTaxon unique_together."""

    def test_create(self):
        """Test creating a cor_indicateur_taxon."""
        cor = CorIndicateurTaxonFactory()
        assert cor.id is not None
        assert cor.cd_nom is not None

    def test_unique_together(self):
        """Test unique_together constraint on (id_indicateur, cd_nom)."""
        from apps.plans.models_indicateurs import CorIndicateurTaxon
        cor = CorIndicateurTaxonFactory()
        with pytest.raises(Exception):
            CorIndicateurTaxon.objects.create(
                id_indicateur=cor.id_indicateur,
                cd_nom=cor.cd_nom,
            )

    def test_cascade_delete_on_indicateur(self):
        """Test cascade delete when indicateur is deleted."""
        from apps.plans.models_indicateurs import CorIndicateurTaxon
        indicateur = IndicateurFactory()
        CorIndicateurTaxonFactory(id_indicateur=indicateur)
        indicateur_id = indicateur.id_indicateur
        indicateur.delete()
        assert not CorIndicateurTaxon.objects.filter(id_indicateur_id=indicateur_id).exists()

    def test_str(self):
        """Test __str__ method."""
        cor = CorIndicateurTaxonFactory(cd_nom=99999)
        assert '99999' in str(cor)
