"""
Qui a publié quoi (#636).

Chaque ligne d'index porte son ``instance_id`` — un identifiant technique
(« rnf », « cen-aura »). Il suffit à *tracer* la donnée, pas à la *présenter* :
affiché tel quel dans une liste de résultats, il ne dit pas à un gestionnaire de
quelle structure vient le plan qu'il consulte.

Ce module résout l'identifiant en nom lisible, dans cet ordre :

1. le **registre** (:class:`~apps.index.models.Instance`), renseigné à
   l'enrôlement — il fait foi, c'est l'administrateur du hub qui l'a écrit ;
2. ce que l'**instance a déclaré** à sa dernière publication — seule source
   disponible pour une instance qui publie encore par jeton d'environnement,
   donc sans ligne au registre ;
3. l'**identifiant** lui-même, faute de mieux. Jamais rien de vide : une tuile
   sans provenance se lit comme une donnée locale, ce qu'elle n'est pas.

L'URL publique suit la même cascade, avec un dernier recours supplémentaire :
celle transportée par les plans eux-mêmes (``PlanIndexe.url_instance``).
"""

from .models import Instance, LotPublication, PlanIndexe


def _declarations(identifiants=None):
    """
    Ce que chaque instance a déclaré d'elle-même, à sa publication la plus récente.

    `DISTINCT ON` plutôt qu'un parcours de tous les lots : la table en accumule
    un par nuit et par instance, et cette résolution est sur le chemin de
    **chaque recherche**. Ramener cinq ans d'historique pour n'en garder que la
    dernière ligne de chacun se paierait sur toutes les pages de résultats.

    Une structure qui se renomme n'a donc rien à faire de plus que publier.
    """
    lots = LotPublication.objects.exclude(libelle_declare='')
    if identifiants is not None:
        lots = lots.filter(instance_id__in=identifiants)

    return {
        instance_id: (libelle, url)
        for instance_id, libelle, url in (
            lots
            .order_by('instance_id', '-date_ouverture')
            .distinct('instance_id')
            .values_list('instance_id', 'libelle_declare', 'url_publique_declaree')
        )
    }


def identites(identifiants=None):
    """
    Rend ``{instance_id: {'libelle': …, 'url_publique': …}}``.

    :param identifiants: restreint la résolution à ces instances. ``None``
        résout toutes celles connues du hub, à quelque titre que ce soit.
    """
    enrolees = Instance.objects.all()
    urls_publiees = PlanIndexe.objects.exclude(url_instance='')
    presentes = set()
    if identifiants is not None:
        identifiants = set(identifiants)
        enrolees = enrolees.filter(instance_id__in=identifiants)
        urls_publiees = urls_publiees.filter(instance_id__in=identifiants)
    else:
        # Sans restriction, la question posée est « toutes celles que le hub
        # connaît » : une instance qui a publié sans jamais déclarer son URL ni
        # être enrôlée en fait partie, et l'omettre la laisserait sans nom.
        presentes = set(
            PlanIndexe.objects.values_list('instance_id', flat=True).distinct()
        )

    enrolees = {i.instance_id: i for i in enrolees}
    declarees = _declarations(identifiants)
    # Une seule URL par instance suffit : c'est la racine de l'instance, pas
    # celle du plan, et elle est identique sur tous ses plans. `DISTINCT ON`
    # évite de ramener les milliers de lignes d'un index complet à chaque
    # recherche pour n'en garder qu'une par instance.
    urls_plans = dict(
        urls_publiees
        .order_by('instance_id')
        .distinct('instance_id')
        .values_list('instance_id', 'url_instance')
    )

    connus = set(enrolees) | set(declarees) | set(urls_plans) | presentes
    if identifiants is not None:
        connus |= identifiants

    resolues = {}
    for instance_id in connus:
        enrolee = enrolees.get(instance_id)
        libelle_declare, url_declaree = declarees.get(instance_id, ('', ''))
        resolues[instance_id] = {
            'libelle': (
                (enrolee.libelle if enrolee else '')
                or libelle_declare
                or instance_id
            ),
            'url_publique': (
                (enrolee.url_publique if enrolee else '')
                or url_declaree
                or urls_plans.get(instance_id, '')
            ),
        }
    return resolues

