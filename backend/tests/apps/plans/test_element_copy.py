"""
Tests pour ElementCopyService — copie profonde d'un élément unique (#552).

Vérifie que copier un facteur / OO / action produit un duplicata INDÉPENDANT
(sous-arbre inclus), rattaché à la cible, sans toucher l'original.
"""
import pytest

from apps.plans.element_copy import ElementCopyService
from apps.plans.models_enjeux import (
    ObjectifOperationnel, ResultatAttendu, CorFacteurEnjeu, FacteurInfluence,
)
from apps.plans.models_indicateurs import Indicateur, Metrique
from apps.plans.models_operations import Operation, OperationAnnee
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import RoleFactory
from tests.factories.enjeux import (
    EnjeuFactory, FacteurInfluenceFactory, PressionFactory,
    ObjectifOperationnelFactory, ResultatAttenduFactory,
    IndicateurPressionFactory, MetriqueFactory, OperationFactory,
    OperationAnneeFactory,
)


@pytest.fixture
def user(db):
    return RoleFactory()


@pytest.fixture
def plan(db, user):
    return PlanGestionFactory(id_utilisateur_ajout=user)


@pytest.mark.django_db
@pytest.mark.unit
class TestCopyOperation:
    def test_copy_operation_to_metrique_is_independent(self, plan, user):
        enjeu = EnjeuFactory(id_pg=plan, id_utilisateur_ajout=user)
        fi = FacteurInfluenceFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        pr = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)
        oo = ObjectifOperationnelFactory(id_utilisateur_ajout=user, pressions=[pr])
        ra = ResultatAttenduFactory(id_oo=oo, id_utilisateur_ajout=user)
        ind = IndicateurPressionFactory(id_resultat_attendu=ra, id_utilisateur_ajout=user)
        src_met = MetriqueFactory(id_indicateur=ind, id_utilisateur_ajout=user)
        target_met = MetriqueFactory(id_indicateur=ind, id_utilisateur_ajout=user)

        op = OperationFactory(libelle='Action A', id_utilisateur_ajout=user)
        op.metriques.add(src_met)
        OperationAnneeFactory(id_operation=op, annee=2025)

        new_op = ElementCopyService.copy_operation(op, user, target_metrique=target_met)

        assert new_op.pk != op.pk
        assert new_op.libelle == 'Action A'
        # Reliée à la métrique cible, pas à la source.
        assert list(new_op.metriques.values_list('id_metrique', flat=True)) == [target_met.id_metrique]
        # Programmation copiée.
        assert OperationAnnee.objects.filter(id_operation=new_op, annee=2025).exists()
        # Original intact.
        assert list(op.metriques.values_list('id_metrique', flat=True)) == [src_met.id_metrique]

    def test_copy_operation_requires_exactly_one_target(self, plan, user):
        op = OperationFactory(id_utilisateur_ajout=user)
        with pytest.raises(ValueError):
            ElementCopyService.copy_operation(op, user)


@pytest.mark.django_db
@pytest.mark.unit
class TestCopyOo:
    def test_copy_oo_to_pression_copies_subtree(self, plan, user):
        enjeu = EnjeuFactory(id_pg=plan, id_utilisateur_ajout=user)
        fi = FacteurInfluenceFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        pr_src = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)
        pr_target = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)
        oo = ObjectifOperationnelFactory(libelle='OO src', id_utilisateur_ajout=user, pressions=[pr_src])
        ra = ResultatAttenduFactory(id_oo=oo, libelle='RA', id_utilisateur_ajout=user)
        IndicateurPressionFactory(id_resultat_attendu=ra, nom_indicateur='Ind', id_utilisateur_ajout=user)

        new_oo = ElementCopyService.copy_oo(oo, user, target_pression=pr_target)

        assert new_oo.pk != oo.pk
        assert new_oo.libelle == 'OO src'
        assert pr_target in new_oo.pressions.all()
        assert pr_src not in new_oo.pressions.all()
        # Sous-arbre copié (RA + indicateur), indépendant.
        new_ra = ResultatAttendu.objects.get(id_oo=new_oo)
        assert new_ra.pk != ra.pk
        assert Indicateur.objects.filter(id_resultat_attendu=new_ra).count() == 1

    def test_copy_oo_to_enjeu_direct_fcr(self, plan, user):
        fcr = EnjeuFactory(id_pg=plan, libelle='FCR', id_utilisateur_ajout=user)
        enjeu = EnjeuFactory(id_pg=plan, id_utilisateur_ajout=user)
        fi = FacteurInfluenceFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
        pr = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)
        oo = ObjectifOperationnelFactory(id_utilisateur_ajout=user, pressions=[pr])

        new_oo = ElementCopyService.copy_oo(oo, user, target_enjeu=fcr)

        assert new_oo.id_enjeu_id == fcr.id_enjeu
        assert new_oo.pressions.count() == 0


@pytest.mark.django_db
@pytest.mark.unit
class TestCopyFacteur:
    def test_copy_facteur_full_subtree_independent(self, plan, user):
        enjeu_src = EnjeuFactory(id_pg=plan, libelle='E src', id_utilisateur_ajout=user)
        enjeu_target = EnjeuFactory(id_pg=plan, libelle='E cible', id_utilisateur_ajout=user)
        fi = FacteurInfluenceFactory(id_enjeu=enjeu_src, libelle='FI', id_utilisateur_ajout=user)
        pr = PressionFactory(id_facteur_influence=fi, libelle='P', id_utilisateur_ajout=user)
        oo = ObjectifOperationnelFactory(libelle='OO', id_utilisateur_ajout=user, pressions=[pr])
        ra = ResultatAttenduFactory(id_oo=oo, id_utilisateur_ajout=user)
        IndicateurPressionFactory(id_resultat_attendu=ra, id_utilisateur_ajout=user)

        new_fi = ElementCopyService.copy_facteur(fi, user, target_enjeu=enjeu_target)

        assert new_fi.pk != fi.pk
        # Rattaché à l'enjeu cible uniquement.
        assert list(new_fi.enjeux.values_list('id_enjeu', flat=True)) == [enjeu_target.id_enjeu]
        # Sous-arbre dupliqué et indépendant.
        assert new_fi.pressions.count() == 1
        new_oo = new_fi.pressions.first().objectifs_operationnels.first()
        assert new_oo is not None and new_oo.pk != oo.pk
        assert ResultatAttendu.objects.filter(id_oo=new_oo).count() == 1
        # Original intact (toujours sous son enjeu, sous-arbre inchangé).
        assert list(fi.enjeux.values_list('id_enjeu', flat=True)) == [enjeu_src.id_enjeu]
        assert FacteurInfluence.objects.filter(pk=fi.pk).exists()

    def test_copy_facteur_shared_oo_copied_once(self, plan, user):
        """Un OO partagé entre 2 pressions du même facteur n'est copié qu'une fois."""
        enjeu_src = EnjeuFactory(id_pg=plan, id_utilisateur_ajout=user)
        enjeu_target = EnjeuFactory(id_pg=plan, id_utilisateur_ajout=user)
        fi = FacteurInfluenceFactory(id_enjeu=enjeu_src, id_utilisateur_ajout=user)
        p1 = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)
        p2 = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)
        # Même OO sous p1 ET p2.
        ObjectifOperationnelFactory(id_utilisateur_ajout=user, pressions=[p1, p2])

        new_fi = ElementCopyService.copy_facteur(fi, user, target_enjeu=enjeu_target)

        new_oos = set()
        for pr in new_fi.pressions.all():
            for o in pr.objectifs_operationnels.all():
                new_oos.add(o.id_oo)
        assert len(new_oos) == 1  # un seul OO copié, relié aux 2 nouvelles pressions
