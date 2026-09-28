"""
Tests du socle du hub : ce sur quoi tout le reste repose.

Ils ne vérifient pas la fédération (dépôt, purge, recherche) — c'est l'objet des
étapes suivantes — mais les invariants du schéma sans lesquels elle ne peut pas
être correcte : l'instance dans les clés, les vecteurs générés, et les
référentiels servis.
"""

import pytest
from django.db.utils import IntegrityError

from apps.index.models import ContenuIndexe, PlanIndexe


class TestSante:
    def test_health_repond_sans_jeton(self, client):
        """La sonde doit répondre même quand aucun jeton n'est configuré."""
        reponse = client.get('/api/health/')
        assert reponse.status_code == 200
        assert reponse.json()['service'] == 'cicada-hub'


class TestIdentiteDesDocuments:
    """`instance_id` dans les clés : le nerf de la fédération."""

    def test_deux_instances_peuvent_publier_le_meme_id_de_plan(self, db):
        """
        Le plan n° 42 de RNF n'a aucun rapport avec le plan n° 42 du CEN.

        Sans l'instance dans la clé, ingérer le second écraserait le premier —
        silencieusement, puisque rien ne signalerait la collision.
        """
        for instance in ('rnf', 'cen'):
            PlanIndexe.objects.create(
                instance_id=instance, id_pg=42, slug='plan', nom=f'Plan {instance}',
                statut='valide',
            )
        assert PlanIndexe.objects.filter(id_pg=42).count() == 2

    def test_la_meme_instance_ne_peut_pas_publier_deux_fois_le_meme_plan(self, plan):
        with pytest.raises(IntegrityError):
            PlanIndexe.objects.create(
                instance_id='rnf', id_pg=42, slug='autre', nom='Doublon',
                statut='valide',
            )

    def test_deux_instances_peuvent_publier_le_meme_id_objet(self, db):
        """Idem au niveau du contenu : chaque base a son enjeu n° 7."""
        for instance in ('rnf', 'cen'):
            parent = PlanIndexe.objects.create(
                instance_id=instance, id_pg=1, slug='p', nom='P', statut='valide',
            )
            ContenuIndexe.objects.create(
                instance_id=instance, type_contenu=ContenuIndexe.TYPE_ENJEU,
                id_objet=7, plan=parent, titre='Enjeu', statut_pg='valide',
            )
        assert ContenuIndexe.objects.filter(id_objet=7).count() == 2

    def test_le_contenu_disparait_avec_son_plan(self, plan):
        """
        Dépublier un plan doit emporter son contenu.

        C'est ce qui rend la purge par état tenable : le hub retire le plan, la
        base retire les documents, sans qu'aucun message de retrait par objet
        n'ait eu à circuler.
        """
        ContenuIndexe.objects.create(
            instance_id='rnf', type_contenu=ContenuIndexe.TYPE_ACTION, id_objet=1,
            plan=plan, titre='Action', statut_pg='valide',
        )
        plan.delete()
        assert ContenuIndexe.objects.count() == 0


class TestVecteursDeRecherche:
    """Les deux modes de recherche, et ce qui les sépare."""

    def _document(self, plan, **kwargs):
        defauts = dict(
            instance_id='rnf', type_contenu=ContenuIndexe.TYPE_ENJEU, id_objet=1,
            plan=plan, titre='Forêt alluviale', statut_pg='valide',
        )
        return ContenuIndexe.objects.create(**{**defauts, **kwargs})

    def test_le_vecteur_ignore_les_accents(self, plan):
        """« foret » doit trouver « Forêt » — c'est tout l'objet de la config."""
        self._document(plan)
        trouve = ContenuIndexe.objects.filter(search_titre='foret')
        assert trouve.count() == 1

    def test_les_rattachements_sont_dans_le_mode_titres(self, plan):
        """
        Chercher une espèce ou un habitat doit remonter l'objet qui la porte,
        sans avoir à élargir la recherche : c'est un rattachement explicite, pas
        du texte de contexte.
        """
        self._document(plan, rattachements='Alnus glutinosa')
        assert ContenuIndexe.objects.filter(search_titre='glutinosa').count() == 1

    def test_le_contexte_n_est_que_dans_le_mode_elargi(self, plan):
        """La frontière entre les deux modes : ce que l'objet porte / ce que ses parents disent."""
        self._document(plan, contexte='Objectif de restauration hydraulique')
        assert ContenuIndexe.objects.filter(search_titre='hydraulique').count() == 0
        assert ContenuIndexe.objects.filter(search_full='hydraulique').count() == 1


class TestReferentiels:
    """Les référentiels nationaux sont ce qui permet aux codes de voyager."""

    def test_l_arbre_des_zones_est_servi(self, client, db):
        from apps.geo.models import AreaType, LArea
        from django.contrib.gis.geos import MultiPolygon, Polygon

        carre = MultiPolygon(Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))), srid=4326)
        type_reg = AreaType.objects.create(type_code=AreaType.REGION, type_name='Région')
        type_dep = AreaType.objects.create(
            type_code=AreaType.DEPARTEMENT, type_name='Département'
        )
        region = LArea.objects.create(
            id_type=type_reg, area_code='93', area_name="Provence", geom=carre,
        )
        LArea.objects.create(
            id_type=type_dep, area_code='13', area_name='Bouches-du-Rhône',
            geom=carre, parent=region,
        )

        reponse = client.get('/api/geo/zones/')
        assert reponse.status_code == 200
        arbre = reponse.json()
        assert [r['nom'] for r in arbre] == ['Provence']
        assert arbre[0]['departements'][0]['code'] == '13'

    def test_un_code_de_zone_est_unique_par_type(self, db):
        """
        C'est cette contrainte qui autorise les documents à voyager en codes.

        Sans elle, re-résoudre « DEP:13 » à l'arrivée pourrait rendre plusieurs
        zones, et le rattachement deviendrait ambigu.
        """
        from apps.geo.models import AreaType, LArea
        from django.contrib.gis.geos import MultiPolygon, Polygon

        carre = MultiPolygon(Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))), srid=4326)
        type_dep = AreaType.objects.create(
            type_code=AreaType.DEPARTEMENT, type_name='Département'
        )
        LArea.objects.create(
            id_type=type_dep, area_code='13', area_name='Bouches-du-Rhône', geom=carre
        )
        with pytest.raises(IntegrityError):
            LArea.objects.create(
                id_type=type_dep, area_code='13', area_name='Doublon', geom=carre
            )
