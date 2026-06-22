"""
#237 — Tests du champ « Objet(s) géologique(s) » d'un enjeu via le serializer.

Vérifie la persistance des objets géologiques (code + libellé + précision),
des patrimoines Documents/Autre, et le remplacement complet à la mise à jour.
"""
import pytest

from apps.plans.models_enjeux import CorEnjeuObjetGeologique
from apps.plans.serializers_enjeux import EnjeuCreateSerializer, EnjeuDetailSerializer
from tests.factories.plans import PlanGestionFactory
from tests.factories.enjeux import NomenclatureEnjeuFactory
from tests.factories.users import RoleFactory

pytestmark = pytest.mark.django_db


def _base_payload(plan, categorie):
    return {
        'id_pg': plan.id_pg,
        'id_categorie': categorie.id_nomenclature,
        'libelle': 'Enjeu géologique #237',
        'rang': 1,
        'categorie_ecologique': True,
        'patrimoine_geologique': True,
        'geo_in_situ': True,
    }


class TestEnjeuObjetsGeologiques:
    def test_create_persiste_objets_et_precision(self):
        user = RoleFactory()
        plan = PlanGestionFactory()
        cat = NomenclatureEnjeuFactory()
        payload = _base_payload(plan, cat)
        payload.update({
            'geo_documents': True,
            'geo_autre': True,
            'geo_autre_precision': 'Patrimoine glaciaire',
            'objets_geologiques_data': [
                {'code': 'IS_SITE_PALEO', 'libelle': 'Site paléontologique'},
                {'code': 'IS_GISEMENT_FOSSILIFERE', 'libelle': 'Gisement fossilifère'},
                {'code': 'IS_AUTRE', 'libelle': 'Autre', 'precision': 'Stries glaciaires'},
            ],
        })
        s = EnjeuCreateSerializer(data=payload)
        assert s.is_valid(), s.errors
        enjeu = s.save(id_utilisateur_ajout=user)

        objets = {o.code: o for o in enjeu.objets_geologiques.all()}
        assert set(objets) == {'IS_SITE_PALEO', 'IS_GISEMENT_FOSSILIFERE', 'IS_AUTRE'}
        assert objets['IS_AUTRE'].precision == 'Stries glaciaires'
        assert objets['IS_SITE_PALEO'].libelle == 'Site paléontologique'

        # Patrimoines exposés par le serializer détail
        data = EnjeuDetailSerializer(enjeu).data
        assert data['geo_documents'] is True
        assert data['geo_autre'] is True
        assert data['geo_autre_precision'] == 'Patrimoine glaciaire'
        assert len(data['objets_geologiques']) == 3

    def test_update_remplace_les_objets(self):
        user = RoleFactory()
        plan = PlanGestionFactory()
        cat = NomenclatureEnjeuFactory()
        payload = _base_payload(plan, cat)
        payload['objets_geologiques_data'] = [
            {'code': 'IS_AFFLEUREMENT', 'libelle': 'Affleurement remarquable'},
            {'code': 'IS_VOLCANIQUE', 'libelle': 'Site volcanique'},
        ]
        s = EnjeuCreateSerializer(data=payload)
        assert s.is_valid(), s.errors
        enjeu = s.save(id_utilisateur_ajout=user)
        assert enjeu.objets_geologiques.count() == 2

        # Mise à jour : on ne garde qu'un objet, avec une précision modifiée
        upd = EnjeuCreateSerializer(
            enjeu,
            data={'objets_geologiques_data': [
                {'code': 'IS_AUTRE', 'libelle': 'Autre', 'precision': 'Z'},
            ]},
            partial=True,
        )
        assert upd.is_valid(), upd.errors
        upd.save(id_utilisateur_maj=user)

        codes = list(enjeu.objets_geologiques.values_list('code', flat=True))
        assert codes == ['IS_AUTRE']
        assert enjeu.objets_geologiques.first().precision == 'Z'

    def test_doublons_de_code_ignores(self):
        user = RoleFactory()
        plan = PlanGestionFactory()
        cat = NomenclatureEnjeuFactory()
        payload = _base_payload(plan, cat)
        payload['objets_geologiques_data'] = [
            {'code': 'IS_AFFLEUREMENT', 'libelle': 'Affleurement remarquable'},
            {'code': 'IS_AFFLEUREMENT', 'libelle': 'doublon'},
        ]
        s = EnjeuCreateSerializer(data=payload)
        assert s.is_valid(), s.errors
        enjeu = s.save(id_utilisateur_ajout=user)
        assert enjeu.objets_geologiques.count() == 1

    def test_cascade_delete(self):
        user = RoleFactory()
        plan = PlanGestionFactory()
        cat = NomenclatureEnjeuFactory()
        payload = _base_payload(plan, cat)
        payload['objets_geologiques_data'] = [
            {'code': 'IS_AFFLEUREMENT', 'libelle': 'Affleurement remarquable'},
        ]
        s = EnjeuCreateSerializer(data=payload)
        assert s.is_valid(), s.errors
        enjeu = s.save(id_utilisateur_ajout=user)
        enjeu_id = enjeu.id_enjeu
        enjeu.delete()
        assert not CorEnjeuObjetGeologique.objects.filter(id_enjeu_id=enjeu_id).exists()
