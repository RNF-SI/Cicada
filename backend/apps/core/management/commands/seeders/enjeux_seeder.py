"""
Seeder pour les Enjeux, FCR et Responsabilités.
"""
from typing import List

from apps.core.models import Nomenclature
from apps.plans.models import PlanGestion
from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, Pression, Responsabilite,
    EtatActuel, ObjectifLongTerme, NiveauExigence,
    ObjectifOperationnel, ResultatAttendu,
    CorEnjeuTaxon, CorEnjeuHabitat,
    CorResponsabiliteTaxon, CorResponsabiliteHabitat,
    CorResponsabiliteEnjeu
)
from apps.plans.models_indicateurs import (
    Indicateur, CorIndicateurTaxon, CorIndicateurHabitat,
    CorIndicateurGeologie, Metrique, Mesure
)
from apps.plans.models_operations import (
    Protocole, SuiviInventaire, Operation, CorOperationIndicateur,
    CorOperationSite, OperationAnnee, FinanceOperation
)
from apps.users.models import Role, Site

from .base import BaseSeeder


class EnjeuxSeeder(BaseSeeder):
    """
    Crée les enjeux, FCR et responsabilités de test.

    Enjeux (16 au total):
    - 5 enjeux pour Plan Camargue (priorités 1, 2, 3)
    - 4 enjeux pour Plan Aiguilles Rouges (priorités 1, 2, 3)
    - 2 enjeux pour Plan Vercors-Ecrins
    - 5 enjeux pour Plan Lac de Remoray (priorités 1, 2, 3)

    FCR (8 au total):
    - 2 FCR pour Plan Camargue
    - 2 FCR pour Plan Aiguilles Rouges
    - 2 FCR pour Plan Vercors-Ecrins
    - 2 FCR pour Plan Lac de Remoray

    Responsabilités (10 au total):
    - 3 pour Camargue
    - 3 pour Aiguilles Rouges
    - 2 pour Vercors
    - 2 pour Lac de Remoray
    """

    name = 'enjeux'
    dependencies = ['plans']

    def _get_nomenclature(self, type_mnemonique: str, mnemonique: str) -> Nomenclature:
        """Récupère une nomenclature par type et mnémonique."""
        return Nomenclature.objects.filter(
            id_type__mnemonique=type_mnemonique,
            mnemonique=mnemonique
        ).first()

    def seed(self) -> dict:
        """
        Crée les enjeux, FCR et responsabilités de test.

        Returns:
            Dictionnaire avec les listes créées
        """
        self.log_header('Création des enjeux, FCR et responsabilités')

        plans = self.context.require('plans')
        sites = self.context.require('sites')
        users = self.context.require('users')

        admin = users[0]  # Pour id_utilisateur_ajout

        # Récupérer les nomenclatures
        cat_enjeu = self._get_nomenclature('CATEGORIE_ENJEU', 'ENJEU')
        cat_fcr = self._get_nomenclature('CATEGORIE_ENJEU', 'FCR')
        fcr_connaissance = self._get_nomenclature('CATEGORIE_FCR', 'CONNAISSANCE')
        fcr_ancrage = self._get_nomenclature('CATEGORIE_FCR', 'ANCRAGE')
        fcr_fonctionnement = self._get_nomenclature('CATEGORIE_FCR', 'FONCTIONNEMENT')
        fcr_autre = self._get_nomenclature('CATEGORIE_FCR', 'AUTRE')

        # Importance / priorité
        priorite_1 = self._get_nomenclature('IMPORTANCE_ENJEU', 'PRIORITE_1')
        priorite_2 = self._get_nomenclature('IMPORTANCE_ENJEU', 'PRIORITE_2')
        priorite_3 = self._get_nomenclature('IMPORTANCE_ENJEU', 'PRIORITE_3')

        # Types de responsabilité
        resp_floristique = self._get_nomenclature('TYPE_RESPONSABILITE', 'FLORISTIQUE')
        resp_faunistique = self._get_nomenclature('TYPE_RESPONSABILITE', 'FAUNISTIQUE')
        resp_habitat = self._get_nomenclature('TYPE_RESPONSABILITE', 'HABITAT')
        resp_geologique = self._get_nomenclature('TYPE_RESPONSABILITE', 'GEOLOGIQUE')

        # Niveaux de responsabilité
        niveau_local = self._get_nomenclature('NIVEAU_RESPONSABILITE', 'LOCAL')
        niveau_regional = self._get_nomenclature('NIVEAU_RESPONSABILITE', 'REGIONAL')
        niveau_national = self._get_nomenclature('NIVEAU_RESPONSABILITE', 'NATIONAL')
        niveau_international = self._get_nomenclature('NIVEAU_RESPONSABILITE', 'INTERNATIONAL')

        if not cat_enjeu or not cat_fcr:
            self.stderr.write('  Nomenclatures CATEGORIE_ENJEU non trouvées, seeder ignoré')
            return {'enjeux': [], 'fcr': [], 'responsabilites': []}

        # Plans de référence
        plan_camargue = plans[0] if len(plans) > 0 else None
        plan_aiguilles = plans[1] if len(plans) > 1 else None
        plan_vercors = plans[3] if len(plans) > 3 else None
        plan_remoray = plans[5] if len(plans) > 5 else None

        # Sites de référence
        site_camargue = sites[0] if len(sites) > 0 else None
        site_aiguilles = sites[1] if len(sites) > 1 else None
        site_vercors = sites[3] if len(sites) > 3 else None
        site_remoray = sites[6] if len(sites) > 6 else None

        enjeux_created = []
        fcr_created = []
        responsabilites_created = []

        # ==================== ENJEUX - CAMARGUE (5) ====================

        if plan_camargue:
            # Enjeu 1 - Priorité 1 - Écologique - Habitat
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_camargue,
                libelle='Conservation des habitats humides méditerranéens',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Hab. humides',
                    'rang': 1,
                    'id_importance': priorite_1,
                    'categorie_ecologique': True,
                    'habitat': True,
                    'espece': False,
                    'processus': False,
                    'etat_enjeu': 'Les habitats humides sont menacés par l\'assèchement et l\'urbanisation. '
                                  'Les sansouires, roselières et lagunes représentent 65% de la surface de la réserve.',
                    'description': 'Maintenir et restaurer les zones humides caractéristiques du delta du Rhône. '
                                   'Objectif : préserver les 8 500 ha de zones humides et restaurer 200 ha de marais dégradés.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='1150',
                defaults={'lb_hab_fr': 'Lagunes côtières'}
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='1410',
                defaults={'lb_hab_fr': 'Prés-salés méditerranéens (Juncetalia maritimi)'}
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='1420',
                defaults={'lb_hab_fr': 'Fourrés halophiles méditerranéens (Sarcocornetea)'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 2 - Priorité 1 - Écologique - Espèce
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_camargue,
                libelle='Protection du Flamant rose et des colonies nicheuses',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Flamant rose',
                    'rang': 1,
                    'id_importance': priorite_1,
                    'categorie_ecologique': True,
                    'habitat': False,
                    'espece': True,
                    'processus': False,
                    'etat_enjeu': 'Population stable mais sensible aux perturbations pendant la nidification. '
                                  'Environ 10 000 couples nicheurs sur l\'étang du Fangassier.',
                    'description': 'Assurer la tranquillité des sites de nidification et d\'alimentation. '
                                   'Suivi démographique annuel et contrôle de l\'accès aux zones sensibles.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuTaxon.objects.get_or_create(
                id_enjeu=enjeu, cd_nom=2517,
                defaults={'nom_complet': 'Phoenicopterus roseus', 'nom_vern': 'Flamant rose'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 3 - Priorité 2 - Socio-économique
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_camargue,
                libelle='Maintien des activités traditionnelles compatibles',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Activités trad.',
                    'rang': 2,
                    'id_importance': priorite_2,
                    'categorie_ecologique': False,
                    'habitat': False,
                    'espece': False,
                    'processus': True,
                    'etat_enjeu': 'Cohabitation parfois difficile entre conservation et activités économiques. '
                                  'Pression foncière croissante autour de la réserve.',
                    'description': 'Concilier pâturage extensif, saliculture et objectifs de conservation. '
                                   'Maintien de 3 exploitations de sel et 12 manades de taureaux et chevaux.',
                    'id_utilisateur_ajout': admin
                }
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 4 - Priorité 2 - Écologique - Processus + Habitat
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_camargue,
                libelle='Gestion hydraulique et fonctionnement des marais',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Hydraulique',
                    'rang': 2,
                    'id_importance': priorite_2,
                    'categorie_ecologique': True,
                    'habitat': True,
                    'espece': False,
                    'processus': True,
                    'etat_enjeu': 'Le fonctionnement hydraulique est perturbé par les aménagements '
                                  'du Rhône et la gestion rizicole en périphérie.',
                    'description': 'Restaurer la dynamique naturelle des échanges d\'eau entre le Rhône, '
                                   'les marais et la mer. Maintien de 45 km d\'ouvrages hydrauliques.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='1310',
                defaults={'lb_hab_fr': 'Végétations pionnières à Salicornia (prés-salés)'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 5 - Priorité 3 - Écologique - Espèce
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_camargue,
                libelle='Protection des populations de tortue cistude',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Cistude',
                    'rang': 3,
                    'id_importance': priorite_3,
                    'categorie_ecologique': True,
                    'habitat': False,
                    'espece': True,
                    'processus': False,
                    'etat_enjeu': 'Population estimée à 1 500 individus. '
                                  'Menacée par la tortue de Floride et la destruction d\'habitats.',
                    'description': 'Suivi des populations de Cistude d\'Europe (Emys orbicularis) '
                                   'et lutte contre la tortue de Floride envahissante.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuTaxon.objects.get_or_create(
                id_enjeu=enjeu, cd_nom=77634,
                defaults={'nom_complet': 'Emys orbicularis', 'nom_vern': 'Cistude d\'Europe'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

        # ==================== ENJEUX - AIGUILLES ROUGES (4) ====================

        if plan_aiguilles:
            # Enjeu 1 - Priorité 1 - Écologique - Habitat et espèce
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_aiguilles,
                libelle='Préservation des pelouses alpines et de leur faune associée',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Pelouses alp.',
                    'rang': 1,
                    'id_importance': priorite_1,
                    'categorie_ecologique': True,
                    'habitat': True,
                    'espece': True,
                    'processus': False,
                    'etat_enjeu': 'Habitats sensibles au piétinement et au changement climatique. '
                                  'Remontée altitudinale des espèces de basse altitude observée.',
                    'description': 'Protection des pelouses et de l\'avifaune nicheuse de haute montagne. '
                                   'Suivi de 12 placettes permanentes entre 2 000 et 2 700 m d\'altitude.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='6170',
                defaults={'lb_hab_fr': 'Pelouses calcaires alpines et subalpines'}
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='6150',
                defaults={'lb_hab_fr': 'Pelouses boréo-alpines siliceuses'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 2 - Priorité 2 - Habitat
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_aiguilles,
                libelle='Conservation des zones humides d\'altitude',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Zones humides alt.',
                    'rang': 2,
                    'id_importance': priorite_2,
                    'categorie_ecologique': True,
                    'habitat': True,
                    'espece': False,
                    'processus': False,
                    'etat_enjeu': 'Menacées par le réchauffement climatique. '
                                  'Assèchement progressif de 3 tourbières sur les 8 inventoriées.',
                    'description': 'Suivi et protection des lacs, tourbières et marais d\'altitude. '
                                   'Réseau de 15 piézomètres pour le suivi hydrique.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='7110',
                defaults={'lb_hab_fr': 'Tourbières hautes actives'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 3 - Priorité 1 - Écologique - Espèce + Habitat
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_aiguilles,
                libelle='Conservation du Tétras-lyre et de son habitat',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Tétras-lyre',
                    'rang': 1,
                    'id_importance': priorite_1,
                    'categorie_ecologique': True,
                    'habitat': True,
                    'espece': True,
                    'processus': False,
                    'etat_enjeu': 'Population en déclin de 15% sur les 10 dernières années. '
                                  'Dérangement hivernal par les activités de ski de randonnée.',
                    'description': 'Suivi des coqs au chant, protection des zones de nidification '
                                   'et sensibilisation des pratiquants de sports de montagne.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuTaxon.objects.get_or_create(
                id_enjeu=enjeu, cd_nom=2923,
                defaults={'nom_complet': 'Lyrurus tetrix', 'nom_vern': 'Tétras lyre'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 4 - Priorité 3 - Socio-économique
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_aiguilles,
                libelle='Maîtrise de la fréquentation touristique',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Fréquentation',
                    'rang': 3,
                    'id_importance': priorite_3,
                    'categorie_ecologique': False,
                    'habitat': False,
                    'espece': False,
                    'processus': True,
                    'etat_enjeu': 'Surfréquentation estivale sur le sentier du Lac Blanc '
                                  '(>500 passages/jour en juillet-août). Érosion des sentiers.',
                    'description': 'Canaliser les flux de randonneurs, restaurer les sentiers dégradés '
                                   'et sensibiliser le public à la fragilité des milieux alpins.',
                    'id_utilisateur_ajout': admin
                }
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

        # ==================== ENJEUX - VERCORS-ECRINS (2) ====================

        if plan_vercors:
            # Enjeu multi-sites
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_vercors,
                libelle='Continuité écologique des corridors forestiers',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Corridors forest.',
                    'rang': 1,
                    'id_importance': priorite_1,
                    'categorie_ecologique': True,
                    'habitat': True,
                    'espece': True,
                    'processus': True,
                    'etat_enjeu': 'Fragmentation croissante due aux infrastructures.',
                    'description': 'Maintenir les connexions entre massifs forestiers pour la grande faune.',
                    'id_utilisateur_ajout': admin
                }
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_vercors,
                libelle='Protection des populations de grands rapaces',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Grands rapaces',
                    'rang': 1,
                    'id_importance': priorite_1,
                    'categorie_ecologique': True,
                    'habitat': False,
                    'espece': True,
                    'processus': False,
                    'etat_enjeu': 'Populations fragiles, sensibles au dérangement.',
                    'description': 'Vautour fauve, Gypaète barbu, Aigle royal : suivi et protection.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuTaxon.objects.get_or_create(
                id_enjeu=enjeu, cd_nom=2873,
                defaults={'nom_complet': 'Gypaetus barbatus', 'nom_vern': 'Gypaète barbu'}
            )
            CorEnjeuTaxon.objects.get_or_create(
                id_enjeu=enjeu, cd_nom=2852,
                defaults={'nom_complet': 'Aquila chrysaetos', 'nom_vern': 'Aigle royal'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

        # ==================== ENJEUX - LAC DE REMORAY (5) ====================

        if plan_remoray:
            # Enjeu 1 - Priorité 1 - Écologique - Habitat + Processus
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_remoray,
                libelle='Préservation de la qualité des eaux du lac',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Qualité eaux',
                    'rang': 1,
                    'id_importance': priorite_1,
                    'categorie_ecologique': True,
                    'habitat': True,
                    'espece': False,
                    'processus': True,
                    'etat_enjeu': 'Eutrophisation modérée, surveillance nécessaire. '
                                  'Taux de phosphore total en hausse de 12% depuis 2018.',
                    'description': 'Maintenir le bon état écologique du lac et de son bassin versant. '
                                   'Suivi physico-chimique mensuel et biologique semestriel sur 6 stations.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='3150',
                defaults={'lb_hab_fr': 'Lacs eutrophes naturels avec végétation du Magnopotamion'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 2 - Priorité 1 - Écologique - Habitat + Espèce
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_remoray,
                libelle='Conservation des tourbières et prairies humides',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Tourbières',
                    'rang': 1,
                    'id_importance': priorite_1,
                    'categorie_ecologique': True,
                    'habitat': True,
                    'espece': True,
                    'processus': False,
                    'etat_enjeu': 'État de conservation variable selon les secteurs. '
                                  'Tourbière de Frasne bien conservée, celle du Crossat en voie d\'assèchement.',
                    'description': 'Protection et restauration des milieux tourbeux du bassin. '
                                   '45 ha de tourbières dont 12 ha en bon état de conservation.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='7110',
                defaults={'lb_hab_fr': 'Tourbières hautes actives'}
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='7230',
                defaults={'lb_hab_fr': 'Tourbières basses alcalines'}
            )
            CorEnjeuTaxon.objects.get_or_create(
                id_enjeu=enjeu, cd_nom=104398,
                defaults={'nom_complet': 'Drosera rotundifolia', 'nom_vern': 'Droséra à feuilles rondes'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 3 - Priorité 1 - Écologique - Espèce
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_remoray,
                libelle='Protection du Balbuzard pêcheur en halte migratoire',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Balbuzard',
                    'rang': 1,
                    'id_importance': priorite_1,
                    'categorie_ecologique': True,
                    'habitat': False,
                    'espece': True,
                    'processus': False,
                    'etat_enjeu': 'Site de halte migratoire régulier pour 2-4 individus au printemps '
                                  'et 3-6 individus en automne. Possibilité de nidification future.',
                    'description': 'Suivi du Balbuzard pêcheur (Pandion haliaetus) en halte migratoire '
                                   'et préparation d\'un programme de nidification assistée.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuTaxon.objects.get_or_create(
                id_enjeu=enjeu, cd_nom=2840,
                defaults={'nom_complet': 'Pandion haliaetus', 'nom_vern': 'Balbuzard pêcheur'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 4 - Priorité 2 - Écologique - Habitat
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_remoray,
                libelle='Conservation des prairies de fauche de montagne',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'Prairies fauche',
                    'rang': 2,
                    'id_importance': priorite_2,
                    'categorie_ecologique': True,
                    'habitat': True,
                    'espece': False,
                    'processus': False,
                    'etat_enjeu': 'Prairies menacées par l\'intensification agricole et l\'abandon. '
                                  '35 ha encore gérés traditionnellement.',
                    'description': 'Maintien des pratiques de fauche tardive et pâturage extensif. '
                                   'Convention avec 5 exploitants agricoles locaux.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuHabitat.objects.get_or_create(
                id_enjeu=enjeu, cd_hab='6520',
                defaults={'lb_hab_fr': 'Prairies de fauche de montagne'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

            # Enjeu 5 - Priorité 3 - Écologique - Processus
            enjeu, created = Enjeu.objects.update_or_create(
                id_pg=plan_remoray,
                libelle='Gestion des espèces exotiques envahissantes',
                defaults={
                    'id_categorie': cat_enjeu,
                    'intitule_court': 'EEE',
                    'rang': 3,
                    'id_importance': priorite_3,
                    'categorie_ecologique': True,
                    'habitat': False,
                    'espece': True,
                    'processus': True,
                    'etat_enjeu': 'Présence de Renouée du Japon sur 3 stations le long du Drugeon. '
                                  'Écrevisse de Californie détectée dans le lac en 2021.',
                    'description': 'Programme de lutte et de veille contre les espèces exotiques envahissantes. '
                                   'Arrachage annuel de la Renouée et piégeage des écrevisses invasives.',
                    'id_utilisateur_ajout': admin
                }
            )
            CorEnjeuTaxon.objects.get_or_create(
                id_enjeu=enjeu, cd_nom=117835,
                defaults={'nom_complet': 'Reynoutria japonica', 'nom_vern': 'Renouée du Japon'}
            )
            enjeux_created.append(enjeu)
            self.log_item('créé' if created else 'mis à jour', f'Enjeu: {enjeu.intitule_court}')

        # ==================== FCR - CAMARGUE (2) ====================

        if plan_camargue and fcr_connaissance:
            fcr, created = Enjeu.objects.update_or_create(
                id_pg=plan_camargue,
                libelle='Amélioration des connaissances sur les espèces patrimoniales',
                defaults={
                    'id_categorie': cat_fcr,
                    'intitule_court': 'Connaissance esp.',
                    'id_categorie_fcr': fcr_connaissance,
                    'description': 'Poursuivre les inventaires et le suivi des populations. '
                                   'Renforcement des partenariats avec la Tour du Valat et le CNRS.',
                    'id_utilisateur_ajout': admin
                }
            )
            fcr_created.append(fcr)
            self.log_item('créé' if created else 'mis à jour', f'FCR: {fcr.intitule_court}')

            fcr, created = Enjeu.objects.update_or_create(
                id_pg=plan_camargue,
                libelle='Renforcement des partenariats locaux',
                defaults={
                    'id_categorie': cat_fcr,
                    'intitule_court': 'Partenariats',
                    'id_categorie_fcr': fcr_ancrage,
                    'description': 'Développer les collaborations avec les acteurs du territoire. '
                                   'Conventions avec le Parc naturel régional de Camargue et les mairies.',
                    'id_utilisateur_ajout': admin
                }
            )
            fcr_created.append(fcr)
            self.log_item('créé' if created else 'mis à jour', f'FCR: {fcr.intitule_court}')

        # ==================== FCR - AIGUILLES ROUGES (2) ====================

        if plan_aiguilles and fcr_fonctionnement:
            fcr, created = Enjeu.objects.update_or_create(
                id_pg=plan_aiguilles,
                libelle='Optimisation des moyens humains et financiers',
                defaults={
                    'id_categorie': cat_fcr,
                    'intitule_court': 'Moyens',
                    'id_categorie_fcr': fcr_fonctionnement,
                    'description': 'Assurer la pérennité des moyens de gestion. '
                                   'Mutualisation des gardes avec la RNN des Contamines-Montjoie.',
                    'id_utilisateur_ajout': admin
                }
            )
            fcr_created.append(fcr)
            self.log_item('créé' if created else 'mis à jour', f'FCR: {fcr.intitule_court}')

            fcr, created = Enjeu.objects.update_or_create(
                id_pg=plan_aiguilles,
                libelle='Développement des connaissances sur le changement climatique',
                defaults={
                    'id_categorie': cat_fcr,
                    'intitule_court': 'Climat',
                    'id_categorie_fcr': fcr_connaissance,
                    'description': 'Suivre les impacts du changement climatique sur les milieux. '
                                   'Participation au programme Sentinelles du Climat.',
                    'id_utilisateur_ajout': admin
                }
            )
            fcr_created.append(fcr)
            self.log_item('créé' if created else 'mis à jour', f'FCR: {fcr.intitule_court}')

        # ==================== FCR - VERCORS-ECRINS (2) ====================

        if plan_vercors and fcr_ancrage:
            fcr, created = Enjeu.objects.update_or_create(
                id_pg=plan_vercors,
                libelle='Coordination inter-sites et inter-gestionnaires',
                defaults={
                    'id_categorie': cat_fcr,
                    'intitule_court': 'Coordination',
                    'id_categorie_fcr': fcr_fonctionnement,
                    'description': 'Harmoniser les pratiques de gestion entre les deux sites.',
                    'id_utilisateur_ajout': admin
                }
            )
            fcr_created.append(fcr)
            self.log_item('créé' if created else 'mis à jour', f'FCR: {fcr.intitule_court}')

            fcr, created = Enjeu.objects.update_or_create(
                id_pg=plan_vercors,
                libelle='Sensibilisation des usagers de la montagne',
                defaults={
                    'id_categorie': cat_fcr,
                    'intitule_court': 'Sensibilisation',
                    'id_categorie_fcr': fcr_ancrage,
                    'description': 'Informer les randonneurs et pratiquants de sports de nature.',
                    'id_utilisateur_ajout': admin
                }
            )
            fcr_created.append(fcr)
            self.log_item('créé' if created else 'mis à jour', f'FCR: {fcr.intitule_court}')

        # ==================== FCR - LAC DE REMORAY (2) ====================

        if plan_remoray and fcr_connaissance:
            fcr, created = Enjeu.objects.update_or_create(
                id_pg=plan_remoray,
                libelle='Mise en place d\'un suivi hydrologique intégré',
                defaults={
                    'id_categorie': cat_fcr,
                    'intitule_court': 'Suivi hydro.',
                    'id_categorie_fcr': fcr_connaissance,
                    'description': 'Déploiement d\'un réseau de suivi hydrologique '
                                   'couvrant le lac, les tourbières et le bassin du Drugeon. '
                                   'Partenariat avec l\'Université de Franche-Comté.',
                    'id_utilisateur_ajout': admin
                }
            )
            fcr_created.append(fcr)
            self.log_item('créé' if created else 'mis à jour', f'FCR: {fcr.intitule_court}')

            fcr, created = Enjeu.objects.update_or_create(
                id_pg=plan_remoray,
                libelle='Intégration dans les politiques territoriales',
                defaults={
                    'id_categorie': cat_fcr,
                    'intitule_court': 'Territ. intégr.',
                    'id_categorie_fcr': fcr_ancrage,
                    'description': 'Inscrire le plan de gestion dans le SAGE Haut-Doubs '
                                   'et le Contrat de rivière Drugeon. Collaboration avec la '
                                   'Communauté de communes Frasne-Drugeon.',
                    'id_utilisateur_ajout': admin
                }
            )
            fcr_created.append(fcr)
            self.log_item('créé' if created else 'mis à jour', f'FCR: {fcr.intitule_court}')

        # ==================== RESPONSABILITÉS - CAMARGUE (3) ====================

        if site_camargue and resp_faunistique and niveau_national:
            resp, created = Responsabilite.objects.update_or_create(
                id_site=site_camargue,
                id_type_responsabilite=resp_faunistique,
                id_niveau_responsabilite=niveau_national,
                defaults={
                    'description': 'Site majeur pour la reproduction du Flamant rose en France. '
                                   'Seule colonie de nidification régulière en France métropolitaine '
                                   '(10 000 couples). Accueille 50 000 oiseaux d\'eau en hiver.',
                    'id_utilisateur_ajout': admin
                }
            )
            # Lier à l'enjeu Flamant rose si existe
            enjeu_flamant = next((e for e in enjeux_created if 'Flamant' in e.libelle), None)
            if enjeu_flamant:
                CorResponsabiliteEnjeu.objects.get_or_create(
                    id_responsabilite=resp,
                    id_enjeu=enjeu_flamant
                )
            # Taxon lié
            CorResponsabiliteTaxon.objects.get_or_create(
                id_responsabilite=resp, cd_nom=2517,
                defaults={'nom_complet': 'Phoenicopterus roseus', 'nom_vern': 'Flamant rose'}
            )
            responsabilites_created.append(resp)
            self.log_item('créé' if created else 'mis à jour', f'Responsabilité: Camargue - Faune nat.')

            resp, created = Responsabilite.objects.update_or_create(
                id_site=site_camargue,
                id_type_responsabilite=resp_habitat,
                id_niveau_responsabilite=niveau_regional,
                defaults={
                    'description': 'Habitats saumâtres uniques en région méditerranéenne française. '
                                   'Plus grande zone humide de France (13 000 ha de marais et lagunes).',
                    'id_utilisateur_ajout': admin
                }
            )
            # Habitat lié
            CorResponsabiliteHabitat.objects.get_or_create(
                id_responsabilite=resp, cd_hab='1150',
                defaults={'lb_hab_fr': 'Lagunes côtières'}
            )
            CorResponsabiliteHabitat.objects.get_or_create(
                id_responsabilite=resp, cd_hab='1410',
                defaults={'lb_hab_fr': 'Prés-salés méditerranéens (Juncetalia maritimi)'}
            )
            responsabilites_created.append(resp)
            self.log_item('créé' if created else 'mis à jour', f'Responsabilité: Camargue - Habitat rég.')

        if site_camargue and resp_faunistique and niveau_international:
            resp, created = Responsabilite.objects.update_or_create(
                id_site=site_camargue,
                id_type_responsabilite=resp_faunistique,
                id_niveau_responsabilite=niveau_international,
                defaults={
                    'description': 'Site Ramsar d\'importance internationale pour les oiseaux d\'eau migrateurs. '
                                   'Halte migratoire majeure sur la voie de migration ouest-méditerranéenne.',
                    'id_utilisateur_ajout': admin
                }
            )
            # Lier à l'enjeu cistude si existe
            enjeu_cistude = next((e for e in enjeux_created if 'cistude' in e.libelle), None)
            if enjeu_cistude:
                CorResponsabiliteEnjeu.objects.get_or_create(
                    id_responsabilite=resp,
                    id_enjeu=enjeu_cistude
                )
            responsabilites_created.append(resp)
            self.log_item('créé' if created else 'mis à jour', f'Responsabilité: Camargue - Faune internat.')

        # ==================== RESPONSABILITÉS - AIGUILLES ROUGES (3) ====================

        if site_aiguilles and resp_floristique and niveau_regional:
            resp, created = Responsabilite.objects.update_or_create(
                id_site=site_aiguilles,
                id_type_responsabilite=resp_floristique,
                id_niveau_responsabilite=niveau_regional,
                defaults={
                    'description': 'Flore alpine rare et endémique des Alpes du Nord. '
                                   '847 espèces végétales inventoriées dont 23 protégées au niveau régional.',
                    'id_utilisateur_ajout': admin
                }
            )
            responsabilites_created.append(resp)
            self.log_item('créé' if created else 'mis à jour', f'Responsabilité: Aiguilles Rouges - Flore rég.')

            resp, created = Responsabilite.objects.update_or_create(
                id_site=site_aiguilles,
                id_type_responsabilite=resp_faunistique,
                id_niveau_responsabilite=niveau_local,
                defaults={
                    'description': 'Populations de bouquetins et chamois en expansion. '
                                   'Harde de 180 bouquetins et 350 chamois sur le massif.',
                    'id_utilisateur_ajout': admin
                }
            )
            responsabilites_created.append(resp)
            self.log_item('créé' if created else 'mis à jour', f'Responsabilité: Aiguilles Rouges - Faune loc.')

        if site_aiguilles and resp_faunistique and niveau_regional:
            resp, created = Responsabilite.objects.update_or_create(
                id_site=site_aiguilles,
                id_type_responsabilite=resp_faunistique,
                id_niveau_responsabilite=niveau_regional,
                defaults={
                    'description': 'Population de Tétras-lyre parmi les plus importantes de Haute-Savoie. '
                                   'Site de reproduction de l\'Aigle royal et du Lagopède alpin.',
                    'id_utilisateur_ajout': admin
                }
            )
            enjeu_tetras = next((e for e in enjeux_created if 'Tétras' in e.libelle), None)
            if enjeu_tetras:
                CorResponsabiliteEnjeu.objects.get_or_create(
                    id_responsabilite=resp,
                    id_enjeu=enjeu_tetras
                )
            CorResponsabiliteTaxon.objects.get_or_create(
                id_responsabilite=resp, cd_nom=2923,
                defaults={'nom_complet': 'Lyrurus tetrix', 'nom_vern': 'Tétras lyre'}
            )
            responsabilites_created.append(resp)
            self.log_item('créé' if created else 'mis à jour', f'Responsabilité: Aiguilles Rouges - Faune rég.')

        # ==================== RESPONSABILITÉS - VERCORS (2) ====================

        if site_vercors and resp_faunistique and niveau_national:
            resp, created = Responsabilite.objects.update_or_create(
                id_site=site_vercors,
                id_type_responsabilite=resp_faunistique,
                id_niveau_responsabilite=niveau_national,
                defaults={
                    'description': 'Site majeur pour la réintroduction des grands rapaces.',
                    'id_utilisateur_ajout': admin
                }
            )
            enjeu_rapaces = next((e for e in enjeux_created if 'rapaces' in e.libelle), None)
            if enjeu_rapaces:
                CorResponsabiliteEnjeu.objects.get_or_create(
                    id_responsabilite=resp,
                    id_enjeu=enjeu_rapaces
                )
            responsabilites_created.append(resp)
            self.log_item('créé' if created else 'mis à jour', f'Responsabilité: Vercors - Rapaces')

            resp, created = Responsabilite.objects.update_or_create(
                id_site=site_vercors,
                id_type_responsabilite=resp_habitat,
                id_niveau_responsabilite=niveau_regional,
                defaults={
                    'description': 'Forêts anciennes et falaises calcaires remarquables.',
                    'id_utilisateur_ajout': admin
                }
            )
            responsabilites_created.append(resp)
            self.log_item('créé' if created else 'mis à jour', f'Responsabilité: Vercors - Habitat')

        # ==================== RESPONSABILITÉS - LAC DE REMORAY (2) ====================

        if site_remoray and resp_faunistique and niveau_regional:
            resp, created = Responsabilite.objects.update_or_create(
                id_site=site_remoray,
                id_type_responsabilite=resp_faunistique,
                id_niveau_responsabilite=niveau_regional,
                defaults={
                    'description': 'Site de halte migratoire du Balbuzard pêcheur. '
                                   'Zone d\'hivernage de la Bécassine des marais et du Râle d\'eau.',
                    'id_utilisateur_ajout': admin
                }
            )
            enjeu_balbuzard = next((e for e in enjeux_created if 'Balbuzard' in e.libelle), None)
            if enjeu_balbuzard:
                CorResponsabiliteEnjeu.objects.get_or_create(
                    id_responsabilite=resp,
                    id_enjeu=enjeu_balbuzard
                )
            CorResponsabiliteTaxon.objects.get_or_create(
                id_responsabilite=resp, cd_nom=2840,
                defaults={'nom_complet': 'Pandion haliaetus', 'nom_vern': 'Balbuzard pêcheur'}
            )
            responsabilites_created.append(resp)
            self.log_item('créé' if created else 'mis à jour', f'Responsabilité: Remoray - Faune rég.')

        if site_remoray and resp_habitat and niveau_national:
            resp, created = Responsabilite.objects.update_or_create(
                id_site=site_remoray,
                id_type_responsabilite=resp_habitat,
                id_niveau_responsabilite=niveau_national,
                defaults={
                    'description': 'Tourbières d\'importance nationale : complexe tourbeux de Frasne-Remoray, '
                                   'inscrit au réseau national des tourbières. '
                                   'Habitats rares en bon état de conservation.',
                    'id_utilisateur_ajout': admin
                }
            )
            enjeu_tourbieres = next((e for e in enjeux_created if 'tourbières' in e.libelle), None)
            if enjeu_tourbieres:
                CorResponsabiliteEnjeu.objects.get_or_create(
                    id_responsabilite=resp,
                    id_enjeu=enjeu_tourbieres
                )
            CorResponsabiliteHabitat.objects.get_or_create(
                id_responsabilite=resp, cd_hab='7110',
                defaults={'lb_hab_fr': 'Tourbières hautes actives'}
            )
            CorResponsabiliteHabitat.objects.get_or_create(
                id_responsabilite=resp, cd_hab='7230',
                defaults={'lb_hab_fr': 'Tourbières basses alcalines'}
            )
            responsabilites_created.append(resp)
            self.log_item('créé' if created else 'mis à jour', f'Responsabilité: Remoray - Habitat nat.')

        # ==================== FACTEURS D'INFLUENCE ET PRESSIONS ====================

        facteurs_created = []
        pressions_created = []

        # Camargue - Habitats humides : facteurs d'influence
        enjeu_hab_humides = next((e for e in enjeux_created if 'habitats humides' in e.libelle), None)
        if enjeu_hab_humides:
            fi, created = FacteurInfluence.objects.update_or_create(
                id_enjeu=enjeu_hab_humides,
                libelle='Modification du régime hydrologique',
                defaults={
                    'description': 'Les aménagements du Rhône et la gestion agricole perturbent '
                                   'le fonctionnement hydrologique naturel des zones humides.',
                    'id_utilisateur_ajout': admin
                }
            )
            facteurs_created.append(fi)
            self.log_item('créé' if created else 'mis à jour', f'Facteur: {fi.libelle}')

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Endiguement du Rhône',
                defaults={
                    'description': 'Les digues limitent les échanges naturels entre le fleuve et les marais.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Pompages agricoles',
                defaults={
                    'description': 'Les prélèvements d\'eau pour la riziculture réduisent les niveaux des nappes.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

            fi, created = FacteurInfluence.objects.update_or_create(
                id_enjeu=enjeu_hab_humides,
                libelle='Urbanisation et artificialisation',
                defaults={
                    'description': 'Pression foncière croissante en périphérie de la réserve.',
                    'id_utilisateur_ajout': admin
                }
            )
            facteurs_created.append(fi)
            self.log_item('créé' if created else 'mis à jour', f'Facteur: {fi.libelle}')

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Extension des zones bâties',
                defaults={
                    'description': 'Construction de lotissements et infrastructures touristiques.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

        # Camargue - Flamant rose : facteur d'influence
        enjeu_flamant = next((e for e in enjeux_created if 'Flamant' in e.libelle), None)
        if enjeu_flamant:
            fi, created = FacteurInfluence.objects.update_or_create(
                id_enjeu=enjeu_flamant,
                libelle='Fréquentation touristique',
                defaults={
                    'description': 'L\'afflux de visiteurs perturbe les zones de nidification et d\'alimentation.',
                    'id_utilisateur_ajout': admin
                }
            )
            facteurs_created.append(fi)
            self.log_item('créé' if created else 'mis à jour', f'Facteur: {fi.libelle}')

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Dérangement en période de nidification',
                defaults={
                    'description': 'Survol de drones et approche des photographes perturbant les colonies.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Bruit des activités nautiques',
                defaults={
                    'description': 'Navigation motorisée à proximité des zones de repos.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

        # Aiguilles Rouges - Pelouses alpines : facteur d'influence
        enjeu_pelouses = next((e for e in enjeux_created if 'pelouses alpines' in e.libelle), None)
        if enjeu_pelouses:
            fi, created = FacteurInfluence.objects.update_or_create(
                id_enjeu=enjeu_pelouses,
                libelle='Changement climatique',
                defaults={
                    'description': 'Le réchauffement modifie la distribution altitudinale des espèces végétales.',
                    'id_utilisateur_ajout': admin
                }
            )
            facteurs_created.append(fi)
            self.log_item('créé' if created else 'mis à jour', f'Facteur: {fi.libelle}')

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Remontée de la limite forestière',
                defaults={
                    'description': 'Les arbustes colonisent progressivement les pelouses d\'altitude.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

            fi, created = FacteurInfluence.objects.update_or_create(
                id_enjeu=enjeu_pelouses,
                libelle='Surfréquentation des sentiers',
                defaults={
                    'description': 'Le piétinement des randonneurs dégrade les pelouses fragiles.',
                    'id_utilisateur_ajout': admin
                }
            )
            facteurs_created.append(fi)
            self.log_item('créé' if created else 'mis à jour', f'Facteur: {fi.libelle}')

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Érosion des sentiers de randonnée',
                defaults={
                    'description': 'Plus de 500 passages par jour en haute saison sur certains sentiers.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

        # Aiguilles Rouges - Tétras-lyre : facteur d'influence
        enjeu_tetras = next((e for e in enjeux_created if 'Tétras-lyre' in e.libelle), None)
        if enjeu_tetras:
            fi, created = FacteurInfluence.objects.update_or_create(
                id_enjeu=enjeu_tetras,
                libelle='Activités hivernales',
                defaults={
                    'description': 'Le ski de randonnée et les raquettes perturbent les zones d\'hivernage.',
                    'id_utilisateur_ajout': admin
                }
            )
            facteurs_created.append(fi)
            self.log_item('créé' if created else 'mis à jour', f'Facteur: {fi.libelle}')

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Dérangement hivernal du tétras-lyre',
                defaults={
                    'description': 'L\'envol forcé des oiseaux en hiver augmente leur dépense énergétique.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

        # Remoray - Qualité eaux : facteur d'influence
        enjeu_qualite = next((e for e in enjeux_created if 'qualité des eaux' in e.libelle), None)
        if enjeu_qualite:
            fi, created = FacteurInfluence.objects.update_or_create(
                id_enjeu=enjeu_qualite,
                libelle='Activités agricoles du bassin versant',
                defaults={
                    'description': 'Les pratiques agricoles intensives contribuent à l\'eutrophisation du lac.',
                    'id_utilisateur_ajout': admin
                }
            )
            facteurs_created.append(fi)
            self.log_item('créé' if created else 'mis à jour', f'Facteur: {fi.libelle}')

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Lessivage des engrais',
                defaults={
                    'description': 'Apports de nitrates et phosphates par ruissellement.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Effluents d\'élevage',
                defaults={
                    'description': 'Rejets des exploitations laitières dans les affluents du lac.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

        # Remoray - Tourbières : facteur d'influence
        enjeu_tourbieres = next((e for e in enjeux_created if 'tourbières' in e.libelle.lower()), None)
        if enjeu_tourbieres:
            fi, created = FacteurInfluence.objects.update_or_create(
                id_enjeu=enjeu_tourbieres,
                libelle='Assèchement des zones humides',
                defaults={
                    'description': 'Le drainage ancien et le changement climatique entraînent '
                                   'un assèchement progressif des tourbières.',
                    'id_utilisateur_ajout': admin
                }
            )
            facteurs_created.append(fi)
            self.log_item('créé' if created else 'mis à jour', f'Facteur: {fi.libelle}')

            p, created = Pression.objects.update_or_create(
                id_facteur_influence=fi,
                libelle='Réseaux de drainage historiques',
                defaults={
                    'description': 'Fossés de drainage creusés au XIXe siècle toujours actifs.',
                    'id_utilisateur_ajout': admin
                }
            )
            pressions_created.append(p)

        # =====================================================================
        # États Actuels, OLTs et Niveaux d'Exigence
        # =====================================================================
        etats_created = []
        olts_created = []
        nes_created = []

        # Camargue - Habitats humides : état actuel + OLT + niveaux d'exigence
        enjeu_hab_humides = next((e for e in enjeux_created if 'habitats humides' in e.libelle.lower()), None)
        if enjeu_hab_humides:
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_hab_humides,
                libelle='Restaurer et maintenir un fonctionnement hydrologique naturel',
                defaults={
                    'description': 'Atteindre un régime hydrologique permettant le maintien '
                                   'des communautés végétales et animales caractéristiques '
                                   'des zones humides camarguaises.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Dégradation progressive des habitats humides',
                defaults={
                    'description': 'Les habitats humides de Camargue subissent une dégradation '
                                   'progressive liée aux modifications du régime hydrologique '
                                   'et à la pression urbaine croissante.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Surface en bon état de conservation ≥ 70%',
                defaults={
                    'description': 'Au moins 70% de la surface des habitats humides '
                                   'doit être en bon état de conservation.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

            ne2, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Débit écologique minimal respecté 90% du temps',
                defaults={
                    'description': 'Le débit écologique minimal doit être respecté '
                                   'au moins 90% du temps sur les cours d\'eau alimentant les zones humides.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne2)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne2.libelle[:50]}')

        # Camargue - Flamant rose : état actuel + OLT
        enjeu_flamant = next((e for e in enjeux_created if 'flamant' in e.libelle.lower()), None)
        if enjeu_flamant:
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_flamant,
                libelle='Maintenir une population nicheuse viable à long terme',
                defaults={
                    'description': 'Assurer le maintien d\'une population reproductrice '
                                   'de flamants roses en Camargue avec un succès de '
                                   'reproduction régulier.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Population stable mais sensible aux dérangements',
                defaults={
                    'description': 'La colonie de flamants roses de Camargue est stable '
                                   'mais reste vulnérable aux dérangements en période '
                                   'de nidification.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Succès de reproduction ≥ 0.5 jeune/couple/an',
                defaults={
                    'description': 'Le taux de reproduction moyen doit atteindre '
                                   'au moins 0.5 jeune à l\'envol par couple reproducteur.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

        # Camargue - Cistude : état actuel + OLT + NE
        enjeu_cistude = next((e for e in enjeux_created if 'cistude' in e.libelle.lower()), None)
        if enjeu_cistude:
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_cistude,
                libelle='Restaurer la connectivité entre les noyaux de population',
                defaults={
                    'description': 'Rétablir des corridors fonctionnels entre les '
                                   'sous-populations de cistude et maintenir des sites '
                                   'de ponte favorables.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Population fragmentée avec perte d\'habitats de ponte',
                defaults={
                    'description': 'Les populations de cistude d\'Europe sont fragmentées. '
                                   'Les sites de ponte se raréfient en raison de la '
                                   'fermeture des milieux et de l\'urbanisation.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Au moins 3 sites de ponte actifs maintenus',
                defaults={
                    'description': 'Maintenir au minimum 3 sites de ponte '
                                   'régulièrement fréquentés par les femelles.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

        # Aiguilles Rouges - Pelouses alpines : 2 états actuels (cas N:N)
        enjeu_pelouses = next((e for e in enjeux_created if 'pelouses alpines' in e.libelle.lower()), None)
        if enjeu_pelouses:
            # OLT 1 : flore
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_pelouses,
                libelle='Préserver les stations relictuelles d\'espèces arctico-alpines',
                defaults={
                    'description': 'Protéger et suivre les stations d\'espèces '
                                   'arctico-alpines en limite d\'aire comme témoins '
                                   'du changement climatique.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat_flore, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Recul des espèces arctico-alpines en limite d\'aire',
                defaults={
                    'description': 'Les inventaires floristiques montrent un recul '
                                   'des espèces arctico-alpines, indicateurs du '
                                   'réchauffement climatique en altitude.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat_flore)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat_flore.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Pas de disparition de station connue sur 10 ans',
                defaults={
                    'description': 'Aucune station d\'espèce arctico-alpine recensée '
                                   'ne doit disparaître sur la durée du plan.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

            # OLT 2 : érosion
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_pelouses,
                libelle='Canaliser la fréquentation pour limiter l\'érosion',
                defaults={
                    'description': 'Réduire l\'impact du piétinement hors sentier '
                                   'et restaurer les zones dégradées par une '
                                   'gestion adaptée de la fréquentation.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat_erosion, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Érosion des sols par surfréquentation des sentiers',
                defaults={
                    'description': 'La fréquentation estivale croissante entraîne une '
                                   'dégradation des pelouses alpines par piétinement '
                                   'et érosion des sentiers.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat_erosion)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat_erosion.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Réduction de 50% des surfaces érodées hors sentier',
                defaults={
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

        # Aiguilles Rouges - Tétras-lyre : état actuel + OLT + NE
        enjeu_tetras = next((e for e in enjeux_created if 'tétras' in e.libelle.lower()), None)
        if enjeu_tetras:
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_tetras,
                libelle='Stabiliser la population de tétras-lyre',
                defaults={
                    'description': 'Maintenir un effectif viable de tétras-lyre '
                                   'en réduisant les sources de dérangement '
                                   'en période critique (hivernage, reproduction).',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Population en déclin lié aux dérangements hivernaux',
                defaults={
                    'description': 'Les comptages au chant montrent une tendance '
                                   'à la baisse des effectifs, corrélée au développement '
                                   'des activités de pleine nature hivernales.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Tendance démographique stable ou positive sur 5 ans',
                defaults={
                    'description': 'L\'indice d\'abondance au chant doit montrer '
                                   'une tendance stable ou en hausse.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

        # Vercors - Grands rapaces : état actuel + OLT + NE
        enjeu_rapaces = next((e for e in enjeux_created if 'rapaces' in e.libelle.lower()), None)
        if enjeu_rapaces:
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_rapaces,
                libelle='Consolider les noyaux de population de grands rapaces',
                defaults={
                    'description': 'Assurer la pérennité des couples nicheurs et '
                                   'favoriser l\'installation de nouveaux couples '
                                   'dans les zones favorables du massif.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Recolonisation en cours mais noyaux fragiles',
                defaults={
                    'description': 'Le gypaète barbu et l\'aigle royal recolonisent '
                                   'progressivement le massif, mais les couples '
                                   'nicheurs restent peu nombreux et sensibles.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Au moins 2 couples nicheurs de gypaète dans le massif',
                defaults={
                    'description': 'L\'objectif est d\'atteindre au minimum 2 couples '
                                   'nicheurs de gypaète barbu installés durablement.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

            ne2, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Succès de reproduction du gypaète ≥ 0.4 jeune/couple/an',
                defaults={
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne2)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne2.libelle[:50]}')

        # Remoray - Qualité des eaux : état actuel + OLT + NE
        enjeu_eaux = next((e for e in enjeux_created if 'qualité' in e.libelle.lower() and 'eaux' in e.libelle.lower()), None)
        if enjeu_eaux:
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_eaux,
                libelle='Atteindre le bon état écologique du lac',
                defaults={
                    'description': 'Réduire les apports en nutriments pour atteindre '
                                   'le bon état écologique au sens de la DCE.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Eutrophisation modérée en augmentation',
                defaults={
                    'description': 'Le lac de Remoray montre des signes d\'eutrophisation '
                                   'croissante liée aux apports agricoles du bassin versant.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Concentration en phosphore total < 20 µg/L',
                defaults={
                    'description': 'La concentration moyenne annuelle en phosphore '
                                   'total dans la colonne d\'eau doit rester '
                                   'inférieure au seuil de bon état.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

        # Remoray - Tourbières : état actuel + OLT + NE
        enjeu_tourbieres = next((e for e in enjeux_created if 'tourbières' in e.libelle.lower()), None)
        if enjeu_tourbieres:
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_tourbieres,
                libelle='Restaurer le fonctionnement hydrologique des tourbières',
                defaults={
                    'description': 'Rétablir des niveaux d\'eau favorables au '
                                   'maintien des communautés turficoles et à '
                                   'l\'accumulation de tourbe.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Assèchement progressif et colonisation ligneuse',
                defaults={
                    'description': 'Les tourbières subissent un assèchement lié au '
                                   'drainage historique et au changement climatique, '
                                   'favorisant la colonisation par les ligneux.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Niveau piézométrique moyen ≤ 20 cm sous la surface',
                defaults={
                    'description': 'Le niveau moyen de la nappe ne doit pas '
                                   'descendre à plus de 20 cm sous la surface '
                                   'pendant la saison de végétation.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

        # Remoray - Balbuzard pêcheur : état actuel + OLT + NE
        enjeu_balbuzard = next((e for e in enjeux_created if 'balbuzard' in e.libelle.lower()), None)
        if enjeu_balbuzard:
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_balbuzard,
                libelle='Garantir la quiétude du site en période de migration',
                defaults={
                    'description': 'Assurer des conditions d\'accueil optimales '
                                   'pour les balbuzards en halte migratoire '
                                   'en limitant les dérangements sur le lac.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Site de halte migratoire régulier mais non protégé',
                defaults={
                    'description': 'Le lac de Remoray constitue un site de halte '
                                   'migratoire régulier pour le balbuzard pêcheur, '
                                   'mais le site n\'est pas encore aménagé pour '
                                   'limiter les dérangements.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Présence régulière ≥ 3 individus en halte migratoire',
                defaults={
                    'description': 'Le site doit accueillir au minimum 3 balbuzards '
                                   'en halte migratoire régulière chaque saison '
                                   '(printemps et automne).',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

            ne2, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Durée moyenne de halte ≥ 5 jours par individu',
                defaults={
                    'description': 'La durée moyenne de séjour des balbuzards en halte '
                                   'doit atteindre au moins 5 jours, indicateur de la '
                                   'qualité du site d\'accueil.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne2)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne2.libelle[:50]}')

        # Remoray - Prairies de fauche : état actuel + OLT + NE
        enjeu_prairies = next((e for e in enjeux_created if 'prairies de fauche' in e.libelle.lower()), None)
        if enjeu_prairies:
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_prairies,
                libelle='Maintenir les prairies de fauche en gestion extensive',
                defaults={
                    'description': 'Conserver les surfaces de prairies de fauche '
                                   'gérées de manière extensive et restaurer les '
                                   'parcelles abandonnées ou intensifiées.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Régression des surfaces gérées traditionnellement',
                defaults={
                    'description': 'Les prairies de fauche de montagne régressent '
                                   'sous l\'effet de l\'intensification agricole '
                                   'et de l\'abandon de parcelles marginales. '
                                   '35 ha encore gérés de façon traditionnelle.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Surface en fauche tardive ≥ 30 ha',
                defaults={
                    'description': 'Maintenir au minimum 30 ha de prairies '
                                   'gérées en fauche tardive (après le 15 juillet).',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

            ne2, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Richesse floristique ≥ 25 espèces/relevé',
                defaults={
                    'description': 'La richesse spécifique moyenne des relevés '
                                   'phytosociologiques doit rester supérieure à '
                                   '25 espèces par relevé standardisé.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne2)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne2.libelle[:50]}')

        # Remoray - EEE : OLT + état actuel + NE
        enjeu_eee = next((e for e in enjeux_created if e.intitule_court == 'EEE'), None)
        if enjeu_eee:
            olt, created = ObjectifLongTerme.objects.update_or_create(
                id_enjeu=enjeu_eee,
                libelle='Contenir et réduire les populations d\'EEE',
                defaults={
                    'description': 'Empêcher l\'extension des espèces exotiques '
                                   'envahissantes et réduire les surfaces colonisées '
                                   'par des campagnes d\'arrachage et de piégeage.',
                    'id_utilisateur_ajout': admin
                }
            )
            olts_created.append(olt)
            self.log_item('créé' if created else 'mis à jour', f'OLT: {olt.libelle[:50]}')

            etat, created = EtatActuel.objects.update_or_create(
                id_olt=olt,
                libelle='Colonisation active par la Renouée du Japon',
                defaults={
                    'description': 'La Renouée du Japon colonise activement les berges '
                                   'du lac et les zones humides adjacentes, menaçant '
                                   'la biodiversité locale par compétition.',
                    'id_utilisateur_ajout': admin
                }
            )
            etats_created.append(etat)
            self.log_item('créé' if created else 'mis à jour', f'ÉtatActuel: {etat.libelle[:50]}')

            ne, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Pas de nouvelle station de Renouée du Japon',
                defaults={
                    'description': 'Aucune nouvelle station de Renouée du Japon '
                                   'ne doit apparaître sur le bassin versant du lac.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne.libelle[:50]}')

            ne2, created = NiveauExigence.objects.update_or_create(
                id_olt=olt,
                libelle='Réduction de 50% des surfaces colonisées par la Renouée',
                defaults={
                    'description': 'Réduire de moitié les surfaces colonisées par '
                                   'la Renouée du Japon grâce aux campagnes annuelles '
                                   'd\'arrachage.',
                    'id_utilisateur_ajout': admin
                }
            )
            nes_created.append(ne2)
            self.log_item('créé' if created else 'mis à jour', f'NE: {ne2.libelle[:50]}')

        # =====================================================================
        # Objectifs Opérationnels (OO) et Résultats Attendus (RA)
        # =====================================================================
        oos_created = []
        ras_created = []

        # Camargue - Habitats humides : OO liés aux facteurs d'influence
        if enjeu_hab_humides:
            facteur_urbain = next((f for f in facteurs_created if 'urbanisation' in f.libelle.lower() or 'urbain' in f.libelle.lower()), None)
            facteur_hydro = next((f for f in facteurs_created if 'hydrologique' in f.libelle.lower() or 'hydraulique' in f.libelle.lower()), None)

            oo, created = ObjectifOperationnel.objects.update_or_create(
                id_enjeu=enjeu_hab_humides,
                libelle='Réduire la pression urbaine sur les zones humides',
                defaults={
                    'description': 'Mettre en place des mesures de protection et de gestion '
                                   'pour limiter l\'impact de l\'urbanisation sur les habitats humides.',
                    'id_facteur_influence': facteur_urbain,
                    'id_utilisateur_ajout': admin
                }
            )
            oos_created.append(oo)
            self.log_item('créé' if created else 'mis à jour', f'OO: {oo.libelle[:50]}')

            ra, created = ResultatAttendu.objects.update_or_create(
                id_oo=oo,
                libelle='Zéro nouvelle emprise urbaine dans le périmètre de protection',
                defaults={
                    'description': 'Aucune nouvelle construction ou emprise urbaine ne doit être autorisée '
                                   'dans le périmètre de protection rapprochée de la réserve.',
                    'id_utilisateur_ajout': admin
                }
            )
            ras_created.append(ra)
            self.log_item('créé' if created else 'mis à jour', f'RA: {ra.libelle[:50]}')

            ra2, created = ResultatAttendu.objects.update_or_create(
                id_oo=oo,
                libelle='Réduction de 30% des rejets polluants',
                defaults={
                    'description': 'Réduire de 30% les rejets polluants d\'origine urbaine '
                                   'dans les cours d\'eau alimentant la réserve.',
                    'id_utilisateur_ajout': admin
                }
            )
            ras_created.append(ra2)
            self.log_item('créé' if created else 'mis à jour', f'RA: {ra2.libelle[:50]}')

            oo2, created = ObjectifOperationnel.objects.update_or_create(
                id_enjeu=enjeu_hab_humides,
                libelle='Restaurer le régime hydrologique naturel',
                defaults={
                    'description': 'Agir sur les ouvrages hydrauliques pour restaurer un régime '
                                   'hydrologique compatible avec le maintien des habitats humides.',
                    'id_facteur_influence': facteur_hydro,
                    'id_utilisateur_ajout': admin
                }
            )
            oos_created.append(oo2)
            self.log_item('créé' if created else 'mis à jour', f'OO: {oo2.libelle[:50]}')

            ra3, created = ResultatAttendu.objects.update_or_create(
                id_oo=oo2,
                libelle='Débit écologique respecté sur 3 ouvrages principaux',
                defaults={
                    'description': 'Les 3 ouvrages hydrauliques principaux respectent '
                                   'le débit écologique minimal 90% du temps.',
                    'id_utilisateur_ajout': admin
                }
            )
            ras_created.append(ra3)
            self.log_item('créé' if created else 'mis à jour', f'RA: {ra3.libelle[:50]}')

        # Lac de Remoray - Tourbières : OO
        enjeu_tourbieres = next((e for e in enjeux_created if 'tourbières' in e.libelle.lower()), None)
        facteur_assechement = next((f for f in facteurs_created if 'assèchement' in f.libelle.lower()), None)
        if enjeu_tourbieres:
            oo_tourb, created = ObjectifOperationnel.objects.update_or_create(
                id_enjeu=enjeu_tourbieres,
                libelle='Maintenir le niveau piézométrique des tourbières',
                defaults={
                    'description': 'Surveiller et maintenir le niveau piézométrique '
                                   'compatible avec le fonctionnement des tourbières.',
                    'id_facteur_influence': facteur_assechement,
                    'id_utilisateur_ajout': admin
                }
            )
            oos_created.append(oo_tourb)
            self.log_item('créé' if created else 'mis à jour', f'OO: {oo_tourb.libelle[:50]}')

            ra_piezo, created = ResultatAttendu.objects.update_or_create(
                id_oo=oo_tourb,
                libelle='Niveau piézométrique stable à ±10 cm sur 5 ans',
                defaults={
                    'description': 'Le niveau piézométrique des tourbières reste stable '
                                   'avec une variation maximale de ±10 cm sur 5 années consécutives.',
                    'id_utilisateur_ajout': admin
                }
            )
            ras_created.append(ra_piezo)
            self.log_item('créé' if created else 'mis à jour', f'RA: {ra_piezo.libelle[:50]}')

            ra_drains, created = ResultatAttendu.objects.update_or_create(
                id_oo=oo_tourb,
                libelle='80% des drains historiques neutralisés',
                defaults={
                    'description': 'Bouchage ou mise hors service d\'au moins 80% des fossés '
                                   'de drainage historiques identifiés sur les 8 tourbières.',
                    'id_utilisateur_ajout': admin
                }
            )
            ras_created.append(ra_drains)
            self.log_item('créé' if created else 'mis à jour', f'RA: {ra_drains.libelle[:50]}')

            # OO 2 : Restauration végétation turficole
            oo_veg, created = ObjectifOperationnel.objects.update_or_create(
                id_enjeu=enjeu_tourbieres,
                libelle='Restaurer les communautés végétales turficoles',
                defaults={
                    'description': 'Favoriser la recolonisation par les sphaignes et espèces '
                                   'caractéristiques des tourbières actives (droséras, linaigrettes).',
                    'id_utilisateur_ajout': admin
                }
            )
            oos_created.append(oo_veg)
            self.log_item('créé' if created else 'mis à jour', f'OO: {oo_veg.libelle[:50]}')

            ra_sphaignes, created = ResultatAttendu.objects.update_or_create(
                id_oo=oo_veg,
                libelle='Recouvrement des sphaignes > 30% sur 5 tourbières',
                defaults={
                    'description': 'Augmenter le recouvrement des sphaignes à plus de 30% '
                                   'sur au moins 5 des 8 tourbières inventoriées.',
                    'id_utilisateur_ajout': admin
                }
            )
            ras_created.append(ra_sphaignes)
            self.log_item('créé' if created else 'mis à jour', f'RA: {ra_sphaignes.libelle[:50]}')

        # Lac de Remoray - Qualité des eaux : OO
        enjeu_qualite = next((e for e in enjeux_created if 'qualité des eaux' in e.libelle), None)
        facteur_agricole = next((f for f in facteurs_created if 'agricoles du bassin' in f.libelle.lower()), None)
        if enjeu_qualite:
            oo_qualite, created = ObjectifOperationnel.objects.update_or_create(
                id_enjeu=enjeu_qualite,
                libelle='Réduire les apports en nutriments d\'origine agricole',
                defaults={
                    'description': 'Réduire de 30% les flux de phosphore et d\'azote '
                                   'entrant dans le lac depuis le bassin versant agricole.',
                    'id_facteur_influence': facteur_agricole,
                    'id_utilisateur_ajout': admin
                }
            )
            oos_created.append(oo_qualite)
            self.log_item('créé' if created else 'mis à jour', f'OO: {oo_qualite.libelle[:50]}')

            ra_phosphore, created = ResultatAttendu.objects.update_or_create(
                id_oo=oo_qualite,
                libelle='Flux de phosphore < 80 kg P/an d\'ici 2028',
                defaults={
                    'description': 'Réduction du flux annuel de phosphore entrant dans le lac '
                                   'en dessous de 80 kg P/an (contre 125 kg actuellement).',
                    'id_utilisateur_ajout': admin
                }
            )
            ras_created.append(ra_phosphore)
            self.log_item('créé' if created else 'mis à jour', f'RA: {ra_phosphore.libelle[:50]}')

            ra_conventions, created = ResultatAttendu.objects.update_or_create(
                id_oo=oo_qualite,
                libelle='100% des exploitations riveraines sous convention',
                defaults={
                    'description': '12 exploitations agricoles du bassin versant signent '
                                   'une convention de bonnes pratiques (limitation intrants, bandes enherbées).',
                    'id_utilisateur_ajout': admin
                }
            )
            ras_created.append(ra_conventions)
            self.log_item('créé' if created else 'mis à jour', f'RA: {ra_conventions.libelle[:50]}')

        # Lac de Remoray - EEE : OO
        enjeu_eee = next((e for e in enjeux_created if 'exotiques envahissantes' in e.libelle.lower()), None)
        if enjeu_eee:
            oo_eee, created = ObjectifOperationnel.objects.update_or_create(
                id_enjeu=enjeu_eee,
                libelle='Contenir l\'expansion de la Renouée du Japon',
                defaults={
                    'description': 'Empêcher la progression des 3 stations connues de Renouée '
                                   'du Japon et réduire leur surface de 50% d\'ici 2030.',
                    'id_utilisateur_ajout': admin
                }
            )
            oos_created.append(oo_eee)
            self.log_item('créé' if created else 'mis à jour', f'OO: {oo_eee.libelle[:50]}')

            ra_renouee, created = ResultatAttendu.objects.update_or_create(
                id_oo=oo_eee,
                libelle='Surface des stations de Renouée réduite de 50%',
                defaults={
                    'description': 'La surface cumulée des 3 stations de Renouée du Japon '
                                   'passe de 450 m² à moins de 225 m² d\'ici 2030.',
                    'id_utilisateur_ajout': admin
                }
            )
            ras_created.append(ra_renouee)
            self.log_item('créé' if created else 'mis à jour', f'RA: {ra_renouee.libelle[:50]}')

        self.log_summary(len(oos_created), 'objectifs opérationnels')
        self.log_summary(len(ras_created), 'résultats attendus')

        # =====================================================================
        # Indicateurs, Métriques et Mesures
        # =====================================================================
        indicateurs_created = []
        metriques_created = []
        mesures_created = []

        # Récupérer nomenclatures indicateurs/métriques
        type_ind_etat = self._get_nomenclature('TYPE_INDICATEUR', 'ETAT')
        type_ind_pression = self._get_nomenclature('TYPE_INDICATEUR', 'PRESSION')
        type_ind_reponse = self._get_nomenclature('TYPE_INDICATEUR', 'REPONSE')
        type_met_numerique = self._get_nomenclature('TYPE_METRIQUE', 'NUMERIQUE')
        type_met_qualitatif = self._get_nomenclature('TYPE_METRIQUE', 'QUALITATIF')
        type_met_booleen = self._get_nomenclature('TYPE_METRIQUE', 'BOOLEEN')

        from datetime import date

        # --- Camargue - NE "Surface en bon état de conservation ≥ 70%" ---
        ne_surface = next((ne for ne in nes_created if 'Surface en bon état' in ne.libelle), None)
        if ne_surface and type_ind_etat:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_surface,
                nom_indicateur='Surface des habitats humides en bon état de conservation',
                defaults={
                    'type_indicateur': type_ind_etat,
                    'est_standardise': True,
                    'description': 'Pourcentage de la surface totale des habitats humides '
                                   'en bon ou très bon état de conservation.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            # Taxon lié à l'indicateur
            CorIndicateurHabitat.objects.get_or_create(
                id_indicateur=ind, cd_hab='1150',
                defaults={'lb_hab_fr': 'Lagunes côtières'}
            )

            # Métrique 1 : numérique avec seuils
            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Pourcentage de surface en bon état',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': '%',
                    'ponderation': 1.0,
                    'etat_reference': 'Référence : 85% en 2015',
                    'score_1_inf': 0, 'score_1_sup': 20,
                    'score_1_label': 'Très dégradé',
                    'score_2_inf': 20, 'score_2_sup': 40,
                    'score_2_label': 'Dégradé',
                    'score_3_inf': 40, 'score_3_sup': 60,
                    'score_3_label': 'Moyen',
                    'score_4_inf': 60, 'score_4_sup': 80,
                    'score_4_label': 'Bon',
                    'score_5_inf': 80, 'score_5_sup': 100,
                    'score_5_label': 'Très bon',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            # Mesures
            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2022, 6, 15),
                defaults={'valeur': '62', 'commentaire': 'Campagne terrain juin 2022', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)
            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 6, 20),
                defaults={'valeur': '65', 'commentaire': 'Amélioration après restauration du marais sud', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

            # Métrique 2 : qualitative
            met2, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='État de la végétation halophile',
                defaults={
                    'type_metrique': type_met_qualitatif,
                    'score_1_label': 'Absente',
                    'score_2_label': 'Résiduelle',
                    'score_3_label': 'Partielle',
                    'score_4_label': 'Bien développée',
                    'score_5_label': 'Optimale',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met2)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met2, date_mesure=date(2023, 7, 10),
                defaults={'valeur': 'Bien développée', 'commentaire': 'Relevé phytosociologique', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Camargue - NE "Succès de reproduction ≥ 0.5" (flamant) ---
        ne_flamant = next((ne for ne in nes_created if 'reproduction' in ne.libelle and 'jeune' in ne.libelle), None)
        if ne_flamant and type_ind_etat:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_flamant,
                nom_indicateur='Succès de reproduction du Flamant rose',
                defaults={
                    'type_indicateur': type_ind_etat,
                    'est_standardise': True,
                    'description': 'Nombre moyen de jeunes à l\'envol par couple reproducteur.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            CorIndicateurTaxon.objects.get_or_create(
                id_indicateur=ind, cd_nom=2517,
                defaults={'nom_complet': 'Phoenicopterus roseus', 'nom_vern': 'Flamant rose'}
            )

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Ratio jeunes/couples reproducteurs',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'jeune/couple',
                    'ponderation': 1.0,
                    'score_1_inf': 0, 'score_1_sup': 0.1,
                    'score_1_label': 'Échec total',
                    'score_2_inf': 0.1, 'score_2_sup': 0.3,
                    'score_2_label': 'Très faible',
                    'score_3_inf': 0.3, 'score_3_sup': 0.5,
                    'score_3_label': 'Insuffisant',
                    'score_4_inf': 0.5, 'score_4_sup': 0.7,
                    'score_4_label': 'Satisfaisant',
                    'score_5_inf': 0.7, 'score_5_sup': 1.0,
                    'score_5_label': 'Excellent',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2022, 9, 1),
                defaults={'valeur': '0.55', 'commentaire': 'Saison 2022 - bonne année', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)
            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 9, 1),
                defaults={'valeur': '0.42', 'commentaire': 'Saison 2023 - perturbations juin', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Camargue - NE "Débit écologique" : indicateur pression ---
        ne_debit = next((ne for ne in nes_created if 'Débit écologique' in ne.libelle), None)
        if ne_debit and type_ind_pression:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_debit,
                nom_indicateur='Pression des prélèvements d\'eau sur le débit écologique',
                defaults={
                    'type_indicateur': type_ind_pression,
                    'est_standardise': False,
                    'description': 'Suivi de l\'impact des pompages agricoles sur le respect du débit minimum.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Nombre de jours sous le débit minimum',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'jours/an',
                    'score_1_inf': 60, 'score_1_sup': 365,
                    'score_1_label': 'Critique',
                    'score_2_inf': 40, 'score_2_sup': 60,
                    'score_2_label': 'Mauvais',
                    'score_3_inf': 20, 'score_3_sup': 40,
                    'score_3_label': 'Moyen',
                    'score_4_inf': 5, 'score_4_sup': 20,
                    'score_4_label': 'Bon',
                    'score_5_inf': 0, 'score_5_sup': 5,
                    'score_5_label': 'Très bon',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 12, 31),
                defaults={'valeur': '28', 'commentaire': 'Bilan annuel 2023', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Aiguilles Rouges - NE "Pas de disparition de station" ---
        ne_stations = next((ne for ne in nes_created if 'disparition de station' in ne.libelle), None)
        if ne_stations and type_ind_etat:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_stations,
                nom_indicateur='Nombre de stations d\'espèces arctico-alpines',
                defaults={
                    'type_indicateur': type_ind_etat,
                    'est_standardise': False,
                    'description': 'Suivi du nombre de stations connues d\'espèces arctico-alpines '
                                   'sur les placettes permanentes.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Nombre de stations actives',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'stations',
                    'etat_reference': 'Référence : 24 stations en 2015',
                    'score_1_inf': 0, 'score_1_sup': 10,
                    'score_2_inf': 10, 'score_2_sup': 16,
                    'score_3_inf': 16, 'score_3_sup': 20,
                    'score_4_inf': 20, 'score_4_sup': 24,
                    'score_5_inf': 24, 'score_5_sup': 50,
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 8, 15),
                defaults={'valeur': '22', 'commentaire': 'Inventaire été 2023 - 2 stations non retrouvées', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Aiguilles Rouges - NE "Tendance démographique tétras" : indicateur réponse ---
        ne_tetras = next((ne for ne in nes_created if 'démographique' in ne.libelle.lower()), None)
        if ne_tetras and type_ind_reponse:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_tetras,
                nom_indicateur='Efficacité des zones de quiétude hivernale',
                defaults={
                    'type_indicateur': type_ind_reponse,
                    'est_standardise': False,
                    'description': 'Évaluation de l\'efficacité des zones de protection '
                                   'mises en place pour limiter le dérangement hivernal.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            CorIndicateurTaxon.objects.get_or_create(
                id_indicateur=ind, cd_nom=2923,
                defaults={'nom_complet': 'Lyrurus tetrix', 'nom_vern': 'Tétras lyre'}
            )

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Respect des zones de quiétude',
                defaults={
                    'type_metrique': type_met_booleen,
                    'score_1_label': 'Non respecté',
                    'score_2_label': 'Peu respecté',
                    'score_3_label': 'Partiellement respecté',
                    'score_4_label': 'Bien respecté',
                    'score_5_label': 'Totalement respecté',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2024, 3, 15),
                defaults={'valeur': 'Bien respecté', 'commentaire': 'Hiver 2023-2024 - bonne compliance', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # =====================================================================
        # Indicateurs Lac de Remoray
        # =====================================================================

        # --- Remoray - NE "Concentration en phosphore total < 20 µg/L" ---
        ne_phosphore = next((ne for ne in nes_created if 'phosphore' in ne.libelle.lower()), None)
        if ne_phosphore and type_ind_etat:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_phosphore,
                nom_indicateur='Concentration en phosphore total dans le lac',
                defaults={
                    'type_indicateur': type_ind_etat,
                    'est_standardise': True,
                    'description': 'Suivi de la concentration en phosphore total '
                                   'dans la colonne d\'eau du lac de Remoray. '
                                   'Indicateur clé de l\'état trophique.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Phosphore total moyen annuel',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'µg/L',
                    'ponderation': 1.0,
                    'etat_reference': 'Référence DCE : seuil bon état = 20 µg/L',
                    'score_1_inf': 50, 'score_1_sup': 200,
                    'score_1_label': 'Hypereutrophe',
                    'score_2_inf': 35, 'score_2_sup': 50,
                    'score_2_label': 'Eutrophe',
                    'score_3_inf': 20, 'score_3_sup': 35,
                    'score_3_label': 'Mésotrophe',
                    'score_4_inf': 10, 'score_4_sup': 20,
                    'score_4_label': 'Oligo-mésotrophe',
                    'score_5_inf': 0, 'score_5_sup': 10,
                    'score_5_label': 'Oligotrophe',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2022, 12, 31),
                defaults={'valeur': '18.5', 'commentaire': 'Moyenne annuelle 2022 - 6 prélèvements', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)
            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 12, 31),
                defaults={'valeur': '21.2', 'commentaire': 'Moyenne annuelle 2023 - dépassement du seuil', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

            # Indicateur pression sur le phosphore
            ind_p, created = Indicateur.objects.update_or_create(
                id_ne=ne_phosphore,
                nom_indicateur='Apports en nutriments du bassin versant',
                defaults={
                    'type_indicateur': type_ind_pression,
                    'est_standardise': False,
                    'description': 'Suivi des flux de nutriments (azote, phosphore) '
                                   'provenant des activités agricoles du bassin versant.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind_p)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind_p.nom_indicateur[:50]}')

            met_p, created = Metrique.objects.update_or_create(
                id_indicateur=ind_p,
                nom_metrique='Flux annuel de phosphore entrant',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'kg P/an',
                    'score_1_inf': 200, 'score_1_sup': 1000,
                    'score_1_label': 'Critique',
                    'score_2_inf': 150, 'score_2_sup': 200,
                    'score_2_label': 'Fort',
                    'score_3_inf': 100, 'score_3_sup': 150,
                    'score_3_label': 'Modéré',
                    'score_4_inf': 50, 'score_4_sup': 100,
                    'score_4_label': 'Faible',
                    'score_5_inf': 0, 'score_5_sup': 50,
                    'score_5_label': 'Très faible',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met_p)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met_p, date_mesure=date(2023, 12, 31),
                defaults={'valeur': '125', 'commentaire': 'Bilan annuel 2023 - affluents + ruissellement', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray - NE "Niveau piézométrique ≤ 20 cm" (Tourbières) ---
        ne_piezo = next((ne for ne in nes_created if 'piézométrique' in ne.libelle.lower()), None)
        if ne_piezo and type_ind_etat:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_piezo,
                nom_indicateur='Niveau piézométrique des tourbières',
                defaults={
                    'type_indicateur': type_ind_etat,
                    'est_standardise': True,
                    'description': 'Suivi du niveau de la nappe dans les tourbières '
                                   'via le réseau de 15 piézomètres.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            CorIndicateurHabitat.objects.get_or_create(
                id_indicateur=ind, cd_hab='7110',
                defaults={'lb_hab_fr': 'Tourbières hautes actives'}
            )

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Profondeur moyenne de la nappe en saison de végétation',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'cm',
                    'ponderation': 1.0,
                    'etat_reference': 'Référence : nappe affleurante en tourbière active',
                    'score_1_inf': 50, 'score_1_sup': 200,
                    'score_1_label': 'Très asséché',
                    'score_2_inf': 30, 'score_2_sup': 50,
                    'score_2_label': 'Asséché',
                    'score_3_inf': 20, 'score_3_sup': 30,
                    'score_3_label': 'Moyennement humide',
                    'score_4_inf': 10, 'score_4_sup': 20,
                    'score_4_label': 'Humide',
                    'score_5_inf': 0, 'score_5_sup': 10,
                    'score_5_label': 'Très humide',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2022, 9, 30),
                defaults={'valeur': '18', 'commentaire': 'Moyenne sept. 2022 - fin saison végétation', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)
            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 9, 30),
                defaults={'valeur': '24', 'commentaire': 'Moyenne sept. 2023 - été sec, dégradation', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

            # Indicateur état qualitatif - végétation turficole
            ind_veg, created = Indicateur.objects.update_or_create(
                id_ne=ne_piezo,
                nom_indicateur='État de la végétation turficole',
                defaults={
                    'type_indicateur': type_ind_etat,
                    'est_standardise': False,
                    'description': 'Évaluation qualitative de l\'état des communautés '
                                   'végétales caractéristiques des tourbières.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind_veg)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind_veg.nom_indicateur[:50]}')

            met_veg, created = Metrique.objects.update_or_create(
                id_indicateur=ind_veg,
                nom_metrique='Recouvrement des sphaignes',
                defaults={
                    'type_metrique': type_met_qualitatif,
                    'unite': '%',
                    'score_1_label': 'Absent (0%)',
                    'score_2_label': 'Résiduel (<10%)',
                    'score_3_label': 'Partiel (10-30%)',
                    'score_4_label': 'Bien développé (30-60%)',
                    'score_5_label': 'Dominant (>60%)',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met_veg)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met_veg, date_mesure=date(2023, 7, 15),
                defaults={'valeur': 'Partiel (10-30%)', 'commentaire': 'Relevé phytosociologique été 2023', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray - NE "Présence régulière ≥ 3 individus" (Balbuzard) ---
        ne_balbuzard = next((ne for ne in nes_created if 'balbuzard' in ne.libelle.lower() or '3 individus' in ne.libelle), None)
        if ne_balbuzard and type_ind_etat:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_balbuzard,
                nom_indicateur='Fréquentation du lac par le Balbuzard pêcheur',
                defaults={
                    'type_indicateur': type_ind_etat,
                    'est_standardise': False,
                    'description': 'Suivi du nombre de balbuzards pêcheurs observés '
                                   'en halte migratoire sur le lac de Remoray.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            CorIndicateurTaxon.objects.get_or_create(
                id_indicateur=ind, cd_nom=2840,
                defaults={'nom_complet': 'Pandion haliaetus', 'nom_vern': 'Balbuzard pêcheur'}
            )

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Nombre maximum d\'individus simultanés en halte',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'individus',
                    'score_1_inf': 0, 'score_1_sup': 1,
                    'score_1_label': 'Absent ou exceptionnel',
                    'score_2_inf': 1, 'score_2_sup': 2,
                    'score_2_label': 'Occasionnel',
                    'score_3_inf': 2, 'score_3_sup': 3,
                    'score_3_label': 'Régulier faible',
                    'score_4_inf': 3, 'score_4_sup': 5,
                    'score_4_label': 'Régulier',
                    'score_5_inf': 5, 'score_5_sup': 20,
                    'score_5_label': 'Site majeur',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 4, 15),
                defaults={'valeur': '3', 'commentaire': 'Migration prénuptiale 2023 - 3 ind. simultanés', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)
            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 9, 20),
                defaults={'valeur': '5', 'commentaire': 'Migration postnuptiale 2023 - pic de 5 ind.', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray - NE "Durée moyenne de halte ≥ 5 jours" (Balbuzard) ---
        ne_duree_halte = next((ne for ne in nes_created if 'halte' in ne.libelle.lower() and 'jours' in ne.libelle.lower()), None)
        if ne_duree_halte and type_ind_reponse:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_duree_halte,
                nom_indicateur='Qualité d\'accueil du site pour le Balbuzard',
                defaults={
                    'type_indicateur': type_ind_reponse,
                    'est_standardise': False,
                    'description': 'Évaluation de la qualité du site d\'accueil '
                                   'par la durée de séjour des balbuzards.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Durée moyenne de séjour',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'jours',
                    'score_1_inf': 0, 'score_1_sup': 1,
                    'score_1_label': 'Transit',
                    'score_2_inf': 1, 'score_2_sup': 3,
                    'score_2_label': 'Halte courte',
                    'score_3_inf': 3, 'score_3_sup': 5,
                    'score_3_label': 'Halte moyenne',
                    'score_4_inf': 5, 'score_4_sup': 10,
                    'score_4_label': 'Halte prolongée',
                    'score_5_inf': 10, 'score_5_sup': 60,
                    'score_5_label': 'Stationnement long',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 10, 15),
                defaults={'valeur': '6.5', 'commentaire': 'Automne 2023 - moyenne sur 4 ind. suivis', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray - NE "Surface en fauche tardive ≥ 30 ha" (Prairies) ---
        ne_fauche = next((ne for ne in nes_created if 'fauche tardive' in ne.libelle.lower()), None)
        if ne_fauche and type_ind_etat:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_fauche,
                nom_indicateur='Surface de prairies en gestion extensive',
                defaults={
                    'type_indicateur': type_ind_etat,
                    'est_standardise': False,
                    'description': 'Suivi des surfaces de prairies de fauche '
                                   'gérées en fauche tardive (après le 15 juillet) '
                                   'dans le cadre des conventions agricoles.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            CorIndicateurHabitat.objects.get_or_create(
                id_indicateur=ind, cd_hab='6520',
                defaults={'lb_hab_fr': 'Prairies de fauche de montagne'}
            )

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Surface totale en fauche tardive',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'ha',
                    'ponderation': 1.0,
                    'etat_reference': 'Référence : 40 ha historiquement gérés en fauche tardive',
                    'score_1_inf': 0, 'score_1_sup': 10,
                    'score_1_label': 'Critique',
                    'score_2_inf': 10, 'score_2_sup': 20,
                    'score_2_label': 'Insuffisant',
                    'score_3_inf': 20, 'score_3_sup': 30,
                    'score_3_label': 'Moyen',
                    'score_4_inf': 30, 'score_4_sup': 40,
                    'score_4_label': 'Bon',
                    'score_5_inf': 40, 'score_5_sup': 60,
                    'score_5_label': 'Très bon',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2022, 10, 1),
                defaults={'valeur': '33', 'commentaire': 'Bilan 2022 - 5 conventions actives', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)
            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 10, 1),
                defaults={'valeur': '35', 'commentaire': 'Bilan 2023 - renouvellement convention Morel', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray - NE "Richesse floristique ≥ 25 espèces/relevé" (Prairies) ---
        ne_flore = next((ne for ne in nes_created if 'richesse floristique' in ne.libelle.lower()), None)
        if ne_flore and type_ind_etat:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_flore,
                nom_indicateur='Diversité floristique des prairies de fauche',
                defaults={
                    'type_indicateur': type_ind_etat,
                    'est_standardise': True,
                    'description': 'Suivi de la richesse spécifique des prairies '
                                   'via des relevés phytosociologiques standardisés '
                                   'sur 10 placettes permanentes.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Nombre moyen d\'espèces par relevé',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'espèces/relevé',
                    'etat_reference': 'Référence : 32 espèces/relevé en 2010',
                    'score_1_inf': 0, 'score_1_sup': 10,
                    'score_1_label': 'Très pauvre',
                    'score_2_inf': 10, 'score_2_sup': 18,
                    'score_2_label': 'Pauvre',
                    'score_3_inf': 18, 'score_3_sup': 25,
                    'score_3_label': 'Moyen',
                    'score_4_inf': 25, 'score_4_sup': 35,
                    'score_4_label': 'Riche',
                    'score_5_inf': 35, 'score_5_sup': 60,
                    'score_5_label': 'Très riche',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 7, 20),
                defaults={'valeur': '28', 'commentaire': 'Relevés juillet 2023 - moyenne 10 placettes', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray - NE "Pas de nouvelle station de Renouée" (EEE) ---
        ne_renouee = next((ne for ne in nes_created if 'nouvelle station' in ne.libelle.lower() and 'renouée' in ne.libelle.lower()), None)
        if ne_renouee and type_ind_pression:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_renouee,
                nom_indicateur='Expansion de la Renouée du Japon',
                defaults={
                    'type_indicateur': type_ind_pression,
                    'est_standardise': False,
                    'description': 'Suivi de l\'extension des stations de Renouée du Japon '
                                   'le long du Drugeon et de ses affluents.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            CorIndicateurTaxon.objects.get_or_create(
                id_indicateur=ind, cd_nom=117835,
                defaults={'nom_complet': 'Reynoutria japonica', 'nom_vern': 'Renouée du Japon'}
            )

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Nombre de stations actives de Renouée',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'stations',
                    'etat_reference': 'Référence : 3 stations en 2020',
                    'score_1_inf': 6, 'score_1_sup': 20,
                    'score_1_label': 'Expansion forte',
                    'score_2_inf': 4, 'score_2_sup': 6,
                    'score_2_label': 'Expansion',
                    'score_3_inf': 3, 'score_3_sup': 4,
                    'score_3_label': 'Stable',
                    'score_4_inf': 1, 'score_4_sup': 3,
                    'score_4_label': 'En régression',
                    'score_5_inf': 0, 'score_5_sup': 1,
                    'score_5_label': 'Quasi éradiqué',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2022, 9, 1),
                defaults={'valeur': '3', 'commentaire': 'Cartographie 2022 - stations stables', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)
            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 9, 1),
                defaults={'valeur': '3', 'commentaire': 'Cartographie 2023 - pas de nouvelle station', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray - NE "Réduction 50% surfaces colonisées" (EEE) ---
        ne_reduction_eee = next((ne for ne in nes_created if 'réduction' in ne.libelle.lower() and 'renouée' in ne.libelle.lower()), None)
        if ne_reduction_eee and type_ind_reponse:
            ind, created = Indicateur.objects.update_or_create(
                id_ne=ne_reduction_eee,
                nom_indicateur='Efficacité des campagnes d\'arrachage de la Renouée',
                defaults={
                    'type_indicateur': type_ind_reponse,
                    'est_standardise': False,
                    'description': 'Évaluation de l\'efficacité des campagnes annuelles '
                                   'd\'arrachage de la Renouée du Japon sur le bassin.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind)
            self.log_item('créé' if created else 'mis à jour', f'Indicateur: {ind.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind,
                nom_metrique='Surface cumulée des stations de Renouée',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'm²',
                    'etat_reference': 'Référence : 450 m² en 2020 (avant campagnes)',
                    'score_1_inf': 400, 'score_1_sup': 1000,
                    'score_1_label': 'En expansion',
                    'score_2_inf': 300, 'score_2_sup': 400,
                    'score_2_label': 'Stable',
                    'score_3_inf': 225, 'score_3_sup': 300,
                    'score_3_label': 'Réduction faible',
                    'score_4_inf': 100, 'score_4_sup': 225,
                    'score_4_label': 'Réduction significative',
                    'score_5_inf': 0, 'score_5_sup': 100,
                    'score_5_label': 'Quasi éradiqué',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2022, 10, 15),
                defaults={'valeur': '380', 'commentaire': 'Post-arrachage 2022 - 3 campagnes', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)
            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 10, 15),
                defaults={'valeur': '320', 'commentaire': 'Post-arrachage 2023 - régression confirmée', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # =====================================================================
        # Indicateurs de pression liés aux Résultats Attendus (chaîne OO)
        # =====================================================================

        # --- Remoray OO Tourbières - RA "Niveau piézométrique stable" ---
        ra_piezo_obj = next((r for r in ras_created if 'piézométrique stable' in r.libelle), None)
        if ra_piezo_obj and type_ind_pression:
            ind_pression_piezo, created = Indicateur.objects.update_or_create(
                id_resultat_attendu=ra_piezo_obj,
                nom_indicateur='Variation du niveau piézométrique saisonnier',
                defaults={
                    'type_indicateur': type_ind_pression,
                    'est_standardise': True,
                    'description': 'Suivi de la variation saisonnière du niveau piézométrique '
                                   'comme indicateur de la pression d\'assèchement sur les tourbières.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind_pression_piezo)
            self.log_item('créé' if created else 'mis à jour',
                          f'Indicateur pression OO: {ind_pression_piezo.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind_pression_piezo,
                nom_metrique='Amplitude piézométrique estivale',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'cm',
                    'ponderation': 1.0,
                    'etat_reference': 'Référence : amplitude < 10 cm en tourbière fonctionnelle',
                    'score_1_inf': 40, 'score_1_sup': 100,
                    'score_1_label': 'Assèchement sévère',
                    'score_2_inf': 25, 'score_2_sup': 40,
                    'score_2_label': 'Assèchement marqué',
                    'score_3_inf': 15, 'score_3_sup': 25,
                    'score_3_label': 'Fluctuation modérée',
                    'score_4_inf': 10, 'score_4_sup': 15,
                    'score_4_label': 'Fluctuation acceptable',
                    'score_5_inf': 0, 'score_5_sup': 10,
                    'score_5_label': 'Stable',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 9, 30),
                defaults={'valeur': '22', 'commentaire': 'Amplitude mai-sept 2023 - été sec', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray OO Tourbières - RA "80% drains neutralisés" ---
        ra_drains_obj = next((r for r in ras_created if 'drains' in r.libelle.lower()), None)
        if ra_drains_obj and type_ind_pression:
            ind_pression_drains, created = Indicateur.objects.update_or_create(
                id_resultat_attendu=ra_drains_obj,
                nom_indicateur='État de fonctionnement des drains historiques',
                defaults={
                    'type_indicateur': type_ind_pression,
                    'est_standardise': False,
                    'description': 'Suivi du nombre et du débit des fossés de drainage '
                                   'encore actifs sur les 8 tourbières inventoriées.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind_pression_drains)
            self.log_item('créé' if created else 'mis à jour',
                          f'Indicateur pression OO: {ind_pression_drains.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind_pression_drains,
                nom_metrique='Pourcentage de drains encore actifs',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': '%',
                    'etat_reference': 'Référence : 14 drains identifiés en 2020, objectif < 20% actifs',
                    'score_1_inf': 80, 'score_1_sup': 100,
                    'score_1_label': 'Quasi tous actifs',
                    'score_2_inf': 50, 'score_2_sup': 80,
                    'score_2_label': 'Majorité active',
                    'score_3_inf': 30, 'score_3_sup': 50,
                    'score_3_label': 'Partiellement neutralisés',
                    'score_4_inf': 20, 'score_4_sup': 30,
                    'score_4_label': 'Bien avancé',
                    'score_5_inf': 0, 'score_5_sup': 20,
                    'score_5_label': 'Objectif atteint',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 11, 15),
                defaults={'valeur': '65', 'commentaire': 'Diagnostic 2023 - 9 drains sur 14 encore actifs', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray OO Tourbières - RA "Recouvrement sphaignes > 30%" ---
        ra_sphaignes_obj = next((r for r in ras_created if 'sphaignes' in r.libelle.lower()), None)
        if ra_sphaignes_obj and type_ind_pression:
            ind_pression_colonisation, created = Indicateur.objects.update_or_create(
                id_resultat_attendu=ra_sphaignes_obj,
                nom_indicateur='Progression de la colonisation ligneuse',
                defaults={
                    'type_indicateur': type_ind_pression,
                    'est_standardise': False,
                    'description': 'Suivi de l\'envahissement des tourbières par les ligneux '
                                   '(bouleaux, saules) en lien avec l\'assèchement.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind_pression_colonisation)
            self.log_item('créé' if created else 'mis à jour',
                          f'Indicateur pression OO: {ind_pression_colonisation.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind_pression_colonisation,
                nom_metrique='Taux de recouvrement ligneux sur les tourbières',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': '%',
                    'score_1_inf': 40, 'score_1_sup': 100,
                    'score_1_label': 'Boisement avancé',
                    'score_2_inf': 25, 'score_2_sup': 40,
                    'score_2_label': 'Colonisation forte',
                    'score_3_inf': 15, 'score_3_sup': 25,
                    'score_3_label': 'Colonisation modérée',
                    'score_4_inf': 5, 'score_4_sup': 15,
                    'score_4_label': 'Colonisation faible',
                    'score_5_inf': 0, 'score_5_sup': 5,
                    'score_5_label': 'Milieu ouvert',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 8, 15),
                defaults={'valeur': '22', 'commentaire': 'Photo-interprétation été 2023 - progression bouleaux', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray OO Qualité eaux - RA "Flux phosphore < 80 kg/an" ---
        ra_phosphore_obj = next((r for r in ras_created if 'phosphore' in r.libelle.lower() and '80 kg' in r.libelle), None)
        if ra_phosphore_obj and type_ind_pression:
            ind_pression_phosphore, created = Indicateur.objects.update_or_create(
                id_resultat_attendu=ra_phosphore_obj,
                nom_indicateur='Charge en phosphore des affluents du lac',
                defaults={
                    'type_indicateur': type_ind_pression,
                    'est_standardise': True,
                    'description': 'Mesure de la charge en phosphore total transportée '
                                   'par les 4 affluents principaux du lac de Remoray.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind_pression_phosphore)
            self.log_item('créé' if created else 'mis à jour',
                          f'Indicateur pression OO: {ind_pression_phosphore.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind_pression_phosphore,
                nom_metrique='Flux annuel de phosphore total des affluents',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'kg P/an',
                    'ponderation': 1.0,
                    'etat_reference': 'Objectif OO : < 80 kg P/an d\'ici 2028',
                    'score_1_inf': 150, 'score_1_sup': 500,
                    'score_1_label': 'Charge très élevée',
                    'score_2_inf': 100, 'score_2_sup': 150,
                    'score_2_label': 'Charge élevée',
                    'score_3_inf': 80, 'score_3_sup': 100,
                    'score_3_label': 'Charge modérée',
                    'score_4_inf': 50, 'score_4_sup': 80,
                    'score_4_label': 'Charge faible',
                    'score_5_inf': 0, 'score_5_sup': 50,
                    'score_5_label': 'Charge très faible',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 12, 31),
                defaults={'valeur': '118', 'commentaire': 'Bilan 2023 - 4 affluents cumulés, prélèvements mensuels', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray OO Qualité eaux - RA "100% exploitations sous convention" ---
        ra_conventions_obj = next((r for r in ras_created if 'exploitations' in r.libelle.lower() and 'convention' in r.libelle.lower()), None)
        if ra_conventions_obj and type_ind_pression:
            ind_pression_conventions, created = Indicateur.objects.update_or_create(
                id_resultat_attendu=ra_conventions_obj,
                nom_indicateur='Taux d\'adhésion des exploitants aux conventions',
                defaults={
                    'type_indicateur': type_ind_pression,
                    'est_standardise': False,
                    'description': 'Suivi du nombre d\'exploitations agricoles ayant signé '
                                   'une convention de bonnes pratiques sur le bassin versant.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind_pression_conventions)
            self.log_item('créé' if created else 'mis à jour',
                          f'Indicateur pression OO: {ind_pression_conventions.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind_pression_conventions,
                nom_metrique='Nombre d\'exploitations sous convention',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': 'exploitations',
                    'etat_reference': 'Objectif : 12 exploitations (100% du bassin versant)',
                    'score_1_inf': 0, 'score_1_sup': 3,
                    'score_1_label': 'Très insuffisant',
                    'score_2_inf': 3, 'score_2_sup': 6,
                    'score_2_label': 'Insuffisant',
                    'score_3_inf': 6, 'score_3_sup': 9,
                    'score_3_label': 'En progrès',
                    'score_4_inf': 9, 'score_4_sup': 12,
                    'score_4_label': 'Presque complet',
                    'score_5_inf': 12, 'score_5_sup': 15,
                    'score_5_label': 'Objectif atteint',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 12, 31),
                defaults={'valeur': '5', 'commentaire': 'Bilan 2023 - 5 conventions signées sur 12 exploitations', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # --- Remoray OO EEE - RA "Surface Renouée réduite de 50%" ---
        ra_renouee_obj = next((r for r in ras_created if 'renouée' in r.libelle.lower() and 'réduite' in r.libelle.lower()), None)
        if ra_renouee_obj and type_ind_pression:
            ind_pression_renouee, created = Indicateur.objects.update_or_create(
                id_resultat_attendu=ra_renouee_obj,
                nom_indicateur='Dynamique de recolonisation de la Renouée post-arrachage',
                defaults={
                    'type_indicateur': type_ind_pression,
                    'est_standardise': False,
                    'description': 'Suivi de la vitesse de repousse de la Renouée du Japon '
                                   'après les campagnes d\'arrachage annuelles.',
                    'id_utilisateur_ajout': admin
                }
            )
            indicateurs_created.append(ind_pression_renouee)
            self.log_item('créé' if created else 'mis à jour',
                          f'Indicateur pression OO: {ind_pression_renouee.nom_indicateur[:50]}')

            met, created = Metrique.objects.update_or_create(
                id_indicateur=ind_pression_renouee,
                nom_metrique='Taux de repousse post-arrachage à 3 mois',
                defaults={
                    'type_metrique': type_met_numerique,
                    'unite': '%',
                    'score_1_inf': 80, 'score_1_sup': 100,
                    'score_1_label': 'Repousse totale',
                    'score_2_inf': 50, 'score_2_sup': 80,
                    'score_2_label': 'Repousse forte',
                    'score_3_inf': 30, 'score_3_sup': 50,
                    'score_3_label': 'Repousse modérée',
                    'score_4_inf': 10, 'score_4_sup': 30,
                    'score_4_label': 'Repousse faible',
                    'score_5_inf': 0, 'score_5_sup': 10,
                    'score_5_label': 'Quasi nul',
                    'id_utilisateur_ajout': admin
                }
            )
            metriques_created.append(met)

            m, _ = Mesure.objects.update_or_create(
                id_metrique=met, date_mesure=date(2023, 12, 1),
                defaults={'valeur': '35', 'commentaire': '3 mois post-arrachage sept. 2023 - repousse modérée', 'id_utilisateur_ajout': admin}
            )
            mesures_created.append(m)

        # =====================================================================
        # Opérations (Actions)
        # =====================================================================
        operations_created = []

        # Récupérer nomenclatures de priorité d'opération
        prio_op_1 = self._get_nomenclature('PRIORITE_OPERATION', 'PRIORITE_1')
        prio_op_2 = self._get_nomenclature('PRIORITE_OPERATION', 'PRIORITE_2')
        prio_op_3 = self._get_nomenclature('PRIORITE_OPERATION', 'PRIORITE_3')

        # --- Opérations Camargue ---
        # Liée à l'indicateur "Surface des habitats humides en bon état de conservation"
        ind_surface = next((i for i in indicateurs_created if 'Surface des habitats humides' in i.nom_indicateur), None)
        if ind_surface and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Restauration hydraulique du marais sud',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'CAM-SE01',
                    'id_referentiel_operations': 'SE',
                    'description': 'Travaux de remise en eau du marais sud par suppression '
                                   'des endiguements et restauration des connexions hydrauliques.',
                    'annee_min': 2024,
                    'annee_max': 2026,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_surface)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op.libelle[:50]}')

            op2, created = Operation.objects.update_or_create(
                libelle='Suivi cartographique des habitats humides',
                defaults={
                    'id_priorite': prio_op_2,
                    'code_operation': 'CAM-SE02',
                    'id_referentiel_operations': 'SE',
                    'description': 'Cartographie annuelle de l\'état de conservation '
                                   'des habitats humides par télédétection et terrain.',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op2, id_indicateur=ind_surface)
            operations_created.append(op2)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op2.libelle[:50]}')

        # Liée à l'indicateur "Succès de reproduction du Flamant rose"
        ind_flamant = next((i for i in indicateurs_created if 'Flamant rose' in i.nom_indicateur), None)
        if ind_flamant and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Régulation de la fréquentation autour des colonies',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'CAM-IP01',
                    'id_referentiel_operations': 'IP',
                    'description': 'Mise en place de zones d\'exclusion temporaires '
                                   'autour des colonies de nidification en période de reproduction.',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_flamant)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op.libelle[:50]}')

        # Liée à l'indicateur "Pression des prélèvements d'eau"
        ind_debit = next((i for i in indicateurs_created if 'prélèvements d\'eau' in i.nom_indicateur), None)
        if ind_debit and prio_op_2:
            op, created = Operation.objects.update_or_create(
                libelle='Négociation de quotas de prélèvement avec les irrigants',
                defaults={
                    'id_priorite': prio_op_2,
                    'code_operation': 'CAM-GE01',
                    'id_referentiel_operations': 'GE',
                    'description': 'Animation de la concertation avec les acteurs agricoles '
                                   'pour la définition de quotas respectant le débit écologique.',
                    'annee_min': 2024,
                    'annee_max': 2028,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_debit)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op.libelle[:50]}')

        # --- Opérations Aiguilles Rouges ---
        # Liée à l'indicateur "Nombre de stations d'espèces arctico-alpines"
        ind_stations = next((i for i in indicateurs_created if 'stations d\'espèces arctico-alpines' in i.nom_indicateur), None)
        if ind_stations and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Inventaire annuel des placettes permanentes',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'AR-CS01',
                    'id_referentiel_operations': 'CS',
                    'description': 'Suivi annuel des 24 placettes permanentes pour le comptage '
                                   'des stations d\'espèces arctico-alpines.',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_stations)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op.libelle[:50]}')

        # Liée à l'indicateur "Efficacité des zones de quiétude hivernale"
        ind_quietude = next((i for i in indicateurs_created if 'zones de quiétude' in i.nom_indicateur), None)
        if ind_quietude and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Mise en défens hivernale des zones de quiétude',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'AR-PR01',
                    'id_referentiel_operations': 'PR',
                    'description': 'Balisage et surveillance des zones de quiétude '
                                   'pour le tétras-lyre en période hivernale (nov-avr).',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_quietude)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op.libelle[:50]}')

            op2, created = Operation.objects.update_or_create(
                libelle='Sensibilisation des pratiquants de sports d\'hiver',
                defaults={
                    'id_priorite': prio_op_2,
                    'code_operation': 'AR-CC01',
                    'id_referentiel_operations': 'CC',
                    'description': 'Campagnes de communication et panneaux d\'information '
                                   'auprès des randonneurs et skieurs de randonnée.',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op2, id_indicateur=ind_quietude)
            operations_created.append(op2)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op2.libelle[:50]}')

        # --- Opérations Lac de Remoray ---
        # Liée à l'indicateur "Concentration en phosphore total"
        ind_phosphore = next((i for i in indicateurs_created if 'phosphore total' in i.nom_indicateur), None)
        if ind_phosphore and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Prélèvements mensuels qualité eau lac',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'REM-CS01',
                    'id_referentiel_operations': 'CS',
                    'description': 'Campagnes de prélèvements mensuels sur 3 points '
                                   'du lac pour le suivi de la qualité physico-chimique.',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_phosphore)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op.libelle[:50]}')

        # Liée à l'indicateur "Apports en nutriments du bassin versant"
        ind_nutriments = next((i for i in indicateurs_created if 'nutriments' in i.nom_indicateur), None)
        if ind_nutriments and prio_op_2:
            op, created = Operation.objects.update_or_create(
                libelle='Diagnostic des pratiques agricoles du bassin versant',
                defaults={
                    'id_priorite': prio_op_2,
                    'code_operation': 'REM-GE01',
                    'id_referentiel_operations': 'GE',
                    'description': 'Enquête et accompagnement des exploitants agricoles '
                                   'pour la réduction des intrants sur le bassin versant.',
                    'annee_min': 2024,
                    'annee_max': 2027,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_nutriments)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op.libelle[:50]}')

        # Liée à l'indicateur "Surface de prairies en gestion extensive"
        ind_prairies = next((i for i in indicateurs_created if 'prairies en gestion extensive' in i.nom_indicateur), None)
        if ind_prairies and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Renouvellement des conventions de fauche tardive',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'REM-GE02',
                    'id_referentiel_operations': 'GE',
                    'description': 'Négociation et renouvellement des conventions '
                                   'avec les agriculteurs pour la fauche tardive (après le 15 juillet).',
                    'annee_min': 2024,
                    'annee_max': 2028,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_prairies)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op.libelle[:50]}')

        # Liée à l'indicateur "Expansion de la Renouée du Japon"
        ind_renouee = next((i for i in indicateurs_created if 'Renouée du Japon' in i.nom_indicateur and 'Expansion' in i.nom_indicateur), None)
        if ind_renouee and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Campagnes d\'arrachage de la Renouée du Japon',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'REM-SE01',
                    'id_referentiel_operations': 'SE',
                    'description': 'Trois campagnes annuelles d\'arrachage mécanique '
                                   'et de suivi des repousses sur les 3 stations connues.',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_renouee)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op.libelle[:50]}')

        # Opération multi-indicateurs : liée à la fois au phosphore et aux nutriments
        if ind_phosphore and ind_nutriments and prio_op_3:
            op, created = Operation.objects.update_or_create(
                libelle='Étude globale du fonctionnement hydrologique du bassin',
                defaults={
                    'id_priorite': prio_op_3,
                    'code_operation': 'REM-CS02',
                    'id_referentiel_operations': 'CS',
                    'description': 'Étude hydrologique intégrée pour comprendre les flux '
                                   'de nutriments et la dynamique de la qualité des eaux.',
                    'annee_min': 2025,
                    'annee_max': 2026,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_phosphore)
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_nutriments)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération: {op.libelle[:50]}')

        # --- Opérations liées aux indicateurs de pression OO (Remoray) ---

        # OO Tourbières : bouchage des drains → lié à ind_pression_drains
        ind_pression_drains_ref = next((i for i in indicateurs_created if 'drains historiques' in i.nom_indicateur), None)
        if ind_pression_drains_ref and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Bouchage et neutralisation des drains historiques',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'REM-TU01',
                    'id_referentiel_operations': 'GE',
                    'description': 'Travaux de bouchage des fossés de drainage du XIXe siècle '
                                   'sur les tourbières du Crossat et de Frasne. '
                                   'Objectif : neutraliser 80% des 14 drains identifiés.',
                    'annee_min': 2024,
                    'annee_max': 2028,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_pression_drains_ref)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération OO: {op.libelle[:50]}')

        # OO Tourbières : suivi piézométrique → lié à ind_pression_piezo
        ind_pression_piezo_ref = next((i for i in indicateurs_created if 'piézométrique saisonnier' in i.nom_indicateur), None)
        if ind_pression_piezo_ref and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Suivi piézométrique mensuel des tourbières',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'REM-TU02',
                    'id_referentiel_operations': 'SE',
                    'description': 'Relevé mensuel des 15 piézomètres installés sur les '
                                   '8 tourbières. Analyse des tendances inter-annuelles.',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_pression_piezo_ref)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération OO: {op.libelle[:50]}')

        # OO Tourbières : débroussaillage ligneux → lié à ind_pression_colonisation
        ind_pression_col_ref = next((i for i in indicateurs_created if 'colonisation ligneuse' in i.nom_indicateur), None)
        if ind_pression_col_ref and prio_op_2:
            op, created = Operation.objects.update_or_create(
                libelle='Débroussaillage sélectif des bouleaux sur tourbières',
                defaults={
                    'id_priorite': prio_op_2,
                    'code_operation': 'REM-TU03',
                    'id_referentiel_operations': 'GE',
                    'description': 'Coupes sélectives de bouleaux et saules colonisant '
                                   'les zones de sphaignes. Export des rémanents hors tourbière.',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_pression_col_ref)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération OO: {op.libelle[:50]}')

        # OO Qualité eaux : suivi affluents → lié à ind_pression_phosphore
        ind_pression_phosphore_ref = next((i for i in indicateurs_created if 'phosphore des affluents' in i.nom_indicateur), None)
        if ind_pression_phosphore_ref and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Suivi mensuel de la charge en phosphore des affluents',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'REM-QE01',
                    'id_referentiel_operations': 'SE',
                    'description': 'Prélèvements mensuels sur les 4 affluents principaux '
                                   'du lac pour mesurer les flux de phosphore total.',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_pression_phosphore_ref)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération OO: {op.libelle[:50]}')

        # OO Qualité eaux : conventions agricoles → lié à ind_pression_conventions
        ind_pression_conv_ref = next((i for i in indicateurs_created if 'adhésion des exploitants' in i.nom_indicateur), None)
        if ind_pression_conv_ref and prio_op_2:
            op, created = Operation.objects.update_or_create(
                libelle='Animation des conventions agricoles du bassin versant',
                defaults={
                    'id_priorite': prio_op_2,
                    'code_operation': 'REM-QE02',
                    'id_referentiel_operations': 'GE',
                    'description': 'Démarchage, accompagnement et suivi des 12 exploitations '
                                   'du bassin versant pour la signature de conventions '
                                   'de bonnes pratiques (bandes enherbées, limitation intrants).',
                    'annee_min': 2024,
                    'annee_max': 2028,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_pression_conv_ref)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération OO: {op.libelle[:50]}')

        # OO EEE : arrachage Renouée (OO) → lié à ind_pression_renouee
        ind_pression_ren_ref = next((i for i in indicateurs_created if 'recolonisation de la Renouée' in i.nom_indicateur), None)
        if ind_pression_ren_ref and prio_op_1:
            op, created = Operation.objects.update_or_create(
                libelle='Campagnes d\'arrachage intensif de la Renouée (OO)',
                defaults={
                    'id_priorite': prio_op_1,
                    'code_operation': 'REM-EE01',
                    'id_referentiel_operations': 'GE',
                    'description': 'Trois campagnes annuelles d\'arrachage mécanique '
                                   'ciblant la réduction de 50% des surfaces colonisées. '
                                   'Suivi post-intervention à 3 mois.',
                    'annee_min': 2024,
                    'annee_max': 2030,
                    'id_utilisateur_ajout': admin
                }
            )
            CorOperationIndicateur.objects.get_or_create(id_operation=op, id_indicateur=ind_pression_ren_ref)
            operations_created.append(op)
            self.log_item('créé' if created else 'mis à jour', f'Opération OO: {op.libelle[:50]}')

        # ============================================
        # Enrichir les opérations avec données détaillées
        # (programmation annuelle, finances, suivi, fréquence, etc.)
        # ============================================
        self.log_header('Enrichissement des opérations avec données détaillées')

        type_action_se = self._get_nomenclature('TYPE_ACTION', 'SUIVI_EVALUATION')
        type_action_cs = self._get_nomenclature('TYPE_ACTION', 'CONNAISSANCE_SCIENTIFIQUE')
        type_action_ge = self._get_nomenclature('TYPE_ACTION', 'GESTION_ENTRETIEN')
        type_action_cc = self._get_nomenclature('TYPE_ACTION', 'COMMUNICATION')
        operateur_agent = self._get_nomenclature('OPERATEUR_TYPE', 'AGENT_RESERVE')
        operateur_presta = self._get_nomenclature('OPERATEUR_TYPE', 'PRESTATAIRE')
        cat_finance_region = self._get_nomenclature('CATEGORIE_FINANCE', 'REGION')
        cat_finance_dept = self._get_nomenclature('CATEGORIE_FINANCE', 'DEPARTEMENT')
        cat_finance_etat = self._get_nomenclature('CATEGORIE_FINANCE', 'ETAT')
        cat_finance_europe = self._get_nomenclature('CATEGORIE_FINANCE', 'EUROPE')

        annees_created = 0
        finances_created = 0
        suivis_created = 0

        for op in operations_created:
            # Set type_action based on id_referentiel_operations
            ref_to_type = {
                'SE': type_action_se, 'CS': type_action_cs,
                'GE': type_action_ge, 'CC': type_action_cc,
            }
            if op.id_referentiel_operations and op.id_referentiel_operations in ref_to_type:
                ta = ref_to_type[op.id_referentiel_operations]
                if ta:
                    op.id_type_action = ta

            # Set frequency and operators for all ops
            op.frequence_nombre = 1
            op.frequence_unite = 'an'
            op.operateurs = 'Agent de la réserve'
            op.save()

            # Create OperationAnnee entries
            if op.annee_min and op.annee_max:
                # Same months for all years (as in the form: monthly template applied to all years)
                mens = {"3": True, "4": True, "5": True, "6": True}
                for year in range(op.annee_min, op.annee_max + 1):
                    budget = 1200 if year % 3 != 0 else 700
                    etp = 5 if year % 2 == 0 else 3

                    oa, _ = OperationAnnee.objects.update_or_create(
                        id_operation=op, annee=year,
                        defaults={
                            'periodicite': True,
                            'budget': budget,
                            'etp': etp,
                            'id_operateur': operateur_agent if year % 2 == 0 else operateur_presta,
                            'periodicite_mensuelle': mens,
                        }
                    )
                    annees_created += 1

        # Create SuiviInventaire + Protocole + finances for the first 3 operations (for variety)
        protocoles_created = 0
        for i, op in enumerate(operations_created[:3]):
            # Create Protocole for first 2 operations
            protocole = None
            if i < 2:
                protocole = Protocole.objects.create(
                    protocole_dans_campanule=i == 0,
                    protocole_campanule_nom='Protocole STOC' if i == 0 else 'Protocole CMR',
                    respect_protocole=True if i == 0 else None,
                    justification_non_respect='',
                    differences_protocole='',
                    description_protocole='Suivi Temporel des Oiseaux Communs' if i == 0
                        else 'Capture-Marquage-Recapture pour suivi démographique',
                    objectif_protocole='Évaluer les tendances des populations d\'oiseaux communs' if i == 0
                        else 'Estimer les effectifs et la dynamique des populations',
                    periode_echantillonnage='Avril - Juin' if i == 0 else 'Mai - Septembre',
                    id_utilisateur_ajout=admin,
                )
                protocoles_created += 1
                self.log_item('créé', f'Protocole: {protocole.protocole_campanule_nom}')

            suivi_intitules = [
                'Suivi entomologique des carabiques',
                'Suivi démographique du flamant rose',
                'Cartographie évolutive des habitats',
            ]
            suivi = SuiviInventaire.objects.create(
                intitule=suivi_intitules[i],
                objectif_principal='Suivre les populations à enjeu' if i == 0
                    else 'Évaluer l\'état de conservation' if i == 1
                    else 'Cartographier l\'évolution spatiale',
                cibles_principales='Flore' if i == 0 else 'Faune' if i == 1 else 'Habitats',
                taxon_taxref='Coléoptères, Carabidae' if i == 0 else 'Phoenicopterus roseus' if i == 1 else '',
                annee_lancement_suivi=1998 if i == 0 else 2010 if i == 1 else None,
                id_protocole=protocole,
                outil_bancarisation='SERENA' if i == 0 else 'GeoNature' if i == 1 else '',
                outil_saisie='Formulaire terrain' if i <= 1 else '',
                transmission_donnee=True if i == 0 else None,
                id_utilisateur_ajout=admin,
            )
            op.est_suivi_existant = False
            op.id_suivi = suivi
            op.save()
            suivis_created += 1
            self.log_item('créé', f'SuiviInventaire pour: {op.libelle[:50]}')

            # Finances for enriched ops
            finances_data = [
                ('Région Auvergne-Rhône-Alpes', cat_finance_region),
                ('DREAL', cat_finance_etat),
            ]
            if i == 0:
                finances_data.append(('Agence de l\'Eau', cat_finance_dept))
            for lib, cat in finances_data:
                FinanceOperation.objects.update_or_create(
                    id_operation=op, libelle=lib,
                    defaults={'id_categorie': cat}
                )
                finances_created += 1

        # Add finances to remaining operations (without suivi)
        for op in operations_created[3:]:
            FinanceOperation.objects.update_or_create(
                id_operation=op, libelle='DREAL',
                defaults={'id_categorie': cat_finance_etat}
            )
            finances_created += 1

        # Link first few operations to sites
        site_camargue = sites[0] if len(sites) > 0 else None
        site_aiguilles = sites[1] if len(sites) > 1 else None
        site_remoray = sites[6] if len(sites) > 6 else None

        site_map = {}
        for op in operations_created:
            code = op.code_operation or ''
            if code.startswith('CAM'):
                site_map[op.id_operation] = site_camargue
            elif code.startswith('AR'):
                site_map[op.id_operation] = site_aiguilles
            elif code.startswith('REM'):
                site_map[op.id_operation] = site_remoray

        for op_id, site in site_map.items():
            if site:
                CorOperationSite.objects.get_or_create(
                    id_operation_id=op_id, id_site=site
                )

        # =====================================================================
        # Standalone SuiviInventaire (not linked to operations)
        # =====================================================================
        standalone_suivis_created = 0

        # Get nomenclatures for standalone suivis
        type_suivi = self._get_nomenclature('TYPE_SUIVI', 'SUIVI')
        type_inventaire = self._get_nomenclature('TYPE_SUIVI', 'INVENTAIRE')
        type_suivi_inv = self._get_nomenclature('TYPE_SUIVI', 'SUIVI_INVENTAIRE')
        statut_en_cours = self._get_nomenclature('STATUT_SUIVI', 'EN_COURS')
        statut_termine = self._get_nomenclature('STATUT_SUIVI', 'TERMINE')
        statut_a_venir = self._get_nomenclature('STATUT_SUIVI', 'A_VENIR')

        # Reference to first plan for some suivis
        plan_ref = plans[0] if plans else None

        standalone_data = [
            {
                'intitule': 'Suivi phénologique des orchidées',
                'objectif_principal': 'Évaluer les dates de floraison',
                'cibles_principales': 'Flore',
                'taxon_taxref': 'Orchidaceae',
                'annee_lancement_suivi': 2022,
                'actif': True,
                'id_type_suivi': type_suivi,
                'id_statut': statut_en_cours,
                'integre_plan_gestion': True,
                'id_pg': plan_ref,
                'commentaires': 'Suivi mensuel d\'avril à juillet',
                'frequence_nombre': 1,
                'frequence_unite': 'mois',
            },
            {
                'intitule': 'Inventaire chiroptères estival',
                'objectif_principal': 'Dénombrer les colonies de reproduction',
                'cibles_principales': 'Faune',
                'taxon_taxref': 'Chiroptera',
                'annee_lancement_suivi': 2019,
                'actif': True,
                'id_type_suivi': type_inventaire,
                'id_statut': statut_en_cours,
                'integre_plan_gestion': False,
                'commentaires': 'Comptage en sortie de gîte',
                'frequence_nombre': 2,
                'frequence_unite': 'an',
            },
            {
                'intitule': 'Suivi qualité des eaux de surface',
                'objectif_principal': 'Surveiller les paramètres physico-chimiques',
                'cibles_principales': 'Habitat',
                'annee_lancement_suivi': 2015,
                'annee_fin_suivi': 2025,
                'actif': True,
                'id_type_suivi': type_suivi,
                'id_statut': statut_en_cours,
                'integre_plan_gestion': True,
                'id_pg': plan_ref,
                'commentaires': 'Prélèvements trimestriels',
                'frequence_nombre': 4,
                'frequence_unite': 'an',
                'prix_indicatif': 3500,
            },
            {
                'intitule': 'Inventaire bryophytes tourbières',
                'objectif_principal': 'Cartographier la diversité bryologique',
                'cibles_principales': 'Flore',
                'annee_lancement_suivi': 2020,
                'annee_fin_suivi': 2022,
                'actif': False,
                'id_type_suivi': type_inventaire,
                'id_statut': statut_termine,
                'commentaires': 'Inventaire terminé, rapport final disponible',
            },
            {
                'intitule': 'Suivi et inventaire amphibiens',
                'objectif_principal': 'Suivre les populations d\'amphibiens',
                'cibles_principales': 'Faune',
                'taxon_taxref': 'Amphibia',
                'annee_lancement_suivi': 2024,
                'actif': True,
                'id_type_suivi': type_suivi_inv,
                'id_statut': statut_en_cours,
                'integre_plan_gestion': False,
                'commentaires': 'Points d\'écoute nocturne + pêche électrique',
                'frequence_nombre': 3,
                'frequence_unite': 'an',
                'prix_indicatif': 5000,
            },
            {
                'intitule': 'Suivi photographique des paysages',
                'objectif_principal': 'Documenter l\'évolution paysagère',
                'cibles_principales': 'Paysage',
                'annee_lancement_suivi': 2026,
                'actif': True,
                'id_type_suivi': type_suivi,
                'id_statut': statut_a_venir,
                'commentaires': 'Points de vue fixes, photographies saisonnières',
                'frequence_nombre': 4,
                'frequence_unite': 'an',
            },
            {
                'intitule': 'Inventaire entomologique prairies',
                'objectif_principal': 'Recenser la diversité des insectes pollinisateurs',
                'cibles_principales': 'Faune',
                'annee_lancement_suivi': 2016,
                'annee_fin_suivi': 2019,
                'actif': False,
                'id_type_suivi': type_inventaire,
                'id_statut': statut_termine,
                'commentaires': 'Étude terminée, résultats publiés',
            },
        ]

        for data in standalone_data:
            prix = data.pop('prix_indicatif', None)
            suivi = SuiviInventaire.objects.create(
                id_utilisateur_ajout=admin,
                **data,
            )
            if prix is not None:
                suivi.prix_indicatif = prix
                suivi.save()
            standalone_suivis_created += 1
            self.log_item('créé', f'Standalone suivi: {suivi.intitule[:50]}')

        self.log_summary(annees_created, 'années de programmation')
        self.log_summary(finances_created, 'sources de financement')
        self.log_summary(protocoles_created, 'protocoles')
        self.log_summary(suivis_created + standalone_suivis_created, 'suivis/inventaires (dont {} standalone)'.format(standalone_suivis_created))

        self.log_summary(len(enjeux_created), 'enjeux')
        self.log_summary(len(fcr_created), 'FCR')
        self.log_summary(len(responsabilites_created), 'responsabilités')
        self.log_summary(len(facteurs_created), "facteurs d'influence")
        self.log_summary(len(pressions_created), 'pressions')
        self.log_summary(len(etats_created), 'états actuels')
        self.log_summary(len(olts_created), 'objectifs à long terme')
        self.log_summary(len(nes_created), "niveaux d'exigence")
        self.log_summary(len(oos_created), 'objectifs opérationnels')
        self.log_summary(len(ras_created), 'résultats attendus')
        self.log_summary(len(indicateurs_created), 'indicateurs')
        self.log_summary(len(metriques_created), 'métriques')
        self.log_summary(len(mesures_created), 'mesures')
        self.log_summary(len(operations_created), 'opérations')

        result = {
            'enjeux': enjeux_created,
            'fcr': fcr_created,
            'responsabilites': responsabilites_created
        }
        self.context.set('enjeux', result)
        return result

    def reset(self) -> int:
        """
        Supprime les enjeux, FCR, facteurs d'influence, pressions,
        états actuels, OLTs, niveaux d'exigence et responsabilités de test.

        Returns:
            Nombre total d'éléments supprimés
        """
        count = 0
        count += FinanceOperation.objects.all().delete()[0]
        count += OperationAnnee.objects.all().delete()[0]
        count += CorOperationSite.objects.all().delete()[0]
        count += CorOperationIndicateur.objects.all().delete()[0]
        count += Operation.objects.all().delete()[0]
        count += SuiviInventaire.objects.all().delete()[0]
        count += Protocole.objects.all().delete()[0]
        count += Mesure.objects.all().delete()[0]
        count += Metrique.objects.all().delete()[0]
        count += CorIndicateurTaxon.objects.all().delete()[0]
        count += CorIndicateurHabitat.objects.all().delete()[0]
        count += CorIndicateurGeologie.objects.all().delete()[0]
        count += Indicateur.objects.all().delete()[0]
        count += ResultatAttendu.objects.all().delete()[0]
        count += ObjectifOperationnel.objects.all().delete()[0]
        count += NiveauExigence.objects.all().delete()[0]
        count += ObjectifLongTerme.objects.all().delete()[0]
        count += EtatActuel.objects.all().delete()[0]
        count += Pression.objects.all().delete()[0]
        count += FacteurInfluence.objects.all().delete()[0]
        count += CorResponsabiliteEnjeu.objects.all().delete()[0]
        count += CorResponsabiliteTaxon.objects.all().delete()[0]
        count += CorResponsabiliteHabitat.objects.all().delete()[0]
        count += CorEnjeuTaxon.objects.all().delete()[0]
        count += CorEnjeuHabitat.objects.all().delete()[0]
        count += Responsabilite.objects.all().delete()[0]
        count += Enjeu.objects.all().delete()[0]
        return count

    def get_dry_run_summary(self) -> List[str]:
        """
        Résumé des éléments qui seraient créés.

        Returns:
            Liste des lignes du résumé
        """
        return [
            '\nEnjeux (16):',
            '  - Camargue: 5 enjeux (hab. humides, flamant rose, activités trad., hydraulique, cistude)',
            '  - Aiguilles Rouges: 4 enjeux (pelouses alpines, zones humides, tétras-lyre, fréquentation)',
            '  - Vercors-Ecrins: 2 enjeux (corridors, grands rapaces)',
            '  - Lac de Remoray: 5 enjeux (qualité eaux, tourbières, balbuzard, prairies, EEE)',
            '\nFCR (8):',
            '  - Camargue: 2 FCR (connaissance, partenariats)',
            '  - Aiguilles Rouges: 2 FCR (moyens, climat)',
            '  - Vercors-Ecrins: 2 FCR (coordination, sensibilisation)',
            '  - Lac de Remoray: 2 FCR (suivi hydro., intégration territoriale)',
            '\nResponsabilités (10):',
            '  - Camargue: 3 (faune nationale, habitat régional, faune internationale)',
            '  - Aiguilles Rouges: 3 (flore régionale, faune locale, faune régionale)',
            '  - Vercors: 2 (rapaces national, habitat régional)',
            '  - Lac de Remoray: 2 (faune régionale, habitat national)',
            "\nFacteurs d'influence (10):",
            "  - Camargue/Hab. humides: 2 (régime hydrologique, urbanisation)",
            "  - Camargue/Flamant: 1 (fréquentation touristique)",
            "  - Aiguilles Rouges/Pelouses: 2 (changement climatique, surfréquentation)",
            "  - Aiguilles Rouges/Tétras-lyre: 1 (activités hivernales)",
            "  - Remoray/Qualité eaux: 1 (activités agricoles)",
            "  - Remoray/Tourbières: 1 (assèchement)",
            "\nPressions (~14):",
            "  - Endiguement, pompages, extension zones bâties",
            "  - Dérangement nidification, bruit nautique",
            "  - Remontée limite forestière, érosion sentiers",
            "  - Dérangement hivernal tétras",
            "  - Lessivage engrais, effluents élevage",
            "  - Drainage historique",
            '\nLiens taxons: 9 (flamant, cistude, tétras, gypaète, aigle, balbuzard, droséra, renouée)',
            'Liens habitats: 13 (lagunes, prés-salés, sansouires, pelouses, tourbières, prairies, lacs)',
            '\nÉtats actuels (10):',
            '  - Camargue: 3 (hab. humides, flamant, cistude)',
            '  - Aiguilles Rouges: 3 (pelouses/flore, pelouses/érosion, tétras-lyre)',
            '  - Vercors: 1 (grands rapaces)',
            '  - Remoray: 3 (qualité eaux, tourbières, balbuzard)',
            '\nObjectifs à long terme (10):',
            '  - Camargue: 3 (hydrologie, population flamant, connectivité cistude)',
            '  - Aiguilles Rouges: 3 (stations relictuelles, fréquentation, tétras)',
            '  - Vercors: 1 (noyaux rapaces)',
            '  - Remoray: 3 (état éco lac, hydrologie tourbières, quiétude balbuzard)',
            "\nNiveaux d'exigence (10):",
            '  - Camargue: 4 (surface 70%, débit 90%, reproduction flamant, sites cistude)',
            '  - Aiguilles Rouges: 3 (stations, érosion 50%, démographie tétras)',
            '  - Vercors: 2 (couples gypaète, reproduction)',
            '  - Remoray: 1 (phosphore < 20 µg/L, piézométrie tourbières)',
            '\nObjectifs opérationnels (6):',
            '  - Camargue/Hab. humides: 2 (gestion hydraulique, régulation urbanisation)',
            '  - Remoray/Tourbières: 2 (piézométrie, restauration végétation)',
            '  - Remoray/Qualité eaux: 1 (réduction nutriments agricoles)',
            '  - Remoray/EEE: 1 (contenir Renouée du Japon)',
            '\nRésultats attendus (9):',
            '  - Camargue OO1: 2 (restauration vannes, suivi piézométrique)',
            '  - Camargue OO2: 1 (cartographie pression urbaine)',
            '  - Remoray OO Tourbières 1: 2 (piézométrie stable, drains neutralisés)',
            '  - Remoray OO Tourbières 2: 1 (recouvrement sphaignes)',
            '  - Remoray OO Qualité: 2 (phosphore < 80 kg/an, conventions agricoles)',
            '  - Remoray OO EEE: 1 (surface Renouée réduite 50%)',
            '\nIndicateurs (5 NE + 6 pression OO):',
            '  - Camargue: 3 (surface habitats [état], reproduction flamant [état], pression débit [pression])',
            '  - Aiguilles Rouges: 2 (stations arctico-alpines [état], quiétude tétras [réponse])',
            '  - Remoray OO: 6 indicateurs de pression (piézo, drains, colonisation, phosphore, conventions, Renouée)',
            '\nMétriques (6 NE + 6 pression OO):',
            '  - NE: % surface bon état, végétation halophile, ratio jeunes/couples, jours sous débit min, etc.',
            '  - OO: amplitude piézo, % drains actifs, recouvrement ligneux, flux phosphore, exploitations, repousse',
            '\nMesures (8 NE + 6 pression OO):',
            '  - NE: 2 mesures par métrique (campagnes 2022-2024)',
            '  - OO: 1 mesure par métrique pression (2023)',
            '\nOpérations (20):',
            '  - Camargue: 4 (restauration hydraulique, suivi carto, régulation fréquentation, quotas prélèvement)',
            '  - Aiguilles Rouges: 3 (inventaire placettes, mise en défens, sensibilisation)',
            '  - Remoray NE: 7 (prélèvements eau, diagnostic agricole, conventions fauche, arrachage renouée, étude hydro, ...)',
            '  - Remoray OO: 6 (bouchage drains, suivi piézo, débroussaillage, suivi phosphore, conventions agricoles, arrachage Renouée)',
            '  - Dont 1 opération multi-indicateurs (phosphore + nutriments)',
        ]
