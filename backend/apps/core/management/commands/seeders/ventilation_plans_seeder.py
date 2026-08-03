"""
Seeder « Ventilation » — un plan de gestion par mode de ventilation budgétaire.

Objectif : pouvoir ouvrir côte à côte, en recette, les 6 modes de ventilation
d'une action (``Operation.ventilation_mode``) sans avoir à ressaisir la
programmation à la main.

Les 6 plans portent **exactement le même contenu** (même enjeu, mêmes 3
actions, mêmes jours de travail, mêmes composants de coût) : seul l'endroit où
la donnée est stockée change, conformément au contrat du formulaire d'action :

| Mode                 | Budget porté par                                        |
|----------------------|---------------------------------------------------------|
| ``none``             | ``OperationAnnee.budget``                                |
| ``by_type``          | ``budget_fonctionnement`` / ``budget_investissement``     |
| ``by_org``           | 1 ligne organisme, total dans ``budget_fonctionnement``   |
| ``by_org_type``      | 1 ligne organisme, fonctionnement / investissement        |
| ``by_type_poste``    | détail des coûts sur l'année + salarial calculé (#624)    |
| ``by_org_type_poste``| détail des coûts par organisme + salarial calculé (#602)  |

Dans les deux modes « + type de poste », les enveloppes fonctionnement /
investissement ne sont volontairement PAS stockées : elles se recalculent
depuis leurs composants (coût salarial = jours × coût jour du poste, stage,
prestataire, autres coûts). Les seeder les stocker les ferait compter deux fois
à l'export.

Conséquence pratique : **les 6 plans affichent les mêmes totaux en euros et en
jours**. Toute différence constatée dans l'application est un bug de la vue.

Le temps de travail suit le même principe : les jours sont identiques, seule la
cible des lignes RH change (globale / par organisme / par poste), comme le fait
``syncRhLines()`` côté formulaire.

Années : ``année courante − 2`` → ``année courante + 2``, pour avoir toujours du
réalisé (2 années passées), l'année en cours et du prévisionnel pur.
"""
from datetime import date
from decimal import Decimal
from typing import Dict, List

from apps.core.models import Nomenclature
from apps.plans.models import PlanGestion, CorSitePg, CorRolePlan
from apps.plans.models_enjeux import Enjeu, ObjectifLongTerme, NiveauExigence
from apps.plans.models_indicateurs import Indicateur, Metrique, Mesure
from apps.plans.models_operations import (
    CategorieDepense,
    CorOperationMetrique,
    CorOperationSite,
    FinanceOperation,
    Fonction,
    Operation,
    OperationAnnee,
    OperationAnneeOrganisme,
    OperationAnneeRH,
    Poste,
    PosteFonction,
    OperationRealisationGlobale,
    RealisationOperationAnnee,
    RealisationOperationAnneeOrganisme,
    RealisationOperationAnneeRH,
)
from apps.users.models import CorOgSite, Site

from .base import BaseSeeder
from ._geo_helpers import make_operation_geom


# Site support des 6 plans : il porte 2 organismes gestionnaires (RNF + OFB),
# indispensable pour les modes ventilés par organisme.
_SITE_KEYWORD = 'Camargue'

# (mode, libellé du mode, suffixe des codes d'action)
_MODES = [
    ('none', 'aucune ventilation', 'NONE'),
    ('by_org', 'par organisme', 'ORG'),
    ('by_type', 'par type de budget', 'TYPE'),
    ('by_org_type', 'par organisme et type de budget', 'ORGTYPE'),
    ('by_type_poste', 'par type de budget et type de poste', 'TYPEPOSTE'),
    ('by_org_type_poste', 'par organisme, type de budget et type de poste', 'ORGTYPEPOSTE'),
]

_PLAN_PREFIX = 'Ventilation — '

# Préfixe des codes d'action de ce seeder. `RealisationsSeeder` s'en sert pour
# laisser ces actions tranquilles : leur suivi est posé ici, cohérent avec le
# mode de ventilation (ce que la distribution générique ne sait pas faire).
VENTILATION_OP_CODE_PREFIX = 'CAM-VENT-'

# Postes du plan (aucun nominatif, RGPD — cf. #560). L'organisme est désigné par
# sa place dans les gestionnaires du site : « principal » = 1er, « secondaire »
# = 2e. Un poste prestataire porte un organisme saisi librement et pas de coût
# jour (coût forfaitaire, facturé en « prestataire »).
# (clé, org, nombre, ETP total, fonction, coût jour)
_POSTES = [
    ('conservateur', 'principal', 1, '1.00', 'Conservateur', '300.00'),
    ('garde', 'principal', 2, '2.00', 'Garde-technicien', '250.00'),
    ('stagiaire', 'secondaire', 3, '1.50', 'Stagiaire', '80.00'),
    ('benevoles', 'principal', 10, '0.50', 'Bénévole', '0.00'),
    ('prestataire', None, 1, None, 'Prestataire', None),
]

# Type de poste déduit du libellé de la fonction (#596), comme dans rh_seeder.
_TYPE_PAR_LIBELLE = [
    ('stagiaire', Fonction.TYPE_STAGIAIRE),
    ('bénévole', Fonction.TYPE_BENEVOLE),
    ('prestataire', Fonction.TYPE_PRESTATAIRE),
    ('partenaire', Fonction.TYPE_PARTENAIRE),
]
_NON_FINANCEES = {'bénévole', 'partenaire'}

_FONCT = CategorieDepense.FONCTIONNEMENT
_INVEST = CategorieDepense.INVESTISSEMENT
_BENEVOLAT = CategorieDepense.BENEVOLAT_PARTENARIAT

# Les 3 actions du plan. `annees` = (offset début, offset fin) dans la période
# du plan. `rh` = (poste, jours/an, catégorie de dépense). `couts` = composants
# de coût annuels, par organisme porteur.
_ACTIONS = [
    {
        'suffix': 'CS1',
        'cat': 'CS',
        'prio': 'PRIORITE_1',
        'libelle': 'Suivi annuel des habitats humides',
        'description': "Cartographie et relevés phytosociologiques annuels des "
                       "habitats humides, sur les mêmes placettes permanentes.",
        'annees': (0, 4),
        'freq': (1, 'an'),
        'mens': {"5": True, "6": True, "7": True},
        'operateurs': 'Conservateur, garde-technicien, stagiaire',
        'partenaires': 'Tour du Valat, CBN méditerranéen',
        'financeurs': "Agence de l'eau, Région",
        'finances': [("Agence de l'eau — contrat de milieu", 'ETAT'),
                     ("Région — dotation annuelle", 'REGION')],
        'rh': [
            ('conservateur', '5', _FONCT),
            ('stagiaire', '20', _FONCT),
            ('benevoles', '6', _BENEVOLAT),
        ],
        'couts': {
            'principal': {
                'cout_prestataire': '2500',
                'autre_cout': '800',
                'autre_cout_commentaire': 'Frais de déplacement et analyses',
            },
            'secondaire': {
                'cout_stage': '1200',
            },
        },
    },
    {
        'suffix': 'IP1',
        'cat': 'IP',
        'prio': 'PRIORITE_1',
        'libelle': 'Restauration hydraulique des annexes du marais',
        'description': "Travaux de curage et de reconnexion des annexes "
                       "hydrauliques, avec pose de deux ouvrages de régulation.",
        'annees': (0, 3),
        'freq': (1, 'an'),
        'mens': {"9": True, "10": True, "11": True},
        'operateurs': 'Garde-technicien, entreprise de travaux',
        'partenaires': 'Syndicat mixte du delta',
        'financeurs': "Agence de l'eau, FEDER",
        'finances': [("FEDER — axe biodiversité", 'EUROPE'),
                     ("Département — travaux hydrauliques", 'DEPARTEMENT')],
        'rh': [
            ('conservateur', '3', _FONCT),
            ('garde', '15', _INVEST),
            ('benevoles', '4', _BENEVOLAT),
        ],
        'couts': {
            'principal': {
                'autre_cout': '500',
                'autre_cout_commentaire': 'Consommables de chantier',
                'cout_prestataire_invest': '12000',
                'autre_cout_invest': '3000',
                'autre_cout_invest_commentaire': "Ouvrages de régulation",
            },
        },
    },
    {
        'suffix': 'PA1',
        'cat': 'PA',
        'prio': 'PRIORITE_2',
        'libelle': 'Animations et sorties nature grand public',
        'description': "Programme annuel de sorties guidées et d'ateliers "
                       "scolaires autour des zones humides.",
        'annees': (1, 4),
        'freq': (6, 'an'),
        'mens': {"3": True, "4": True, "5": True, "6": True, "9": True, "10": True},
        'operateurs': 'Garde-technicien, stagiaire, bénévoles',
        'partenaires': 'Écoles du territoire, association locale',
        'financeurs': 'Commune, Région',
        'finances': [("Commune — convention d'animation", 'COMMUNE')],
        'rh': [
            ('garde', '8', _FONCT),
            ('stagiaire', '10', _FONCT),
            ('benevoles', '12', _BENEVOLAT),
        ],
        'couts': {
            'principal': {
                'cout_prestataire': '1500',
                'autre_cout': '400',
                'autre_cout_commentaire': 'Impression des supports',
            },
            'secondaire': {
                'cout_stage': '600',
            },
        },
    },
]

# Suivi de réalisation : niveau + ratio appliqué au prévisionnel, par ancienneté
# de l'année. Les années futures ne sont pas suivies.
_REALISATION_PAR_ANNEE = [
    ('TERMINE', Decimal('0.95')),   # année courante − 2
    ('PARTIEL', Decimal('0.55')),   # année courante − 1
    ('EN_COURS', Decimal('0.40')),  # année courante
]

# Chaîne enjeu → OLT → NE → indicateur → métrique, identique sur les 6 plans.
_ENJEU = {
    'libelle': 'Habitats humides et fonctionnement hydraulique',
    'court': 'Habitats humides',
    'olt': "Maintenir en bon état de conservation les habitats humides du site",
    'ne': "Surface d'habitats humides en bon état ≥ 120 ha",
    'indicateur': "Surface d'habitats humides en bon état de conservation",
    'metrique': 'Surface en bon état (ha)',
    'unite': 'ha',
    'cible': '≥ 120 ha',
    'mesures': ['112', '116', '119'],  # une par année écoulée (2 passées + courante)
}

_COUT_FIELDS = (
    'cout_stage', 'cout_prestataire', 'autre_cout',
    'cout_prestataire_invest', 'autre_cout_invest',
)


def _dec(value) -> Decimal:
    """Décimal tolérant : None / '' → 0."""
    if value in (None, ''):
        return Decimal('0')
    return Decimal(str(value))


def _q(value: Decimal) -> Decimal:
    return value.quantize(Decimal('0.01'))


class VentilationPlansSeeder(BaseSeeder):
    """Crée 1 plan de gestion par mode de ventilation, entièrement programmé."""

    name = 'ventilation_plans'
    dependencies = ['plans']

    # ------------------------------------------------------------------ utils

    def _nomenclature(self, type_mnemonique: str, mnemonique: str):
        return Nomenclature.objects.filter(
            id_type__mnemonique=type_mnemonique, mnemonique=mnemonique,
        ).first()

    def _fonction(self, libelle: str) -> Fonction:
        fonction = Fonction.objects.filter(libelle__iexact=libelle).first()
        if fonction:
            return fonction
        key = libelle.lower()
        type_poste = next(
            (t for needle, t in _TYPE_PAR_LIBELLE if needle in key),
            Fonction.TYPE_SALARIE,
        )
        return Fonction.objects.create(
            libelle=libelle,
            type_poste=type_poste,
            finance_par_defaut=key not in _NON_FINANCEES,
            is_socle=False,
        )

    # ------------------------------------------------------------------- seed

    def seed(self) -> dict:
        self.log_header('Plans « Ventilation » (1 par mode de ventilation)')

        users = self.context.require('users')
        admin = users[0] if users else None

        site = Site.objects.filter(nom_site__icontains=_SITE_KEYWORD).first()
        if not site:
            self.log(f'Site « {_SITE_KEYWORD} » introuvable — seeder ignoré.', 'WARNING')
            return {}

        # Gestionnaires du site, principal en tête : ce sont eux que le
        # formulaire propose pour la ventilation par organisme.
        organismes = [
            cor.uuid_og
            for cor in CorOgSite.objects.filter(id_site=site)
            .select_related('uuid_og')
            .order_by('-principal', 'uuid_og__nom_organisme')
        ]
        if not organismes:
            self.log(
                f'Aucun organisme gestionnaire sur « {site.nom_site} » — '
                'les modes ventilés par organisme seraient vides, seeder ignoré.',
                'WARNING',
            )
            return {}
        org_map = {
            'principal': organismes[0],
            'secondaire': organismes[1] if len(organismes) > 1 else organismes[0],
        }

        nomenclatures = self._load_nomenclatures()
        if not nomenclatures:
            return {}

        current_year = date.today().year
        annee_debut, annee_fin = current_year - 2, current_year + 2
        years = list(range(annee_debut, annee_fin + 1))

        plans: List[PlanGestion] = []
        nb_ops = 0
        for mode, libelle_mode, code_suffix in _MODES:
            plan = self._create_plan(
                libelle_mode, site, admin, users,
                annee_debut, annee_fin, nomenclatures,
            )
            postes = self._create_postes(plan, org_map)
            metrique = self._create_arborescence(plan, admin, years, nomenclatures)
            for action in _ACTIONS:
                op = self._create_operation(
                    plan, action, code_suffix, site, metrique, admin,
                    years, nomenclatures,
                )
                self._program_operation(
                    op, action, mode, postes, org_map, years, current_year,
                    admin, nomenclatures,
                )
                nb_ops += 1
            plans.append(plan)
            self.log_item('plan', f'{plan.nom} ({len(_ACTIONS)} actions, {len(years)} années)')

        self.log_summary(len(plans), 'plans « Ventilation » créés')
        self.log_summary(nb_ops, 'actions programmées (budget + RH + suivi)')
        self.context.set('ventilation_plans', plans)
        return {'ventilation_plans': plans}

    def _load_nomenclatures(self) -> Dict:
        """Charge les nomenclatures nécessaires ; None si l'une manque."""
        noms = {
            'cat_enjeu': self._nomenclature('CATEGORIE_ENJEU', 'ENJEU'),
            'type_ind': self._nomenclature('TYPE_INDICATEUR', 'ETAT'),
            'type_met': self._nomenclature('TYPE_METRIQUE', 'NUMERIQUE'),
            'type_doc': self._nomenclature('TYPE_DOCUMENT_PLAN', 'PLAN_INITIAL')
            or Nomenclature.objects.filter(mnemonique='PLAN_INITIAL').first(),
        }
        if not all((noms['cat_enjeu'], noms['type_ind'], noms['type_met'])):
            self.log(
                'Nomenclatures de base manquantes (CATEGORIE_ENJEU / '
                'TYPE_INDICATEUR / TYPE_METRIQUE) — seeder ignoré.',
                'WARNING',
            )
            return {}
        noms['importance'] = {
            mn: self._nomenclature('IMPORTANCE_ENJEU', mn)
            for mn in ('PRIORITE_1', 'PRIORITE_2')
        }
        noms['priorite_op'] = {
            mn: self._nomenclature('PRIORITE_OPERATION', mn)
            for mn in ('PRIORITE_1', 'PRIORITE_2')
        }
        noms['cat_reserve'] = {
            code: self._nomenclature('CATEGORIE_ACTION_RESERVE', code)
            for code in ('CS', 'IP', 'PA')
        }
        # #588 — le type d'action est obligatoire dans le formulaire : les
        # actions seedées doivent en porter un, sinon leur fiche est
        # inéditable (formulaire invalide dès l'ouverture).
        noms['type_action'] = {
            cat: self._nomenclature('TYPE_ACTION', mn)
            for cat, mn in (('CS', 'CS8'), ('IP', 'IP1'), ('PA', 'PA1'))
        }
        noms['finance'] = {
            code: self._nomenclature('CATEGORIE_FINANCE', code)
            for code in ('ETAT', 'REGION', 'DEPARTEMENT', 'EUROPE', 'COMMUNE')
        }
        noms['niveaux'] = {
            mn: self._nomenclature('NIVEAU_REALISATION', mn)
            for mn in ('TERMINE', 'PARTIEL', 'EN_COURS')
        }
        return noms

    # ------------------------------------------------------------------ plans

    def _create_plan(self, libelle_mode, site, admin, users,
                     annee_debut, annee_fin, nomenclatures) -> PlanGestion:
        """Plan en brouillon (donc éditable) porté par le site de démonstration."""
        plan, _ = PlanGestion.objects.update_or_create(
            nom=f'{_PLAN_PREFIX}{libelle_mode}',
            defaults={
                'annee_debut': annee_debut,
                'annee_fin': annee_fin,
                'rang': 1,
                'version': '1',
                'statut': 'draft',
                'surface': Decimal(str(site.surf_off)) if site.surf_off else None,
                'id_type_document': nomenclatures.get('type_doc'),
                'redacteur_nom': 'Jeu de démonstration CICADA',
                'commentaire': (
                    "Plan de démonstration : toutes les actions utilisent le mode "
                    f"de ventilation « {libelle_mode} ». Les 6 plans « Ventilation "
                    "— … » portent le même contenu (mêmes jours, mêmes coûts) : "
                    "seul le stockage de la donnée budgétaire change, les totaux "
                    "affichés doivent donc être identiques d'un plan à l'autre."
                ),
                'id_utilisateur_ajout': admin,
                'id_utilisateur_maj': admin,
            },
        )
        CorSitePg.objects.get_or_create(
            site=site, plan_de_gestion=plan, defaults={'rang': 1},
        )
        # Référents : super admin + admin organisme, plus un utilisateur simple
        # comme membre (permet de tester les vues en lecture seule).
        membres = [(u, i < 2) for i, u in enumerate(users[:3])]
        referents = []
        for user, is_referent in membres:
            CorRolePlan.objects.update_or_create(
                id_role=user, plan_de_gestion=plan,
                defaults={'referent': is_referent},
            )
            if is_referent:
                referents.append(user)
        plan.referents.set(referents)
        return plan

    def _create_postes(self, plan, org_map) -> Dict[str, Poste]:
        """Postes du plan (identiques d'un plan à l'autre)."""
        Poste.objects.filter(id_pg=plan).delete()
        postes = {}
        for cle, org_key, nombre, etp, fonction, cout_jour in _POSTES:
            poste = Poste.objects.create(
                id_pg=plan,
                id_organisme=org_map[org_key] if org_key else None,
                organisme_libre='' if org_key else "Bureau d'études Hydro-Concept",
                nombre=nombre,
                etp=Decimal(etp) if etp else None,
                cout_jour=Decimal(cout_jour) if cout_jour else None,
            )
            PosteFonction.objects.create(
                id_poste=poste, id_fonction=self._fonction(fonction),
            )
            postes[cle] = poste
        return postes

    def _create_arborescence(self, plan, admin, years, nomenclatures) -> Metrique:
        """Enjeu → OLT → NE → indicateur → métrique + mesures des années écoulées."""
        enjeu, _ = Enjeu.objects.update_or_create(
            id_pg=plan, libelle=_ENJEU['libelle'],
            defaults={
                'id_categorie': nomenclatures['cat_enjeu'],
                'intitule_court': _ENJEU['court'],
                'rang': 1,
                'id_importance': nomenclatures['importance'].get('PRIORITE_1'),
                'categorie_ecologique': True,
                'habitat': True,
                'description': "Enjeu de démonstration servant de support aux "
                               "actions de test de la ventilation budgétaire.",
                'id_utilisateur_ajout': admin,
            },
        )
        olt, _ = ObjectifLongTerme.objects.update_or_create(
            id_enjeu=enjeu, libelle=_ENJEU['olt'],
            defaults={'id_utilisateur_ajout': admin},
        )
        ne, _ = NiveauExigence.objects.update_or_create(
            id_olt=olt, libelle=_ENJEU['ne'],
            defaults={'id_utilisateur_ajout': admin},
        )
        indicateur, _ = Indicateur.objects.update_or_create(
            id_ne=ne, nom_indicateur=_ENJEU['indicateur'],
            defaults={
                'type_indicateur': nomenclatures['type_ind'],
                'id_utilisateur_ajout': admin,
            },
        )
        metrique, _ = Metrique.objects.update_or_create(
            id_indicateur=indicateur, nom_metrique=_ENJEU['metrique'],
            defaults={
                'type_metrique': nomenclatures['type_met'],
                'unite': _ENJEU['unite'],
                'sens_variation': 'CROISSANT',
                'etat_reference': _ENJEU['cible'],
                'id_utilisateur_ajout': admin,
            },
        )
        for offset, valeur in enumerate(_ENJEU['mesures']):
            Mesure.objects.update_or_create(
                id_metrique=metrique, date_mesure=date(years[offset], 6, 15),
                defaults={
                    'valeur': valeur,
                    'commentaire': 'Mesure de démonstration (seed ventilation).',
                    'id_utilisateur_ajout': admin,
                },
            )
        return metrique

    # --------------------------------------------------------------- actions

    def _create_operation(self, plan, action, code_suffix, site, metrique,
                          admin, years, nomenclatures) -> Operation:
        code = f"{VENTILATION_OP_CODE_PREFIX}{code_suffix}-{action['suffix']}"
        debut, fin = action['annees']
        op, _ = Operation.objects.update_or_create(
            code_operation=code,
            defaults={
                'libelle': action['libelle'],
                'description': action['description'],
                'id_priorite': nomenclatures['priorite_op'].get(action['prio']),
                'id_categorie_action_reserve': nomenclatures['cat_reserve'].get(action['cat']),
                'id_type_action': nomenclatures['type_action'].get(action['cat']),
                'annee_min': years[debut],
                'annee_max': years[fin],
                'frequence_nombre': action['freq'][0],
                'frequence_unite': action['freq'][1],
                'operateurs': action['operateurs'],
                'partenaires': action['partenaires'],
                'financeurs': action['financeurs'],
                'programmation_mensuelle_defaut': action['mens'],
                'id_utilisateur_ajout': admin,
            },
        )
        if not op.geom:
            op.geom = make_operation_geom(code, len(code))
            op.save(update_fields=['geom'])
        CorOperationMetrique.objects.get_or_create(id_operation=op, id_metrique=metrique)
        CorOperationSite.objects.get_or_create(id_operation=op, id_site=site)
        for libelle, categorie in action['finances']:
            FinanceOperation.objects.update_or_create(
                id_operation=op, libelle=libelle,
                defaults={'id_categorie': nomenclatures['finance'].get(categorie)},
            )
        return op

    # ------------------------------------------------------- coûts par action

    def _salarial(self, action, postes) -> Dict[str, Dict[str, Decimal]]:
        """
        Coût salarial annuel de l'action, par organisme du poste et par
        catégorie de dépense : Σ jours × coût jour. Le bénévolat est valorisé en
        jours seulement, jamais en euros.
        """
        totaux: Dict[str, Dict[str, Decimal]] = {}
        for cle, jours, categorie in action['rh']:
            if categorie == _BENEVOLAT:
                continue
            poste = postes[cle]
            org_key = self._org_key_of_poste(cle)
            cout = _dec(poste.cout_jour) * _dec(jours)
            totaux.setdefault(org_key, {_FONCT: Decimal('0'), _INVEST: Decimal('0')})
            totaux[org_key][categorie] += cout
        return totaux

    @staticmethod
    def _org_key_of_poste(cle_poste: str) -> str:
        for cle, org_key, *_ in _POSTES:
            if cle == cle_poste:
                return org_key or 'principal'
        return 'principal'

    def _org_totaux(self, action, postes) -> Dict[str, Dict[str, Decimal]]:
        """
        Enveloppes fonctionnement / investissement d'une année, par organisme.

        C'est la source unique des montants : les modes ventilés par organisme
        les stockent tels quels, les modes globaux en stockent la somme, et les
        modes « + type de poste » stockent leurs composants (le total se
        recalcule alors à l'identique).
        """
        salarial = self._salarial(action, postes)
        totaux: Dict[str, Dict[str, Decimal]] = {}

        def cell(org_key):
            return totaux.setdefault(
                org_key, {'fonct': Decimal('0'), 'invest': Decimal('0')},
            )

        for org_key, par_categorie in salarial.items():
            c = cell(org_key)
            c['fonct'] += par_categorie[_FONCT]
            c['invest'] += par_categorie[_INVEST]
        for org_key, couts in action['couts'].items():
            c = cell(org_key)
            c['fonct'] += (_dec(couts.get('cout_stage'))
                           + _dec(couts.get('cout_prestataire'))
                           + _dec(couts.get('autre_cout')))
            c['invest'] += (_dec(couts.get('cout_prestataire_invest'))
                            + _dec(couts.get('autre_cout_invest')))
        return totaux

    # ------------------------------------------------- programmation annuelle

    def _program_operation(self, op, action, mode, postes, org_map, years,
                           current_year, admin, nomenclatures) -> None:
        """Programme l'action année par année selon son mode de ventilation."""
        op.ventilation_mode = mode
        op.declinaison_par_poste = mode in Operation.VENTILATION_POSTE_MODES
        op.save(update_fields=['ventilation_mode', 'declinaison_par_poste'])

        # Pas de statut global forcé : le niveau de réalisation affiché doit
        # découler du suivi annuel posé ci-dessous (nettoie une éventuelle
        # surcharge laissée par un passage de `RealisationsSeeder`).
        OperationRealisationGlobale.objects.filter(id_operation=op).delete()

        totaux = self._org_totaux(action, postes)
        total_fonct = sum((c['fonct'] for c in totaux.values()), Decimal('0'))
        total_invest = sum((c['invest'] for c in totaux.values()), Decimal('0'))
        jours_total = sum((_dec(j) for _, j, _ in action['rh']), Decimal('0'))

        debut, fin = action['annees']
        for year in years[debut:fin + 1]:
            oa = self._create_annee(
                op, action, mode, year, totaux, total_fonct, total_invest,
                jours_total, org_map,
            )
            lignes_prev = self._create_rh_lines(oa, action, mode, postes, org_map)
            self._create_realisation(
                oa, op, action, mode, year, current_year, lignes_prev,
                admin, nomenclatures,
            )

    def _create_annee(self, op, action, mode, year, totaux, total_fonct,
                      total_invest, jours_total, org_map) -> OperationAnnee:
        """Crée l'``OperationAnnee`` et, si le mode l'exige, ses lignes organisme."""
        defaults = {
            'periodicite': True,
            'periodicite_mensuelle': action['mens'],
            'budget': _q(total_fonct + total_invest),
            'etp': _q(jours_total),
            'budget_fonctionnement': None,
            'budget_investissement': None,
        }
        # Les composants de coût ne sont portés par l'année qu'en `by_type_poste`.
        for champ in _COUT_FIELDS:
            defaults[champ] = None
        defaults['autre_cout_commentaire'] = ''
        defaults['autre_cout_invest_commentaire'] = ''

        if mode == 'by_type':
            defaults['budget_fonctionnement'] = _q(total_fonct)
            defaults['budget_investissement'] = _q(total_invest)
        elif mode == 'by_type_poste':
            # #624 — détail des coûts sur l'année, budgets fonct/invest dérivés
            # (donc NON stockés) ; le coût salarial vient des lignes RH.
            fusion = self._fusion_couts(action)
            for champ in _COUT_FIELDS:
                defaults[champ] = _q(_dec(fusion.get(champ))) if fusion.get(champ) else None
            defaults['autre_cout_commentaire'] = fusion.get('autre_cout_commentaire', '')
            defaults['autre_cout_invest_commentaire'] = fusion.get(
                'autre_cout_invest_commentaire', '')

        oa, _ = OperationAnnee.objects.update_or_create(
            id_operation=op, annee=year, defaults=defaults,
        )

        OperationAnneeOrganisme.objects.filter(id_operation_annee=oa).delete()
        if mode not in ('by_org', 'by_org_type', 'by_org_type_poste'):
            return oa

        for org_key, cell in totaux.items():
            organisme = org_map[org_key]
            org_defaults = {
                'budget_fonctionnement': None,
                'budget_investissement': None,
                'cout_stage': None,
                'cout_prestataire': None,
                'autre_cout': None,
                'autre_cout_commentaire': '',
                'cout_prestataire_invest': None,
                'autre_cout_invest': None,
                'autre_cout_invest_commentaire': '',
                'etp': None,
            }
            if mode == 'by_org':
                # Un seul montant par organisme : le total, stocké côté
                # fonctionnement (le mode ne distingue pas les types).
                org_defaults['budget_fonctionnement'] = _q(cell['fonct'] + cell['invest'])
                org_defaults['etp'] = _q(self._jours_org(action, org_key))
            elif mode == 'by_org_type':
                org_defaults['budget_fonctionnement'] = _q(cell['fonct'])
                org_defaults['budget_investissement'] = _q(cell['invest'])
                org_defaults['etp'] = _q(self._jours_org(action, org_key))
            else:
                # by_org_type_poste : composants de coût par organisme ; les
                # budgets fonct/invest sont dérivés (jamais stockés) et le temps
                # de travail est décliné par poste, pas par organisme.
                couts = action['couts'].get(org_key, {})
                for champ in _COUT_FIELDS:
                    org_defaults[champ] = _q(_dec(couts[champ])) if couts.get(champ) else None
                org_defaults['autre_cout_commentaire'] = couts.get('autre_cout_commentaire', '')
                org_defaults['autre_cout_invest_commentaire'] = couts.get(
                    'autre_cout_invest_commentaire', '')
            OperationAnneeOrganisme.objects.update_or_create(
                id_operation_annee=oa, id_organisme=organisme, defaults=org_defaults,
            )
        return oa

    @staticmethod
    def _fusion_couts(action) -> dict:
        """Composants de coût cumulés tous organismes (mode sans organisme)."""
        fusion: dict = {}
        for couts in action['couts'].values():
            for champ in _COUT_FIELDS:
                if couts.get(champ):
                    fusion[champ] = _dec(fusion.get(champ)) + _dec(couts[champ])
            for champ in ('autre_cout_commentaire', 'autre_cout_invest_commentaire'):
                if couts.get(champ) and not fusion.get(champ):
                    fusion[champ] = couts[champ]
        return fusion

    def _jours_org(self, action, org_key) -> Decimal:
        """Jours annuels imputés à un organisme (via l'organisme de chaque poste)."""
        return sum(
            (_dec(jours) for cle, jours, _cat in action['rh']
             if self._org_key_of_poste(cle) == org_key),
            Decimal('0'),
        )

    # ---------------------------------------------------------------- RH (#560)

    def _create_rh_lines(self, oa, action, mode, postes, org_map) -> List[OperationAnneeRH]:
        """
        Lignes de temps de travail prévisionnel. Les jours sont les mêmes dans
        les 6 plans ; seule la cible change, comme dans le formulaire :
        globale (aucune ventilation), par organisme, ou par poste.
        """
        OperationAnneeRH.objects.filter(id_operation_annee=oa).delete()
        lignes = []

        if mode in Operation.VENTILATION_POSTE_MODES:
            for cle, jours, categorie in action['rh']:
                lignes.append(OperationAnneeRH.objects.create(
                    id_operation_annee=oa,
                    id_poste=postes[cle],
                    jours=_dec(jours),
                    categorie_depense=categorie,
                    finance=categorie != _BENEVOLAT,
                ))
            return lignes

        if mode in ('by_org', 'by_org_type'):
            # Une ligne par organisme et par catégorie de dépense présente.
            cumul: Dict[tuple, Decimal] = {}
            for cle, jours, categorie in action['rh']:
                key = (self._org_key_of_poste(cle), categorie)
                cumul[key] = cumul.get(key, Decimal('0')) + _dec(jours)
            for (org_key, categorie), jours in cumul.items():
                lignes.append(OperationAnneeRH.objects.create(
                    id_operation_annee=oa,
                    id_organisme=org_map[org_key],
                    jours=jours,
                    categorie_depense=categorie,
                    finance=categorie != _BENEVOLAT,
                ))
            return lignes

        # Modes globaux : une ligne de temps total par catégorie de dépense.
        cumul_cat: Dict[str, Decimal] = {}
        for _cle, jours, categorie in action['rh']:
            cumul_cat[categorie] = cumul_cat.get(categorie, Decimal('0')) + _dec(jours)
        for categorie, jours in cumul_cat.items():
            lignes.append(OperationAnneeRH.objects.create(
                id_operation_annee=oa,
                jours=jours,
                categorie_depense=categorie,
                finance=categorie != _BENEVOLAT,
            ))
        return lignes

    # ------------------------------------------------------------- réalisation

    def _create_realisation(self, oa, op, action, mode, year, current_year,
                            lignes_prev, admin, nomenclatures) -> None:
        """Suivi des années écoulées et de l'année en cours (rien au-delà)."""
        anciennete = current_year - year
        if anciennete < 0 or anciennete >= len(_REALISATION_PAR_ANNEE):
            return
        mnemo, ratio = _REALISATION_PAR_ANNEE[len(_REALISATION_PAR_ANNEE) - 1 - anciennete]
        niveau = nomenclatures['niveaux'].get(mnemo)

        defaults = {
            'id_niveau_realisation': niveau,
            'periodicite_realisee': mnemo in ('TERMINE', 'PARTIEL'),
            'periodicite_mensuelle_realisee': action['mens'] if mnemo == 'TERMINE' else {},
            'commentaires': f"Suivi {year} (seed ventilation) — {mnemo.lower()}.",
            'operateurs_realises': action['operateurs'],
            'financeurs_realises': action['financeurs'],
            'id_utilisateur_maj': admin,
            # Réinitialisés puis renseignés selon le mode.
            'budget_realise': None,
            'budget_fonctionnement_realise': None,
            'budget_investissement_realise': None,
            'etp_realise': None,
            'cout_stage_realise': None,
            'cout_prestataire_realise': None,
            'autre_cout_realise': None,
            'autre_cout_commentaire_realise': '',
            'cout_prestataire_invest_realise': None,
            'autre_cout_invest_realise': None,
            'autre_cout_invest_commentaire_realise': '',
        }

        if mode == 'none':
            defaults['budget_realise'] = _q(_dec(oa.budget) * ratio)
            defaults['etp_realise'] = _q(_dec(oa.etp) * ratio)
        elif mode == 'by_type':
            defaults['budget_fonctionnement_realise'] = _q(_dec(oa.budget_fonctionnement) * ratio)
            defaults['budget_investissement_realise'] = _q(_dec(oa.budget_investissement) * ratio)
            defaults['etp_realise'] = _q(_dec(oa.etp) * ratio)
        elif mode == 'by_type_poste':
            for champ in _COUT_FIELDS:
                valeur = getattr(oa, champ)
                if valeur is not None:
                    defaults[f'{champ}_realise'] = _q(_dec(valeur) * ratio)
            defaults['autre_cout_commentaire_realise'] = oa.autre_cout_commentaire
            defaults['autre_cout_invest_commentaire_realise'] = oa.autre_cout_invest_commentaire

        realisation, _ = RealisationOperationAnnee.objects.update_or_create(
            id_operation_annee=oa, defaults=defaults,
        )

        # Ventilation réalisée par organisme, miroir du prévisionnel.
        for oao in OperationAnneeOrganisme.objects.filter(id_operation_annee=oa):
            org_defaults = {
                'budget_fonctionnement_realise': None,
                'budget_investissement_realise': None,
                'etp_realise': None,
                'cout_stage_realise': None,
                'cout_prestataire_realise': None,
                'autre_cout_realise': None,
                'autre_cout_commentaire_realise': '',
                'cout_prestataire_invest_realise': None,
                'autre_cout_invest_realise': None,
                'autre_cout_invest_commentaire_realise': '',
            }
            if mode == 'by_org_type_poste':
                for champ in _COUT_FIELDS:
                    valeur = getattr(oao, champ)
                    if valeur is not None:
                        org_defaults[f'{champ}_realise'] = _q(_dec(valeur) * ratio)
                org_defaults['autre_cout_commentaire_realise'] = oao.autre_cout_commentaire
                org_defaults['autre_cout_invest_commentaire_realise'] = \
                    oao.autre_cout_invest_commentaire
            else:
                if oao.budget_fonctionnement is not None:
                    org_defaults['budget_fonctionnement_realise'] = _q(
                        _dec(oao.budget_fonctionnement) * ratio)
                if oao.budget_investissement is not None:
                    org_defaults['budget_investissement_realise'] = _q(
                        _dec(oao.budget_investissement) * ratio)
                if oao.etp is not None:
                    org_defaults['etp_realise'] = _q(_dec(oao.etp) * ratio)
            RealisationOperationAnneeOrganisme.objects.update_or_create(
                id_operation_annee_organisme=oao, defaults=org_defaults,
            )

        # Temps de travail réalisé : miroir des lignes prévues, au même ratio.
        RealisationOperationAnneeRH.objects.filter(
            id_realisation_operation_annee=realisation,
        ).delete()
        for ligne in lignes_prev:
            RealisationOperationAnneeRH.objects.create(
                id_realisation_operation_annee=realisation,
                id_operation_annee_rh=ligne,
                id_poste=ligne.id_poste,
                id_organisme=ligne.id_organisme,
                jours=_q(_dec(ligne.jours) * ratio),
                categorie_depense=ligne.categorie_depense,
                finance=ligne.finance,
            )

    # ------------------------------------------------------------------ reset

    def reset(self) -> int:
        codes = [
            f"{VENTILATION_OP_CODE_PREFIX}{suffix}-{action['suffix']}"
            for _mode, _libelle, suffix in _MODES
            for action in _ACTIONS
        ]
        count = Operation.objects.filter(code_operation__in=codes).delete()[0]
        count += PlanGestion.objects.filter(nom__startswith=_PLAN_PREFIX).delete()[0]
        return count

    def get_dry_run_summary(self) -> List[str]:
        return [
            '\nPlans « Ventilation » (1 par mode de ventilation) :',
            f'  - {len(_MODES)} plans en brouillon sur le site {_SITE_KEYWORD}, '
            "années : année courante −2 → +2",
            f'  - {len(_MODES)} × 1 enjeu → OLT → NE → indicateur → métrique',
            f'  - {len(_MODES) * len(_ACTIONS)} actions programmées '
            '(budget, temps de travail, suivi de réalisation)',
            f'  - {len(_MODES) * len(_POSTES)} postes (dont bénévoles et prestataire)',
        ]
