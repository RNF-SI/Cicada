"""
Filtres Django pour les Plans de Gestion.
"""
import django_filters
from django.db import models
from django_filters import rest_framework as filters
from datetime import datetime

from .models import PlanGestion, CorPgFichier
from apps.core.models import Nomenclature


class PlanGestionFilter(filters.FilterSet):
    """
    Filtres pour les Plans de Gestion.
    """

    # Filtres de base
    statut = filters.ChoiceFilter(choices=PlanGestion.STATUT_CHOICES)
    gestion_partagee = filters.BooleanFilter()
    ct88 = filters.BooleanFilter()
    risque_incendie = filters.BooleanFilter()

    # Filtres par période
    annee_debut = filters.NumberFilter()
    annee_fin = filters.NumberFilter()
    annee_debut_gte = filters.NumberFilter(field_name='annee_debut', lookup_expr='gte')
    annee_debut_lte = filters.NumberFilter(field_name='annee_debut', lookup_expr='lte')
    annee_fin_gte = filters.NumberFilter(field_name='annee_fin', lookup_expr='gte')
    annee_fin_lte = filters.NumberFilter(field_name='annee_fin', lookup_expr='lte')

    # Filtre pour plans actifs (annee courante dans la periode du plan)
    actif = filters.BooleanFilter(method='filter_actif')

    # Filtre pour plans actifs dans une année donnée
    actif_en_annee = filters.NumberFilter(method='filter_actif_en_annee')
    
    # Filtres par nomenclatures
    evaluation = filters.ModelChoiceFilter(
        field_name='id_evaluation',
        queryset=Nomenclature.objects.filter(id_type__mnemonique='Evaluation PG')
    )
    redacteur_type = filters.ModelChoiceFilter(
        field_name='id_redacteur_type',
        queryset=Nomenclature.objects.filter(id_type__mnemonique='Rédacteur type')
    )
    
    # Filtres par relations
    site_id = filters.NumberFilter(field_name='sites__site__id_site')
    organisme_id = filters.NumberFilter(method='filter_by_organisme_id')
    organisme = filters.NumberFilter(method='filter_by_organisme_id')
    referent_id = filters.NumberFilter(field_name='referents__id_role')
    
    # Filtres géospatiaux
    a_geometrie = filters.BooleanFilter(method='filter_a_geometrie')
    
    # Filtres de dates
    cree_apres = filters.DateFilter(field_name='date_ajout', lookup_expr='gte')
    cree_avant = filters.DateFilter(field_name='date_ajout', lookup_expr='lte')
    modifie_apres = filters.DateFilter(field_name='date_maj', lookup_expr='gte')
    modifie_avant = filters.DateFilter(field_name='date_maj', lookup_expr='lte')
    
    # Filtres par utilisateurs
    cree_par = filters.NumberFilter(field_name='id_utilisateur_ajout__id_role')
    modifie_par = filters.NumberFilter(field_name='id_utilisateur_maj__id_role')
    
    # Filtres textuels avancés
    nom_contient = filters.CharFilter(field_name='nom', lookup_expr='icontains')
    redacteur_nom_contient = filters.CharFilter(
        field_name='redacteur_nom', lookup_expr='icontains'
    )
    commentaire_contient = filters.CharFilter(
        field_name='commentaire', lookup_expr='icontains'
    )
    
    # Filtres par nombre d'éléments
    min_sites = filters.NumberFilter(method='filter_min_sites')
    max_sites = filters.NumberFilter(method='filter_max_sites')
    min_fichiers = filters.NumberFilter(method='filter_min_fichiers')
    max_fichiers = filters.NumberFilter(method='filter_max_fichiers')
    
    # Filtres spéciaux
    multi_sites = filters.BooleanFilter(method='filter_multi_sites')
    avec_fichiers = filters.BooleanFilter(method='filter_avec_fichiers')
    avec_referents = filters.BooleanFilter(method='filter_avec_referents')
    
    class Meta:
        model = PlanGestion
        fields = {
            'id_pg': ['exact'],
            'id_cdr': ['exact', 'icontains'],
            'version': ['exact', 'icontains'],
        }
    
    def filter_actif(self, queryset, name, value):
        """Filtrer les plans actifs (annee courante dans la periode du plan)."""
        current_year = datetime.now().year
        if value is True:
            return queryset.filter(
                annee_debut__lte=current_year,
                annee_fin__gte=current_year
            )
        elif value is False:
            from django.db.models import Q
            return queryset.filter(
                Q(annee_debut__gt=current_year) | Q(annee_fin__lt=current_year)
            )
        return queryset

    def filter_actif_en_annee(self, queryset, name, value):
        """Filtrer les plans actifs dans une année donnée."""
        if value:
            return queryset.filter(
                annee_debut__lte=value,
                annee_fin__gte=value
            )
        return queryset
    
    def filter_by_organisme_id(self, queryset, name, value):
        """Filtrer par organisme gestionnaire via CorOgSite."""
        from apps.users.models import CorOgSite
        site_ids = CorOgSite.objects.filter(
            uuid_og__id_organisme=value
        ).values_list('id_site_id', flat=True)
        return queryset.filter(sites__site__id_site__in=site_ids).distinct()

    def filter_a_geometrie(self, queryset, name, value):
        """Filtrer selon la présence d'une géométrie."""
        if value is True:
            return queryset.filter(geometrie__isnull=False)
        elif value is False:
            return queryset.filter(geometrie__isnull=True)
        return queryset
    
    def filter_min_sites(self, queryset, name, value):
        """Filtrer par nombre minimum de sites."""
        if value:
            return queryset.annotate(
                nb_sites=models.Count('sites')
            ).filter(nb_sites__gte=value)
        return queryset
    
    def filter_max_sites(self, queryset, name, value):
        """Filtrer par nombre maximum de sites."""
        if value:
            return queryset.annotate(
                nb_sites=models.Count('sites')
            ).filter(nb_sites__lte=value)
        return queryset
    
    def filter_min_fichiers(self, queryset, name, value):
        """Filtrer par nombre minimum de fichiers."""
        if value:
            return queryset.annotate(
                nb_fichiers=models.Count('fichiers')
            ).filter(nb_fichiers__gte=value)
        return queryset
    
    def filter_max_fichiers(self, queryset, name, value):
        """Filtrer par nombre maximum de fichiers."""
        if value:
            return queryset.annotate(
                nb_fichiers=models.Count('fichiers')
            ).filter(nb_fichiers__lte=value)
        return queryset
    
    def filter_multi_sites(self, queryset, name, value):
        """Filtrer les plans multi-sites."""
        if value is True:
            return queryset.annotate(
                nb_sites=models.Count('sites')
            ).filter(nb_sites__gt=1)
        elif value is False:
            return queryset.annotate(
                nb_sites=models.Count('sites')
            ).filter(nb_sites__lte=1)
        return queryset
    
    def filter_avec_fichiers(self, queryset, name, value):
        """Filtrer selon la présence de fichiers."""
        if value is True:
            return queryset.filter(fichiers__isnull=False).distinct()
        elif value is False:
            return queryset.filter(fichiers__isnull=True)
        return queryset
    
    def filter_avec_referents(self, queryset, name, value):
        """Filtrer selon la présence de référents."""
        if value is True:
            return queryset.filter(referents__isnull=False).distinct()
        elif value is False:
            return queryset.filter(referents__isnull=True)
        return queryset


class CorPgFichierFilter(filters.FilterSet):
    """
    Filtres pour les fichiers de Plans de Gestion.
    """
    
    # Filtres de base
    type_fichier = filters.ChoiceFilter(choices=CorPgFichier.TYPE_FICHIER_CHOICES)
    public = filters.BooleanFilter()
    
    # Filtres par plan
    plan_id = filters.NumberFilter(field_name='plan_de_gestion__id_pg')
    plan_nom = filters.CharFilter(
        field_name='plan_de_gestion__nom', lookup_expr='icontains'
    )
    plan_statut = filters.ChoiceFilter(
        field_name='plan_de_gestion__statut',
        choices=PlanGestion.STATUT_CHOICES
    )
    
    # Filtres par taille
    taille_min = filters.NumberFilter(field_name='taille_fichier', lookup_expr='gte')
    taille_max = filters.NumberFilter(field_name='taille_fichier', lookup_expr='lte')
    
    # Filtres par extension
    extension = filters.CharFilter(lookup_expr='iexact')
    
    # Filtres par dates
    upload_apres = filters.DateFilter(field_name='date_upload', lookup_expr='gte')
    upload_avant = filters.DateFilter(field_name='date_upload', lookup_expr='lte')
    modifie_apres = filters.DateFilter(field_name='date_maj', lookup_expr='gte')
    modifie_avant = filters.DateFilter(field_name='date_maj', lookup_expr='lte')
    
    # Filtres par utilisateur
    upload_par = filters.NumberFilter(field_name='id_utilisateur_upload__id_role')
    
    # Filtres textuels
    nom_contient = filters.CharFilter(field_name='nom_fichier', lookup_expr='icontains')
    titre_contient = filters.CharFilter(field_name='titre', lookup_expr='icontains')
    auteur_contient = filters.CharFilter(field_name='auteur', lookup_expr='icontains')
    
    # Filtres spéciaux
    images_seulement = filters.BooleanFilter(method='filter_images_seulement')
    documents_seulement = filters.BooleanFilter(method='filter_documents_seulement')
    
    class Meta:
        model = CorPgFichier
        fields = {
            'ordre_affichage': ['exact', 'gte', 'lte'],
        }
    
    def filter_images_seulement(self, queryset, name, value):
        """Filtrer seulement les images."""
        if value is True:
            return queryset.filter(
                extension__in=['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
            )
        return queryset
    
    def filter_documents_seulement(self, queryset, name, value):
        """Filtrer seulement les documents."""
        if value is True:
            return queryset.filter(
                extension__in=['.pdf', '.doc', '.docx', '.odt', '.txt']
            )
        return queryset


# Filtres pour recherches rapides

class PlanGestionQuickFilter:
    """Filtres rapides prédéfinis pour les Plans de Gestion."""
    
    @staticmethod
    def actifs_cette_annee():
        """Plans actifs cette année."""
        current_year = datetime.now().year
        return {
            'annee_debut__lte': current_year,
            'annee_fin__gte': current_year
        }
    
    @staticmethod
    def en_cours_redaction():
        """Plans en cours de rédaction."""
        return {'statut': 'draft'}
    
    @staticmethod
    def valides():
        """Plans validés."""
        return {'statut': 'valide'}
    
    @staticmethod
    def multi_sites():
        """Plans multi-sites."""
        return {'gestion_partagee': True}
    
    @staticmethod
    def avec_geometrie():
        """Plans avec géométrie."""
        return {'geometrie__isnull': False}
    
    @staticmethod
    def recents(jours=30):
        """Plans créés récemment."""
        from django.utils import timezone
        date_limite = timezone.now() - timezone.timedelta(days=jours)
        return {'date_ajout__gte': date_limite}
    
    @staticmethod
    def modifies_recemment(jours=7):
        """Plans modifiés récemment."""
        from django.utils import timezone
        date_limite = timezone.now() - timezone.timedelta(days=jours)
        return {'date_maj__gte': date_limite}
    
    @staticmethod
    def par_organisme(organisme_id):
        """Plans d'un organisme."""
        from apps.users.models import CorOgSite
        site_ids = CorOgSite.objects.filter(
            uuid_og__id_organisme=organisme_id
        ).values_list('id_site_id', flat=True)
        return {'sites__site__id_site__in': list(site_ids)}
    
    @staticmethod
    def par_referent(referent_id):
        """Plans d'un référent."""
        return {'referents__id_role': referent_id}