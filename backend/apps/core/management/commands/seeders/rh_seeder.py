"""
Seeder RH (#560) — postes, fonctions et lignes de temps de travail.

Enrichit le plan de gestion « Lacs et zones humides continentales » (créé par
MinimalPlansSeeder) avec des **postes** (aucun nominatif, RGPD) et des lignes
de temps de travail prévisionnel — et réalisé quand un suivi existe.

Les postes couvrent volontairement les cas de figure du modèle :
  - poste simple (1 fonction, 1 ETP) ;
  - poste **combiné sans quotité** : un « garde animateur » à 1 ETP cumule les
    deux casquettes sur tout son temps ;
  - poste à **quotités explicites** (50 % / 50 %) ;
  - poste en **plusieurs exemplaires** (3 stagiaires pour 1,5 ETP au total) ;
  - poste **non financé** (bénévoles).

Les actions couvrent les trois façons de saisir la RH :
  - `declinaison_par_poste=True` → une ligne par poste ;
  - ventilation budgétaire par organisme → une ligne par organisme ;
  - ni l'un ni l'autre → aucune ligne (la saisie RH est alors facultative).
"""
from decimal import Decimal

from django.db.models import Q

from apps.plans.models import PlanGestion
from apps.plans.models_operations import (
    Operation, OperationAnnee, OperationAnneeOrganisme, OperationAnneeRH,
    RealisationOperationAnneeRH,
    Fonction, Poste, PosteFonction,
)
from apps.users.models import BibOrganismes

from .base import BaseSeeder


_PLAN_SLUG = 'plan-de-gestion-2023-2033-lacs-et-zones-humides-continentales'

# Postes du PG : (clé, organisme, nombre, ETP total, [(fonction, quotité %)]).
# Quotité None = le poste cumule ses fonctions sur l'ensemble de son temps.
_POSTES = [
    ('conservateur', 'Réserves Naturelles de France', 1, '1.00',
     [('Conservateur', None)]),
    # Le cas « garde animateur » : deux casquettes, 1 ETP, pas de quotité.
    ('garde_animateur', 'Réserves Naturelles de France', 1, '1.00',
     [('Garde-technicien', None), ('Animateur nature', None)]),
    # Le même métier, mais avec une répartition explicite du temps.
    ('anim_com', 'CEN Auvergne-Rhône-Alpes', 1, '1.00',
     [('Animateur nature', '50.00'), ('Chargé de communication', '50.00')]),
    # Plusieurs exemplaires du même poste, pour une enveloppe d'ETP commune.
    ('stagiaires', 'CEN Auvergne-Rhône-Alpes', 3, '1.50',
     [('Stagiaire', None)]),
    ('service_civique', 'CEN Auvergne-Rhône-Alpes', 2, '2.00',
     [('Service civique', None)]),
    # Temps non financé — la valorisation visée par #560.
    ('benevoles', 'Réserves Naturelles de France', 10, '0.50',
     [('Bénévole', None)]),
]

# Fonctions non financées par défaut (cohérent avec le socle #560).
_NON_FINANCEES = {'bénévole', 'écovolontaire', 'partenaire'}

# Type de poste par défaut d'après le libellé de la fonction (#596).
_TYPE_PAR_LIBELLE = [
    ('stagiaire', Fonction.TYPE_STAGIAIRE),
    ('service civique', Fonction.TYPE_STAGIAIRE),
    ('bénévole', Fonction.TYPE_BENEVOLE),
    ('écovolontaire', Fonction.TYPE_BENEVOLE),
    ('prestataire', Fonction.TYPE_PRESTATAIRE),
]

# Coût jour indicatif par type de poste (€), pour rendre visible le calcul du
# coût salarial (#596). Un prestataire n'a pas de coût jour (None).
_COUT_JOUR_PAR_TYPE = {
    Fonction.TYPE_SALARIE: Decimal('300.00'),
    Fonction.TYPE_STAGIAIRE: Decimal('80.00'),
    Fonction.TYPE_BENEVOLE: Decimal('0.00'),
    Fonction.TYPE_PRESTATAIRE: None,
}

# Répartition des jours par poste, variée d'une action à l'autre.
_VARIANTES_POSTES = [
    [('conservateur', '8', True), ('garde_animateur', '12', True), ('benevoles', '5', False)],
    [('anim_com', '6', True), ('service_civique', '10', True)],
    [('garde_animateur', '15', True)],
    [('conservateur', '4', True), ('stagiaires', '20', True), ('benevoles', '8', False)],
]

# Jours par organisme, pour les actions ventilées par organisme.
_VARIANTES_ORGANISMES = [
    [('9', True), ('6', True)],
    [('12', True), ('3', False)],
    [('7', True)],
]


class RhSeeder(BaseSeeder):
    name = 'rh'
    dependencies = ['minimal_plans', 'realisations']

    def seed(self) -> dict:
        self.log_header('Ressources humaines (#560)')
        plan = PlanGestion.objects.filter(slug=_PLAN_SLUG).first()
        if not plan:
            self.log('Plan zones humides introuvable, RH ignoré.', 'WARNING')
            return {'postes': 0, 'lignes_prev': 0, 'lignes_reel': 0}

        postes = self._seed_postes(plan)

        operations = self._plan_operations(plan)
        lignes_prev = 0
        lignes_reel = 0
        nb_declinees = 0
        for idx, op in enumerate(operations):
            # Une action sur trois détaille sa RH poste par poste ; les autres
            # s'appuient sur la ventilation budgétaire par organisme.
            declinee = idx % 3 == 0
            par_organisme = not declinee and op.ventilation_mode in ('by_org', 'by_org_type')
            if op.declinaison_par_poste != declinee:
                op.declinaison_par_poste = declinee
                op.save(update_fields=['declinaison_par_poste'])
            if declinee:
                nb_declinees += 1

            for oa in OperationAnnee.objects.filter(id_operation=op):
                # Remplace les lignes génériques issues de la migration #560.
                OperationAnneeRH.objects.filter(id_operation_annee=oa).delete()
                if declinee:
                    lignes = self._lignes_postes(idx, postes)
                elif par_organisme:
                    lignes = self._lignes_organismes(idx, oa)
                else:
                    # Ni déclinaison ni ventilation par organisme : la saisie RH
                    # est facultative et le tableau n'est pas affiché.
                    lignes = []

                prevues = [
                    OperationAnneeRH.objects.create(id_operation_annee=oa, **ligne)
                    for ligne in lignes
                ]
                lignes_prev += len(prevues)

                # Réel : quand un suivi de l'année existe, saisir ~85 % du prévu.
                real = getattr(oa, 'realisation', None)
                if real is None:
                    continue
                RealisationOperationAnneeRH.objects.filter(
                    id_realisation_operation_annee=real
                ).delete()
                for prevue, ligne in zip(prevues, lignes):
                    reel = dict(ligne)
                    if reel['jours'] is not None:
                        reel['jours'] = round(reel['jours'] * Decimal('0.85'), 2)
                    RealisationOperationAnneeRH.objects.create(
                        id_realisation_operation_annee=real,
                        # Le réel réalise la ligne prévue correspondante :
                        # sans ce lien il remonterait en « non prévu ».
                        id_operation_annee_rh=prevue,
                        **reel,
                    )
                    lignes_reel += 1

        self.log_summary(len(postes), 'postes créés')
        self.log_summary(nb_declinees, 'actions déclinées par poste')
        self.log_summary(lignes_prev, 'lignes RH prévisionnelles créées')
        self.log_summary(lignes_reel, 'lignes RH réalisées créées')
        return {
            'postes': len(postes),
            'lignes_prev': lignes_prev,
            'lignes_reel': lignes_reel,
        }

    def _seed_postes(self, plan) -> dict:
        """Crée les postes du PG (idempotent) et retourne {clé: Poste}."""
        # Les postes n'ont pas de nom : on les ré-identifie par leur rang,
        # d'où une purge préalable plutôt qu'un get_or_create.
        Poste.objects.filter(id_pg=plan).delete()
        postes = {}
        for cle, org_nom, nombre, etp, fonctions in _POSTES:
            poste = Poste.objects.create(
                id_pg=plan,
                id_organisme=self._get_organisme(org_nom),
                nombre=nombre,
                etp=Decimal(etp),
            )
            for libelle, pct in fonctions:
                PosteFonction.objects.create(
                    id_poste=poste,
                    id_fonction=self._get_fonction(libelle),
                    pourcentage=Decimal(pct) if pct is not None else None,
                )
            # Coût jour indicatif d'après le type de la 1re fonction (#596).
            first = poste.fonctions.first()
            if first:
                poste.cout_jour = _COUT_JOUR_PAR_TYPE.get(
                    first.id_fonction.type_poste, Decimal('300.00')
                )
                poste.save(update_fields=['cout_jour'])
            postes[cle] = poste
        return postes

    def _lignes_postes(self, idx, postes) -> list:
        """Lignes RH d'une action déclinée par poste."""
        variante = _VARIANTES_POSTES[idx % len(_VARIANTES_POSTES)]
        return [
            dict(id_poste=postes[cle], id_organisme=None,
                 jours=Decimal(jours), finance=finance)
            for cle, jours, finance in variante
        ]

    def _lignes_organismes(self, idx, oa) -> list:
        """Lignes RH d'une action dont le budget est ventilé par organisme."""
        organismes = [
            oao.id_organisme
            for oao in OperationAnneeOrganisme.objects.filter(
                id_operation_annee=oa
            ).select_related('id_organisme')
        ]
        variante = _VARIANTES_ORGANISMES[idx % len(_VARIANTES_ORGANISMES)]
        return [
            dict(id_poste=None, id_organisme=organisme,
                 jours=Decimal(jours), finance=finance)
            for organisme, (jours, finance) in zip(organismes, variante)
        ]

    def _get_organisme(self, nom):
        return BibOrganismes.objects.filter(nom_organisme=nom).first()

    def _get_fonction(self, libelle):
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
            finance_par_defaut=libelle.lower() not in _NON_FINANCEES,
            is_socle=False,
        )

    def _plan_operations(self, plan):
        return list(
            Operation.objects.filter(
                Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan)
                | Q(id_suivi__id_pg=plan)
            ).distinct().order_by('id_operation')
        )

    def reset(self) -> int:
        plan = PlanGestion.objects.filter(slug=_PLAN_SLUG).first()
        if not plan:
            return 0
        count = 0
        for op in self._plan_operations(plan):
            if op.declinaison_par_poste:
                op.declinaison_par_poste = False
                op.save(update_fields=['declinaison_par_poste'])
            for oa in OperationAnnee.objects.filter(id_operation=op):
                count += OperationAnneeRH.objects.filter(id_operation_annee=oa).delete()[0]
                real = getattr(oa, 'realisation', None)
                if real is not None:
                    count += RealisationOperationAnneeRH.objects.filter(
                        id_realisation_operation_annee=real
                    ).delete()[0]
        count += Poste.objects.filter(id_pg=plan).delete()[0]
        return count

    def get_dry_run_summary(self) -> list:
        return [
            f'{len(_POSTES)} postes sur le plan « Lacs et zones humides continentales » '
            '(dont un garde animateur combiné, un poste à quotités 50/50, '
            '3 stagiaires pour 1,5 ETP et des bénévoles non financés)',
            'lignes RH prévisionnelles (et réalisées) par poste ou par organisme '
            'selon le mode de saisie de chaque action',
        ]
