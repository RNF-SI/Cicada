"""#803 — Un seul suivi par rang : il suit le plan d'une version à l'autre.

Une nouvelle version au même rang (modification, prolongation, mi-parcours) est
le même plan de gestion. À sa validation, le suivi saisi sur les versions
antérieures du rang y est **déplacé** ; elles renvoient vers elle et leur suivi
n'est plus saisissable. Le lien entre une action et sa copie (``origine``) fait
suivre le suivi d'une action même modifiée ; une action supprimée garde le sien
sur l'ancienne version, une action ajoutée part vide.
"""
from datetime import date
from decimal import Decimal

import pytest

from apps.plans.models import PlanGestion
from apps.plans.models_indicateurs import (
    IndicateurMesure, IndicateurRealisationGlobale, Mesure, Metrique,
)
from apps.plans.models_operations import (
    Financeur, Operation, OperationAnnee, OperationAnneeOrganisme, OperationAnneeRH,
    OperationRealisationGlobale, Poste, RealisationFinanceur, RealisationOperationAnnee,
    RealisationOperationAnneeOrganisme, RealisationOperationAnneeRH,
)
from apps.plans.models_planification import (
    AjustementAnnuel, AjustementAnnuelFinanceur, AjustementAnnuelRH,
)
from apps.plans.services import PlanDuplicationService
from apps.plans.suivi_version import rattraper, transferer_suivi
from tests.factories.enjeux import NomenclatureNiveauRealisationFactory
from tests.integrite.socle import construire_plan_complet

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

MODELES_DE_SUIVI = (
    RealisationOperationAnnee, RealisationOperationAnneeOrganisme, RealisationOperationAnneeRH,
    RealisationFinanceur, OperationRealisationGlobale, AjustementAnnuel, Mesure,
    IndicateurMesure, IndicateurRealisationGlobale,
)


def _comptes():
    return {m.__name__: m._base_manager.count() for m in MODELES_DE_SUIVI}


def _rea(action, annee):
    return RealisationOperationAnnee.objects.filter(
        id_operation_annee__id_operation=action, id_operation_annee__annee=annee).first()


def _copie(action, plan):
    """La copie de ``action`` dans ``plan``."""
    return Operation.objects.get(origine=action, metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan)


def _valider(api_client, plan, user):
    api_client.force_authenticate(user=user)
    rep = api_client.post(f'/api/plans/plans/{plan.pk}/change-status/',
                          {'new_status': 'valide'}, format='json')
    assert rep.status_code == 200, rep.content
    plan.refresh_from_db()
    return rep.json()


@pytest.fixture
def pc():
    pc = construire_plan_complet(statut='valide')
    # Scores d'indicateur saisis (surcharges annuelle et globale).
    indicateur = pc.metrique.id_indicateur
    IndicateurMesure.objects.create(id_indicateur=indicateur, annee=pc.annee - 1, score_override=4)
    IndicateurRealisationGlobale.objects.create(id_indicateur=indicateur, score_override=3)
    # Niveau global et réglages du suivi de l'action (#355, #741).
    OperationRealisationGlobale.objects.create(
        id_operation=pc.action, commentaire_override='Bilan de l’action',
        declinaison_par_type_cout_realise=True)
    return pc


@pytest.fixture
def v2(pc):
    """Nouvelle version au même rang (« Créer une nouvelle version »), en brouillon."""
    return PlanDuplicationService.duplicate_plan(pc.plan, pc.admin)


class TestCopieDUneVersion:
    def test_la_copie_relie_chaque_objet_a_son_original(self, pc, v2):
        copie = _copie(pc.action, v2)
        assert copie.origine_id == pc.action.pk
        assert Metrique.objects.get(origine=pc.metrique).id_indicateur.origine_id == \
            pc.metrique.id_indicateur_id
        assert Poste.objects.get(id_pg=v2).origine_id == pc.poste.pk
        assert v2.suivi_poursuivi_dans_id is None

    def test_le_suivi_ne_bouge_pas_tant_que_la_version_est_en_brouillon(self, pc, v2, api_client):
        assert _rea(pc.action, pc.annee - 1) is not None
        assert _rea(_copie(pc.action, v2), pc.annee - 1) is None
        pc.plan.refresh_from_db()
        assert pc.plan.suivi_poursuivi_dans_id is None
        # La saisie continue sur la version en vigueur.
        api_client.force_authenticate(user=pc.referent)
        assert api_client.get(f'/api/plans/plans/{pc.plan.pk}/').json()['peut_saisir_suivis'] is True

    def test_une_action_copiee_dans_le_meme_plan_part_sans_lien(self, pc):
        copie = PlanDuplicationService._dup(_copie_source := pc.action, pc.admin)
        assert copie.origine is None and _copie_source.origine is None


class TestBasculeALaValidation:
    def test_tout_le_suivi_passe_dans_la_nouvelle_version_sans_doublon(self, pc, v2, api_client):
        avant = _comptes()
        reponse = _valider(api_client, v2, pc.admin)

        assert _comptes() == avant, "déplacé, jamais copié ni perdu"
        assert reponse['statut'] == 'modifie'
        assert reponse['suivi_repris']['actions'] == 2
        action_v2, globale_v2 = _copie(pc.action, v2), _copie(pc.action_globale, v2)
        for action in (action_v2, globale_v2):
            for an in (pc.annee - 1, pc.annee):
                rea = _rea(action, an)
                assert rea is not None and rea.commentaires.startswith('Suivi PC-0')
                # Temps et financeurs réalisés : postes et financeurs de la v2.
                rh = RealisationOperationAnneeRH.objects.get(id_realisation_operation_annee=rea)
                assert rh.id_poste.id_pg_id == v2.pk and rh.jours == Decimal('11.00')
                assert rh.id_operation_annee_rh.id_operation_annee.id_operation_id == action.pk
                fin = RealisationFinanceur.objects.get(id_realisation_operation_annee=rea)
                assert fin.id_financeur.id_pg_id == v2.pk
                # Réalisé par organisme, sur les lignes organisme de la v2.
                assert RealisationOperationAnneeOrganisme.objects.filter(
                    id_operation_annee_organisme__id_operation_annee__id_operation=action,
                    id_operation_annee_organisme__id_operation_annee__annee=an).count() == 2
        for action in (pc.action, pc.action_globale):
            assert not RealisationOperationAnnee.objects.filter(
                id_operation_annee__id_operation=action).exists()

        assert OperationRealisationGlobale.objects.get(id_operation=action_v2).commentaire_override \
            == 'Bilan de l’action'
        ajustement = AjustementAnnuel.objects.get(id_operation=action_v2)
        assert AjustementAnnuelRH.objects.get(id_ajustement_annuel=ajustement).id_poste.id_pg_id == v2.pk
        assert AjustementAnnuelFinanceur.objects.get(
            id_ajustement_annuel=ajustement).id_financeur.id_pg_id == v2.pk
        metrique_v2 = Metrique.objects.get(origine=pc.metrique)
        assert sorted(m.valeur for m in metrique_v2.mesures.all()) == ['112', '116']
        assert IndicateurMesure.objects.get(id_indicateur=metrique_v2.id_indicateur).score_override == 4
        assert IndicateurRealisationGlobale.objects.get(
            id_indicateur=metrique_v2.id_indicateur).score_override == 3
        # Aucun financeur en double : celui de la v2 (copié avec l'action) est repris.
        assert Financeur.objects.filter(id_pg=v2).count() == 1

    def test_l_ancienne_version_renvoie_vers_la_nouvelle_en_lecture_seule(self, pc, v2, api_client):
        _valider(api_client, v2, pc.admin)
        api_client.force_authenticate(user=pc.referent)
        detail = api_client.get(f'/api/plans/plans/{pc.plan.pk}/').json()
        assert detail['suivi_poursuivi_dans']['id_pg'] == v2.pk
        assert detail['suivi_poursuivi_dans']['slug'] == v2.slug
        assert detail['peut_saisir_suivis'] is False
        assert detail['peut_voir_suivis'] is True
        assert api_client.get(f'/api/plans/plans/{v2.pk}/').json()['suivi_poursuivi_dans'] is None

        # Saisir sur l'ancienne version est refusé, même pour un super admin.
        api_client.force_authenticate(user=pc.admin)
        rep = api_client.post('/api/plans/realisations/upsert/', {
            'id_operation': pc.action.pk, 'annee': pc.annee + 1,
            'commentaires': 'Saisie sur la v1'}, format='json')
        assert rep.status_code == 403
        assert not RealisationOperationAnnee.objects.filter(commentaires='Saisie sur la v1').exists()
        # … et accepté sur la nouvelle.
        rep = api_client.post('/api/plans/realisations/upsert/', {
            'id_operation': _copie(pc.action, v2).pk, 'annee': pc.annee + 1,
            'commentaires': 'Saisie sur la v2'}, format='json')
        assert rep.status_code in (200, 201), rep.content

    def test_un_nouveau_rang_ne_reprend_rien(self, pc, api_client):
        rang_suivant = PlanDuplicationService.duplicate_plan(pc.plan, pc.admin)
        rang_suivant.rang = (pc.plan.rang or 1) + 1
        rang_suivant.save(update_fields=['rang'])
        avant = _rea(pc.action, pc.annee - 1)
        _valider(api_client, rang_suivant, pc.admin)
        assert _rea(pc.action, pc.annee - 1) == avant
        pc.plan.refresh_from_db()
        assert pc.plan.suivi_poursuivi_dans_id is None


class TestEvolutionDesActions:
    """Ce que devient la saisie quand l'action change entre les deux versions."""

    def test_action_supprimee_son_suivi_reste_sur_l_ancienne_version(self, pc, v2, api_client):
        _copie(pc.action_globale, v2).delete()
        _valider(api_client, v2, pc.admin)
        assert _rea(pc.action_globale, pc.annee - 1) is not None
        assert _rea(_copie(pc.action, v2), pc.annee - 1) is not None

    def test_action_ajoutee_part_sans_suivi(self, pc, v2, api_client):
        nouvelle = PlanDuplicationService._dup(_copie(pc.action, v2), pc.admin,
                                               code_operation='PC-99', libelle='Nouvelle')
        nouvelle.save()
        nouvelle.metriques.add(Metrique.objects.get(origine=pc.metrique))
        _valider(api_client, v2, pc.admin)
        assert not RealisationOperationAnnee.objects.filter(
            id_operation_annee__id_operation=nouvelle).exists()
        assert _rea(_copie(pc.action, v2), pc.annee - 1) is not None

    def test_action_renommee_et_recodee_garde_son_suivi(self, pc, v2, api_client):
        copie = _copie(pc.action, v2)
        copie.libelle, copie.code_operation = 'Fauche tardive des prairies', 'FA-07'
        copie.save()
        _valider(api_client, v2, pc.admin)
        assert _rea(copie, pc.annee - 1).commentaires == f'Suivi PC-01 {pc.annee - 1}'

    def test_annee_retiree_de_la_programmation_garde_son_suivi_sans_prevu(self, pc, v2, api_client):
        copie = _copie(pc.action, v2)
        OperationAnnee.objects.filter(id_operation=copie, annee=pc.annee - 1).delete()
        _valider(api_client, v2, pc.admin)
        rea = _rea(copie, pc.annee - 1)
        assert rea is not None
        oa = rea.id_operation_annee
        assert oa.periodicite is False and oa.budget is None
        assert oa.organismes.count() == 2  # réalisé par organisme repris
        rh = RealisationOperationAnneeRH.objects.get(id_realisation_operation_annee=rea)
        assert rh.id_operation_annee_rh is None and rh.jours == Decimal('11.00')

    def test_organisme_retire_d_une_annee_garde_son_realise(self, pc, v2, api_client):
        copie = _copie(pc.action, v2)
        OperationAnneeOrganisme.objects.filter(
            id_operation_annee__id_operation=copie, id_organisme=pc.org_b).delete()
        _valider(api_client, v2, pc.admin)
        assert RealisationOperationAnneeOrganisme.objects.filter(
            id_operation_annee_organisme__id_operation_annee__id_operation=copie,
            id_operation_annee_organisme__id_organisme=pc.org_b).count() == 2

    def test_poste_supprime_le_temps_realise_reste_sans_poste(self, pc, v2, api_client):
        Poste.objects.get(id_pg=v2).delete()
        _valider(api_client, v2, pc.admin)
        rea = _rea(_copie(pc.action, v2), pc.annee - 1)
        rh = RealisationOperationAnneeRH.objects.get(id_realisation_operation_annee=rea)
        assert rh.id_poste is None and rh.jours == Decimal('11.00')
        assert rh.id_organisme_id == pc.poste.id_organisme_id or rh.id_organisme_id is None

    def test_financeur_renomme_le_realise_garde_son_financeur(self, pc, v2, api_client):
        Financeur.objects.filter(id_pg=v2).update(nom='Région')
        _valider(api_client, v2, pc.admin)
        rea = _rea(_copie(pc.action, v2), pc.annee - 1)
        fin = RealisationFinanceur.objects.get(id_realisation_operation_annee=rea)
        assert fin.id_financeur.id_pg_id == v2.pk and fin.id_financeur.nom == 'Agence de l’eau'
        assert fin.montant == Decimal('3000.00')

    def test_metrique_supprimee_ses_mesures_restent_sur_l_ancienne_version(self, pc, v2, api_client):
        Metrique.objects.get(origine=pc.metrique).delete()
        _valider(api_client, v2, pc.admin)
        assert pc.metrique.mesures.count() == 2

    def test_ventilation_changee_le_suivi_suit(self, pc, v2, api_client):
        copie = _copie(pc.action, v2)
        copie.ventilation_mode = 'none'
        copie.declinaison_par_type_cout = False
        copie.save()
        _valider(api_client, v2, pc.admin)
        assert _rea(copie, pc.annee).budget_realise == Decimal('9000.00')


class TestConflitsEtChaines:
    def test_une_annee_deja_saisie_sur_la_nouvelle_version_prime(self, pc, v2, api_client):
        copie = _copie(pc.action, v2)
        oa = OperationAnnee.objects.get(id_operation=copie, annee=pc.annee - 1)
        RealisationOperationAnnee.objects.create(
            id_operation_annee=oa, commentaires='Ressaisi sur la v2',
            id_niveau_realisation=NomenclatureNiveauRealisationFactory(mnemonique='EN_COURS'))
        _valider(api_client, v2, pc.admin)
        assert _rea(copie, pc.annee - 1).commentaires == 'Ressaisi sur la v2'
        assert _rea(pc.action, pc.annee - 1).commentaires == f'Suivi PC-01 {pc.annee - 1}'
        assert _rea(copie, pc.annee).commentaires == f'Suivi PC-01 {pc.annee}'

    def test_trois_versions_le_suivi_finit_sur_la_derniere(self, pc, v2, api_client):
        _valider(api_client, v2, pc.admin)
        v3 = PlanDuplicationService.duplicate_plan(v2, pc.admin)
        _valider(api_client, v3, pc.admin)
        action_v3 = _copie(_copie(pc.action, v2), v3)
        assert _rea(action_v3, pc.annee - 1) is not None
        pc.plan.refresh_from_db()
        v2.refresh_from_db()
        assert pc.plan.suivi_poursuivi_dans_id == v3.pk
        assert v2.suivi_poursuivi_dans_id == v3.pk

    def test_idempotent(self, pc, v2, api_client):
        _valider(api_client, v2, pc.admin)
        avant = _comptes()
        assert sum(transferer_suivi(v2).values()) == 0
        assert _comptes() == avant

    def test_supprimer_la_version_qui_porte_le_suivi_le_rend_a_la_precedente(
            self, pc, v2, api_client):
        _valider(api_client, v2, pc.admin)
        avant = _comptes()
        api_client.force_authenticate(user=pc.admin)
        rep = api_client.post(f'/api/plans/plans/{v2.pk}/delete-version/')
        assert rep.status_code == 200, rep.content
        assert _comptes() == avant
        assert _rea(pc.action, pc.annee - 1) is not None
        pc.plan.refresh_from_db()
        assert pc.plan.suivi_poursuivi_dans_id is None


class TestRattrapage:
    """Migration plans.0153 : versions créées avant #803, sans lien `origine`."""

    def _version_sans_lien(self, pc):
        v2 = PlanDuplicationService.duplicate_plan(pc.plan, pc.admin)
        for modele in (Operation, Metrique, Poste):
            modele.objects.filter(origine__isnull=False).update(origine=None)
        from apps.plans.models_indicateurs import Indicateur
        Indicateur.objects.filter(origine__isnull=False).update(origine=None)
        return v2

    def test_les_versions_existantes_sont_appariees_puis_rattrapees(self, pc):
        v2 = self._version_sans_lien(pc)
        PlanGestion.objects.filter(pk=v2.pk).update(statut='modifie')
        avant = _comptes()
        rattraper()
        assert _comptes() == avant
        action_v2 = Operation.objects.get(origine=pc.action)
        assert _rea(action_v2, pc.annee - 1) is not None
        assert Metrique.objects.get(origine=pc.metrique).mesures.count() == 2
        pc.plan.refresh_from_db()
        assert pc.plan.suivi_poursuivi_dans_id == v2.pk

    def test_un_brouillon_n_est_qu_apparie(self, pc):
        v2 = self._version_sans_lien(pc)
        rattraper()
        assert Operation.objects.get(origine=pc.action) is not None
        assert _rea(pc.action, pc.annee - 1) is not None
        pc.plan.refresh_from_db()
        assert pc.plan.suivi_poursuivi_dans_id is None
        assert v2.statut == 'draft'

    def test_une_action_ambigue_n_est_pas_appariee(self, pc):
        v2 = self._version_sans_lien(pc)
        PlanGestion.objects.filter(pk=v2.pk).update(statut='modifie')
        # Deux actions de même libellé et sans code de part et d'autre : rien n'est deviné.
        Operation.objects.filter(pk__in=[pc.action.pk, pc.action_globale.pk]).update(
            libelle='Fauche', code_operation='')
        Operation.objects.exclude(pk__in=[pc.action.pk, pc.action_globale.pk]).update(
            libelle='Fauche', code_operation='')
        rattraper()
        assert not Operation.objects.filter(origine__isnull=False).exists()
        assert _rea(pc.action, pc.annee - 1) is not None

    def test_une_instance_sans_chaine_n_est_pas_touchee(self, pc):
        avant = _comptes()
        rattraper()
        assert _comptes() == avant
        assert not PlanGestion.objects.exclude(suivi_poursuivi_dans=None).exists()
