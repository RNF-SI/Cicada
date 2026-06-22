"""
#237 — Tests des documents (numériques + références papier) d'un enjeu.

Couvre la validation du serializer, le stockage d'un fichier téléversé,
la référence papier sans fichier, et l'exposition via le serializer détail.
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.plans.models_enjeux import CorEnjeuFichier
from apps.plans.serializers_enjeux import (
    CorEnjeuFichierSerializer, EnjeuCreateSerializer, EnjeuDetailSerializer,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.enjeux import NomenclatureEnjeuFactory
from tests.factories.users import RoleFactory

pytestmark = pytest.mark.django_db


def _make_enjeu():
    user = RoleFactory()
    plan = PlanGestionFactory()
    cat = NomenclatureEnjeuFactory()
    s = EnjeuCreateSerializer(data={
        'id_pg': plan.id_pg,
        'id_categorie': cat.id_nomenclature,
        'libelle': 'Enjeu doc #237',
        'rang': 1,
        'categorie_ecologique': True,
        'patrimoine_geologique': True,
        'geo_documents': True,
    })
    assert s.is_valid(), s.errors
    return s.save(id_utilisateur_ajout=user), user


class TestEnjeuDocuments:
    def test_reference_papier_sans_fichier(self):
        enjeu, user = _make_enjeu()
        s = CorEnjeuFichierSerializer(data={
            'id_enjeu': enjeu.id_enjeu,
            'support': 'papier',
            'titre': 'Archive cadastrale 1923',
        })
        assert s.is_valid(), s.errors
        doc = s.save(id_utilisateur_upload=user)
        assert doc.support == 'papier'
        assert doc.titre == 'Archive cadastrale 1923'
        assert doc.chemin_fichier == ''

    def test_papier_exige_un_titre(self):
        enjeu, _ = _make_enjeu()
        s = CorEnjeuFichierSerializer(data={'id_enjeu': enjeu.id_enjeu, 'support': 'papier', 'titre': ''})
        assert not s.is_valid()
        assert 'titre' in s.errors

    def test_numerique_exige_un_fichier(self):
        enjeu, _ = _make_enjeu()
        s = CorEnjeuFichierSerializer(data={'id_enjeu': enjeu.id_enjeu, 'support': 'numerique'})
        assert not s.is_valid()
        assert 'fichier' in s.errors

    def test_upload_fichier_numerique(self, settings, tmp_path):
        settings.MEDIA_ROOT = str(tmp_path)  # n'écrit pas dans le media réel
        enjeu, user = _make_enjeu()
        upload = SimpleUploadedFile('rapport.pdf', b'%PDF-1.4 contenu', content_type='application/pdf')
        s = CorEnjeuFichierSerializer(data={
            'id_enjeu': enjeu.id_enjeu,
            'support': 'numerique',
            'fichier': upload,
        })
        assert s.is_valid(), s.errors
        doc = s.save(id_utilisateur_upload=user)
        assert doc.support == 'numerique'
        assert doc.nom_fichier == 'rapport.pdf'
        assert doc.extension == '.pdf'
        assert doc.taille_fichier and doc.taille_fichier > 0
        assert doc.chemin_fichier

    def test_documents_exposes_dans_detail(self):
        enjeu, user = _make_enjeu()
        CorEnjeuFichier.objects.create(id_enjeu=enjeu, support='papier', titre='Doc papier')
        data = EnjeuDetailSerializer(enjeu).data
        assert 'documents' in data
        assert len(data['documents']) == 1
        assert data['documents'][0]['support'] == 'papier'
        assert data['documents'][0]['titre'] == 'Doc papier'

    def test_cascade_delete(self):
        enjeu, _ = _make_enjeu()
        CorEnjeuFichier.objects.create(id_enjeu=enjeu, support='papier', titre='X')
        enjeu_id = enjeu.id_enjeu
        enjeu.delete()
        assert not CorEnjeuFichier.objects.filter(id_enjeu_id=enjeu_id).exists()
