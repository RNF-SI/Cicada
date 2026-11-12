"""Droits d'écriture : les chemins « à côté » de la matrice (deuxième passe).

La matrice (``test_droits_ecriture.py``) ferme les gestes directs. Ceux-ci
passaient par un lien entre plans, un circuit de validation, un objet sans
plan, une clé imbriquée ou une exception oubliée. Chaque refus laisse
l'inventaire intact.
"""
import pytest
from rest_framework.test import APIClient

from apps.notifications.models import ValidationRequest
from apps.plans.models import PlanGestion
from apps.plans.models_enjeux import Responsabilite
from apps.plans.models_operations import Fonction, Poste, RealisationOperationAnnee
from tests.factories.enjeux import EnjeuFactory, NomenclatureEnjeuFactory, OperationFactory, SuiviInventaireFactory
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import (
    AdminOrganismeFactory, CorOgSiteFactory, CorRoleSiteFactory, OrganismeFactory, RoleFactory,
    SiteFactory,
)
from tests.integrite.socle import construire_plan_complet, ecarts, inventaire

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def deux_organismes():
    org_a, org_b = OrganismeFactory(), OrganismeFactory()
    site_a, site_b = SiteFactory(), SiteFactory()
    CorOgSiteFactory(id_site=site_a, uuid_og=org_a, principal=True)
    CorOgSiteFactory(id_site=site_b, uuid_og=org_b, principal=True)
    return org_a, org_b, site_a, site_b


class TestChaineDeVersions:
    def test_on_ne_se_rattache_pas_au_brouillon_d_un_autre(self, deux_organismes):
        org_a, _, site_a, _ = deux_organismes
        brouillon_d_autrui = PlanGestionFactory(statut='draft', sites=[site_a], rang=1,
                                                referents=[RoleFactory(id_organisme=org_a)])
        membre = RoleFactory(id_organisme=org_a)
        CorRoleSiteFactory(id_role=membre, id_site=site_a)
        reponse = _client(membre).post('/api/plans/plans/', {
            'nom': 'Mon plan rang 2', 'rang': 2, 'annee_debut': 2026, 'annee_fin': 2036,
            'sites_ids': [site_a.pk], 'plan_parent_id': brouillon_d_autrui.pk,
        }, format='json')
        assert reponse.status_code == 201, reponse.content[:300]
        plan = PlanGestion.objects.get(pk=reponse.json()['id_pg'])
        assert plan.plan_parent_id is None

    def test_valider_ne_valide_pas_un_parent_en_brouillon(self, deux_organismes):
        org_a, _, site_a, _ = deux_organismes
        referent = RoleFactory(id_organisme=org_a)
        parent = PlanGestionFactory(statut='draft', sites=[site_a], rang=1, referents=[referent])
        enfant = PlanGestionFactory(statut='draft', sites=[site_a], rang=2, referents=[referent])
        enfant.plan_parent = parent
        enfant.save(update_fields=['plan_parent'])
        reponse = _client(referent).post(f'/api/plans/plans/{enfant.pk}/change-status/',
                                          {'new_status': 'valide'}, format='json')
        assert reponse.status_code == 400
        parent.refresh_from_db()
        enfant.refresh_from_db()
        assert (parent.statut, enfant.statut) == ('draft', 'draft')


class TestDemandesDAcces:
    def _demande(self, demandeur, plan, en_saisie=True):
        return ValidationRequest.objects.create(
            request_type='plan_access', status='pending', requester=demandeur,
            target_plan=plan, request_as_referent=en_saisie)

    def test_on_n_approuve_pas_sa_propre_demande(self, deux_organismes):
        org_a, _, site_a, _ = deux_organismes
        plan = PlanGestionFactory(statut='draft', sites=[site_a])
        referent_du_site = RoleFactory(id_organisme=org_a)
        CorRoleSiteFactory(id_role=referent_du_site, id_site=site_a, referent=True, referent_valid=True)
        demande = self._demande(referent_du_site, plan)
        reponse = _client(referent_du_site).post(f'/api/validations/{demande.pk}/approve/', {}, format='json')
        assert reponse.status_code == 403
        assert not plan.referents.filter(pk=referent_du_site.pk).exists()

    def test_un_referent_de_site_n_accorde_pas_la_saisie(self, deux_organismes):
        org_a, _, site_a, _ = deux_organismes
        plan = PlanGestionFactory(statut='draft', sites=[site_a])
        referent_du_site = RoleFactory(id_organisme=org_a)
        CorRoleSiteFactory(id_role=referent_du_site, id_site=site_a, referent=True, referent_valid=True)
        demandeur = RoleFactory(id_organisme=org_a)
        demande = self._demande(demandeur, plan)
        client = _client(referent_du_site)
        reponse = client.post(f'/api/validations/{demande.pk}/approve/', {}, format='json')
        assert reponse.status_code == 403
        assert not plan.referents.filter(pk=demandeur.pk).exists()
        # L'accès en lecture, lui, il peut l'accorder.
        reponse = client.post(f'/api/validations/{demande.pk}/approve/',
                              {'approve_as_referent': False}, format='json')
        assert reponse.status_code == 200
        assert not plan.referents.filter(pk=demandeur.pk).exists()

    def test_pas_de_demande_nue(self, db):
        reponse = _client(RoleFactory()).post('/api/validations/', {'request_type': 'plan_access'}, format='json')
        assert reponse.status_code == 405


class TestRedacteurExterneEtSuivi:
    """#700 : le rédacteur externe saisit le plan, jamais le suivi."""

    @pytest.fixture
    def monde(self):
        m = construire_plan_complet(statut='valide')
        m.redacteur = RoleFactory(role_level='redacteur', id_organisme=OrganismeFactory())
        m.plan.referents.add(m.redacteur)
        m.action.id_utilisateur_ajout = m.redacteur
        m.action.save(update_fields=['id_utilisateur_ajout'])
        return m

    def test_il_n_ecrit_pas_le_suivi_de_son_action(self, monde):
        avant = inventaire()
        reponse = _client(monde.redacteur).post('/api/plans/realisations/upsert/', {
            'id_operation': monde.action.pk, 'annee': monde.annee - 1, 'commentaire': 'écrasé',
        }, format='json')
        assert reponse.status_code in (403, 404)
        assert not ecarts(avant, inventaire())

    def test_il_ne_lit_pas_le_suivi(self, monde):
        client = _client(monde.redacteur)
        lu = client.get(f'/api/plans/realisations/by-operation/{monde.action.pk}/')
        assert lu.status_code in (403, 404) or lu.json()['total'] == 0
        assert client.get(f'/api/plans/plans/{monde.plan.pk}/export-budget-suivi-xlsx/').status_code == 403
        assert client.get(
            f'/api/plans/plans/{monde.plan.pk}/export-fiches-suivi-xlsx/?annee={monde.annee}').status_code == 403
        assert client.get(f'/api/plans/operations/suivi-defaults/{monde.plan.pk}/').status_code == 403
        mesures = client.get('/api/plans/mesures/').json()
        assert len(mesures.get('results', []) if isinstance(mesures, dict) else mesures) == 0

    def test_la_liste_des_actions_ne_porte_pas_le_niveau_realise(self, monde):
        reponse = _client(monde.redacteur).get('/api/plans/operations/')
        assert reponse.status_code == 200
        assert 'niveau_realisation_global_mnemonique' not in reponse.content.decode()


class TestObjetsEtClesDAutresPlans:
    def test_une_action_sans_plan_ne_passe_pas_dans_le_plan_d_un_autre(self, deux_organismes):
        org_a, org_b, site_a, site_b = deux_organismes
        m = construire_plan_complet(statut='draft')
        orpheline = OperationFactory(code_operation='ORPH')
        auteur = RoleFactory(id_organisme=org_b)
        PlanGestionFactory(statut='draft', sites=[site_b], referents=[auteur])  # « référent de quelque chose »
        orpheline.id_utilisateur_ajout = auteur
        orpheline.save(update_fields=['id_utilisateur_ajout'])
        reponse = _client(auteur).post(f'/api/plans/operations/{orpheline.pk}/move/', {
            'new_indicateur_id': m.metrique.id_indicateur_id, 'position': 0}, format='json')
        assert reponse.status_code in (403, 404)
        orpheline.refresh_from_db()
        assert orpheline.get_plan_de_gestion() is None

    def test_le_poste_d_un_autre_plan_est_refuse(self, db):
        m = construire_plan_complet(statut='draft')
        autre = construire_plan_complet(statut='draft')
        avant = inventaire()
        reponse = _client(m.referent).post('/api/plans/operations/', {
            'libelle': 'Action qui emprunte un poste', 'metrique_ids': [m.metrique.pk],
            'id_indicateur': m.metrique.id_indicateur_id,
            'operation_annees': [{'annee': m.annee, 'rh_lignes': [
                {'id_poste': autre.poste.pk, 'jours': '3'}]}],
        }, format='json')
        assert reponse.status_code == 400, reponse.content[:300]
        assert 'poste' in reponse.content.decode().lower()
        assert not ecarts(avant, inventaire())

    def test_une_fonction_ne_change_pas_de_plan(self, db):
        m = construire_plan_complet(statut='draft')
        autre = construire_plan_complet(statut='valide')
        fonction = Fonction.objects.create(libelle='Garde du plan A', id_pg=m.plan)
        reponse = _client(m.referent).patch(f'/api/plans/fonctions/{fonction.pk}/',
                                            {'id_pg': autre.plan.pk}, format='json')
        assert reponse.status_code == 400
        fonction.refresh_from_db()
        assert fonction.id_pg_id == m.plan.pk

    def test_on_ne_relie_pas_le_suivi_autonome_d_un_autre_organisme(self, db):
        m = construire_plan_complet(statut='draft')
        etranger = SuiviInventaireFactory(intitule='Suivi d’ailleurs')
        etranger.id_utilisateur_ajout = RoleFactory(id_organisme=OrganismeFactory())
        etranger.save(update_fields=['id_utilisateur_ajout'])
        reponse = _client(m.referent).patch(f'/api/plans/operations/{m.action.pk}/',
                                            {'id_suivi': etranger.pk}, format='json')
        assert reponse.status_code == 400
        m.action.refresh_from_db()
        assert m.action.id_suivi_id != etranger.pk


class TestSitesEtOrdre:
    def test_responsabilite_d_un_site_d_un_autre_organisme(self, deux_organismes):
        org_a, _, site_a, site_b = deux_organismes
        from tests.factories.core import NomenclatureFactory
        responsabilite = Responsabilite.objects.create(
            id_site=site_b, description='Tourbière',
            id_type_responsabilite=NomenclatureFactory(), id_niveau_responsabilite=NomenclatureFactory(),
            id_utilisateur_ajout=RoleFactory(id_organisme=org_a))
        referent_ailleurs = RoleFactory(id_organisme=org_a)
        PlanGestionFactory(statut='draft', sites=[site_a], referents=[referent_ailleurs])
        client = _client(referent_ailleurs)
        assert client.patch(f'/api/plans/responsabilites/{responsabilite.pk}/',
                            {'description': 'Réécrite'}, format='json').status_code in (403, 404)
        assert client.post('/api/plans/responsabilites/',
                           {'id_site': site_b.pk, 'description': 'Ajout'}, format='json').status_code == 403
        responsabilite.refresh_from_db()
        assert responsabilite.description == 'Tourbière'

    def test_un_lecteur_ne_reordonne_pas_les_enjeux(self, deux_organismes):
        org_a, _, site_a, _ = deux_organismes
        plan = PlanGestionFactory(statut='draft', sites=[site_a], referents=[RoleFactory(id_organisme=org_a)])
        e1, e2 = EnjeuFactory(id_pg=plan), EnjeuFactory(id_pg=plan)
        lecteur = RoleFactory(id_organisme=org_a)
        CorRoleSiteFactory(id_role=lecteur, id_site=site_a)
        PlanGestionFactory(statut='draft', sites=[site_a], referents=[lecteur])  # référent d'un autre plan
        reponse = _client(lecteur).post('/api/plans/enjeux/reorder/', {
            'parent_id': plan.pk, 'ordered_ids': [e2.pk, e1.pk]}, format='json')
        assert reponse.status_code == 403

    def test_l_organisme_principal_reste_au_super_admin(self, deux_organismes):
        org_a, _, site_a, _ = deux_organismes
        admin = AdminOrganismeFactory(id_organisme=org_a)
        reponse = _client(admin).post(f'/api/users/sites/{site_a.slug}/set_principal_organisme/',
                                      {'organisme_id': org_a.pk}, format='json')
        assert reponse.status_code == 403
