"""
Tests du registre des instances (#636).

Le registre remplace les jetons lus dans l'environnement. Ce qu'il faut
vérifier n'est donc pas seulement qu'il fonctionne, mais qu'il **prend le
dessus** : une révocation qui laisserait passer un jeton d'environnement oublié
dans un fichier de déploiement ne révoquerait rien.
"""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.index.models import Instance, PlanIndexe

pytestmark = pytest.mark.django_db


@pytest.fixture
def rnf():
    """Une instance enrôlée, avec ses deux jetons."""
    instance = Instance(instance_id='rnf', libelle='Réserves Naturelles de France')
    jetons = {
        'depot': instance.poser_jeton(Instance.USAGE_DEPOT),
        'lecture': instance.poser_jeton(Instance.USAGE_LECTURE),
    }
    instance.save()
    return instance, jetons


def ouvrir_lot(client, jeton):
    return client.post(
        '/api/federation/lots/',
        data={'format_version': 1},
        content_type='application/json',
        HTTP_X_FEDERATION_TOKEN=jeton,
    )


class TestIdentification:
    def test_le_jeton_retrouve_son_instance(self, rnf):
        _, jetons = rnf
        assert Instance.identifier(jetons['depot'], Instance.USAGE_DEPOT) == 'rnf'

    def test_un_jeton_ne_vaut_que_pour_son_usage(self, rnf):
        """
        Déposer et lire sont deux droits distincts : présenter le jeton de
        lecture à l'API de dépôt ne doit pas ouvrir de lot.
        """
        _, jetons = rnf
        assert Instance.identifier(jetons['lecture'], Instance.USAGE_DEPOT) is None

    def test_le_jeton_n_est_pas_stocke_en_clair(self, rnf):
        instance, jetons = rnf
        assert jetons['depot'] not in instance.empreinte_depot
        assert len(instance.empreinte_depot) == 64

    def test_une_instance_desactivee_n_est_plus_reconnue(self, rnf):
        instance, jetons = rnf
        instance.active = False
        instance.save()
        assert Instance.identifier(jetons['depot'], Instance.USAGE_DEPOT) is None

    def test_un_renouvellement_invalide_l_ancien_jeton(self, rnf):
        instance, jetons = rnf
        ancien = jetons['depot']
        nouveau = instance.poser_jeton(Instance.USAGE_DEPOT)
        instance.save()

        assert Instance.identifier(ancien, Instance.USAGE_DEPOT) is None
        assert Instance.identifier(nouveau, Instance.USAGE_DEPOT) == 'rnf'


class TestPreseanceSurLEnvironnement:
    """
    Le registre fait foi. L'environnement n'est qu'une amorce, et seulement pour
    une instance qu'il ne connaît pas.
    """

    def test_l_environnement_amorce_une_instance_absente_du_registre(
        self, client, settings
    ):
        settings.HUB_FEDERATION_TOKENS = {'cen': 'jeton-cen'}
        reponse = ouvrir_lot(client, 'jeton-cen')
        assert reponse.status_code == 201
        assert reponse.json()['instance_id'] == 'cen'

    def test_l_environnement_ne_rattrape_pas_un_jeton_revoque(
        self, client, settings, rnf
    ):
        """
        Le cas qui justifie toute la règle : l'instance est enrôlée, son jeton a
        été renouvelé, mais l'ancien traîne encore dans un fichier
        d'environnement. Il doit être refusé.
        """
        settings.HUB_FEDERATION_TOKENS = {'rnf': 'ancien-jeton-rnf'}
        assert ouvrir_lot(client, 'ancien-jeton-rnf').status_code == 403

    def test_l_environnement_ne_reactive_pas_une_instance_suspendue(
        self, client, settings, rnf
    ):
        instance, _ = rnf
        instance.active = False
        instance.save()
        settings.HUB_FEDERATION_TOKENS = {'rnf': 'jeton-rnf'}
        assert ouvrir_lot(client, 'jeton-rnf').status_code == 403

    def test_le_jeton_du_registre_ouvre_un_lot(self, client, settings, rnf):
        settings.HUB_FEDERATION_TOKENS = {}
        _, jetons = rnf
        reponse = ouvrir_lot(client, jetons['depot'])
        assert reponse.status_code == 201
        assert reponse.json()['instance_id'] == 'rnf'


class TestLectureParLeRegistre:
    def test_la_reciprocite_s_applique_aussi_aux_instances_enrolees(
        self, client, settings, rnf
    ):
        """
        Être enrôlé n'est pas publier. Une instance qui n'a rien déposé ne lit
        pas, quel que soit l'endroit d'où vient son jeton.
        """
        settings.HUB_READ_TOKENS = {}
        _, jetons = rnf
        reponse = client.get(
            '/api/exploration/contenus/', HTTP_X_HUB_TOKEN=jetons['lecture']
        )
        assert reponse.status_code == 403

    def test_une_instance_enrolee_qui_publie_peut_lire(
        self, client, settings, rnf, plan
    ):
        settings.HUB_READ_TOKENS = {}
        _, jetons = rnf
        reponse = client.get(
            '/api/exploration/contenus/', HTTP_X_HUB_TOKEN=jetons['lecture']
        )
        assert reponse.status_code == 200


class TestVueDuRegistre:
    def test_sans_jeton_le_registre_est_refuse(self, client):
        assert client.get('/api/federation/instances/').status_code == 403

    def test_un_jeton_de_depot_suffit_a_consulter(self, client, settings, rnf):
        settings.HUB_FEDERATION_TOKENS = {}
        _, jetons = rnf
        reponse = client.get(
            '/api/federation/instances/', HTTP_X_FEDERATION_TOKEN=jetons['depot']
        )
        assert reponse.status_code == 200

    def test_le_registre_expose_l_etat_de_publication(
        self, client, settings, rnf, plan
    ):
        settings.HUB_FEDERATION_TOKENS = {}
        _, jetons = rnf
        donnees = client.get(
            '/api/federation/instances/', HTTP_X_FEDERATION_TOKEN=jetons['depot']
        ).json()

        rnf_vue = next(i for i in donnees['instances'] if i['instance_id'] == 'rnf')
        assert rnf_vue['enrolee'] is True
        assert rnf_vue['libelle'] == 'Réserves Naturelles de France'
        assert rnf_vue['plans_publies'] == 1

    def test_une_instance_non_enrolee_figure_quand_meme(
        self, client, settings, rnf, plan
    ):
        """
        Sinon un hub à moitié migré paraîtrait vide, et la liste de ce qu'il
        reste à enrôler serait invisible.
        """
        settings.HUB_FEDERATION_TOKENS = {}
        PlanIndexe.objects.create(
            instance_id='cen', id_pg=7, slug='vercors', nom='Vercors',
            statut='valide',
        )
        _, jetons = rnf
        donnees = client.get(
            '/api/federation/instances/', HTTP_X_FEDERATION_TOKEN=jetons['depot']
        ).json()

        cen = next(i for i in donnees['instances'] if i['instance_id'] == 'cen')
        assert cen['enrolee'] is False
        assert cen['plans_publies'] == 1

    def test_aucun_jeton_ni_empreinte_ne_sort(self, client, settings, rnf):
        settings.HUB_FEDERATION_TOKENS = {}
        instance, jetons = rnf
        corps = client.get(
            '/api/federation/instances/', HTTP_X_FEDERATION_TOKEN=jetons['depot']
        ).content.decode()

        assert jetons['depot'] not in corps
        assert jetons['lecture'] not in corps
        # L'empreinte non plus : elle permettrait de vérifier hors ligne un
        # jeton deviné, sans que le hub ne journalise quoi que ce soit.
        assert instance.empreinte_depot not in corps


class TestCommandeEnrolement:
    def _appeler(self, *args, **options):
        sortie = StringIO()
        call_command('enroler_instance', *args, stdout=sortie, stderr=sortie, **options)
        return sortie.getvalue()

    def test_l_enrolement_cree_l_instance_et_affiche_ses_deux_jetons(self):
        sortie = self._appeler('cen-aura', '--libelle', 'CEN Auvergne')

        instance = Instance.objects.get(pk='cen-aura')
        assert instance.libelle == 'CEN Auvergne'
        assert instance.empreinte_depot and instance.empreinte_lecture
        assert 'dépôt' in sortie and 'lecture' in sortie

    def test_le_jeton_affiche_est_bien_celui_qui_authentifie(self):
        sortie = self._appeler('cen-aura')
        jeton = next(
            ligne.split(':', 1)[1].strip()
            for ligne in sortie.splitlines() if 'dépôt' in ligne and ':' in ligne
        )
        assert Instance.identifier(jeton, Instance.USAGE_DEPOT) == 'cen-aura'

    def test_un_identifiant_mal_forme_est_refuse(self):
        """
        Il entre dans la référence publique d'un plan et dans chaque ligne
        d'index : c'est le seul moment où l'erreur se corrige sans conséquence.
        """
        with pytest.raises(CommandError):
            self._appeler('CEN Auvergne')
        assert not Instance.objects.exists()

    def test_une_mise_a_jour_ne_renouvelle_pas_les_jetons(self):
        self._appeler('cen-aura')
        empreinte = Instance.objects.get(pk='cen-aura').empreinte_depot

        self._appeler('cen-aura', '--libelle', 'Nouveau nom')

        instance = Instance.objects.get(pk='cen-aura')
        assert instance.libelle == 'Nouveau nom'
        assert instance.empreinte_depot == empreinte

    def test_la_liste_signale_les_instances_qui_publient_sans_etre_enrolees(self):
        PlanIndexe.objects.create(
            instance_id='cen', id_pg=7, slug='vercors', nom='Vercors', statut='valide',
        )
        sortie = self._appeler('--lister')
        assert 'cen' in sortie
        assert 'environnement' in sortie
