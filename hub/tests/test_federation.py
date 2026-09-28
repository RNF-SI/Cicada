"""
Tests du dépôt de l'index par les instances.

Ils portent sur trois choses, dans cet ordre d'importance :

1. **la purge ne déborde pas** — une instance ne peut pas dépublier une autre ;
2. **l'état fait foi** — ce qui n'est plus publié disparaît, sans message ;
3. **une publication interrompue ne détruit rien** — c'est la raison d'être du
   lot en trois temps.
"""

import pytest

from apps.index.models import ContenuIndexe, LotPublication, PlanIndexe

JETONS = {'rnf': 'jeton-rnf', 'cen': 'jeton-cen'}

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def jetons_configures(settings):
    """Deux instances autorisées à publier — le minimum pour tester le cloisonnement."""
    settings.HUB_FEDERATION_TOKENS = JETONS


def entetes(instance='rnf'):
    return {'HTTP_X_FEDERATION_TOKEN': JETONS[instance]}


def plan_charge(id_pg=1, nom='Plan de la Camargue', contenus=None, **kwargs):
    """
    Une charge utile de plan, telle qu'une instance en enverrait.

    Les `id_objet` par défaut sont dérivés de `id_pg` : chez l'émetteur, un
    identifiant d'enjeu est une séquence **globale**, pas une numérotation par
    plan. Deux plans ne peuvent donc pas porter un enjeu n° 1 chacun, et un jeu
    d'essai qui le supposerait ne testerait rien de réel.
    """
    charge = {
        'id_pg': id_pg,
        'nom': nom,
        'slug': f'plan-{id_pg}',
        'statut': 'valide',
        'annee_debut': 2020,
        'annee_fin': 2030,
        'type_site_codes': ['RNN'],
        'site_inpn_codes': ['FR3600001'],
        'contenus': contenus if contenus is not None else [
            {
                'type_contenu': 'enjeu',
                'id_objet': id_pg * 100 + 1,
                'titre': 'Forêt alluviale',
            },
        ],
    }
    charge.update(kwargs)
    return charge


class Publication:
    """Enchaîne les trois temps d'une publication, pour alléger les tests."""

    def __init__(self, client, instance='rnf'):
        self.client = client
        self.instance = instance

    def ouvrir(self, format_version=1):
        reponse = self.client.post(
            '/api/federation/lots/',
            {'format_version': format_version},
            content_type='application/json',
            **entetes(self.instance),
        )
        self.lot_id = reponse.json().get('lot_id')
        return reponse

    def deposer(self, *plans):
        return self.client.post(
            f'/api/federation/lots/{self.lot_id}/plans/',
            {'plans': list(plans)},
            content_type='application/json',
            **entetes(self.instance),
        )

    def basculer(self):
        return self.client.post(
            f'/api/federation/lots/{self.lot_id}/bascule/',
            content_type='application/json',
            **entetes(self.instance),
        )

    def publier(self, *plans):
        """Le cas nominal : ouvrir, déposer, basculer."""
        self.ouvrir()
        self.deposer(*plans)
        return self.basculer()


class TestAuthentification:
    def test_sans_jeton_le_depot_est_refuse(self, client):
        reponse = client.post(
            '/api/federation/lots/', {'format_version': 1},
            content_type='application/json',
        )
        assert reponse.status_code == 403

    def test_un_jeton_inconnu_est_refuse(self, client):
        reponse = client.post(
            '/api/federation/lots/', {'format_version': 1},
            content_type='application/json',
            HTTP_X_FEDERATION_TOKEN='jeton-invente',
        )
        assert reponse.status_code == 403

    def test_l_instance_vient_du_jeton_et_non_du_corps(self, client):
        """
        Déclarer `instance_id` dans la requête ne doit rien changer.

        Sinon n'importe quel porteur d'un jeton valide publierait — et purgerait
        — au nom de n'importe qui.
        """
        reponse = client.post(
            '/api/federation/lots/',
            {'format_version': 1, 'instance_id': 'cen'},
            content_type='application/json',
            **entetes('rnf'),
        )
        assert reponse.json()['instance_id'] == 'rnf'


class TestFormat:
    def test_un_format_inconnu_est_refuse_a_l_ouverture(self, client):
        """
        Refuser tôt, et explicitement.

        Les instances sont mises à jour indépendamment : un émetteur peut être
        en avance sur le hub. Mieux vaut refuser le lot que d'écrire des
        documents à moitié compris.
        """
        reponse = Publication(client).ouvrir(format_version=99)
        assert reponse.status_code == 400
        assert 'format' in str(reponse.json()).lower()


class TestIngestion:
    def test_un_plan_publie_est_consultable_avec_son_contenu(self, client):
        Publication(client).publier(plan_charge())

        plan = PlanIndexe.objects.get(instance_id='rnf', id_pg=1)
        assert plan.nom == 'Plan de la Camargue'
        assert plan.contenus.count() == 1
        assert plan.contenus.first().titre == 'Forêt alluviale'

    def test_les_facettes_du_plan_redescendent_sur_le_contenu(self, client):
        """
        Filtrer et compter par facette est l'opération la plus fréquente de
        l'exploration : les facettes sont dupliquées sur la ligne de contenu
        pour éviter une jointure par requête.
        """
        Publication(client).publier(plan_charge())

        contenu = ContenuIndexe.objects.get()
        assert contenu.statut_pg == 'valide'
        assert contenu.annee_debut == 2020
        assert contenu.type_site_codes == ['RNN']

    def test_republier_un_plan_remplace_son_contenu(self, client):
        """
        L'unité d'échange est le plan entier : un enjeu retiré chez l'émetteur
        disparaît parce qu'il n'est plus dans la liste, pas parce qu'un message
        l'a annoncé.
        """
        Publication(client).publier(plan_charge(contenus=[
            {'type_contenu': 'enjeu', 'id_objet': 1, 'titre': 'Gardé'},
            {'type_contenu': 'enjeu', 'id_objet': 2, 'titre': 'Retiré'},
        ]))
        Publication(client).publier(plan_charge(contenus=[
            {'type_contenu': 'enjeu', 'id_objet': 1, 'titre': 'Gardé'},
        ]))

        assert ContenuIndexe.objects.count() == 1
        assert ContenuIndexe.objects.get().titre == 'Gardé'

    def test_un_objet_qui_change_de_plan_ne_bloque_pas_la_page(self, client):
        """
        L'unicité du contenu est globale à l'instance, pas par plan : un
        identifiant d'enjeu est une séquence globale chez l'émetteur.

        Vider le contenu du plan courant ne suffit donc pas si l'objet est
        arrivé sous un *autre* plan — l'insertion violerait la contrainte et
        ferait échouer la page entière. Ce n'est pas censé arriver ; ça ne doit
        surtout pas bloquer une publication si ça arrive.
        """
        enjeu = {'type_contenu': 'enjeu', 'id_objet': 777, 'titre': 'Roselières'}

        Publication(client).publier(
            plan_charge(id_pg=1, contenus=[enjeu]),
            plan_charge(id_pg=2, contenus=[]),
        )
        # L'enjeu 777 passe du plan 1 au plan 2.
        Publication(client).publier(
            plan_charge(id_pg=1, contenus=[]),
            plan_charge(id_pg=2, contenus=[enjeu]),
        )

        contenu = ContenuIndexe.objects.get(id_objet=777)
        assert contenu.plan.id_pg == 2

    def test_les_organismes_restent_vides(self, client):
        """
        Faute d'identité nationale des organismes, la colonne reste vide.

        Recopier un identifiant local ferait matcher le mauvais organisme — une
        corruption silencieuse — là où un tableau vide produit une absence
        visible au filtrage.
        """
        Publication(client).publier(plan_charge(organisme_codes=['42']))

        assert PlanIndexe.objects.get().organisme_codes == []
        assert ContenuIndexe.objects.get().organisme_codes == []


class TestResolutionDesZones:
    def _zone(self, type_code, area_code, nom):
        from django.contrib.gis.geos import MultiPolygon, Polygon

        from apps.geo.models import AreaType, LArea

        carre = MultiPolygon(
            Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))), srid=4326
        )
        type_zone, _ = AreaType.objects.get_or_create(
            type_code=type_code, defaults={'type_name': type_code}
        )
        return LArea.objects.create(
            id_type=type_zone, area_code=area_code, area_name=nom, geom=carre
        )

    def test_les_codes_sont_retraduits_en_identifiants_locaux(self, client):
        """
        Le découpage administratif vient du même référentiel national partout :
        seuls les identifiants techniques diffèrent, pas les codes.
        """
        dep = self._zone('DEP', '13', 'Bouches-du-Rhône')
        Publication(client).publier(plan_charge(area_codes=['DEP:13']))

        assert PlanIndexe.objects.get().area_ids == [dep.id_area]
        assert ContenuIndexe.objects.get().area_ids == [dep.id_area]

    def test_le_type_evite_de_confondre_departement_et_region(self, client):
        """Un code de département et un code de région peuvent se ressembler."""
        self._zone('DEP', '93', 'Seine-Saint-Denis')
        region = self._zone('REG', '93', "Provence-Alpes-Côte d'Azur")

        Publication(client).publier(plan_charge(area_codes=['REG:93']))
        assert PlanIndexe.objects.get().area_ids == [region.id_area]

    def test_une_zone_inconnue_ne_se_resout_a_rien(self, client):
        """Le hub n'a pas à inventer une zone qu'il ne connaît pas."""
        Publication(client).publier(plan_charge(area_codes=['DEP:999']))
        assert PlanIndexe.objects.get().area_ids == []


class TestBascule:
    def test_un_plan_non_republie_disparait(self, client):
        """L'état fait foi : la dépublication n'a besoin d'aucun message."""
        Publication(client).publier(plan_charge(id_pg=1), plan_charge(id_pg=2))
        assert PlanIndexe.objects.count() == 2

        Publication(client).publier(plan_charge(id_pg=1))

        assert [p.id_pg for p in PlanIndexe.objects.all()] == [1]

    def test_le_contenu_suit_son_plan(self, client):
        Publication(client).publier(plan_charge(id_pg=1), plan_charge(id_pg=2))
        Publication(client).publier(plan_charge(id_pg=1))

        assert ContenuIndexe.objects.count() == 1

    def test_la_bascule_rend_le_compte_des_purges(self, client):
        Publication(client).publier(plan_charge(id_pg=1), plan_charge(id_pg=2))

        reponse = Publication(client).publier(plan_charge(id_pg=1))
        assert reponse.json()['plans_purges'] == 1

    def test_une_instance_ne_purge_pas_les_plans_d_une_autre(self, client):
        """
        L'invariant le plus important du module.

        Sans la borne sur l'instance, un jeton compromis suffirait à vider
        l'index entier en basculant un lot vide.
        """
        Publication(client, 'cen').publier(plan_charge(id_pg=1, nom='Plan CEN'))
        Publication(client, 'rnf').publier(plan_charge(id_pg=1, nom='Plan RNF'))

        # Le CEN republie à vide : seul son propre plan doit tomber.
        Publication(client, 'cen').publier()

        restants = PlanIndexe.objects.all()
        assert [(p.instance_id, p.nom) for p in restants] == [('rnf', 'Plan RNF')]

    def test_on_ne_peut_pas_basculer_le_lot_d_une_autre_instance(self, client):
        publication = Publication(client, 'rnf')
        publication.ouvrir()
        publication.deposer(plan_charge())

        pirate = Publication(client, 'cen')
        pirate.lot_id = publication.lot_id
        assert pirate.basculer().status_code == 404

    def test_un_lot_deja_bascule_ne_se_rebascule_pas(self, client):
        publication = Publication(client)
        publication.publier(plan_charge())
        assert publication.basculer().status_code == 404


class TestPublicationInterrompue:
    """La raison d'être du lot en trois temps."""

    def test_une_publication_sans_bascule_ne_purge_rien(self, client):
        """
        Une coupure en milieu d'envoi ne doit pas vider le hub de ce qui
        n'était pas encore arrivé.
        """
        Publication(client).publier(plan_charge(id_pg=1), plan_charge(id_pg=2))

        interrompue = Publication(client)
        interrompue.ouvrir()
        interrompue.deposer(plan_charge(id_pg=1))
        # …et le réseau tombe : pas de bascule.

        assert PlanIndexe.objects.count() == 2

    def test_un_lot_abandonne_ne_purge_rien(self, client):
        Publication(client).publier(plan_charge(id_pg=1), plan_charge(id_pg=2))

        abandonnee = Publication(client)
        abandonnee.ouvrir()
        abandonnee.deposer(plan_charge(id_pg=1))
        reponse = client.delete(
            f'/api/federation/lots/{abandonnee.lot_id}/', **entetes()
        )

        assert reponse.status_code == 204
        assert PlanIndexe.objects.count() == 2

    def test_la_bascule_suivante_rattrape_un_lot_abandonne(self, client):
        """
        Un lot abandonné ne laisse pas de trace durable : la publication
        suivante fait autorité sur tout l'état de l'instance.
        """
        Publication(client).publier(plan_charge(id_pg=1), plan_charge(id_pg=2))

        abandonnee = Publication(client)
        abandonnee.ouvrir()
        abandonnee.deposer(plan_charge(id_pg=1))
        client.delete(f'/api/federation/lots/{abandonnee.lot_id}/', **entetes())

        Publication(client).publier(plan_charge(id_pg=2))
        assert [p.id_pg for p in PlanIndexe.objects.all()] == [2]


class TestFiche:
    def test_la_fiche_est_stockee_telle_quelle(self, client):
        """
        Le hub ne l'inspecte pas : la valider reviendrait à recopier ici le
        schéma de la fiche de CICADA, et donc à le suivre à chaque évolution.
        """
        arbre = {
            'nom': 'Plan de la Camargue',
            'enjeux': [{'titre': 'Roselières', 'objectifs': [{'titre': 'OLT 1'}]}],
        }
        Publication(client).publier(plan_charge(fiche=arbre))

        assert PlanIndexe.objects.get().fiche == arbre

    def test_un_plan_sans_fiche_reste_publiable(self, client):
        """Un émetteur plus ancien peut ne pas encore l'envoyer."""
        Publication(client).publier(plan_charge())
        assert PlanIndexe.objects.get().fiche == {}


class TestJournalDesLots:
    def test_le_lot_garde_trace_de_ce_qui_a_ete_recu(self, client):
        Publication(client).publier(
            plan_charge(id_pg=1, contenus=[
                {'type_contenu': 'enjeu', 'id_objet': 1, 'titre': 'A'},
                {'type_contenu': 'action', 'id_objet': 2, 'titre': 'B'},
            ]),
            plan_charge(id_pg=2),
        )

        lot = LotPublication.objects.get()
        assert lot.etat == LotPublication.ETAT_BASCULE
        assert lot.plans_recus == 2
        assert lot.contenus_recus == 3
        assert lot.date_bascule is not None
