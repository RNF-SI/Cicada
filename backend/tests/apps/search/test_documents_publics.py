"""
#747 — Les documents des plans sortent dans l'exploration.

Le hub ne stocke que l'**adresse** d'un document, jamais le fichier : la fiche
publiée porte un lien vers l'instance d'origine, qui sert le document sans
connexion. D'où trois règles verrouillées ici :

- l'adresse repose sur un identifiant aléatoire (`uuid_public`), pas sur la clé
  du fichier en base — quiconque la connaît peut télécharger le document ;
- l'accès anonyme fait partie du consentement au partage
  (`SiteConfiguration.federation_partage`) : décocher le partage le coupe ;
- un brouillon n'est pas explorable, ses documents non plus.
"""

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.core.models import SiteConfiguration
from apps.plans.models_enjeux import CorEnjeuFichier
from tests.factories.enjeux import EnjeuFactory
from tests.factories.plans import CorPgFichierFactory, PlanGestionFactory
from tests.factories.users import RoleFactory


def url_document(fichier):
    return f'/api/public/documents/{fichier.uuid_public}/'


def fiche_de(plan):
    client = APIClient()
    client.force_authenticate(RoleFactory())
    reponse = client.get(f'/api/exploration/plans/{plan.slug}/')
    assert reponse.status_code == 200
    return reponse.data


@pytest.fixture
def partage(db):
    return SiteConfiguration.objects.create(federation_partage=True)


@pytest.fixture
def document(db, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    (tmp_path / 'arrete.pdf').write_bytes(b'%PDF-1.4 arrete')
    plan = PlanGestionFactory(statut='valide')
    return CorPgFichierFactory(
        plan_de_gestion=plan, nom_fichier='arrete.pdf', chemin_fichier='arrete.pdf',
        titre='Arrêté préfectoral', type_fichier='document',
    )


@pytest.fixture
def document_enjeu(db, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    (tmp_path / 'coupe.png').write_bytes(b'PNG coupe')
    enjeu = EnjeuFactory(id_pg=PlanGestionFactory(statut='valide'))
    return CorEnjeuFichier.objects.create(
        id_enjeu=enjeu, support='numerique', nom_fichier='coupe.png',
        chemin_fichier='coupe.png', extension='.png', titre='Coupe géologique',
    )


class TestAdresseNonDevinable:

    def test_chaque_document_recoit_un_identifiant_aleatoire(self, document):
        autre = CorPgFichierFactory(plan_de_gestion=document.plan_de_gestion)
        assert document.uuid_public and autre.uuid_public
        assert document.uuid_public != autre.uuid_public
        assert str(document.pk) not in url_document(document).split('/')

    def test_la_cle_en_base_nouvre_rien(self, partage, document):
        reponse = APIClient().get(f'/api/public/documents/{document.pk}/')
        assert reponse.status_code == 404


class TestAccesSansConnexion:

    def test_document_du_plan_servi_sans_connexion(self, partage, document):
        reponse = APIClient().get(url_document(document))
        assert reponse.status_code == 200
        assert b''.join(reponse.streaming_content if reponse.streaming else [reponse.content]) == b'%PDF-1.4 arrete'
        assert 'arrete.pdf' in reponse['Content-Disposition']

    def test_document_dun_enjeu_servi_sans_connexion(self, partage, document_enjeu):
        reponse = APIClient().get(url_document(document_enjeu))
        assert reponse.status_code == 200

    def test_partage_decoche_coupe_lacces_anonyme(self, document):
        SiteConfiguration.objects.create(federation_partage=False)
        assert APIClient().get(url_document(document)).status_code == 404

    def test_sans_partage_un_utilisateur_de_linstance_y_accede(self, document):
        """L'exploration locale montre les documents de ses propres plans."""
        SiteConfiguration.objects.create(federation_partage=False)
        client = APIClient()
        client.force_authenticate(RoleFactory())
        assert client.get(url_document(document)).status_code == 200

    def test_brouillon_jamais_servi(self, partage, document):
        plan = document.plan_de_gestion
        plan.statut = 'draft'
        plan.save()
        assert APIClient().get(url_document(document)).status_code == 404


class TestDocumentsDansLaFiche:

    @override_settings(CICADA_PUBLIC_URL='https://cicada.rnf.fr/')
    def test_la_fiche_porte_ladresse_absolue_des_documents(
        self, partage, document, document_enjeu,
    ):
        fiche = fiche_de(document.plan_de_gestion)
        assert [d['titre'] for d in fiche['documents']] == ['Arrêté préfectoral']
        assert fiche['documents'][0]['url'] == (
            f'https://cicada.rnf.fr/api/public/documents/{document.uuid_public}/'
        )

        plan_enjeu = document_enjeu.id_enjeu.id_pg
        fiche = fiche_de(plan_enjeu)
        documents = fiche['enjeux'][0]['documents']
        assert documents[0]['titre'] == 'Coupe géologique'
        assert documents[0]['url'].endswith(f'/{document_enjeu.uuid_public}/')

    def test_document_papier_liste_sans_lien(self, partage, document_enjeu):
        CorEnjeuFichier.objects.create(
            id_enjeu=document_enjeu.id_enjeu, support='papier', titre='Carnet de terrain',
        )
        fiche = fiche_de(document_enjeu.id_enjeu.id_pg)
        papier = next(
            d for d in fiche['enjeux'][0]['documents'] if d['titre'] == 'Carnet de terrain'
        )
        assert papier['url'] is None
