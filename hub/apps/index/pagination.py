"""
Pagination de l'exploration.

Forme de réponse identique à celle de CICADA : pendant la transition, une même
page d'interface peut être servie par un index local ou par le hub, et le
frontend ne doit pas avoir à distinguer les deux.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ExplorationPagination(PageNumberPagination):
    """
    Pagination des résultats d'exploration.

    ``get_paginated_response`` accepte des métadonnées supplémentaires : le mode
    « contenu » y place les compteurs par type, qui alimentent les onglets
    « Tout (24) / Pressions (2) / … » au-dessus de la liste.
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data, **extra):  # noqa: D102
        corps = {
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'pagination': {
                'count': self.page.paginator.count,
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'page_size': self.get_page_size(self.request),
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            },
            'results': data,
        }
        corps.update(extra)
        return Response(corps)
