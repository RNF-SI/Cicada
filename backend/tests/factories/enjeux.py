"""
Factories for Enjeux, FCR, Facteurs d'Influence et Pressions.
Uses Factory Boy for test data generation.
"""
import factory
from factory.django import DjangoModelFactory

from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, Pression,
    ObjectifLongTerme, NiveauExigence,
    ObjectifOperationnel, ResultatAttendu,
    CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
    CorFacteurEnjeu,
)
from apps.plans.models_indicateurs import (
    Indicateur, Metrique, Mesure,
)
from apps.plans.models_operations import (
    Protocole, SuiviInventaire, Operation,
    OperationAnnee, OperationAnneeOrganisme,
    RealisationOperationAnnee, RealisationOperationAnneeOrganisme,
)
from apps.users.models import BibOrganismes
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
    """Factory for FacteurInfluence model.

    #552 — le facteur n'a plus de FK `id_enjeu` : il est partagé entre plusieurs
    enjeux via `CorFacteurEnjeu`. Le kwarg `id_enjeu=` reste accepté (et crée la
    liaison) car c'est ainsi que les tests expriment « un facteur sous cet
    enjeu » ; sans argument, un enjeu est créé, comme avant.
    Pour un facteur partagé : `FacteurInfluenceFactory(enjeux=[e1, e2])`.
    """

    class Meta:
        model = FacteurInfluence
        skip_postgeneration_save = True

    libelle = factory.Sequence(lambda n: f'Facteur Influence Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)

    # NB : les hooks post_generation s'exécutent dans l'ordre de déclaration.
    # `enjeux` doit donc passer AVANT `id_enjeu`, qui ne crée un enjeu par
    # défaut que si aucune liaison n'a déjà été posée.

    @factory.post_generation
    def enjeux(obj, create, extracted, **kwargs):
        """Rattache le facteur à plusieurs enjeux (partage, #552)."""
        if not create or not extracted:
            return
        for enjeu in extracted:
            CorFacteurEnjeu.objects.get_or_create(
                id_facteur_influence=obj, id_enjeu=enjeu
            )

    @factory.post_generation
    def id_enjeu(obj, create, extracted, **kwargs):
        """Rattache le facteur à un enjeu unique (cas courant)."""
        if not create:
            return
        if extracted is not None:
            CorFacteurEnjeu.objects.get_or_create(
                id_facteur_influence=obj, id_enjeu=extracted
            )
        elif not obj.enjeux.exists():
            CorFacteurEnjeu.objects.create(
                id_facteur_influence=obj, id_enjeu=EnjeuFactory()
            )


class PressionFactory(DjangoModelFactory):
    """Factory for Pression model."""

    class Meta:
        model = Pression

    id_facteur_influence = factory.SubFactory(FacteurInfluenceFactory)
    libelle = factory.Sequence(lambda n: f'Pression Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


# =============================================================================
# OLT / Niveau d'Exigence factories
# =============================================================================

class ObjectifLongTermeFactory(DjangoModelFactory):
    """Factory for ObjectifLongTerme model."""

    class Meta:
        model = ObjectifLongTerme

    id_enjeu = factory.SubFactory(EnjeuFactory)
    libelle = factory.Sequence(lambda n: f'OLT Test {n}')
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
# Objectif Opérationnel / Résultat Attendu factories
# =============================================================================

class ObjectifOperationnelFactory(DjangoModelFactory):
    """Factory for ObjectifOperationnel model."""

    class Meta:
        model = ObjectifOperationnel

    libelle = factory.Sequence(lambda n: f'OO Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)

    @factory.post_generation
    def pressions(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.pressions.set(extracted)


class ResultatAttenduFactory(DjangoModelFactory):
    """Factory for ResultatAttendu model."""

    class Meta:
        model = ResultatAttendu

    id_oo = factory.SubFactory(ObjectifOperationnelFactory)
    libelle = factory.Sequence(lambda n: f'Résultat Attendu Test {n}')
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
    cd_nomenclature = factory.Iterator(['NUMERIQUE', 'CHIFFRE', 'TEXTE'])
    mnemonique = factory.Iterator(['NUMERIQUE', 'CHIFFRE', 'TEXTE'])
    label = factory.Iterator(['Intervalle numérique', 'Chiffre', 'Texte'])


class FormatMetriqueTypeFactory(TypeNomenclatureFactory):
    """Factory for TypeNomenclature FORMAT_METRIQUE (#452)."""

    mnemonique = 'FORMAT_METRIQUE'
    label = 'Format de métrique'


class NomenclatureFormatMetriqueFactory(NomenclatureFactory):
    """Factory for a FORMAT_METRIQUE nomenclature (SIMPLE / GRILLE) — #452."""

    class Meta:
        model = NomenclatureFactory._meta.model
        django_get_or_create = ('mnemonique',)

    id_type = factory.SubFactory(FormatMetriqueTypeFactory)
    cd_nomenclature = 'SIMPLE'
    mnemonique = 'SIMPLE'
    label = 'Simple'


class IndicateurFactory(DjangoModelFactory):
    """Factory for Indicateur model (linked to NE by default)."""

    class Meta:
        model = Indicateur

    id_ne = factory.SubFactory(NiveauExigenceFactory)
    id_resultat_attendu = None
    nom_indicateur = factory.Sequence(lambda n: f'Indicateur Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    type_indicateur = factory.SubFactory(NomenclatureTypeIndicateurFactory)
    est_standardise = False
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


class IndicateurPressionFactory(IndicateurFactory):
    """Factory for Indicateur linked to a ResultatAttendu (pression indicator)."""

    id_ne = None
    id_resultat_attendu = factory.SubFactory(ResultatAttenduFactory)


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


# =============================================================================
# Operation factories
# =============================================================================

class ProtocoleFactory(DjangoModelFactory):
    """Factory for Protocole model."""

    class Meta:
        model = Protocole

    protocole_dans_campanule = None
    protocole_campanule_nom = ''
    cd_protocole_campanule = None
    nb_etp_cycle = None
    nom_protocole = ''
    respect_protocole = None
    justification_non_respect = ''
    differences_protocole = ''
    description_protocole = ''
    objectif_protocole = ''
    periode_echantillonnage = ''
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


class SuiviInventaireFactory(DjangoModelFactory):
    """Factory for SuiviInventaire model."""

    class Meta:
        model = SuiviInventaire

    intitule = factory.Sequence(lambda n: f'Suivi Test {n}')
    actif = True
    id_type_action = None
    objectif_principal = 'OBJ_ETAT_CONSERVATION'
    cibles_principales = 'ESPECES'
    taxon_taxref = ''
    date_lancement_suivi = None
    id_protocole = None
    outil_bancarisation = ''
    outil_saisie = ''
    transmission_donnee = None
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)


class PrioriteOperationTypeFactory(TypeNomenclatureFactory):
    """Factory for TypeNomenclature PRIORITE_OPERATION."""

    mnemonique = 'PRIORITE_OPERATION'
    label = "Priorité d'opération"


class NomenclaturePrioriteOperationFactory(NomenclatureFactory):
    """Factory for a specific operation priority nomenclature."""

    id_type = factory.SubFactory(PrioriteOperationTypeFactory)
    cd_nomenclature = factory.Iterator(['P1', 'P2', 'P3'])
    mnemonique = factory.Iterator(['PRIORITE_1', 'PRIORITE_2', 'PRIORITE_3'])
    label = factory.Iterator(['Priorité 1', 'Priorité 2', 'Priorité 3'])


class OperationFactory(DjangoModelFactory):
    """Factory for Operation model."""

    class Meta:
        model = Operation

    libelle = factory.Sequence(lambda n: f'Opération Test {n}')
    description = factory.Faker('sentence', locale='fr_FR')
    id_priorite = factory.SubFactory(NomenclaturePrioriteOperationFactory)
    code_operation = factory.Sequence(lambda n: f'OP-{n:03d}')
    id_referentiel_operations = factory.Sequence(lambda n: f'REF-{n:03d}')
    annee_min = 2024
    annee_max = 2030
    id_utilisateur_ajout = factory.SubFactory(RoleFactory)

    @factory.post_generation
    def metriques(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for metrique in extracted:
                self.metriques.add(metrique)


# =============================================================================
# OperationAnnee / OperationAnneeOrganisme / Realisation (Phase 1 - Suivis)
# =============================================================================

class OperationAnneeFactory(DjangoModelFactory):
    """Programmation annuelle d'une opération."""

    class Meta:
        model = OperationAnnee

    id_operation = factory.SubFactory(OperationFactory)
    annee = factory.Sequence(lambda n: 2024 + (n % 7))
    periodicite = True
    budget = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    etp = factory.Faker('pydecimal', left_digits=2, right_digits=2, positive=True)


class OperationAnneeOrganismeFactory(DjangoModelFactory):
    """Ventilation par organisme d'une OperationAnnee."""

    class Meta:
        model = OperationAnneeOrganisme

    id_operation_annee = factory.SubFactory(OperationAnneeFactory)
    id_organisme = factory.LazyAttribute(
        lambda _: BibOrganismes.objects.first() or BibOrganismes.objects.create(
            nom_organisme='Org Test'
        )
    )
    budget_fonctionnement = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    budget_investissement = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    etp = factory.Faker('pydecimal', left_digits=2, right_digits=2, positive=True)


def _get_or_create_niveau_realisation_type():
    """Récupère ou crée le TypeNomenclature NIVEAU_REALISATION (singleton par DB)."""
    from apps.core.models import TypeNomenclature
    type_obj, _ = TypeNomenclature.objects.get_or_create(
        mnemonique='NIVEAU_REALISATION',
        defaults={'label': "Niveau de réalisation"},
    )
    return type_obj


def NomenclatureNiveauRealisationFactory(mnemonique: str = 'TERMINE', label: str = None):
    """
    Crée (ou récupère) une nomenclature NIVEAU_REALISATION par mnémonique.

    Mappage label par défaut :
      NON_DEMARRE → "Non démarré", EN_COURS → "En cours", PARTIEL → "Partiel",
      TERMINE → "Terminé", ABANDONNE → "Abandonné", REPORTE → "Reporté".
    """
    from apps.core.models import Nomenclature
    labels = {
        'NON_DEMARRE': 'Non démarré', 'EN_COURS': 'En cours', 'PARTIEL': 'Partiel',
        'TERMINE': 'Terminé', 'ABANDONNE': 'Abandonné', 'REPORTE': 'Reporté',
    }
    type_obj = _get_or_create_niveau_realisation_type()
    nomenclature, _ = Nomenclature.objects.get_or_create(
        id_type=type_obj,
        mnemonique=mnemonique,
        defaults={
            'cd_nomenclature': mnemonique[:10],
            'label': label or labels.get(mnemonique, mnemonique),
        },
    )
    return nomenclature


class RealisationOperationAnneeFactory(DjangoModelFactory):
    """Suivi de réalisation annuel."""

    class Meta:
        model = RealisationOperationAnnee

    id_operation_annee = factory.SubFactory(OperationAnneeFactory)
    id_niveau_realisation = factory.LazyFunction(
        lambda: NomenclatureNiveauRealisationFactory(mnemonique='TERMINE')
    )
    periodicite_realisee = True
    commentaires = factory.Faker('sentence', locale='fr_FR')
    budget_realise = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    etp_realise = factory.Faker('pydecimal', left_digits=2, right_digits=2, positive=True)


class RealisationOperationAnneeOrganismeFactory(DjangoModelFactory):
    """Ventilation par organisme d'une réalisation."""

    class Meta:
        model = RealisationOperationAnneeOrganisme

    id_operation_annee_organisme = factory.SubFactory(OperationAnneeOrganismeFactory)
    budget_fonctionnement_realise = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    budget_investissement_realise = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    etp_realise = factory.Faker('pydecimal', left_digits=2, right_digits=2, positive=True)
