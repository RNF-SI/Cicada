"""
Factories for Enjeux, FCR, Facteurs d'Influence et Pressions.
Uses Factory Boy for test data generation.
"""
import factory
from factory.django import DjangoModelFactory

from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, Pression,
    EtatActuel, ObjectifLongTerme, NiveauExigence,
    CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
)
from apps.plans.models_indicateurs import (
    Indicateur, Metrique, Mesure, CorIndicateurTaxon,
)
from tests.factories.core import TypeNomenclatureFactory, NomenclatureFactory
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import RoleFactory


# =============================================================================
# Nomenclature factories for Enjeux
# =============================================================================

class CategorieEnjeuTypeFactory(TypeNomenclatureFactory):
    """Factory for TypeNomenclature CATEGORIE_ENJEU (get_or_create)."""

    mnemonique = 'CATEGORIE_ENJEU'
    label = 'Catégorie enjeu'


class NomenclatureEnjeuFactory(NomenclatureFactory):
    """Factory for Nomenclature with mnemonique=ENJEU."""

    class Meta:
        model = NomenclatureFactory._meta.model
        django_get_or_create = ('mnemonique',)

    id_type = factory.SubFactory(CategorieEnjeuTypeFactory)
    mnemonique = 'ENJEU'
    cd_nomenclature = 'ENJEU'
    label = 'Enjeu de conservation'


class NomenclatureFcrFactory(NomenclatureFactory):
    """Factory for Nomenclature with mnemonique=FCR."""

    class Meta:
        model = NomenclatureFactory._meta.model
        django_get_or_create = ('mnemonique',)

    id_type = factory.SubFactory(CategorieEnjeuTypeFactory)
    mnemonique = 'FCR'
    cd_nomenclature = 'FCR'
    label = 'Facteur Clé de Réussite'


class CategorieFcrTypeFactory(TypeNomenclatureFactory):
    """Factory for TypeNomenclature CATEGORIE_FCR."""

    mnemonique = 'CATEGORIE_FCR'
    label = 'Catégorie FCR'


class NomenclatureCategorieFcrFactory(NomenclatureFactory):
    """Factory for a specific FCR category nomenclature."""

    id_type = factory.SubFactory(CategorieFcrTypeFactory)
    cd_nomenclature = factory.Iterator(['CONN', 'ANCR', 'FONC', 'AUTR'])
    mnemonique = factory.Iterator(['CONNAISSANCE', 'ANCRAGE', 'FONCTIONNEMENT', 'AUTRE'])
    label = factory.Iterator([
        'Connaissance',
        'Ancrage territorial',
        'Fonctionnement',
        'Autre'
    ])


# =============================================================================
# Enjeu / FCR factories
# =============================================================================

class EnjeuFactory(DjangoModelFactory):
    """Factory for Enjeu model (conservation issue)."""

    class Meta:
        model = Enjeu

    id_pg = factory.SubFactory(PlanGestionFactory)
    id_categorie = factory.SubFactory(NomenclatureEnjeuFactory)
    libelle = factory.Sequence(lambda n: f'Enjeu Test {n}')
    intitule_court = factory.LazyAttribute(lambda obj: obj.libelle[:25])
    rang = 1
    categorie_ecologique = True
    habitat = False
    espece = False
    processus = False
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


class FcrFactory(EnjeuFactory):
    """Factory for FCR (Key Success Factor), inherits from EnjeuFactory."""

    id_categorie = factory.SubFactory(NomenclatureFcrFactory)
    libelle = factory.Sequence(lambda n: f'FCR Test {n}')
    rang = None
    categorie_ecologique = None
    id_categorie_fcr = factory.SubFactory(NomenclatureCategorieFcrFactory)


# =============================================================================
# Facteur d'Influence / Pression factories
# =============================================================================

class FacteurInfluenceFactory(DjangoModelFactory):
    """Factory for FacteurInfluence model."""

    class Meta:
        model = FacteurInfluence

    id_enjeu = factory.SubFactory(EnjeuFactory)
    libelle = factory.Sequence(lambda n: f'Facteur Influence Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


class PressionFactory(DjangoModelFactory):
    """Factory for Pression model."""

    class Meta:
        model = Pression

    id_facteur_influence = factory.SubFactory(FacteurInfluenceFactory)
    libelle = factory.Sequence(lambda n: f'Pression Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


# =============================================================================
# État Actuel / OLT / Niveau d'Exigence factories
# =============================================================================

class ObjectifLongTermeFactory(DjangoModelFactory):
    """Factory for ObjectifLongTerme model."""

    class Meta:
        model = ObjectifLongTerme

    id_enjeu = factory.SubFactory(EnjeuFactory)
    libelle = factory.Sequence(lambda n: f'OLT Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


class EtatActuelFactory(DjangoModelFactory):
    """Factory for EtatActuel model (1:1 with OLT)."""

    class Meta:
        model = EtatActuel

    id_olt = factory.SubFactory(ObjectifLongTermeFactory)
    libelle = factory.Sequence(lambda n: f'État Actuel Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


class NiveauExigenceFactory(DjangoModelFactory):
    """Factory for NiveauExigence model."""

    class Meta:
        model = NiveauExigence

    id_olt = factory.SubFactory(ObjectifLongTermeFactory)
    libelle = factory.Sequence(lambda n: f'Niveau Exigence Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


# =============================================================================
# Correlation table factories
# =============================================================================

class CorEnjeuTaxonFactory(DjangoModelFactory):
    """Factory for CorEnjeuTaxon (enjeu-taxon relationship)."""

    class Meta:
        model = CorEnjeuTaxon

    id_enjeu = factory.SubFactory(EnjeuFactory)
    cd_nom = factory.Sequence(lambda n: 100000 + n)
    nom_complet = factory.Sequence(lambda n: f'Taxon complet {n}')
    nom_vern = factory.Sequence(lambda n: f'Taxon vernaculaire {n}')


class CorEnjeuHabitatFactory(DjangoModelFactory):
    """Factory for CorEnjeuHabitat (enjeu-habitat relationship)."""

    class Meta:
        model = CorEnjeuHabitat

    id_enjeu = factory.SubFactory(EnjeuFactory)
    cd_hab = factory.Sequence(lambda n: f'HAB_{n:04d}')
    lb_hab_fr = factory.Sequence(lambda n: f'Habitat français {n}')


class CorEnjeuGeologieFactory(DjangoModelFactory):
    """Factory for CorEnjeuGeologie (enjeu-geology relationship)."""

    class Meta:
        model = CorEnjeuGeologie

    id_enjeu = factory.SubFactory(EnjeuFactory)
    id_inpg = factory.Sequence(lambda n: f'INPG_{n:04d}')
    nom = factory.Sequence(lambda n: f'Élément géologique {n}')


# =============================================================================
# Indicateur / Metrique / Mesure factories
# =============================================================================

class TypeIndicateurTypeFactory(TypeNomenclatureFactory):
    """Factory for TypeNomenclature TYPE_INDICATEUR."""

    mnemonique = 'TYPE_INDICATEUR'
    label = 'Type d\'indicateur'


class NomenclatureTypeIndicateurFactory(NomenclatureFactory):
    """Factory for a specific indicateur type nomenclature."""

    id_type = factory.SubFactory(TypeIndicateurTypeFactory)
    cd_nomenclature = factory.Iterator(['ETAT', 'PRESSION', 'REPONSE'])
    mnemonique = factory.Iterator(['ETAT', 'PRESSION', 'REPONSE'])
    label = factory.Iterator(['État', 'Pression', 'Réponse'])


class TypeMetriqueTypeFactory(TypeNomenclatureFactory):
    """Factory for TypeNomenclature TYPE_METRIQUE."""

    mnemonique = 'TYPE_METRIQUE'
    label = 'Type de métrique'


class NomenclatureTypeMetriqueFactory(NomenclatureFactory):
    """Factory for a specific metrique type nomenclature."""

    id_type = factory.SubFactory(TypeMetriqueTypeFactory)
    cd_nomenclature = factory.Iterator(['NUMERIQUE', 'QUALITATIF', 'BOOLEEN'])
    mnemonique = factory.Iterator(['NUMERIQUE', 'QUALITATIF', 'BOOLEEN'])
    label = factory.Iterator(['Numérique', 'Qualitatif', 'Booléen'])


class IndicateurFactory(DjangoModelFactory):
    """Factory for Indicateur model."""

    class Meta:
        model = Indicateur

    id_ne = factory.SubFactory(NiveauExigenceFactory)
    nom_indicateur = factory.Sequence(lambda n: f'Indicateur Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    type_indicateur = factory.SubFactory(NomenclatureTypeIndicateurFactory)
    est_standardise = False
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


class MetriqueFactory(DjangoModelFactory):
    """Factory for Metrique model."""

    class Meta:
        model = Metrique

    id_indicateur = factory.SubFactory(IndicateurFactory)
    nom_metrique = factory.Sequence(lambda n: f'Métrique Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    type_metrique = factory.SubFactory(NomenclatureTypeMetriqueFactory)
    unite = '%'
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


class MesureFactory(DjangoModelFactory):
    """Factory for Mesure model."""

    class Meta:
        model = Mesure

    id_metrique = factory.SubFactory(MetriqueFactory)
    valeur = factory.Sequence(lambda n: str(50 + n))
    date_mesure = factory.Faker('date_object')
    commentaire = factory.Faker('sentence', locale='fr_FR')
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


class CorIndicateurTaxonFactory(DjangoModelFactory):
    """Factory for CorIndicateurTaxon."""

    class Meta:
        model = CorIndicateurTaxon

    id_indicateur = factory.SubFactory(IndicateurFactory)
    cd_nom = factory.Sequence(lambda n: 200000 + n)
    nom_complet = factory.Sequence(lambda n: f'Taxon indicateur {n}')
    nom_vern = factory.Sequence(lambda n: f'Taxon vern indicateur {n}')
