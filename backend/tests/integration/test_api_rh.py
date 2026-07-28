"""
Tests d'intégration pour l'API RH des plans de gestion (#560) :
référentiel de fonctions, postes du PG et lignes de temps de travail.
"""
import pytest
from rest_framework.test import APIClient

from apps.plans.models_operations import (
    Fonction,
    OperationAnneeRH,
    Poste,
    RealisationOperationAnnee,
    RealisationOperationAnneeRH,
)
from tests.factories.users import ReferentFactory, SuperAdminFactory
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import OrganismeFactory
from tests.factories.enjeux import (
    OperationAnneeFactory,
    OperationFactory,
    SuiviInventaireFactory,
)


@pytest.fixture
def admin_client():
    client = APIClient()
    client.force_authenticate(SuperAdminFactory())
    return client


@pytest.fixture
def referent_client():
    """Gestionnaire d'un plan : peut alimenter SON plan, pas le socle (#631)."""
    user = ReferentFactory()
    PlanGestionFactory().referents.add(user)
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
@pytest.mark.integration
class TestFonctionEndpoint:
    """Référentiel global des fonctions/postes."""

    def test_socle_seede(self, admin_client):
        r = admin_client.get('/api/plans/fonctions/')
        assert r.status_code == 200
        data = r.json()
        libelles = [f['libelle'] for f in data]
        assert 'Conservateur' in libelles
        # Au moins une fonction non financée par défaut (écovolontaire, bénévole…)
        assert any(f['finance_par_defaut'] is False for f in data)
        assert all(f['is_socle'] for f in data)

    def test_prestataire_retire_du_referentiel_actif(self, admin_client):
        """
        #622 — un prestataire n'a pas de coût jour, donc pas de temps de travail
        à programmer : sa fonction n'est plus proposée. Elle est désactivée et
        non supprimée, pour que les postes existants restent valides (son coût
        continue de se saisir en « Coût prestataire » du budget de l'action).
        """
        actives = admin_client.get('/api/plans/fonctions/?actif=true').json()
        assert all(f['type_poste'] != 'prestataire' for f in actives), actives
        assert 'Prestataire' not in [f['libelle'] for f in actives]
        # La fonction socle existe toujours, simplement inactive.
        prestataire = Fonction.objects.filter(libelle='Prestataire').first()
        assert prestataire is not None
        assert prestataire.actif is False

    def test_create_a_la_volee(self, admin_client):
        r = admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': 'Poste inédit', 'finance_par_defaut': False},
            format='json',
        )
        assert r.status_code == 201
        assert r.json()['finance_par_defaut'] is False
        assert r.json()['is_socle'] is False

    def test_create_dedup_insensible_casse(self, admin_client):
        admin_client.post('/api/plans/fonctions/', {'libelle': 'Ranger'}, format='json')
        admin_client.post('/api/plans/fonctions/', {'libelle': 'ranger'}, format='json')
        assert Fonction.objects.filter(libelle__iexact='ranger').count() == 1

    def test_suppression_socle_interdite(self, admin_client):
        fonction = Fonction.objects.filter(is_socle=True).first()
        r = admin_client.delete(f'/api/plans/fonctions/{fonction.id_fonction}/')
        assert r.status_code == 400
        assert Fonction.objects.filter(pk=fonction.pk).exists()


@pytest.mark.django_db
@pytest.mark.integration
class TestPosteNomLocal:
    """#632 — nom local et commentaire d'un poste, sans donnée nominative."""

    def _poste(self, plan, **kwargs):
        poste = Poste.objects.create(id_pg=plan, nombre=1, **kwargs)
        poste.fonctions.create(id_fonction=Fonction.objects.get(libelle='Garde'))
        return poste

    def test_libelle_derive_des_fonctions_sans_nom_local(self):
        poste = self._poste(PlanGestionFactory())
        assert poste.libelle == 'Garde'

    def test_nom_local_prime_sur_le_libelle_des_fonctions(self):
        """Le nom local s'affiche partout : tuiles, fiches actions, suivis."""
        poste = self._poste(PlanGestionFactory(), nom_local='Garde du secteur nord')
        assert poste.libelle == 'Garde du secteur nord'
        assert poste.libelle_fonctions == 'Garde'

    def test_nom_local_vide_ne_masque_pas_les_fonctions(self):
        poste = self._poste(PlanGestionFactory(), nom_local='   ')
        assert poste.libelle == 'Garde'

    def test_api_enregistre_nom_local_et_commentaire(self, admin_client):
        plan = PlanGestionFactory()
        garde = Fonction.objects.get(libelle='Garde')
        r = admin_client.post('/api/plans/postes/', {
            'id_pg': plan.id_pg,
            'nombre': 1,
            'nom_local': 'Garde du secteur nord',
            'commentaire': 'Poste partagé avec la commune.',
            'fonctions': [{'id_fonction': garde.id_fonction}],
        }, format='json')
        assert r.status_code == 201
        body = r.json()
        assert body['nom_local'] == 'Garde du secteur nord'
        assert body['commentaire'] == 'Poste partagé avec la commune.'
        assert body['libelle'] == 'Garde du secteur nord'
        assert body['libelle_fonctions'] == 'Garde'

    def test_lignes_rh_affichent_le_nom_local(self, admin_client):
        """Le libellé servi aux fiches actions / suivis suit le nom local."""
        poste = self._poste(PlanGestionFactory(), nom_local='Garde du secteur nord')
        r = admin_client.get(f'/api/plans/postes/by-plan/{poste.id_pg_id}/')
        assert [p['libelle'] for p in r.json()] == ['Garde du secteur nord']


@pytest.mark.django_db
@pytest.mark.integration
class TestSocleFonctions:
    """#632 — fonctions oubliées du socle."""

    def test_garde_animateur_dans_le_socle(self, admin_client):
        libelles = [f['libelle'] for f in admin_client.get('/api/plans/fonctions/').json()]
        assert 'Garde animateur' in libelles

    def test_pas_de_fonction_test(self):
        assert not Fonction.objects.filter(libelle__iexact='test', actif=True).exists()


@pytest.mark.django_db
@pytest.mark.integration
class TestFonctionPorteePlan:
    """#631 — une fonction ajoutée depuis un plan reste à l'échelle de ce plan."""

    def test_creation_rattachee_au_plan(self, admin_client):
        plan = PlanGestionFactory()
        r = admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': 'Garde du marais', 'id_pg': plan.id_pg},
            format='json',
        )
        assert r.status_code == 201
        assert r.json()['id_pg'] == plan.id_pg

    def test_liste_du_plan_socle_plus_fonctions_locales(self, admin_client):
        plan = PlanGestionFactory()
        autre = PlanGestionFactory()
        admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': 'Garde du marais', 'id_pg': plan.id_pg}, format='json',
        )
        admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': "Garde de l'étang", 'id_pg': autre.id_pg}, format='json',
        )

        libelles = [
            f['libelle']
            for f in admin_client.get(f'/api/plans/fonctions/?id_pg={plan.id_pg}').json()
        ]
        assert 'Garde du marais' in libelles          # la sienne
        assert 'Conservateur' in libelles             # le socle partagé
        assert "Garde de l'étang" not in libelles     # celle du voisin

    def test_liste_sans_plan_ne_renvoie_que_le_socle(self, admin_client):
        plan = PlanGestionFactory()
        admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': 'Garde du marais', 'id_pg': plan.id_pg}, format='json',
        )
        data = admin_client.get('/api/plans/fonctions/').json()
        assert all(f['id_pg'] is None for f in data)
        assert 'Garde du marais' not in [f['libelle'] for f in data]

    def test_meme_libelle_dans_deux_plans(self, admin_client):
        """Deux plans peuvent nommer leur fonction pareil sans se marcher dessus."""
        plan = PlanGestionFactory()
        autre = PlanGestionFactory()
        r1 = admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': 'Garde du marais', 'id_pg': plan.id_pg}, format='json',
        )
        r2 = admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': 'Garde du marais', 'id_pg': autre.id_pg}, format='json',
        )
        assert r1.status_code == r2.status_code == 201
        assert r1.json()['id_fonction'] != r2.json()['id_fonction']

    def test_dedup_reutilise_le_socle(self, admin_client):
        """Recréer une fonction du socle ne la duplique pas dans le plan."""
        plan = PlanGestionFactory()
        r = admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': 'conservateur', 'id_pg': plan.id_pg}, format='json',
        )
        assert r.json()['id_pg'] is None
        assert Fonction.objects.filter(libelle__iexact='conservateur').count() == 1

    def test_dedup_dans_le_plan(self, admin_client):
        plan = PlanGestionFactory()
        admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': 'Garde du marais', 'id_pg': plan.id_pg}, format='json',
        )
        admin_client.post(
            '/api/plans/fonctions/',
            {'libelle': 'garde du marais', 'id_pg': plan.id_pg}, format='json',
        )
        assert Fonction.objects.filter(
            libelle__iexact='garde du marais', id_pg=plan
        ).count() == 1

    def test_referent_ne_peut_pas_alimenter_le_socle(self, referent_client):
        """Sans plan, la fonction irait dans le socle partagé : refusé (#631)."""
        r = referent_client.post(
            '/api/plans/fonctions/', {'libelle': 'Poste maison'}, format='json',
        )
        assert r.status_code == 403
        assert not Fonction.objects.filter(libelle='Poste maison').exists()


@pytest.mark.django_db
@pytest.mark.integration
class TestPosteEndpoint:
    """Postes d'un plan de gestion. Aucune donnée nominative (RGPD)."""

    def test_create_avec_fonctions(self, admin_client):
        plan = PlanGestionFactory()
        organisme = OrganismeFactory()
        fonction = Fonction.objects.get(libelle='Conservateur')
        payload = {
            'id_pg': plan.id_pg,
            'id_organisme': organisme.id_organisme,
            'nombre': 1,
            'etp': '1.00',
            'fonctions': [{'id_fonction': fonction.id_fonction}],
        }
        r = admin_client.post('/api/plans/postes/', payload, format='json')
        assert r.status_code == 201, r.content
        body = r.json()
        assert body['libelle'] == 'Conservateur'
        assert body['organisme_nom'] == organisme.nom_organisme
        assert body['nombre'] == 1
        assert len(body['fonctions']) == 1

    def test_plusieurs_exemplaires_pour_un_etp_total(self, admin_client):
        """3 stagiaires pour 1,5 ETP au total (et non 1,5 ETP chacun)."""
        plan = PlanGestionFactory()
        fonction = Fonction.objects.get(libelle='Stagiaire')
        r = admin_client.post('/api/plans/postes/', {
            'id_pg': plan.id_pg, 'nombre': 3, 'etp': '1.50',
            'fonctions': [{'id_fonction': fonction.id_fonction}],
        }, format='json')
        assert r.status_code == 201, r.content
        assert r.json()['nombre'] == 3
        assert r.json()['etp'] == '1.50'

    def test_poste_combine_sans_quotite(self, admin_client):
        """Un « garde animateur » cumule ses deux fonctions sur tout son temps."""
        plan = PlanGestionFactory()
        garde = Fonction.objects.get(libelle='Garde')
        animateur = Fonction.objects.get(libelle='Animateur nature')
        r = admin_client.post('/api/plans/postes/', {
            'id_pg': plan.id_pg, 'nombre': 1, 'etp': '1.00',
            'fonctions': [
                {'id_fonction': garde.id_fonction},
                {'id_fonction': animateur.id_fonction},
            ],
        }, format='json')
        assert r.status_code == 201, r.content
        assert r.json()['libelle'] == 'Animateur nature · Garde'
        assert all(f['pourcentage'] is None for f in r.json()['fonctions'])

    def test_poste_avec_quotites(self, admin_client):
        """50 % garde / 50 % animateur : le libellé porte la répartition."""
        plan = PlanGestionFactory()
        garde = Fonction.objects.get(libelle='Garde')
        animateur = Fonction.objects.get(libelle='Animateur nature')
        r = admin_client.post('/api/plans/postes/', {
            'id_pg': plan.id_pg, 'nombre': 1, 'etp': '1.00',
            'fonctions': [
                {'id_fonction': garde.id_fonction, 'pourcentage': '50.00'},
                {'id_fonction': animateur.id_fonction, 'pourcentage': '50.00'},
            ],
        }, format='json')
        assert r.status_code == 201, r.content
        assert r.json()['libelle'] == 'Animateur nature 50 % · Garde 50 %'

    def test_quotites_doivent_faire_100(self, admin_client):
        plan = PlanGestionFactory()
        garde = Fonction.objects.get(libelle='Garde')
        animateur = Fonction.objects.get(libelle='Animateur nature')
        r = admin_client.post('/api/plans/postes/', {
            'id_pg': plan.id_pg, 'nombre': 1,
            'fonctions': [
                {'id_fonction': garde.id_fonction, 'pourcentage': '50.00'},
                {'id_fonction': animateur.id_fonction, 'pourcentage': '30.00'},
            ],
        }, format='json')
        assert r.status_code == 400
        assert 'fonctions' in r.json()

    def test_quotites_toutes_ou_aucune(self, admin_client):
        """Un mélange quotité / pas de quotité est ambigu : on le refuse."""
        plan = PlanGestionFactory()
        garde = Fonction.objects.get(libelle='Garde')
        animateur = Fonction.objects.get(libelle='Animateur nature')
        r = admin_client.post('/api/plans/postes/', {
            'id_pg': plan.id_pg, 'nombre': 1,
            'fonctions': [
                {'id_fonction': garde.id_fonction, 'pourcentage': '100.00'},
                {'id_fonction': animateur.id_fonction},
            ],
        }, format='json')
        assert r.status_code == 400

    def test_poste_sans_fonction_refuse(self, admin_client):
        plan = PlanGestionFactory()
        r = admin_client.post('/api/plans/postes/', {
            'id_pg': plan.id_pg, 'nombre': 1, 'fonctions': [],
        }, format='json')
        assert r.status_code == 400

    def test_finance_par_defaut_derive_des_fonctions(self, admin_client):
        """Un poste n'est non financé que si TOUTES ses fonctions le sont."""
        plan = PlanGestionFactory()
        benevole = Fonction.objects.get(libelle='Bénévole')
        r = admin_client.post('/api/plans/postes/', {
            'id_pg': plan.id_pg, 'nombre': 10, 'etp': '0.50',
            'fonctions': [{'id_fonction': benevole.id_fonction}],
        }, format='json')
        assert r.status_code == 201, r.content
        assert r.json()['finance_par_defaut'] is False

    def test_by_plan(self, admin_client):
        plan = PlanGestionFactory()
        autre = PlanGestionFactory()
        conservateur = Fonction.objects.get(libelle='Conservateur')
        for pg in (plan, autre):
            poste = Poste.objects.create(id_pg=pg, nombre=1)
            poste.fonctions.create(id_fonction=conservateur)
        r = admin_client.get(f'/api/plans/postes/by-plan/{plan.id_pg}/')
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]['id_pg'] == plan.id_pg

    def test_update_remplace_fonctions(self, admin_client):
        plan = PlanGestionFactory()
        poste = Poste.objects.create(id_pg=plan, nombre=1)
        poste.fonctions.create(id_fonction=Fonction.objects.get(libelle='Conservateur'))
        garde = Fonction.objects.get(libelle='Garde')
        r = admin_client.patch(
            f'/api/plans/postes/{poste.id_poste}/',
            {'fonctions': [{'id_fonction': garde.id_fonction}]},
            format='json',
        )
        assert r.status_code == 200
        assert poste.fonctions.count() == 1
        assert poste.fonctions.first().id_fonction.libelle == 'Garde'


@pytest.mark.django_db
@pytest.mark.integration
class TestRealisationRhLignes:
    """
    Saisie du temps de travail *réalisé* (page suivi) : lignes RH portées par
    la réalisation annuelle, en sémantique « replace-all ».
    """

    @pytest.fixture
    def operation_annee(self):
        """
        OperationAnnee rattachée à un plan : `Operation.get_plan_de_gestion()`
        remonte via le suivi (id_suivi → id_pg), le chemin le plus court.
        """
        plan = PlanGestionFactory()
        suivi = SuiviInventaireFactory(id_pg=plan)
        return OperationAnneeFactory(id_operation=OperationFactory(id_suivi=suivi))

    def _upsert(self, client, oa, rh_lignes):
        return client.post(
            '/api/plans/realisations/upsert/',
            {'id_operation_annee': oa.id_operation_annee, 'rh_lignes': rh_lignes},
            format='json',
        )

    def test_upsert_cree_les_lignes(self, admin_client, operation_annee):
        oa = operation_annee
        poste = Poste.objects.create(
            id_pg=oa.id_operation.get_plan_de_gestion(), nombre=1,
        )
        organisme = OrganismeFactory()
        r = self._upsert(admin_client, oa, [
            {'id_poste': poste.id_poste, 'jours': '6.50', 'finance': True},
            {'id_organisme': organisme.id_organisme, 'jours': '2.00', 'finance': False},
        ])
        assert r.status_code == 200, r.content
        lignes = r.json()['rh_lignes']
        assert len(lignes) == 2
        realisation = RealisationOperationAnnee.objects.get(id_operation_annee=oa)
        assert realisation.rh_lignes.count() == 2
        non_finance = realisation.rh_lignes.get(finance=False)
        assert non_finance.id_organisme_id == organisme.id_organisme

    def test_lignes_realisees_portent_le_cout_jour_du_poste(self, admin_client, operation_annee):
        """
        #616 — les vues de synthèse valorisent le temps RÉALISÉ (jours × coût
        jour du poste). Sans ces champs dénormalisés — que la ligne
        prévisionnelle expose déjà — le budget réalisé restait à 0 €.
        """
        oa = operation_annee
        organisme = OrganismeFactory()
        poste = Poste.objects.create(
            id_pg=oa.id_operation.get_plan_de_gestion(),
            id_organisme=organisme, nombre=1, cout_jour=300,
        )
        r = self._upsert(admin_client, oa, [
            {'id_poste': poste.id_poste, 'jours': '8.00', 'finance': True},
        ])
        assert r.status_code == 200, r.content
        ligne = r.json()['rh_lignes'][0]
        assert float(ligne['poste_cout_jour']) == 300.0
        assert ligne['poste_id_organisme'] == organisme.id_organisme

    def test_upsert_remplace_les_lignes(self, admin_client, operation_annee):
        oa = operation_annee
        realisation = RealisationOperationAnnee.objects.create(id_operation_annee=oa)
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=realisation, jours=3, finance=True,
        )
        r = self._upsert(admin_client, oa, [{'jours': '9.00', 'finance': True}])
        assert r.status_code == 200, r.content
        assert realisation.rh_lignes.count() == 1
        assert float(realisation.rh_lignes.first().jours) == 9.0

    def test_upsert_liste_vide_efface_les_lignes(self, admin_client, operation_annee):
        oa = operation_annee
        realisation = RealisationOperationAnnee.objects.create(id_operation_annee=oa)
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=realisation, jours=3, finance=True,
        )
        r = self._upsert(admin_client, oa, [])
        assert r.status_code == 200, r.content
        assert realisation.rh_lignes.count() == 0

    def test_ligne_sans_cible_acceptee(self, admin_client, operation_annee):
        """
        « Temps non affecté » : c'est l'état des saisies converties depuis
        l'ancien champ `etp` par la migration 0100. La cible doit rester
        facultative, sinon ces lignes seraient perdues au premier ré-enregistrement.
        """
        oa = operation_annee
        r = self._upsert(admin_client, oa, [{'jours': '4.00', 'finance': True}])
        assert r.status_code == 200, r.content
        ligne = RealisationOperationAnnee.objects.get(
            id_operation_annee=oa,
        ).rh_lignes.first()
        assert ligne.id_poste_id is None
        assert ligne.id_organisme_id is None
        assert float(ligne.jours) == 4.0

    def test_duplication_copie_postes_et_lignes_rh(self, operation_annee):
        """
        #377 + #560 — une nouvelle version doit emporter les postes du PG et le
        temps de travail prévisionnel, remappés vers ses propres copies : sans
        cela le prévisionnel RH serait silencieusement perdu, et les lignes
        copiées pointeraient sur les postes de la version source.
        """
        from apps.plans.services import PlanDuplicationService

        oa = operation_annee
        source = oa.id_operation.get_plan_de_gestion()
        organisme = OrganismeFactory()
        poste = Poste.objects.create(
            id_pg=source, id_organisme=organisme, nombre=3, etp='1.50',
        )
        conservateur = Fonction.objects.get(libelle='Conservateur')
        poste.fonctions.create(id_fonction=conservateur, pourcentage=None)
        OperationAnneeRH.objects.create(
            id_operation_annee=oa, id_poste=poste, jours=9, finance=True,
        )

        cible = PlanGestionFactory()
        PlanDuplicationService.copy_content(source, cible, SuperAdminFactory())

        # Poste copié (nouvelle instance) + ses fonctions et son organisme.
        copies = Poste.objects.filter(id_pg=cible)
        assert copies.count() == 1
        copie = copies.first()
        assert copie.id_poste != poste.id_poste
        assert copie.nombre == 3
        assert float(copie.etp) == 1.5
        assert copie.id_organisme_id == organisme.id_organisme
        assert copie.fonctions.first().id_fonction_id == conservateur.id_fonction

        # Ligne RH copiée et repointée vers le poste du NOUVEAU plan.
        lignes = OperationAnneeRH.objects.filter(
            id_operation_annee__id_operation__id_suivi__id_pg=cible,
        )
        assert lignes.count() == 1
        assert float(lignes.first().jours) == 9.0
        assert lignes.first().id_poste_id == copie.id_poste

        # La version source reste intacte.
        assert Poste.objects.filter(id_pg=source).count() == 1
        assert OperationAnneeRH.objects.filter(id_operation_annee=oa).count() == 1

    def test_duplication_recopie_les_fonctions_du_plan(self, operation_annee):
        """
        #631 — une fonction propre au plan source n'est pas visible du plan
        cible : la duplication doit lui en donner sa propre copie, sinon la
        nouvelle version pointerait sur une fonction qu'elle ne peut pas voir.
        Les fonctions du socle, elles, restent partagées.
        """
        from apps.plans.services import PlanDuplicationService

        source = operation_annee.id_operation.get_plan_de_gestion()
        locale = Fonction.objects.create(
            libelle='Garde du marais', id_pg=source, type_poste='salarie',
        )
        socle = Fonction.objects.get(libelle='Conservateur')
        poste = Poste.objects.create(id_pg=source, nombre=1)
        poste.fonctions.create(id_fonction=locale)
        poste.fonctions.create(id_fonction=socle)

        cible = PlanGestionFactory()
        PlanDuplicationService.copy_content(source, cible, SuperAdminFactory())

        copie = Poste.objects.get(id_pg=cible)
        fonctions = {
            pf.id_fonction.libelle: pf.id_fonction for pf in copie.fonctions.all()
        }
        # Fonction locale : recopiée pour le plan cible.
        assert fonctions['Garde du marais'].id_pg_id == cible.id_pg
        assert fonctions['Garde du marais'].id_fonction != locale.id_fonction
        # Fonction du socle : partagée, donc réutilisée telle quelle.
        assert fonctions['Conservateur'].id_fonction == socle.id_fonction

    def test_bilan_ventile_finance_et_non_finance(self, admin_client, operation_annee):
        """Le bilan doit valoriser séparément le temps non financé (#560)."""
        oa = operation_annee
        plan = oa.id_operation.get_plan_de_gestion()
        OperationAnneeRH.objects.create(id_operation_annee=oa, jours=10, finance=True)
        OperationAnneeRH.objects.create(id_operation_annee=oa, jours=4, finance=False)
        realisation = RealisationOperationAnnee.objects.create(id_operation_annee=oa)
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=realisation, jours=8, finance=True,
        )
        RealisationOperationAnneeRH.objects.create(
            id_realisation_operation_annee=realisation, jours=3, finance=False,
        )
        r = admin_client.get(f'/api/plans/realisations/bilan/{plan.id_pg}/')
        assert r.status_code == 200, r.content
        rh = r.json()['rh']
        assert rh['previsionnel_finance'] == 10
        assert rh['previsionnel_non_finance'] == 4
        assert rh['realise_finance'] == 8
        assert rh['realise_non_finance'] == 3
        assert rh['previsionnel'] == 14
        assert rh['realise'] == 11
