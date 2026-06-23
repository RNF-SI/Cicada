"""
#237 — Tests du champ « Objet(s) géologique(s) » d'un enjeu via le serializer.

Les objets référencent désormais des nomenclatures TYPE_OBJET_GEOLOGIQUE
(référentiel centralisé). On vérifie la persistance (FK + précision), le
remplacement complet à la mise à jour, la déduplication et le rejet d'ids
hors typologie.
"""
import pytest

from apps.core.models import Nomenclature, TypeNomenclature
from apps.plans.models_enjeux import CorEnjeuObjetGeologique
from apps.plans.serializers_enjeux import EnjeuCreateSerializer, EnjeuDetailSerializer
from tests.factories.plans import PlanGestionFactory
from tests.factories.enjeux import NomenclatureEnjeuFactory
from tests.factories.users import RoleFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def geo_objets(db):
    """Crée quelques nomenclatures TYPE_OBJET_GEOLOGIQUE. Retourne {code: id}."""
    t, _ = TypeNomenclature.objects.get_or_create(
        mnemonique='TYPE_OBJET_GEOLOGIQUE',
        defaults={'label': "Type d'objet géologique"},
    )
    out = {}
    for code, label, hier in [
        ('IS_SITE_PALEO', 'Site paléontologique', '1.01'),
        ('IS_GISEMENT_FOSSILIFERE', 'Gisement fossilifère', '1.01.01'),
        ('IS_AFFLEUREMENT', 'Affleurement remarquable', '1.02'),
        ('IS_AUTRE', 'Autre', '1.11'),
        ('ES_COLL_PALEO', 'Collection paléontologique', '2.01'),
    ]:
        n = Nomenclature.objects.create(
            id_type=t, cd_nomenclature=code, mnemonique=code, label=label, hierarchy=hier,
        )
        out[code] = n.id_nomenclature
    return out


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
    def test_create_persiste_objets_et_precision(self, geo_objets):
        user = RoleFactory()
        plan = PlanGestionFactory()
        cat = NomenclatureEnjeuFactory()
        payload = _base_payload(plan, cat)
        payload.update({
            'geo_autre': True,
            'geo_autre_precision': 'Patrimoine glaciaire',
            'objets_geologiques_data': [
                {'id_objet_geologique': geo_objets['IS_SITE_PALEO']},
                {'id_objet_geologique': geo_objets['IS_GISEMENT_FOSSILIFERE']},
                {'id_objet_geologique': geo_objets['IS_AUTRE'], 'precision': 'Stries glaciaires'},
            ],
        })
        s = EnjeuCreateSerializer(data=payload)
        assert s.is_valid(), s.errors
        enjeu = s.save(id_utilisateur_ajout=user)

        objets = {o.id_objet_geologique.cd_nomenclature: o for o in enjeu.objets_geologiques.select_related('id_objet_geologique')}
        assert set(objets) == {'IS_SITE_PALEO', 'IS_GISEMENT_FOSSILIFERE', 'IS_AUTRE'}
        assert objets['IS_AUTRE'].precision == 'Stries glaciaires'

        data = EnjeuDetailSerializer(enjeu).data
        assert data['geo_autre'] is True
        assert data['geo_autre_precision'] == 'Patrimoine glaciaire'
        # le serializer expose code + libellé dénormalisés depuis la nomenclature
        codes = {o['code'] for o in data['objets_geologiques']}
        assert codes == {'IS_SITE_PALEO', 'IS_GISEMENT_FOSSILIFERE', 'IS_AUTRE'}

    def test_update_remplace_les_objets(self, geo_objets):
        user = RoleFactory()
        plan = PlanGestionFactory()
        cat = NomenclatureEnjeuFactory()
        payload = _base_payload(plan, cat)
        payload['objets_geologiques_data'] = [
            {'id_objet_geologique': geo_objets['IS_AFFLEUREMENT']},
            {'id_objet_geologique': geo_objets['ES_COLL_PALEO']},
        ]
        s = EnjeuCreateSerializer(data=payload)
        assert s.is_valid(), s.errors
        enjeu = s.save(id_utilisateur_ajout=user)
        assert enjeu.objets_geologiques.count() == 2

        upd = EnjeuCreateSerializer(
            enjeu,
            data={'objets_geologiques_data': [
                {'id_objet_geologique': geo_objets['IS_AUTRE'], 'precision': 'Z'},
            ]},
            partial=True,
        )
        assert upd.is_valid(), upd.errors
        upd.save(id_utilisateur_maj=user)

        rows = list(enjeu.objets_geologiques.all())
        assert len(rows) == 1
        assert rows[0].id_objet_geologique_id == geo_objets['IS_AUTRE']
        assert rows[0].precision == 'Z'

    def test_doublons_ignores(self, geo_objets):
        user = RoleFactory()
        plan = PlanGestionFactory()
        cat = NomenclatureEnjeuFactory()
        payload = _base_payload(plan, cat)
        payload['objets_geologiques_data'] = [
            {'id_objet_geologique': geo_objets['IS_AFFLEUREMENT']},
            {'id_objet_geologique': geo_objets['IS_AFFLEUREMENT']},
        ]
        s = EnjeuCreateSerializer(data=payload)
        assert s.is_valid(), s.errors
        enjeu = s.save(id_utilisateur_ajout=user)
        assert enjeu.objets_geologiques.count() == 1

    def test_id_hors_typologie_ignore(self, geo_objets):
        """Un id qui n'est pas un TYPE_OBJET_GEOLOGIQUE est écarté."""
        user = RoleFactory()
        plan = PlanGestionFactory()
        cat = NomenclatureEnjeuFactory()
        autre_nom = NomenclatureEnjeuFactory()  # nomenclature d'un autre type
        payload = _base_payload(plan, cat)
        payload['objets_geologiques_data'] = [
            {'id_objet_geologique': geo_objets['IS_AFFLEUREMENT']},
            {'id_objet_geologique': autre_nom.id_nomenclature},
        ]
        s = EnjeuCreateSerializer(data=payload)
        assert s.is_valid(), s.errors
        enjeu = s.save(id_utilisateur_ajout=user)
        assert enjeu.objets_geologiques.count() == 1

    def test_cascade_delete(self, geo_objets):
        user = RoleFactory()
        plan = PlanGestionFactory()
        cat = NomenclatureEnjeuFactory()
        payload = _base_payload(plan, cat)
        payload['objets_geologiques_data'] = [
            {'id_objet_geologique': geo_objets['IS_AFFLEUREMENT']},
        ]
        s = EnjeuCreateSerializer(data=payload)
        assert s.is_valid(), s.errors
        enjeu = s.save(id_utilisateur_ajout=user)
        enjeu_id = enjeu.id_enjeu
        enjeu.delete()
        assert not CorEnjeuObjetGeologique.objects.filter(id_enjeu_id=enjeu_id).exists()
