"""
Tests d'intégration pour l'API REST des Suivis de réalisation (Phase 1).

Couvre :
- modèle (1-1 OperationAnnee / OperationAnneeOrganisme, get_plan_de_gestion)
- API CRUD, upsert, by-operation, by-plan
- Scoping par rôle (super_admin / admin_og / référent / utilisateur isolé)
- Sérialisation nested via OperationAnnee
"""
import pytest
from decimal import Decimal
from django.db import transaction, IntegrityError
from rest_framework import status

from apps.plans.models_operations import (
    RealisationOperationAnnee,
    RealisationOperationAnneeOrganisme,
)
from tests.factories.enjeux import (
    EnjeuFactory, NomenclatureEnjeuFactory,
    ObjectifLongTermeFactory, NiveauExigenceFactory,
    IndicateurFactory, MetriqueFactory, OperationFactory,
    NomenclaturePrioriteOperationFactory,
    OperationAnneeFactory, OperationAnneeOrganismeFactory,
    NomenclatureNiveauRealisationFactory,
    RealisationOperationAnneeFactory, RealisationOperationAnneeOrganismeFactory,
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)


@pytest.fixture
def realisation_test_data(db):
    """Données partagées : plan + opération + OperationAnnee + utilisateurs."""
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan Test Réalisations', statut='draft')
    CorSitePgFactory(plan_de_gestion=plan, site=site)

    super_admin = SuperAdminFactory()
    admin_og = AdminOrganismeFactory(id_organisme=organisme)
    referent = ReferentFactory(id_organisme=organisme)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan.referents.add(referent)
    other_user = RoleFactory()  # n'a accès à rien

    # Hiérarchie enjeu → ... → métrique pour rattacher l'opération au plan
    cat_enjeu = NomenclatureEnjeuFactory()
    priorite = NomenclaturePrioriteOperationFactory(
        mnemonique='PRIORITE_1', cd_nomenclature='P1', label='Priorité 1'
    )
    enjeu = EnjeuFactory(
        id_pg=plan, id_categorie=cat_enjeu, libelle='Enjeu Test',
        rang=1, categorie_ecologique=True, id_utilisateur_ajout=referent,
    )
    olt = ObjectifLongTermeFactory(id_enjeu=enjeu, libelle='OLT Test', id_utilisateur_ajout=referent)
    ne = NiveauExigenceFactory(id_olt=olt, libelle='NE Test', id_utilisateur_ajout=referent)
    indicateur = IndicateurFactory(id_ne=ne, nom_indicateur='Ind Test', id_utilisateur_ajout=referent)
    metrique = MetriqueFactory(id_indicateur=indicateur, nom_metrique='Métrique Test', id_utilisateur_ajout=referent)

    operation = OperationFactory(
        libelle='Opération Test Réalisation',
        id_priorite=priorite, code_operation='REA-001',
        annee_min=2024, annee_max=2026,
        ventilation_mode='none',
        metriques=[metrique],
        id_utilisateur_ajout=referent,
    )
    op_annee = OperationAnneeFactory(
        id_operation=operation, annee=2024,
        periodicite=True, budget=Decimal('1000.00'), etp=Decimal('5.00'),
    )

    niveau_termine = NomenclatureNiveauRealisationFactory(mnemonique='TERMINE')
    niveau_partiel = NomenclatureNiveauRealisationFactory(mnemonique='PARTIEL')

    return {
        'organisme': organisme, 'site': site, 'plan': plan,
        'super_admin': super_admin, 'admin_og': admin_og,
        'referent': referent, 'other_user': other_user,
        'operation': operation, 'op_annee': op_annee,
        'niveau_termine': niveau_termine, 'niveau_partiel': niveau_partiel,
    }


# =============================================================================
# Modèle
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestRealisationModel:

    def test_one_to_one_constraint_with_operation_annee(self, realisation_test_data):
        """Impossible de créer 2 RealisationOperationAnnee pour la même OperationAnnee."""
        RealisationOperationAnneeFactory(
            id_operation_annee=realisation_test_data['op_annee']
        )
        # Encapsuler dans un savepoint pour ne pas empoisonner la transaction de test.
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                RealisationOperationAnneeFactory(
                    id_operation_annee=realisation_test_data['op_annee']
                )

    def test_get_plan_de_gestion_via_metrique(self, realisation_test_data):
        """La réalisation remonte au plan via OperationAnnee → Operation → métrique."""
        realisation = RealisationOperationAnneeFactory(
            id_operation_annee=realisation_test_data['op_annee']
        )
        assert realisation.get_plan_de_gestion() == realisation_test_data['plan']

    def test_cascade_delete_from_operation_annee(self, realisation_test_data):
        """Supprimer OperationAnnee supprime la réalisation associée."""
        realisation = RealisationOperationAnneeFactory(
            id_operation_annee=realisation_test_data['op_annee']
        )
        rid = realisation.pk
        realisation_test_data['op_annee'].delete()
        assert not RealisationOperationAnnee.objects.filter(pk=rid).exists()

    def test_organisme_realisation_get_plan(self, realisation_test_data):
        """RealisationOperationAnneeOrganisme.get_plan_de_gestion via la chaîne complète."""
        oao = OperationAnneeOrganismeFactory(
            id_operation_annee=realisation_test_data['op_annee'],
            id_organisme=realisation_test_data['organisme'],
        )
        realisation_org = RealisationOperationAnneeOrganismeFactory(
            id_operation_annee_organisme=oao
        )
        assert realisation_org.get_plan_de_gestion() == realisation_test_data['plan']


# =============================================================================
# API — Liste / lecture
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestRealisationListEndpoint:

    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get('/api/plans/realisations/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, realisation_test_data):
        RealisationOperationAnneeFactory(id_operation_annee=realisation_test_data['op_annee'])
        # Autre réalisation pas dans le scope
        RealisationOperationAnneeFactory()
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get('/api/plans/realisations/')
        assert response.status_code == status.HTTP_200_OK
        # super_admin voit tout (2)
        results = response.data.get('results', response.data)
        assert len(results) >= 2

    def test_referent_sees_own_plan_realisations(self, api_client, realisation_test_data):
        RealisationOperationAnneeFactory(id_operation_annee=realisation_test_data['op_annee'])
        RealisationOperationAnneeFactory()  # autre plan
        api_client.force_authenticate(user=realisation_test_data['referent'])
        response = api_client.get('/api/plans/realisations/')
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get('results', response.data)
        # Le référent voit la réalisation de son plan ; pas garanti qu'il ne voie pas d'autres
        # plans en statut 'valide', mais doit voir la sienne.
        ids = [r['id_realisation_operation_annee'] for r in results]
        assert len(ids) >= 1

    def test_isolated_user_sees_nothing(self, api_client, realisation_test_data):
        """
        #610 — la lecture est ouverte à tout authentifié, mais bornée au
        périmètre : un utilisateur sans rattachement ne voit aucune réalisation.
        """
        RealisationOperationAnneeFactory(id_operation_annee=realisation_test_data['op_annee'])
        api_client.force_authenticate(user=realisation_test_data['other_user'])
        response = api_client.get('/api/plans/realisations/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'] == []

    def test_filter_by_operation_annee(self, api_client, realisation_test_data):
        r1 = RealisationOperationAnneeFactory(id_operation_annee=realisation_test_data['op_annee'])
        RealisationOperationAnneeFactory()
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/realisations/?id_operation_annee={realisation_test_data["op_annee"].pk}'
        )
        results = response.data.get('results', response.data)
        assert len(results) == 1
        assert results[0]['id_realisation_operation_annee'] == r1.pk


# =============================================================================
# API — Upsert (saisie depuis le formulaire)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestRealisationUpsertEndpoint:

    def test_upsert_creates_when_missing(self, api_client, realisation_test_data):
        api_client.force_authenticate(user=realisation_test_data['referent'])
        payload = {
            'id_operation_annee': realisation_test_data['op_annee'].pk,
            'id_niveau_realisation': realisation_test_data['niveau_termine'].pk,
            'periodicite_realisee': True,
            'budget_realise': '950.00',
            'etp_realise': '4.50',
            'commentaires': 'Test saisie',
        }
        response = api_client.post('/api/plans/realisations/upsert/', payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['budget_realise'] == '950.00'
        assert response.data['commentaires'] == 'Test saisie'
        assert RealisationOperationAnnee.objects.filter(
            id_operation_annee=realisation_test_data['op_annee']
        ).exists()

    def test_upsert_updates_when_present(self, api_client, realisation_test_data):
        existing = RealisationOperationAnneeFactory(
            id_operation_annee=realisation_test_data['op_annee'],
            budget_realise=Decimal('500.00'),
        )
        api_client.force_authenticate(user=realisation_test_data['referent'])
        payload = {
            'id_operation_annee': realisation_test_data['op_annee'].pk,
            'budget_realise': '999.99',
        }
        response = api_client.post('/api/plans/realisations/upsert/', payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        existing.refresh_from_db()
        assert existing.budget_realise == Decimal('999.99')
        # Une seule réalisation existe toujours (pas de doublon)
        assert RealisationOperationAnnee.objects.filter(
            id_operation_annee=realisation_test_data['op_annee']
        ).count() == 1

    def test_upsert_derives_periodicite_from_niveau(self, api_client, realisation_test_data):
        """#609 — la périodicité réalisée est dérivée du niveau (TERMINE → cochée)."""
        api_client.force_authenticate(user=realisation_test_data['referent'])
        response = api_client.post('/api/plans/realisations/upsert/', {
            'id_operation_annee': realisation_test_data['op_annee'].pk,
            'id_niveau_realisation': realisation_test_data['niveau_termine'].pk,
            # périodicité non transmise : elle doit être déduite du niveau.
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['periodicite_realisee'] is True

    def test_upsert_non_realise_unchecks_periodicite(self, api_client, realisation_test_data):
        """#609 — « non réalisé » ⇒ périodicité décochée, même envoyée à True."""
        niveau_non = NomenclatureNiveauRealisationFactory(mnemonique='NON_REALISE')
        api_client.force_authenticate(user=realisation_test_data['referent'])
        response = api_client.post('/api/plans/realisations/upsert/', {
            'id_operation_annee': realisation_test_data['op_annee'].pk,
            'id_niveau_realisation': niveau_non.pk,
            'periodicite_realisee': True,  # tentative : doit être ignorée (#609)
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['periodicite_realisee'] is False

    def test_org_upsert_persists_realised_cost_detail(self, api_client, realisation_test_data):
        """#608 — détail des coûts réalisés (ventilation maximale) enregistré."""
        oao = OperationAnneeOrganismeFactory(
            id_operation_annee=realisation_test_data['op_annee'],
            id_organisme=realisation_test_data['organisme'],
        )
        api_client.force_authenticate(user=realisation_test_data['referent'])
        response = api_client.post('/api/plans/realisations-organismes/upsert/', {
            'id_operation_annee_organisme': oao.pk,
            'cout_prestataire_realise': '1200.00',
            'autre_cout_realise': '500.00',
            'autre_cout_commentaire_realise': 'Frais divers',
            'cout_prestataire_invest_realise': '700.00',
            'autre_cout_invest_realise': '300.00',
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['cout_prestataire_realise'] == '1200.00'
        assert response.data['autre_cout_invest_realise'] == '300.00'
        assert response.data['autre_cout_commentaire_realise'] == 'Frais divers'

    def test_upsert_persists_realised_cost_detail_without_org(self, api_client, realisation_test_data):
        """#624 — mode « par type de budget + type de poste » : le détail des
        coûts réalisés est porté par l'ANNÉE, sans organisme.
        """
        api_client.force_authenticate(user=realisation_test_data['referent'])
        response = api_client.post('/api/plans/realisations/upsert/', {
            'id_operation_annee': realisation_test_data['op_annee'].pk,
            'cout_stage_realise': '200.00',
            'cout_prestataire_realise': '1200.00',
            'autre_cout_realise': '500.00',
            'autre_cout_commentaire_realise': 'Frais divers',
            'cout_prestataire_invest_realise': '700.00',
            'autre_cout_invest_realise': '300.00',
            'autre_cout_invest_commentaire_realise': 'Matériel',
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['cout_stage_realise'] == '200.00'
        assert response.data['cout_prestataire_realise'] == '1200.00'
        assert response.data['autre_cout_commentaire_realise'] == 'Frais divers'
        assert response.data['autre_cout_invest_realise'] == '300.00'
        assert response.data['autre_cout_invest_commentaire_realise'] == 'Matériel'
        instance = RealisationOperationAnnee.objects.get(
            id_operation_annee=realisation_test_data['op_annee']
        )
        assert instance.cout_prestataire_realise == Decimal('1200.00')
        assert instance.autre_cout_invest_realise == Decimal('300.00')

    def test_upsert_persists_operateurs_financeurs_realises(self, api_client, realisation_test_data):
        """#541 — opérateur(s)/financeur(s) réalisés saisis par année dans le suivi."""
        api_client.force_authenticate(user=realisation_test_data['referent'])
        payload = {
            'id_operation_annee': realisation_test_data['op_annee'].pk,
            'operateurs_realises': 'Conservateur, Chargé de mission pastoralisme',
            'financeurs_realises': "Agence de l'Eau, PAC (MAEC)",
        }
        response = api_client.post('/api/plans/realisations/upsert/', payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['operateurs_realises'] == 'Conservateur, Chargé de mission pastoralisme'
        assert response.data['financeurs_realises'] == "Agence de l'Eau, PAC (MAEC)"
        instance = RealisationOperationAnnee.objects.get(
            id_operation_annee=realisation_test_data['op_annee']
        )
        assert instance.operateurs_realises == 'Conservateur, Chargé de mission pastoralisme'
        assert instance.financeurs_realises == "Agence de l'Eau, PAC (MAEC)"

    def test_upsert_requires_id_operation_annee(self, api_client, realisation_test_data):
        api_client.force_authenticate(user=realisation_test_data['referent'])
        response = api_client.post('/api/plans/realisations/upsert/', {}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upsert_forbidden_for_isolated_user(self, api_client, realisation_test_data):
        api_client.force_authenticate(user=realisation_test_data['other_user'])
        payload = {
            'id_operation_annee': realisation_test_data['op_annee'].pk,
            'id_niveau_realisation': realisation_test_data['niveau_termine'].pk,
        }
        response = api_client.post('/api/plans/realisations/upsert/', payload, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upsert_works_on_validated_plan(self, api_client, realisation_test_data):
        """Vérifie qu'un suivi peut être saisi même quand le plan est validé."""
        realisation_test_data['plan'].statut = 'valide'
        realisation_test_data['plan'].save()
        api_client.force_authenticate(user=realisation_test_data['referent'])
        payload = {
            'id_operation_annee': realisation_test_data['op_annee'].pk,
            'budget_realise': '1100.00',
        }
        response = api_client.post('/api/plans/realisations/upsert/', payload, format='json')
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# API — Endpoints custom
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestRealisationByOperationEndpoint:

    def test_by_operation_returns_realisations(self, api_client, realisation_test_data):
        op_annee_2 = OperationAnneeFactory(
            id_operation=realisation_test_data['operation'], annee=2025,
        )
        r1 = RealisationOperationAnneeFactory(id_operation_annee=realisation_test_data['op_annee'])
        r2 = RealisationOperationAnneeFactory(id_operation_annee=op_annee_2)
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/realisations/by-operation/{realisation_test_data["operation"].pk}/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 2
        ids = [r['id_realisation_operation_annee'] for r in response.data['realisations']]
        assert set(ids) == {r1.pk, r2.pk}


@pytest.mark.django_db
@pytest.mark.integration
class TestRealisationByPlanEndpoint:

    def test_by_plan_returns_realisations(self, api_client, realisation_test_data):
        RealisationOperationAnneeFactory(id_operation_annee=realisation_test_data['op_annee'])
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/realisations/by-plan/{realisation_test_data["plan"].pk}/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['plan_id'] == realisation_test_data['plan'].pk
        assert response.data['total'] == 1


# =============================================================================
# API — Endpoint Bilan (agrégations)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestRealisationBilanEndpoint:

    def test_bilan_empty_plan_returns_zero_counts(self, api_client, realisation_test_data):
        """Bilan d'un plan sans aucune réalisation : tous les compteurs à zéro."""
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/realisations/bilan/{realisation_test_data["plan"].pk}/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['plan_id'] == realisation_test_data['plan'].pk
        assert response.data['taux_realisation']['total'] == 0
        assert response.data['by_categorie_action'] == []
        assert response.data['by_enjeu'] == []
        assert response.data['budget']['total']['previsionnel'] == 0
        assert response.data['budget']['total']['realise'] == 0
        assert response.data['rh']['previsionnel'] == 0
        assert response.data['rh']['realise'] == 0

    def test_bilan_counts_by_niveau(self, api_client, realisation_test_data):
        """1 réalisation TERMINE → taux_realisation.termine = 1, total = 1."""
        RealisationOperationAnneeFactory(
            id_operation_annee=realisation_test_data['op_annee'],
            id_niveau_realisation=realisation_test_data['niveau_termine'],
        )
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/realisations/bilan/{realisation_test_data["plan"].pk}/'
        )
        assert response.status_code == status.HTTP_200_OK
        taux = response.data['taux_realisation']
        assert taux['total'] == 1
        assert taux['termine'] == 1

    def test_bilan_aggregates_budget_for_none_mode(self, api_client, realisation_test_data):
        """Mode 'none' : budget_realise remonte au niveau année."""
        from decimal import Decimal
        RealisationOperationAnneeFactory(
            id_operation_annee=realisation_test_data['op_annee'],
            id_niveau_realisation=realisation_test_data['niveau_termine'],
            budget_realise=Decimal('800.00'),
        )
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/realisations/bilan/{realisation_test_data["plan"].pk}/'
        )
        assert response.data['budget']['fonctionnement']['previsionnel'] == 1000.0  # planifié
        assert response.data['budget']['fonctionnement']['realise'] == 800.0       # réalisé

    def test_bilan_rh_lit_les_lignes_rh_et_non_etp(self, api_client, realisation_test_data):
        """
        #560 — le temps de travail du bilan vient des lignes RH, plus du champ
        `etp` (déprécié, conservé en base et converti par la migration 0100).

        Volontairement dissocié de `etp` : si le bilan retombait sur `etp` en
        l'absence de lignes RH, supprimer toutes les lignes d'une année (= « rien
        de prévu ») ferait ressurgir l'ancienne valeur.
        """
        from decimal import Decimal
        from apps.plans.models_operations import (
            OperationAnneeRH, RealisationOperationAnneeRH,
        )
        oa = realisation_test_data['op_annee']
        assert oa.etp == Decimal('5.00'), "le fixture porte bien un etp hérité"

        OperationAnneeRH.objects.create(id_operation_annee=oa, jours=7, finance=True)
        OperationAnneeRH.objects.create(id_operation_annee=oa, jours=2, finance=False)
        realisation = RealisationOperationAnneeFactory(
            id_operation_annee=oa,
            id_niveau_realisation=realisation_test_data['niveau_termine'],
            etp_realise=Decimal('4.00'),
        )
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=realisation, jours=6, finance=True,
        )

        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/realisations/bilan/{realisation_test_data["plan"].pk}/'
        )
        rh = response.data['rh']
        assert rh['previsionnel'] == 9.0   # 7 + 2, et non les 5.0 de `etp`
        assert rh['realise'] == 6.0        # et non les 4.0 de `etp_realise`
        assert rh['previsionnel_finance'] == 7.0
        assert rh['previsionnel_non_finance'] == 2.0
        assert rh['realise_finance'] == 6.0
        assert rh['realise_non_finance'] == 0.0

    def test_bilan_groups_by_categorie_action(self, api_client, realisation_test_data):
        """L'agrégation par catégorie utilise id_categorie_action_reserve ou id_type_action."""
        RealisationOperationAnneeFactory(
            id_operation_annee=realisation_test_data['op_annee'],
            id_niveau_realisation=realisation_test_data['niveau_termine'],
        )
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/realisations/bilan/{realisation_test_data["plan"].pk}/'
        )
        assert len(response.data['by_categorie_action']) >= 1
        cat = response.data['by_categorie_action'][0]
        assert cat['total'] == 1
        assert cat['termine'] == 1

    def test_bilan_forbidden_for_isolated_user(self, api_client, realisation_test_data):
        """#610 — accès au plan requis : agrégation calculée hors get_queryset()."""
        api_client.force_authenticate(user=realisation_test_data['other_user'])
        response = api_client.get(
            f'/api/plans/realisations/bilan/{realisation_test_data["plan"].pk}/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# API — Bilan : séries par année (graphiques « évolution »)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestRealisationBilanSeriesEndpoint:

    def test_series_structure_and_empty(self, api_client, realisation_test_data):
        """Plan sans réalisation : séries alignées sur les années, tout à None/0."""
        plan = realisation_test_data['plan']
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(f'/api/plans/realisations/bilan-series/{plan.pk}/')

        assert response.status_code == status.HTTP_200_OK
        years = response.data['years']
        assert years == list(range(plan.annee_debut, plan.annee_fin + 1))
        n = len(years)

        ev = response.data['indicateurs_evolution']
        for key in ('mean', 'min', 'max', 'std'):
            assert len(ev[key]) == n
            assert all(v is None for v in ev[key])  # aucune mesure → tout None

        assert response.data['rh_par_annee']['previsionnel'] == [0.0] * n
        assert response.data['rh_par_annee']['realise'] == [0.0] * n

        niveaux = response.data['actions_par_annee']['niveaux']
        assert {'termine', 'partiel', 'en_cours', 'reporte',
                'non_demarre', 'abandonne', 'inconnu'}.issubset(niveaux.keys())
        assert all(sum(v) == 0 for v in niveaux.values())

    def test_series_rh_and_actions_bucketed_by_year(self, api_client, realisation_test_data):
        """RH (prévi/réel) et niveau de réalisation atterrissent dans la bonne année."""
        from decimal import Decimal
        from apps.plans.models_operations import (
            OperationAnneeRH, RealisationOperationAnneeRH,
        )
        plan = realisation_test_data['plan']
        year = plan.annee_debut  # dans la fenêtre du plan
        oa = OperationAnneeFactory(
            id_operation=realisation_test_data['operation'], annee=year,
            periodicite=True, budget=Decimal('500.00'),
        )
        OperationAnneeRH.objects.create(id_operation_annee=oa, jours=10, finance=True)
        realisation = RealisationOperationAnneeFactory(
            id_operation_annee=oa,
            id_niveau_realisation=realisation_test_data['niveau_termine'],
        )
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=realisation, jours=8, finance=True,
        )

        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(f'/api/plans/realisations/bilan-series/{plan.pk}/')

        assert response.status_code == status.HTTP_200_OK
        i = response.data['years'].index(year)
        assert response.data['rh_par_annee']['previsionnel'][i] == 10.0
        assert response.data['rh_par_annee']['realise'][i] == 8.0
        assert response.data['actions_par_annee']['niveaux']['termine'][i] == 1

    def test_series_forbidden_for_isolated_user(self, api_client, realisation_test_data):
        """Même contrôle d'accès au plan que /bilan/ (#610)."""
        api_client.force_authenticate(user=realisation_test_data['other_user'])
        response = api_client.get(
            f'/api/plans/realisations/bilan-series/{realisation_test_data["plan"].pk}/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# API — Réalisations par organisme (ventilation)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestRealisationOrganismeEndpoint:

    def test_upsert_creates_organisme_realisation(self, api_client, realisation_test_data):
        oao = OperationAnneeOrganismeFactory(
            id_operation_annee=realisation_test_data['op_annee'],
            id_organisme=realisation_test_data['organisme'],
        )
        api_client.force_authenticate(user=realisation_test_data['referent'])
        payload = {
            'id_operation_annee_organisme': oao.pk,
            'budget_fonctionnement_realise': '600.00',
            'budget_investissement_realise': '400.00',
            'etp_realise': '3.00',
        }
        response = api_client.post(
            '/api/plans/realisations-organismes/upsert/', payload, format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['budget_fonctionnement_realise'] == '600.00'
        assert RealisationOperationAnneeOrganisme.objects.filter(
            id_operation_annee_organisme=oao
        ).count() == 1


# =============================================================================
# Sérialisation nested via OperationAnneeSerializer
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestRealisationNestedInOperation:

    def test_operation_detail_includes_realisation(self, api_client, realisation_test_data):
        """Le détail opération expose realisation dans chaque operation_annee."""
        RealisationOperationAnneeFactory(
            id_operation_annee=realisation_test_data['op_annee'],
            id_niveau_realisation=realisation_test_data['niveau_termine'],
            budget_realise=Decimal('950.00'),
        )
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/operations/{realisation_test_data["operation"].pk}/'
        )
        assert response.status_code == status.HTTP_200_OK
        annees = response.data.get('operation_annees', [])
        assert annees, "operation_annees vide"
        annee_2024 = next((a for a in annees if a['annee'] == 2024), None)
        assert annee_2024 is not None
        assert annee_2024['realisation'] is not None
        assert annee_2024['realisation']['budget_realise'] == '950.00'
        assert annee_2024['realisation']['niveau_realisation_mnemonique'] == 'TERMINE'

    def test_operation_detail_realisation_null_if_not_seeded(self, api_client, realisation_test_data):
        """Si pas de réalisation, le champ est null (et l'opération reste lisible)."""
        api_client.force_authenticate(user=realisation_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/operations/{realisation_test_data["operation"].pk}/'
        )
        assert response.status_code == status.HTTP_200_OK
        annees = response.data.get('operation_annees', [])
        annee_2024 = next((a for a in annees if a['annee'] == 2024), None)
        assert annee_2024 is not None
        assert annee_2024['realisation'] is None
