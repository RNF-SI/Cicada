"""
#355 — Tests du niveau de réalisation GLOBAL d'une action (sur la période) :
calcul automatique sur les années programmées + surcharge manuelle hybride.
"""
from datetime import date

import pytest

from apps.plans.models_operations import OperationRealisationGlobale, Operation
from tests.factories.enjeux import (
    OperationFactory,
    OperationAnneeFactory,
    RealisationOperationAnneeFactory,
    NomenclatureNiveauRealisationFactory,
    IndicateurFactory,
    MetriqueFactory,
    MesureFactory,
    NomenclatureTypeMetriqueFactory,
)
from tests.factories.users import (
    SuperAdminFactory,
    RoleFactory,
    CorRoleSiteFactory,
)


def _annee(op, annee, niveau_mnem=None, periodicite=True):
    """Crée une année programmée + sa réalisation éventuelle."""
    oa = OperationAnneeFactory(id_operation=op, annee=annee, periodicite=periodicite)
    if niveau_mnem is not None:
        RealisationOperationAnneeFactory(
            id_operation_annee=oa,
            id_niveau_realisation=NomenclatureNiveauRealisationFactory(mnemonique=niveau_mnem),
        )
    return oa


@pytest.mark.django_db
@pytest.mark.unit
class TestComputeNiveauRealisationGlobal:
    """Calcul automatique du statut global."""

    def test_toutes_annees_terminees(self):
        op = OperationFactory()
        _annee(op, 2024, 'TERMINE')
        _annee(op, 2025, 'TERMINE')
        _annee(op, 2026, 'TERMINE')
        assert op.compute_niveau_realisation_global() == 'TERMINE'

    def test_une_seule_annee_terminee_sur_trois_reste_en_cours(self):
        """Cœur du #355 : 1/3 réalisée ≠ Terminé au global."""
        op = OperationFactory()
        _annee(op, 2024, 'TERMINE')
        _annee(op, 2025, None)
        _annee(op, 2026, None)
        assert op.compute_niveau_realisation_global() == 'EN_COURS'

    def test_aucune_annee_programmee(self):
        op = OperationFactory()
        assert op.compute_niveau_realisation_global() is None

    def test_annees_sans_realisation(self):
        op = OperationFactory()
        _annee(op, 2024, None)
        _annee(op, 2025, None)
        assert op.compute_niveau_realisation_global() == 'NON_DEMARRE'

    def test_que_des_partiels(self):
        op = OperationFactory()
        _annee(op, 2024, 'PARTIEL')
        _annee(op, 2025, 'PARTIEL')
        assert op.compute_niveau_realisation_global() == 'PARTIEL'

    def test_que_des_abandonnes(self):
        op = OperationFactory()
        _annee(op, 2024, 'ABANDONNE')
        _annee(op, 2025, 'ABANDONNE')
        assert op.compute_niveau_realisation_global() == 'ABANDONNE'

    def test_que_des_non_realisees(self):
        # #379 — toutes les années programmées « non réalisée »
        op = OperationFactory()
        _annee(op, 2024, 'NON_REALISE')
        _annee(op, 2025, 'NON_REALISE')
        assert op.compute_niveau_realisation_global() == 'NON_REALISE'

    def test_terminee_et_non_realisee_reste_en_cours(self):
        op = OperationFactory()
        _annee(op, 2024, 'TERMINE')
        _annee(op, 2025, 'NON_REALISE')
        assert op.compute_niveau_realisation_global() == 'EN_COURS'


@pytest.mark.django_db
@pytest.mark.unit
class TestOverrideGlobal:
    """Surcharge manuelle hybride."""

    def test_override_prime_sur_le_calcul(self):
        op = OperationFactory()
        _annee(op, 2024, 'TERMINE')
        _annee(op, 2025, None)  # calcul → EN_COURS
        OperationRealisationGlobale.objects.create(
            id_operation=op,
            id_niveau_realisation=NomenclatureNiveauRealisationFactory('TERMINE'),
        )
        fresh = Operation.objects.get(pk=op.pk)
        assert fresh.get_niveau_realisation_global() == 'TERMINE'
        assert fresh.is_niveau_realisation_global_manuel() is True

    def test_pas_de_surcharge_par_defaut(self):
        op = OperationFactory()
        _annee(op, 2024, 'TERMINE')
        assert op.is_niveau_realisation_global_manuel() is False


@pytest.mark.django_db
@pytest.mark.integration
class TestGlobalRealisationEndpoint:
    """Endpoint POST/GET/DELETE de la surcharge global."""

    URL = '/api/plans/realisations/global-realisation/{op}/'

    def test_superadmin_pose_recupere_et_retire_la_surcharge(self, api_client):
        admin = SuperAdminFactory()
        op = OperationFactory()
        _annee(op, 2024, 'TERMINE')
        _annee(op, 2025, None)  # calcul → EN_COURS
        niveau = NomenclatureNiveauRealisationFactory('TERMINE')

        api_client.force_authenticate(admin)
        url = self.URL.format(op=op.id_operation)

        # POST — pose la surcharge
        r = api_client.post(url, {'id_niveau_realisation': niveau.pk}, format='json')
        assert r.status_code == 200
        assert r.data['niveau_realisation_global_mnemonique'] == 'TERMINE'
        assert r.data['niveau_realisation_global_manuel'] is True

        # GET — état effectif
        g = api_client.get(url)
        assert g.status_code == 200
        assert g.data['niveau_realisation_global_manuel'] is True

        # DELETE — retour au calcul automatique (EN_COURS)
        d = api_client.delete(url)
        assert d.status_code == 200
        assert d.data['niveau_realisation_global_manuel'] is False
        assert d.data['niveau_realisation_global_mnemonique'] == 'EN_COURS'

    def test_referent_non_gestionnaire_du_plan_refuse(self, api_client):
        # Utilisateur référent (passe IsReferent) mais pas gestionnaire de ce plan
        user = RoleFactory()
        CorRoleSiteFactory(id_role=user, referent=True, referent_valid=True)
        assert user.is_referent()

        op = OperationFactory()  # pas de plan rattaché → non gestionnaire
        niveau = NomenclatureNiveauRealisationFactory('TERMINE')

        api_client.force_authenticate(user)
        r = api_client.post(
            self.URL.format(op=op.id_operation),
            {'id_niveau_realisation': niveau.pk},
            format='json',
        )
        assert r.status_code == 403


@pytest.mark.django_db
@pytest.mark.integration
class TestIndicateurGlobalEndpoint:
    """#355 — Évaluation globale par indicateur (tableau de bord)."""

    def _metrique_avec_seuils(self, ind):
        return MetriqueFactory(
            id_indicateur=ind,
            # Type figé sur NUMERIQUE : la NomenclatureTypeMetriqueFactory cycle
            # via un factory.Iterator (NUMERIQUE/CHIFFRE/TEXTE), donc sans épinglage
            # le type dépend de l'ordre d'exécution des tests et les seuils
            # numériques ci-dessous seraient ignorés (score None) selon l'ordre.
            type_metrique=NomenclatureTypeMetriqueFactory(mnemonique='NUMERIQUE'),
            score_1_inf=0, score_1_sup=20,
            score_2_inf=20, score_2_sup=40,
            score_3_inf=40, score_3_sup=60,
            score_4_inf=60, score_4_sup=80,
            score_5_inf=80, score_5_sup=100,
        )

    def test_etat_courant_moyenne_et_tendance(self, api_client):
        admin = SuperAdminFactory()
        ind = IndicateurFactory()
        met = self._metrique_avec_seuils(ind)
        MesureFactory(id_metrique=met, valeur='50', date_mesure=date(2024, 6, 1))  # score 3
        MesureFactory(id_metrique=met, valeur='90', date_mesure=date(2025, 6, 1))  # score 5

        api_client.force_authenticate(admin)
        r = api_client.get(f'/api/plans/indicateurs/{ind.id_indicateur}/global/')

        assert r.status_code == 200
        assert r.data['etat_courant_score'] == 5.0       # dernière année = 2025
        assert r.data['moyenne_score'] == 4.0            # (3 + 5) / 2
        assert r.data['tendance'] == 'hausse'            # 3 → 5
        m0 = r.data['metriques'][0]
        assert m0['etat_courant'] == {'annee': 2025, 'score': 5}
        assert len(m0['series']) == 2

    def test_sans_mesure(self, api_client):
        admin = SuperAdminFactory()
        ind = IndicateurFactory()
        self._metrique_avec_seuils(ind)

        api_client.force_authenticate(admin)
        r = api_client.get(f'/api/plans/indicateurs/{ind.id_indicateur}/global/')

        assert r.status_code == 200
        assert r.data['etat_courant_score'] is None
        assert r.data['moyenne_score'] is None
        assert r.data['serie'] == []


@pytest.mark.django_db
@pytest.mark.integration
class TestIndicateurGlobalEvaluationOverride:
    """#356 — Surcharge manuelle de l'évaluation globale d'un indicateur."""

    URL = '/api/plans/indicateur-mesures/global-evaluation/{ind}/'

    def _metrique_avec_seuils(self, ind):
        return MetriqueFactory(
            id_indicateur=ind,
            # Type figé sur NUMERIQUE : la NomenclatureTypeMetriqueFactory cycle
            # via un factory.Iterator (NUMERIQUE/CHIFFRE/TEXTE), donc sans épinglage
            # le type dépend de l'ordre d'exécution des tests et les seuils
            # numériques ci-dessous seraient ignorés (score None) selon l'ordre.
            type_metrique=NomenclatureTypeMetriqueFactory(mnemonique='NUMERIQUE'),
            score_1_inf=0, score_1_sup=20,
            score_2_inf=20, score_2_sup=40,
            score_3_inf=40, score_3_sup=60,
            score_4_inf=60, score_4_sup=80,
            score_5_inf=80, score_5_sup=100,
        )

    def test_superadmin_pose_recupere_et_retire_la_surcharge(self, api_client):
        admin = SuperAdminFactory()
        ind = IndicateurFactory()
        met = self._metrique_avec_seuils(ind)
        MesureFactory(id_metrique=met, valeur='50', date_mesure=date(2024, 6, 1))  # score 3

        api_client.force_authenticate(admin)
        url = self.URL.format(ind=ind.id_indicateur)

        # POST — pose une icône d'évaluation forcée (++ = 5)
        r = api_client.post(url, {'score_override': 5}, format='json')
        assert r.status_code == 200
        assert r.data['score_override'] == 5
        assert r.data['manuel'] is True

        # GET indicateurs/{id}/global/ — l'icône effective suit la surcharge,
        # mais le score calculé (moyenne) ne change pas.
        g = api_client.get(f'/api/plans/indicateurs/{ind.id_indicateur}/global/')
        assert g.data['etat_courant_effectif'] == 5
        assert g.data['moyenne_score'] == 3.0
        assert g.data['manuel'] is True

        # DELETE — retour au calcul automatique
        d = api_client.delete(url)
        assert d.status_code == 200
        assert d.data['manuel'] is False
        assert d.data['score_override'] is None

    def test_commentaire_seul_n_active_pas_le_mode_manuel(self, api_client):
        admin = SuperAdminFactory()
        ind = IndicateurFactory()

        api_client.force_authenticate(admin)
        url = self.URL.format(ind=ind.id_indicateur)

        r = api_client.post(url, {'commentaire_override': 'Note libre'}, format='json')
        assert r.status_code == 200
        assert r.data['manuel'] is False
        assert r.data['score_override'] is None
        assert r.data['commentaire'] == 'Note libre'

    def test_post_vide_refuse(self, api_client):
        admin = SuperAdminFactory()
        ind = IndicateurFactory()
        api_client.force_authenticate(admin)
        r = api_client.post(self.URL.format(ind=ind.id_indicateur), {}, format='json')
        assert r.status_code == 400

    def test_referent_non_gestionnaire_du_plan_refuse(self, api_client):
        user = RoleFactory()
        CorRoleSiteFactory(id_role=user, referent=True, referent_valid=True)
        assert user.is_referent()

        ind = IndicateurFactory()  # pas de plan rattaché → non gestionnaire
        api_client.force_authenticate(user)
        r = api_client.post(
            self.URL.format(ind=ind.id_indicateur),
            {'score_override': 4},
            format='json',
        )
        assert r.status_code == 403


@pytest.mark.django_db
@pytest.mark.integration
class TestOperationGlobalCommentaireSeul:
    """#356 — Commentaire global d'une action, indépendant du forçage de statut."""

    URL = '/api/plans/realisations/global-realisation/{op}/'

    def test_commentaire_seul_n_active_pas_le_mode_manuel(self, api_client):
        admin = SuperAdminFactory()
        op = OperationFactory()
        _annee(op, 2024, 'TERMINE')  # calcul → TERMINE

        api_client.force_authenticate(admin)
        url = self.URL.format(op=op.id_operation)

        r = api_client.post(url, {'commentaire_override': 'RAS'}, format='json')
        assert r.status_code == 200
        # Niveau toujours calculé (pas de surcharge de statut), mais commentaire posé
        assert r.data['niveau_realisation_global_manuel'] is False
        assert r.data['niveau_realisation_global_mnemonique'] == 'TERMINE'
        assert r.data['niveau_realisation_global_commentaire'] == 'RAS'
