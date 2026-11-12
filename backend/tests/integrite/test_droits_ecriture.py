"""Filet « perte de données » — famille F : qui peut écrire où.

Règle : écrire dans un plan (contenu, documents, postes, financeurs, réglages)
est réservé à ses **référents** et à ses **gestionnaires** (admin d'un
organisme gestionnaire d'un de ses sites, rédacteur principal, super admin).
Être référent d'un autre plan ou d'un site, être membre, être d'un autre
organisme ne donne que la lecture. Le plan d'arrivée d'un objet déplacé ou
relié suit la même règle, et le verrou « brouillon seulement » (#248).

Chaque refus laisse l'inventaire intact.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.plans.models import PlanGestion
from apps.plans.models_enjeux import Enjeu
from apps.users.models import CorOgSite
from apps.plans.models_operations import Fonction
from tests.factories.enjeux import EnjeuFactory, NomenclatureEnjeuFactory
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import (
    AdminOrganismeFactory, CorOgSiteFactory, CorRoleSiteFactory, OrganismeFactory, RoleFactory,
    SiteFactory, SuperAdminFactory,
)
from tests.integrite.socle import ecarts, inventaire

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

AUTORISES = ('super_admin', 'redacteur_principal', 'admin_og_gestionnaire', 'referent_du_plan')
REFUSES = ('admin_og_autre_organisme', 'referent_d_un_autre_plan', 'membre_du_site',
           'redacteur_externe_non_rattache', 'utilisateur_autre_organisme')


class Monde:
    """Deux organismes, deux sites, un brouillon de A, un plan validé de B."""

    def __init__(self):
        self.org_a, self.org_b = OrganismeFactory(), OrganismeFactory()
        self.site_a, self.site_b = SiteFactory(), SiteFactory()
        CorOgSiteFactory(id_site=self.site_a, uuid_og=self.org_a, principal=True)
        CorOgSiteFactory(id_site=self.site_b, uuid_og=self.org_b, principal=True)
        self.referent = RoleFactory(id_organisme=self.org_a)
        self.plan = PlanGestionFactory(statut='draft', sites=[self.site_a], referents=[self.referent])
        self.enjeu = EnjeuFactory(id_pg=self.plan, libelle='Enjeu de A')
        self.plan_b = PlanGestionFactory(statut='valide', sites=[self.site_b])
        self.enjeu_b = EnjeuFactory(id_pg=self.plan_b)
        self.categorie = NomenclatureEnjeuFactory()
        self.fonction = Fonction.objects.create(libelle='Garde technicien')

    def utilisateur(self, profil):
        if profil == 'super_admin':
            return SuperAdminFactory()
        if profil == 'redacteur_principal':
            return RoleFactory(role_level='redacteur_principal')
        if profil == 'admin_og_gestionnaire':
            return AdminOrganismeFactory(id_organisme=self.org_a)
        if profil == 'admin_og_autre_organisme':
            return AdminOrganismeFactory(id_organisme=self.org_b)
        if profil == 'referent_du_plan':
            return self.referent
        if profil == 'referent_d_un_autre_plan':
            # Lit le plan (membre du site) et est référent… d'un autre plan.
            user = RoleFactory(id_organisme=self.org_a)
            CorRoleSiteFactory(id_role=user, id_site=self.site_a)
            PlanGestionFactory(statut='draft', sites=[self.site_a], referents=[user])
            return user
        if profil == 'membre_du_site':
            user = RoleFactory(id_organisme=self.org_a)
            CorRoleSiteFactory(id_role=user, id_site=self.site_a)
            return user
        if profil == 'redacteur_externe_non_rattache':
            return RoleFactory(role_level='redacteur', id_organisme=OrganismeFactory())
        if profil == 'utilisateur_autre_organisme':
            return RoleFactory(id_organisme=self.org_b)
        raise ValueError(profil)

    def client(self, profil):
        client = APIClient()
        client.force_authenticate(self.utilisateur(profil))
        return client


@pytest.fixture
def monde():
    return Monde()


GESTES = {
    'modifier le plan': lambda m, c: c.patch(
        f'/api/plans/plans/{m.plan.pk}/', {'commentaire': 'modifié'}, format='json'),
    "modifier un enjeu": lambda m, c: c.patch(
        f'/api/plans/enjeux/{m.enjeu.pk}/', {'libelle': 'Renommé'}, format='json'),
    'créer un enjeu': lambda m, c: c.post(
        '/api/plans/enjeux/',
        {'id_pg': m.plan.pk, 'libelle': 'Nouveau', 'id_categorie': m.categorie.pk}, format='json'),
    'vider par import « remplacer »': lambda m, c: c.post(
        f'/api/plans/plans/{m.plan.pk}/import-arborescence/import-data/',
        {'mode': 'replace', 'data': {}}, format='json'),
    'créer un poste': lambda m, c: c.post(
        '/api/plans/postes/', {
            'id_pg': m.plan.pk, 'nom_local': 'Garde',
            'fonctions': [{'id_fonction': m.fonction.pk}]}, format='json'),
    'créer un financeur': lambda m, c: c.post(
        '/api/plans/financeurs/', {'id_pg': m.plan.pk, 'nom': 'Région'}, format='json'),
    'déposer un document': lambda m, c: c.post(
        '/api/plans/fichiers/', {
            'plan_de_gestion': m.plan.pk, 'type_fichier': 'document', 'nom_fichier': 'note.pdf',
            'fichier': SimpleUploadedFile('note.pdf', b'%PDF-1.4', content_type='application/pdf'),
        }, format='multipart'),
    'supprimer le plan': lambda m, c: c.delete(f'/api/plans/plans/{m.plan.pk}/'),
}


@pytest.mark.parametrize('geste', list(GESTES))
@pytest.mark.parametrize('profil', REFUSES)
def test_un_simple_lecteur_n_ecrit_pas(monde, profil, geste):
    client = monde.client(profil)
    avant = inventaire()
    reponse = GESTES[geste](monde, client)
    assert reponse.status_code in (403, 404), (profil, geste, reponse.status_code, reponse.content[:300])
    assert not ecarts(avant, inventaire()), (profil, geste)


@pytest.mark.parametrize('geste', [g for g in GESTES if g != 'supprimer le plan'])
@pytest.mark.parametrize('profil', AUTORISES)
def test_qui_a_la_main_sur_le_plan_ecrit(monde, profil, geste):
    reponse = GESTES[geste](monde, monde.client(profil))
    assert 200 <= reponse.status_code < 300, (profil, geste, reponse.status_code, reponse.content[:300])


class TestPlanDArrivee:
    def test_deplacer_un_enjeu_vers_le_plan_valide_d_un_autre_organisme(self, monde):
        client = monde.client('referent_du_plan')
        avant = inventaire()
        reponse = client.patch(
            f'/api/plans/enjeux/{monde.enjeu.pk}/', {'id_pg': monde.plan_b.pk}, format='json')
        assert reponse.status_code == 403, reponse.content[:300]
        assert not ecarts(avant, inventaire())
        assert Enjeu.objects.get(pk=monde.enjeu.pk).id_pg_id == monde.plan.pk

    def test_creer_sous_le_parent_d_un_plan_ou_l_on_n_ecrit_pas(self, monde):
        """Un référent de A ne crée rien dans un brouillon de B."""
        brouillon_b = PlanGestionFactory(statut='draft', sites=[monde.site_b])
        client = monde.client('referent_du_plan')
        reponse = client.post(
            '/api/plans/enjeux/', {'id_pg': brouillon_b.pk, 'libelle': 'Intrus'}, format='json')
        assert reponse.status_code == 403, reponse.content[:300]
        assert not Enjeu.objects.filter(id_pg=brouillon_b, libelle='Intrus').exists()


class TestCycleDeVie:
    def test_le_statut_ne_change_pas_par_un_patch_du_plan(self, monde):
        reponse = monde.client('referent_du_plan').patch(
            f'/api/plans/plans/{monde.plan.pk}/',
            {'statut': 'valide', 'en_revision': True, 'annees_extension': 2}, format='json')
        assert reponse.status_code == 200, reponse.content[:300]
        plan = PlanGestion.objects.get(pk=monde.plan.pk)
        assert (plan.statut, plan.en_revision, plan.annees_extension) == ('draft', False, 0)

    def test_un_lecteur_ne_s_ajoute_pas_aux_referents(self, monde):
        lecteur = monde.utilisateur('referent_d_un_autre_plan')
        client = APIClient()
        client.force_authenticate(lecteur)
        reponse = client.patch(
            f'/api/plans/plans/{monde.plan.pk}/', {'referents_ids': [lecteur.pk]}, format='json')
        assert reponse.status_code == 403, reponse.content[:300]
        assert not monde.plan.referents.filter(pk=lecteur.pk).exists()

    def test_dupliquer_pour_exporter_est_refuse_a_un_lecteur(self, monde):
        valide = PlanGestionFactory(statut='valide', sites=[monde.site_a])
        reponse = monde.client('membre_du_site').post(
            f'/api/plans/plans/{valide.pk}/duplicate/', {}, format='json')
        assert reponse.status_code == 403, reponse.content[:300]
        assert PlanGestion.objects.count() == 3  # A, B, valide : aucune copie


class TestSitesEntreOrganismes:
    def test_un_admin_ne_prend_pas_le_site_d_un_autre_organisme(self, monde):
        admin_a = AdminOrganismeFactory(id_organisme=monde.org_a)
        client = APIClient()
        client.force_authenticate(admin_a)
        reponse = client.post(
            f'/api/users/organismes/{monde.org_a.pk}/assign_site/',
            {'site_id': monde.site_b.pk}, format='json')
        assert reponse.status_code == 403, reponse.content[:300]
        assert not CorOgSite.objects.filter(uuid_og=monde.org_a, id_site=monde.site_b).exists()
        # … ni le plan de ce site, par la suite.
        assert client.get(f'/api/plans/plans/{monde.plan_b.pk}/export-plan-docx/').status_code in (403, 404)

    def test_ni_en_masse(self, monde):
        admin_a = AdminOrganismeFactory(id_organisme=monde.org_a)
        client = APIClient()
        client.force_authenticate(admin_a)
        reponse = client.post(
            f'/api/users/organismes/{monde.org_a.pk}/bulk_assign_sites/',
            {'site_ids': [monde.site_b.pk]}, format='json')
        assert reponse.status_code == 200, reponse.content[:300]
        assert [s['id_site'] for s in reponse.json()['forbidden']] == [monde.site_b.pk]
        assert not CorOgSite.objects.filter(uuid_og=monde.org_a, id_site=monde.site_b).exists()

    def test_un_site_sans_gestionnaire_se_rattache(self, monde):
        orphelin = SiteFactory()
        admin_a = AdminOrganismeFactory(id_organisme=monde.org_a)
        client = APIClient()
        client.force_authenticate(admin_a)
        reponse = client.post(
            f'/api/users/organismes/{monde.org_a.pk}/assign_site/',
            {'site_id': orphelin.pk}, format='json')
        assert reponse.status_code in (200, 201), reponse.content[:300]
