"""
Tests pour le code calculé d'affichage des opérations (#228 / 2026-05-12).

Couvre :
- Calcul `<prefix><rang>` avec `id_categorie_action_reserve` prioritaire
- Fallback sur `id_type_action.cd_nomenclature` quand pas de catégorie réserve
- Une même Operation rattachée à plusieurs métriques compte une seule fois
- L'endpoint by-plan retourne le code calculé dans la branche NE et la branche RA
- Le move/reorder respecte le verrou hors brouillon (seul draft est éditable)
"""
import pytest
from rest_framework import status

from apps.plans.models_operations import Operation, CorOperationMetrique
from apps.plans.serializers_operations import compute_operation_codes_for_plan
from apps.core.models import Nomenclature, TypeNomenclature
from tests.factories.enjeux import (
    EnjeuFactory, ObjectifLongTermeFactory, NiveauExigenceFactory,
    IndicateurFactory, MetriqueFactory, OperationFactory,
    NomenclatureEnjeuFactory, NomenclatureTypeIndicateurFactory,
    NomenclatureTypeMetriqueFactory,
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory
from tests.factories.users import (
    SuperAdminFactory, ReferentFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)


@pytest.fixture
def cat_reserve_nomenclatures(db):
    """Garantit que les nomenclatures CATEGORIE_ACTION_RESERVE existent
    (créées par la migration 0063, mais on les force ici pour les tests
    qui repartent d'une base vierge)."""
    type_cat, _ = TypeNomenclature.objects.get_or_create(
        id_type=66,
        defaults={
            'mnemonique': 'CATEGORIE_ACTION_RESERVE',
            'label': "Catégorie d'action réserve",
            'source': 'CICADA/CT88',
            'statut': 'Validé',
        },
    )
    entries = [
        ('SP', "Surveillance"),
        ('CS', "Connaissance et suivi"),
        ('IP', "Interventions"),
    ]
    nomencs = {}
    for code, label in entries:
        n, _ = Nomenclature.objects.get_or_create(
            cd_nomenclature=code,
            id_type=type_cat,
            defaults={
                'mnemonique': code,
                'label': label,
                'definition': label,
                'source': 'CICADA/CT88',
                'statut': 'Validé',
                'hierarchy': code,
                'actif': True,
            },
        )
        nomencs[code] = n
    return nomencs


@pytest.fixture
def type_action_nomenclatures(db):
    """Récupère ou crée 2 entrées TYPE_ACTION pour les tests fallback."""
    type_ta, _ = TypeNomenclature.objects.get_or_create(
        id_type=51,
        defaults={
            'mnemonique': 'TYPE_ACTION',
            'label': "Type d'action",
            'source': 'CICADA',
            'statut': 'Validé',
        },
    )
    cs1, _ = Nomenclature.objects.get_or_create(
        cd_nomenclature='CS1',
        id_type=type_ta,
        defaults={
            'mnemonique': 'CS1',
            'label': 'Surveillance des impacts',
            'definition': 'Surveillance',
            'source': 'CICADA',
            'statut': 'Validé',
            'hierarchy': 'CS1',
            'actif': True,
        },
    )
    ip1, _ = Nomenclature.objects.get_or_create(
        cd_nomenclature='IP1',
        id_type=type_ta,
        defaults={
            'mnemonique': 'IP1',
            'label': "Restauration d'habitats",
            'definition': 'Restauration',
            'source': 'CICADA',
            'statut': 'Validé',
            'hierarchy': 'IP1',
            'actif': True,
        },
    )
    return {'CS1': cs1, 'IP1': ip1}


@pytest.fixture
def plan_with_actions(db, cat_reserve_nomenclatures, type_action_nomenclatures):
    """Construit un plan draft avec 1 enjeu / OLT / NE / indicateur / métrique
    et plusieurs actions de préfixes variés pour tester le code calculé."""
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)
    plan = PlanGestionFactory(nom='Plan Test Codes', statut='draft')
    CorSitePgFactory(plan_de_gestion=plan, site=site)
    referent = ReferentFactory(id_organisme=organisme)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan.referents.add(referent)
    super_admin = SuperAdminFactory()

    cat_enjeu = NomenclatureEnjeuFactory()
    enjeu = EnjeuFactory(id_pg=plan, id_categorie=cat_enjeu, libelle='E1', id_utilisateur_ajout=referent)
    olt = ObjectifLongTermeFactory(id_enjeu=enjeu, libelle='OLT1', id_utilisateur_ajout=referent)
    ne = NiveauExigenceFactory(id_olt=olt, libelle='NE1', id_utilisateur_ajout=referent)
    # #576 — épingler le type ETAT : cet indicateur est rattaché à un NE (branche
    # OLT/état), donc la vue by-plan ne le niche sous le NE que s'il est de type
    # ETAT. Sans ce pin, IndicateurFactory tire son type d'un factory.Iterator
    # (['ETAT','PRESSION','REPONSE']) dont l'état fuit entre tests : selon l'ordre
    # d'exécution, l'indicateur pouvait être créé en REPONSE et disparaître de la
    # branche OLT → aucune opération trouvée → test flaky (échec en suite complète,
    # OK en isolation).
    type_ind = NomenclatureTypeIndicateurFactory(cd_nomenclature='ETAT', mnemonique='ETAT')
    type_met = NomenclatureTypeMetriqueFactory()
    ind = IndicateurFactory(id_ne=ne, nom_indicateur='IND1', type_indicateur=type_ind, id_utilisateur_ajout=referent)
    met = MetriqueFactory(id_indicateur=ind, nom_metrique='M1', type_metrique=type_met, id_utilisateur_ajout=referent)
    met2 = MetriqueFactory(id_indicateur=ind, nom_metrique='M2', type_metrique=type_met, id_utilisateur_ajout=referent)

    # 3 opérations : 2 avec catégorie réserve, 1 avec type_action seul
    op_cs = OperationFactory(
        libelle='Action CS via catégorie réserve',
        id_priorite=None,
        id_categorie_action_reserve=cat_reserve_nomenclatures['CS'],
        id_utilisateur_ajout=referent,
        ordre=0,
    )
    op_ip = OperationFactory(
        libelle='Action IP via catégorie réserve',
        id_priorite=None,
        id_categorie_action_reserve=cat_reserve_nomenclatures['IP'],
        id_utilisateur_ajout=referent,
        ordre=1,
    )
    op_via_type = OperationFactory(
        libelle='Action CS via type_action seul',
        id_priorite=None,
        id_type_action=type_action_nomenclatures['CS1'],
        id_utilisateur_ajout=referent,
        ordre=2,
    )

    # Lien M2M : op_cs sur 2 métriques (test du dédoublonnage)
    CorOperationMetrique.objects.create(id_operation=op_cs, id_metrique=met)
    CorOperationMetrique.objects.create(id_operation=op_cs, id_metrique=met2)
    CorOperationMetrique.objects.create(id_operation=op_ip, id_metrique=met)
    CorOperationMetrique.objects.create(id_operation=op_via_type, id_metrique=met)

    return {
        'plan': plan, 'enjeu': enjeu, 'metrique': met,
        'referent': referent, 'super_admin': super_admin,
        'op_cs': op_cs, 'op_ip': op_ip, 'op_via_type': op_via_type,
    }


# =============================================================================
# Helper de calcul (unitaire)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestComputeOperationCodes:
    def test_categorie_reserve_prend_la_priorite(self, plan_with_actions):
        codes = compute_operation_codes_for_plan(plan_with_actions['plan'].pk)
        # op_cs : catégorie 'CS', 1er ordre → 'CS1'
        assert codes[plan_with_actions['op_cs'].pk] == 'CS1'
        # op_ip : catégorie 'IP', 1er ordre IP → 'IP1'
        assert codes[plan_with_actions['op_ip'].pk] == 'IP1'

    def test_fallback_sur_type_action(self, plan_with_actions):
        codes = compute_operation_codes_for_plan(plan_with_actions['plan'].pk)
        # op_via_type : pas de cat réserve, type_action='CS1' → préfixe 'CS', rang 2 (après op_cs)
        assert codes[plan_with_actions['op_via_type'].pk] == 'CS2'

    def test_dedoublonnage_m2m(self, plan_with_actions):
        """op_cs est liée à 2 métriques, mais ne doit avoir qu'UN code."""
        codes = compute_operation_codes_for_plan(plan_with_actions['plan'].pk)
        # Compte le nombre d'entrées avec code commençant par 'CS'
        cs_count = sum(1 for v in codes.values() if v.startswith('CS'))
        assert cs_count == 2  # op_cs + op_via_type, PAS 3 (op_cs comptée une fois)

    def test_dnd_intra_metrique_decale_localement(self, plan_with_actions):
        """
        Démontre la stabilité du nouveau calcul (#228 v2) :
        - On part d'un plan avec une seule métrique partagée par 3 actions
          (op_cs, op_ip, op_via_type) classées dans cet ordre par `ordre`.
        - On échange op_cs et op_via_type dans la métrique → ordre devient
          [op_via_type, op_ip, op_cs].
        - Les codes CS doivent suivre la nouvelle position de lecture :
            op_via_type (préfixe CS via type_action) → CS1
            op_cs (préfixe CS via cat. réserve) → CS2
          Tout autre action conserve son rang relatif.
        """
        op_cs = plan_with_actions['op_cs']
        op_via_type = plan_with_actions['op_via_type']

        # État initial : op_cs = CS1 (ordre=0), op_via_type = CS2 (ordre=2)
        codes_before = compute_operation_codes_for_plan(plan_with_actions['plan'].pk)
        assert codes_before[op_cs.pk] == 'CS1'
        assert codes_before[op_via_type.pk] == 'CS2'

        # Échange : op_via_type passe en tête, op_cs en queue.
        op_via_type.ordre = 0
        op_via_type.save(update_fields=['ordre'])
        op_cs.ordre = 2
        op_cs.save(update_fields=['ordre'])

        codes_after = compute_operation_codes_for_plan(plan_with_actions['plan'].pk)
        assert codes_after[op_via_type.pk] == 'CS1'
        assert codes_after[op_cs.pk] == 'CS2'
        # IP1 n'a pas bougé (autre préfixe, autre compteur).
        assert codes_after[plan_with_actions['op_ip'].pk] == 'IP1'


# =============================================================================
# Numéro fixé manuellement dans le code (#485, décline #442 / #526)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestComputeOperationCodesNumeroManuel:
    """Le chiffre du code (CS1, IP2…) est fixable manuellement (`numero_manuel`).
    Un numéro fixé est réservé POUR SON PRÉFIXE : l'action le conserve quel que
    soit l'ordre (drag & drop) et l'auto-numérotation des autres actions du même
    préfixe saute cet indice."""

    def test_numero_fixe_impose_le_chiffre_du_code(self, plan_with_actions):
        op_via_type = plan_with_actions['op_via_type']  # préfixe CS via type_action
        op_via_type.numero_manuel = 1
        op_via_type.save(update_fields=['numero_manuel'])

        codes = compute_operation_codes_for_plan(plan_with_actions['plan'].pk)
        # op_via_type garde CS1 bien qu'elle soit en 2e position de lecture (ordre=2).
        assert codes[op_via_type.pk] == 'CS1'
        # op_cs (auto, préfixe CS) saute l'indice 1 réservé → CS2.
        assert codes[plan_with_actions['op_cs'].pk] == 'CS2'
        # Autre préfixe non impacté.
        assert codes[plan_with_actions['op_ip'].pk] == 'IP1'

    def test_numero_fixe_persiste_au_reordonnancement(self, plan_with_actions):
        """Le cœur de #485 : un numéro fixé ne change pas au drag & drop et son
        indice n'est pas réattribué aux autres actions du même préfixe."""
        op_cs = plan_with_actions['op_cs']            # CS via cat réserve, ordre 0
        op_via_type = plan_with_actions['op_via_type']  # CS via type_action, ordre 2

        op_cs.numero_manuel = 2
        op_cs.save(update_fields=['numero_manuel'])

        codes_before = compute_operation_codes_for_plan(plan_with_actions['plan'].pk)
        assert codes_before[op_cs.pk] == 'CS2'        # fixé
        assert codes_before[op_via_type.pk] == 'CS1'  # auto, saute le 2

        # On déplace op_cs (fixé) en tête : son code ne doit PAS bouger.
        op_cs.ordre = 5
        op_cs.save(update_fields=['ordre'])
        op_via_type.ordre = 0
        op_via_type.save(update_fields=['ordre'])

        codes_after = compute_operation_codes_for_plan(plan_with_actions['plan'].pk)
        assert codes_after[op_cs.pk] == 'CS2'         # inchangé malgré le déplacement
        assert codes_after[op_via_type.pk] == 'CS1'   # auto, saute toujours le 2

    def test_reservation_est_par_prefixe(self, plan_with_actions):
        """Un numéro fixé sur un préfixe (CS) ne réserve rien sur un autre (IP)."""
        op_cs = plan_with_actions['op_cs']
        op_cs.numero_manuel = 1
        op_cs.save(update_fields=['numero_manuel'])

        codes = compute_operation_codes_for_plan(plan_with_actions['plan'].pk)
        assert codes[op_cs.pk] == 'CS1'
        # op_via_type (CS auto) saute le 1 réservé → CS2.
        assert codes[plan_with_actions['op_via_type'].pk] == 'CS2'
        # op_ip (IP auto) démarre à 1 : la réservation CS ne l'affecte pas.
        assert codes[plan_with_actions['op_ip'].pk] == 'IP1'


# =============================================================================
# Endpoint by-plan : code_affichage exposé via serializer context
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestByPlanCodeAffichage:
    def test_code_affichage_present_dans_by_plan(self, api_client, plan_with_actions):
        api_client.force_authenticate(user=plan_with_actions['referent'])
        url = f'/api/plans/enjeux/by-plan/{plan_with_actions["plan"].pk}/'
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Naviguer dans le payload pour trouver une opération
        body = response.json()
        found_codes = set()
        for enjeu in body.get('enjeux', []):
            for olt in enjeu.get('objectifs_long_terme', []):
                for ne in olt.get('niveaux_exigence', []):
                    for ind in ne.get('indicateurs', []):
                        for met in ind.get('metriques', []):
                            for op in met.get('operations', []):
                                if op.get('code_affichage'):
                                    found_codes.add(op['code_affichage'])

        assert 'CS1' in found_codes
        assert 'IP1' in found_codes
        assert 'CS2' in found_codes


# =============================================================================
# Verrou hors brouillon — DnD interdit sur plan validé / archivé
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestReorderEditableStatuses:
    """Vérifie que reorder n'accepte que `draft` ; un plan validé même
    étendu (#250) reste verrouillé en lecture seule."""

    def test_reorder_sur_plan_draft_autorise(self, api_client, plan_with_actions):
        api_client.force_authenticate(user=plan_with_actions['referent'])
        met = plan_with_actions['metrique']
        # Réordonne les 3 opérations rattachées à la métrique
        ids = [
            plan_with_actions['op_via_type'].pk,
            plan_with_actions['op_ip'].pk,
            plan_with_actions['op_cs'].pk,
        ]
        response = api_client.post(
            '/api/plans/operations/reorder/',
            {'parent_id': met.pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data

    def test_reorder_sur_plan_etendu_refuse(self, api_client, plan_with_actions):
        """#250 — Un plan validé ET étendu (annees_extension > 0) reste verrouillé.
        L'extension est un attribut indépendant du statut et ne débloque pas l'édition."""
        plan = plan_with_actions['plan']
        plan.statut = 'valide'
        plan.annees_extension = 2
        plan.save(update_fields=['statut', 'annees_extension'])
        api_client.force_authenticate(user=plan_with_actions['referent'])
        ids = [plan_with_actions['op_cs'].pk, plan_with_actions['op_ip'].pk]
        response = api_client.post(
            '/api/plans/operations/reorder/',
            {'parent_id': plan_with_actions['metrique'].pk, 'ordered_ids': ids},
            format='json',
        )
        # Plan validé = lecture seule, même étendu (#250 / #248)
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data

    def test_reorder_sur_plan_valide_refuse(self, api_client, plan_with_actions):
        plan = plan_with_actions['plan']
        plan.statut = 'valide'
        plan.save(update_fields=['statut'])
        api_client.force_authenticate(user=plan_with_actions['referent'])
        ids = [plan_with_actions['op_cs'].pk, plan_with_actions['op_ip'].pk]
        response = api_client.post(
            '/api/plans/operations/reorder/',
            {'parent_id': plan_with_actions['metrique'].pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data

    def test_reorder_sur_plan_archive_refuse(self, api_client, plan_with_actions):
        plan = plan_with_actions['plan']
        plan.statut = 'archive'
        plan.save(update_fields=['statut'])
        api_client.force_authenticate(user=plan_with_actions['referent'])
        ids = [plan_with_actions['op_cs'].pk]
        response = api_client.post(
            '/api/plans/operations/reorder/',
            {'parent_id': plan_with_actions['metrique'].pk, 'ordered_ids': ids},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.data
