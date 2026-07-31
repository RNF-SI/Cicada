"""
Tests d'intégration pour les actions `reorder` des ViewSets du module plans
(#249 / #261).

Couvre :
- POST reorder avec ordered_ids valides → 200 + ordres mis à jour en BDD
- POST reorder avec ordre mélangé → 200 + nouvel ordre persisté
- POST reorder avec un ID n'appartenant pas au parent → 400
- POST reorder sur un plan non-draft → 403 (verrou #248)
- POST reorder par un utilisateur non autorisé → 403/404

Cible chaque ViewSet : enjeux, facteurs-influence, pressions,
objectifs-long-terme, niveaux-exigence, objectifs-operationnels,
resultats-attendus, indicateurs, operations.
"""
import pytest
from rest_framework import status

from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, Pression,
    ObjectifLongTerme, NiveauExigence,
    ObjectifOperationnel, ResultatAttendu,
)
from apps.plans.models_indicateurs import Indicateur, Metrique
from apps.plans.models_operations import Operation, CorOperationMetrique
from tests.factories.enjeux import (
    EnjeuFactory, FacteurInfluenceFactory, PressionFactory,
    ObjectifLongTermeFactory, NiveauExigenceFactory,
    ObjectifOperationnelFactory, ResultatAttenduFactory,
    IndicateurFactory, IndicateurPressionFactory, MetriqueFactory,
    OperationFactory,
    NomenclatureEnjeuFactory, NomenclatureTypeIndicateurFactory,
    NomenclatureTypeMetriqueFactory,
)
from tests.factories.plans import (
    PlanGestionFactory, PlanGestionValideFactory, CorSitePgFactory,
)
from tests.factories.users import (
    SuperAdminFactory, ReferentFactory, RoleFactory,
    SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)


@pytest.fixture
def reorder_test_data(db):
    """
    Crée la hiérarchie complète Enjeu → FI → Pression → OO → RA,
    avec NE/Indicateur/Métrique/Opération, sur un plan en brouillon
    accessible par `referent` et `super_admin`.

    Crée également un second plan VALIDÉ avec un enjeu pour tester le verrou
    #248, et un utilisateur `user` (non référent) pour les tests d'accès.
    """
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan Reorder Test', statut='draft')
    CorSitePgFactory(plan_de_gestion=plan, site=site)

    super_admin = SuperAdminFactory()
    referent = ReferentFactory(id_organisme=organisme)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan.referents.add(referent)
    user = RoleFactory()  # ni admin, ni référent du plan

    cat_enjeu = NomenclatureEnjeuFactory()

    # 3 enjeux, 3 FI sous enjeu1, 3 pressions sous fi1, ...
    enjeu1 = EnjeuFactory(id_pg=plan, id_categorie=cat_enjeu, libelle='E1', id_utilisateur_ajout=referent)
    enjeu2 = EnjeuFactory(id_pg=plan, id_categorie=cat_enjeu, libelle='E2', id_utilisateur_ajout=referent)
    enjeu3 = EnjeuFactory(id_pg=plan, id_categorie=cat_enjeu, libelle='E3', id_utilisateur_ajout=referent)

    fi1 = FacteurInfluenceFactory(id_enjeu=enjeu1, libelle='FI1', id_utilisateur_ajout=referent)
    fi2 = FacteurInfluenceFactory(id_enjeu=enjeu1, libelle='FI2', id_utilisateur_ajout=referent)
    fi3 = FacteurInfluenceFactory(id_enjeu=enjeu1, libelle='FI3', id_utilisateur_ajout=referent)

    p1 = PressionFactory(id_facteur_influence=fi1, libelle='P1', id_utilisateur_ajout=referent)
    p2 = PressionFactory(id_facteur_influence=fi1, libelle='P2', id_utilisateur_ajout=referent)
    p3 = PressionFactory(id_facteur_influence=fi1, libelle='P3', id_utilisateur_ajout=referent)

    olt1 = ObjectifLongTermeFactory(id_enjeu=enjeu1, libelle='OLT1', id_utilisateur_ajout=referent)
    olt2 = ObjectifLongTermeFactory(id_enjeu=enjeu1, libelle='OLT2', id_utilisateur_ajout=referent)
    olt3 = ObjectifLongTermeFactory(id_enjeu=enjeu1, libelle='OLT3', id_utilisateur_ajout=referent)

    ne1 = NiveauExigenceFactory(id_olt=olt1, libelle='NE1', id_utilisateur_ajout=referent)
    ne2 = NiveauExigenceFactory(id_olt=olt1, libelle='NE2', id_utilisateur_ajout=referent)
    ne3 = NiveauExigenceFactory(id_olt=olt1, libelle='NE3', id_utilisateur_ajout=referent)

    oo1 = ObjectifOperationnelFactory(libelle='OO1', id_utilisateur_ajout=referent, pressions=[p1])
    oo2 = ObjectifOperationnelFactory(libelle='OO2', id_utilisateur_ajout=referent, pressions=[p2])
    oo3 = ObjectifOperationnelFactory(libelle='OO3', id_utilisateur_ajout=referent, pressions=[p3])

    ra1 = ResultatAttenduFactory(id_oo=oo1, libelle='RA1', id_utilisateur_ajout=referent)
    ra2 = ResultatAttenduFactory(id_oo=oo1, libelle='RA2', id_utilisateur_ajout=referent)
    ra3 = ResultatAttenduFactory(id_oo=oo1, libelle='RA3', id_utilisateur_ajout=referent)

    # Crée les nomenclatures de type une seule fois pour éviter les conflits
    # de PK liés à `factory.Iterator` sans `django_get_or_create` sur
    # NomenclatureFactory (cf. NomenclatureTypeIndicateurFactory etc.).
    type_ind = NomenclatureTypeIndicateurFactory()
    type_met = NomenclatureTypeMetriqueFactory()

    # 3 indicateurs sous NE1 — on partage id_utilisateur_ajout pour éviter
    # de spawner trop de Roles et donc de séquences inutiles.
    ind1 = IndicateurFactory(id_ne=ne1, nom_indicateur='IND1', type_indicateur=type_ind, id_utilisateur_ajout=referent)
    ind2 = IndicateurFactory(id_ne=ne1, nom_indicateur='IND2', type_indicateur=type_ind, id_utilisateur_ajout=referent)
    ind3 = IndicateurFactory(id_ne=ne1, nom_indicateur='IND3', type_indicateur=type_ind, id_utilisateur_ajout=referent)

    # 2 indicateurs sous RA1
    ind_ra_1 = IndicateurPressionFactory(id_resultat_attendu=ra1, nom_indicateur='IND_RA_1', type_indicateur=type_ind, id_utilisateur_ajout=referent)
    ind_ra_2 = IndicateurPressionFactory(id_resultat_attendu=ra1, nom_indicateur='IND_RA_2', type_indicateur=type_ind, id_utilisateur_ajout=referent)

    # 1 métrique + 3 opérations rattachées via M2M à metrique1.
    # On passe `id_priorite=None` à OperationFactory pour éviter d'invoquer
    # NomenclaturePrioriteOperationFactory (factory.Iterator sans
    # django_get_or_create → conflit de PK entre tests).
    metrique1 = MetriqueFactory(id_indicateur=ind1, nom_metrique='M1', type_metrique=type_met, id_utilisateur_ajout=referent)

    op1 = OperationFactory(libelle='OP1', id_priorite=None, id_utilisateur_ajout=referent)
    op2 = OperationFactory(libelle='OP2', id_priorite=None, id_utilisateur_ajout=referent)
    op3 = OperationFactory(libelle='OP3', id_priorite=None, id_utilisateur_ajout=referent)
    CorOperationMetrique.objects.create(id_operation=op1, id_metrique=metrique1)
    CorOperationMetrique.objects.create(id_operation=op2, id_metrique=metrique1)
    CorOperationMetrique.objects.create(id_operation=op3, id_metrique=metrique1)

    # Plan validé pour tester le verrou #248
    plan_valide = PlanGestionValideFactory(nom='Plan Validé', statut='valide')
    CorSitePgFactory(plan_de_gestion=plan_valide, site=site)
    plan_valide.referents.add(referent)
    enjeu_valide_1 = EnjeuFactory(id_pg=plan_valide, id_categorie=cat_enjeu, libelle='EV1', id_utilisateur_ajout=referent)
    enjeu_valide_2 = EnjeuFactory(id_pg=plan_valide, id_categorie=cat_enjeu, libelle='EV2', id_utilisateur_ajout=referent)

    return {
        'organisme': organisme,
        'site': site,
        'plan': plan,
        'plan_valide': plan_valide,
        'super_admin': super_admin,
        'referent': referent,
        'user': user,
        'enjeu1': enjeu1, 'enjeu2': enjeu2, 'enjeu3': enjeu3,
        'fi1': fi1, 'fi2': fi2, 'fi3': fi3,
        'p1': p1, 'p2': p2, 'p3': p3,
        'olt1': olt1, 'olt2': olt2, 'olt3': olt3,
        'ne1': ne1, 'ne2': ne2, 'ne3': ne3,
        'oo1': oo1, 'oo2': oo2, 'oo3': oo3,
        'ra1': ra1, 'ra2': ra2, 'ra3': ra3,
        'ind1': ind1, 'ind2': ind2, 'ind3': ind3,
        'ind_ra_1': ind_ra_1, 'ind_ra_2': ind_ra_2,
        'metrique1': metrique1,
        'op1': op1, 'op2': op2, 'op3': op3,
        'enjeu_valide_1': enjeu_valide_1,
        'enjeu_valide_2': enjeu_valide_2,
    }


# =============================================================================
# Helper assertions
# =============================================================================

def _assert_order(model_cls, pk_field, ids_ordered):
    """Assert que les ordres en BDD correspondent à `ids_ordered` (0, 1, 2, ...)."""
    for expected_pos, pk in enumerate(ids_ordered):
        instance = model_cls.objects.get(**{pk_field: pk})
        assert instance.ordre == expected_pos, (
            f"{model_cls.__name__}#{pk}: ordre={instance.ordre}, attendu={expected_pos}"
        )


def _assert_facteur_order(enjeu, ids_ordered):
    """Idem pour les facteurs d'influence (#552).

    L'ordre n'est plus porté par le facteur mais par sa liaison à l'enjeu : un
    facteur partagé a un ordre propre à chacun de ses enjeux.
    """
    from apps.plans.models_enjeux import CorFacteurEnjeu

    for expected_pos, pk in enumerate(ids_ordered):
        cor = CorFacteurEnjeu.objects.get(
            id_facteur_influence_id=pk, id_enjeu=enjeu
        )
        assert cor.ordre == expected_pos, (
            f"CorFacteurEnjeu(facteur={pk}, enjeu={enjeu.pk}): "
            f"ordre={cor.ordre}, attendu={expected_pos}"
        )


def _assert_oo_order(enjeu, ids_ordered):
    """Ordre des OO propre à un enjeu, porté par CorOoEnjeu (#552)."""
    from apps.plans.models_enjeux import CorOoEnjeu

    for expected_pos, pk in enumerate(ids_ordered):
        cor = CorOoEnjeu.objects.get(id_oo_id=pk, id_enjeu=enjeu)
        assert cor.ordre == expected_pos, (
            f"CorOoEnjeu(oo={pk}, enjeu={enjeu.pk}): "
            f"ordre={cor.ordre}, attendu={expected_pos}"
        )


# =============================================================================
# EnjeuViewSet reorder
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestEnjeuReorder:
    """Tests POST /api/plans/enjeux/reorder/"""

    URL = '/api/plans/enjeux/reorder/'

    def test_reorder_valid_payload_updates_ordre(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['super_admin'])
        plan = reorder_test_data['plan']
        ids = [reorder_test_data['enjeu3'].pk, reorder_test_data['enjeu1'].pk, reorder_test_data['enjeu2'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': plan.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['updated'] == 3
        _assert_order(Enjeu, 'id_enjeu', ids)

    def test_reorder_same_order_is_noop(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        plan = reorder_test_data['plan']
        ids = [reorder_test_data['enjeu1'].pk, reorder_test_data['enjeu2'].pk, reorder_test_data['enjeu3'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': plan.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        _assert_order(Enjeu, 'id_enjeu', ids)

    def test_reorder_with_id_from_other_parent_returns_400(self, api_client, reorder_test_data):
        """Un id qui n'appartient pas au plan parent doit être rejeté."""
        api_client.force_authenticate(user=reorder_test_data['super_admin'])
        plan = reorder_test_data['plan']
        # enjeu_valide_1 appartient à plan_valide, pas à plan
        ids = [
            reorder_test_data['enjeu1'].pk,
            reorder_test_data['enjeu_valide_1'].pk,
        ]
        response = api_client.post(
            self.URL,
            {'parent_id': plan.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reorder_on_validated_plan_returns_403(self, api_client, reorder_test_data):
        """Verrou #248 : un plan non-draft refuse toute écriture."""
        api_client.force_authenticate(user=reorder_test_data['referent'])
        plan_valide = reorder_test_data['plan_valide']
        ids = [reorder_test_data['enjeu_valide_2'].pk, reorder_test_data['enjeu_valide_1'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': plan_valide.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_reorder_non_referent_user_denied(self, api_client, reorder_test_data):
        """IsReferent : un utilisateur sans droit ne peut pas appeler l'action."""
        api_client.force_authenticate(user=reorder_test_data['user'])
        plan = reorder_test_data['plan']
        ids = [reorder_test_data['enjeu1'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': plan.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_reorder_unauthenticated_returns_401(self, api_client, reorder_test_data):
        response = api_client.post(
            self.URL,
            {'parent_id': reorder_test_data['plan'].pk, 'ordered_ids': []},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_reorder_invalid_payload_returns_400(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['super_admin'])
        # parent_id manquant
        response = api_client.post(
            self.URL,
            {'ordered_ids': [1, 2, 3]},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# FacteurInfluenceViewSet reorder
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestFacteurInfluenceReorder:
    """Tests POST /api/plans/facteurs-influence/reorder/"""

    URL = '/api/plans/facteurs-influence/reorder/'

    def test_reorder_valid_payload(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        enjeu = reorder_test_data['enjeu1']
        ids = [reorder_test_data['fi2'].pk, reorder_test_data['fi3'].pk, reorder_test_data['fi1'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': enjeu.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        _assert_facteur_order(enjeu, ids)

    def test_reorder_with_id_from_other_parent_returns_400(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['super_admin'])
        # Tente de réordonner les FI de enjeu1 mais avec un id qui appartient à enjeu2 (aucun n'existe pour enjeu2)
        # On utilise donc un id qui appartient bien à enjeu1 + un faux id
        ids = [reorder_test_data['fi1'].pk, 99999]
        response = api_client.post(
            self.URL,
            {'parent_id': reorder_test_data['enjeu1'].pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# PressionViewSet reorder
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPressionReorder:
    """Tests POST /api/plans/pressions/reorder/"""

    URL = '/api/plans/pressions/reorder/'

    def test_reorder_valid_payload(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        fi = reorder_test_data['fi1']
        ids = [reorder_test_data['p3'].pk, reorder_test_data['p1'].pk, reorder_test_data['p2'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': fi.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        _assert_order(Pression, 'id_pression', ids)


# =============================================================================
# ObjectifLongTermeViewSet reorder
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifLongTermeReorder:
    """Tests POST /api/plans/objectifs-long-terme/reorder/"""

    URL = '/api/plans/objectifs-long-terme/reorder/'

    def test_reorder_valid_payload(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        enjeu = reorder_test_data['enjeu1']
        ids = [reorder_test_data['olt2'].pk, reorder_test_data['olt1'].pk, reorder_test_data['olt3'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': enjeu.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        _assert_order(ObjectifLongTerme, 'id_olt', ids)


# =============================================================================
# NiveauExigenceViewSet reorder
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestNiveauExigenceReorder:
    """Tests POST /api/plans/niveaux-exigence/reorder/"""

    URL = '/api/plans/niveaux-exigence/reorder/'

    def test_reorder_valid_payload(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        olt = reorder_test_data['olt1']
        ids = [reorder_test_data['ne3'].pk, reorder_test_data['ne2'].pk, reorder_test_data['ne1'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': olt.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        _assert_order(NiveauExigence, 'id_ne', ids)


# =============================================================================
# ObjectifOperationnelViewSet reorder
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifOperationnelReorder:
    """Tests POST /api/plans/objectifs-operationnels/reorder/

    Cas M2M : on remonte au plan via Pression → FI → Enjeu. Le parent_id
    correspond à un enjeu.
    """

    URL = '/api/plans/objectifs-operationnels/reorder/'

    def test_reorder_valid_payload(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        enjeu = reorder_test_data['enjeu1']
        # Les 3 OO sont rattachés transitivement à enjeu1 via leurs pressions
        ids = [reorder_test_data['oo2'].pk, reorder_test_data['oo1'].pk, reorder_test_data['oo3'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': enjeu.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        # #552 — l'ordre est porté par CorOoEnjeu (propre à l'enjeu), pas par oo.ordre
        _assert_oo_order(enjeu, ids)

    def test_reorder_is_independent_per_enjeu(self, api_client, reorder_test_data):
        """#552 — réordonner un OO partagé sous un enjeu n'affecte pas l'autre."""
        from apps.plans.models_enjeux import CorFacteurEnjeu, CorOoEnjeu

        d = reorder_test_data
        enjeu1, enjeu2 = d['enjeu1'], d['enjeu2']
        # Partage : le facteur fi1 (dont dépendent oo1/oo2/oo3 via p1/p2/p3) est
        # aussi rattaché à enjeu2 → les 3 OO deviennent visibles sous enjeu2.
        CorFacteurEnjeu.objects.get_or_create(
            id_facteur_influence=d['fi1'], id_enjeu=enjeu2,
        )

        api_client.force_authenticate(user=d['referent'])
        ids = [d['oo3'].pk, d['oo2'].pk, d['oo1'].pk]
        resp = api_client.post(
            self.URL, {'parent_id': enjeu1.pk, 'ordered_ids': ids}, format='json',
        )
        assert resp.status_code == status.HTTP_200_OK

        # enjeu1 a bien ses lignes d'ordre ; enjeu2 n'a rien reçu (indépendant).
        _assert_oo_order(enjeu1, ids)
        assert not CorOoEnjeu.objects.filter(id_enjeu=enjeu2).exists()

    def test_reorder_reflected_in_by_plan_oo_ordre(self, api_client, reorder_test_data):
        """#552 — after a reorder, by-plan exposes the per-enjeu order in oo_ordre."""
        d = reorder_test_data
        enjeu = d['enjeu1']
        api_client.force_authenticate(user=d['referent'])
        ids = [d['oo2'].pk, d['oo3'].pk, d['oo1'].pk]
        assert api_client.post(
            self.URL, {'parent_id': enjeu.pk, 'ordered_ids': ids}, format='json',
        ).status_code == status.HTTP_200_OK

        resp = api_client.get(f'/api/plans/enjeux/by-plan/{d["plan"].id_pg}/')
        assert resp.status_code == status.HTTP_200_OK
        e = next(x for x in resp.data['enjeux'] if x['id_enjeu'] == enjeu.pk)
        # Le map reflète l'ordre demandé (clés = id_oo, valeurs = position).
        assert e['oo_ordre'] == {ids[0]: 0, ids[1]: 1, ids[2]: 2}


# =============================================================================
# ResultatAttenduViewSet reorder
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestResultatAttenduReorder:
    """Tests POST /api/plans/resultats-attendus/reorder/"""

    URL = '/api/plans/resultats-attendus/reorder/'

    def test_reorder_valid_payload(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        oo = reorder_test_data['oo1']
        ids = [reorder_test_data['ra3'].pk, reorder_test_data['ra1'].pk, reorder_test_data['ra2'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': oo.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        _assert_order(ResultatAttendu, 'id_ra', ids)


# =============================================================================
# IndicateurViewSet reorder (NE & RA)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestIndicateurReorder:
    """Tests POST /api/plans/indicateurs/reorder/

    Cas spécial : un indicateur a deux parents possibles (NE XOR RA).
    Le payload doit inclure `parent_type` ('ne' ou 'ra').
    """

    URL = '/api/plans/indicateurs/reorder/'

    def test_reorder_under_ne(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        ne = reorder_test_data['ne1']
        ids = [reorder_test_data['ind3'].pk, reorder_test_data['ind1'].pk, reorder_test_data['ind2'].pk]
        response = api_client.post(
            self.URL,
            {'parent_type': 'ne', 'parent_id': ne.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        _assert_order(Indicateur, 'id_indicateur', ids)

    def test_reorder_under_ra(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        ra = reorder_test_data['ra1']
        ids = [reorder_test_data['ind_ra_2'].pk, reorder_test_data['ind_ra_1'].pk]
        response = api_client.post(
            self.URL,
            {'parent_type': 'ra', 'parent_id': ra.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        _assert_order(Indicateur, 'id_indicateur', ids)

    def test_reorder_invalid_parent_type_returns_400(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['super_admin'])
        response = api_client.post(
            self.URL,
            {'parent_type': 'xxx', 'parent_id': reorder_test_data['ne1'].pk, 'ordered_ids': []},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reorder_indicateur_from_other_ne_returns_400(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['super_admin'])
        # ind_ra_1 appartient à RA1, pas à NE1
        ids = [reorder_test_data['ind1'].pk, reorder_test_data['ind_ra_1'].pk]
        response = api_client.post(
            self.URL,
            {'parent_type': 'ne', 'parent_id': reorder_test_data['ne1'].pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# OperationViewSet reorder
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationReorder:
    """Tests POST /api/plans/operations/reorder/

    Cas M2M : l'ordre porte sur les opérations rattachées à une métrique.
    """

    URL = '/api/plans/operations/reorder/'

    def test_reorder_valid_payload(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        metrique = reorder_test_data['metrique1']
        ids = [reorder_test_data['op3'].pk, reorder_test_data['op1'].pk, reorder_test_data['op2'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': metrique.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        _assert_order(Operation, 'id_operation', ids)

    def test_reorder_with_unrelated_id_returns_400(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['super_admin'])
        # Crée une opération qui n'est PAS liée à metrique1
        op_unrelated = OperationFactory(
            libelle='OP_UNRELATED',
            id_priorite=None,
            id_utilisateur_ajout=reorder_test_data['referent'],
        )
        ids = [reorder_test_data['op1'].pk, op_unrelated.pk]
        response = api_client.post(
            self.URL,
            {'parent_id': reorder_test_data['metrique1'].pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reorder_by_indicateur_scope(self, api_client, reorder_test_data):
        """#544 : l'arborescence réordonne les actions à la portée indicateur.

        op1/op2/op3 sont rattachées à ind1 via metrique1 : un `parent_type=indicateur`
        avec parent_id=ind1 doit donc les réordonner.
        """
        api_client.force_authenticate(user=reorder_test_data['referent'])
        ind1 = reorder_test_data['ind1']
        ids = [reorder_test_data['op3'].pk, reorder_test_data['op1'].pk, reorder_test_data['op2'].pk]
        response = api_client.post(
            self.URL,
            {'parent_id': ind1.pk, 'ordered_ids': ids, 'parent_type': 'indicateur'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        _assert_order(Operation, 'id_operation', ids)

    def test_reorder_by_indicateur_rejects_unrelated_id(self, api_client, reorder_test_data):
        """#544 : anti-tampering — une action hors de l'indicateur est refusée."""
        api_client.force_authenticate(user=reorder_test_data['super_admin'])
        op_unrelated = OperationFactory(
            libelle='OP_UNRELATED_IND',
            id_priorite=None,
            id_utilisateur_ajout=reorder_test_data['referent'],
        )
        ids = [reorder_test_data['op1'].pk, op_unrelated.pk]
        response = api_client.post(
            self.URL,
            {'parent_id': reorder_test_data['ind1'].pk, 'ordered_ids': ids, 'parent_type': 'indicateur'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# IndicateurViewSet move (#261)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestIndicateurMove:
    """Tests POST /api/plans/indicateurs/{id}/move/

    Déplace un indicateur entre NE / RA (intra-plan).
    """

    def _url(self, indicateur_id):
        return f'/api/plans/indicateurs/{indicateur_id}/move/'

    def test_move_indicateur_to_another_ne(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        ind = reorder_test_data['ind1']
        new_ne = reorder_test_data['ne2']
        response = api_client.post(
            self._url(ind.pk),
            {'new_parent_type': 'ne', 'new_parent_id': new_ne.pk, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        ind.refresh_from_db()
        assert ind.id_ne_id == new_ne.pk
        assert ind.id_resultat_attendu_id is None
        assert ind.ordre == 0

    def test_move_indicateur_from_ne_to_ra(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        ind = reorder_test_data['ind1']  # initialement sous NE1
        target_ra = reorder_test_data['ra2']
        response = api_client.post(
            self._url(ind.pk),
            {'new_parent_type': 'ra', 'new_parent_id': target_ra.pk, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        ind.refresh_from_db()
        assert ind.id_resultat_attendu_id == target_ra.pk
        assert ind.id_ne_id is None

    def test_move_with_invalid_parent_type_returns_400(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        response = api_client.post(
            self._url(reorder_test_data['ind1'].pk),
            {'new_parent_type': 'xxx', 'new_parent_id': 1, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_move_to_nonexistent_parent_returns_404(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        response = api_client.post(
            self._url(reorder_test_data['ind1'].pk),
            {'new_parent_type': 'ne', 'new_parent_id': 999999, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_move_on_validated_plan_returns_403(self, api_client, reorder_test_data):
        """Verrou #248 : on ne peut pas déplacer un indicateur sur un plan validé.

        On réutilise l'arborescence du plan draft (ind1 sous ne1) et on bascule
        le plan en validé juste avant l'appel — évite de recréer des nomenclatures
        via factory.Iterator (instable en suite, cf. note dans reorder.py).
        """
        plan = reorder_test_data['plan']
        plan.statut = 'valide'
        plan.save(update_fields=['statut'])

        api_client.force_authenticate(user=reorder_test_data['referent'])
        ind = reorder_test_data['ind1']
        target_ne = reorder_test_data['ne2']
        response = api_client.post(
            self._url(ind.pk),
            {'new_parent_type': 'ne', 'new_parent_id': target_ne.pk, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data

    def test_move_unauthenticated_returns_401(self, api_client, reorder_test_data):
        response = api_client.post(
            self._url(reorder_test_data['ind1'].pk),
            {'new_parent_type': 'ne', 'new_parent_id': reorder_test_data['ne2'].pk, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# PressionViewSet move (#472)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPressionMove:
    """Tests POST /api/plans/pressions/{id}/move/

    Déplace une pression vers un autre facteur d'influence (intra-plan, #472).
    """

    def _url(self, pression_id):
        return f'/api/plans/pressions/{pression_id}/move/'

    def test_move_pression_to_another_facteur(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        pression = reorder_test_data['p1']  # sous fi1
        target_fi = reorder_test_data['fi2']
        response = api_client.post(
            self._url(pression.pk),
            {'new_facteur_id': target_fi.pk, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        pression.refresh_from_db()
        assert pression.id_facteur_influence_id == target_fi.pk
        assert pression.ordre == 0

    def test_move_pression_renumbers_siblings_in_target(self, api_client, reorder_test_data):
        """La pression insérée en tête décale les siblings existants du facteur cible."""
        api_client.force_authenticate(user=reorder_test_data['referent'])
        # fi2 a déjà une pression pré-existante
        Pression.objects.filter(pk=reorder_test_data['p2'].pk).update(
            id_facteur_influence=reorder_test_data['fi2'], ordre=0
        )
        pression = reorder_test_data['p1']
        target_fi = reorder_test_data['fi2']
        response = api_client.post(
            self._url(pression.pk),
            {'new_facteur_id': target_fi.pk, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        pression.refresh_from_db()
        p2 = Pression.objects.get(pk=reorder_test_data['p2'].pk)
        assert pression.ordre == 0
        assert p2.ordre == 1

    def test_move_to_nonexistent_facteur_returns_404(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        response = api_client.post(
            self._url(reorder_test_data['p1'].pk),
            {'new_facteur_id': 999999, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_move_without_facteur_id_returns_400(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        response = api_client.post(
            self._url(reorder_test_data['p1'].pk),
            {'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_move_on_validated_plan_returns_403(self, api_client, reorder_test_data):
        """Verrou #248 : pas de déplacement de pression sur un plan validé."""
        plan = reorder_test_data['plan']
        plan.statut = 'valide'
        plan.save(update_fields=['statut'])

        api_client.force_authenticate(user=reorder_test_data['referent'])
        response = api_client.post(
            self._url(reorder_test_data['p1'].pk),
            {'new_facteur_id': reorder_test_data['fi2'].pk, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data

    def test_move_unauthenticated_returns_401(self, api_client, reorder_test_data):
        response = api_client.post(
            self._url(reorder_test_data['p1'].pk),
            {'new_facteur_id': reorder_test_data['fi2'].pk, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# OperationViewSet move (#586)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationMove:
    """Tests POST /api/plans/operations/{id}/move/

    Déplace une action d'un indicateur (état ou pression) vers un autre.
    """

    def _url(self, operation_id):
        return f'/api/plans/operations/{operation_id}/move/'

    def test_move_operation_to_another_indicateur(self, api_client, reorder_test_data):
        """op1 est liée à metrique1 (sous ind1) : elle passe sous ind2."""
        api_client.force_authenticate(user=reorder_test_data['referent'])
        op = reorder_test_data['op1']
        target = reorder_test_data['ind2']

        response = api_client.post(
            self._url(op.pk),
            {'new_indicateur_id': target.pk, 'position': 0},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        op.refresh_from_db()
        assert op.id_indicateur_id == target.pk
        assert op.ordre == 0

    def test_move_cuts_links_to_source_indicateur_metriques(self, api_client, reorder_test_data):
        """Les liens vers les métriques de l'indicateur QUITTÉ sont supprimés."""
        api_client.force_authenticate(user=reorder_test_data['referent'])
        op = reorder_test_data['op1']
        metrique1 = reorder_test_data['metrique1']  # portée par ind1
        assert op.metriques.filter(pk=metrique1.pk).exists()

        api_client.post(
            self._url(op.pk),
            {'new_indicateur_id': reorder_test_data['ind2'].pk, 'position': 0},
            format='json',
        )

        assert not op.metriques.filter(pk=metrique1.pk).exists()

    def test_move_rattache_laction_aux_metriques_de_la_cible(
        self, api_client, reorder_test_data
    ):
        """#586 — l'action prend les métriques de l'indicateur d'accueil.

        Retour de recette : « en déplaçant l'action, elle ne se rattache pas à
        la nouvelle métrique ». Le déplacement coupait les liens de la source
        sans en créer aucun : l'action s'affichait au bon endroit mais n'était
        plus reliée à aucune métrique.
        """
        from tests.factories.enjeux import MetriqueFactory

        api_client.force_authenticate(user=reorder_test_data['referent'])
        target = reorder_test_data['ind2']
        met_a = MetriqueFactory(id_indicateur=target, nom_metrique='M2-A')
        met_b = MetriqueFactory(id_indicateur=target, nom_metrique='M2-B')
        op = reorder_test_data['op1']

        response = api_client.post(
            self._url(op.pk),
            {'new_indicateur_id': target.pk, 'position': 0},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        op.refresh_from_db()
        assert set(op.metriques.values_list('pk', flat=True)) == {met_a.pk, met_b.pk}
        # Portée par ses métriques : pas de rattachement direct en plus, sinon
        # l'action serait comptée deux fois sous le même indicateur (#367/#539).
        assert op.id_indicateur_id is None

    def test_move_vers_un_indicateur_sans_metrique_garde_le_lien_direct(
        self, api_client, reorder_test_data
    ):
        """#367/#539 — sans métrique, l'action se rattache à l'indicateur."""
        api_client.force_authenticate(user=reorder_test_data['referent'])
        target = reorder_test_data['ind3']   # aucun métrique dans la fixture
        op = reorder_test_data['op1']

        api_client.post(
            self._url(op.pk),
            {'new_indicateur_id': target.pk, 'position': 0},
            format='json',
        )

        op.refresh_from_db()
        assert op.id_indicateur_id == target.pk
        assert list(op.metriques.all()) == []

    def test_move_conserve_les_metriques_dun_autre_indicateur(
        self, api_client, reorder_test_data
    ):
        """Action partagée (#585) : seuls les liens de la source sont coupés."""
        from tests.factories.enjeux import MetriqueFactory

        api_client.force_authenticate(user=reorder_test_data['referent'])
        ailleurs = MetriqueFactory(
            id_indicateur=reorder_test_data['ind_ra_2'], nom_metrique='M-AILLEURS',
        )
        op = reorder_test_data['op1']
        CorOperationMetrique.objects.create(id_operation=op, id_metrique=ailleurs)

        api_client.post(
            self._url(op.pk),
            {
                'new_indicateur_id': reorder_test_data['ind3'].pk,
                'position': 0,
                # L'indicateur d'où l'action a été glissée : lui seul est délié.
                'from_indicateur_id': reorder_test_data['ind1'].pk,
            },
            format='json',
        )

        assert op.metriques.filter(pk=ailleurs.pk).exists()
        assert not op.metriques.filter(
            pk=reorder_test_data['metrique1'].pk
        ).exists()

    def test_move_between_branches_etat_and_pression(self, api_client, reorder_test_data):
        """Une action peut passer d'un indicateur d'état à un indicateur de réponse."""
        api_client.force_authenticate(user=reorder_test_data['referent'])
        op = reorder_test_data['op2']
        target = reorder_test_data['ind_ra_1']

        response = api_client.post(
            self._url(op.pk),
            {'new_indicateur_id': target.pk, 'position': 0},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        op.refresh_from_db()
        assert op.id_indicateur_id == target.pk

    def test_move_renumbers_target_siblings(self, api_client, reorder_test_data):
        """L'action déplacée prend la position demandée, les autres se décalent."""
        api_client.force_authenticate(user=reorder_test_data['referent'])
        target = reorder_test_data['ind2']

        # op3 arrive en premier sous ind2, puis op1 s'insère en position 0.
        api_client.post(
            self._url(reorder_test_data['op3'].pk),
            {'new_indicateur_id': target.pk, 'position': 0},
            format='json',
        )
        api_client.post(
            self._url(reorder_test_data['op1'].pk),
            {'new_indicateur_id': target.pk, 'position': 0},
            format='json',
        )

        op1 = reorder_test_data['op1']
        op3 = reorder_test_data['op3']
        op1.refresh_from_db()
        op3.refresh_from_db()
        assert op1.ordre == 0
        assert op3.ordre == 1

    def test_move_without_indicateur_id_returns_400(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        response = api_client.post(
            self._url(reorder_test_data['op1'].pk), {'position': 0}, format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_move_to_nonexistent_indicateur_returns_404(self, api_client, reorder_test_data):
        api_client.force_authenticate(user=reorder_test_data['referent'])
        response = api_client.post(
            self._url(reorder_test_data['op1'].pk),
            {'new_indicateur_id': 999999, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_move_on_validated_plan_returns_403(self, api_client, reorder_test_data):
        """Verrou #248 : pas de déplacement sur un plan hors brouillon."""
        plan = reorder_test_data['plan']
        plan.statut = 'valide'
        plan.save(update_fields=['statut'])

        api_client.force_authenticate(user=reorder_test_data['referent'])
        response = api_client.post(
            self._url(reorder_test_data['op1'].pk),
            {'new_indicateur_id': reorder_test_data['ind2'].pk, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data

    def test_move_unauthenticated_returns_401(self, api_client, reorder_test_data):
        response = api_client.post(
            self._url(reorder_test_data['op1'].pk),
            {'new_indicateur_id': reorder_test_data['ind2'].pk, 'position': 0},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
