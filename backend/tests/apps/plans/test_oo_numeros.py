"""
Tests pour la numérotation plan-wide des OO (#552).

`compute_oo_numeros_for_plan` attribue à chaque OO un numéro unique à l'échelle
du plan, à sa première rencontre dans l'ordre de lecture (enjeux par ordre, puis
OO par leur ordre propre à l'enjeu). Un OO partagé a le même numéro partout ;
`numero_manuel` réserve son indice.
"""
import pytest

from apps.plans.models_enjeux import CorFacteurEnjeu, CorOoEnjeu
from apps.plans.serializers_enjeux import compute_oo_numeros_for_plan
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import RoleFactory
from tests.factories.enjeux import (
    EnjeuFactory, FacteurInfluenceFactory, PressionFactory,
    ObjectifOperationnelFactory,
)


@pytest.fixture
def user(db):
    return RoleFactory()


def _oo_under(enjeu, user, libelle, ordre=0):
    """Crée un OO rattaché à `enjeu` via un facteur/pression dédiés."""
    fi = FacteurInfluenceFactory(id_enjeu=enjeu, id_utilisateur_ajout=user)
    pr = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)
    return ObjectifOperationnelFactory(
        libelle=libelle, ordre=ordre, id_utilisateur_ajout=user, pressions=[pr],
    )


@pytest.mark.django_db
@pytest.mark.unit
class TestComputeOoNumeros:
    def test_numbered_plan_wide_in_reading_order(self, user):
        plan = PlanGestionFactory(id_utilisateur_ajout=user)
        e1 = EnjeuFactory(id_pg=plan, ordre=0, libelle='E1', id_utilisateur_ajout=user)
        e2 = EnjeuFactory(id_pg=plan, ordre=1, libelle='E2', id_utilisateur_ajout=user)
        a = _oo_under(e1, user, 'A', ordre=0)
        b = _oo_under(e1, user, 'B', ordre=1)
        c = _oo_under(e2, user, 'C', ordre=0)

        numeros = compute_oo_numeros_for_plan(plan.id_pg)
        # Plan-wide : ne repart pas à 1 sous e2.
        assert numeros[a.id_oo] == 1
        assert numeros[b.id_oo] == 2
        assert numeros[c.id_oo] == 3

    def test_shared_oo_same_number_under_all_enjeux(self, user):
        """Un OO partagé garde le numéro de son PREMIER enjeu."""
        plan = PlanGestionFactory(id_utilisateur_ajout=user)
        e1 = EnjeuFactory(id_pg=plan, ordre=0, libelle='E1', id_utilisateur_ajout=user)
        e2 = EnjeuFactory(id_pg=plan, ordre=1, libelle='E2', id_utilisateur_ajout=user)
        # OO partagé : son facteur est rattaché à e1 ET e2.
        fi = FacteurInfluenceFactory(id_enjeu=e1, id_utilisateur_ajout=user)
        CorFacteurEnjeu.objects.get_or_create(id_facteur_influence=fi, id_enjeu=e2)
        pr = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=user)
        shared = ObjectifOperationnelFactory(
            libelle='partagé', ordre=0, id_utilisateur_ajout=user, pressions=[pr],
        )
        other = _oo_under(e2, user, 'e2-only', ordre=5)

        numeros = compute_oo_numeros_for_plan(plan.id_pg)
        # Un seul numéro pour l'OO partagé (rencontré sous e1 en premier).
        assert numeros[shared.id_oo] == 1
        assert numeros[other.id_oo] == 2

    def test_manual_number_reserved(self, user):
        plan = PlanGestionFactory(id_utilisateur_ajout=user)
        e1 = EnjeuFactory(id_pg=plan, ordre=0, libelle='E1', id_utilisateur_ajout=user)
        forced = _oo_under(e1, user, 'forcé', ordre=0)
        forced.numero_manuel = 1
        forced.save()
        auto = _oo_under(e1, user, 'auto', ordre=1)

        numeros = compute_oo_numeros_for_plan(plan.id_pg)
        # L'indice 1 est réservé par le forcé → l'auto saute à 2.
        assert numeros[forced.id_oo] == 1
        assert numeros[auto.id_oo] == 2

    def test_per_enjeu_order_drives_numbering(self, user):
        """L'ordre propre à l'enjeu (CorOoEnjeu) prime sur l'ordre global."""
        plan = PlanGestionFactory(id_utilisateur_ajout=user)
        e1 = EnjeuFactory(id_pg=plan, ordre=0, libelle='E1', id_utilisateur_ajout=user)
        a = _oo_under(e1, user, 'A', ordre=0)
        b = _oo_under(e1, user, 'B', ordre=1)
        # Surcharge : sous e1, B passe avant A.
        CorOoEnjeu.objects.create(id_oo=b, id_enjeu=e1, ordre=0)
        CorOoEnjeu.objects.create(id_oo=a, id_enjeu=e1, ordre=1)

        numeros = compute_oo_numeros_for_plan(plan.id_pg)
        assert numeros[b.id_oo] == 1
        assert numeros[a.id_oo] == 2
