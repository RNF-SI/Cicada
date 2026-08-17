"""
Partage d'un indicateur entre plusieurs parents (#585).

Deux relations, sur les deux branches de l'arborescence :

- un indicateur **d'état** peut être partagé entre plusieurs niveaux d'exigence ;
- un indicateur **de pression** entre plusieurs résultats attendus.

C'est le MÊME indicateur, avec ses métriques et ses actions, qui apparaît sous
chaque parent lié : toute modification se répercute partout. Le parent
**porteur** (``id_ne`` / ``id_resultat_attendu``) reste le rattachement de
référence, celui sur lequel s'appuient la remontée au plan, les exports et la
duplication.
"""

import pytest
from rest_framework import status

from apps.plans.models_indicateurs import (
    CorIndicateurNe, CorIndicateurRa, Indicateur,
)
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, IndicateurPressionFactory,
    MetriqueFactory, NiveauExigenceFactory, ObjectifLongTermeFactory,
    ObjectifOperationnelFactory, ResultatAttenduFactory,
)
from tests.factories.plans import CorSitePgFactory, PlanGestionFactory
from tests.factories.users import RoleFactory, SiteFactory


def _plan_brouillon():
    referent = RoleFactory()
    plan = PlanGestionFactory(statut='draft')
    CorSitePgFactory(plan_de_gestion=plan, site=SiteFactory())
    plan.referents.add(referent)
    return plan, referent


@pytest.fixture
def etat(db):
    """Un indicateur d'état, son niveau d'exigence porteur et un second niveau."""
    plan, referent = _plan_brouillon()
    olt = ObjectifLongTermeFactory(id_enjeu=EnjeuFactory(id_pg=plan))
    ne_porteur = NiveauExigenceFactory(id_olt=olt)
    ne_autre = NiveauExigenceFactory(id_olt=olt)
    indicateur = IndicateurFactory(id_ne=ne_porteur, id_utilisateur_ajout=referent)
    return {
        'plan': plan, 'referent': referent,
        'porteur': ne_porteur, 'autre': ne_autre, 'indicateur': indicateur,
    }


@pytest.fixture
def pression(db):
    """Un indicateur de pression, son résultat attendu porteur et un second."""
    plan, referent = _plan_brouillon()
    oo = ObjectifOperationnelFactory(id_enjeu=EnjeuFactory(id_pg=plan))
    ra_porteur = ResultatAttenduFactory(id_oo=oo)
    ra_autre = ResultatAttenduFactory(id_oo=oo)
    indicateur = IndicateurPressionFactory(
        id_resultat_attendu=ra_porteur, id_utilisateur_ajout=referent,
    )
    return {
        'plan': plan, 'referent': referent,
        'porteur': ra_porteur, 'autre': ra_autre, 'indicateur': indicateur,
    }


def _url(indicateur, verbe):
    return f'/api/plans/indicateurs/{indicateur.pk}/{verbe}/'


@pytest.mark.unit
class TestInvariantPorteur:
    """Sans lien du porteur, un indicateur créé par l'import, le seed ou la
    duplication d'un plan serait invisible des listes construites sur la
    liaison — c'est-à-dire de toute l'arborescence."""

    def test_la_creation_pose_le_lien_du_niveau_porteur(self, etat):
        assert CorIndicateurNe.objects.filter(
            id_indicateur=etat['indicateur'], id_ne=etat['porteur'],
        ).exists()

    def test_la_creation_pose_le_lien_du_resultat_attendu_porteur(self, pression):
        assert CorIndicateurRa.objects.filter(
            id_indicateur=pression['indicateur'], id_resultat_attendu=pression['porteur'],
        ).exists()

    def test_le_lien_ne_se_duplique_pas_a_chaque_sauvegarde(self, etat):
        indicateur = etat['indicateur']
        indicateur.nom_indicateur = 'Modifié'
        indicateur.save()
        indicateur.save()

        assert CorIndicateurNe.objects.filter(id_indicateur=indicateur).count() == 1

    def test_un_indicateur_detat_na_pas_de_lien_cote_resultat_attendu(self, etat):
        assert not CorIndicateurRa.objects.filter(
            id_indicateur=etat['indicateur']
        ).exists()


@pytest.mark.integration
class TestPartageIndicateurEtat:

    def test_lier_a_un_second_niveau_dexigence(self, api_client, etat):
        api_client.force_authenticate(user=etat['referent'])

        response = api_client.post(
            _url(etat['indicateur'], 'link'), {'ne_id': etat['autre'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert sorted(response.data['ne_ids']) == sorted(
            [etat['porteur'].pk, etat['autre'].pk]
        )

    def test_lindicateur_partage_apparait_sous_les_deux_niveaux(self, api_client, etat):
        """C'est la même entité, pas une copie : les métriques suivent."""
        indicateur = etat['indicateur']
        MetriqueFactory(id_indicateur=indicateur, nom_metrique='Métrique partagée')
        api_client.force_authenticate(user=etat['referent'])
        api_client.post(
            _url(indicateur, 'link'), {'ne_id': etat['autre'].pk}, format='json',
        )

        for ne in (etat['porteur'], etat['autre']):
            reponse = api_client.get(f'/api/plans/indicateurs/by-ne/{ne.pk}/')
            noms = [i['nom_indicateur'] for i in reponse.data['indicateurs']]
            assert indicateur.nom_indicateur in noms, (ne.pk, noms)
            metriques = reponse.data['indicateurs'][0]['metriques']
            assert [m['nom_metrique'] for m in metriques] == ['Métrique partagée']

    def test_lier_deux_fois_est_sans_effet(self, api_client, etat):
        api_client.force_authenticate(user=etat['referent'])
        for _ in range(2):
            api_client.post(
                _url(etat['indicateur'], 'link'), {'ne_id': etat['autre'].pk}, format='json',
            )

        assert CorIndicateurNe.objects.filter(id_indicateur=etat['indicateur']).count() == 2

    def test_lier_a_un_niveau_dun_autre_plan_est_refuse(self, api_client, etat):
        autre_plan = PlanGestionFactory(statut='draft')
        ne_etranger = NiveauExigenceFactory(
            id_olt=ObjectifLongTermeFactory(id_enjeu=EnjeuFactory(id_pg=autre_plan)),
        )
        api_client.force_authenticate(user=etat['referent'])

        response = api_client.post(
            _url(etat['indicateur'], 'link'), {'ne_id': ne_etranger.pk}, format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_lier_hors_brouillon_est_refuse(self, api_client, etat):
        """Verrou #248 : le partage est une modification du contenu."""
        plan = etat['plan']
        plan.statut = 'valide'
        plan.save(update_fields=['statut'])
        api_client.force_authenticate(user=etat['referent'])

        response = api_client.post(
            _url(etat['indicateur'], 'link'), {'ne_id': etat['autre'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_detacher_un_niveau_partage(self, api_client, etat):
        api_client.force_authenticate(user=etat['referent'])
        api_client.post(
            _url(etat['indicateur'], 'link'), {'ne_id': etat['autre'].pk}, format='json',
        )

        response = api_client.post(
            _url(etat['indicateur'], 'unlink'), {'ne_id': etat['autre'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data['ne_ids'] == [etat['porteur'].pk]
        # L'indicateur lui-même survit : on n'a retiré qu'un partage.
        assert Indicateur.objects.filter(pk=etat['indicateur'].pk).exists()

    def test_detacher_le_niveau_porteur_est_refuse(self, api_client, etat):
        """Ce serait un déplacement (cf. l'endpoint `move`), pas un départage :
        l'indicateur se retrouverait sans parent de référence."""
        api_client.force_authenticate(user=etat['referent'])

        response = api_client.post(
            _url(etat['indicateur'], 'unlink'), {'ne_id': etat['porteur'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CorIndicateurNe.objects.filter(id_indicateur=etat['indicateur']).count() == 1


@pytest.mark.integration
class TestPartageIndicateurPression:

    def test_lier_a_un_second_resultat_attendu(self, api_client, pression):
        api_client.force_authenticate(user=pression['referent'])

        response = api_client.post(
            _url(pression['indicateur'], 'link'),
            {'ra_id': pression['autre'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert sorted(response.data['ra_ids']) == sorted(
            [pression['porteur'].pk, pression['autre'].pk]
        )

    def test_lindicateur_partage_apparait_sous_les_deux_resultats(self, api_client, pression):
        indicateur = pression['indicateur']
        api_client.force_authenticate(user=pression['referent'])
        api_client.post(
            _url(indicateur, 'link'), {'ra_id': pression['autre'].pk}, format='json',
        )

        for ra in (pression['porteur'], pression['autre']):
            reponse = api_client.get(f'/api/plans/indicateurs/by-ra/{ra.pk}/')
            noms = [i['nom_indicateur'] for i in reponse.data['indicateurs']]
            assert indicateur.nom_indicateur in noms, (ra.pk, noms)

    def test_detacher_le_resultat_porteur_est_refuse(self, api_client, pression):
        api_client.force_authenticate(user=pression['referent'])

        response = api_client.post(
            _url(pression['indicateur'], 'unlink'),
            {'ra_id': pression['porteur'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestBranchesDisjointes:
    """Le partage se fait entre parents de MÊME nature : un indicateur d'état
    n'a rien à faire sous un résultat attendu, et réciproquement."""

    def test_un_indicateur_detat_refuse_une_cible_resultat_attendu(self, api_client, etat, pression):
        api_client.force_authenticate(user=etat['referent'])

        response = api_client.post(
            _url(etat['indicateur'], 'link'), {'ra_id': pression['autre'].pk}, format='json',
        )

        # L'indicateur est un indicateur d'état : c'est un `ne_id` qui est attendu.
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_un_indicateur_de_pression_refuse_une_cible_niveau_dexigence(
        self, api_client, etat, pression,
    ):
        api_client.force_authenticate(user=pression['referent'])

        response = api_client.post(
            _url(pression['indicateur'], 'link'), {'ne_id': etat['autre'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestDeplacementEtPartage:
    """`move` (#261) DÉPLACE l'indicateur ; `link` (#585) le PARTAGE. Un
    déplacement ne doit donc laisser aucun lien vers l'ancien parent, sinon
    l'indicateur resterait affiché des deux côtés."""

    def test_le_deplacement_efface_les_liens_de_lancien_parent(self, api_client, etat):
        indicateur = etat['indicateur']
        api_client.force_authenticate(user=etat['referent'])

        response = api_client.post(
            f'/api/plans/indicateurs/{indicateur.pk}/move/',
            {'new_parent_type': 'ne', 'new_parent_id': etat['autre'].pk, 'position': 0},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        liens = CorIndicateurNe.objects.filter(id_indicateur=indicateur)
        assert [lien.id_ne_id for lien in liens] == [etat['autre'].pk]

    def test_le_deplacement_vers_lautre_branche_bascule_la_liaison(self, api_client, etat, pression):
        """Un indicateur d'état déplacé sous un résultat attendu ne doit plus
        avoir de liaison côté niveau d'exigence."""
        indicateur = etat['indicateur']
        ra_cible = ResultatAttenduFactory(
            id_oo=ObjectifOperationnelFactory(id_enjeu=EnjeuFactory(id_pg=etat['plan'])),
        )
        api_client.force_authenticate(user=etat['referent'])

        response = api_client.post(
            f'/api/plans/indicateurs/{indicateur.pk}/move/',
            {'new_parent_type': 'ra', 'new_parent_id': ra_cible.pk, 'position': 0},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert not CorIndicateurNe.objects.filter(id_indicateur=indicateur).exists()
        assert CorIndicateurRa.objects.filter(
            id_indicateur=indicateur, id_resultat_attendu=ra_cible,
        ).exists()
