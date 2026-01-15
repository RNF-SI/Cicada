"""
Configuration de pagination pour l'API des utilisateurs.
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class UsersPagination(PageNumberPagination):
    """
    Pagination personnalisée pour les utilisateurs.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        Réponse de pagination avec métadonnées étendues.
        """
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'pagination': {
                'count': self.page.paginator.count,
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.page_size,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            },
            'results': data
        })


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination pour de gros résultats (exports, statistiques).
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 500


class StandardPagination(UsersPagination):
    """
    Pagination standard héritée de UsersPagination.
    Alias pour compatibilité avec les viewsets organismes et sites.
    """
    pass