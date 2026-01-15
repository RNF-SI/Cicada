"""
Factories for core app models.
Uses Factory Boy for test data generation.
"""
import factory
from factory.django import DjangoModelFactory

from apps.core.models import Nomenclature, TypeNomenclature


class TypeNomenclatureFactory(DjangoModelFactory):
    """Factory for TypeNomenclature model."""

    class Meta:
        model = TypeNomenclature
        django_get_or_create = ('mnemonique',)

    mnemonique = factory.Sequence(lambda n: f'TYPE_{n}')
    label = factory.LazyAttribute(lambda obj: f'Type {obj.mnemonique}')
    definition = factory.Faker('sentence', locale='fr_FR')


class NomenclatureFactory(DjangoModelFactory):
    """Factory for Nomenclature model."""

    class Meta:
        model = Nomenclature

    id_type = factory.SubFactory(TypeNomenclatureFactory)
    cd_nomenclature = factory.Sequence(lambda n: f'CODE_{n}')
    mnemonique = factory.Sequence(lambda n: f'MNEMONIC_{n}')
    label = factory.Sequence(lambda n: f'Nomenclature {n}')
    definition = factory.Faker('sentence', locale='fr_FR')
    actif = True


# Specialized nomenclature factories for specific types
class SiteTypeNomenclatureFactory(NomenclatureFactory):
    """Factory for site type nomenclatures (RNN, RNR, etc.)."""

    id_type = factory.SubFactory(
        TypeNomenclatureFactory,
        mnemonique='TYPE_SITE',
        label='Type de site'
    )
    cd_nomenclature = factory.Iterator(['RNN', 'RNR', 'PNR', 'ENS', 'APB'])
    label = factory.Iterator([
        'Réserve Naturelle Nationale',
        'Réserve Naturelle Régionale',
        'Parc Naturel Régional',
        'Espace Naturel Sensible',
        'Arrêté de Protection de Biotope'
    ])


class EvaluationTypeNomenclatureFactory(NomenclatureFactory):
    """Factory for evaluation type nomenclatures."""

    id_type = factory.SubFactory(
        TypeNomenclatureFactory,
        mnemonique='TYPE_EVALUATION',
        label="Type d'évaluation"
    )
    cd_nomenclature = factory.Iterator(['EVAL_INT', 'EVAL_FIN', 'EVAL_ANN'])
    label = factory.Iterator([
        'Évaluation intermédiaire',
        'Évaluation finale',
        'Évaluation annuelle'
    ])


class RedacteurTypeNomenclatureFactory(NomenclatureFactory):
    """Factory for redacteur type nomenclatures."""

    id_type = factory.SubFactory(
        TypeNomenclatureFactory,
        mnemonique='TYPE_REDACTEUR',
        label='Type de rédacteur'
    )
    cd_nomenclature = factory.Iterator(['BE', 'GEST', 'AUTRE'])
    label = factory.Iterator([
        "Bureau d'études",
        'Gestionnaire',
        'Autre'
    ])
