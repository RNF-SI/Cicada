"""
Tests de l'enrôlement délégué à l'API de suivi RNF (#696).

L'API de suivi enrôle une instance dont RNF a accepté l'adhésion, en ne
transmettant que les empreintes des jetons que l'instance a tirés elle-même. Ce
qu'il faut vérifier : que la porte est fermée tant qu'elle n'est pas configurée,
qu'un réessai ne casse rien, qu'une instance existante n'est jamais dépossédée
de ses jetons — et, au bout du compte, que le jeton gardé par l'instance est
bien accepté par le hub.
"""

import pytest

from apps.index.federation import identifier_porteur
from apps.index.models import Instance

pytestmark = pytest.mark.django_db

URL = '/api/federation/enrolements/'
JETON_ADMIN = 'jeton-admin-du-suivi'


@pytest.fixture
def admin_configure(settings):
    settings.HUB_ADMIN_TOKEN = JETON_ADMIN


@pytest.fixture
def jetons():
    """Les deux jetons, tirés par l'instance : le hub n'en verra que l'empreinte."""
    return {
        'depot': Instance.nouveau_jeton(),
        'lecture': Instance.nouveau_jeton(),
    }


def corps(jetons, **surcharges):
    donnees = {
        'instance_id': 'cen-aura',
        'libelle': 'CEN Auvergne-Rhône-Alpes',
        'url_publique': 'https://cicada.cen-aura.fr',
        'empreinte_depot': Instance.empreinte(jetons['depot']),
        'empreinte_lecture': Instance.empreinte(jetons['lecture']),
    }
    donnees.update(surcharges)
    return donnees


def enroler(client, donnees, jeton=JETON_ADMIN):
    entetes = {'HTTP_X_HUB_ADMIN_TOKEN': jeton} if jeton is not None else {}
    return client.post(URL, data=donnees, content_type='application/json', **entetes)


class TestCreation:
    def test_cree_l_instance_avec_les_empreintes_fournies(
        self, client, admin_configure, jetons,
    ):
        reponse = enroler(client, corps(jetons))

        assert reponse.status_code == 201
        assert reponse.json() == {'instance_id': 'cen-aura', 'active': True, 'cree': True}
        instance = Instance.objects.get(pk='cen-aura')
        assert instance.libelle == 'CEN Auvergne-Rhône-Alpes'
        assert instance.url_publique == 'https://cicada.cen-aura.fr'
        assert instance.empreinte_depot == Instance.empreinte(jetons['depot'])
        assert instance.empreinte_lecture == Instance.empreinte(jetons['lecture'])
        assert instance.active

    def test_aucun_jeton_ni_empreinte_dans_la_reponse(
        self, client, admin_configure, jetons,
    ):
        contenu = enroler(client, corps(jetons)).content.decode()
        for jeton in jetons.values():
            assert jeton not in contenu
            assert Instance.empreinte(jeton) not in contenu

    def test_les_jetons_de_l_instance_sont_ensuite_acceptes(
        self, client, admin_configure, jetons,
    ):
        """Le bout de la chaîne : l'instance publie et lit avec ses propres jetons."""
        enroler(client, corps(jetons))

        assert identifier_porteur(jetons['depot'], Instance.USAGE_DEPOT) == (
            'cen-aura', 'registre',
        )
        assert identifier_porteur(jetons['lecture'], Instance.USAGE_LECTURE) == (
            'cen-aura', 'registre',
        )
        # Un usage ne vaut pas l'autre.
        assert identifier_porteur(jetons['lecture'], Instance.USAGE_DEPOT) == (None, None)

        ouverture = client.post(
            '/api/federation/lots/', data={'format_version': 1},
            content_type='application/json',
            HTTP_X_FEDERATION_TOKEN=jetons['depot'],
        )
        assert ouverture.status_code == 201

    def test_l_url_publique_est_facultative(self, client, admin_configure, jetons):
        donnees = corps(jetons)
        del donnees['url_publique']
        assert enroler(client, donnees).status_code == 201


class TestIdempotence:
    def test_un_reessai_avec_les_memes_empreintes_repond_200(
        self, client, admin_configure, jetons,
    ):
        assert enroler(client, corps(jetons)).status_code == 201

        reponse = enroler(client, corps(jetons))

        assert reponse.status_code == 200
        assert reponse.json() == {'instance_id': 'cen-aura', 'active': True, 'cree': False}
        assert Instance.objects.filter(pk='cen-aura').count() == 1

    def test_un_reessai_ne_reactive_pas_une_instance_suspendue(
        self, client, admin_configure, jetons,
    ):
        """Suspendre est une décision de RNF ; un réessai du suivi ne l'annule pas."""
        enroler(client, corps(jetons))
        Instance.objects.filter(pk='cen-aura').update(active=False)

        reponse = enroler(client, corps(jetons))

        assert reponse.status_code == 200
        assert reponse.json()['active'] is False
        assert not Instance.objects.get(pk='cen-aura').active


class TestConflit:
    def test_d_autres_empreintes_repondent_409_sans_rien_modifier(
        self, client, admin_configure, jetons,
    ):
        enroler(client, corps(jetons))
        autres = {'depot': Instance.nouveau_jeton(), 'lecture': Instance.nouveau_jeton()}

        reponse = enroler(client, corps(autres, libelle='Usurpateur'))

        assert reponse.status_code == 409
        assert 'detail' in reponse.json()
        instance = Instance.objects.get(pk='cen-aura')
        assert instance.libelle == 'CEN Auvergne-Rhône-Alpes'
        assert instance.empreinte_depot == Instance.empreinte(jetons['depot'])
        assert identifier_porteur(autres['depot'], Instance.USAGE_DEPOT) == (None, None)

    def test_une_instance_enrolee_a_la_main_n_est_pas_ecrasee(
        self, client, admin_configure, jetons,
    ):
        instance = Instance(instance_id='cen-aura', libelle='CEN')
        jeton_existant = instance.poser_jeton(Instance.USAGE_DEPOT)
        instance.poser_jeton(Instance.USAGE_LECTURE)
        instance.save()

        assert enroler(client, corps(jetons)).status_code == 409
        assert Instance.identifier(jeton_existant, Instance.USAGE_DEPOT) == 'cen-aura'


class TestAutorisation:
    def test_jeton_absent(self, client, admin_configure, jetons):
        assert enroler(client, corps(jetons), jeton=None).status_code == 403
        assert not Instance.objects.exists()

    def test_jeton_faux(self, client, admin_configure, jetons):
        assert enroler(client, corps(jetons), jeton='pas-le-bon').status_code == 403
        assert not Instance.objects.exists()

    def test_jeton_non_ascii(self, client, admin_configure, jetons):
        """Un en-tête fantaisiste produit un refus, pas une erreur serveur."""
        reponse = client.post(
            URL, data=corps(jetons), content_type='application/json',
            HTTP_X_HUB_ADMIN_TOKEN='jéton',
        )
        assert reponse.status_code == 403

    @pytest.mark.parametrize('presente', [None, '', JETON_ADMIN])
    def test_desactive_tant_que_non_configure(self, client, settings, jetons, presente):
        """Un réglage vide ferme la porte, même à qui présente un en-tête vide."""
        settings.HUB_ADMIN_TOKEN = ''
        assert enroler(client, corps(jetons), jeton=presente).status_code == 403
        assert not Instance.objects.exists()

    def test_les_jetons_d_instance_n_ouvrent_pas_l_enrolement(
        self, client, admin_configure, jetons,
    ):
        instance = Instance(instance_id='rnf')
        depot = instance.poser_jeton(Instance.USAGE_DEPOT)
        instance.save()

        reponse = client.post(
            URL, data=corps(jetons), content_type='application/json',
            HTTP_X_FEDERATION_TOKEN=depot,
        )
        assert reponse.status_code == 403

    def test_get_refuse(self, client, admin_configure):
        reponse = client.get(URL, HTTP_X_HUB_ADMIN_TOKEN=JETON_ADMIN)
        assert reponse.status_code == 405


class TestValidation:
    @pytest.mark.parametrize('surcharge', [
        {'instance_id': 'CEN_Aura'},
        {'instance_id': '-cen'},
        {'instance_id': ''},
        {'libelle': ''},
        {'empreinte_depot': 'abc'},
        {'empreinte_depot': 'A' * 64},
        {'empreinte_lecture': 'g' * 64},
        {'url_publique': 'pas une url'},
    ])
    def test_corps_invalide(self, client, admin_configure, jetons, surcharge):
        reponse = enroler(client, corps(jetons, **surcharge))
        assert reponse.status_code == 400
        assert not Instance.objects.exists()

    @pytest.mark.parametrize('champ', [
        'instance_id', 'libelle', 'empreinte_depot', 'empreinte_lecture',
    ])
    def test_champ_requis_manquant(self, client, admin_configure, jetons, champ):
        donnees = corps(jetons)
        del donnees[champ]
        assert enroler(client, donnees).status_code == 400

    def test_empreintes_identiques_refusees(self, client, admin_configure, jetons):
        empreinte = Instance.empreinte(jetons['depot'])
        reponse = enroler(
            client, corps(jetons, empreinte_depot=empreinte, empreinte_lecture=empreinte),
        )
        assert reponse.status_code == 400
