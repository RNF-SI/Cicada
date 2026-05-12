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
        _assert_order(FacteurInfluence, 'id_facteur_influence', ids)

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
        _assert_order(ObjectifOperationnel, 'id_oo', ids)


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
