"""
Tâches Celery du module plans.

`extract_plan_ia` : extraction IA (API Anthropic) d'un plan de gestion à partir
d'un ou plusieurs PDF, en tâche de fond (l'appel peut durer plusieurs minutes).
Le résultat ({data, report, meta}) est récupéré par le front via l'AsyncResult,
puis relu/validé dans la grille de correction (#9). L'IA n'importe rien.
"""

import base64
import logging

from celery import shared_task

from .models import PlanGestion
from .services_import_ia import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, extract

logger = logging.getLogger(__name__)


@shared_task(name="plans.extract_plan_ia", bind=True)
def extract_plan_ia(self, plan_id, target, pdf_b64_list, model=DEFAULT_MODEL,
                    max_tokens=DEFAULT_MAX_TOKENS):
    """Extrait `target` (arborescence | actions) du/des PDF pour le plan donné.

    Args:
        plan_id: PK du plan (brouillon).
        target: "arborescence" ou "actions".
        pdf_b64_list: liste de PDF encodés en base64 (transport Celery-safe).
        model / max_tokens: paramètres du modèle Anthropic.

    Returns:
        {"data": ..., "report": ..., "meta": ...} — même forme que validate-data.
    """
    plan = PlanGestion.objects.get(pk=plan_id)
    pdf_bytes = [base64.standard_b64decode(b) for b in pdf_b64_list]
    logger.info(
        "Extraction IA plan=%s cible=%s modèle=%s (%d PDF)",
        plan_id, target, model, len(pdf_bytes),
    )
    return extract(target, plan, pdf_bytes, model=model, max_tokens=max_tokens)
