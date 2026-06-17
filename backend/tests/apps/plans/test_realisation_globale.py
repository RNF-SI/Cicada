"""
#355 — Tests du niveau de réalisation GLOBAL d'une action (sur la période) :
calcul automatique sur les années programmées + surcharge manuelle hybride.
"""
import pytest

from apps.plans.models_operations import OperationRealisationGlobale, Operation
from tests.factories.enjeux import (
    OperationFactory,
    OperationAnneeFactory,
    RealisationOperationAnneeFactory,
    NomenclatureNiveauRealisationFactory,
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
