"""
Planification annuelle ajustée (#794) — règles partagées.

Le plan de gestion fixe la programmation de référence de chaque action
(``OperationAnnee``). Chaque année, le gestionnaire revoit chaque action et en
ajuste la programmation de l'année (``AjustementAnnuel``) sans modifier le plan.

Règles :

- **Prévu effectif** d'une année : l'ajustement s'il existe, sinon la
  programmation du plan de gestion. Une année « non prévue » ou « reportée »
  n'a pas de moyens.
- **Report** d'une année N vers N+k : toute la suite de la programmation est
  décalée de k ans (moyens et mois), ajustée ou non. Une année où du réalisé
  est saisi n'est jamais déplacée ni écrasée ; ce qui tombe après la fin du
  plan (prolongation comprise) est abandonné. Un aperçu précède l'écriture.
- **Report partiel** : l'année N reste planifiée ; l'année cible reçoit, en
  plus de son propre prévu, le reste à faire de N (prévu N − réalisé N). La
  suite n'est pas décalée.
- **Réalisation en avance** : rien n'est décalé ; l'année est simplement
  planifiée.
- **Revue** : enregistrer l'ajustement d'une action pour une année, même sans
  rien changer, la marque revue.

Un « contenu » est un ``dict`` de même forme que la programmation d'une année
(champs de ``OperationAnnee``, ``organismes``, ``rh_lignes``) plus le statut,
les mois et les financeurs : il passe tel quel d'une année à l'autre et vers
l'API.
"""
from copy import deepcopy
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models_operations import (
    FinanceOperation, OperationAnnee, Poste, RealisationOperationAnnee,
)
from .models_planification import (
    CHAMPS_COMMENTAIRES_COUTS, CHAMPS_COUTS_ANNEE, CHAMPS_COUTS_ORGANISME,
    AjustementAnnuel, AjustementAnnuelFinanceur, AjustementAnnuelOrganisme,
    AjustementAnnuelRH, StatutAnnuel,
)
from .services_export_finance import (
    CostCell, _d, ajouter_couts_annee_prevu, ajouter_couts_organisme_prevu,
    ajouter_temps_prevu, regles_salaire_prevu,
)

PLANIFIEE, NON_PREVUE, REPORTEE = (
    StatutAnnuel.PLANIFIEE, StatutAnnuel.NON_PREVUE, StatutAnnuel.REPORTEE)
NIVEAU_REPORTE = 'REPORTE'
MOIS = tuple(str(m) for m in range(1, 13))

# Champ réalisé correspondant à chaque champ prévu (année et organisme).
_REALISE = {champ: f'{champ}_realise' for champ in CHAMPS_COUTS_ANNEE}


class ReportImpossible(Exception):
    """Report refusé : ``code`` est renvoyé à l'interface avec le message."""

    def __init__(self, message, code):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Lecture par les vues de suivi et les exports
# ---------------------------------------------------------------------------

def ajustements_par_annee(operation_ids):
    """{(id_operation, année): AjustementAnnuel} des actions données, avec
    organismes et lignes de temps (prêts pour ``build_action_finance`` et le
    Bilan)."""
    return {
        (aj.id_operation_id, aj.annee): aj for aj in
        AjustementAnnuel.objects.filter(id_operation__in=list(operation_ids))
        .prefetch_related('organismes__id_organisme', 'rh_lignes__id_poste__id_organisme',
                          'rh_lignes__id_organisme')
    }


def est_planifiee(oa, ajustements):
    """Année ``oa`` (du plan) planifiée selon la planification ajustée."""
    ajustement = ajustements.get((oa.id_operation_id, oa.annee))
    if ajustement is not None:
        return ajustement.statut == PLANIFIEE
    return bool(oa.periodicite)


def prevu_de(oa, ajustements):
    """Ce qui porte le prévu de l'année : l'ajustement planifié, l'année du
    plan sans ajustement, ``None`` pour une année ajustée non prévue ou
    reportée. L'ajustement a les mêmes champs qu'une année du plan."""
    ajustement = ajustements.get((oa.id_operation_id, oa.annee))
    if ajustement is None:
        return oa
    return ajustement if ajustement.statut == PLANIFIEE else None


# ---------------------------------------------------------------------------
# Contenus
# ---------------------------------------------------------------------------

def contenu_vide(statut=NON_PREVUE):
    contenu = {
        'statut': statut, 'annee_report': None, 'report_de': None,
        'periodicite_mensuelle': {}, 'commentaire': '',
        'organismes': [], 'rh_lignes': [], 'financeurs': [],
    }
    contenu.update({champ: None for champ in CHAMPS_COUTS_ANNEE})
    contenu.update({champ: '' for champ in CHAMPS_COMMENTAIRES_COUTS})
    return contenu


def _mois(valeur):
    valeur = valeur or {}
    return {m: bool(valeur.get(m)) for m in MOIS if valeur.get(m)}


def _organisme(ligne):
    donnees = {'id_organisme': ligne.id_organisme_id}
    for champ in CHAMPS_COUTS_ORGANISME + CHAMPS_COMMENTAIRES_COUTS:
        donnees[champ] = getattr(ligne, champ)
    return donnees


def _rh(ligne):
    return {
        'id_poste': ligne.id_poste_id, 'id_organisme': ligne.id_organisme_id,
        'jours': ligne.jours, 'finance': ligne.finance,
        'categorie_depense': ligne.categorie_depense,
    }


def _remplir(contenu, source):
    for champ in CHAMPS_COUTS_ANNEE + CHAMPS_COMMENTAIRES_COUTS:
        contenu[champ] = getattr(source, champ)
    contenu['organismes'] = [_organisme(x) for x in source.organismes.all()]
    contenu['rh_lignes'] = [_rh(x) for x in source.rh_lignes.all()]
    return contenu


def contenu_pg(oa):
    """Programmation du plan de gestion pour une année (``OperationAnnee`` ou None)."""
    if oa is None:
        return contenu_vide()
    contenu = contenu_vide(PLANIFIEE if oa.periodicite else NON_PREVUE)
    contenu['periodicite_mensuelle'] = _mois(oa.periodicite_mensuelle)
    return _remplir(contenu, oa)


def contenu_ajuste(ajustement):
    contenu = contenu_vide(ajustement.statut)
    contenu.update(
        annee_report=ajustement.annee_report, report_de=ajustement.report_de,
        periodicite_mensuelle=_mois(ajustement.periodicite_mensuelle),
        commentaire=ajustement.commentaire or '')
    _remplir(contenu, ajustement)
    contenu['financeurs'] = [
        {'id_financeur': f.id_financeur_id, 'montant': f.montant}
        for f in ajustement.financeurs.all()]
    return contenu


def sans_moyens(contenu):
    """Une année non prévue ou reportée ne porte ni moyens ni mois."""
    vide = contenu_vide(contenu['statut'])
    vide.update(annee_report=contenu.get('annee_report'), report_de=contenu.get('report_de'),
                commentaire=contenu.get('commentaire') or '')
    return vide


def _somme(a, b):
    if a is None and b is None:
        return None
    return _d(a) + _d(b)


def _reste(prevu, realise):
    if prevu is None:
        return None
    return max(_d(prevu) - _d(realise), Decimal('0'))


def _cle_rh(ligne):
    return (ligne['id_poste'], ligne['id_organisme'], ligne.get('categorie_depense') or '')


def additionner(base, ajout):
    """Prévu ``base`` augmenté de ``ajout`` (report partiel reçu)."""
    total = deepcopy(base)
    for champ in CHAMPS_COUTS_ANNEE:
        total[champ] = _somme(base[champ], ajout[champ])
    organismes = {o['id_organisme']: o for o in total['organismes']}
    for org in ajout['organismes']:
        cible = organismes.get(org['id_organisme'])
        if cible is None:
            total['organismes'].append(deepcopy(org))
            continue
        for champ in CHAMPS_COUTS_ORGANISME:
            cible[champ] = _somme(cible[champ], org[champ])
    lignes = {_cle_rh(x): x for x in total['rh_lignes']}
    for ligne in ajout['rh_lignes']:
        cible = lignes.get(_cle_rh(ligne))
        if cible is None:
            total['rh_lignes'].append(deepcopy(ligne))
        else:
            cible['jours'] = _somme(cible['jours'], ligne['jours'])
    financeurs = {f['id_financeur']: f for f in total['financeurs']}
    for fin in ajout['financeurs']:
        cible = financeurs.get(fin['id_financeur'])
        if cible is None:
            total['financeurs'].append(deepcopy(fin))
        else:
            cible['montant'] = _somme(cible['montant'], fin['montant'])
    if not total['periodicite_mensuelle']:
        total['periodicite_mensuelle'] = dict(ajout['periodicite_mensuelle'])
    return total


def mois_actifs(contenu):
    return [int(m) for m in MOIS if contenu['periodicite_mensuelle'].get(m)]


# ---------------------------------------------------------------------------
# Coûts — mêmes règles que les exports (services_export_finance)
# ---------------------------------------------------------------------------

def couts(op, contenu, postes, avec_organismes):
    """``CostCell`` du prévu d'un contenu.

    ``postes`` : {id_poste: Poste} du plan (coût jour) ; ``avec_organismes`` :
    l'action porte ses montants par organisme (règle des exports : des lignes
    par organisme dans la programmation)."""
    auto_salary, manual_salary = regles_salaire_prevu(op)
    cellule = CostCell()
    for ligne in contenu['rh_lignes']:
        poste = postes.get(ligne['id_poste'])
        cout_jour = _d(getattr(poste, 'cout_jour', None)) if poste else Decimal('0')
        ajouter_temps_prevu(cellule, _Objet(ligne), cout_jour, auto_salary)
    if avec_organismes or contenu['organismes']:
        for org in contenu['organismes']:
            ajouter_couts_organisme_prevu(cellule, _Objet(org), manual_salary)
    else:
        ajouter_couts_annee_prevu(cellule, op, _Objet(contenu), manual_salary)
    return cellule


class _Objet:
    """Accès par attribut à un dict (champ absent → None)."""

    def __init__(self, donnees):
        self._donnees = donnees

    def __getattr__(self, nom):
        return self._donnees.get(nom)


def resume(op, contenu, postes, avec_organismes):
    cellule = couts(op, contenu, postes, avec_organismes)
    return {
        'statut': contenu['statut'],
        'annee_report': contenu.get('annee_report'),
        'report_de': contenu.get('report_de'),
        'mois': mois_actifs(contenu),
        'budget': cellule.tot,
        'budget_fonctionnement': cellule.tot_fonct,
        'budget_investissement': cellule.tot_invest,
        'jours': cellule.jours + cellule.j_benevole,
        'jours_benevole': cellule.j_benevole,
        'financeurs': sum((_d(f['montant']) for f in contenu['financeurs']), Decimal('0')),
    }


def _comparable(contenu):
    """Ce qui compte pour dire si un ajustement « diverge » du plan."""
    def _num(v):
        return None if v in (None, '') else _d(v)
    return (
        contenu['statut'], tuple(mois_actifs(contenu)),
        tuple(_num(contenu[c]) for c in CHAMPS_COUTS_ANNEE),
        tuple(sorted(
            (o['id_organisme'],) + tuple(_num(o[c]) for c in CHAMPS_COUTS_ORGANISME)
            for o in contenu['organismes'])),
        tuple(sorted((_cle_rh(x), _num(x['jours'])) for x in contenu['rh_lignes']
                     if _num(x['jours']))),
    )


def identiques(a, b):
    """Deux contenus de même statut, mois, moyens, financeurs et reports."""
    def _fin(contenu):
        return tuple(sorted((f['id_financeur'], None if f['montant'] in (None, '') else _d(f['montant']))
                            for f in contenu['financeurs']))
    return (_comparable(a) == _comparable(b) and _fin(a) == _fin(b)
            and a.get('annee_report') == b.get('annee_report')
            and a.get('report_de') == b.get('report_de'))


# ---------------------------------------------------------------------------
# Lecture groupée
# ---------------------------------------------------------------------------

class Planification:
    """Programmation de référence, ajustements et réalisé des actions d'un plan."""

    def __init__(self, plan, operations):
        self.plan = plan
        self.operations = {op.id_operation: op for op in operations}
        ids = list(self.operations)
        self.postes = {
            p.id_poste: p for p in Poste.objects.filter(id_pg=plan)
            .select_related('id_organisme').prefetch_related('fonctions__id_fonction')}
        self._pg = {}
        for oa in (OperationAnnee.objects.filter(id_operation__in=ids)
                   .prefetch_related('organismes__realisation', 'rh_lignes')):
            self._pg[(oa.id_operation_id, oa.annee)] = oa
        self._globales = {
            oa.id_operation_id: oa for oa in
            OperationAnnee.tous.filter(id_operation__in=ids, annee__isnull=True)
            .prefetch_related('organismes', 'rh_lignes')}
        self._ajustements = {
            (aj.id_operation_id, aj.annee): aj for aj in
            AjustementAnnuel.objects.filter(id_operation__in=ids)
            .select_related('id_utilisateur_revue')
            .prefetch_related('organismes', 'rh_lignes', 'financeurs')}
        self._realises = {
            (r.id_operation_annee.id_operation_id, r.id_operation_annee.annee): r
            for r in RealisationOperationAnnee.objects
            .filter(id_operation_annee__id_operation__in=ids)
            .select_related('id_operation_annee', 'id_niveau_realisation')
            .prefetch_related('rh_lignes', 'financeurs')}
        self._avec_organismes = set(
            OperationAnnee.tous.filter(id_operation__in=ids, organismes__isnull=False)
            .values_list('id_operation', flat=True))

    @classmethod
    def pour_action(cls, operation):
        return cls(operation.get_plan_de_gestion(), [operation])

    # --- Bornes -----------------------------------------------------------
    @property
    def annees(self):
        return self.plan.annees_plan()

    @property
    def annee_fin(self):
        return self.plan.annee_fin_effective

    # --- Lectures par (action, année) --------------------------------------
    def operation_annee(self, op_id, annee):
        return self._pg.get((op_id, annee))

    def annee_globale(self, op_id):
        return self._globales.get(op_id)

    def ajustement(self, op_id, annee):
        return self._ajustements.get((op_id, annee))

    def realisation(self, op_id, annee):
        return self._realises.get((op_id, annee))

    def pg(self, op_id, annee):
        return contenu_pg(self.operation_annee(op_id, annee))

    def effectif(self, op_id, annee):
        ajustement = self.ajustement(op_id, annee)
        if ajustement is None:
            return self.pg(op_id, annee)
        contenu = contenu_ajuste(ajustement)
        return contenu if contenu['statut'] == PLANIFIEE else sans_moyens(contenu)

    def avec_organismes(self, op_id):
        return op_id in self._avec_organismes

    def resume(self, op_id, contenu):
        return resume(self.operations[op_id], contenu, self.postes, self.avec_organismes(op_id))

    def diverge(self, op_id, annee):
        """L'année ajustée s'écarte du plan de gestion (statut, mois ou moyens)."""
        if self.ajustement(op_id, annee) is None:
            return False
        return _comparable(self.effectif(op_id, annee)) != _comparable(self.pg(op_id, annee))

    def annee_fixee(self, op_id, annee):
        """Du réalisé est saisi cette année (hors niveau « Reporté »)."""
        realisation = self.realisation(op_id, annee)
        if realisation is None:
            return False
        niveau = realisation.id_niveau_realisation
        return not (niveau is not None and niveau.mnemonique == NIVEAU_REPORTE)

    def reports_entrants(self, op_id, annee):
        """Années dont l'action a été reportée (en tout ou partie) sur ``annee``."""
        entrants = []
        for (op, origine), ajustement in sorted(self._ajustements.items()):
            if op != op_id or origine >= annee or ajustement.annee_report != annee:
                continue
            entrants.append({
                'annee': origine, 'partiel': ajustement.statut != REPORTEE})
        return entrants

    def reste_a_faire(self, op_id, annee):
        """Prévu effectif de l'année moins son réalisé, champ par champ (≥ 0)."""
        prevu = self.effectif(op_id, annee)
        realisation = self.realisation(op_id, annee)
        reste = contenu_vide(PLANIFIEE)
        reste['periodicite_mensuelle'] = dict(prevu['periodicite_mensuelle'])
        for champ in CHAMPS_COUTS_ANNEE:
            reste[champ] = _reste(prevu[champ], getattr(realisation, _REALISE[champ], None))
        oa = self.operation_annee(op_id, annee)
        realise_org = {}
        if oa is not None:
            for ligne in oa.organismes.all():
                realise_org[ligne.id_organisme_id] = getattr(ligne, 'realisation', None)
        for org in prevu['organismes']:
            fait = realise_org.get(org['id_organisme'])
            ligne = {'id_organisme': org['id_organisme']}
            for champ in CHAMPS_COUTS_ORGANISME:
                ligne[champ] = _reste(org[champ], getattr(fait, _REALISE[champ], None))
            for champ in CHAMPS_COMMENTAIRES_COUTS:
                ligne[champ] = org[champ]
            reste['organismes'].append(ligne)
        jours_faits = {}
        for ligne in (realisation.rh_lignes.all() if realisation else []):
            cle = (ligne.id_poste_id, ligne.id_organisme_id, ligne.categorie_depense or '')
            jours_faits[cle] = jours_faits.get(cle, Decimal('0')) + _d(ligne.jours)
        for ligne in prevu['rh_lignes']:
            jours = _reste(ligne['jours'], jours_faits.get(_cle_rh(ligne)))
            if jours:
                reste['rh_lignes'].append(dict(ligne, jours=jours))
        finance = {}
        for ligne in (realisation.financeurs.all() if realisation else []):
            finance[ligne.id_financeur_id] = _d(ligne.montant)
        for fin in prevu['financeurs']:
            montant = _reste(fin['montant'], finance.get(fin['id_financeur']))
            if montant:
                reste['financeurs'].append({'id_financeur': fin['id_financeur'], 'montant': montant})
        return reste

    # --- Report ----------------------------------------------------------
    def _controler_report(self, op_id, annee, annee_report):
        if annee not in self.annees:
            raise ReportImpossible("Cette année n'appartient pas au plan de gestion.",
                                   'annee_hors_plan')
        if annee_report is None or annee_report <= annee:
            raise ReportImpossible("Une action se reporte sur une année suivante.",
                                   'annee_report_invalide')
        if annee_report > self.annee_fin:
            raise ReportImpossible(
                f"Le plan de gestion s'arrête en {self.annee_fin} (prolongation comprise).",
                'annee_report_hors_plan')
        source = self.effectif(op_id, annee)
        if source['statut'] != PLANIFIEE:
            raise ReportImpossible("Seule une action planifiée cette année peut être reportée.",
                                   'action_non_planifiee')
        if source.get('annee_report') is not None:
            raise ReportImpossible(
                f"L'action est déjà reportée en {source['annee_report']} pour cette année.",
                'deja_reportee')
        if self.effectif(op_id, annee_report)['statut'] == REPORTEE:
            raise ReportImpossible(
                f"En {annee_report}, l'action est elle-même reportée : choisir une autre année.",
                'annee_cible_reportee')
        return source

    def apercu_report(self, op_id, annee, annee_report, partiel=False):
        """Avant / après d'un report, sans rien écrire.

        Rend ``{'annees': [...], 'deplacements': [...], 'abandonnees': [...],
        'contenus': {annee: contenu après}}`` — ``contenus`` ne sert qu'à
        l'écriture (``reporter``)."""
        source = self._controler_report(op_id, annee, annee_report)
        annees = [a for a in self.annees if a >= annee]
        avant = {a: self.effectif(op_id, a) for a in annees}
        apres = {a: deepcopy(c) for a, c in avant.items()}
        deplacements, abandonnees = [], []
        fixes = set()

        if partiel:
            apres[annee]['annee_report'] = annee_report
            recu = additionner(self.effectif(op_id, annee_report), self.reste_a_faire(op_id, annee))
            recu.update(statut=PLANIFIEE, report_de=annee, annee_report=None)
            apres[annee_report] = recu
        else:
            # Années qui ne bougent pas et ne reçoivent rien : réalisé saisi, ou
            # déjà reportées ailleurs (une décision antérieure à ne pas écraser).
            fixes = {a for a in annees if a > annee and (
                self.annee_fixee(op_id, a) or avant[a]['statut'] == REPORTEE)}
            if annee_report in fixes:
                raise ReportImpossible(
                    f"Du réalisé est déjà saisi en {annee_report} : l'action ne peut pas "
                    "y être reportée en totalité.", 'annee_cible_suivie')
            sources = [annee] + [a for a in annees if a > annee and a not in fixes
                                 and avant[a]['statut'] == PLANIFIEE]
            for a in sources:
                apres[a] = contenu_vide()
            apres[annee] = contenu_vide(REPORTEE)
            apres[annee]['annee_report'] = annee_report
            apres[annee]['commentaire'] = source.get('commentaire') or ''
            decalage, derniere = annee_report - annee, None
            for a in sources:
                cible = a + decalage
                if derniere is not None and cible <= derniere:
                    cible = derniere + 1
                while cible in fixes:
                    cible += 1
                if cible > self.annee_fin:
                    abandonnees.append({'annee': a, 'resume': self.resume(op_id, avant[a])})
                    continue
                contenu = deepcopy(avant[a])
                contenu.update(statut=PLANIFIEE, annee_report=None,
                               report_de=annee if a == annee else avant[a].get('report_de'))
                if a == annee:
                    contenu['commentaire'] = ''
                apres[cible] = contenu
                deplacements.append({'de': a, 'vers': cible})
                derniere = cible

        lignes = []
        for a in annees:
            lignes.append({
                'annee': a,
                'avant': self.resume(op_id, avant[a]),
                'apres': self.resume(op_id, apres[a]),
                'fixe': a in fixes,
                'modifiee': not identiques(avant[a], apres[a]),
            })
        return {
            'annee': annee, 'annee_report': annee_report, 'partiel': partiel,
            'annees': lignes, 'deplacements': deplacements, 'abandonnees': abandonnees,
            'contenus': {x['annee']: apres[x['annee']] for x in lignes if x['modifiee']},
        }

    @transaction.atomic
    def reporter(self, op_id, annee, annee_report, user, partiel=False):
        """Applique le report (aperçu recalculé) ; l'année d'origine est marquée revue."""
        apercu = self.apercu_report(op_id, annee, annee_report, partiel=partiel)
        operation = self.operations[op_id]
        for a, contenu in apercu['contenus'].items():
            ecrire(operation, a, contenu, user, revue=(a == annee),
                   ajustement=self.ajustement(op_id, a))
        return apercu


# ---------------------------------------------------------------------------
# Écriture
# ---------------------------------------------------------------------------

def _decimal(valeur):
    return None if valeur in (None, '') else Decimal(str(valeur))


@transaction.atomic
def ecrire(operation, annee, contenu, user, revue=True, ajustement=None):
    """Enregistre ``contenu`` comme ajustement de l'année (lignes filles
    remplacées). ``revue`` : l'action est marquée revue pour l'année ; sinon la
    revue existante tombe (le contenu a changé sans que l'année soit revue)."""
    if ajustement is None:
        ajustement = AjustementAnnuel.objects.filter(id_operation=operation, annee=annee).first()
    if ajustement is None:
        ajustement = AjustementAnnuel(id_operation=operation, annee=annee)
    if contenu['statut'] != PLANIFIEE:
        contenu = sans_moyens(contenu)
    ajustement.statut = contenu['statut']
    ajustement.annee_report = contenu.get('annee_report')
    ajustement.report_de = contenu.get('report_de')
    ajustement.periodicite_mensuelle = _mois(contenu.get('periodicite_mensuelle'))
    ajustement.commentaire = contenu.get('commentaire') or ''
    for champ in CHAMPS_COUTS_ANNEE:
        setattr(ajustement, champ, _decimal(contenu.get(champ)))
    for champ in CHAMPS_COMMENTAIRES_COUTS:
        setattr(ajustement, champ, contenu.get(champ) or '')
    ajustement.id_utilisateur_maj = user
    if revue:
        ajustement.date_revue = timezone.now()
        ajustement.id_utilisateur_revue = user
    else:
        ajustement.date_revue = None
        ajustement.id_utilisateur_revue = None
    ajustement.save()

    ajustement.organismes.all().delete()
    for org in contenu.get('organismes') or []:
        donnees = {champ: _decimal(org.get(champ)) for champ in CHAMPS_COUTS_ORGANISME}
        donnees.update({champ: org.get(champ) or '' for champ in CHAMPS_COMMENTAIRES_COUTS})
        AjustementAnnuelOrganisme.objects.create(
            id_ajustement_annuel=ajustement, id_organisme_id=org['id_organisme'], **donnees)
    ajustement.rh_lignes.all().delete()
    for ligne in contenu.get('rh_lignes') or []:
        AjustementAnnuelRH.objects.create(
            id_ajustement_annuel=ajustement, id_poste_id=ligne.get('id_poste'),
            id_organisme_id=ligne.get('id_organisme'), jours=_decimal(ligne.get('jours')),
            finance=ligne.get('finance', True),
            categorie_depense=ligne.get('categorie_depense') or '')
    ajustement.financeurs.all().delete()
    for fin in contenu.get('financeurs') or []:
        AjustementAnnuelFinanceur.objects.create(
            id_ajustement_annuel=ajustement, id_financeur_id=fin['id_financeur'],
            montant=_decimal(fin.get('montant')))
    return ajustement


def financeurs_pg(operation):
    """Financeurs prévus par le plan de gestion, montant global sur l'action (#790)."""
    return [
        {'id_financeur': f.id_financeur_id, 'nom': f.id_financeur.nom if f.id_financeur_id else f.libelle,
         'montant': f.montant}
        for f in FinanceOperation.objects.filter(id_operation=operation)
        .select_related('id_financeur').order_by('libelle')
    ]
