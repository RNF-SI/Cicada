"""
#751 / #776 — passage du référentiel des types d'action (Eden 62 → Gestref V1, et suivants).

- la simulation n'écrit rien ;
- sûre / probable → nouveau type et catégorie (changements informatifs, que le
  référent peut corriger, même dans un plan validé ou archivé) ;
- à arbitrer → **cohabitation** : l'action garde son ancien type (et sa
  catégorie) tant que le référent n'a pas choisi ; les équivalents possibles
  sont proposés ; anciens types désactivés ;
- une notification par référent et par passage, une notification de suivi
  regroupée quand un autre référent actualise ;
- choisir le type est permis hors brouillon, refusé si un autre référent l'a
  choisi entre-temps ; une action qui devient CS sans suivi en reçoit un ;
- « accepter toutes les propositions » ne pose que les équivalents uniques ;
- `import_nomenclatures --force` ne défait pas le passage ; il s'annule.
"""
import csv
import json
from pathlib import Path

import pytest
from rest_framework import status

from apps.core.models import Nomenclature, TypeNomenclature
from apps.notifications.models import Notification
from apps.plans import referentiel_actions as ref
from apps.plans.models_operations import SuiviInventaire
from apps.plans.models_referentiel import PassageReferentielObjet
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, MetriqueFactory, NiveauExigenceFactory,
    ObjectifLongTermeFactory, OperationFactory, SuiviInventaireFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import RoleFactory


def _nom(type_mnemo, code, label=None, actif=True):
    t, _ = TypeNomenclature.objects.get_or_create(mnemonique=type_mnemo,
                                                  defaults={'label': type_mnemo})
    # Une catégorie peut déjà exister (migrations) : même ligne, comme en base.
    n, _ = Nomenclature.objects.update_or_create(
        id_type=t, cd_nomenclature=code,
        defaults={'mnemonique': code, 'label': label or code, 'actif': actif})
    return n


def _ecrire_version(dossier: Path, *, exclure=()):
    d = dossier / 'test_v1'
    d.mkdir()
    (d / 'version.json').write_text(json.dumps({
        'code': 'TEST_V1', 'libelle': 'Test V1', 'depuis': 'EDEN62',
        'exclure_categories': list(exclure)}), encoding='utf-8')
    with open(d / 'referentiel.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['code', 'libelle'])
        w.writerows([['CS', 'Connaissance (V1)'], ['CS.1', 'Études des eaux'],
                     ['CS.1.1', 'Études hydrologiques'], ['GE', 'Gestion des équipements'],
                     ['GE.1', 'Infrastructures'], ['CP', 'Pratiques'], ['CP.1', 'Contrats']])
    with open(d / 'correspondance.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['ancien_code', 'nouveau_code', 'confiance', 'options', 'note'])
        w.writerows([['CS14', 'CS.1.1', 'sure', '', ''],
                     ['CI2', 'GE.1', 'probable', '', 'Infrastructures d’accueil'],
                     ['CS8', 'CS.1', 'a_arbitrer', 'CS.1|CS.1.1', 'Faune : à préciser'],
                     ['EI3', 'CS.1', 'a_arbitrer', '', 'Étude devenue CS'],
                     ['MS7', 'CP.1', 'sure', '', '']])
    return 'test_v1'


@pytest.fixture
def referentiel(db, tmp_path, monkeypatch):
    monkeypatch.setattr(ref, 'DOSSIER_REFERENTIELS', tmp_path)
    # Les notifications partent après le commit : dans un test (transaction
    # jamais validée), on les exécute tout de suite.
    monkeypatch.setattr(ref.transaction, 'on_commit', lambda f, *a, **k: f())
    eden = {
        'cat_cs': _nom(ref.CATEGORIE, 'CS', 'Connaissance (Eden)'),
        'cat_ci': _nom(ref.CATEGORIE, 'CI', 'Infrastructures (Eden)'),
        'cat_ei': _nom(ref.CATEGORIE, 'EI', 'Études (Eden)'),
        'cs14': _nom(ref.TYPE_ACTION, 'CS14', 'Suivi des facteurs abiotiques'),
        'ci2': _nom(ref.TYPE_ACTION, 'CI2', 'Infrastructures d’accueil'),
        'cs8': _nom(ref.TYPE_ACTION, 'CS8', 'Inventaire de la faune'),
        'ei3': _nom(ref.TYPE_ACTION, 'EI3', 'Étude des facteurs'),
        'ms7': _nom(ref.TYPE_ACTION, 'MS7', 'Démarches administratives'),
    }
    return {'nom': _ecrire_version(tmp_path, exclure=['CP']), **eden}


def _plan_avec_actions(statut, *actions):
    plan = PlanGestionFactory(statut=statut)
    met = MetriqueFactory(id_indicateur=IndicateurFactory(
        id_ne=NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(
            id_enjeu=EnjeuFactory(id_pg=plan)))))
    ops = [OperationFactory(metriques=[met], id_type_action=t, id_categorie_action_reserve=c)
           for t, c in actions]
    return plan, ops


@pytest.fixture
def plans(referentiel):
    r = referentiel
    p1, (op_sure, op_arb, op_ei) = _plan_avec_actions(
        'valide', (r['cs14'], r['cat_cs']), (r['cs8'], r['cat_cs']), (r['ei3'], r['cat_ei']))
    suivi = SuiviInventaireFactory(id_pg=p1, id_type_action=r['cs8'])
    op_arb.id_suivi = suivi
    op_arb.save()
    p2, (op_prob, op_arb2) = _plan_avec_actions(
        'draft', (r['ci2'], r['cat_ci']), (r['cs8'], None))
    p3, (op_arch,) = _plan_avec_actions('archive', (r['cs14'], r['cat_cs']))
    alice, bob = RoleFactory(), RoleFactory()
    p1.referents.add(alice, bob)
    p2.referents.add(alice)
    p3.referents.add(alice)
    return {'p1': p1, 'p2': p2, 'p3': p3, 'op_sure': op_sure, 'op_arb': op_arb, 'op_ei': op_ei,
            'op_prob': op_prob, 'op_arb2': op_arb2, 'op_arch': op_arch, 'suivi': suivi,
            'alice': alice, 'bob': bob}


def _appliquer(referentiel, **kw):
    definition = ref.charger_version(referentiel['nom'])
    return ref.appliquer(definition, **kw)


def _type(code):
    return Nomenclature.objects.get(id_type__mnemonique=ref.TYPE_ACTION, cd_nomenclature=code)


@pytest.mark.django_db
class TestPassage:
    def test_lecture_ecarte_la_categorie_exclue_et_lit_les_options(self, referentiel):
        d = ref.charger_version(referentiel['nom'])
        assert d.codes_categories == {'CS', 'GE'}
        assert 'CP.1' not in d.codes_types
        # Une correspondance vers une catégorie écartée ne peut être posée.
        assert d.correspondance['MS7'].confiance == 'a_arbitrer'
        assert d.correspondance['MS7'].nouveau_code == ''
        assert d.correspondance['CS8'].options == ['CS.1', 'CS.1.1']
        assert d.correspondance['EI3'].options == ['CS.1']

    def test_simulation_n_ecrit_rien(self, referentiel, plans):
        rapport = ref.simuler(ref.charger_version(referentiel['nom']))
        assert rapport['actions']['sure'] == 2
        assert rapport['actions']['probable'] == 1
        assert rapport['actions']['a_arbitrer'] == 3
        assert rapport['devient_cs']['total'] == 1
        plans['op_sure'].refresh_from_db()
        assert plans['op_sure'].id_type_action == referentiel['cs14']
        assert not Nomenclature.objects.filter(cd_nomenclature='CS.1.1').exists()

    def test_applique_sure_et_probable_et_garde_l_ancien_type_a_arbitrer(self, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        for k in ('op_sure', 'op_arb', 'op_prob', 'op_arb2', 'op_ei', 'op_arch'):
            plans[k].refresh_from_db()
        assert plans['op_sure'].id_type_action.cd_nomenclature == 'CS.1.1'
        assert plans['op_arch'].id_type_action.cd_nomenclature == 'CS.1.1'
        assert plans['op_prob'].id_type_action.cd_nomenclature == 'GE.1'
        assert plans['op_prob'].id_categorie_action_reserve.cd_nomenclature == 'GE'
        # Cohabitation : l'action à arbitrer garde son ancien type et sa catégorie.
        assert plans['op_arb'].id_type_action == referentiel['cs8']
        assert plans['op_ei'].id_categorie_action_reserve == referentiel['cat_ei']
        assert plans['op_arb'].id_suivi_id == plans['suivi'].pk
        plans['suivi'].refresh_from_db()
        assert plans['suivi'].id_type_action == referentiel['cs8']
        # Une action sans catégorie n'en reçoit pas.
        assert plans['op_arb2'].id_categorie_action_reserve is None
        # La catégorie partagée CS est réutilisée, avec le libellé V1.
        cs = Nomenclature.objects.get(pk=referentiel['cat_cs'].pk)
        assert cs.actif and cs.label == 'Connaissance (V1)'
        # Les anciens types ne sont plus proposés, mais restent lisibles.
        assert not Nomenclature.objects.get(pk=referentiel['cs8'].pk).actif
        assert not Nomenclature.objects.get(pk=referentiel['cat_ci'].pk).actif
        assert _type('CS.1.1').pk >= ref.REFERENTIEL_ID_BASE
        objets = {o.operation_id: o for o in PassageReferentielObjet.objects.filter(
            operation__isnull=False)}
        assert objets[plans['op_arb'].pk].statut == 'a_actualiser'
        assert objets[plans['op_arb'].pk].options == ['CS.1', 'CS.1.1']
        assert objets[plans['op_sure'].pk].statut == 'applique'

    def test_une_notification_par_referent(self, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        notifs = Notification.objects.filter(notification_type='referentiel_actions')
        # Alice est référente des trois plans : une seule notification.
        assert notifs.filter(recipient=plans['alice']).count() == 1
        assert notifs.filter(recipient=plans['bob']).count() == 1
        msg = notifs.get(recipient=plans['alice']).message
        assert "3 action(s) n'ont pas d'équivalent certain" in msg

    def test_import_nomenclatures_ne_defait_pas_le_passage(self, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        # Ce que fait l'upsert du fichier SQL : types Eden réactivés, libellé Eden.
        Nomenclature.objects.filter(pk=referentiel['cs14'].pk).update(actif=True)
        Nomenclature.objects.filter(pk=referentiel['cat_cs'].pk).update(label='Connaissance (Eden)')
        assert ref.reappliquer_version_courante()
        assert not Nomenclature.objects.get(pk=referentiel['cs14'].pk).actif
        assert Nomenclature.objects.get(pk=referentiel['cat_cs'].pk).label == 'Connaissance (V1)'

    def test_annuler_restaure_la_version_de_depart(self, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        ref.annuler(ref.charger_version(referentiel['nom']))
        plans['op_sure'].refresh_from_db()
        plans['op_prob'].refresh_from_db()
        assert plans['op_sure'].id_type_action == referentiel['cs14']
        assert plans['op_prob'].id_categorie_action_reserve == referentiel['cat_ci']
        assert Nomenclature.objects.get(pk=referentiel['cs14'].pk).actif
        assert not _type('CS.1.1').actif
        assert Nomenclature.objects.get(pk=referentiel['cat_cs'].pk).label == 'Connaissance (Eden)'
        assert not Notification.objects.filter(notification_type='referentiel_actions').exists()

    def test_depart_incoherent_refuse(self, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        with pytest.raises(ref.ReferentielErreur):
            ref.simuler(ref.charger_version(referentiel['nom']))


SUIVI_NOUVEAU = {
    'intitule': 'Étude des facteurs', 'objectif_principal': 'OBJ_ETAT_CONSERVATION',
    'cibles_principales': 'ESPECES',
    'protocoles': [{'protocole_dans_campanule': False, 'nom_protocole': 'Protocole local'}],
}


@pytest.mark.django_db
class TestActualisation:
    def _actualiser(self, client, op, type_id, attendu, **extra):
        return client.post(f'/api/plans/operations/{op.pk}/actualiser-type/',
                           {'id_type_action': type_id, 'type_attendu': attendu, **extra},
                           format='json')

    def test_plan_valide_et_suivi_des_autres(self, api_client, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        cs11 = _type('CS.1.1')
        api_client.force_authenticate(user=plans['bob'])
        r = self._actualiser(api_client, plans['op_arb'], cs11.pk, referentiel['cs8'].pk)
        assert r.status_code == status.HTTP_200_OK, r.content
        assert r.data['type_action_a_actualiser'] is None
        plans['op_arb'].refresh_from_db()
        assert plans['op_arb'].id_type_action == cs11
        # La catégorie suit le nouveau type, le suivi aussi.
        assert plans['op_arb'].id_categorie_action_reserve.cd_nomenclature == 'CS'
        plans['suivi'].refresh_from_db()
        assert plans['suivi'].id_type_action == cs11
        obj = PassageReferentielObjet.objects.get(operation=plans['op_arb'])
        assert obj.statut == 'actualise' and obj.actualise_par == plans['bob']
        # Alice (autre référente) est prévenue ; Bob ne se notifie pas lui-même.
        suivi = Notification.objects.filter(notification_type='referentiel_actions_suivi')
        assert list(suivi.values_list('recipient', flat=True)) == [plans['alice'].pk]

    def test_conflit_si_deja_choisi(self, api_client, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        cs11, cs1 = _type('CS.1.1'), _type('CS.1')
        api_client.force_authenticate(user=plans['bob'])
        assert self._actualiser(api_client, plans['op_arb'], cs11.pk,
                                referentiel['cs8'].pk).status_code == 200
        api_client.force_authenticate(user=plans['alice'])
        r = self._actualiser(api_client, plans['op_arb'], cs1.pk, referentiel['cs8'].pk)
        assert r.status_code == status.HTTP_409_CONFLICT
        assert r.data['code'] == 'type_deja_modifie'
        plans['op_arb'].refresh_from_db()
        assert plans['op_arb'].id_type_action == cs11

    def test_corriger_un_changement_automatique_plan_archive(self, api_client, referentiel, plans):
        """Refuser l'appariement automatique et choisir un autre type, même
        dans un plan archivé."""
        _appliquer(referentiel, envoyer_email=False)
        cs11, cs1 = _type('CS.1.1'), _type('CS.1')
        api_client.force_authenticate(user=plans['alice'])
        r = self._actualiser(api_client, plans['op_arch'], cs1.pk, cs11.pk)
        assert r.status_code == 200, r.content
        obj = PassageReferentielObjet.objects.get(operation=plans['op_arch'])
        assert obj.statut == 'actualise' and obj.type_choisi == cs1

    def test_type_quelconque_refuse_hors_brouillon(self, api_client, referentiel, plans):
        """Hors brouillon, seul le type d'une action touchée par le passage change."""
        _appliquer(referentiel, envoyer_email=False)
        plan, (op,) = _plan_avec_actions('valide', (_type('GE.1'), None))
        plan.referents.add(plans['alice'])
        api_client.force_authenticate(user=plans['alice'])
        r = self._actualiser(api_client, op, _type('CS.1').pk, _type('GE.1').pk)
        assert r.status_code == status.HTTP_403_FORBIDDEN

    def test_devient_cs_demande_un_suivi(self, api_client, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        cs1 = _type('CS.1')
        op = plans['op_ei']
        api_client.force_authenticate(user=plans['alice'])
        r = self._actualiser(api_client, op, cs1.pk, referentiel['ei3'].pk)
        assert r.status_code == 400 and r.data['code'] == 'suivi_requis'
        incomplet = {**SUIVI_NOUVEAU, 'cibles_principales': ''}
        r = self._actualiser(api_client, op, cs1.pk, referentiel['ei3'].pk, suivi=incomplet)
        assert r.status_code == 400
        r = self._actualiser(api_client, op, cs1.pk, referentiel['ei3'].pk, suivi=SUIVI_NOUVEAU)
        assert r.status_code == 200, r.content
        op.refresh_from_db()
        suivi = op.id_suivi
        assert suivi.intitule == 'Étude des facteurs' and suivi.id_type_action == cs1
        assert suivi.id_pg == plans['p1']
        assert [p.nom_protocole for p in suivi.protocoles.all()] == ['Protocole local']

    def test_devient_cs_avec_un_suivi_existant(self, api_client, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        cs1 = _type('CS.1')
        existant = SuiviInventaireFactory(id_pg=plans['p1'], id_type_action=cs1)
        api_client.force_authenticate(user=plans['alice'])
        r = self._actualiser(api_client, plans['op_ei'], cs1.pk, referentiel['ei3'].pk,
                             suivi={'id_suivi': existant.pk})
        assert r.status_code == 200, r.content
        plans['op_ei'].refresh_from_db()
        assert plans['op_ei'].id_suivi == existant
        assert plans['op_ei'].est_suivi_existant
        assert SuiviInventaire.objects.filter(id_pg=plans['p1']).count() == 2

    def test_hors_des_plans_de_l_utilisateur(self, api_client, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        api_client.force_authenticate(user=plans['bob'])   # pas référent de p2
        r = self._actualiser(api_client, plans['op_arb2'], _type('CS.1').pk, referentiel['cs8'].pk)
        assert r.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_accepter_toutes_les_propositions(self, api_client, referentiel, plans):
        """Seules les actions à un équivalent unique sont posées ; une action qui
        deviendrait CS sans suivi, ou à plusieurs équivalents, attend un choix."""
        _appliquer(referentiel, envoyer_email=False)
        api_client.force_authenticate(user=plans['alice'])
        r = api_client.post('/api/plans/referentiel-actions/accepter-propositions/', {},
                            format='json')
        assert r.status_code == 200, r.content
        assert r.data == {'acceptees': 0, 'plusieurs_options': 2, 'suivi_requis': 1}
        # Une fois le suivi rattaché, EI3 n'a plus qu'un équivalent à accepter.
        plans['op_ei'].id_suivi = SuiviInventaireFactory(id_pg=plans['p1'])
        plans['op_ei'].save()
        r = api_client.post('/api/plans/referentiel-actions/accepter-propositions/',
                            {'plan': plans['p1'].pk}, format='json')
        assert r.data['acceptees'] == 1
        plans['op_ei'].refresh_from_db()
        assert plans['op_ei'].id_type_action == _type('CS.1')
        assert PassageReferentielObjet.objects.get(operation=plans['op_ei']).statut == 'actualise'

    def test_liste_a_actualiser(self, api_client, referentiel, plans):
        _appliquer(referentiel, envoyer_email=False)
        api_client.force_authenticate(user=plans['alice'])
        r = api_client.get('/api/plans/referentiel-actions/a-actualiser/')
        assert r.status_code == 200
        assert r.data['total_a_actualiser'] == 3
        par_plan = {p['id_pg']: p for p in r.data['plans']}
        item = next(a for a in par_plan[plans['p1'].pk]['a_actualiser']
                    if a['ancien_code'] == 'CS8')
        assert [o['code'] for o in item['options']] == ['CS.1', 'CS.1.1']
        assert item['type_actuel_code'] == 'CS8' and item['a_un_suivi']
        # Les changements automatiques (sûrs et probables) sont listés, modifiables.
        assert [a['ancien_code'] for a in par_plan[plans['p2'].pk]['automatiques']] == ['CI2']
        assert [a['ancien_code'] for a in par_plan[plans['p3'].pk]['automatiques']] == ['CS14']
        api_client.force_authenticate(user=plans['bob'])
        r = api_client.get('/api/plans/referentiel-actions/a-actualiser/')
        assert {p['id_pg'] for p in r.data['plans']} == {plans['p1'].pk}

    def test_compte_pour_le_bandeau(self, api_client, referentiel, plans):
        api_client.force_authenticate(user=plans['alice'])
        url = '/api/plans/referentiel-actions/a-actualiser/compte/'
        assert api_client.get(url).data == {'total': 0, 'automatiques': 0, 'vers': None}
        _appliquer(referentiel, envoyer_email=False)
        assert api_client.get(url).data == {'total': 3, 'automatiques': 3, 'vers': 'Test V1'}
        api_client.force_authenticate(user=plans['bob'])   # référent du seul p1
        assert api_client.get(url).data['total'] == 2
        api_client.force_authenticate(user=RoleFactory())
        assert api_client.get(url).data['total'] == 0

    def test_fiche_puis_formulaire(self, api_client, referentiel, plans):
        """Formulaire (plan brouillon) : le type choisi solde l'attente ; un
        `id_type_action_attendu` périmé est refusé."""
        _appliquer(referentiel, envoyer_email=False)
        api_client.force_authenticate(user=plans['alice'])
        op = plans['op_arb2']
        fiche = api_client.get(f'/api/plans/operations/{op.pk}/').data
        aa = fiche['type_action_a_actualiser']
        assert aa['ancien_code'] == 'CS8'
        assert [o['code'] for o in aa['options']] == ['CS.1', 'CS.1.1']
        cs11 = _type('CS.1.1')
        r = api_client.patch(f'/api/plans/operations/{op.pk}/',
                             {'id_type_action': cs11.pk,
                              'id_type_action_attendu': referentiel['cs8'].pk},
                             format='json')
        assert r.status_code == 200, r.content
        assert PassageReferentielObjet.objects.get(operation=op).statut == 'actualise'
        r = api_client.patch(f'/api/plans/operations/{op.pk}/',
                             {'id_type_action': _type('CS.1').pk,
                              'id_type_action_attendu': referentiel['cs8'].pk},
                             format='json')
        assert r.status_code == 400
        assert 'id_type_action' in r.data


@pytest.mark.django_db
def test_gestref_v1_couvre_tous_les_codes_eden():
    """La version livrée se lit, écarte CP, et la table couvre chaque type
    d'action du fichier des nomenclatures (codification Eden 62)."""
    d = ref.charger_version('gestref_v1')
    assert d.depuis == 'EDEN62' and 'CP' not in d.codes_categories
    assert not any(c.startswith('CP') for c in d.codes_types)
    assert any(len(c.options) > 1 for c in d.correspondance.values())
    sql = (Path(ref.DOSSIER_REFERENTIELS).parent / 'nomenclatures_inserts.sql').read_text()
    eden = set()
    for ligne in sql.splitlines():
        if ligne.startswith('INSERT') and 'VALUES (' in ligne:
            valeurs = ligne.split('VALUES (', 1)[1].split(', ')
            if valeurs[1] == '51':
                eden.add(valeurs[2].strip("'"))
    assert len(eden) > 300
    assert eden - set(d.correspondance) == set()


@pytest.mark.django_db
def test_fiche_action_affiche_le_type_a_actualiser(referentiel, plans):
    """Excel et Word : l'ancien type, marqué « à actualiser »."""
    import io

    from docx import Document
    from openpyxl import load_workbook

    from apps.plans.services_export_fiche_action import build_fiche_action_workbook
    from apps.plans.services_export_fiche_action_word import build_fiche_action_docx

    _appliquer(referentiel, envoyer_email=False)
    attendu = "CS8 — Inventaire de la faune (ancien référentiel, à actualiser)"
    op = plans['op_arb']
    contenu = build_fiche_action_workbook(plans['p1'], operation_ids=[op.pk])
    wb = load_workbook(io.BytesIO(contenu if isinstance(contenu, bytes) else contenu.getvalue()))
    cellules = {c.value for ws in wb.worksheets for row in ws.iter_rows() for c in row}
    assert attendu in cellules
    docx = build_fiche_action_docx(plans['p1'], operation_ids=[op.pk])
    doc = Document(io.BytesIO(docx if isinstance(docx, bytes) else docx.getvalue()))
    textes = {c.text for t in doc.tables for r in t.rows for c in r.cells}
    assert attendu in textes
