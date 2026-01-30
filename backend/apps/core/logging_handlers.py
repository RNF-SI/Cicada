"""
Handler de log personnalise pour enregistrer les erreurs en base de donnees.
Utilise une queue et un thread worker pour eviter d'impacter les performances.
"""
import logging
import queue
import threading
import traceback
from typing import Any


class DatabaseLogHandler(logging.Handler):
    """
    Handler non-bloquant qui enregistre les logs d'erreur en base de donnees.

    Utilise une queue et un thread worker en arriere-plan pour:
    - Ne pas bloquer les requetes HTTP
    - Grouper les ecritures en base
    - Gerer les erreurs de facon robuste

    Usage dans settings.py LOGGING:
        'handlers': {
            'db_errors': {
                'level': 'ERROR',
                'class': 'apps.core.logging_handlers.DatabaseLogHandler',
            },
        }
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pour eviter plusieurs workers."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        super().__init__()
        self._queue: queue.Queue = queue.Queue()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name='DatabaseLogHandler-Worker'
        )
        self._worker_thread.start()
        self._initialized = True

    def emit(self, record: logging.LogRecord) -> None:
        """
        Ajoute le record a la queue pour traitement asynchrone.
        Ne fait rien si le niveau n'est pas ERROR ou CRITICAL.
        """
        try:
            # Filtrer les niveaux - seulement ERROR et CRITICAL
            if record.levelno < logging.ERROR:
                return

            # Ne pas logger les erreurs du handler lui-meme
            if record.name == 'apps.core.logging_handlers':
                return

            # Preparer les donnees a envoyer
            log_data = self._prepare_log_data(record)
            self._queue.put(log_data)

        except Exception:
            # Ne jamais lever d'exception dans emit()
            self.handleError(record)

    def _prepare_log_data(self, record: logging.LogRecord) -> dict[str, Any]:
        """Extrait les donnees du LogRecord pour stockage en base."""
        # Message formate
        try:
            message = self.format(record) if self.formatter else record.getMessage()
        except Exception:
            message = str(record.msg)

        # Stack trace si exception
        stack_trace = None
        exception_type = None
        if record.exc_info:
            exception_type = record.exc_info[0].__name__ if record.exc_info[0] else None
            stack_trace = ''.join(traceback.format_exception(*record.exc_info))

        # Recuperer le correlation_id et les infos de requete depuis les extras
        correlation_id = getattr(record, 'correlation_id', None)
        user_id = getattr(record, 'user_id', None)
        path = getattr(record, 'path', None)
        method = getattr(record, 'method', None)

        # Contexte additionnel
        context = {}
        for key in ['request_data', 'extra_context', 'view_name']:
            value = getattr(record, key, None)
            if value is not None:
                context[key] = value

        return {
            'level': record.levelname,
            'message': message[:5000],  # Limiter la taille du message
            'logger_name': record.name,
            'correlation_id': correlation_id,
            'user_id': user_id,
            'path': path,
            'method': method,
            'exception_type': exception_type,
            'stack_trace': stack_trace,
            'context': context,
        }

    def _worker_loop(self) -> None:
        """
        Boucle du worker qui consomme les logs de la queue.
        S'execute dans un thread separe.
        """
        while True:
            try:
                # Attendre un log (bloquant)
                log_data = self._queue.get()

                # Traiter le log
                self._write_to_db(log_data)

            except Exception as e:
                # Logger l'erreur vers stderr (pas vers ce handler!)
                import sys
                print(f"DatabaseLogHandler worker error: {e}", file=sys.stderr)

    def _write_to_db(self, log_data: dict[str, Any]) -> None:
        """
        Ecrit le log en base de donnees.
        Import lazy pour eviter les imports circulaires.
        """
        try:
            # Import lazy du modele
            from apps.core.models import ErrorLog

            # Recuperer l'utilisateur si user_id fourni
            user = None
            user_id = log_data.pop('user_id', None)
            if user_id:
                try:
                    from apps.users.models import Role
                    user = Role.objects.filter(id_role=user_id).first()
                except Exception:
                    pass

            # Creer le log
            ErrorLog.objects.create(
                level=log_data['level'],
                message=log_data['message'],
                logger_name=log_data.get('logger_name'),
                correlation_id=log_data.get('correlation_id'),
                user=user,
                path=log_data.get('path'),
                method=log_data.get('method'),
                exception_type=log_data.get('exception_type'),
                stack_trace=log_data.get('stack_trace'),
                context=log_data.get('context', {}),
            )

        except Exception as e:
            # Ne jamais propager d'erreur
            import sys
            print(f"DatabaseLogHandler write error: {e}", file=sys.stderr)
