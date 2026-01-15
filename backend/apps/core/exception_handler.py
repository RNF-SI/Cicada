"""
Exception handler personnalise pour Django REST Framework.

Ce module fournit un handler qui:
- Log automatiquement toutes les exceptions avec le correlation_id
- Retourne des reponses JSON coherentes
- Ajoute le correlation_id dans la reponse d'erreur
"""

import logging
import traceback
from typing import Optional

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .middleware.logging import get_correlation_id


logger = logging.getLogger('apps')


def exception_handler(exc: Exception, context: dict) -> Optional[Response]:
    """
    Handler d'exceptions personnalise pour DRF.

    Ce handler:
    1. Log l'exception avec le correlation_id et le contexte
    2. Appelle le handler DRF par defaut pour le traitement standard
    3. Enrichit la reponse avec le correlation_id

    Args:
        exc: L'exception levee.
        context: Le contexte de la requete (view, request, etc.).

    Returns:
        Une Response DRF ou None si l'exception n'est pas geree.
    """
    # Recuperer les informations de contexte
    request = context.get('request')
    view = context.get('view')
    correlation_id = get_correlation_id()

    # Construire les infos de log
    log_extra = {
        'exception_type': type(exc).__name__,
        'exception_message': str(exc),
        'correlation_id': correlation_id,
        'view': view.__class__.__name__ if view else None,
        'path': request.path if request else None,
        'method': request.method if request else None,
    }

    # Ajouter l'utilisateur si disponible
    if request and hasattr(request, 'user') and request.user and request.user.is_authenticated:
        log_extra['user_id'] = getattr(request.user, 'id_role', None)
        log_extra['user_email'] = getattr(request.user, 'email', None)

    # Determiner le niveau de log selon le type d'exception
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        # Erreurs d'authentification: niveau INFO (normal)
        logger.info(
            f"Authentication error: {type(exc).__name__}",
            extra=log_extra,
        )
    elif isinstance(exc, PermissionDenied):
        # Erreurs de permission: niveau WARNING
        logger.warning(
            f"Permission denied: {exc}",
            extra=log_extra,
        )
    elif isinstance(exc, ValidationError):
        # Erreurs de validation: niveau INFO (normal)
        logger.info(
            f"Validation error: {exc}",
            extra={**log_extra, 'validation_errors': exc.detail},
        )
    elif isinstance(exc, Http404):
        # 404: niveau INFO
        logger.info(
            f"Not found: {request.path if request else 'unknown'}",
            extra=log_extra,
        )
    elif isinstance(exc, APIException):
        # Autres erreurs API: niveau WARNING
        logger.warning(
            f"API error: {type(exc).__name__} - {exc}",
            extra=log_extra,
        )
    else:
        # Erreurs inattendues: niveau ERROR avec stack trace
        logger.error(
            f"Unhandled exception: {type(exc).__name__} - {exc}",
            extra={
                **log_extra,
                'traceback': traceback.format_exc(),
            },
        )

    # Appeler le handler DRF par defaut
    response = drf_exception_handler(exc, context)

    # Si DRF n'a pas gere l'exception, creer une reponse 500
    if response is None:
        response = Response(
            {
                'error': 'internal_server_error',
                'detail': 'Une erreur inattendue s\'est produite.',
                'correlation_id': correlation_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    else:
        # Enrichir la reponse avec le correlation_id
        if isinstance(response.data, dict):
            response.data['correlation_id'] = correlation_id

    return response
