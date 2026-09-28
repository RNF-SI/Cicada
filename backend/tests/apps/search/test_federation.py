"""
Tests de la fédération de l'exploration (#636).

CICADA étant déployé en plusieurs instances, l'exploration centralisée agrège
des documents venus de bases différentes. Ce qui est vérifié ici, ce sont les
invariants qui font qu'une agrégation reste juste :

- deux instances peuvent avoir le **même** identifiant d'objet sans se marcher
  dessus (tous les identifiants de l'application sont des séquences locales) ;
- une instance ne publie que **ses** documents, pas ceux qu'elle a ingérés ;
- les facettes sans clé stable entre instances sont **vidées**, jamais recopiées
  telles quelles — une valeur fausse serait pire qu'une valeur absente ;
- une dépublication côté source **retire** bien le document du portail.
"""

import pytest
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.geo.models import AreaType, LArea
from apps.search.federation import contenu_depuis_document
from apps.search.indexing import index_plan
from apps.search.models import ContenuIndexe
from apps.search.serializers import ContenuResultatSerializer
from tests.factories.enjeux import EnjeuFactory
from tests.factories.plans import CorSitePgFactory, PlanGestionFactory
from tests.factories.users import RoleFactory, SiteFactory

URL_PUBLICATION = '/api/exploration/federation/documents/'
JETON = 'jeton-de-test'


def carre(xmin, ymin, xmax, ymax):
    return MultiPolygon(Polygon.from_bbox((xmin, ymin, xmax, ymax)), srid=4326)


@pytest.fixture
def zones(db):
    """Un département et sa région, tels qu'importés du référentiel national."""
    type_dep = AreaType.objects.create(
        type_code=AreaType.DEPARTEMENT, type_name='Département'
    )
    type_reg = AreaType.objects.create(
        type_code=AreaType.REGION, type_name='Région'
    )
    region = LArea.objects.create(
        id_type=type_reg, area_code='84', area_name='Région test',
        geom=carre(0, 0, 10, 10),
    )
    departement = LArea.objects.create(
        id_type=type_dep, area_code='69', area_name='Département test',
        geom=carre(0, 0, 5, 5), parent=region,
    )
    return {'region': region, 'departement': departement}


@pytest.fixture
def plan_indexe(db, settings):
    """Un plan validé, indexé sous l'identité de l'instance courante."""
    settings.CICADA_INSTANCE_ID = 'rnf'
    plan = PlanGestionFactory(statut='valide')
    CorSitePgFactory(plan_de_gestion=plan, site=SiteFactory(), rang=1)
    EnjeuFactory(id_pg=plan, libelle="Pelouse sèche du causse")
    index_plan(plan)
    return plan


@pytest.fixture
def client_federation(settings):
    settings.CICADA_FEDERATION_TOKEN = JETON
    return APIClient()


# --------------------------------------------------------------------------- #
# Publication
# --------------------------------------------------------------------------- #

class TestPublication:
    """L'endpoint que consomme le portail."""

    def test_sans_jeton_refuse(self, client_federation, plan_indexe):
        assert client_federation.get(URL_PUBLICATION).status_code == 401

    def test_mauvais_jeton_refuse(self, client_federation, plan_indexe):
        reponse = client_federation.get(
            URL_PUBLICATION, headers={'X-Federation-Token': 'faux'}
        )
        assert reponse.status_code == 401

    def test_aucun_jeton_configure_refuse_tout(self, settings, plan_indexe):
        """Une instance sans jeton ne publie rien — pas même à un appelant nu."""
        settings.CICADA_FEDERATION_TOKEN = ''
        reponse = APIClient().get(
            URL_PUBLICATION, headers={'X-Federation-Token': ''}
        )
        assert reponse.status_code == 401

    def test_publie_les_documents_locaux(self, client_federation, plan_indexe):
        reponse = client_federation.get(
            URL_PUBLICATION, headers={'X-Federation-Token': JETON}
        )
        assert reponse.status_code == 200
        assert reponse.data['instance_id'] == 'rnf'
        assert reponse.data['format_version'] == 1
        assert reponse.data['pagination']['count'] >= 1

    def test_ne_repropage_pas_les_documents_ingeres(
        self, client_federation, plan_indexe
    ):
        """
        La fédération est en étoile, pas en cascade.

        Si un portail repropageait ce qu'il a reçu, plus aucune instance ne
        ferait autorité sur un document — et le retirer deviendrait impossible.
        """
        ContenuIndexe.objects.create(
            instance_id='cen', type_contenu='enjeu', id_objet=999,
            titre="Enjeu venu d'ailleurs", statut_pg='valide',
        )
        reponse = client_federation.get(
            URL_PUBLICATION, headers={'X-Federation-Token': JETON},
        )
        origines = {doc['id_objet'] for doc in reponse.data['results']}
        assert 999 not in origines

    def test_emporte_le_bandeau_du_plan(self, client_federation, plan_indexe):
        """Le portail n'a pas le plan en base : l'affichage voyage avec le document."""
        reponse = client_federation.get(
            URL_PUBLICATION, headers={'X-Federation-Token': JETON}
        )
        plan = reponse.data['results'][0]['plan']
        assert plan['nom'] == plan_indexe.nom
        assert plan['slug'] == plan_indexe.slug
        assert 'sites' in plan

    def test_publie_les_zones_en_codes_et_non_en_identifiants(
        self, client_federation, settings, zones
    ):
        """
        `l_areas.id_area` est une séquence locale, `area_code` est le code INSEE.

        C'est le code qui voyage, préfixé de son type : un code de département et
        un code de région peuvent se ressembler.
        """
        settings.CICADA_INSTANCE_ID = 'rnf'
        plan = PlanGestionFactory(statut='valide')
        CorSitePgFactory(plan_de_gestion=plan, site=SiteFactory(), rang=1)
        EnjeuFactory(id_pg=plan, libelle="Enjeu situé")
        index_plan(plan)
        ContenuIndexe.objects.filter(id_pg=plan).update(
            area_ids=[zones['departement'].pk, zones['region'].pk]
        )

        reponse = client_federation.get(
            URL_PUBLICATION, headers={'X-Federation-Token': JETON}
        )
        codes = reponse.data['results'][0]['area_codes']
        assert set(codes) == {'DEP:69', 'REG:84'}

    def test_publie_les_sites_en_codes_inpn_et_jamais_en_identifiants(
        self, db, client_federation, settings
    ):
        """
        `id_site` est une séquence locale, `id_inpn` vient du référentiel national.

        L'identifiant local ne doit apparaître nulle part dans le document : il
        ne désigne rien chez le destinataire.
        """
        settings.CICADA_INSTANCE_ID = 'rnf'
        plan = PlanGestionFactory(statut='valide')
        CorSitePgFactory(
            plan_de_gestion=plan, site=SiteFactory(id_inpn='FR1100796'), rang=1,
        )
        EnjeuFactory(id_pg=plan, libelle="Enjeu d'un site identifié")
        index_plan(plan)

        reponse = client_federation.get(
            URL_PUBLICATION, headers={'X-Federation-Token': JETON}
        )
        document = reponse.data['results'][0]
        assert document['site_inpn_codes'] == ['FR1100796']
        assert 'site_ids' not in document

    def test_le_cout_en_requetes_ne_suit_pas_le_nombre_de_documents(
        self, db, client_federation, settings, zones
    ):
        """
        Traduire les codes document par document coûterait deux requêtes *par
        document* — un millier pour une page de 500, alors que l'index vise
        ~1,3 M de documents une fois les ~4 400 plans repris.

        Le nombre de plans est laissé constant : seul le nombre de documents
        varie, donc seul le coût de la traduction est mesuré.
        """
        settings.CICADA_INSTANCE_ID = 'rnf'
        plan = PlanGestionFactory(statut='valide')
        CorSitePgFactory(
            plan_de_gestion=plan, site=SiteFactory(id_inpn='FR1100796'), rang=1,
        )
        EnjeuFactory(id_pg=plan, libelle="Premier enjeu")
        index_plan(plan)
        ContenuIndexe.objects.filter(id_pg=plan).update(
            area_ids=[zones['departement'].pk, zones['region'].pk]
        )
        avec_un_document = self._requetes_de_publication(client_federation)

        for numero in range(5):
            EnjeuFactory(id_pg=plan, libelle=f"Enjeu supplémentaire {numero}")
        index_plan(plan)
        ContenuIndexe.objects.filter(id_pg=plan).update(
            area_ids=[zones['departement'].pk, zones['region'].pk]
        )
        assert ContenuIndexe.objects.count() == 6

        assert self._requetes_de_publication(client_federation) == avec_un_document

    def _requetes_de_publication(self, client):
        with CaptureQueriesContext(connection) as requetes:
            reponse = client.get(
                URL_PUBLICATION, headers={'X-Federation-Token': JETON}
            )
            assert reponse.status_code == 200
        return len(requetes)

    def test_un_site_sans_code_inpn_est_omis(self, db, client_federation, settings):
        """
        `id_inpn` est *nullable* : la couverture est partielle par construction.

        Sans code national il ne reste que l'identifiant local, qui ne veut rien
        dire ailleurs. Le site est donc passé sous silence plutôt que mal
        transmis — la liste publiée dit « ces sites-là », pas « seulement
        ceux-là ».
        """
        settings.CICADA_INSTANCE_ID = 'rnf'
        plan = PlanGestionFactory(statut='valide')
        CorSitePgFactory(
            plan_de_gestion=plan, site=SiteFactory(id_inpn='FR1100796'), rang=1,
        )
        CorSitePgFactory(
            plan_de_gestion=plan, site=SiteFactory(id_inpn=None), rang=2,
        )
        EnjeuFactory(id_pg=plan, libelle="Enjeu inter-sites")
        index_plan(plan)

        reponse = client_federation.get(
            URL_PUBLICATION, headers={'X-Federation-Token': JETON}
        )
        assert reponse.data['results'][0]['site_inpn_codes'] == ['FR1100796']


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #

class TestIngestion:
    """La transformation d'un document reçu en ligne d'index locale."""

    def document(self, **surcharges):
        base = {
            'type_contenu': 'enjeu', 'id_objet': 42,
            'titre': "Tourbière alcaline", 'description': '', 'contexte': '',
            'rattachements': '', 'parent_type': None, 'parent_libelle': None,
            'sous_type': 'ecologique', 'sous_type_libelle': None,
            'statut_pg': 'valide', 'annee_debut': 2020, 'annee_fin': 2030,
            'type_site_codes': ['RNN'], 'area_codes': [], 'site_inpn_codes': [],
            'plan': {'nom': 'PG distant', 'slug': 'pg-distant'},
        }
        base.update(surcharges)
        return base

    def test_le_plan_reste_nul_et_le_bandeau_est_conserve(self, db):
        contenu = contenu_depuis_document(self.document(), 'cen')
        assert contenu.id_pg is None
        assert contenu.plan_denorm['nom'] == 'PG distant'
        assert contenu.instance_id == 'cen'

    def test_les_organismes_sont_vides_faute_de_cle_stable(self, db):
        """
        Recopier un identifiant local ferait matcher le mauvais organisme.

        Un tableau vide produit une absence visible ; un identifiant recopié
        produirait une corruption silencieuse. Tant que l'identité nationale des
        organismes n'est pas tranchée (#636), c'est le seul comportement tenable.
        """
        contenu = contenu_depuis_document(self.document(), 'cen')
        assert contenu.organisme_ids == []

    def test_les_sites_sont_re_resolus_par_code_inpn(self, db):
        """
        Un code INPN désigne le même espace protégé dans toutes les instances.

        Quand le portail connaît déjà ce site — co-gestion, cas fréquent — le
        document distant se rattache au bon site local.
        """
        site = SiteFactory(id_inpn='FR1100796')
        contenu = contenu_depuis_document(
            self.document(site_inpn_codes=['FR1100796']), 'cen'
        )
        assert contenu.site_ids == [site.pk]

    def test_un_code_inpn_inconnu_ne_rattache_rien(self, db):
        """Le portail n'invente pas un site qu'il ne connaît pas."""
        SiteFactory(id_inpn='FR1100796')
        contenu = contenu_depuis_document(
            self.document(site_inpn_codes=['FR-INCONNU']), 'cen'
        )
        assert contenu.site_ids == []

    def test_un_document_sans_codes_sites_reste_ingerable(self, db):
        """
        Émetteur antérieur à l'ajout du champ (#636).

        Les instances sont mises à jour indépendamment : un champ optionnel
        absent doit dégrader vers « aucun rattachement », jamais faire échouer
        l'ingestion — c'est ce qui autorise à ne pas bumper `FORMAT_VERSION`
        pour un ajout purement additif.
        """
        document = self.document()
        document.pop('site_inpn_codes')
        contenu = contenu_depuis_document(document, 'cen')
        assert contenu.site_ids == []

    def test_les_mnemoniques_traversent_intactes(self, db):
        contenu = contenu_depuis_document(self.document(), 'cen')
        assert contenu.type_site_codes == ['RNN']
        assert contenu.statut_pg == 'valide'

    def test_les_zones_sont_re_resolues_en_identifiants_locaux(self, db, zones):
        """
        Le découpage administratif vient du même référentiel national partout :
        seuls les identifiants techniques diffèrent, pas les codes.
        """
        contenu = contenu_depuis_document(
            self.document(area_codes=['DEP:69', 'REG:84']), 'cen'
        )
        assert set(contenu.area_ids) == {
            zones['departement'].pk, zones['region'].pk
        }

    def test_un_code_inconnu_est_ignore_sans_planter(self, db, zones):
        contenu = contenu_depuis_document(
            self.document(area_codes=['DEP:999', 'REG:84']), 'cen'
        )
        assert contenu.area_ids == [zones['region'].pk]


# --------------------------------------------------------------------------- #
# Cohabitation dans l'index du portail
# --------------------------------------------------------------------------- #

class TestCohabitation:
    """Ce qui casserait sans `instance_id` dans la clé."""

    def test_deux_instances_peuvent_avoir_le_meme_identifiant_objet(self, db):
        """
        Le cas nominal, pas un cas limite : les identifiants sont des séquences
        locales, donc l'enjeu n° 1 existe dans **toutes** les instances.
        """
        for instance in ('rnf', 'cen'):
            ContenuIndexe.objects.create(
                instance_id=instance, type_contenu='enjeu', id_objet=1,
                titre=f"Enjeu n°1 de {instance}", statut_pg='valide',
            )
        assert ContenuIndexe.objects.filter(type_contenu='enjeu', id_objet=1).count() == 2

    def test_la_tuile_affiche_le_bandeau_recopie_pour_un_document_distant(self, db):
        contenu = ContenuIndexe.objects.create(
            instance_id='cen', type_contenu='enjeu', id_objet=7,
            titre="Enjeu distant", statut_pg='valide',
            plan_denorm={'nom': 'PG du CEN', 'slug': 'pg-du-cen'},
        )
        donnees = ContenuResultatSerializer(contenu).data
        assert donnees['instance_id'] == 'cen'
        assert donnees['plan']['nom'] == 'PG du CEN'

    def test_la_tuile_joint_le_plan_pour_un_document_local(self, plan_indexe):
        """Un document local garde la jointure à la lecture : rien ne peut se périmer."""
        contenu = ContenuIndexe.objects.filter(id_pg=plan_indexe).first()
        donnees = ContenuResultatSerializer(contenu).data
        assert donnees['plan']['nom'] == plan_indexe.nom

    def test_retirer_une_instance_ne_touche_pas_les_autres(self, db):
        for instance in ('rnf', 'cen'):
            ContenuIndexe.objects.create(
                instance_id=instance, type_contenu='enjeu', id_objet=1,
                titre=f"Enjeu de {instance}", statut_pg='valide',
            )
        ContenuIndexe.objects.filter(instance_id='cen').delete()
        restants = ContenuIndexe.objects.values_list('instance_id', flat=True)
        assert list(restants) == ['rnf']


@pytest.fixture
def client_connecte(db):
    client = APIClient()
    client.force_authenticate(RoleFactory())
    return client


class TestRechercheAgregee:
    """L'exploration du portail, une fois les documents ingérés."""

    def test_la_recherche_remonte_les_documents_des_deux_instances(
        self, db, client_connecte
    ):
        for instance in ('rnf', 'cen'):
            ContenuIndexe.objects.create(
                instance_id=instance, type_contenu='enjeu', id_objet=1,
                titre="Tourbière alcaline du Jura", statut_pg='valide',
                plan_denorm={'nom': f'PG {instance}'},
            )
        reponse = client_connecte.get('/api/exploration/contenus/?q=tourbiere')
        assert reponse.status_code == 200
        origines = {r['instance_id'] for r in reponse.data['results']}
        assert origines == {'rnf', 'cen'}
