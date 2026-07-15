"""
Helper réutilisable pour les actions `reorder` des ViewSets du module plans
(#249 / #261).

Le drag-and-drop côté frontend met à jour le champ `ordre` des entités d'un
même parent. Chaque ViewSet expose une action POST `reorder` qui valide le
payload, vérifie l'appartenance des IDs au parent indiqué (anti-tampering),
applique le verrou plan-hors-brouillon (#248) puis met à jour les ordres
en BDD dans une transaction.

Le verrou : la permission DRF `CanModifyOnlyDraftPlan` ne sait pas résoudre
le plan depuis le payload personnalisé `{parent_id, ordered_ids}` d'une
action `reorder`. On le vérifie explicitement ici en se basant sur la
méthode `get_plan_de_gestion()` du premier objet ciblé (tous appartiennent
au même parent, donc au même plan).
"""
from django.db import transaction
from django.db.models import Q
from rest_framework import status as drf_status
from rest_framework.response import Response

from .permissions import CanModifyOnlyDraftPlan


def do_reorder(viewset, request, *, parent_filter, parent_id=None, ordre_writer=None):
    """
    Implémentation factorisée de l'action `reorder`.

    Args:
        viewset: instance du ViewSet appelant (accès à `get_queryset()` et
            `queryset` pour les updates).
        request: requête DRF.
        parent_filter: soit le nom d'un champ FK (str, ex: 'id_pg'), soit une
            fonction `(parent_id, request) -> Q` pour les cas M2M (OO, Operation)
            ou multi-parents (Indicateur).
        parent_id: si fourni, ignore la valeur du payload (utile pour les vues
            qui ne reçoivent pas explicitement `parent_id`). Sinon, lit
            `parent_id` depuis le body.
        ordre_writer: callable optionnel `(parent_id, pk, pos) -> None` appliqué
            pour écrire l'ordre. Par défaut, met à jour ``ordre`` sur le modèle
            lui-même. #552 — nécessaire quand l'ordre est propre au parent et
            porté par une table de liaison (facteur partagé → CorFacteurEnjeu).

    Payload attendu :
        { "parent_id": <id>, "ordered_ids": [id1, id2, ...] }

    Réponse :
        - 200 OK : `{"updated": <int>}`
        - 400 Bad Request : payload invalide ou IDs n'appartenant pas au parent
    """
    if parent_id is None:
        parent_id = request.data.get('parent_id')
    ordered_ids = request.data.get('ordered_ids', [])

    if not isinstance(ordered_ids, list) or parent_id is None:
        return Response(
            {"detail": "Payload invalide : 'parent_id' et 'ordered_ids' (list) requis."},
            status=drf_status.HTTP_400_BAD_REQUEST,
        )

    # Normaliser les IDs en entiers (le frontend peut envoyer des strings)
    try:
        ordered_ids = [int(pk) for pk in ordered_ids]
        parent_id = int(parent_id)
    except (TypeError, ValueError):
        return Response(
            {"detail": "Les IDs doivent être des entiers."},
            status=drf_status.HTTP_400_BAD_REQUEST,
        )

    # Construit le filtre d'appartenance au parent
    if callable(parent_filter):
        parent_q = parent_filter(parent_id, request)
    else:
        parent_q = Q(**{parent_filter: parent_id})

    # Anti-tampering : vérifier que tous les IDs sont accessibles ET
    # appartiennent au parent indiqué. `get_queryset()` applique déjà les
    # permissions de scoping de l'utilisateur.
    valid_qs = viewset.get_queryset().filter(parent_q)
    valid_ids = set(valid_qs.values_list('pk', flat=True))
    requested = set(ordered_ids)
    if not requested.issubset(valid_ids):
        return Response(
            {"detail": "Certains IDs ne correspondent pas au parent indiqué ou ne sont pas accessibles."},
            status=drf_status.HTTP_400_BAD_REQUEST,
        )

    # Verrou #248 : si l'objet sait remonter au plan via `get_plan_de_gestion()`,
    # on bloque l'opération quand le plan n'est pas en statut éditable.
    # On vérifie sur le premier objet — tous appartiennent au même parent donc
    # au même plan.
    if ordered_ids:
        first = valid_qs.filter(pk=ordered_ids[0]).first()
        plan = CanModifyOnlyDraftPlan._resolve_plan_from_object(first) if first else None
        if plan is not None and plan.statut not in CanModifyOnlyDraftPlan.EDITABLE_STATUSES:
            return Response(
                {"detail": CanModifyOnlyDraftPlan.message},
                status=drf_status.HTTP_403_FORBIDDEN,
            )

    # Update en batch dans une transaction. On passe par le manager du
    # modèle sous-jacent pour bypass les éventuels `distinct()` du queryset
    # de base.
    model = viewset.queryset.model
    with transaction.atomic():
        for pos, pk in enumerate(ordered_ids):
            if ordre_writer is not None:
                ordre_writer(parent_id, pk, pos)
            else:
                model.objects.filter(pk=pk).update(ordre=pos)

    return Response({"updated": len(ordered_ids)}, status=drf_status.HTTP_200_OK)
