"""
#715 — Un même suivi/inventaire se saisit à deux endroits : le module
Inventaires (`/api/inventaires/suivis/`) et la fiche d'une action CS
(`/api/plans/operations/`). Ces tests passent d'un module à l'autre et
vérifient qu'aucun des deux ne perd ni n'écrase ce que l'autre a saisi.
"""
import pytest
from django.core.management import call_command
from rest_framework import status

from apps.core.models import Nomenclature
from apps.plans.models_operations import Operation, SuiviInventaire
from tests.factories.users import SuperAdminFactory

SUIVIS = '/api/inventaires/suivis/'
OPERATIONS = '/api/plans/operations/'


def _type_action(code):
    return Nomenclature.objects.get(id_type__mnemonique='TYPE_ACTION', cd_nomenclature=code)


@pytest.fixture
def donnees(db, api_client):
    call_command('import_nomenclatures', '--force', verbosity=0)
    admin = SuperAdminFactory()
    api_client.force_authenticate(user=admin)
    return {
        'client': api_client,
        'cs8': _type_action('CS8'),
        'ip1': _type_action('IP1'),
    }


def _suivi_saisi_dans_l_inventaire(client, type_action):
    """Suivi complet saisi dans le module Inventaires : 2 protocoles, habitats."""
    resp = client.post(SUIVIS, {
        'intitule': 'Suivi des chiroptères',
        'id_type_action': type_action.id_nomenclature,
        'objectif_principal': 'OBJ_ETAT_CONSERVATION',
        'cibles_principales': 'HABITATS_VEGETATIONS',
        'habitat_ref': 'Prairies humides',
        'habitats': [{'cd_hab': 1234, 'lb_hab_fr': 'Prairies humides'}],
        'frequence_nombre': 1,
        'frequence_unite': 'AN',
        'protocoles': [
            {'protocole_dans_campanule': True, 'cd_protocole_campanule': 42,
             'protocole_campanule_nom': 'STOC', 'respect_protocole': True},
            {'protocole_dans_campanule': False, 'nom_protocole': 'Protocole local',
             'periode_suivi': 'AVRIL,MAI', 'documentation_disponible': True,
             'url_documentation': 'https://example.org/doc'},
        ],
    }, format='json')
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    return SuiviInventaire.objects.get(pk=resp.data['id_suivi_inventaire'])


def _action_cs(client, type_action, **extra):
    payload = {'libelle': 'Action de suivi', 'id_type_action': type_action.id_nomenclature}
    payload.update(extra)
    resp = client.post(OPERATIONS, payload, format='json')
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    return Operation.objects.get(pk=resp.data['id_operation'])


@pytest.mark.django_db
@pytest.mark.integration
class TestSuiviCreeDepuisUneAction:

    def test_le_suivi_prend_le_type_de_l_action(self, donnees):
        """Sans type, le suivi n'apparaît plus dans « Suivi existant ? »."""
        op = _action_cs(donnees['client'], donnees['cs8'], est_suivi_existant=False,
                        suivi_inventaire={'intitule': 'Inventaire des chauves-souris',
                                          'objectif_principal': 'OBJ_INVENTAIRE_INITIAL',
                                          'cibles_principales': 'ESPECES'})
        assert op.id_suivi.id_type_action == donnees['cs8']

        # Il est alors proposé aux autres actions CS8.
        resp = donnees['client'].get(SUIVIS, {'type_action_prefix': 'CS8'})
        ids = [s['id_suivi_inventaire'] for s in resp.data['results']]
        assert op.id_suivi_id in ids

    def test_le_type_est_aussi_pose_a_la_modification(self, donnees):
        op = _action_cs(donnees['client'], donnees['cs8'], est_suivi_existant=False,
                        suivi_inventaire={'intitule': 'Inventaire'})
        SuiviInventaire.objects.filter(pk=op.id_suivi_id).update(id_type_action=None)

        resp = donnees['client'].patch(f'{OPERATIONS}{op.pk}/', {
            'suivi_inventaire': {'intitule': 'Inventaire', 'id_type_action': donnees['cs8'].pk},
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK, resp.data
        op.id_suivi.refresh_from_db()
        assert op.id_suivi.id_type_action == donnees['cs8']


@pytest.mark.django_db
@pytest.mark.integration
class TestSuiviExistantRattacheAUneAction:

    def test_rattacher_puis_enregistrer_ne_touche_pas_au_suivi(self, donnees):
        client = donnees['client']
        suivi = _suivi_saisi_dans_l_inventaire(client, donnees['cs8'])
        avant = client.get(f'{SUIVIS}{suivi.pk}/').data

        op = _action_cs(client, donnees['cs8'], est_suivi_existant=True, id_suivi=suivi.pk)
        resp = client.patch(f'{OPERATIONS}{op.pk}/', {
            'libelle': 'Action renommée', 'est_suivi_existant': True, 'id_suivi': suivi.pk,
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK, resp.data

        apres = client.get(f'{SUIVIS}{suivi.pk}/').data
        for champ in ('intitule', 'id_type_action', 'objectif_principal', 'cibles_principales',
                      'habitat_ref', 'habitats', 'frequence_nombre', 'frequence_unite'):
            assert apres[champ] == avant[champ], champ
        assert [p['nom_protocole'] or p['protocole_campanule_nom'] for p in apres['protocoles']] \
            == ['STOC', 'Protocole local']
        assert apres['protocoles'][1]['periode_suivi'] == 'AVRIL,MAI'

    def test_repasser_a_non_cree_un_nouveau_suivi(self, donnees):
        """« Suivi existant ? » Oui → Non : l'ancien suivi, partagé, reste intact."""
        client = donnees['client']
        suivi = _suivi_saisi_dans_l_inventaire(client, donnees['cs8'])
        op = _action_cs(client, donnees['cs8'], est_suivi_existant=True, id_suivi=suivi.pk)
        autre = _action_cs(client, donnees['cs8'], est_suivi_existant=True, id_suivi=suivi.pk)

        resp = client.patch(f'{OPERATIONS}{op.pk}/', {
            'est_suivi_existant': False,
            'suivi_inventaire': {
                'intitule': 'Nouveau suivi',
                'objectif_principal': 'OBJ_INVENTAIRE_INITIAL',
                'cibles_principales': 'ESPECES',
                'protocoles': [{'protocole_dans_campanule': False, 'nom_protocole': 'Autre'}],
            },
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK, resp.data

        op.refresh_from_db()
        suivi.refresh_from_db()
        assert op.id_suivi_id != suivi.pk
        assert op.id_suivi.intitule == 'Nouveau suivi'
        assert suivi.intitule == 'Suivi des chiroptères'
        assert suivi.protocoles.count() == 2
        autre.refresh_from_db()
        assert autre.id_suivi_id == suivi.pk

    def test_modifier_son_propre_suivi_le_met_a_jour(self, donnees):
        """Une action qui a créé son suivi le modifie, sans en créer un autre."""
        client = donnees['client']
        op = _action_cs(client, donnees['cs8'], est_suivi_existant=False,
                        suivi_inventaire={'intitule': 'Inventaire'})
        suivi_id = op.id_suivi_id

        resp = client.patch(f'{OPERATIONS}{op.pk}/', {
            'est_suivi_existant': False,
            'suivi_inventaire': {'intitule': 'Inventaire renommé'},
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK, resp.data
        op.refresh_from_db()
        assert op.id_suivi_id == suivi_id
        assert op.id_suivi.intitule == 'Inventaire renommé'


@pytest.mark.django_db
@pytest.mark.integration
class TestActionQuiNEstPlusCS:

    def test_une_action_qui_n_est_plus_cs_se_detache_du_suivi(self, donnees):
        client = donnees['client']
        suivi = _suivi_saisi_dans_l_inventaire(client, donnees['cs8'])
        op = _action_cs(client, donnees['cs8'], est_suivi_existant=True, id_suivi=suivi.pk)

        # Le formulaire n'envoie plus rien sur le suivi quand l'action n'est pas CS.
        resp = client.patch(f'{OPERATIONS}{op.pk}/', {
            'id_type_action': donnees['ip1'].pk, 'est_suivi_existant': False,
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK, resp.data

        op.refresh_from_db()
        assert op.id_suivi is None
        assert op.est_suivi_existant is False
        assert SuiviInventaire.objects.filter(pk=suivi.pk).exists()

    def test_une_action_non_cs_n_accepte_pas_de_suivi(self, donnees):
        op = _action_cs(donnees['client'], donnees['ip1'], est_suivi_existant=False,
                        suivi_inventaire={'intitule': 'Ne devrait pas exister'})
        assert op.id_suivi is None
        assert not SuiviInventaire.objects.filter(intitule='Ne devrait pas exister').exists()


@pytest.mark.django_db
@pytest.mark.integration
class TestFicheDuSuivi:

    def test_la_fiche_expose_les_libelles(self, donnees):
        """La fiche du module Inventaires affichait les codes (OBJ_…, ESPECES)."""
        client = donnees['client']
        suivi = _suivi_saisi_dans_l_inventaire(client, donnees['cs8'])
        SuiviInventaire.objects.filter(pk=suivi.pk).update(
            objectif_secondaire='OBJ_INVENTAIRE_INITIAL', cible_secondaire='ESPECES',
            type_indicateur='ETAT')

        data = client.get(f'{SUIVIS}{suivi.pk}/').data
        assert data['objectif_principal_label'] == 'Etat de conservation des habitats et espèces'
        assert data['objectif_secondaire_label'] == 'Inventaire initial'
        assert data['cibles_principales_label'] == 'Habitats et végétations'
        assert data['cible_secondaire_label'] == 'Espèces et groupes taxonomiques'
        assert data['type_indicateur_label'] == 'État'
        assert data['frequence_unite_label'] == 'Ans'

    def test_la_fiche_action_voit_le_type_du_suivi(self, donnees):
        client = donnees['client']
        suivi = _suivi_saisi_dans_l_inventaire(client, donnees['cs8'])
        op = _action_cs(client, donnees['cs8'], est_suivi_existant=True, id_suivi=suivi.pk)
        data = client.get(f'{OPERATIONS}{op.pk}/').data
        assert data['suivi_inventaire']['id_type_action'] == donnees['cs8'].pk
