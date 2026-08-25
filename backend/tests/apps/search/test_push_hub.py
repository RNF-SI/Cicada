"""
Tests de la publication vers le hub et du relais de l'exploration (#636).

Le hub n'est pas lancé pendant ces tests : ce qui est vérifié ici est ce que
CICADA **construit** et **décide**, pas ce que le hub en fait — c'est l'objet de
la suite du hub. La frontière est le contrat d'échange.
"""

from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from apps.search.indexing import index_plan
from apps.search.push import charge_utile, plans_a_publier
from apps.search.serializers import prefetch_sites
from apps.search.tasks import publier_vers_le_hub
from tests.factories import (
    EnjeuFactory, PlanGestionFactory, SiteFactory, UserFactory,
)


@pytest.fixture(autouse=True)
def partage_consenti(db):
    """
    L'instance participe à l'exploration nationale (#636).

    Ce module teste la **mécanique** de publication et de relais, pas le
    consentement — celui-ci a ses propres tests dans
    `test_partage_federation.py`. Sans ce décor, tous les cas échoueraient sur
    le même refus et masqueraient ce qu'ils vérifient réellement.
    """
    from apps.core.models import SiteConfiguration

    return SiteConfiguration.objects.create(federation_partage=True)


@pytest.fixture
def site(db):
    """Un site portant un code INPN — seuls ceux-là sont publiables."""
    return SiteFactory(nom_site='Camargue', id_inpn='FR3600001')


@pytest.fixture
def plan_indexe(db, site):
    """
    Un plan validé, rattaché à un site, avec du contenu, et indexé.

    Le contenu n'est pas décoratif : un plan vide ne produit aucune ligne
    d'index, et la commande de dépôt refuse alors de publier (cf.
    `_verifier_index`). C'est l'état normal d'un plan explorable.
    """
    plan = PlanGestionFactory(
        statut='valide', nom='Plan de la Camargue', sites=[site],
    )
    EnjeuFactory(id_pg=plan, libelle='Forêt alluviale')
    index_plan(plan)
    return plan


@pytest.fixture
def plan_vide(db, site):
    """Un plan validé sans aucun contenu — il reste publiable, mais nu."""
    plan = PlanGestionFactory(statut='valide', nom='Plan vide', sites=[site])
    index_plan(plan)
    return plan


@pytest.mark.django_db
class TestPerimetreDePublication:
    def test_un_brouillon_n_est_pas_publiable(self):
        """
        Le hub ne doit jamais recevoir un plan que l'instance ne montrerait pas
        elle-même : le périmètre de publication est celui de l'indexation.
        """
        PlanGestionFactory(statut='draft')
        assert plans_a_publier().count() == 0

    def test_un_plan_valide_est_publiable(self, plan_indexe):
        assert list(plans_a_publier()) == [plan_indexe]

    def test_un_plan_archive_reste_publiable(self):
        """Un plan archivé reste explorable : c'est de la mémoire, pas du rebut."""
        PlanGestionFactory(statut='archive')
        assert plans_a_publier().count() == 1


@pytest.mark.django_db
class TestChargeUtile:
    def _charge(self, plan, **kwargs):
        plan = (
            plans_a_publier().prefetch_related(prefetch_sites()).get(pk=plan.pk)
        )
        return charge_utile(plan, **kwargs)

    def test_la_charge_porte_le_plan_et_son_contenu(self, plan_indexe):
        charge = self._charge(plan_indexe)

        assert charge['id_pg'] == plan_indexe.pk
        assert charge['nom'] == 'Plan de la Camargue'
        assert charge['statut'] == 'valide'
        assert isinstance(charge['contenus'], list)

    def test_aucun_identifiant_local_ne_voyage(self, plan_indexe):
        """
        Le cœur du problème de la fédération : `id_site`, `id_organisme` et
        `id_area` sont des séquences propres à cette base. Les transmettre
        ferait apparier les documents sur les mauvais objets à l'arrivée.
        """
        charge = self._charge(plan_indexe)

        assert 'site_ids' not in charge
        assert 'area_ids' not in charge
        assert 'organisme_ids' not in charge
        # Seuls des codes nationaux, et le nom de l'organisme pour l'affichage.
        assert 'area_codes' in charge
        assert 'site_inpn_codes' in charge
        assert 'gestionnaire_principal' in charge

    def test_les_zones_partent_en_codes_prefixes_par_leur_type(self, plan_indexe):
        """Un code de département et un code de région peuvent se ressembler."""
        from apps.geo.models import AreaType, CorSiteArea, LArea
        from django.contrib.gis.geos import MultiPolygon, Polygon

        carre = MultiPolygon(
            Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))), srid=4326
        )
        type_dep, _ = AreaType.objects.get_or_create(
            type_code=AreaType.DEPARTEMENT, defaults={'type_name': 'Département'}
        )
        zone = LArea.objects.create(
            id_type=type_dep, area_code='13', area_name='Bouches-du-Rhône', geom=carre
        )
        for lien in plan_indexe.sites.all():
            CorSiteArea.objects.create(id_site_id=lien.site_id, id_area=zone)

        assert self._charge(plan_indexe)['area_codes'] == ['DEP:13']

    def test_un_site_sans_code_inpn_n_est_pas_publie(self, db):
        """
        `id_inpn` est nullable, et beaucoup de sites n'en portent pas. Sans clé
        stable, les publier reviendrait à transmettre l'identifiant local que
        tout ce module s'attache à ne pas faire voyager. La liste publiée dit
        « ces sites-là », jamais « seulement ceux-là ».
        """
        sans_code = SiteFactory(nom_site='Site sans code INPN', id_inpn=None)
        plan = PlanGestionFactory(statut='valide', sites=[sans_code])
        index_plan(plan)

        charge = self._charge(plan)
        assert charge['site_inpn_codes'] == []
        # Il reste affiché sur la tuile : c'est le code qui manque, pas le site.
        assert [s['nom_site'] for s in charge['sites']] == ['Site sans code INPN']

    def test_un_plan_sans_contenu_publie_quand_meme_ses_facettes(self, plan_vide):
        """
        Les facettes viennent du plan, pas de ses lignes d'index.

        Un plan validé mais vide n'a aucune ligne : lire les facettes dessus le
        ferait disparaître de tous les filtres par zone ou par type d'aire
        protégée, alors qu'il doit rester trouvable en mode « plan de gestion ».
        """
        assert plan_vide.contenus_indexes.count() == 0

        charge = self._charge(plan_vide)
        assert charge['contenus'] == []
        assert charge['site_inpn_codes'] == ['FR3600001']

    def test_la_fiche_voyage_rendue(self, plan_indexe):
        """
        Un arbre JSON autonome, que le hub range sans l'inspecter — c'est ce qui
        lui évite de connaître les enjeux, les objectifs et les actions.
        """
        charge = self._charge(plan_indexe)

        assert 'fiche' in charge
        assert charge['fiche']['nom'] == 'Plan de la Camargue'
        assert 'enjeux' in charge['fiche']

    def test_la_fiche_peut_etre_omise(self, plan_indexe):
        """Une fiche mobilise des centaines d'objets : on doit pouvoir s'en passer."""
        assert 'fiche' not in self._charge(plan_indexe, avec_fiche=False)


@pytest.mark.django_db
class TestCommandeDeDepot:
    def test_sans_hub_configure_la_commande_refuse(self, plan_indexe, settings):
        settings.CICADA_HUB_URL = ''
        with pytest.raises(CommandError, match='hub'):
            call_command('push_federation')

    def test_sans_jeton_la_commande_refuse(self, plan_indexe, settings):
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_PUSH_TOKEN = ''
        with pytest.raises(CommandError, match='[jJ]eton'):
            call_command('push_federation')

    def test_un_index_vide_n_ouvre_aucun_lot(self, db, settings):
        """
        L'invariant qui évite l'accident : un dépôt vide **dépublierait** tout
        ce que le hub connaît de cette instance. Une instance dont l'index n'a
        pas encore été construit ne doit pas effacer sa propre publication.
        """
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'

        with patch('requests.request') as appel:
            call_command('push_federation')

        appel.assert_not_called()

    def test_un_index_construit_sous_une_autre_identite_est_refuse(
        self, plan_indexe, settings
    ):
        """
        Le garde-fou qui évite l'échec le plus sournois.

        La charge utile ne retient que les lignes portant l'identité de cette
        instance. Si l'index a été construit sous une autre — identité changée,
        ou restée vide avant d'être renseignée — le dépôt réussirait en
        déposant des plans **sans aucun document** : l'exploration les
        afficherait en mode « plan », mais aucune recherche de contenu ne les
        trouverait. Publier moins que rien, sans le dire.
        """
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'
        settings.CICADA_INSTANCE_ID = 'identite-changee'

        with patch('requests.request') as appel:
            with pytest.raises(CommandError, match='rebuild_search_index'):
                call_command('push_federation')

        appel.assert_not_called()

    def test_un_index_vide_est_refuse(self, db, site, settings):
        """Des plans explorables mais aucun document : l'index n'a pas été construit."""
        PlanGestionFactory(statut='valide', sites=[site])
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'

        with pytest.raises(CommandError, match='index local est vide'):
            call_command('push_federation')

    def test_le_dry_run_n_envoie_rien(self, plan_indexe):
        with patch('requests.request') as appel:
            call_command('push_federation', '--dry-run')

        appel.assert_not_called()

    def test_un_echec_en_cours_de_depot_abandonne_le_lot(self, plan_indexe, settings):
        """
        Entre « incomplet » et « périmé », c'est périmé qui est récupérable :
        basculer un état partiel dépublierait du contenu valide.
        """
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'

        appels = []

        def repondre(methode, url, **kwargs):
            appels.append((methode, url))
            reponse = type('R', (), {})()
            reponse.content = b'{}'
            reponse.json = lambda: {'lot_id': 'lot-1'}
            reponse.status_code = 201 if url.endswith('/lots/') else 500
            reponse.text = 'boom'
            return reponse

        with patch('requests.request', side_effect=repondre):
            with pytest.raises(CommandError):
                call_command('push_federation')

        assert ('DELETE', 'http://hub:8000/api/federation/lots/lot-1/') in appels
        assert not any('bascule' in url for _, url in appels)


@pytest.mark.django_db
class TestRelais:
    """Le basculement de l'exploration vers le hub."""

    @pytest.fixture
    def client_connecte(self):
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        return client

    def test_par_defaut_l_exploration_reste_locale(self, client_connecte, plan_indexe):
        with patch('apps.search.relay.requests.get') as appel:
            reponse = client_connecte.get('/api/exploration/contenus/')

        assert reponse.status_code == 200
        appel.assert_not_called()

    def test_active_le_relais_transmet_au_hub(self, client_connecte, settings):
        settings.CICADA_EXPLORATION_SOURCE = 'hub'
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_READ_TOKEN = 'jeton-lecture'

        attendu = {'results': [], 'compteurs': {'tout': 0}}
        with patch('apps.search.relay.requests.get') as appel:
            appel.return_value.status_code = 200
            appel.return_value.json.return_value = attendu
            reponse = client_connecte.get('/api/exploration/contenus/?q=foret')

        assert reponse.json() == attendu
        url, = appel.call_args[0]
        assert url == 'http://hub:8000/api/exploration/contenus/'
        assert appel.call_args[1]['params'] == {'q': ['foret']}

    def test_un_hub_injoignable_ne_retombe_pas_sur_l_index_local(
        self, client_connecte, plan_indexe, settings
    ):
        """
        Un repli silencieux servirait les résultats de cette seule instance sous
        une interface qui promet une recherche transverse : l'utilisateur
        conclurait que les plans des autres organismes n'existent pas.
        """
        import requests

        settings.CICADA_EXPLORATION_SOURCE = 'hub'
        settings.CICADA_HUB_URL = 'http://hub:8000'

        with patch(
            'apps.search.relay.requests.get',
            side_effect=requests.ConnectionError('injoignable'),
        ):
            reponse = client_connecte.get('/api/exploration/contenus/')

        assert reponse.status_code == 502
        assert 'indisponible' in reponse.json()['detail']

    def test_la_fiche_est_demandee_par_reference_complete(
        self, client_connecte, settings
    ):
        """
        Le frontend navigue encore par slug seul : un slug nu désigne donc un
        plan de cette instance, ce qui est vrai de tous les liens existants.
        """
        settings.CICADA_EXPLORATION_SOURCE = 'hub'
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_INSTANCE_ID = 'rnf'

        with patch('apps.search.relay.requests.get') as appel:
            appel.return_value.status_code = 200
            appel.return_value.json.return_value = {'fiche': {}}
            client_connecte.get('/api/exploration/plans/camargue/')

        url, = appel.call_args[0]
        assert url == 'http://hub:8000/api/exploration/plans/rnf:camargue/'

    def test_une_reference_deja_complete_est_transmise_telle_quelle(
        self, client_connecte, settings
    ):
        """Une tuile servie par le hub porte déjà l'instance du plan."""
        settings.CICADA_EXPLORATION_SOURCE = 'hub'
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_INSTANCE_ID = 'rnf'

        with patch('apps.search.relay.requests.get') as appel:
            appel.return_value.status_code = 200
            appel.return_value.json.return_value = {'fiche': {}}
            client_connecte.get('/api/exploration/plans/cen:vercors/')

        url, = appel.call_args[0]
        assert url == 'http://hub:8000/api/exploration/plans/cen:vercors/'


class TestPublicationPlanifiee:
    """
    La tâche de nuit (#636), et surtout ce qu'elle refuse de faire.

    Elle est planifiée sur **toutes** les instances, y compris celles qui ne
    fédèrent pas : ce qui la retient n'est donc pas l'absence de planification
    mais trois conditions distinctes, qui ne disent pas la même chose.
    """

    def test_sans_hub_configure_elle_ne_fait_rien(self, db, settings):
        settings.CICADA_HUB_URL = ''
        settings.CICADA_HUB_PUSH_TOKEN = ''

        with patch('apps.search.tasks.call_command') as commande:
            assert publier_vers_le_hub() == 'non configurée'
        commande.assert_not_called()

    def test_le_relais_seul_ne_declenche_pas_la_publication(self, db, settings):
        """
        Lire l'exploration nationale exige l'URL du hub. Une instance qui lit
        sans vouloir publier automatiquement doit pouvoir le dire, sinon
        configurer le relais publierait dans son dos.
        """
        settings.CICADA_HUB_URL = 'http://hub'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'
        settings.CICADA_HUB_PUSH_AUTO = False

        with patch('apps.search.tasks.call_command') as commande:
            assert publier_vers_le_hub() == 'non configurée'
        commande.assert_not_called()

    def test_sans_consentement_de_la_structure_rien_ne_part(
        self, db, settings, partage_consenti
    ):
        """
        Le consentement vit en base et peut être retiré entre deux nuits. La
        tâche doit alors s'arrêter **sans échouer** : un retrait assumé ne doit
        pas se signaler comme une panne.
        """
        settings.CICADA_HUB_URL = 'http://hub'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'
        partage_consenti.federation_partage = False
        partage_consenti.save()

        with patch('apps.search.tasks.call_command') as commande:
            assert publier_vers_le_hub() == 'partage désactivé'
        commande.assert_not_called()

    def test_les_trois_conditions_reunies_declenchent_le_depot(self, db, settings):
        settings.CICADA_HUB_URL = 'http://hub'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'
        settings.CICADA_HUB_PUSH_AUTO = True

        with patch('apps.search.tasks.call_command') as commande:
            publier_vers_le_hub()

        assert commande.call_args[0] == ('push_federation',)

    def test_un_echec_remonte_plutot_que_de_passer_inapercu(self, db, settings):
        """
        La commande a déjà abandonné son lot : la publication précédente est
        intacte. L'échec doit rester visible dans le journal des tâches — c'est
        le seul endroit où l'exploitant le verra, personne n'attendant devant
        une tâche de 2h30.
        """
        settings.CICADA_HUB_URL = 'http://hub'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'

        with patch('apps.search.tasks.call_command', side_effect=RuntimeError('hub muet')):
            with pytest.raises(RuntimeError):
                publier_vers_le_hub()
