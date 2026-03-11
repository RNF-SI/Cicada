from django.contrib import admin

from .models import Inpg


@admin.register(Inpg)
class InpgAdmin(admin.ModelAdmin):
    list_display = ('id_inpg', 'id_metier', 'lb_site', 'region', 'departements', 'typologie_1')
    list_filter = ('region', 'typologie_1', 'etat_de_conservation')
    search_fields = ('lb_site', 'id_metier', 'communes', 'departements')
    readonly_fields = ('id_inpg',)
