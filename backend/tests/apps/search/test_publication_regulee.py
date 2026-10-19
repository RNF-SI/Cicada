"""
#701 — Publication de nuit : étalement, relance, retard.

Toutes les instances publiaient à 2h30, sans relance : un hub saturé ou
redémarré à ce moment-là faisait attendre la nuit suivante, et une instance
malchanceuse pouvait rester périmée plusieurs nuits sans que personne le voie.
"""
from datetime import timedelta
from unittest.mock import patch

import pytest
import requests
from celery.exceptions import Retry
from django.core.management import call_command
from django.utils import timezone

from apps.search.models import PublicationHub
from apps.search.tasks import publier_vers_le_hub
from config.creneau import FENETRE_DEBUT, FENETRE_FIN, creneau_publication


@pytest.fixture(autouse=True)
def partage_consenti(db):
    from apps.core.models import SiteConfiguration
    return SiteConfiguration.objects.create(federation_partage=True)


@pytest.fixture
def hub(settings):
    settings.CICADA_HUB_URL = 'http://hub:8000'
    settings.CICADA_HUB_PUSH_TOKEN = 'jeton'
    settings.CICADA_HUB_PUSH_AUTO = True
    settings.CICADA_INSTANCE_LABEL = 'Réserves Naturelles de France'


def reponse(status, corps=None, entetes=None):
    r = type('R', (), {})()
    r.status_code = status
    r.headers = entetes or {}
    r.content = b'{}'
    r.text = str(corps)
    r.json = lambda: corps or {}
    return r


class TestCreneau:
    """Chaque instance a « son » créneau, sans coordination."""

    def test_stable_pour_une_meme_instance(self):
        assert creneau_publication('rnf') == creneau_publication('rnf')

    def test_dans_la_fenetre_de_nuit(self):
        for identifiant in ('rnf', 'cen-aura', 'dreal-na', 'local', 'x' * 64):
            heure, minute = creneau_publication(identifiant)
            assert FENETRE_DEBUT <= heure * 60 + minute < FENETRE_FIN, identifiant

    def test_des_instances_differentes_sont_etalees(self):
        creneaux = {creneau_publication(f'instance-{i}') for i in range(40)}
        heures = {h for h, _ in creneaux}
        assert len(creneaux) > 30
        assert len(heures) >= 3

    def test_la_planification_utilise_le_creneau_de_l_instance(self, settings):
        from django.conf import settings as reglages
        tache = reglages.CELERY_BEAT_SCHEDULE['push-federation']['schedule']
        heure, minute = creneau_publication(reglages.CICADA_INSTANCE_ID)
        assert tache.hour == {heure} and tache.minute == {minute}


@pytest.mark.django_db
class TestHubIndisponible:
    """Le hub répond « plus tard » (429), est en panne (5xx) ou injoignable."""

    def test_429_avec_retry_after(self, hub):
        from apps.search.management.commands.push_federation import HubIndisponible
        with patch('requests.request', return_value=reponse(429, {'retry_after': 600}, {'Retry-After': '600'})):
            from apps.search.management.commands.push_federation import Command
            commande = Command()
            commande.hub, commande.jeton = 'http://hub:8000', 'jeton'
            with pytest.raises(HubIndisponible) as exc:
                commande._appel('POST', '/api/federation/lots/', {})
        assert exc.value.retry_after == 600

    @pytest.mark.parametrize('cause', [
        reponse(503, 'maintenance'),
        requests.ConnectionError('injoignable'),
        requests.Timeout('trop long'),
    ])
    def test_panne_ou_reseau(self, hub, cause):
        from apps.search.management.commands.push_federation import Command, HubIndisponible
        commande = Command()
        commande.hub, commande.jeton = 'http://hub:8000', 'jeton'
        kwargs = {'side_effect': cause} if isinstance(cause, Exception) else {'return_value': cause}
        with patch('requests.request', **kwargs):
            with pytest.raises(HubIndisponible) as exc:
                commande._appel('POST', '/api/federation/lots/', {})
        assert exc.value.retry_after is None

    def test_une_requete_refusee_n_est_pas_une_indisponibilite(self, hub):
        """400 / 403 : réessayer ne changera rien."""
        from apps.search.management.commands.push_federation import Command, HubIndisponible
        commande = Command()
        commande.hub, commande.jeton = 'http://hub:8000', 'jeton'
        with patch('requests.request', return_value=reponse(403, 'jeton refusé')):
            with pytest.raises(Exception) as exc:
                commande._appel('POST', '/api/federation/lots/', {})
        assert not isinstance(exc.value, HubIndisponible)


@pytest.mark.django_db
class TestRelance:

    def test_429_relance_apres_le_delai_demande(self, hub):
        from apps.search.management.commands.push_federation import HubIndisponible
        with patch('apps.search.tasks.call_command',
                   side_effect=HubIndisponible("hub saturé", retry_after=600)), \
             patch.object(publier_vers_le_hub, 'retry', side_effect=Retry()) as relance:
            with pytest.raises(Retry):
                publier_vers_le_hub()
        assert relance.call_args.kwargs['countdown'] == 600

    def test_sans_retry_after_le_delai_croit(self, hub):
        from apps.search.management.commands.push_federation import HubIndisponible
        from apps.search.tasks import delai_relance
        assert delai_relance(0) < delai_relance(1) < delai_relance(2)
        assert delai_relance(20) == delai_relance(21)   # plafonné
        with patch('apps.search.tasks.call_command',
                   side_effect=HubIndisponible("hub en panne")), \
             patch.object(publier_vers_le_hub, 'retry', side_effect=Retry()) as relance:
            with pytest.raises(Retry):
                publier_vers_le_hub()
        assert relance.call_args.kwargs['countdown'] == delai_relance(0)

    def test_une_relance_s_inscrit_comme_telle(self, hub):
        publier_vers_le_hub.push_request(retries=2)
        try:
            with patch('apps.search.tasks.call_command') as commande:
                # `.run()` : l'appel direct empilerait un nouveau contexte
                # Celery, où le compteur de relances repart à zéro.
                publier_vers_le_hub.run()
        finally:
            publier_vers_le_hub.pop_request()
        assert commande.call_args.kwargs['origine'] == PublicationHub.ORIGINE_RELANCE

    def test_une_erreur_definitive_n_est_pas_relancee(self, hub):
        with patch('apps.search.tasks.call_command', side_effect=RuntimeError('jeton refusé')), \
             patch.object(publier_vers_le_hub, 'retry') as relance:
            with pytest.raises(RuntimeError):
                publier_vers_le_hub()
        relance.assert_not_called()

    def test_la_commande_consigne_l_echec_avec_son_origine(self, hub, db, site_indexe):
        with patch('requests.request', return_value=reponse(429, {}, {'Retry-After': '60'})):
            with pytest.raises(Exception):
                call_command('push_federation', origine='relance')
        derniere = PublicationHub.objects.first()
        assert derniere.origine == PublicationHub.ORIGINE_RELANCE
        assert derniere.resultat == PublicationHub.RESULTAT_ECHEC


@pytest.fixture
def site_indexe(db):
    from apps.search.indexing import index_plan
    from tests.factories import EnjeuFactory, PlanGestionFactory, SiteFactory
    site = SiteFactory(nom_site='Camargue', id_inpn='FR3600001')
    plan = PlanGestionFactory(statut='valide', nom='Plan de la Camargue', sites=[site])
    EnjeuFactory(id_pg=plan, libelle='Forêt alluviale')
    index_plan(plan)
    return plan


@pytest.mark.django_db
class TestRetard:
    """Diagnostic de la page Paramètres : plus de 48 h sans publication réussie."""

    def _publier(self, il_y_a, resultat=PublicationHub.RESULTAT_REUSSIE):
        p = PublicationHub.enregistrer(PublicationHub.ORIGINE_NUIT, resultat)
        PublicationHub.objects.filter(pk=p.pk).update(date=timezone.now() - il_y_a)

    def test_publication_en_retard_au_dela_de_48h(self, hub):
        from apps.search.raccordement import etat
        self._publier(timedelta(hours=60))
        diagnostic = etat(actualiser=False)['diagnostic']
        assert diagnostic['cle'] == 'publication_en_retard'
        assert diagnostic['niveau'] == 'attention'
        assert diagnostic['parametres']['depuis']

    def test_publication_recente_ok(self, hub):
        from apps.search.raccordement import etat
        self._publier(timedelta(hours=20))
        assert etat(actualiser=False)['diagnostic']['cle'] == 'ok'
