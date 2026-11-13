"""Un seul suivi par rang : il suit le plan d'une version à l'autre (#803).

Une nouvelle version d'un plan **au même rang** (modification, prolongation,
évaluation à mi-parcours) est le même plan de gestion, qui continue. Son suivi
ne vit donc qu'à un endroit : sur la dernière version validée du rang.

- Pendant la rédaction de la nouvelle version (brouillon), on continue de
  saisir le suivi sur la version en vigueur.
- À la **validation** de la nouvelle version, tout le suivi déjà saisi sur les
  versions antérieures du même rang y est **déplacé** (pas copié : aucune
  donnée en double) — :func:`transferer_suivi`. Ces versions sont marquées
  ``suivi_poursuivi_dans`` : leur suivi n'est plus modifiable, leurs pages de
  suivi renvoient vers la version qui le porte.
- Supprimer la version qui porte le suivi le rend à la version précédente du
  rang (:func:`rendre_suivi`) au lieu de l'emporter dans la cascade.

Ce qui se déplace : par action, la réalisation annuelle (niveau, budget, temps,
ventilation par organisme, financeurs réalisés, commentaires, emprise
réalisée), le niveau de réalisation global et les réglages du suivi, la
planification annuelle ajustée (#794) ; par indicateur, les mesures de ses
métriques et ses scores annuels / global.

**Correspondance d'une version à l'autre** : chaque action, indicateur,
métrique et poste copié pointe sur celui dont il est la copie (``origine``,
posé par ``PlanDuplicationService``). Une action modifiée garde son lien, et
donc son suivi ; une action supprimée dans la nouvelle version n'a plus de
copie : son suivi reste sur l'ancienne version, consultable ; une action
ajoutée part sans suivi. Les versions créées avant #803 n'ont pas ce lien :
la migration de rattrapage les apparie par code et libellé
(:func:`apparier_versions`).

**Conflit** : une année déjà saisie sur la nouvelle version (même action, même
année) prime ; celle de l'ancienne version reste où elle est.

Les fonctions acceptent les modèles en paramètre (``modeles=``) pour servir
telles quelles dans une migration de données (modèles historiques).
"""
from collections import defaultdict
from types import SimpleNamespace

from .access import INDICATEUR_TO_PG_PATHS, OPERATION_TO_PG_PATHS

#: Garde-fou contre une chaîne de versions (ou d'origines) qui bouclerait.
PROFONDEUR_MAX = 100


def modeles(apps=None):
    """Modèles utilisés ici — ceux du registre courant, ou d'une migration."""
    if apps is None:
        from django.apps import apps
    noms = (
        'PlanGestion', 'Operation', 'OperationAnnee', 'OperationAnneeOrganisme',
        'OperationAnneeRH', 'RealisationOperationAnnee', 'RealisationOperationAnneeOrganisme',
        'RealisationOperationAnneeRH', 'RealisationFinanceur', 'OperationRealisationGlobale',
        'Financeur', 'Poste', 'Indicateur', 'Metrique', 'Mesure', 'IndicateurMesure',
        'IndicateurRealisationGlobale', 'AjustementAnnuel', 'AjustementAnnuelRH',
        'AjustementAnnuelFinanceur',
    )
    return SimpleNamespace(**{nom: apps.get_model('plans', nom) for nom in noms})


# ---------------------------------------------------------------------------
# Objets d'un plan
# ---------------------------------------------------------------------------

def _ids(modele, paths, plan_id):
    ids = set()
    for path in paths:
        ids.update(modele._base_manager.filter(**{path: plan_id}).values_list('pk', flat=True))
    return ids


def objets_du_plan(plan_id, M):
    """{'operation'|'indicateur'|'metrique'|'poste': ids} d'un plan."""
    indicateurs = _ids(M.Indicateur, INDICATEUR_TO_PG_PATHS, plan_id)
    return {
        'operation': _ids(M.Operation, OPERATION_TO_PG_PATHS, plan_id),
        'indicateur': indicateurs,
        'metrique': set(M.Metrique._base_manager.filter(
            id_indicateur_id__in=indicateurs).values_list('pk', flat=True)),
        'poste': set(M.Poste._base_manager.filter(id_pg_id=plan_id).values_list('pk', flat=True)),
    }


def _modele(M, nature):
    return {'operation': M.Operation, 'indicateur': M.Indicateur,
            'metrique': M.Metrique, 'poste': M.Poste}[nature]


def correspondances(source_id, cible_id, M):
    """{nature: {id dans la source: id dans la cible}} en remontant ``origine``.

    Chaque objet de la cible remonte ses origines (copie de copie…) jusqu'à
    trouver un objet de la source. Si deux objets de la cible descendent du
    même objet source (copie d'une action dans la nouvelle version), le
    premier — le plus ancien — l'emporte.
    """
    src, cib = objets_du_plan(source_id, M), objets_du_plan(cible_id, M)
    resultat = {}
    for nature, ids_cible in cib.items():
        modele, ids_source = _modele(M, nature), src[nature]
        appariement = {}
        # cible → origine courante, remontée niveau par niveau (une requête par niveau).
        courant = dict(modele._base_manager.filter(pk__in=ids_cible).exclude(
            origine_id=None).values_list('pk', 'origine_id'))
        for _ in range(PROFONDEUR_MAX):
            if not courant:
                break
            for cible, origine in sorted(courant.items()):
                if origine in ids_source:
                    appariement.setdefault(origine, cible)
            reste = {c: o for c, o in courant.items() if o not in ids_source}
            parents = dict(modele._base_manager.filter(pk__in=set(reste.values())).exclude(
                origine_id=None).values_list('pk', 'origine_id'))
            courant = {c: parents[o] for c, o in reste.items() if o in parents}
        resultat[nature] = appariement
    return resultat


# ---------------------------------------------------------------------------
# Déplacement
# ---------------------------------------------------------------------------

def _financeur_cible(financeur, cible_id, M, cache):
    """Financeur de même nom et même catégorie dans la cible (créé au besoin)."""
    if financeur is None:
        return None
    cle = (financeur.nom.strip().lower(), financeur.id_categorie_id,
           (financeur.categorie_libre or '').strip().lower())
    if cle not in cache:
        existant = M.Financeur._base_manager.filter(
            id_pg_id=cible_id, nom__iexact=financeur.nom.strip(),
            id_categorie_id=financeur.id_categorie_id,
            categorie_libre__iexact=(financeur.categorie_libre or '').strip(),
        ).first()
        cache[cle] = existant or M.Financeur._base_manager.create(
            id_pg_id=cible_id, nom=financeur.nom.strip(),
            id_categorie_id=financeur.id_categorie_id,
            categorie_libre=(financeur.categorie_libre or '').strip())
    return cache[cle]


def _annee_saisie(oa, M):
    """L'année d'action porte-t-elle déjà du suivi (année ou organisme) ?"""
    return (M.RealisationOperationAnnee._base_manager.filter(id_operation_annee=oa).exists()
            or M.RealisationOperationAnneeOrganisme._base_manager.filter(
                id_operation_annee_organisme__id_operation_annee=oa).exists())


def _deplacer_annee(oa_src, op_cible_id, cible_id, postes, M, financeurs, stats):
    rea = M.RealisationOperationAnnee._base_manager.filter(id_operation_annee=oa_src).first()
    reas_org = list(M.RealisationOperationAnneeOrganisme._base_manager.filter(
        id_operation_annee_organisme__id_operation_annee=oa_src
    ).select_related('id_operation_annee_organisme'))
    if rea is None and not reas_org:
        return

    oa_cible = M.OperationAnnee._base_manager.filter(
        id_operation_id=op_cible_id, annee=oa_src.annee).first()
    if oa_cible is not None and _annee_saisie(oa_cible, M):
        stats['annees_conservees'] += 1  # la nouvelle version prime
        return
    if oa_cible is None:
        # Année retirée de la programmation de la nouvelle version : le suivi
        # saisi la garde, sans prévu (comme une réalisation non prévue, #418).
        oa_cible = M.OperationAnnee._base_manager.create(
            id_operation_id=op_cible_id, annee=oa_src.annee, periodicite=False)

    if rea is not None:
        rea.id_operation_annee = oa_cible
        rea.save(update_fields=['id_operation_annee'])
        lignes_rh_cible = list(M.OperationAnneeRH._base_manager.filter(id_operation_annee=oa_cible))
        for ligne in M.RealisationOperationAnneeRH._base_manager.filter(
                id_realisation_operation_annee=rea):
            ligne.id_poste_id = postes.get(ligne.id_poste_id)
            ligne.id_operation_annee_rh = next((
                p for p in lignes_rh_cible
                if p.id_poste_id == ligne.id_poste_id and p.id_organisme_id == ligne.id_organisme_id
                and p.categorie_depense == ligne.categorie_depense), None)
            ligne.save(update_fields=['id_poste', 'id_operation_annee_rh'])
        for ligne in M.RealisationFinanceur._base_manager.filter(
                id_realisation_operation_annee=rea).select_related('id_financeur'):
            ligne.id_financeur = _financeur_cible(ligne.id_financeur, cible_id, M, financeurs)
            ligne.save(update_fields=['id_financeur'])

    for rea_org in reas_org:
        oao_src = rea_org.id_operation_annee_organisme
        oao_cible, _ = M.OperationAnneeOrganisme._base_manager.get_or_create(
            id_operation_annee=oa_cible, id_organisme_id=oao_src.id_organisme_id)
        rea_org.id_operation_annee_organisme = oao_cible
        rea_org.save(update_fields=['id_operation_annee_organisme'])
    stats['annees'] += 1


def _deplacer_operation(op_src, op_cible, cible_id, postes, M, financeurs, stats):
    avant = stats['annees'] + stats['ajustements'] + stats['globales']
    globale = M.OperationRealisationGlobale._base_manager.filter(id_operation_id=op_src).first()
    if globale is not None:
        if M.OperationRealisationGlobale._base_manager.filter(id_operation_id=op_cible).exists():
            stats['annees_conservees'] += 1
        else:
            globale.id_operation_id = op_cible
            globale.save(update_fields=['id_operation'])
            stats['globales'] += 1

    for oa in M.OperationAnnee._base_manager.filter(
            id_operation_id=op_src).exclude(annee=None).order_by('annee'):
        _deplacer_annee(oa, op_cible, cible_id, postes, M, financeurs, stats)

    annees_cible = set(M.AjustementAnnuel._base_manager.filter(
        id_operation_id=op_cible).values_list('annee', flat=True))
    for ajustement in M.AjustementAnnuel._base_manager.filter(id_operation_id=op_src):
        if ajustement.annee in annees_cible:
            stats['annees_conservees'] += 1
            continue
        ajustement.id_operation_id = op_cible
        ajustement.save(update_fields=['id_operation'])
        for ligne in M.AjustementAnnuelRH._base_manager.filter(id_ajustement_annuel=ajustement):
            ligne.id_poste_id = postes.get(ligne.id_poste_id)
            ligne.save(update_fields=['id_poste'])
        for ligne in M.AjustementAnnuelFinanceur._base_manager.filter(
                id_ajustement_annuel=ajustement).select_related('id_financeur'):
            ligne.id_financeur = _financeur_cible(ligne.id_financeur, cible_id, M, financeurs)
            ligne.save(update_fields=['id_financeur'])
        stats['ajustements'] += 1
    if stats['annees'] + stats['ajustements'] + stats['globales'] > avant:
        stats['actions'] += 1  # actions dont du suivi a effectivement suivi


def _annee(mesure):
    return mesure.date_mesure.year if mesure.date_mesure else None


def _deplacer_indicateurs(appariement, M, stats):
    for src, cible in appariement['indicateur'].items():
        annees = set(M.IndicateurMesure._base_manager.filter(
            id_indicateur_id=cible).values_list('annee', flat=True))
        stats['annees_conservees'] += M.IndicateurMesure._base_manager.filter(
            id_indicateur_id=src, annee__in=annees).count()
        M.IndicateurMesure._base_manager.filter(id_indicateur_id=src).exclude(
            annee__in=annees).update(id_indicateur_id=cible)
        if not M.IndicateurRealisationGlobale._base_manager.filter(id_indicateur_id=cible).exists():
            M.IndicateurRealisationGlobale._base_manager.filter(
                id_indicateur_id=src).update(id_indicateur_id=cible)

    for src, cible in appariement['metrique'].items():
        annees = {_annee(m) for m in M.Mesure._base_manager.filter(id_metrique_id=cible)}
        for mesure in M.Mesure._base_manager.filter(id_metrique_id=src):
            if _annee(mesure) in annees:
                stats['annees_conservees'] += 1
                continue
            mesure.id_metrique_id = cible
            mesure.save(update_fields=['id_metrique'])
            stats['mesures'] += 1


def deplacer(source_id, cible_id, appariement, M):
    """Déplace le suivi de ``source_id`` vers ``cible_id`` selon ``appariement``
    ({nature: {id source: id cible}}). Ce qui n'a pas de correspondant reste."""
    stats = defaultdict(int)
    financeurs = {}
    postes = appariement['poste']
    for src, cible in appariement['operation'].items():
        _deplacer_operation(src, cible, cible_id, postes, M, financeurs, stats)
    _deplacer_indicateurs(appariement, M, stats)
    return stats


# ---------------------------------------------------------------------------
# Chaîne de versions
# ---------------------------------------------------------------------------

def anterieures_meme_rang(plan, M):
    """Versions antérieures du même rang, de la plus proche à la plus ancienne."""
    resultat, vus = [], {plan.pk}
    courant = M.PlanGestion._base_manager.filter(pk=plan.plan_parent_id).first()
    while courant is not None and courant.pk not in vus and len(resultat) < PROFONDEUR_MAX:
        if courant.rang != plan.rang:
            break
        resultat.append(courant)
        vus.add(courant.pk)
        courant = M.PlanGestion._base_manager.filter(pk=courant.plan_parent_id).first()
    return resultat


def transferer_suivi(plan, apps=None):
    """À la validation de ``plan`` : le suivi des versions antérieures du même
    rang y est déplacé, et ces versions renvoient vers lui. Idempotent."""
    M = modeles(apps)
    total = defaultdict(int)
    for ancienne in anterieures_meme_rang(plan, M):
        for cle, valeur in deplacer(
                ancienne.pk, plan.pk, correspondances(ancienne.pk, plan.pk, M), M).items():
            total[cle] += valeur
        M.PlanGestion._base_manager.filter(pk=ancienne.pk).update(suivi_poursuivi_dans_id=plan.pk)
    # Les versions qui renvoyaient vers une version antérieure renvoient
    # désormais vers celle-ci : un seul saut, toujours.
    anciennes = [p.pk for p in anterieures_meme_rang(plan, M)]
    if anciennes:
        M.PlanGestion._base_manager.filter(
            suivi_poursuivi_dans_id__in=anciennes).update(suivi_poursuivi_dans_id=plan.pk)
    M.PlanGestion._base_manager.filter(pk=plan.pk).update(suivi_poursuivi_dans_id=None)
    return dict(total)


def rendre_suivi(plan, apps=None):
    """Avant la suppression de ``plan`` : s'il porte le suivi de versions
    antérieures, il le rend à la plus proche du même rang."""
    M = modeles(apps)
    if not M.PlanGestion._base_manager.filter(suivi_poursuivi_dans_id=plan.pk).exists():
        return {}
    anciennes = anterieures_meme_rang(plan, M)
    if not anciennes:
        return {}
    receveuse = anciennes[0]
    aller = correspondances(receveuse.pk, plan.pk, M)
    retour = {nature: {c: s for s, c in paires.items()} for nature, paires in aller.items()}
    stats = deplacer(plan.pk, receveuse.pk, retour, M)
    M.PlanGestion._base_manager.filter(suivi_poursuivi_dans_id=plan.pk).exclude(
        pk=receveuse.pk).update(suivi_poursuivi_dans_id=receveuse.pk)
    M.PlanGestion._base_manager.filter(pk=receveuse.pk).update(suivi_poursuivi_dans_id=None)
    return dict(stats)


# ---------------------------------------------------------------------------
# Rattrapage des versions créées avant #803 (migration)
# ---------------------------------------------------------------------------

def _norm(texte):
    return ' '.join((texte or '').split()).lower()


def _apparier(sources, cibles, cles):
    """Apparie deux listes de (id, attributs) : clé par clé, une clé ne vaut
    que si elle est unique des deux côtés. Renvoie {id source: id cible}."""
    paires, libres_s, libres_c = {}, dict(sources), dict(cibles)
    for cle in cles:
        index_s, index_c = defaultdict(list), defaultdict(list)
        for i, attrs in libres_s.items():
            k = cle(attrs)
            if k:
                index_s[k].append(i)
        for i, attrs in libres_c.items():
            k = cle(attrs)
            if k:
                index_c[k].append(i)
        for k, ids_s in index_s.items():
            ids_c = index_c.get(k, [])
            if len(ids_s) == 1 and len(ids_c) == 1:
                paires[ids_s[0]] = ids_c[0]
                libres_s.pop(ids_s[0])
                libres_c.pop(ids_c[0])
    return paires


def apparier_versions(source_id, cible_id, M):
    """Pose ``origine`` sur les objets de la cible qui n'en ont pas, par
    appariement avec ceux de la source (versions créées avant #803)."""
    src, cib = objets_du_plan(source_id, M), objets_du_plan(cible_id, M)

    def sans_origine(modele, ids, *champs):
        return list(modele._base_manager.filter(pk__in=ids, origine_id=None).values_list(
            'pk', *champs))

    def poser(modele, paires):
        for s, c in paires.items():
            modele._base_manager.filter(pk=c).update(origine_id=s)

    deja = correspondances(source_id, cible_id, M)

    def restants(nature, modele, *champs):
        pris = set(deja[nature])
        return [(r[0], r[1:]) for r in modele._base_manager.filter(
            pk__in=src[nature] - pris).values_list('pk', *champs)]

    ops = _apparier(
        restants('operation', M.Operation, 'code_operation', 'libelle'),
        [(r[0], r[1:]) for r in sans_origine(M.Operation, cib['operation'], 'code_operation', 'libelle')],
        [lambda a: (_norm(a[0]), _norm(a[1])) if a[0] and a[1] else None,
         lambda a: _norm(a[1]) or None,
         lambda a: _norm(a[0]) or None])
    poser(M.Operation, ops)

    inds = _apparier(
        restants('indicateur', M.Indicateur, 'nom_indicateur'),
        [(r[0], r[1:]) for r in sans_origine(M.Indicateur, cib['indicateur'], 'nom_indicateur')],
        [lambda a: _norm(a[0]) or None])
    poser(M.Indicateur, inds)

    # Métriques : au sein d'indicateurs appariés, par nom (ou seule métrique).
    tous_inds = {**correspondances(source_id, cible_id, M)['indicateur']}
    for ind_s, ind_c in tous_inds.items():
        mets = _apparier(
            [(r[0], r[1:]) for r in M.Metrique._base_manager.filter(
                id_indicateur_id=ind_s).values_list('pk', 'nom_metrique')],
            [(r[0], r[1:]) for r in M.Metrique._base_manager.filter(
                id_indicateur_id=ind_c, origine_id=None).values_list('pk', 'nom_metrique')],
            [lambda a: _norm(a[0]) or None, lambda a: 'seule'])
        poser(M.Metrique, mets)

    postes = _apparier(
        restants('poste', M.Poste, 'nom_local', 'id_organisme_id', 'organisme_libre', 'cout_jour'),
        [(r[0], r[1:]) for r in sans_origine(
            M.Poste, cib['poste'], 'nom_local', 'id_organisme_id', 'organisme_libre', 'cout_jour')],
        [lambda a: (_norm(a[0]), a[1], _norm(a[2]), str(a[3])),
         lambda a: (_norm(a[0]), a[1], _norm(a[2])) if a[0] else None])
    poser(M.Poste, postes)


def rattraper(apps=None):
    """Migration #803 : apparie les versions existantes d'un même rang, puis
    fait suivre le suivi jusqu'à la dernière version validée de chaque rang."""
    M = modeles(apps)
    plans = list(M.PlanGestion._base_manager.exclude(plan_parent_id=None).select_related(
        'plan_parent'))
    meme_rang = [p for p in plans if p.plan_parent.rang == p.rang]

    def profondeur(plan):
        n, courant = 0, plan
        while courant.plan_parent_id is not None and n < PROFONDEUR_MAX:
            n += 1
            courant = M.PlanGestion._base_manager.get(pk=courant.plan_parent_id)
        return n

    meme_rang.sort(key=profondeur)
    for plan in meme_rang:
        apparier_versions(plan.plan_parent_id, plan.pk, M)
    for plan in meme_rang:
        if plan.statut != 'draft':
            transferer_suivi(plan, apps)
