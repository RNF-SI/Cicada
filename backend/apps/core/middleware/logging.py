"""
Middleware de logging avec correlation ID.

Ce module fournit:
- CorrelationIdFilter: Filtre de logging qui ajoute le correlation_id aux logs
- RequestLoggingMiddleware: Middleware qui genere le correlation_id et log les requetes
"""

import logging
import threading
import time
import uuid
from typing import Optional

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin


# Thread-local storage pour le correlation_id
_correlation_id = threading.local()


def get_correlation_id() -> Optional[str]:
    """
    Recupere le correlation_id du thread courant.

    Returns:
        Le correlation_id ou None si non defini.
    """
    return getattr(_correlation_id, 'value', None)


def set_correlation_id(correlation_id: str) -> None:
    """
    Definit le correlation_id pour le thread courant.

    Args:
        correlation_id: L'identifiant de correlation a definir.
    """
    _correlation_id.value = correlation_id


def clear_correlation_id() -> None:
    """
    Supprime le correlation_id du thread courant.
    """
    if hasattr(_correlation_id, 'value'):
        del _correlation_id.value


class CorrelationIdFilter(logging.Filter):
    """
    Filtre de logging qui ajoute le correlation_id a chaque enregistrement de log.

    Ce filtre recupere le correlation_id du thread courant et l'ajoute
    a l'enregistrement de log, permettant de tracer les logs d'une meme requete.

    Exemple de log resultant:
        {"timestamp": "...", "correlation_id": "550e8400-e29b-41d4-a716-446655440000", ...}
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Ajoute le correlation_id a l'enregistrement de log.

        Args:
            record: L'enregistrement de log a modifier.

        Returns:
            True (le log n'est jamais filtre).
        """
        record.correlation_id = get_correlation_id() or '-'
        return True


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware qui genere un correlation_id unique pour chaque requete
    et log les informations de la requete.

    Fonctionnalites:
    - Genere un UUID unique pour chaque requete (ou utilise celui du header X-Correlation-ID)
    - Ajoute le correlation_id dans le header de reponse X-Correlation-ID
    - Log la requete (methode, path, user) au debut
    - Log la reponse (status, duration) a la fin

    Exemple de configuration dans settings.py:
        MIDDLEWARE = [
            ...
            'apps.core.middleware.logging.RequestLoggingMiddleware',
            ...
        ]
    """

    # URLs a exclure du logging detaille (health checks, etc.)
    EXCLUDED_PATHS = [
        '/api/health/',
        '/api/auth/health/',
        '/static/',
        '/media/',
        '/favicon.ico',
    ]

    def __init__(self, get_response=None):
        """Initialise le middleware."""
        super().__init__(get_response)
        self.logger = logging.getLogger('http')

    def process_request(self, request: HttpRequest) -> None:
        """
        Traite la requete entrante.

        - Genere ou recupere le correlation_id
        - Stocke le timestamp de debut
        - Log la requete

        Args:
            request: La requete HTTP entrante.
        """
        # Generer ou recuperer le correlation_id
        correlation_id = request.headers.get('X-Correlation-ID')
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Stocker dans le thread local
        set_correlation_id(correlation_id)

        # Stocker dans la requete pour usage ulterieur
        request.correlation_id = correlation_id
        request._logging_start_time = time.time()

        # Log la requete si pas exclue
        if not self._should_exclude(request.path):
            user_info = self._get_user_info(request)
            self.logger.info(
                "Request started",
                extra={
                    'method': request.method,
                    'path': request.path,
                    'query_string': request.META.get('QUERY_STRING', ''),
                    **user_info,
                }
            )

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Traite la reponse sortante.

        - Ajoute le header X-Correlation-ID
        - Log la reponse avec la duree
        - Nettoie le thread local

        Args:
            request: La requete HTTP.
            response: La reponse HTTP.

        Returns:
            La reponse modifiee avec le header X-Correlation-ID.
        """
        try:
            # Ajouter le correlation_id dans la reponse
            correlation_id = getattr(request, 'correlation_id', None) or get_correlation_id()
            if correlation_id:
                response['X-Correlation-ID'] = correlation_id

            # Calculer la duree
            start_time = getattr(request, '_logging_start_time', None)
            duration_ms = None
            if start_time:
                duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log la reponse si pas exclue
            if not self._should_exclude(request.path):
                user_info = self._get_user_info(request)
                log_level = logging.INFO if response.status_code < 400 else logging.WARNING
                if response.status_code >= 500:
                    log_level = logging.ERROR

                self.logger.log(
                    log_level,
                    "Request completed",
                    extra={
                        'method': request.method,
                        'path': request.path,
                        'status_code': response.status_code,
                        'duration_ms': duration_ms,
                        **user_info,
                    }
                )
        finally:
            # Nettoyer le thread local
            clear_correlation_id()

        return response

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        """
        Log les exceptions non gerees.

        Args:
            request: La requete HTTP.
            exception: L'exception levee.
        """
        user_info = self._get_user_info(request)
        self.logger.exception(
            f"Unhandled exception: {type(exception).__name__}",
            extra={
                'method': request.method,
                'path': request.path,
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                **user_info,
            }
        )

    def _should_exclude(self, path: str) -> bool:
        """
        Verifie si le path doit etre exclu du logging.

        Args:
            path: Le chemin de la requete.

        Returns:
            True si le path doit etre exclu.
        """
        return any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)

    def _get_user_info(self, request: HttpRequest) -> dict:
        """
        Extrait les informations utilisateur de la requete.

        Args:
            request: La requete HTTP.

        Returns:
            Dictionnaire avec user_id et user_email si disponibles.
        """
        info = {}
        if hasattr(request, 'user') and request.user and request.user.is_authenticated:
            info['user_id'] = getattr(request.user, 'id_role', None)
            info['user_email'] = getattr(request.user, 'email', None)
        return info
