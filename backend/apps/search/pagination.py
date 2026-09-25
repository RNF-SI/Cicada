"""Pagination de l'exploration des données."""

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

    def get_paginated_response(self, data, **extra):  # noqa: D102 (cf. docstring de classe)
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


class FederationPagination(ExplorationPagination):
    """
    Pagination de la publication vers l'exploration centralisée (#636).

    Pages nettement plus grosses que celles de l'interface : c'est une
    synchronisation machine à machine, et l'index complet représentera de
    l'ordre de 1,3 M de documents une fois les ~4 400 plans repris. À 100 par
    page, une resynchronisation demanderait 13 000 requêtes.
    """

    page_size = 500
    max_page_size = 2000
