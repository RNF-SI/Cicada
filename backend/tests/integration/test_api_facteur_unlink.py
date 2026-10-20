"""
#730 — Retirer un facteur d'influence partagé (#552) d'un seul enjeu.

POST /api/plans/facteurs-influence/{id}/unlink/ existait depuis #552 sans être
appelé par l'interface ni couvert par un test : « Supprimer » effaçait le
facteur sous tous ses enjeux. Le premier test a révélé que retirer le dernier
lien répondait 500, et le retrait d'un lien renvoyait un `enjeu_ids` périmé.
"""
import pytest
from rest_framework.test import APIClient

from apps.plans.models_enjeux import FacteurInfluence, Pression
from tests.factories.enjeux import EnjeuFactory, FacteurInfluenceFactory, NomenclatureEnjeuFactory, PressionFactory
from tests.factories.plans import CorSitePgFactory, PlanGestionFactory
from tests.factories.users import CorOgSiteFactory, CorRoleSiteFactory, OrganismeFactory, ReferentFactory, SiteFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture
def partage(db):
    org = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=org)
    referent = ReferentFactory(id_organisme=org)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan = PlanGestionFactory(statut='draft', id_utilisateur_ajout=referent)
    CorSitePgFactory(plan_de_gestion=plan, site=site)
    plan.referents.add(referent)
    cat = NomenclatureEnjeuFactory()
    e1 = EnjeuFactory(id_pg=plan, id_categorie=cat, id_utilisateur_ajout=referent)
    e2 = EnjeuFactory(id_pg=plan, id_categorie=cat, id_utilisateur_ajout=referent)
    fi = FacteurInfluenceFactory(enjeux=[e1, e2], id_utilisateur_ajout=referent)
    pr = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=referent)
    client = APIClient()
    client.force_authenticate(user=referent)
    return {'client': client, 'plan': plan, 'e1': e1, 'e2': e2, 'fi': fi, 'pr': pr}


def unlink(d, enjeu):
    return d['client'].post(
        f"/api/plans/facteurs-influence/{d['fi'].pk}/unlink/", {'enjeu_id': enjeu.pk}, format='json')


def test_retirer_d_un_enjeu_garde_le_facteur_sous_les_autres(partage):
    reponse = unlink(partage, partage['e1'])
    assert reponse.status_code == 200
    assert reponse.json()['enjeu_ids'] == [partage['e2'].pk]
    fi = FacteurInfluence.objects.get(pk=partage['fi'].pk)
    assert list(fi.enjeux.all()) == [partage['e2']]
    assert Pression.objects.filter(pk=partage['pr'].pk).exists()


def test_retirer_du_dernier_enjeu_supprime_le_facteur(partage):
    unlink(partage, partage['e1'])
    assert unlink(partage, partage['e2']).status_code == 204
    assert not FacteurInfluence.objects.filter(pk=partage['fi'].pk).exists()
    assert not Pression.objects.filter(pk=partage['pr'].pk).exists()


def test_refuse_hors_brouillon(partage):
    type(partage['plan']).objects.filter(pk=partage['plan'].pk).update(statut='valide')
    assert unlink(partage, partage['e1']).status_code == 403
    assert partage['fi'].enjeux.count() == 2
