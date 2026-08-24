"""
Tests de l'API publique des métadonnées des plans de gestion (#645).

Ce que ces tests protègent, et qui n'est visible nulle part ailleurs :
- l'endpoint reste **fermé** tant que la structure ne l'a pas ouvert ;
- une fois ouvert, il ne demande **aucune** authentification ;
- il n'expose **que** des métadonnées, et **jamais** un brouillon ;
- la référence transmise à la GED est stable et porte l'instance d'origine.
"""
import uuid as uuid_lib

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import SiteConfiguration
from tests.factories.plans import (
    PlanGestionFactory, PlanGestionValideFactory, PlanGestionArchiveFactory,
    CorSitePgFactory,
)
from tests.factories.users import SiteFactory

URL_LISTE = '/api/public/plans/'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api_ouverte(db):
    """L'instance a ouvert son API publique."""
    config = SiteConfiguration.get_instance()
    config.api_publique_plans = True
    config.save()
    return config


@pytest.fixture
def api_fermee(db):
    config = SiteConfiguration.get_instance()
    config.api_publique_plans = False
    config.save()
    return config


@pytest.mark.django_db
@pytest.mark.integration
class TestInterrupteurApiPublique:
    """L'ouverture est une décision de la structure, pas un défaut."""

    def test_fermee_par_defaut(self, api_client, db):
        SiteConfiguration.get_instance()
        assert SiteConfiguration.get_instance().api_publique_plans is False
        assert api_client.get(URL_LISTE).status_code == status.HTTP_404_NOT_FOUND

    def test_liste_refusee_quand_coupee(self, api_client, api_fermee):
        PlanGestionValideFactory()
        assert api_client.get(URL_LISTE).status_code == status.HTTP_404_NOT_FOUND

    def test_detail_refuse_quand_coupee(self, api_client, api_fermee):
        plan = PlanGestionValideFactory()
        reponse = api_client.get(f'{URL_LISTE}{plan.uuid_plan}/')
        assert reponse.status_code == status.HTTP_404_NOT_FOUND

    def test_ouverte_sans_authentification(self, api_client, api_ouverte):
        PlanGestionValideFactory()
        reponse = api_client.get(URL_LISTE)
        assert reponse.status_code == status.HTTP_200_OK
        assert reponse.data['count'] == 1


@pytest.mark.django_db
@pytest.mark.integration
class TestIdentifiantStable:
    """L'identifiant est ce que la GED conserve : il ne doit pas bouger."""

    def test_uuid_unique_par_plan(self, db):
        premier = PlanGestionValideFactory()
        second = PlanGestionValideFactory()
        assert premier.uuid_plan != second.uuid_plan

    def test_reference_prefixee_par_instance(self, db, settings):
        settings.CICADA_INSTANCE_ID = 'cen'
        plan = PlanGestionValideFactory()
        assert plan.reference == f'cicada:cen:{plan.uuid_plan}'

    def test_uuid_survit_au_renommage(self, db):
        """Le slug suit le nom ; l'identifiant transmis à la GED, non."""
        plan = PlanGestionValideFactory(nom='Plan avant renommage')
        uuid_initial = plan.uuid_plan
        plan.nom = 'Plan après renommage'
        plan.slug = ''
        plan.save()
        plan.refresh_from_db()
        assert plan.uuid_plan == uuid_initial

    def test_detail_par_uuid(self, api_client, api_ouverte, settings):
        settings.CICADA_INSTANCE_ID = 'cen'
        plan = PlanGestionValideFactory()
        reponse = api_client.get(f'{URL_LISTE}{plan.uuid_plan}/')
        assert reponse.status_code == status.HTTP_200_OK
        assert reponse.data['uuid'] == str(plan.uuid_plan)
        assert reponse.data['reference'] == f'cicada:cen:{plan.uuid_plan}'
        assert reponse.data['instance_id'] == 'cen'

    def test_une_nouvelle_version_recoit_son_propre_identifiant(self, db):
        """
        Une version dérivée est un autre document pour une GED.

        `PlanDuplicationService._dup` recopie tous les champs concrets, UUID
        compris : sans tirage explicite, l'INSERT violerait l'unicité — et s'il
        passait, la nouvelle version écraserait la précédente côté GED.
        """
        from apps.plans.services import PlanDuplicationService
        from tests.factories.users import RoleFactory

        source = PlanGestionValideFactory()
        auteur = RoleFactory()
        nouvelle = PlanDuplicationService.build_version_plan(
            source, auteur, nom='Version dérivée',
        )
        nouvelle.save()
        assert nouvelle.uuid_plan != source.uuid_plan
        assert nouvelle.reference != source.reference

    def test_uuid_inconnu_donne_404(self, api_client, api_ouverte):
        reponse = api_client.get(f'{URL_LISTE}{uuid_lib.uuid4()}/')
        assert reponse.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.integration
class TestPerimetreExpose:
    """Ni brouillon, ni contenu de plan."""

    def test_brouillons_exclus(self, api_client, api_ouverte):
        PlanGestionFactory(nom='Brouillon en cours')
        valide = PlanGestionValideFactory(nom='Plan publié')
        reponse = api_client.get(URL_LISTE)
        noms = [plan['nom'] for plan in reponse.data['results']]
        assert noms == ['Plan publié']
        assert reponse.data['results'][0]['uuid'] == str(valide.uuid_plan)

    def test_brouillon_inaccessible_en_detail(self, api_client, api_ouverte):
        brouillon = PlanGestionFactory()
        reponse = api_client.get(f'{URL_LISTE}{brouillon.uuid_plan}/')
        assert reponse.status_code == status.HTTP_404_NOT_FOUND

    def test_archives_exposes(self, api_client, api_ouverte):
        PlanGestionArchiveFactory(nom='Plan terminé')
        reponse = api_client.get(URL_LISTE)
        assert [p['nom'] for p in reponse.data['results']] == ['Plan terminé']

    def test_aucun_contenu_de_plan(self, api_client, api_ouverte):
        """Une GED documente des documents : elle n'a pas besoin de leur substance."""
        PlanGestionValideFactory()
        fiche = api_client.get(URL_LISTE).data['results'][0]
        interdits = {
            'enjeux', 'objectifs', 'indicateurs', 'operations', 'actions',
            'budget', 'postes', 'realisations', 'mesures', 'suivis',
        }
        assert interdits.isdisjoint(fiche.keys())

    def test_metadonnees_du_formulaire_de_creation(self, api_client, api_ouverte):
        plan = PlanGestionValideFactory(
            nom='Plan métadonnées',
            rang=2,
            annee_debut=2020,
            annee_fin=2030,
            ct88=True,
            redacteurs='Bureau d\'études Alpha',
            relecteurs='CSRPN',
            id_docgestion_fcen='DG-42',
        )
        fiche = api_client.get(f'{URL_LISTE}{plan.uuid_plan}/').data
        assert fiche['nom'] == 'Plan métadonnées'
        assert fiche['rang'] == 2
        assert fiche['annee_debut'] == 2020
        assert fiche['annee_fin'] == 2030
        assert fiche['ct88'] is True
        assert fiche['redacteurs'] == "Bureau d'études Alpha"
        assert fiche['relecteurs'] == 'CSRPN'
        assert fiche['id_docgestion_fcen'] == 'DG-42'
        assert fiche['statut'] == 'valide'
        assert fiche['date_modification'] is not None

    def test_sites_exposes_par_code_inpn(self, api_client, api_ouverte):
        """Seul identifiant national d'un site — la clé de rapprochement d'une GED."""
        site = SiteFactory(nom_site='Réserve du Test', id_inpn='FR3800001')
        plan = PlanGestionValideFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site, rang=1)
        fiche = api_client.get(f'{URL_LISTE}{plan.uuid_plan}/').data
        assert len(fiche['sites']) == 1
        assert fiche['sites'][0]['id_inpn'] == 'FR3800001'
        assert fiche['sites'][0]['nom'] == 'Réserve du Test'


@pytest.mark.django_db
@pytest.mark.integration
class TestFiltres:
    """Le rattrapage incrémental est la raison d'être de cette API."""

    def test_modifie_depuis_ecarte_les_plans_anterieurs(self, api_client, api_ouverte):
        from django.utils import timezone
        ancien = PlanGestionValideFactory(nom='Ancien')
        PlanGestion = type(ancien)
        PlanGestion.objects.filter(pk=ancien.pk).update(
            date_maj=timezone.now() - timezone.timedelta(days=30)
        )
        PlanGestionValideFactory(nom='Récent')

        borne = (timezone.now() - timezone.timedelta(days=1)).isoformat()
        reponse = api_client.get(URL_LISTE, {'modifie_depuis': borne})
        assert [p['nom'] for p in reponse.data['results']] == ['Récent']

    def test_modifie_depuis_accepte_une_date_seule(self, api_client, api_ouverte):
        PlanGestionValideFactory(nom='Plan du jour')
        reponse = api_client.get(URL_LISTE, {'modifie_depuis': '2000-01-01'})
        assert reponse.status_code == status.HTTP_200_OK
        assert reponse.data['count'] == 1

    def test_modifie_depuis_illisible_donne_400(self, api_client, api_ouverte):
        reponse = api_client.get(URL_LISTE, {'modifie_depuis': 'avant-hier'})
        assert reponse.status_code == status.HTTP_400_BAD_REQUEST

    def test_filtre_statut(self, api_client, api_ouverte):
        PlanGestionValideFactory(nom='Validé')
        PlanGestionArchiveFactory(nom='Archivé')
        reponse = api_client.get(URL_LISTE, {'statut': 'archive'})
        assert [p['nom'] for p in reponse.data['results']] == ['Archivé']

    def test_filtre_statut_brouillon_refuse(self, api_client, api_ouverte):
        """Le brouillon n'est pas « filtrable » : il n'est pas exposé du tout."""
        reponse = api_client.get(URL_LISTE, {'statut': 'draft'})
        assert reponse.status_code == status.HTTP_400_BAD_REQUEST

    def test_filtre_id_inpn(self, api_client, api_ouverte):
        site = SiteFactory(id_inpn='FR9999999')
        attendu = PlanGestionValideFactory(nom='Plan du site')
        CorSitePgFactory(plan_de_gestion=attendu, site=site, rang=1)
        PlanGestionValideFactory(nom='Plan d\'ailleurs')
        reponse = api_client.get(URL_LISTE, {'id_inpn': 'FR9999999'})
        assert [p['nom'] for p in reponse.data['results']] == ['Plan du site']

    def test_ordre_croissant_par_date_de_modification(self, api_client, api_ouverte):
        """Un rattrapage qui pagine ne doit jamais manquer un plan modifié en route."""
        from django.utils import timezone
        premier = PlanGestionValideFactory(nom='Premier')
        second = PlanGestionValideFactory(nom='Second')
        PlanGestion = type(premier)
        PlanGestion.objects.filter(pk=premier.pk).update(
            date_maj=timezone.now() - timezone.timedelta(days=2)
        )
        PlanGestion.objects.filter(pk=second.pk).update(
            date_maj=timezone.now() - timezone.timedelta(days=1)
        )
        reponse = api_client.get(URL_LISTE)
        assert [p['nom'] for p in reponse.data['results']] == ['Premier', 'Second']


@pytest.mark.django_db
@pytest.mark.integration
class TestLectureSeule:
    """Aucune écriture, quelle que soit la méthode."""

    @pytest.mark.parametrize('methode', ['post', 'put', 'patch', 'delete'])
    def test_ecritures_refusees(self, api_client, api_ouverte, methode):
        plan = PlanGestionValideFactory()
        cible = URL_LISTE if methode == 'post' else f'{URL_LISTE}{plan.uuid_plan}/'
        reponse = getattr(api_client, methode)(cible, {}, format='json')
        assert reponse.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
