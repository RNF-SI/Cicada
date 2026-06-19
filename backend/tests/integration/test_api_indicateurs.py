"""
Tests d'intégration pour l'API REST Indicateurs, Métriques et Mesures.
"""
import pytest
from rest_framework import status

from apps.plans.models_indicateurs import Indicateur, Metrique, Mesure, CorIndicateurTaxon
from tests.factories.enjeux import (
    EnjeuFactory, ObjectifLongTermeFactory, NiveauExigenceFactory,
    NomenclatureEnjeuFactory,
    IndicateurFactory, MetriqueFactory, MesureFactory,
    NomenclatureTypeIndicateurFactory, NomenclatureTypeMetriqueFactory,
    CorIndicateurTaxonFactory,
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)


@pytest.fixture
def indicateur_test_data(db):
    """Fixture providing test data for indicateurs, metriques and mesures tests."""
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan Indicateur Test', statut='draft')
    CorSitePgFactory(plan_de_gestion=plan, site=site)

    super_admin = SuperAdminFactory()
    admin_og = AdminOrganismeFactory(id_organisme=organisme)
    referent = ReferentFactory(id_organisme=organisme)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan.referents.add(referent)
    user = RoleFactory()

    cat_enjeu = NomenclatureEnjeuFactory()
    enjeu = EnjeuFactory(
        id_pg=plan, id_categorie=cat_enjeu, libelle='Enjeu Indicateur Test',
        id_utilisateur_ajout=referent
    )
    olt = ObjectifLongTermeFactory(
        id_enjeu=enjeu, libelle='OLT Indicateur',
        id_utilisateur_ajout=referent
    )
    ne1 = NiveauExigenceFactory(
        id_olt=olt, libelle='NE Indicateur 1',
        id_utilisateur_ajout=referent
    )
    ne2 = NiveauExigenceFactory(
        id_olt=olt, libelle='NE Indicateur 2',
        id_utilisateur_ajout=referent
    )

    type_ind = NomenclatureTypeIndicateurFactory()
    type_met = NomenclatureTypeMetriqueFactory()

    indicateur1 = IndicateurFactory(
        id_ne=ne1, nom_indicateur='Indicateur Principal',
        description='Description de l\'indicateur principal',
        type_indicateur=type_ind,
        id_utilisateur_ajout=referent
    )
    indicateur2 = IndicateurFactory(
        id_ne=ne1, nom_indicateur='Indicateur Secondaire',
        type_indicateur=type_ind,
        id_utilisateur_ajout=referent
    )

    metrique1 = MetriqueFactory(
        id_indicateur=indicateur1, nom_metrique='Métrique Principale',
        description='Description de la métrique',
        type_metrique=type_met, unite='%',
        id_utilisateur_ajout=referent
    )
    metrique2 = MetriqueFactory(
        id_indicateur=indicateur1, nom_metrique='Métrique Secondaire',
        type_metrique=type_met, unite='m²',
        id_utilisateur_ajout=referent
    )

    mesure1 = MesureFactory(
        id_metrique=metrique1, valeur='75.5',
        commentaire='Mesure initiale',
        id_utilisateur_ajout=referent
    )
    mesure2 = MesureFactory(
        id_metrique=metrique1, valeur='82.3',
        commentaire='Mesure suivante',
        id_utilisateur_ajout=referent
    )

    return {
        'organisme': organisme,
        'site': site,
        'plan': plan,
        'super_admin': super_admin,
        'admin_og': admin_og,
        'referent': referent,
        'user': user,
        'enjeu': enjeu,
        'olt': olt,
        'ne1': ne1,
        'ne2': ne2,
        'type_ind': type_ind,
        'type_met': type_met,
        'indicateur1': indicateur1,
        'indicateur2': indicateur2,
        'metrique1': metrique1,
        'metrique2': metrique2,
        'mesure1': mesure1,
        'mesure2': mesure2,
    }


# =============================================================================
# Indicateur CRUD
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestIndicateurList:
    """Tests for GET /api/plans/indicateurs/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/indicateurs/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, indicateur_test_data):
        """Test super admin can see all indicateurs."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.get('/api/plans/indicateurs/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_referent_sees_own(self, api_client, indicateur_test_data):
        """Test referent sees indicateurs from their plans."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        response = api_client.get('/api/plans/indicateurs/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2


@pytest.mark.django_db
@pytest.mark.integration
class TestIndicateurCreate:
    """Tests for POST /api/plans/indicateurs/"""

    def test_referent_creates(self, api_client, indicateur_test_data):
        """Test referent can create an indicateur."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        response = api_client.post('/api/plans/indicateurs/', {
            'id_ne': indicateur_test_data['ne1'].id_ne,
            'nom_indicateur': 'Nouvel Indicateur',
            'description': 'Description test',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Indicateur.objects.filter(nom_indicateur='Nouvel Indicateur').exists()

    def test_non_referent_denied(self, api_client, indicateur_test_data):
        """Test non-referent cannot create."""
        api_client.force_authenticate(user=indicateur_test_data['user'])
        response = api_client.post('/api/plans/indicateurs/', {
            'id_ne': indicateur_test_data['ne1'].id_ne,
            'nom_indicateur': 'Should Fail',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_audit_fields_set(self, api_client, indicateur_test_data):
        """Test audit fields are set on create."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.post('/api/plans/indicateurs/', {
            'id_ne': indicateur_test_data['ne1'].id_ne,
            'nom_indicateur': 'Indicateur Audit',
        })
        assert response.status_code == status.HTTP_201_CREATED
        ind = Indicateur.objects.get(nom_indicateur='Indicateur Audit')
        assert ind.id_utilisateur_ajout == indicateur_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestIndicateurDetail:
    """Tests for GET/PATCH/DELETE /api/plans/indicateurs/{id}/"""

    def test_referent_gets_detail(self, api_client, indicateur_test_data):
        """Test referent can retrieve indicateur detail."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/indicateurs/{ind_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom_indicateur'] == 'Indicateur Principal'

    def test_detail_includes_metriques(self, api_client, indicateur_test_data):
        """Test detail includes nested metriques."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/indicateurs/{ind_id}/')
        assert 'metriques' in response.data
        assert len(response.data['metriques']) >= 2

    def test_detail_metriques_include_direction_fields(self, api_client, indicateur_test_data):
        """Test detail metriques include sens_variation and inclusivity fields."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/indicateurs/{ind_id}/')
        metrique_data = response.data['metriques'][0]
        assert 'sens_variation' in metrique_data
        assert 'score_1_sup_inclusive' in metrique_data
        assert 'score_2_sup_inclusive' in metrique_data
        assert 'score_3_sup_inclusive' in metrique_data
        assert 'score_4_sup_inclusive' in metrique_data
        assert 'has_borne_score1' in metrique_data
        assert 'has_borne_score5' in metrique_data
        # Defaults should be returned
        assert metrique_data['sens_variation'] == 'CROISSANT'
        assert metrique_data['score_1_sup_inclusive'] is True
        assert metrique_data['has_borne_score1'] is False
        assert metrique_data['has_borne_score5'] is False

    def test_nb_metriques_correct(self, api_client, indicateur_test_data):
        """Test nb_metriques is correct."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/indicateurs/{ind_id}/')
        assert response.data['nb_metriques'] == 2

    def test_nonexistent_returns_404(self, api_client, indicateur_test_data):
        """Test nonexistent indicateur returns 404."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.get('/api/plans/indicateurs/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_referent_updates(self, api_client, indicateur_test_data):
        """Test referent can update an indicateur."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        response = api_client.patch(f'/api/plans/indicateurs/{ind_id}/', {
            'nom_indicateur': 'Indicateur Mis à Jour'
        })
        assert response.status_code == status.HTTP_200_OK
        indicateur_test_data['indicateur1'].refresh_from_db()
        assert indicateur_test_data['indicateur1'].nom_indicateur == 'Indicateur Mis à Jour'

    def test_referent_deletes(self, api_client, indicateur_test_data):
        """Test referent can delete an indicateur."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        ind_id = indicateur_test_data['indicateur2'].id_indicateur
        response = api_client.delete(f'/api/plans/indicateurs/{ind_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Indicateur.objects.filter(id_indicateur=ind_id).exists()

    def test_non_referent_delete_denied(self, api_client, indicateur_test_data):
        """Test non-referent cannot delete."""
        api_client.force_authenticate(user=indicateur_test_data['user'])
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        response = api_client.delete(f'/api/plans/indicateurs/{ind_id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# Indicateur by-ne endpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestIndicateurByNe:
    """Tests for GET /api/plans/indicateurs/by-ne/{ne_id}/"""

    def test_unauthenticated_returns_401(self, api_client, indicateur_test_data):
        """Test unauthenticated access returns 401."""
        ne_id = indicateur_test_data['ne1'].id_ne
        response = api_client.get(f'/api/plans/indicateurs/by-ne/{ne_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_referent_gets_by_ne(self, api_client, indicateur_test_data):
        """Test referent can get indicateurs by niveau d'exigence."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        ne_id = indicateur_test_data['ne1'].id_ne
        response = api_client.get(f'/api/plans/indicateurs/by-ne/{ne_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['ne_id'] == ne_id

    def test_response_structure(self, api_client, indicateur_test_data):
        """Test response has correct structure."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        ne_id = indicateur_test_data['ne1'].id_ne
        response = api_client.get(f'/api/plans/indicateurs/by-ne/{ne_id}/')
        assert 'ne_id' in response.data
        assert 'ne_libelle' in response.data
        assert 'indicateurs' in response.data
        assert 'total' in response.data

    def test_empty_ne_returns_empty_list(self, api_client, indicateur_test_data):
        """Test NE without indicateurs returns empty list."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        ne_id = indicateur_test_data['ne2'].id_ne
        response = api_client.get(f'/api/plans/indicateurs/by-ne/{ne_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 0
        assert len(response.data['indicateurs']) == 0

    def test_nonexistent_ne_returns_404(self, api_client, indicateur_test_data):
        """Test nonexistent NE returns 404."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.get('/api/plans/indicateurs/by-ne/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Metrique CRUD
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestMetriqueList:
    """Tests for GET /api/plans/metriques/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/metriques/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, indicateur_test_data):
        """Test super admin can see all metriques."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.get('/api/plans/metriques/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_referent_sees_own(self, api_client, indicateur_test_data):
        """Test referent sees metriques from their plans."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        response = api_client.get('/api/plans/metriques/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2


@pytest.mark.django_db
@pytest.mark.integration
class TestMetriqueCreate:
    """Tests for POST /api/plans/metriques/"""

    def test_referent_creates(self, api_client, indicateur_test_data):
        """Test referent can create a metrique."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': 'Nouvelle Métrique',
            'description': 'Description test',
            'unite': 'individus',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Metrique.objects.filter(nom_metrique='Nouvelle Métrique').exists()

    def test_create_indetermine_without_name(self, api_client, indicateur_test_data):
        """#339 — une métrique de type « Indéterminé » peut être créée sans intitulé."""
        type_indet = NomenclatureTypeMetriqueFactory(
            cd_nomenclature='INDETERMINE', mnemonique='INDETERMINE', label='Indéterminé'
        )
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': '',
            'type_metrique': type_indet.id_nomenclature,
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Metrique.objects.filter(
            id_indicateur=indicateur_test_data['indicateur1'], nom_metrique=''
        ).exists()

    def test_create_non_indetermine_requires_name(self, api_client, indicateur_test_data):
        """#339 — pour les autres types, l'intitulé reste obligatoire (400 sans nom)."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': '',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'nom_metrique' in response.data

    def test_create_with_seuils(self, api_client, indicateur_test_data):
        """Test create a metrique with score thresholds."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': 'Métrique Seuils',
            'unite': '%',
            'score_1_inf': '0.0000',
            'score_1_sup': '20.0000',
            'score_1_label': 'Très mauvais',
            'score_2_inf': '20.0000',
            'score_2_sup': '40.0000',
            'score_2_label': 'Mauvais',
            'score_3_inf': '40.0000',
            'score_3_sup': '60.0000',
            'score_3_label': 'Moyen',
            'score_4_inf': '60.0000',
            'score_4_sup': '80.0000',
            'score_4_label': 'Bon',
            'score_5_inf': '80.0000',
            'score_5_sup': '100.0000',
            'score_5_label': 'Très bon',
        })
        assert response.status_code == status.HTTP_201_CREATED
        metrique = Metrique.objects.get(nom_metrique='Métrique Seuils')
        assert metrique.score_1_label == 'Très mauvais'
        assert metrique.score_5_label == 'Très bon'
        # New fields should have defaults
        assert metrique.sens_variation == 'CROISSANT'
        assert metrique.score_1_sup_inclusive is True
        assert metrique.score_2_sup_inclusive is True
        assert metrique.score_3_sup_inclusive is True
        assert metrique.score_4_sup_inclusive is True
        assert metrique.has_borne_score1 is False
        assert metrique.has_borne_score5 is False

    def test_create_with_direction_and_inclusivity(self, api_client, indicateur_test_data):
        """Test create a metrique with explicit sens_variation and inclusivity fields."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': 'Métrique Décroissante',
            'unite': 'mg/L',
            'sens_variation': 'DECROISSANT',
            'score_1_sup_inclusive': False,
            'score_2_sup_inclusive': True,
            'score_3_sup_inclusive': False,
            'score_4_sup_inclusive': True,
            'has_borne_score1': True,
            'has_borne_score5': False,
            'score_1_inf': '10.0000',
            'score_1_sup': '25.0000',
            'score_2_inf': '0.0000',
            'score_2_sup': '10.0000',
        })
        assert response.status_code == status.HTTP_201_CREATED
        metrique = Metrique.objects.get(nom_metrique='Métrique Décroissante')
        assert metrique.sens_variation == 'DECROISSANT'
        assert metrique.score_1_sup_inclusive is False
        assert metrique.score_2_sup_inclusive is True
        assert metrique.score_3_sup_inclusive is False
        assert metrique.score_4_sup_inclusive is True
        assert metrique.has_borne_score1 is True
        assert metrique.has_borne_score5 is False

    def test_create_with_bloc_intitule_and_block_labels(self, api_client, indicateur_test_data):
        """Métriques multi-blocs : intitulé/unité par bloc (principal + complémentaire)."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': 'État de la végétation',
            'bloc_intitule': 'hauteur',
            'unite': 'm',
            'score_1_inf': '0.0000', 'score_1_sup': '10.0000',
            'score_blocks': [{
                'position': 1,
                'intitule': 'recouvrement',
                'unite': '%',
                'logical_op': 'OR',
                'sens_variation': 'CROISSANT',
                'score_1_inf': '0.0000', 'score_1_sup': '20.0000',
            }],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED, response.data
        met = Metrique.objects.get(nom_metrique='État de la végétation')
        assert met.bloc_intitule == 'hauteur'
        block = met.score_blocks.get(position=1)
        assert block.intitule == 'recouvrement'
        assert block.unite == '%'
        detail = api_client.get(f'/api/plans/metriques/{met.id_metrique}/')
        assert detail.status_code == status.HTTP_200_OK
        assert detail.data['bloc_intitule'] == 'hauteur'
        assert detail.data['score_blocks'][0]['intitule'] == 'recouvrement'
        assert detail.data['score_blocks'][0]['unite'] == '%'

    def test_chiffre_active_level_requires_value(self, api_client, indicateur_test_data):
        """Chiffre : un niveau actif sans valeur → 400 (saisie obligatoire)."""
        type_chiffre = NomenclatureTypeMetriqueFactory(
            cd_nomenclature='CHIFFRE', mnemonique='CHIFFRE', label='Chiffre'
        )
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': 'Chiffre incomplet',
            'type_metrique': type_chiffre.id_nomenclature,
            'score_1_val': '1.0000',
            # score_2_val manquant alors que le niveau 2 est actif
            'score_3_val': '3.0000',
            'score_4_val': '4.0000',
            'score_5_val': '5.0000',
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'score_2_val' in response.data

    def test_chiffre_inactive_level_not_required(self, api_client, indicateur_test_data):
        """Chiffre : un niveau marqué « non utilisé » n'a pas besoin de valeur → 201."""
        type_chiffre = NomenclatureTypeMetriqueFactory(
            cd_nomenclature='CHIFFRE', mnemonique='CHIFFRE', label='Chiffre'
        )
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': 'Chiffre niveau 2 non utilisé',
            'type_metrique': type_chiffre.id_nomenclature,
            'inactive_levels': [2],
            'score_1_val': '1.0000',
            'score_3_val': '3.0000',
            'score_4_val': '4.0000',
            'score_5_val': '5.0000',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED, response.data

    def test_texte_active_level_requires_label(self, api_client, indicateur_test_data):
        """Texte : un niveau actif sans libellé → 400."""
        type_texte = NomenclatureTypeMetriqueFactory(
            cd_nomenclature='TEXTE', mnemonique='TEXTE', label='Texte'
        )
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': 'Texte incomplet',
            'type_metrique': type_texte.id_nomenclature,
            'score_1_label': 'Mauvais',
            'score_2_label': 'Moyen',
            # niveaux 3/4/5 actifs mais sans libellé
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'score_3_label' in response.data

    def test_create_without_unite(self, api_client, indicateur_test_data):
        """L'unité de la métrique est optionnelle (création sans unité acceptée)."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': 'Métrique sans unité',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED, response.data
        met = Metrique.objects.get(nom_metrique='Métrique sans unité')
        assert not met.unite

    def test_non_referent_denied(self, api_client, indicateur_test_data):
        """Test non-referent cannot create."""
        api_client.force_authenticate(user=indicateur_test_data['user'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': 'Should Fail',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_audit_fields_set(self, api_client, indicateur_test_data):
        """Test audit fields are set on create."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.post('/api/plans/metriques/', {
            'id_indicateur': indicateur_test_data['indicateur1'].id_indicateur,
            'nom_metrique': 'Métrique Audit',
        })
        assert response.status_code == status.HTTP_201_CREATED
        met = Metrique.objects.get(nom_metrique='Métrique Audit')
        assert met.id_utilisateur_ajout == indicateur_test_data['super_admin']


# =============================================================================
# Metrique by-indicateur endpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestMetriqueByIndicateur:
    """Tests for GET /api/plans/metriques/by-indicateur/{indicateur_id}/"""

    def test_unauthenticated_returns_401(self, api_client, indicateur_test_data):
        """Test unauthenticated access returns 401."""
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/metriques/by-indicateur/{ind_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_referent_gets_by_indicateur(self, api_client, indicateur_test_data):
        """Test referent can get metriques by indicateur."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/metriques/by-indicateur/{ind_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['indicateur_id'] == ind_id

    def test_response_structure(self, api_client, indicateur_test_data):
        """Test response has correct structure."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/metriques/by-indicateur/{ind_id}/')
        assert 'indicateur_id' in response.data
        assert 'indicateur_nom' in response.data
        assert 'metriques' in response.data
        assert 'total' in response.data

    def test_nonexistent_indicateur_returns_404(self, api_client, indicateur_test_data):
        """Test nonexistent indicateur returns 404."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.get('/api/plans/metriques/by-indicateur/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Mesure CRUD
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestMesureCreate:
    """Tests for POST /api/plans/mesures/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/mesures/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_referent_creates(self, api_client, indicateur_test_data):
        """Test referent can create a mesure."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        response = api_client.post('/api/plans/mesures/', {
            'id_metrique': indicateur_test_data['metrique1'].id_metrique,
            'valeur': '95.0',
            'date_mesure': '2025-06-15',
            'commentaire': 'Mesure de test',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Mesure.objects.filter(valeur='95.0').exists()

    def test_non_referent_denied(self, api_client, indicateur_test_data):
        """Test non-referent cannot create."""
        api_client.force_authenticate(user=indicateur_test_data['user'])
        response = api_client.post('/api/plans/mesures/', {
            'id_metrique': indicateur_test_data['metrique1'].id_metrique,
            'valeur': '50',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_audit_fields_set(self, api_client, indicateur_test_data):
        """Test audit fields are set on create."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.post('/api/plans/mesures/', {
            'id_metrique': indicateur_test_data['metrique1'].id_metrique,
            'valeur': '88',
        })
        assert response.status_code == status.HTTP_201_CREATED
        mes = Mesure.objects.get(valeur='88')
        assert mes.id_utilisateur_ajout == indicateur_test_data['super_admin']


# =============================================================================
# Mesure by-metrique endpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestMesureByMetrique:
    """Tests for GET /api/plans/mesures/by-metrique/{metrique_id}/"""

    def test_unauthenticated_returns_401(self, api_client, indicateur_test_data):
        """Test unauthenticated access returns 401."""
        met_id = indicateur_test_data['metrique1'].id_metrique
        response = api_client.get(f'/api/plans/mesures/by-metrique/{met_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_referent_gets_by_metrique(self, api_client, indicateur_test_data):
        """Test referent can get mesures by metrique."""
        api_client.force_authenticate(user=indicateur_test_data['referent'])
        met_id = indicateur_test_data['metrique1'].id_metrique
        response = api_client.get(f'/api/plans/mesures/by-metrique/{met_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['metrique_id'] == met_id

    def test_response_structure(self, api_client, indicateur_test_data):
        """Test response has correct structure."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        met_id = indicateur_test_data['metrique1'].id_metrique
        response = api_client.get(f'/api/plans/mesures/by-metrique/{met_id}/')
        assert 'metrique_id' in response.data
        assert 'metrique_nom' in response.data
        assert 'mesures' in response.data
        assert 'total' in response.data

    def test_nonexistent_metrique_returns_404(self, api_client, indicateur_test_data):
        """Test nonexistent metrique returns 404."""
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.get('/api/plans/mesures/by-metrique/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Cascade delete tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestCascadeDelete:
    """Tests for cascade deletion across the full hierarchy."""

    def test_delete_indicateur_cascades_metriques(self, api_client, indicateur_test_data):
        """Test deleting indicateur cascades to metriques."""
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/indicateurs/{ind_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Metrique.objects.filter(id_indicateur_id=ind_id).exists()

    def test_delete_indicateur_cascades_mesures(self, api_client, indicateur_test_data):
        """Test deleting indicateur cascades through metriques to mesures."""
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        met_id = indicateur_test_data['metrique1'].id_metrique
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/indicateurs/{ind_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Mesure.objects.filter(id_metrique_id=met_id).exists()

    def test_delete_metrique_cascades_mesures(self, api_client, indicateur_test_data):
        """Test deleting metrique cascades to mesures."""
        met_id = indicateur_test_data['metrique1'].id_metrique
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/metriques/{met_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Mesure.objects.filter(id_metrique_id=met_id).exists()

    def test_delete_metrique_keeps_indicateur(self, api_client, indicateur_test_data):
        """Test deleting metrique does not delete parent indicateur."""
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        met_id = indicateur_test_data['metrique2'].id_metrique
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/metriques/{met_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Indicateur.objects.filter(id_indicateur=ind_id).exists()

    def test_delete_mesure_keeps_metrique(self, api_client, indicateur_test_data):
        """Test deleting mesure does not delete parent metrique."""
        met_id = indicateur_test_data['metrique1'].id_metrique
        mes_id = indicateur_test_data['mesure1'].id_mesure
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/mesures/{mes_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Metrique.objects.filter(id_metrique=met_id).exists()

    def test_delete_ne_cascades_to_indicateurs(self, api_client, indicateur_test_data):
        """Test deleting NE cascades to indicateurs, metriques, and mesures."""
        ne_id = indicateur_test_data['ne1'].id_ne
        ind_id = indicateur_test_data['indicateur1'].id_indicateur
        met_id = indicateur_test_data['metrique1'].id_metrique
        api_client.force_authenticate(user=indicateur_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/niveaux-exigence/{ne_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Indicateur.objects.filter(id_indicateur=ind_id).exists()
        assert not Metrique.objects.filter(id_metrique=met_id).exists()
        assert not Mesure.objects.filter(id_metrique_id=met_id).exists()
