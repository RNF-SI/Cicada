"""
#779 — passage de version générique : PressRef, TaxRef, HabRef.

- un code repris tel quel n'est pas touché ; sûr / probable → posé ;
  à arbitrer → l'ancien code reste (cohabitation), équivalents proposés ;
- fusion de deux taxons d'un même enjeu → la ligne en double disparaît ;
- habitats structurés d'un suivi remappés entrée par entrée ;
- annulation ; choix par l'API (même plan validé), conflit, propositions
  uniques acceptées ; le bandeau compte tous les référentiels.
"""
import csv
import json

import pytest

from apps.core.models import Nomenclature, TypeNomenclature
from apps.notifications.models import Notification
from apps.plans.models_enjeux import CorEnjeuHabitat, CorEnjeuTaxon, Pression
from apps.plans.models_referentiel import PassageReferentielObjet
from apps.plans.referentiels import moteur
from apps.taxonomy.models import TMetaTaxref
from tests.factories.enjeux import (
    EnjeuFactory, FacteurInfluenceFactory, PressionFactory, SuiviInventaireFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import RoleFactory


def _ecrire(dossier, ref, nom, meta, lignes, corresp):
    d = dossier / ref / nom
    d.mkdir(parents=True)
    (d / 'version.json').write_text(json.dumps(meta), encoding='utf-8')
    if lignes is not None:
        with open(d / 'referentiel.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['code', 'libelle'])
            w.writerows(lignes)
    with open(d / 'correspondance.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['ancien_code', 'nouveau_code', 'confiance', 'options', 'note'])
        w.writerows(corresp)


@pytest.fixture
def donnees(db, tmp_path, monkeypatch):
    monkeypatch.setattr(moteur, 'DOSSIER_VERSIONS', tmp_path)
    monkeypatch.setattr(moteur.transaction, 'on_commit', lambda f, *a, **k: f())
    TMetaTaxref.objects.create(referential_name='TAXREF', version='18')
    t, _ = TypeNomenclature.objects.get_or_create(mnemonique='TYPE_PRESSION',
                                                  defaults={'label': 'Type de pression'})
    for code in ('1.1', '1.2', '2.1'):
        Nomenclature.objects.update_or_create(id_type=t, cd_nomenclature=code,
                                              defaults={'label': f'Pression {code}', 'actif': True})
    _ecrire(tmp_path, 'pressref', 'v2', {'code': 'PRESSREF_V2', 'libelle': 'PressRef V2',
                                         'depuis': 'PRESSREF_CARET_V1'},
            [['1.1', 'Pression 1.1'], ['1.3', 'Pression 1.3 (V2)'], ['1.4', 'Pression 1.4']],
            [['1.2', '1.3', 'sure', '', '']])
    _ecrire(tmp_path, 'taxref', 'v19', {'code': 'TAXREF_V19', 'libelle': 'TaxRef v19',
                                        'depuis': 'TAXREF_V18'},
            [['200', 'Taxon fusionné'], ['201', 'Taxon A'], ['202', 'Taxon B']],
            [['100', '200', 'sure', '', 'Fusion'], ['101', '201', 'a_arbitrer', '201|202', 'Scission'],
             ['102', '200', 'sure', '', 'Fusion']])
    _ecrire(tmp_path, 'habref', 'v6', {'code': 'HABREF_V6', 'libelle': 'HabRef 6',
                                       'depuis': 'HABREF_V5.0'},
            [['11', 'Habitat 11'], ['13', 'Habitat 13'], ['14', 'Habitat 14']],
            [['10', '11', 'probable', '', ''], ['12', '13', 'a_arbitrer', '13|14', '']])

    plan = PlanGestionFactory(statut='valide')
    enjeu = EnjeuFactory(id_pg=plan, libelle='Prairies')
    pressions = {
        code: PressionFactory(id_facteur_influence=FacteurInfluenceFactory(id_enjeu=enjeu),
                              id_type_pression=Nomenclature.objects.get(id_type=t, cd_nomenclature=code))
        for code in ('1.1', '1.2', '2.1')}
    taxons = {cd: CorEnjeuTaxon.objects.create(id_enjeu=enjeu, cd_nom=cd, nom_complet=f'Taxon {cd}')
              for cd in (100, 101, 102)}
    hab = CorEnjeuHabitat.objects.create(id_enjeu=enjeu, cd_hab='12', lb_hab_fr='Habitat 12')
    suivi = SuiviInventaireFactory(id_pg=plan, habitats=[{'cd_hab': '10', 'lb_hab_fr': 'Habitat 10'},
                                                         {'cd_hab': '99', 'lb_hab_fr': 'Inchangé'}])
    alice, bob = RoleFactory(), RoleFactory()
    plan.referents.add(alice, bob)
    return {'plan': plan, 'enjeu': enjeu, 'pressions': pressions, 'taxons': taxons, 'hab': hab,
            'suivi': suivi, 'alice': alice, 'bob': bob}


def _appliquer(code, nom):
    ref = moteur.referentiel(code)
    return moteur.appliquer(ref, moteur.charger(ref, nom), envoyer_email=False)


@pytest.mark.django_db
class TestMoteur:
    def test_pressref_nomenclature(self, donnees):
        r = moteur.simuler(moteur.referentiel('PRESSREF'),
                           moteur.charger(moteur.referentiel('PRESSREF'), 'v2'))
        assert r['objets'] == {'sure': 1, 'a_arbitrer': 1}   # 1.1 repris, non touché
        _appliquer('PRESSREF', 'v2')
        p = {c: Pression.objects.get(pk=o.pk) for c, o in donnees['pressions'].items()}
        assert p['1.1'].id_type_pression.cd_nomenclature == '1.1'
        assert p['1.2'].id_type_pression.cd_nomenclature == '1.3'
        # Cohabitation : 2.1 (absent de V2, hors table) garde son ancien type, désactivé.
        assert p['2.1'].id_type_pression.cd_nomenclature == '2.1'
        assert not p['2.1'].id_type_pression.actif
        assert Nomenclature.objects.get(id_type__mnemonique='TYPE_PRESSION', cd_nomenclature='1.4').actif
        assert moteur.version_en_service(moteur.referentiel('PRESSREF'))[0] == 'PRESSREF_V2'

    def test_taxref_fusion_scission(self, donnees):
        _appliquer('TAXREF', 'v19')
        cds = sorted(CorEnjeuTaxon.objects.filter(id_enjeu=donnees['enjeu']).values_list('cd_nom', flat=True))
        # 100 et 102 fusionnent en 200 (une seule ligne) ; 101 attend un choix.
        assert cds == [101, 200]
        assert CorEnjeuTaxon.objects.get(cd_nom=200).nom_complet == 'Taxon fusionné'
        obj = PassageReferentielObjet.objects.get(cible='enjeu_taxon', ancien_code='101')
        assert obj.statut == 'a_actualiser' and obj.options == ['201', '202']

    def test_habref_enjeu_et_suivi(self, donnees):
        _appliquer('HABREF', 'v6')
        donnees['suivi'].refresh_from_db()
        assert donnees['suivi'].habitats == [{'cd_hab': '11', 'lb_hab_fr': 'Habitat 11'},
                                             {'cd_hab': '99', 'lb_hab_fr': 'Inchangé'}]
        donnees['hab'].refresh_from_db()
        assert donnees['hab'].cd_hab == '12'                 # cohabitation

    def test_annuler(self, donnees):
        _appliquer('PRESSREF', 'v2')
        ref = moteur.referentiel('PRESSREF')
        moteur.annuler(ref, moteur.charger(ref, 'v2'))
        p = Pression.objects.get(pk=donnees['pressions']['1.2'].pk)
        assert p.id_type_pression.cd_nomenclature == '1.2'
        assert Nomenclature.objects.get(id_type__mnemonique='TYPE_PRESSION', cd_nomenclature='2.1').actif
        assert not Nomenclature.objects.get(id_type__mnemonique='TYPE_PRESSION', cd_nomenclature='1.4').actif

    def test_une_notification_par_referent(self, donnees):
        _appliquer('TAXREF', 'v19')
        notifs = Notification.objects.filter(notification_type='referentiel_actions')
        assert notifs.filter(recipient=donnees['alice']).count() == 1
        assert notifs.get(recipient=donnees['alice']).title.startswith('Taxons (TaxRef)')


@pytest.mark.django_db
class TestApi:
    def test_liste_choix_conflit_et_bandeau(self, api_client, donnees):
        _appliquer('TAXREF', 'v19')
        api_client.force_authenticate(user=donnees['alice'])
        r = api_client.get('/api/plans/referentiels/a-actualiser/')
        assert r.status_code == 200
        (taxref,) = r.data['referentiels']
        assert taxref['code'] == 'TAXREF' and taxref['total_a_actualiser'] == 1
        item = taxref['plans'][0]['a_actualiser'][0]
        assert item['code_actuel'] == '101'
        assert [o['code'] for o in item['options']] == ['201', '202']
        assert 'Prairies' in item['contexte']
        compte = api_client.get('/api/plans/referentiel-actions/a-actualiser/compte/').data
        assert compte['total'] == 1 and compte['referentiels'][0]['code'] == 'TAXREF'

        url = f"/api/plans/referentiels/objets/{item['id']}/actualiser/"
        r = api_client.post(url, {'code': '202', 'attendu': '101'}, format='json')
        assert r.status_code == 200, r.content                # plan validé : permis
        assert CorEnjeuTaxon.objects.filter(id_enjeu=donnees['enjeu'], cd_nom=202).exists()
        api_client.force_authenticate(user=donnees['bob'])
        r = api_client.post(url, {'code': '201', 'attendu': '101'}, format='json')
        assert r.status_code == 409 and r.data['code'] == 'code_deja_modifie'

    def test_hors_plan_refuse(self, api_client, donnees):
        _appliquer('TAXREF', 'v19')
        obj = PassageReferentielObjet.objects.get(cible='enjeu_taxon', ancien_code='101')
        api_client.force_authenticate(user=RoleFactory())
        r = api_client.post(f'/api/plans/referentiels/objets/{obj.pk}/actualiser/',
                            {'code': '201', 'attendu': '101'}, format='json')
        assert r.status_code == 403

    def test_accepter_propositions(self, api_client, donnees):
        _appliquer('HABREF', 'v6')
        api_client.force_authenticate(user=donnees['alice'])
        r = api_client.post('/api/plans/referentiels/accepter-propositions/',
                            {'referentiel': 'HABREF'}, format='json')
        assert r.data == {'acceptees': 0, 'plusieurs_options': 1, 'suivi_requis': 0}
