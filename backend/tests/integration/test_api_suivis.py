"""
Tests d'intégration pour l'API REST Suivis/Inventaires (standalone).
"""
import pytest
from rest_framework import status

from apps.plans.models_operations import SuiviInventaire, Protocole
from tests.factories.enjeux import (
    SuiviInventaireFactory, ProtocoleFactory,
)
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory


@pytest.fixture
def suivi_test_data(db):
    """Fixture providing common test data for suivis tests."""
    from django.core.management import call_command
    from apps.core.models import Nomenclature

    # Import nomenclatures (needed for id_type_action required field)
    call_command('import_nomenclatures', '--force', verbosity=0)

    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan Test Suivis', statut='draft')
    CorSitePgFactory(plan_de_gestion=plan, site=site)

    # Users
    super_admin = SuperAdminFactory()
    admin_og = AdminOrganismeFactory(id_organisme=organisme)
    referent = ReferentFactory(id_organisme=organisme)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan.referents.add(referent)
    user = RoleFactory()

    # Get a CS type_action nomenclature for test suivis
    cs8 = Nomenclature.objects.filter(
        id_type__mnemonique='TYPE_ACTION', cd_nomenclature='CS8'
    ).first()

    # Suivis/Inventaires
    suivi1 = SuiviInventaireFactory(
        intitule='Suivi floristique prairie humide',
        actif=True,
        date_lancement_suivi='2020-01-01',
        annee_fin_suivi=None,
        objectif_principal='OBJ_ETAT_CONSERVATION',
        cibles_principales='ESPECES',
        commentaires='Premier suivi de test',
        id_utilisateur_ajout=referent,
    )
    suivi2 = SuiviInventaireFactory(
        intitule='Inventaire avifaune nicheuse',
        actif=True,
        date_lancement_suivi='2018-01-01',
        annee_fin_suivi=2023,
        objectif_principal='OBJ_ACQUISITION_CONNAISSANCES',
        cibles_principales='ESPECES',
        commentaires='Deuxième suivi de test',
        id_utilisateur_ajout=referent,
    )
    suivi3 = SuiviInventaireFactory(
        intitule='Suivi inactif ancien',
        actif=False,
        date_lancement_suivi='2010-01-01',
        annee_fin_suivi=2015,
        id_utilisateur_ajout=referent,
    )

    return {
        'organisme': organisme,
        'site': site,
        'plan': plan,
        'super_admin': super_admin,
        'admin_og': admin_og,
        'referent': referent,
        'user': user,
        'suivi1': suivi1,
        'suivi2': suivi2,
        'suivi3': suivi3,
        'type_action_cs8': cs8,
    }


# =============================================================================
# TestSuivisListEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisListEndpoint:
    """Tests for GET /api/inventaires/suivis/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/inventaires/suivis/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, suivi_test_data):
        """Test super admin can see all suivis."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 3

    def test_filter_by_actif(self, api_client, suivi_test_data):
        """Test filtering by actif=true shows only active suivis."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/?actif=true')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['actif'] is True

    def test_filter_by_inactif(self, api_client, suivi_test_data):
        """Test filtering by actif=false shows only inactive suivis."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/?actif=false')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['actif'] is False

    def test_search_by_intitule(self, api_client, suivi_test_data):
        """Test search filters by intitule."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/?search=floristique')
        assert response.status_code == status.HTTP_200_OK
        intitules = [s['intitule'] for s in response.data['results']]
        assert 'Suivi floristique prairie humide' in intitules

    def test_pagination_works(self, api_client, suivi_test_data):
        """Test pagination is present in response."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'pagination' in response.data
        assert 'count' in response.data['pagination']

    def test_list_includes_expected_fields(self, api_client, suivi_test_data):
        """Test list response includes expected fields."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/')
        assert response.status_code == status.HTTP_200_OK
        if response.data['results']:
            item = response.data['results'][0]
            assert 'intitule' in item
            assert 'actif' in item
            assert 'nb_operations' in item
            assert 'date_lancement_suivi' in item


# =============================================================================
# TestSuivisCreateEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisCreateEndpoint:
    """Tests for POST /api/inventaires/suivis/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated create returns 401."""
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Nouveau suivi',
        }, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_creates_suivi(self, api_client, suivi_test_data):
        """Test super admin can create a suivi."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Nouveau suivi SA',
            'objectif_principal': 'OBJ_RISQUES_ECOLOGIQUES',
            'cibles_principales': 'HABITATS_VEGETATIONS',
            'date_lancement_suivi': '2025-01-01',
            'id_type_action': suivi_test_data['type_action_cs8'].id_nomenclature,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert SuiviInventaire.objects.filter(intitule='Nouveau suivi SA').exists()

    def test_create_with_nested_protocole(self, api_client, suivi_test_data):
        """Test creating suivi with nested protocole."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Suivi avec protocole',
            'objectif_principal': 'OBJ_ETAT_CONSERVATION',
            'cibles_principales': 'ESPECES',
            'id_type_action': suivi_test_data['type_action_cs8'].id_nomenclature,
            'protocole': {
                'protocole_dans_campanule': True,
                'protocole_campanule_nom': 'Proto Test',
                'nom_protocole': '',
                'description_protocole': 'Description du protocole',
            },
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        suivi = SuiviInventaire.objects.get(intitule='Suivi avec protocole')
        assert suivi.protocoles.count() == 1
        assert suivi.protocoles.first().protocole_campanule_nom == 'Proto Test'

    def test_create_campanule_protocole(self, api_client, suivi_test_data):
        """Test creating suivi with Campanule protocol (cd_protocole_campanule)."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Suivi Campanule',
            'objectif_principal': 'OBJ_ETAT_CONSERVATION',
            'cibles_principales': 'ESPECES',
            'id_type_action': suivi_test_data['type_action_cs8'].id_nomenclature,
            'protocole': {
                'protocole_dans_campanule': True,
                'protocole_campanule_nom': 'STOC-EPS',
                'cd_protocole_campanule': 42,
                'description_protocole': 'Description auto-remplie depuis Campanule',
                'objectif_protocole': 'Objectif auto-rempli',
                'periode_echantillonnage': 'Avril - Juin',
                'respect_protocole': True,
            },
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        suivi = SuiviInventaire.objects.get(intitule='Suivi Campanule')
        proto = suivi.protocoles.first()
        assert proto is not None
        assert proto.protocole_dans_campanule is True
        assert proto.cd_protocole_campanule == 42
        assert proto.protocole_campanule_nom == 'STOC-EPS'
        assert proto.nom_protocole == ''
        assert proto.nb_etp_cycle is None

    def test_create_non_campanule_protocole(self, api_client, suivi_test_data):
        """Test creating suivi with custom protocol (nom_protocole + nb_etp_cycle)."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Suivi Custom',
            'objectif_principal': 'OBJ_RISQUES_ECOLOGIQUES',
            'cibles_principales': 'HABITATS_VEGETATIONS',
            'id_type_action': suivi_test_data['type_action_cs8'].id_nomenclature,
            'protocole': {
                'protocole_dans_campanule': False,
                'nom_protocole': 'Mon protocole maison',
                'nb_etp_cycle': 2.5,
                'description_protocole': 'Description libre',
                'objectif_protocole': 'Objectif libre',
                'periode_echantillonnage': 'Toute année',
                'respect_protocole': False,
                'justification_non_respect': 'Adaptations locales',
                'differences_protocole': 'Quadrats plus grands',
            },
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        suivi = SuiviInventaire.objects.get(intitule='Suivi Custom')
        proto = suivi.protocoles.first()
        assert proto is not None
        assert proto.protocole_dans_campanule is False
        assert proto.cd_protocole_campanule is None
        assert proto.nom_protocole == 'Mon protocole maison'
        assert float(proto.nb_etp_cycle) == 2.5
        assert proto.respect_protocole is False
        assert proto.justification_non_respect == 'Adaptations locales'
        assert proto.differences_protocole == 'Quadrats plus grands'

    def test_create_with_minimal_fields(self, api_client, suivi_test_data):
        """Test create with intitule and id_type_action (required)."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Suivi Minimal',
            'id_type_action': suivi_test_data['type_action_cs8'].id_nomenclature,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_audit_field_set_on_create(self, api_client, suivi_test_data):
        """Test id_utilisateur_ajout is set on create."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Suivi Audit',
            'id_type_action': suivi_test_data['type_action_cs8'].id_nomenclature,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        suivi = SuiviInventaire.objects.get(intitule='Suivi Audit')
        assert suivi.id_utilisateur_ajout == suivi_test_data['super_admin']


# =============================================================================
# TestSuivisDetailEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisDetailEndpoint:
    """Tests for GET /api/inventaires/suivis/{id}/"""

    def test_unauthenticated_returns_401(self, api_client, suivi_test_data):
        """Test unauthenticated detail returns 401."""
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.get(f'/api/inventaires/suivis/{suivi_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_gets_detail(self, api_client, suivi_test_data):
        """Test super admin can get detail of a suivi."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.get(f'/api/inventaires/suivis/{suivi_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['intitule'] == 'Suivi floristique prairie humide'
        assert 'protocole' in response.data
        assert 'nb_operations' in response.data
        assert 'createur_nom' in response.data

    def test_detail_with_protocole(self, api_client, suivi_test_data):
        """Test detail includes nested protocole when present."""
        # Create a suivi with protocole
        protocole = ProtocoleFactory(
            protocole_dans_campanule=True,
            protocole_campanule_nom='Proto Detail',
            id_utilisateur_ajout=suivi_test_data['referent'],
        )
        suivi_with_proto = SuiviInventaireFactory(
            intitule='Suivi avec proto detail',
            protocoles=[protocole],
            id_utilisateur_ajout=suivi_test_data['referent'],
        )

        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get(f'/api/inventaires/suivis/{suivi_with_proto.id_suivi_inventaire}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['protocole'] is not None
        assert response.data['protocole']['protocole_campanule_nom'] == 'Proto Detail'

    def test_detail_roundtrip_all_fields(self, api_client, suivi_test_data):
        """Test POST create → GET detail returns all fields for edit form pre-fill."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])

        # Create a suivi with all fields populated
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Suivi roundtrip complet',
            'prix_indicatif': 1500,
            'integre_plan_gestion': True,
            'id_type_action': suivi_test_data['type_action_cs8'].id_nomenclature,
            'objectif_principal': 'OBJ_ETAT_CONSERVATION',
            'objectif_secondaire': 'OBJ_DYNAMIQUE_MILIEUX',
            'cibles_principales': 'ESPECES',
            'cible_secondaire': 'HABITATS_VEGETATIONS',
            'taxon_taxref': 'Aves, Chiroptera',
            'habitat_ref': 'Prairie humide',
            'date_lancement_suivi': '2024-01-01',
            'annee_fin_suivi': 2030,
            'frequence_nombre': 2,
            'frequence_unite': 'mois',
            'commentaires': 'Commentaire de test complet',
            'outil_bancarisation': 'GeoNature',
            'outil_saisie': 'OdkCollect',
            'transmission_donnee': True,
            'protocole': {
                'protocole_dans_campanule': True,
                'protocole_campanule_nom': 'STOC-EPS',
                'cd_protocole_campanule': 42,
                'description_protocole': 'Suivi temporel des oiseaux communs',
                'objectif_protocole': 'Évaluer les tendances',
                'periode_echantillonnage': 'Avril - Juin',
                'respect_protocole': True,
            },
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        suivi_id = response.data['id_suivi_inventaire']

        # GET detail — simulates opening the edit form
        response = api_client.get(f'/api/inventaires/suivis/{suivi_id}/')
        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # All main fields must be present for form pre-fill
        assert data['intitule'] == 'Suivi roundtrip complet'
        assert float(data['prix_indicatif']) == 1500
        assert data['integre_plan_gestion'] is True
        assert data['objectif_principal'] == 'OBJ_ETAT_CONSERVATION'
        assert data['objectif_secondaire'] == 'OBJ_DYNAMIQUE_MILIEUX'
        assert data['cibles_principales'] == 'ESPECES'
        assert data['cible_secondaire'] == 'HABITATS_VEGETATIONS'
        assert data['taxon_taxref'] == 'Aves, Chiroptera'
        assert data['habitat_ref'] == 'Prairie humide'
        assert data['date_lancement_suivi'] == '2024-01-01'
        assert data['annee_fin_suivi'] == 2030
        assert data['frequence_nombre'] == 2
        assert data['frequence_unite'] == 'mois'
        assert data['commentaires'] == 'Commentaire de test complet'

        # Bancarisation
        assert data['outil_bancarisation'] == 'GeoNature'
        assert data['outil_saisie'] == 'OdkCollect'
        assert data['transmission_donnee'] is True

        # Nested protocole
        proto = data['protocole']
        assert proto is not None
        assert proto['protocole_dans_campanule'] is True
        assert proto['protocole_campanule_nom'] == 'STOC-EPS'
        assert proto['cd_protocole_campanule'] == 42
        assert proto['description_protocole'] == 'Suivi temporel des oiseaux communs'
        assert proto['objectif_protocole'] == 'Évaluer les tendances'
        assert proto['periode_echantillonnage'] == 'Avril - Juin'
        assert proto['respect_protocole'] is True

        # Computed/read-only fields for the detail page
        assert 'nb_operations' in data
        assert 'createur_nom' in data
        assert 'statut_label' in data
        assert 'type_action_label' in data
        assert 'date_ajout' in data


# =============================================================================
# TestSuivisUpdateEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisUpdateEndpoint:
    """Tests for PATCH /api/inventaires/suivis/{id}/"""

    def test_super_admin_updates_suivi(self, api_client, suivi_test_data):
        """Test super admin can update a suivi."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.patch(f'/api/inventaires/suivis/{suivi_id}/', {
            'intitule': 'Suivi modifié',
            'commentaires': 'Commentaire mis à jour',
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        suivi_test_data['suivi1'].refresh_from_db()
        assert suivi_test_data['suivi1'].intitule == 'Suivi modifié'
        assert suivi_test_data['suivi1'].commentaires == 'Commentaire mis à jour'

    def test_update_with_nested_protocole(self, api_client, suivi_test_data):
        """Test updating suivi with nested protocole creation."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.patch(f'/api/inventaires/suivis/{suivi_id}/', {
            'protocole': {
                'protocole_dans_campanule': False,
                'nom_protocole': 'Protocole custom',
            },
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        suivi_test_data['suivi1'].refresh_from_db()
        assert suivi_test_data['suivi1'].protocoles.count() == 1

    def test_audit_field_set_on_update(self, api_client, suivi_test_data):
        """Test id_utilisateur_maj is set on update."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.patch(f'/api/inventaires/suivis/{suivi_id}/', {
            'intitule': 'Suivi audit update',
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        suivi_test_data['suivi1'].refresh_from_db()
        assert suivi_test_data['suivi1'].id_utilisateur_maj == suivi_test_data['super_admin']


# =============================================================================
# TestSuivisDeleteEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisDeleteEndpoint:
    """Tests for DELETE /api/inventaires/suivis/{id}/"""

    def test_unauthenticated_returns_401(self, api_client, suivi_test_data):
        """Test unauthenticated delete returns 401."""
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.delete(f'/api/inventaires/suivis/{suivi_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_deletes_suivi(self, api_client, suivi_test_data):
        """Test super admin can delete a suivi."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        suivi_id = suivi_test_data['suivi3'].id_suivi_inventaire
        response = api_client.delete(f'/api/inventaires/suivis/{suivi_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not SuiviInventaire.objects.filter(id_suivi_inventaire=suivi_id).exists()


# =============================================================================
# TestSuivisTypeAction
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisTypeAction:
    """Tests pour le champ id_type_action et le filtre type_action_prefix."""

    def test_create_suivi_with_type_action(self, api_client, suivi_test_data):
        """Test création d'un suivi avec un type d'action CS."""
        from apps.core.models import Nomenclature
        cs8 = Nomenclature.objects.filter(
            id_type__mnemonique='TYPE_ACTION', cd_nomenclature='CS8'
        ).first()
        assert cs8 is not None, "Nomenclature CS8 doit exister après import"

        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        payload = {
            'intitule': 'Inventaire faune avec type action',
            'id_type_action': cs8.id_nomenclature,
        }
        response = api_client.post('/api/inventaires/suivis/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['id_type_action'] == cs8.id_nomenclature

    def test_detail_returns_type_action_fields(self, api_client, suivi_test_data):
        """Test que le détail retourne type_action_code et type_action_label."""
        from apps.core.models import Nomenclature
        cs8 = Nomenclature.objects.filter(
            id_type__mnemonique='TYPE_ACTION', cd_nomenclature='CS8'
        ).first()
        assert cs8 is not None

        suivi = suivi_test_data['suivi1']
        suivi.id_type_action = cs8
        suivi.save()

        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get(f'/api/inventaires/suivis/{suivi.id_suivi_inventaire}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['type_action_code'] == 'CS8'
        assert response.data['type_action_label'] == cs8.label

    def test_filter_by_type_action_prefix(self, api_client, suivi_test_data):
        """Test filtre par préfixe de type d'action (CS8 → CS8, CS8.1, ...)."""
        from apps.core.models import Nomenclature
        cs8 = Nomenclature.objects.filter(
            id_type__mnemonique='TYPE_ACTION', cd_nomenclature='CS8'
        ).first()
        cs8_1 = Nomenclature.objects.filter(
            id_type__mnemonique='TYPE_ACTION', cd_nomenclature='CS8.1'
        ).first()
        assert cs8 is not None and cs8_1 is not None

        # Assigner des types différents
        suivi1 = suivi_test_data['suivi1']
        suivi1.id_type_action = cs8
        suivi1.save()
        suivi2 = suivi_test_data['suivi2']
        suivi2.id_type_action = cs8_1
        suivi2.save()

        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/?type_action_prefix=CS8')
        assert response.status_code == status.HTTP_200_OK
        ids = [s['id_suivi_inventaire'] for s in response.data['results']]
        assert suivi1.id_suivi_inventaire in ids
        assert suivi2.id_suivi_inventaire in ids


@pytest.mark.django_db
class TestSuiviMultiProtocoles:
    """#252 — un suivi peut porter plusieurs protocoles."""

    def test_create_with_several_protocoles(self, api_client, suivi_test_data):
        """POST avec N protocoles → les N sont rattachés au suivi."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Inventaire ornithologique',
            'id_type_action': suivi_test_data['type_action_cs8'].id_nomenclature,
            'protocoles': [
                {
                    'protocole_dans_campanule': True,
                    'protocole_campanule_nom': "Points d'écoute",
                    'cd_protocole_campanule': 42,
                },
                {
                    'protocole_dans_campanule': False,
                    'nom_protocole': 'IPA',
                    'nb_etp_cycle': 1.5,
                },
            ],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        suivi = SuiviInventaire.objects.get(intitule='Inventaire ornithologique')
        assert suivi.protocoles.count() == 2
        noms = {
            p.protocole_campanule_nom or p.nom_protocole
            for p in suivi.protocoles.all()
        }
        assert noms == {"Points d'écoute", 'IPA'}

    def test_detail_exposes_protocoles_list(self, api_client, suivi_test_data):
        """GET détail expose `protocoles` (liste) et `protocole` (1er, déprécié)."""
        p1 = ProtocoleFactory(
            protocole_campanule_nom='Proto A',
            id_utilisateur_ajout=suivi_test_data['referent'],
        )
        p2 = ProtocoleFactory(
            nom_protocole='Proto B',
            id_utilisateur_ajout=suivi_test_data['referent'],
        )
        suivi = SuiviInventaireFactory(
            intitule='Suivi multi',
            protocoles=[p1, p2],
            id_utilisateur_ajout=suivi_test_data['referent'],
        )

        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get(f'/api/inventaires/suivis/{suivi.id_suivi_inventaire}/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['protocoles']) == 2
        # Alias singulier conservé pour les clients antérieurs à #252.
        assert response.data['protocole']['protocole_campanule_nom'] == 'Proto A'

    def test_update_replaces_the_whole_list(self, api_client, suivi_test_data):
        """PATCH avec une nouvelle liste remplace l'ancienne et purge les orphelins."""
        p1 = ProtocoleFactory(
            nom_protocole='Ancien',
            id_utilisateur_ajout=suivi_test_data['referent'],
        )
        suivi = SuiviInventaireFactory(
            intitule='Suivi à mettre à jour',
            protocoles=[p1],
            id_utilisateur_ajout=suivi_test_data['referent'],
        )
        ancien_id = p1.id_protocole

        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.patch(
            f'/api/inventaires/suivis/{suivi.id_suivi_inventaire}/',
            {
                'protocoles': [
                    {'protocole_dans_campanule': False, 'nom_protocole': 'Nouveau 1'},
                    {'protocole_dans_campanule': False, 'nom_protocole': 'Nouveau 2'},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

        suivi.refresh_from_db()
        assert suivi.protocoles.count() == 2
        assert {p.nom_protocole for p in suivi.protocoles.all()} == {'Nouveau 1', 'Nouveau 2'}
        # L'ancien protocole n'est plus référencé nulle part → supprimé.
        assert not Protocole.objects.filter(id_protocole=ancien_id).exists()

    def test_update_with_empty_list_detaches_all(self, api_client, suivi_test_data):
        """PATCH avec une liste vide retire tous les protocoles."""
        p1 = ProtocoleFactory(
            nom_protocole='À retirer',
            id_utilisateur_ajout=suivi_test_data['referent'],
        )
        suivi = SuiviInventaireFactory(
            intitule='Suivi à vider',
            protocoles=[p1],
            id_utilisateur_ajout=suivi_test_data['referent'],
        )

        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.patch(
            f'/api/inventaires/suivis/{suivi.id_suivi_inventaire}/',
            {'protocoles': []},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        suivi.refresh_from_db()
        assert suivi.protocoles.count() == 0

    def test_update_without_protocoles_key_leaves_list_untouched(self, api_client, suivi_test_data):
        """PATCH partiel sans clé protocole(s) ne touche pas la liste existante."""
        p1 = ProtocoleFactory(
            nom_protocole='Conservé',
            id_utilisateur_ajout=suivi_test_data['referent'],
        )
        suivi = SuiviInventaireFactory(
            intitule='Suivi intact',
            protocoles=[p1],
            id_utilisateur_ajout=suivi_test_data['referent'],
        )

        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.patch(
            f'/api/inventaires/suivis/{suivi.id_suivi_inventaire}/',
            {'intitule': 'Suivi intact renommé'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        suivi.refresh_from_db()
        assert suivi.protocoles.count() == 1
        assert suivi.protocoles.first().nom_protocole == 'Conservé'

    def test_shared_protocole_is_not_deleted_while_still_used(self, api_client, suivi_test_data):
        """Un protocole partagé avec un autre suivi survit à la purge des orphelins."""
        partage = ProtocoleFactory(
            nom_protocole='Partagé',
            id_utilisateur_ajout=suivi_test_data['referent'],
        )
        suivi_a = SuiviInventaireFactory(
            intitule='Suivi A',
            protocoles=[partage],
            id_utilisateur_ajout=suivi_test_data['referent'],
        )
        suivi_b = SuiviInventaireFactory(
            intitule='Suivi B',
            protocoles=[partage],
            id_utilisateur_ajout=suivi_test_data['referent'],
        )

        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.patch(
            f'/api/inventaires/suivis/{suivi_a.id_suivi_inventaire}/',
            {'protocoles': [{'protocole_dans_campanule': False, 'nom_protocole': 'Autre'}]},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

        # Le protocole reste rattaché à suivi_b, donc il n'est pas supprimé.
        assert Protocole.objects.filter(id_protocole=partage.id_protocole).exists()
        assert suivi_b.protocoles.count() == 1
