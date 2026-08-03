"""
Partage d'un résultat attendu entre plusieurs objectifs opérationnels (#585).

C'est le MÊME résultat attendu, avec ses indicateurs, qui apparaît sous chaque
objectif lié : toute modification se répercute des deux côtés. L'objectif
**porteur** (`ResultatAttendu.id_oo`) reste le rattachement de référence, celui
sur lequel s'appuient la remontée au plan, les exports et la duplication.
"""

import pytest
from rest_framework import status

from apps.plans.models_enjeux import CorRaOo, ResultatAttendu
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurPressionFactory, ObjectifOperationnelFactory,
    ResultatAttenduFactory,
)
from tests.factories.plans import CorSitePgFactory, PlanGestionFactory
from tests.factories.users import RoleFactory, SiteFactory


@pytest.fixture
def contexte(db):
    """Un plan en brouillon, deux objectifs opérationnels, un résultat attendu."""
    referent = RoleFactory()
    site = SiteFactory()
    plan = PlanGestionFactory(statut='draft')
    CorSitePgFactory(plan_de_gestion=plan, site=site)
    plan.referents.add(referent)

    enjeu = EnjeuFactory(id_pg=plan)
    oo_porteur = ObjectifOperationnelFactory(id_enjeu=enjeu)
    oo_autre = ObjectifOperationnelFactory(id_enjeu=enjeu)
    ra = ResultatAttenduFactory(id_oo=oo_porteur, id_utilisateur_ajout=referent)
    return {
        'plan': plan, 'referent': referent, 'enjeu': enjeu,
        'oo_porteur': oo_porteur, 'oo_autre': oo_autre, 'ra': ra,
    }


@pytest.mark.unit
class TestInvariantPorteur:

    def test_la_creation_pose_le_lien_de_lobjectif_porteur(self, contexte):
        """Sans ça, un RA créé par l'import ou le seed serait invisible des
        listes construites sur la liaison."""
        assert CorRaOo.objects.filter(
            id_ra=contexte['ra'], id_oo=contexte['oo_porteur']
        ).exists()

    def test_oo_ids_contient_toujours_le_porteur(self, contexte):
        ra = contexte['ra']
        assert list(ra.objectifs_operationnels.values_list('pk', flat=True)) == [
            contexte['oo_porteur'].pk
        ]

    def test_le_lien_ne_se_duplique_pas_a_chaque_sauvegarde(self, contexte):
        ra = contexte['ra']
        ra.libelle = 'Modifié'
        ra.save()
        ra.save()

        assert CorRaOo.objects.filter(id_ra=ra).count() == 1


@pytest.mark.integration
class TestPartageApi:

    def _url(self, ra, verbe):
        return f'/api/plans/resultats-attendus/{ra.pk}/{verbe}/'

    def test_lier_un_ra_a_un_second_objectif(self, api_client, contexte):
        api_client.force_authenticate(user=contexte['referent'])

        response = api_client.post(
            self._url(contexte['ra'], 'link'),
            {'oo_id': contexte['oo_autre'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert sorted(response.data['oo_ids']) == sorted(
            [contexte['oo_porteur'].pk, contexte['oo_autre'].pk]
        )

    def test_le_ra_partage_apparait_sous_les_deux_objectifs(self, api_client, contexte):
        """C'est la même entité, pas une copie : l'indicateur suit."""
        ra = contexte['ra']
        IndicateurPressionFactory(id_resultat_attendu=ra, nom_indicateur='IND partagé')
        api_client.force_authenticate(user=contexte['referent'])
        api_client.post(
            self._url(ra, 'link'), {'oo_id': contexte['oo_autre'].pk}, format='json',
        )

        for oo in (contexte['oo_porteur'], contexte['oo_autre']):
            reponse = api_client.get(
                f'/api/plans/resultats-attendus/by-oo/{oo.pk}/'
            )
            libelles = [r['libelle'] for r in reponse.data['resultats_attendus']]
            assert ra.libelle in libelles, (oo.pk, libelles)
            indicateurs = reponse.data['resultats_attendus'][0]['indicateurs']
            assert [i['nom_indicateur'] for i in indicateurs] == ['IND partagé']

    def test_lier_deux_fois_est_sans_effet(self, api_client, contexte):
        api_client.force_authenticate(user=contexte['referent'])
        for _ in range(2):
            api_client.post(
                self._url(contexte['ra'], 'link'),
                {'oo_id': contexte['oo_autre'].pk}, format='json',
            )

        assert CorRaOo.objects.filter(id_ra=contexte['ra']).count() == 2

    def test_lier_a_un_objectif_dun_autre_plan_est_refuse(self, api_client, contexte):
        autre_plan = PlanGestionFactory(statut='draft')
        oo_etranger = ObjectifOperationnelFactory(id_enjeu=EnjeuFactory(id_pg=autre_plan))
        api_client.force_authenticate(user=contexte['referent'])

        response = api_client.post(
            self._url(contexte['ra'], 'link'), {'oo_id': oo_etranger.pk}, format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_lier_hors_brouillon_est_refuse(self, api_client, contexte):
        """Verrou #248 : le partage est une modification du contenu."""
        plan = contexte['plan']
        plan.statut = 'valide'
        plan.save(update_fields=['statut'])
        api_client.force_authenticate(user=contexte['referent'])

        response = api_client.post(
            self._url(contexte['ra'], 'link'),
            {'oo_id': contexte['oo_autre'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_detacher_un_objectif_partage(self, api_client, contexte):
        api_client.force_authenticate(user=contexte['referent'])
        api_client.post(
            self._url(contexte['ra'], 'link'),
            {'oo_id': contexte['oo_autre'].pk}, format='json',
        )

        response = api_client.post(
            self._url(contexte['ra'], 'unlink'),
            {'oo_id': contexte['oo_autre'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data['oo_ids'] == [contexte['oo_porteur'].pk]
        # Le résultat attendu lui-même survit : on n'a retiré qu'un partage.
        assert ResultatAttendu.objects.filter(pk=contexte['ra'].pk).exists()

    def test_detacher_lobjectif_porteur_est_refuse(self, api_client, contexte):
        """Ce serait un déplacement, pas un départage : le RA se retrouverait
        sans parent de référence."""
        api_client.force_authenticate(user=contexte['referent'])

        response = api_client.post(
            self._url(contexte['ra'], 'unlink'),
            {'oo_id': contexte['oo_porteur'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert CorRaOo.objects.filter(id_ra=contexte['ra']).count() == 1


@pytest.mark.integration
class TestCopieApi:
    """La copie produit un duplicata INDÉPENDANT, là où `link` partage la même
    entité. Les deux sont proposés dans le même dialogue : la différence doit
    être réelle en base."""

    def _url(self, ra, verbe):
        return f'/api/plans/resultats-attendus/{ra.pk}/{verbe}/'

    def test_copier_cree_un_nouveau_ra_avec_ses_indicateurs(self, api_client, contexte):
        ra = contexte['ra']
        IndicateurPressionFactory(id_resultat_attendu=ra, nom_indicateur='IND source')
        api_client.force_authenticate(user=contexte['referent'])

        response = api_client.post(
            self._url(ra, 'copy'), {'oo_id': contexte['oo_autre'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data['id_ra'] != ra.pk
        assert response.data['id_oo'] == contexte['oo_autre'].pk
        assert [i['nom_indicateur'] for i in response.data['indicateurs']] == ['IND source']

    def test_la_copie_est_independante_de_loriginal(self, api_client, contexte):
        ra = contexte['ra']
        api_client.force_authenticate(user=contexte['referent'])
        copie_id = api_client.post(
            self._url(ra, 'copy'), {'oo_id': contexte['oo_autre'].pk}, format='json',
        ).data['id_ra']

        api_client.patch(
            f'/api/plans/resultats-attendus/{copie_id}/',
            {'libelle': 'Libellé de la copie'}, format='json',
        )

        ra.refresh_from_db()
        assert ra.libelle != 'Libellé de la copie'
        # ...et l'original n'a pas gagné de partage au passage.
        assert CorRaOo.objects.filter(id_ra=ra).count() == 1

    def test_copier_hors_brouillon_est_refuse(self, api_client, contexte):
        plan = contexte['plan']
        plan.statut = 'valide'
        plan.save(update_fields=['statut'])
        api_client.force_authenticate(user=contexte['referent'])

        response = api_client.post(
            self._url(contexte['ra'], 'copy'),
            {'oo_id': contexte['oo_autre'].pk}, format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
