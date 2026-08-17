"""
Dépôt de l'index par les instances (#636).

## Le contrat

Une publication se fait en trois temps :

1. ``POST /api/federation/lots/`` — ouvre un lot ;
2. ``POST /api/federation/lots/{id}/plans/`` — N pages de plans, chacune portant
   ses plans **et leur contenu** ;
3. ``POST /api/federation/lots/{id}/bascule/`` — publie le lot et purge les
   plans de cette instance qui n'y figuraient pas.

L'unité d'échange est le **plan entier**, pas le document. Un plan arrive avec
la liste complète de ses objets explorables, et remplace intégralement ce que le
hub connaissait de lui. C'est ce qui rend l'ingestion idempotente sans avoir à
comparer objet par objet : un enjeu supprimé chez l'émetteur disparaît parce
qu'il n'est plus dans la liste, pas parce qu'un message l'a annoncé.

## Pourquoi l'état plutôt que l'événement

Un index alimenté par des événements finit immanquablement par laisser visible
un plan que son gestionnaire a dépublié — un message perdu, une instance
redémarrée au mauvais moment. C'est un incident, pas une gêne : de la donnée que
quelqu'un a explicitement retirée reste consultable. La republication complète
coûte plus cher à chaque passage, mais elle converge toujours.

## Ce que le hub refuse de croire

L'instance émettrice est déduite du **jeton**, jamais du corps de la requête.
Sans quoi n'importe quel porteur d'un jeton valide pourrait ouvrir un lot au nom
d'une autre instance, puis le basculer — c'est-à-dire purger l'index de
quelqu'un d'autre.
"""

import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

from apps.geo.models import LArea

from .models import ContenuIndexe, PlanIndexe

logger = logging.getLogger(__name__)

#: Version du contrat de dépôt.
#:
#: Elle ne bouge que si un document ancien risquerait d'être **mal compris** par
#: ce lecteur, ou l'inverse. Ajouter un champ optionnel n'est pas ce cas : un
#: lecteur ancien l'ignore, un lecteur récent retombe sur une valeur vide quand
#: l'émetteur ne l'envoie pas encore. Les instances étant mises à jour
#: indépendamment (paquet Debian), bumper à chaque ajout aurait pour seul effet
#: d'interrompre la publication entre deux versions qui se comprenaient.
FORMAT_VERSION = 1

#: Versions que ce hub sait lire.
FORMATS_ACCEPTES = {1}

#: Champs d'un document de contenu repris tels quels.
CHAMPS_CONTENU = [
    'type_contenu', 'id_objet',
    'titre', 'description', 'rattachements', 'contexte',
    'parent_type', 'parent_libelle', 'sous_type', 'sous_type_libelle',
    'index_version',
]


class EstInstanceAutorisee(BasePermission):
    """
    Jeton de dépôt, un par instance émettrice.

    Un jeton par instance plutôt qu'un secret unique partagé : révoquer l'accès
    d'une instance compromise ne doit pas interrompre la publication des autres.

    Volontairement rudimentaire — l'authentification définitive dépend de #514
    (OAuth2 / OIDC). Ce qui compte ici est que l'identité de l'émetteur soit
    **portée par le jeton** et non déclarée dans la requête.
    """

    message = "Jeton de fédération absent ou invalide."

    def has_permission(self, request, view):
        jeton = request.headers.get('X-Federation-Token')
        if not jeton:
            return False
        for instance_id, attendu in settings.HUB_FEDERATION_TOKENS.items():
            if jeton == attendu:
                request.instance_id = instance_id
                return True
        logger.warning("Dépôt refusé : jeton inconnu.")
        return False


class PeutLire(BasePermission):
    """
    Jeton de lecture, partagé par les instances qui relaient l'exploration.

    Distinct des jetons de dépôt : lire n'est pas écrire, et une instance peut
    légitimement consulter l'exploration sans être autorisée à y publier.
    """

    message = "Jeton de lecture absent ou invalide."

    def has_permission(self, request, view):
        attendu = settings.HUB_READ_TOKEN
        if not attendu:
            return False
        return request.headers.get('X-Hub-Token') == attendu


# --------------------------------------------------------------------------- #
# Résolution des codes nationaux
# --------------------------------------------------------------------------- #

def resoudre_zones(codes):
    """
    Traduit les codes de zones publiés (« DEP:13 ») en identifiants **locaux**.

    Possible parce que le découpage administratif vient du même référentiel
    national partout : seuls les identifiants techniques diffèrent, pas les
    codes. Un code inconnu ne se résout à rien — le résultat correct : le hub
    n'a pas à inventer une zone qu'il ne connaît pas.
    """
    if not codes:
        return []
    paires = [code.split(':', 1) for code in codes if ':' in code]
    if not paires:
        return []

    # Une seule requête pour toute la liste : traduire code par code coûterait
    # deux requêtes par plan, et un lot en compte des centaines.
    conditions = {(type_code, area_code) for type_code, area_code in paires}
    connues = LArea.objects.filter(
        id_type__type_code__in={t for t, _ in conditions},
        area_code__in={c for _, c in conditions},
    ).values_list('id_type__type_code', 'area_code', 'id_area')

    return sorted(
        id_area for type_code, area_code, id_area in connues
        if (type_code, area_code) in conditions
    )


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #

def ingerer_plan(charge, instance_id, lot):
    """
    Enregistre un plan et **remplace intégralement** son contenu.

    Le remplacement est en bloc plutôt qu'en différentiel : comparer les objets
    un à un coûterait une requête par objet pour un gain nul, le contenu d'un
    plan validé étant verrouillé en lecture seule côté CICADA (#248). Ce qui
    bouge d'une publication à l'autre, c'est le plan entier ou rien.

    :returns: le nombre de documents de contenu écrits.
    """
    area_ids = resoudre_zones(charge.get('area_codes'))
    site_inpn_codes = sorted(charge.get('site_inpn_codes') or [])
    type_site_codes = sorted(charge.get('type_site_codes') or [])

    plan, _ = PlanIndexe.objects.update_or_create(
        instance_id=instance_id,
        id_pg=charge['id_pg'],
        defaults={
            'lot': lot,
            'slug': charge.get('slug') or '',
            'url_instance': charge.get('url_instance') or '',
            'nom': charge['nom'],
            'statut': charge['statut'],
            'rang': charge.get('rang'),
            'annee_debut': charge.get('annee_debut'),
            'annee_fin': charge.get('annee_fin'),
            'type_document': charge.get('type_document'),
            'gestionnaire_principal': charge.get('gestionnaire_principal'),
            'sites': charge.get('sites') or [],
            'site_inpn_codes': site_inpn_codes,
            'type_site_codes': type_site_codes,
            'area_ids': area_ids,
            # Vide tant que l'identité nationale des organismes n'est pas
            # tranchée. Recopier un identifiant local ferait matcher le mauvais
            # organisme, en silence.
            'organisme_codes': [],
            'fiche': charge.get('fiche') or {},
            'format_version': lot.format_version,
        },
    )

    plan.contenus.all().delete()

    documents_recus = charge.get('contenus') or []

    # Défense contre un objet qui aurait changé de plan entre deux publications.
    # L'unicité du contenu est globale à l'instance — `(instance_id,
    # type_contenu, id_objet)` — parce qu'un identifiant d'enjeu ou d'action est
    # une séquence globale chez l'émetteur, pas une numérotation par plan. Vider
    # le contenu du plan courant ne suffit donc pas : si l'objet est arrivé sous
    # un autre plan, l'insertion violerait la contrainte et ferait échouer la
    # page entière. Ce n'est pas censé arriver ; c'est précisément pour ça qu'il
    # vaut mieux le traiter que de le laisser bloquer une publication.
    if documents_recus:
        cles = {(d['type_contenu'], d['id_objet']) for d in documents_recus}
        ailleurs = (
            ContenuIndexe.objects
            .filter(
                instance_id=instance_id,
                type_contenu__in={t for t, _ in cles},
                id_objet__in={i for _, i in cles},
            )
            .exclude(plan=plan)
            .values_list('pk', 'type_contenu', 'id_objet')
        )
        # Le filtre ci-dessus est un produit cartésien des deux colonnes : on
        # ne supprime que les lignes dont le couple exact est réclamé.
        a_supprimer = [pk for pk, type_c, id_o in ailleurs if (type_c, id_o) in cles]
        if a_supprimer:
            logger.warning(
                "Instance %s : %s document(s) réattribué(s) au plan %s.",
                instance_id, len(a_supprimer), plan.id_pg,
            )
            ContenuIndexe.objects.filter(pk__in=a_supprimer).delete()

    facettes = {
        'statut_pg': plan.statut,
        'annee_debut': plan.annee_debut,
        'annee_fin': plan.annee_fin,
        'type_site_codes': type_site_codes,
        'area_ids': area_ids,
        'organisme_codes': [],
    }
    documents = [
        ContenuIndexe(
            instance_id=instance_id,
            plan=plan,
            **{champ: doc.get(champ) for champ in CHAMPS_CONTENU
               if doc.get(champ) is not None},
            **facettes,
        )
        for doc in documents_recus
    ]
    ContenuIndexe.objects.bulk_create(documents, batch_size=500)
    return len(documents)


def basculer(lot):
    """
    Publie le lot et retire ce qui n'y figurait pas.

    La purge est **bornée à l'instance du lot** : une instance ne peut pas
    dépublier le contenu d'une autre, même en basculant un lot vide. Sans cette
    borne, un jeton compromis suffirait à vider l'index entier.

    Le contenu suit ses plans par cascade : le hub n'a pas à raisonner sur les
    objets, seulement sur les plans.

    :returns: le nombre de plans purgés.
    """
    from django.utils import timezone

    obsoletes = (
        PlanIndexe.objects
        .filter(instance_id=lot.instance_id)
        .exclude(lot=lot)
    )
    # Compté avant la suppression : `delete()` rend le total des lignes
    # touchées, contenu cascadé compris, qui ne dit rien du nombre de plans.
    nb_purges = obsoletes.count()
    obsoletes.delete()

    plans_restants = PlanIndexe.objects.filter(instance_id=lot.instance_id).count()

    lot.etat = lot.ETAT_BASCULE
    lot.date_bascule = timezone.now()
    lot.plans_purges = nb_purges
    lot.save(update_fields=['etat', 'date_bascule', 'plans_purges'])

    logger.info(
        "Lot %s basculé pour l'instance %s : %s plans reçus, %s purgés, "
        "%s publiés au total.",
        lot.id, lot.instance_id, lot.plans_recus, nb_purges, plans_restants,
    )
    return nb_purges
