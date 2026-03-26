"""
Tests pour la commande import_nomenclatures.

Vérifie que la commande importe correctement les nomenclatures
depuis les fichiers SQL et gère l'idempotence.
"""
import pytest
from io import StringIO

from django.core.management import call_command
from django.db import connection

from apps.core.models import TypeNomenclature, Nomenclature


@pytest.mark.django_db
class TestImportNomenclaturesCommand:
    """Tests pour la commande import_nomenclatures."""

    def _call_command(self, *args, **kwargs):
        """Helper pour appeler la commande et capturer la sortie."""
        out = StringIO()
        call_command('import_nomenclatures', *args, stdout=out, **kwargs)
        return out.getvalue()

    def _clear_nomenclatures(self):
        """Vide les tables de nomenclatures pour tester l'import."""
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE t_nomenclatures CASCADE;')
            cursor.execute('TRUNCATE TABLE bib_nomenclatures_types CASCADE;')

    def test_import_creates_types(self):
        """L'import crée les types de nomenclature."""
        self._clear_nomenclatures()
        self._call_command('--force')

        assert TypeNomenclature.objects.count() > 0
        # Vérifier quelques types essentiels
        assert TypeNomenclature.objects.filter(mnemonique='Espace naturel').exists()
        assert TypeNomenclature.objects.filter(mnemonique='Evaluation PG').exists()
        assert TypeNomenclature.objects.filter(mnemonique='Rédacteur type').exists()
        assert TypeNomenclature.objects.filter(mnemonique='Type document plan').exists()

    def test_import_creates_nomenclatures(self):
        """L'import crée les nomenclatures."""
        self._clear_nomenclatures()
        self._call_command('--force')

        assert Nomenclature.objects.count() > 0

    def test_import_site_types(self):
        """L'import crée les types de site (RNN, RNR, PNR, etc.)."""
        self._clear_nomenclatures()
        self._call_command('--force')

        type_site = TypeNomenclature.objects.get(mnemonique='Espace naturel')
        site_noms = Nomenclature.objects.filter(id_type=type_site)

        mnemoniques = set(site_noms.values_list('mnemonique', flat=True))
        assert 'RNN' in mnemoniques
        assert 'RNR' in mnemoniques
        assert 'RNC' in mnemoniques
        assert 'PNR' in mnemoniques
        assert 'ENS' in mnemoniques
        assert 'APB' in mnemoniques
        assert 'AUTRE' in mnemoniques

    def test_import_doc_types(self):
        """L'import crée les types de document plan (PLAN_INITIAL, etc.)."""
        self._clear_nomenclatures()
        self._call_command('--force')

        type_doc = TypeNomenclature.objects.get(mnemonique='Type document plan')
        doc_noms = Nomenclature.objects.filter(id_type=type_doc)

        mnemoniques = set(doc_noms.values_list('mnemonique', flat=True))
        assert 'PLAN_INITIAL' in mnemoniques
        assert 'EVAL_MI_PARCOURS' in mnemoniques
        assert 'PLAN_REVISE' in mnemoniques

    def test_import_suivi_types(self):
        """L'import crée les types de suivi/inventaire."""
        self._clear_nomenclatures()
        self._call_command('--force')

        assert TypeNomenclature.objects.filter(mnemonique='TYPE_SUIVI').exists()
        assert TypeNomenclature.objects.filter(mnemonique='STATUT_SUIVI').exists()
        assert TypeNomenclature.objects.filter(mnemonique='OBJECTIF_SUIVI').exists()
        assert TypeNomenclature.objects.filter(mnemonique='CIBLE_SUIVI').exists()

        type_suivi = TypeNomenclature.objects.get(mnemonique='TYPE_SUIVI')
        suivi_noms = Nomenclature.objects.filter(id_type=type_suivi)
        mnemoniques = set(suivi_noms.values_list('mnemonique', flat=True))
        assert 'SUIVI' in mnemoniques
        assert 'INVENTAIRE' in mnemoniques
        assert 'SUIVI_INVENTAIRE' in mnemoniques

    def test_import_objectif_suivi_values(self):
        """L'import crée les 11 valeurs OBJECTIF_SUIVI avec hiérarchie."""
        self._clear_nomenclatures()
        self._call_command('--force')

        type_obj = TypeNomenclature.objects.get(mnemonique='OBJECTIF_SUIVI')
        noms = Nomenclature.objects.filter(id_type=type_obj)
        mnemoniques = set(noms.values_list('mnemonique', flat=True))
        assert len(mnemoniques) == 11
        # Catégorie A - Inventorier
        assert 'OBJ_INVENTAIRE_INITIAL' in mnemoniques
        assert 'OBJ_ACQUISITION_CONNAISSANCES' in mnemoniques
        # Catégorie B - Suivre/surveiller état
        assert 'OBJ_ETAT_CONSERVATION' in mnemoniques
        assert 'OBJ_DYNAMIQUE_MILIEUX' in mnemoniques
        assert 'OBJ_PHYSICO_CHIMIQUES' in mnemoniques
        assert 'OBJ_FONCTIONNALITES' in mnemoniques
        # Catégorie C - Suivre/surveiller pressions
        assert 'OBJ_RISQUES_ECOLOGIQUES' in mnemoniques
        assert 'OBJ_CHANGEMENT_CLIMATIQUE' in mnemoniques
        assert 'OBJ_ACTIVITES_HUMAINES' in mnemoniques
        # Catégorie D - Évaluer gestion
        assert 'OBJ_EFFICACITE_GESTION' in mnemoniques
        # Autre
        assert 'OBJ_AUTRE' in mnemoniques

        # Vérifier que definition (groupe) et hierarchy sont renseignés
        obj_inv = noms.get(mnemonique='OBJ_INVENTAIRE_INITIAL')
        assert obj_inv.definition != ''
        assert obj_inv.hierarchy == 'A.1'

    def test_import_cible_suivi_values(self):
        """L'import crée les 7 valeurs CIBLE_SUIVI."""
        self._clear_nomenclatures()
        self._call_command('--force')

        type_cible = TypeNomenclature.objects.get(mnemonique='CIBLE_SUIVI')
        noms = Nomenclature.objects.filter(id_type=type_cible)
        mnemoniques = set(noms.values_list('mnemonique', flat=True))
        assert len(mnemoniques) == 7
        assert 'MULTI_COMPOSANTES' in mnemoniques
        assert 'ESPECES' in mnemoniques
        assert 'HABITATS_VEGETATIONS' in mnemoniques
        assert 'ABIOTIQUE' in mnemoniques
        assert 'STRUCTURES_PAYSAGE' in mnemoniques
        assert 'PROCESSUS_FONCTIONS' in mnemoniques
        assert 'ANTHROPIQUE' in mnemoniques

    def test_idempotent_skip(self):
        """L'import est ignoré si les données existent déjà."""
        self._clear_nomenclatures()
        self._call_command('--force')
        count_before = Nomenclature.objects.count()

        # Deuxième appel sans --force : doit être ignoré
        output = self._call_command()
        assert 'déjà importées' in output

        # Le nombre ne doit pas changer
        assert Nomenclature.objects.count() == count_before

    def test_force_reimport(self):
        """--force réimporte même si les données existent."""
        self._clear_nomenclatures()
        self._call_command('--force')
        count_first = Nomenclature.objects.count()

        # Force reimport
        output = self._call_command('--force')
        assert 'terminé avec succès' in output

        # Le nombre doit être identique (réimport complet)
        assert Nomenclature.objects.count() == count_first

    def test_sequences_updated(self):
        """Les séquences PostgreSQL sont mises à jour après l'import."""
        self._clear_nomenclatures()
        self._call_command('--force')

        max_type_id = TypeNomenclature.objects.order_by('-id_type').values_list('id_type', flat=True).first()
        max_nom_id = Nomenclature.objects.order_by('-id_nomenclature').values_list('id_nomenclature', flat=True).first()

        # Vérifier qu'on peut créer de nouveaux objets sans conflit de séquence
        new_type = TypeNomenclature.objects.create(
            mnemonique='TEST_SEQ',
            label='Test séquence'
        )
        assert new_type.id_type > max_type_id

        new_nom = Nomenclature.objects.create(
            id_type=new_type,
            mnemonique='TEST_SEQ_NOM',
            label='Test séquence nomenclature'
        )
        assert new_nom.id_nomenclature > max_nom_id

        # Nettoyage
        new_nom.delete()
        new_type.delete()

    def test_enjeux_nomenclatures(self):
        """L'import crée les nomenclatures nécessaires aux enjeux."""
        self._clear_nomenclatures()
        self._call_command('--force')

        # Types d'enjeux
        assert TypeNomenclature.objects.filter(mnemonique='CATEGORIE_ENJEU').exists()
        assert TypeNomenclature.objects.filter(mnemonique='IMPORTANCE_ENJEU').exists()
        assert TypeNomenclature.objects.filter(mnemonique='TYPE_RESPONSABILITE').exists()
        assert TypeNomenclature.objects.filter(mnemonique='NIVEAU_RESPONSABILITE').exists()
        assert TypeNomenclature.objects.filter(mnemonique='CATEGORIE_FCR').exists()

        # Valeurs d'enjeux
        cat_enjeu = TypeNomenclature.objects.get(mnemonique='CATEGORIE_ENJEU')
        cats = set(Nomenclature.objects.filter(id_type=cat_enjeu).values_list('mnemonique', flat=True))
        assert 'ENJEU' in cats
        assert 'FCR' in cats

    def test_operations_nomenclatures(self):
        """L'import crée les nomenclatures nécessaires aux opérations."""
        self._clear_nomenclatures()
        self._call_command('--force')

        assert TypeNomenclature.objects.filter(mnemonique='PRIORITE_OPERATION').exists()
        assert TypeNomenclature.objects.filter(mnemonique='TYPE_ACTION').exists()
        assert TypeNomenclature.objects.filter(mnemonique='OPERATEUR_TYPE').exists()
        assert TypeNomenclature.objects.filter(mnemonique='CATEGORIE_FINANCE').exists()

        # Types d'action (codification Eden 62 - 318 entrées hiérarchiques)
        type_action = TypeNomenclature.objects.get(mnemonique='TYPE_ACTION')
        actions = Nomenclature.objects.filter(id_type=type_action)
        assert actions.count() == 318
        # Vérifier quelques codes clés
        assert actions.filter(cd_nomenclature='IP1').exists()
        assert actions.filter(cd_nomenclature='CS8.1').exists()
        assert actions.filter(cd_nomenclature='CI2').exists()
        assert actions.filter(cd_nomenclature='SP1').exists()
        # Vérifier la hiérarchie
        ip1 = actions.get(cd_nomenclature='IP1')
        assert ip1.hierarchy == 'IP1'
        ip1_1 = actions.get(cd_nomenclature='IP1.1')
        assert ip1_1.hierarchy == 'IP1.1'

    def test_import_bancarisation_nomenclatures(self):
        """L'import crée les nomenclatures de bancarisation et outil de saisie."""
        self._clear_nomenclatures()
        self._call_command('--force')

        assert TypeNomenclature.objects.filter(mnemonique='BANCARISATION_STOCKAGE').exists()
        assert TypeNomenclature.objects.filter(mnemonique='OUTIL_SAISIE').exists()

        type_banc = TypeNomenclature.objects.get(mnemonique='BANCARISATION_STOCKAGE')
        banc_noms = Nomenclature.objects.filter(id_type=type_banc)
        mnemoniques = set(banc_noms.values_list('mnemonique', flat=True))
        assert len(mnemoniques) == 5
        assert 'PAS_STOCKAGE' in mnemoniques
        assert 'FORMAT_UNIQUE' in mnemoniques
        assert 'BDD_INTERNE' in mnemoniques
        assert 'CENTRALISEE_REFERENT' in mnemoniques
        assert 'CENTRALISEE_NATIONALE' in mnemoniques

        type_saisie = TypeNomenclature.objects.get(mnemonique='OUTIL_SAISIE')
        saisie_noms = Nomenclature.objects.filter(id_type=type_saisie)
        mnemoniques = set(saisie_noms.values_list('mnemonique', flat=True))
        assert len(mnemoniques) == 3
        assert 'AUCUN' in mnemoniques
        assert 'NON_ADAPTE' in mnemoniques
        assert 'ADAPTE' in mnemoniques

    def test_upsert_updates_labels(self):
        """--force met à jour les labels existants via upsert."""
        self._clear_nomenclatures()
        self._call_command('--force')

        # Modifier un label manuellement
        nom = Nomenclature.objects.get(mnemonique='RNN')
        original_label = nom.label
        nom.label = 'MODIFIED_LABEL'
        nom.save()
        assert Nomenclature.objects.get(mnemonique='RNN').label == 'MODIFIED_LABEL'

        # Re-run avec --force : doit restaurer le label original
        self._call_command('--force')
        assert Nomenclature.objects.get(mnemonique='RNN').label == original_label

    def test_upsert_preserves_data(self):
        """--force ne supprime pas les entrées existantes."""
        self._clear_nomenclatures()
        self._call_command('--force')
        count_after_first = Nomenclature.objects.count()

        # Ajouter une entrée custom
        type_test = TypeNomenclature.objects.first()
        Nomenclature.objects.create(
            id_type=type_test,
            mnemonique='CUSTOM_ENTRY',
            label='Custom test entry'
        )
        assert Nomenclature.objects.count() == count_after_first + 1

        # Re-run --force (sans --prune): l'entrée custom doit rester
        self._call_command('--force')
        assert Nomenclature.objects.filter(mnemonique='CUSTOM_ENTRY').exists()

    def test_prune_removes_obsolete(self):
        """--force --prune supprime les entrées absentes des fichiers SQL."""
        self._clear_nomenclatures()
        self._call_command('--force')

        # Ajouter une entrée custom
        type_test = TypeNomenclature.objects.first()
        Nomenclature.objects.create(
            id_type=type_test,
            mnemonique='OBSOLETE_ENTRY',
            label='Should be pruned'
        )
        assert Nomenclature.objects.filter(mnemonique='OBSOLETE_ENTRY').exists()

        # Run avec --prune : l'entrée custom doit être supprimée
        output = self._call_command('--force', '--prune')
        assert not Nomenclature.objects.filter(mnemonique='OBSOLETE_ENTRY').exists()
        assert 'Supprimé' in output
