"""
Interface d'administration pour les instances
"""
from django.contrib import admin, messages
from django.utils import timezone

from .adhesion import EchecEnrolement, enroler_sur_hub
from .models import AdhesionHub, Heartbeat, Instance


@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ('token_short', 'version', 'last_heartbeat', 'is_active', 
                    'structure_name', 'rgpd_consent')
    list_filter = ('is_active', 'version', 'rgpd_consent', 'last_heartbeat')
    search_fields = ('token', 'admin_email', 'structure_name')
    readonly_fields = ('token', 'first_seen', 'created_at', 'updated_at')
    
    def token_short(self, obj):
        return str(obj.token)[:8] + '...'
    token_short.short_description = 'Token'


@admin.register(Heartbeat)
class HeartbeatAdmin(admin.ModelAdmin):
    list_display = ('instance', 'timestamp', 'version', 'ip_address')
    list_filter = ('timestamp', 'version')
    readonly_fields = ('instance', 'timestamp', 'version', 'ip_address')


RAPPEL_VERIFICATION = "Vérifiez auprès de la structure que la demande émane bien d'elle avant d'accepter."


@admin.register(AdhesionHub)
class AdhesionHubAdmin(admin.ModelAdmin):
    """Validation manuelle, par RNF, des adhésions au hub (#696).

    Tout est en lecture seule sauf le motif de refus : la demande est l'œuvre de
    l'instance, et les empreintes doivent être enrôlées telles qu'elle les a envoyées.
    """
    list_display = ('libelle', 'instance_id_demande', 'statut', 'demandee_le', 'traitee_le')
    list_filter = ('statut',)
    search_fields = ('libelle', 'instance_id_demande')
    actions = ['accepter', 'refuser']
    readonly_fields = ('instance', 'instance_id_demande', 'libelle', 'url_publique',
                       'statut', 'empreinte_depot', 'empreinte_lecture', 'hub_url',
                       'demandee_le', 'traitee_le', 'traitee_par')
    fieldsets = (
        ('Demande', {'fields': ('instance', 'instance_id_demande', 'libelle', 'url_publique',
                                'demandee_le'),
                     'description': RAPPEL_VERIFICATION}),
        ('Décision', {'fields': ('statut', 'motif_refus', 'hub_url', 'traitee_le', 'traitee_par'),
                      'description': "Pour refuser : saisir le motif, enregistrer, puis lancer l'action "
                                     "« Refuser » depuis la liste. Il est affiché à la structure."}),
        ('Empreintes des jetons', {'fields': ('empreinte_depot', 'empreinte_lecture'),
                                   'classes': ('collapse',)}),
    )

    def has_add_permission(self, request):
        # Une demande vient toujours d'une instance, authentifiée par son jeton de
        # suivi : en créer une ici n'aurait pas d'émetteur.
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), 'subtitle': RAPPEL_VERIFICATION}
        return super().changelist_view(request, extra_context=extra_context)

    def _traiter(self, adhesion, request, statut):
        adhesion.statut = statut
        adhesion.traitee_le = timezone.now()
        adhesion.traitee_par = request.user.get_username()

    @admin.action(description="Accepter et enrôler sur le hub")
    def accepter(self, request, queryset):
        for adhesion in queryset:
            if adhesion.statut != AdhesionHub.EN_ATTENTE:
                self.message_user(request, f"{adhesion} : seule une demande en attente peut être acceptée.",
                                  messages.WARNING)
                continue
            try:
                hub_url = enroler_sur_hub(adhesion)
            except EchecEnrolement as exc:
                # La demande reste en attente : on ne déclare pas « acceptée »
                # une instance que le hub ne connaît pas.
                self.message_user(request, f"{adhesion} : enrôlement impossible. {exc}", messages.ERROR)
                continue
            self._traiter(adhesion, request, AdhesionHub.ACCEPTEE)
            adhesion.hub_url = hub_url
            adhesion.motif_refus = ''
            adhesion.save()
            self.message_user(request, f"{adhesion.libelle} ({adhesion.instance_id_demande}) est enrôlée "
                                       f"sur le hub.", messages.SUCCESS)

    @admin.action(description="Refuser")
    def refuser(self, request, queryset):
        for adhesion in queryset:
            if adhesion.statut != AdhesionHub.EN_ATTENTE:
                # Refuser une adhésion acceptée laisserait l'instance enrôlée sur
                # le hub tout en lui affichant « refusée » : le retrait se fait sur le hub.
                self.message_user(request, f"{adhesion} : seule une demande en attente peut être refusée.",
                                  messages.WARNING)
                continue
            self._traiter(adhesion, request, AdhesionHub.REFUSEE)
            adhesion.save()
            if not adhesion.motif_refus:
                self.message_user(request, f"{adhesion.libelle} : refusée sans motif — la structure ne saura "
                                           "pas quoi corriger. Vous pouvez encore en saisir un.",
                                  messages.WARNING)
            else:
                self.message_user(request, f"{adhesion.libelle} : demande refusée.", messages.SUCCESS)
