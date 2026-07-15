"""
Tests d'intégration pour l'API RH des plans de gestion (#560) :
référentiel de fonctions, personnes du PG et lignes de temps de travail.
"""
import pytest
from rest_framework.test import APIClient

from apps.plans.models_operations import (
    Fonction,
    OperationAnneeRH,
    PersonnePlan,
    RealisationOperationAnnee,
    RealisationOperationAnneeRH,
)
from tests.factories.users import SuperAdminFactory
from tests.factories.plans import PlanGestionFactory
from tests.factories.enjeux import (
    OperationAnneeFactory,
    OperationFactory,
    SuiviInventaireFactory,
)


@pytest.fixture
def admin_client():
    client = APIClient()
    client.force_authenticate(SuperAdminFactory())
    return client


@pytest.mark.django_db
@pytest.mark.integration
class TestFonctionEndpoint:
    """Référentiel global des fonctions/postes."""

    def test_socle_seede(self, admin_client):
        r = admin_client.get('/api/plans/fonctions/')
        assert r.status_code == 200
        data = r.json()
        libelles = [f['libelle'] for f in data]
        assert 'Conservateur' in libelles
        # Au moins une fonction non financée par défaut (écovolontaire, bénévole…)
        assert any(f['finance_par_defaut'] is False for f in data)
        assert all(f['is_socle'] for f in data)

    def test_create_a_la_volee(self, admin_client):
        r = admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': 'Poste inédit', 'finance_par_defaut': False},
            format='json',
        )
        assert r.status_code == 201
        assert r.json()['finance_par_defaut'] is False
        assert r.json()['is_socle'] is False

    def test_create_dedup_insensible_casse(self, admin_client):
        admin_client.post('/api/plans/fonctions/', {'libelle': 'Ranger'}, format='json')
        admin_client.post('/api/plans/fonctions/', {'libelle': 'ranger'}, format='json')
        assert Fonction.objects.filter(libelle__iexact='ranger').count() == 1

    def test_suppression_socle_interdite(self, admin_client):
        fonction = Fonction.objects.filter(is_socle=True).first()
        r = admin_client.delete(f'/api/plans/fonctions/{fonction.id_fonction}/')
        assert r.status_code == 400
        assert Fonction.objects.filter(pk=fonction.pk).exists()


@pytest.mark.django_db
@pytest.mark.integration
class TestPersonnePlanEndpoint:
    """Personnes rattachées à un plan de gestion, avec leurs fonctions."""

    def test_create_avec_fonctions(self, admin_client):
        plan = PlanGestionFactory()
        fonction = Fonction.objects.get(libelle='Conservateur')
        payload = {
            'id_pg': plan.id_pg,
            'nom': 'Marie Dupont',
            'fonctions': [{'id_fonction': fonction.id_fonction, 'pourcentage': '50.00'}],
        }
        r = admin_client.post('/api/plans/personnes/', payload, format='json')
        assert r.status_code == 201, r.content
        body = r.json()
        assert body['nom'] == 'Marie Dupont'
        assert len(body['fonctions']) == 1
        assert body['fonctions'][0]['fonction_libelle'] == 'Conservateur'
        assert body['fonctions'][0]['pourcentage'] == '50.00'

    def test_by_plan(self, admin_client):
        plan = PlanGestionFactory()
        PersonnePlan.objects.create(id_pg=plan, nom='Alice')
        autre = PlanGestionFactory()
        PersonnePlan.objects.create(id_pg=autre, nom='Bob')
        r = admin_client.get(f'/api/plans/personnes/by-plan/{plan.id_pg}/')
        assert r.status_code == 200
        noms = [p['nom'] for p in r.json()]
        assert noms == ['Alice']

    def test_update_remplace_fonctions(self, admin_client):
        plan = PlanGestionFactory()
        personne = PersonnePlan.objects.create(id_pg=plan, nom='Yann')
        fonction = Fonction.objects.get(libelle='Garde')
        r = admin_client.patch(
            f'/api/plans/personnes/{personne.id_personne_plan}/',
            {'fonctions': [{'id_fonction': fonction.id_fonction}]},
            format='json',
        )
        assert r.status_code == 200
        assert personne.fonctions.count() == 1
        assert personne.fonctions.first().id_fonction.libelle == 'Garde'


@pytest.mark.django_db
@pytest.mark.integration
class TestRealisationRhLignes:
    """
    Saisie du temps de travail *réalisé* (page suivi) : lignes RH portées par
    la réalisation annuelle, en sémantique « replace-all ».
    """

    @pytest.fixture
    def operation_annee(self):
        """
        OperationAnnee rattachée à un plan : `Operation.get_plan_de_gestion()`
        remonte via le suivi (id_suivi → id_pg), le chemin le plus court.
        """
        plan = PlanGestionFactory()
        suivi = SuiviInventaireFactory(id_pg=plan)
        return OperationAnneeFactory(id_operation=OperationFactory(id_suivi=suivi))

    def _upsert(self, client, oa, rh_lignes):
        return client.post(
            '/api/plans/realisations/upsert/',
            {'id_operation_annee': oa.id_operation_annee, 'rh_lignes': rh_lignes},
            format='json',
        )

    def test_upsert_cree_les_lignes(self, admin_client, operation_annee):
        oa = operation_annee
        personne = PersonnePlan.objects.create(
            id_pg=oa.id_operation.get_plan_de_gestion(), nom='Camille',
        )
        benevole = Fonction.objects.get(libelle='Bénévole')
        r = self._upsert(admin_client, oa, [
            {'id_personne_plan': personne.id_personne_plan, 'jours': '6.50', 'finance': True},
            {'id_fonction': benevole.id_fonction, 'jours': '2.00', 'finance': False},
        ])
        assert r.status_code == 200, r.content
        lignes = r.json()['rh_lignes']
        assert len(lignes) == 2
        realisation = RealisationOperationAnnee.objects.get(id_operation_annee=oa)
        assert realisation.rh_lignes.count() == 2
        non_finance = realisation.rh_lignes.get(finance=False)
        assert non_finance.id_fonction_id == benevole.id_fonction

    def test_upsert_remplace_les_lignes(self, admin_client, operation_annee):
        oa = operation_annee
        realisation = RealisationOperationAnnee.objects.create(id_operation_annee=oa)
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=realisation, jours=3, finance=True,
        )
        r = self._upsert(admin_client, oa, [{'jours': '9.00', 'finance': True}])
        assert r.status_code == 200, r.content
        assert realisation.rh_lignes.count() == 1
        assert float(realisation.rh_lignes.first().jours) == 9.0

    def test_upsert_liste_vide_efface_les_lignes(self, admin_client, operation_annee):
        oa = operation_annee
        realisation = RealisationOperationAnnee.objects.create(id_operation_annee=oa)
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=realisation, jours=3, finance=True,
        )
        r = self._upsert(admin_client, oa, [])
        assert r.status_code == 200, r.content
        assert realisation.rh_lignes.count() == 0

    def test_ligne_sans_personne_ni_fonction_acceptee(self, admin_client, operation_annee):
        """
        « Temps non affecté » : c'est l'état des saisies converties depuis
        l'ancien champ `etp` par la migration 0100. Le couple doit rester
        facultatif, sinon ces lignes seraient perdues au premier ré-enregistrement.
        """
        oa = operation_annee
        r = self._upsert(admin_client, oa, [{'jours': '4.00', 'finance': True}])
        assert r.status_code == 200, r.content
        ligne = RealisationOperationAnnee.objects.get(
            id_operation_annee=oa,
        ).rh_lignes.first()
        assert ligne.id_personne_plan_id is None
        assert ligne.id_fonction_id is None
        assert float(ligne.jours) == 4.0

    def test_duplication_copie_personnes_et_lignes_rh(self, operation_annee):
        """
        #377 + #560 — une nouvelle version doit emporter les personnes du PG et
        le temps de travail prévisionnel, remappés vers ses propres copies :
        sans cela le prévisionnel RH serait silencieusement perdu, et les
        lignes copiées pointeraient sur les personnes de la version source.
        """
        from apps.plans.services import PlanDuplicationService

        oa = operation_annee
        source = oa.id_operation.get_plan_de_gestion()
        personne = PersonnePlan.objects.create(id_pg=source, nom='Camille')
        conservateur = Fonction.objects.get(libelle='Conservateur')
        personne.fonctions.create(id_fonction=conservateur, pourcentage=80)
        OperationAnneeRH.objects.create(
            id_operation_annee=oa, id_personne_plan=personne, jours=9, finance=True,
        )

        cible = PlanGestionFactory()
        PlanDuplicationService.copy_content(source, cible, SuperAdminFactory())

        # Personne copiée (nouvelle instance) + ses fonctions.
        copies = PersonnePlan.objects.filter(id_pg=cible)
        assert [p.nom for p in copies] == ['Camille']
        copie = copies.first()
        assert copie.id_personne_plan != personne.id_personne_plan
        assert copie.fonctions.first().id_fonction_id == conservateur.id_fonction

        # Ligne RH copiée et repointée vers la personne du NOUVEAU plan.
        lignes = OperationAnneeRH.objects.filter(
            id_operation_annee__id_operation__id_suivi__id_pg=cible,
        )
        assert lignes.count() == 1
        assert float(lignes.first().jours) == 9.0
        assert lignes.first().id_personne_plan_id == copie.id_personne_plan

        # La version source reste intacte.
        assert PersonnePlan.objects.filter(id_pg=source).count() == 1
        assert OperationAnneeRH.objects.filter(id_operation_annee=oa).count() == 1

    def test_bilan_ventile_finance_et_non_finance(self, admin_client, operation_annee):
        """Le bilan doit valoriser séparément le temps non financé (#560)."""
        oa = operation_annee
        plan = oa.id_operation.get_plan_de_gestion()
        OperationAnneeRH.objects.create(id_operation_annee=oa, jours=10, finance=True)
        OperationAnneeRH.objects.create(id_operation_annee=oa, jours=4, finance=False)
        realisation = RealisationOperationAnnee.objects.create(id_operation_annee=oa)
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=realisation, jours=8, finance=True,
        )
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=realisation, jours=3, finance=False,
        )
        r = admin_client.get(f'/api/plans/realisations/bilan/{plan.id_pg}/')
        assert r.status_code == 200, r.content
        rh = r.json()['rh']
        assert rh['previsionnel_finance'] == 10
        assert rh['previsionnel_non_finance'] == 4
        assert rh['realise_finance'] == 8
        assert rh['realise_non_finance'] == 3
        assert rh['previsionnel'] == 14
        assert rh['realise'] == 11
